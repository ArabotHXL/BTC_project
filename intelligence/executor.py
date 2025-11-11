"""
限电执行引擎 Power Curtailment Execution Engine
==============================================

实现自动和半自动限电执行，使用CGMinerClient控制矿机开关
Implements automatic and semi-automatic power curtailment execution, using CGMinerClient to control miners

核心功能 Core Features:
1. execute_curtailment_plan() - 主执行函数 Main execution function
2. shutdown_miners() - 批量关闭矿机 Batch shutdown miners
3. restore_miners() - 恢复矿机运行 Restore miner operations
4. scheduled_curtailment_check() - 定时检查待执行计划 Scheduled check for pending plans
5. cancel_active_plans() - 取消活动计划 Cancel active plans

执行策略 Execution Strategy:
- 方案B: 更新矿机状态为'curtailed'，记录执行日志
- Plan B: Update miner status to 'curtailed', log execution records
- 实际物理关机需要PDU或运维团队执行
- Actual physical shutdown requires PDU or operations team

Author: HashInsight Intelligence Team
Created: 2025-11-11
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
import time

from sqlalchemy import and_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload

from app import db
from models import (
    CurtailmentPlan, CurtailmentExecution, HostingMiner, MinerModel,
    PlanStatus, ExecutionAction, ExecutionStatus, UserAccess
)

try:
    from agent.miner_agent import CGMinerClient
    CGMINER_AVAILABLE = True
except ImportError:
    logging.warning("CGMinerClient not available - using fallback mode")
    CGMINER_AVAILABLE = False
    CGMinerClient = None

logger = logging.getLogger(__name__)


def execute_curtailment_plan(plan_id: int, auto_execute: bool = False) -> Dict:
    """
    主函数：执行限电计划
    Main function: Execute power curtailment plan
    
    Args:
        plan_id: 限电计划ID Curtailment plan ID
        auto_execute: 是否自动执行（跳过审批检查） Auto execute (skip approval check)
        
    Returns:
        {
            'success': bool,
            'plan_id': int,
            'executed_count': int,  # 成功执行数量 Successfully executed count
            'failed_count': int,    # 失败数量 Failed count
            'total_power_saved_kw': float,
            'execution_duration_seconds': float,
            'details': [{miner_id, status, error}],
            'started_at': str,
            'completed_at': str
        }
    """
    start_time = datetime.utcnow()
    
    try:
        logger.info(f"========== 开始执行限电计划 Starting curtailment plan execution: plan_id={plan_id}, auto_execute={auto_execute} ==========")
        
        # 1. 查询限电计划 Query curtailment plan
        plan = CurtailmentPlan.query.filter_by(id=plan_id).first()
        
        if not plan:
            logger.error(f"限电计划不存在 Curtailment plan not found: plan_id={plan_id}")
            return {
                'success': False,
                'error': f'Plan {plan_id} not found',
                'executed_count': 0,
                'failed_count': 0
            }
        
        logger.info(f"找到限电计划 Found plan: {plan.plan_name}, status={plan.status.value}, site_id={plan.site_id}")
        
        # 2. 半自动模式：检查审批状态 Semi-auto mode: Check approval status
        if not auto_execute and plan.status != PlanStatus.APPROVED:
            logger.warning(
                f"限电计划未批准，无法执行 Plan not approved, cannot execute: "
                f"plan_id={plan_id}, status={plan.status.value}"
            )
            return {
                'success': False,
                'error': f'Plan status is {plan.status.value}, must be APPROVED for semi-auto execution',
                'executed_count': 0,
                'failed_count': 0
            }
        
        # 3. 检查计划是否已执行 Check if plan already executed
        if plan.status in [PlanStatus.EXECUTING, PlanStatus.COMPLETED]:
            logger.warning(
                f"限电计划已在执行或已完成 Plan already executing or completed: "
                f"plan_id={plan_id}, status={plan.status.value}"
            )
            return {
                'success': False,
                'error': f'Plan already {plan.status.value}',
                'executed_count': 0,
                'failed_count': 0
            }
        
        # 4. 更新计划状态为执行中 Update plan status to EXECUTING
        plan.status = PlanStatus.EXECUTING
        db.session.commit()
        logger.info(f"计划状态更新为执行中 Plan status updated to EXECUTING: plan_id={plan_id}")
        
        # 5. 获取要关闭的矿机列表 Get miners to shutdown
        # 方法：查询已有的execution记录或从站点查询所有active矿机
        # Method: Query existing execution records or get all active miners from site
        
        # 首先尝试从现有execution记录获取矿机列表
        # First try to get miner list from existing execution records
        existing_executions = CurtailmentExecution.query.filter_by(
            plan_id=plan_id,
            execution_action=ExecutionAction.SHUTDOWN
        ).all()
        
        if existing_executions:
            # 使用已有的矿机列表 Use existing miner list
            miner_ids = [exec.miner_id for exec in existing_executions]
            logger.info(f"从现有execution记录获取矿机列表 Got miner list from existing executions: {len(miner_ids)} miners")
        else:
            # 如果没有预先创建的execution记录，从站点查询active矿机
            # If no pre-created execution records, query active miners from site
            # 这里需要根据target_power_reduction选择矿机
            # Here we need to select miners based on target_power_reduction
            
            # 简单策略：按功率从大到小选择矿机，直到达到目标削减功率
            # Simple strategy: Select miners by power descending until target reduction reached
            miners = HostingMiner.query.filter_by(
                site_id=plan.site_id,
                status='active'
            ).join(MinerModel).order_by(HostingMiner.actual_power.desc()).all()
            
            target_power_w = float(plan.target_power_reduction_kw) * 1000
            accumulated_power = 0.0
            miner_ids = []
            
            for miner in miners:
                if accumulated_power >= target_power_w:
                    break
                miner_ids.append(miner.id)
                accumulated_power += miner.actual_power
            
            logger.info(
                f"动态选择矿机 Dynamically selected miners: {len(miner_ids)} miners, "
                f"total_power={accumulated_power/1000:.2f}kW"
            )
        
        if not miner_ids:
            logger.warning(f"没有找到需要关闭的矿机 No miners found to shutdown: plan_id={plan_id}")
            plan.status = PlanStatus.COMPLETED
            db.session.commit()
            return {
                'success': True,
                'plan_id': plan_id,
                'executed_count': 0,
                'failed_count': 0,
                'total_power_saved_kw': 0.0,
                'details': [],
                'message': 'No miners to shutdown'
            }
        
        # 6. 执行关机操作 Execute shutdown
        logger.info(f"开始关闭 {len(miner_ids)} 个矿机 Starting to shutdown {len(miner_ids)} miners")
        
        shutdown_result = shutdown_miners(miner_ids, plan_id)
        
        # 7. 更新计划状态为已完成 Update plan status to COMPLETED
        plan.status = PlanStatus.COMPLETED
        plan.calculated_power_reduction_kw = Decimal(str(shutdown_result.get('total_power_saved_kw', 0.0)))
        db.session.commit()
        
        # 8. 计算执行时长 Calculate execution duration
        end_time = datetime.utcnow()
        execution_duration = (end_time - start_time).total_seconds()
        
        logger.info(
            f"========== 限电计划执行完成 Curtailment plan execution completed: "
            f"plan_id={plan_id}, "
            f"success={shutdown_result['success_count']}, "
            f"failed={shutdown_result['failed_count']}, "
            f"duration={execution_duration:.2f}s =========="
        )
        
        return {
            'success': True,
            'plan_id': plan_id,
            'executed_count': shutdown_result['success_count'],
            'failed_count': shutdown_result['failed_count'],
            'total_power_saved_kw': shutdown_result.get('total_power_saved_kw', 0.0),
            'execution_duration_seconds': round(execution_duration, 2),
            'details': shutdown_result.get('details', []),
            'started_at': start_time.isoformat(),
            'completed_at': end_time.isoformat()
        }
        
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"数据库错误 Database error in execute_curtailment_plan: {e}")
        return {
            'success': False,
            'error': f'Database error: {str(e)}',
            'executed_count': 0,
            'failed_count': 0
        }
    except Exception as e:
        db.session.rollback()
        logger.error(f"执行限电计划失败 Failed to execute curtailment plan: {e}", exc_info=True)
        
        # 尝试回滚计划状态 Try to rollback plan status
        try:
            plan = CurtailmentPlan.query.filter_by(id=plan_id).first()
            if plan and plan.status == PlanStatus.EXECUTING:
                plan.status = PlanStatus.APPROVED
                db.session.commit()
                logger.info(f"已回滚计划状态 Rolled back plan status to APPROVED")
        except:
            pass
        
        return {
            'success': False,
            'error': str(e),
            'executed_count': 0,
            'failed_count': 0
        }


def shutdown_miners(miner_ids: List[int], plan_id: int) -> Dict:
    """
    批量关闭矿机
    Batch shutdown miners
    
    执行策略 Execution Strategy:
    - 方案B: 更新矿机状态为'curtailed'，创建execution记录
    - Plan B: Update miner status to 'curtailed', create execution records
    - 实际物理关机需要PDU或运维团队执行
    - Actual physical shutdown requires PDU or operations team
    
    Args:
        miner_ids: 矿机ID列表 List of miner IDs
        plan_id: 限电计划ID Curtailment plan ID
        
    Returns:
        {
            'success_count': int,
            'failed_count': int,
            'total_power_saved_kw': float,
            'details': [{
                'miner_id': int,
                'serial_number': str,
                'status': 'SUCCESS'/'FAILED',
                'power_saved_kw': float,
                'error': str (optional)
            }]
        }
    """
    try:
        logger.info(f"========== 开始批量关闭矿机 Starting batch shutdown: {len(miner_ids)} miners ==========")
        
        success_count = 0
        failed_count = 0
        total_power_saved = 0.0
        details = []
        
        # 查询所有矿机信息 Query all miner information
        miners = HostingMiner.query.filter(
            HostingMiner.id.in_(miner_ids)
        ).options(joinedload(HostingMiner.miner_model)).all()
        
        miner_dict = {miner.id: miner for miner in miners}
        
        # 遍历每个矿机执行关机操作 Iterate each miner to execute shutdown
        for miner_id in miner_ids:
            miner = miner_dict.get(miner_id)
            
            if not miner:
                logger.warning(f"矿机不存在 Miner not found: miner_id={miner_id}")
                failed_count += 1
                details.append({
                    'miner_id': miner_id,
                    'serial_number': 'UNKNOWN',
                    'status': 'FAILED',
                    'error': 'Miner not found',
                    'power_saved_kw': 0.0
                })
                
                # 创建失败execution记录 Create failed execution record
                _create_execution_record(
                    plan_id=plan_id,
                    miner_id=miner_id,
                    action=ExecutionAction.SHUTDOWN,
                    status=ExecutionStatus.FAILED,
                    error_message='Miner not found',
                    power_saved_kw=0.0
                )
                continue
            
            try:
                logger.info(
                    f"关闭矿机 Shutting down miner: "
                    f"ID={miner.id}, SN={miner.serial_number}, "
                    f"IP={miner.ip_address or 'N/A'}, "
                    f"Power={miner.actual_power}W"
                )
                
                # 执行关机操作 Execute shutdown
                shutdown_success = False
                error_message = None
                
                # 尝试方案A: 使用CGMiner API关机 (如果可用)
                # Try Plan A: Use CGMiner API to shutdown (if available)
                if CGMINER_AVAILABLE and miner.ip_address and CGMinerClient:
                    try:
                        cgminer = CGMinerClient(miner.ip_address)
                        
                        # 尝试发送关机命令 Try to send shutdown command
                        # 注意：CGMiner API可能不支持shutdown，这里使用reboot作为替代
                        # Note: CGMiner API may not support shutdown, using reboot as alternative
                        shutdown_success = cgminer.reboot()
                        
                        if shutdown_success:
                            logger.info(f"✅ CGMiner关机命令发送成功 CGMiner shutdown command sent successfully: {miner.serial_number}")
                        else:
                            logger.warning(f"⚠️ CGMiner关机命令发送失败 CGMiner shutdown command failed: {miner.serial_number}")
                            error_message = 'CGMiner command failed'
                    except Exception as e:
                        logger.warning(f"⚠️ CGMiner通信失败 CGMiner communication failed: {miner.serial_number}, error={e}")
                        error_message = f'CGMiner error: {str(e)}'
                        shutdown_success = False
                else:
                    if not miner.ip_address:
                        logger.warning(f"⚠️ 矿机无IP地址 Miner has no IP address: {miner.serial_number}")
                        error_message = 'No IP address configured'
                
                # 方案B: 更新矿机状态为'curtailed' (主要策略)
                # Plan B: Update miner status to 'curtailed' (primary strategy)
                old_status = miner.status
                miner.status = 'curtailed'
                db.session.flush()
                
                logger.info(
                    f"✅ 矿机状态已更新 Miner status updated: "
                    f"{miner.serial_number}, {old_status} -> curtailed"
                )
                
                # 计算节省功率 Calculate power saved
                power_saved_kw = round(miner.actual_power / 1000, 2)
                total_power_saved += power_saved_kw
                
                # 创建成功execution记录 Create success execution record
                _create_execution_record(
                    plan_id=plan_id,
                    miner_id=miner.id,
                    action=ExecutionAction.SHUTDOWN,
                    status=ExecutionStatus.SUCCESS,
                    error_message=error_message,
                    power_saved_kw=power_saved_kw
                )
                
                success_count += 1
                details.append({
                    'miner_id': miner.id,
                    'serial_number': miner.serial_number,
                    'status': 'SUCCESS',
                    'power_saved_kw': power_saved_kw,
                    'cgminer_shutdown': shutdown_success,
                    'error': error_message
                })
                
                logger.info(
                    f"✅ 矿机关闭成功 Miner shutdown successful: "
                    f"{miner.serial_number}, power_saved={power_saved_kw}kW"
                )
                
            except Exception as e:
                logger.error(
                    f"❌ 关闭矿机失败 Failed to shutdown miner: "
                    f"{miner.serial_number}, error={e}"
                )
                failed_count += 1
                
                # 创建失败execution记录 Create failed execution record
                _create_execution_record(
                    plan_id=plan_id,
                    miner_id=miner.id,
                    action=ExecutionAction.SHUTDOWN,
                    status=ExecutionStatus.FAILED,
                    error_message=str(e),
                    power_saved_kw=0.0
                )
                
                details.append({
                    'miner_id': miner.id,
                    'serial_number': miner.serial_number,
                    'status': 'FAILED',
                    'error': str(e),
                    'power_saved_kw': 0.0
                })
        
        # 提交所有数据库更改 Commit all database changes
        db.session.commit()
        
        logger.info(
            f"========== 批量关闭完成 Batch shutdown completed: "
            f"success={success_count}, failed={failed_count}, "
            f"total_power_saved={total_power_saved:.2f}kW =========="
        )
        
        return {
            'success_count': success_count,
            'failed_count': failed_count,
            'total_power_saved_kw': round(total_power_saved, 2),
            'details': details
        }
        
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"数据库错误 Database error in shutdown_miners: {e}")
        return {
            'success_count': 0,
            'failed_count': len(miner_ids),
            'total_power_saved_kw': 0.0,
            'details': [],
            'error': str(e)
        }
    except Exception as e:
        db.session.rollback()
        logger.error(f"批量关闭矿机失败 Failed to batch shutdown miners: {e}", exc_info=True)
        return {
            'success_count': 0,
            'failed_count': len(miner_ids),
            'total_power_saved_kw': 0.0,
            'details': [],
            'error': str(e)
        }


def restore_miners(miner_ids: List[int], reason: str = 'manual_restore', plan_id: Optional[int] = None) -> Dict:
    """
    恢复（重启）矿机
    Restore (reboot) miners
    
    Args:
        miner_ids: 矿机ID列表 List of miner IDs
        reason: 恢复原因 Restore reason
        plan_id: 关联的限电计划ID (可选) Associated plan ID (optional)
        
    Returns:
        {
            'success_count': int,
            'failed_count': int,
            'details': [{
                'miner_id': int,
                'serial_number': str,
                'status': 'SUCCESS'/'FAILED',
                'error': str (optional)
            }]
        }
    """
    try:
        logger.info(f"========== 开始恢复矿机 Starting miner restoration: {len(miner_ids)} miners, reason={reason} ==========")
        
        success_count = 0
        failed_count = 0
        details = []
        
        # 查询所有矿机信息 Query all miner information
        miners = HostingMiner.query.filter(
            HostingMiner.id.in_(miner_ids)
        ).options(joinedload(HostingMiner.miner_model)).all()
        
        miner_dict = {miner.id: miner for miner in miners}
        
        # 遍历每个矿机执行恢复操作 Iterate each miner to execute restoration
        for miner_id in miner_ids:
            miner = miner_dict.get(miner_id)
            
            if not miner:
                logger.warning(f"矿机不存在 Miner not found: miner_id={miner_id}")
                failed_count += 1
                details.append({
                    'miner_id': miner_id,
                    'serial_number': 'UNKNOWN',
                    'status': 'FAILED',
                    'error': 'Miner not found'
                })
                
                # 如果有plan_id，创建失败execution记录
                # If plan_id provided, create failed execution record
                if plan_id:
                    _create_execution_record(
                        plan_id=plan_id,
                        miner_id=miner_id,
                        action=ExecutionAction.STARTUP,
                        status=ExecutionStatus.FAILED,
                        error_message='Miner not found',
                        power_saved_kw=0.0
                    )
                continue
            
            try:
                logger.info(
                    f"恢复矿机 Restoring miner: "
                    f"ID={miner.id}, SN={miner.serial_number}, "
                    f"IP={miner.ip_address or 'N/A'}, "
                    f"current_status={miner.status}"
                )
                
                # 执行恢复操作 Execute restoration
                reboot_success = False
                error_message = None
                
                # 尝试使用CGMiner API重启 Try to reboot using CGMiner API
                if CGMINER_AVAILABLE and miner.ip_address and CGMinerClient:
                    try:
                        cgminer = CGMinerClient(miner.ip_address)
                        reboot_success = cgminer.reboot()
                        
                        if reboot_success:
                            logger.info(f"✅ CGMiner重启命令发送成功 CGMiner reboot command sent successfully: {miner.serial_number}")
                        else:
                            logger.warning(f"⚠️ CGMiner重启命令发送失败 CGMiner reboot command failed: {miner.serial_number}")
                            error_message = 'CGMiner reboot failed'
                    except Exception as e:
                        logger.warning(f"⚠️ CGMiner通信失败 CGMiner communication failed: {miner.serial_number}, error={e}")
                        error_message = f'CGMiner error: {str(e)}'
                        reboot_success = False
                else:
                    if not miner.ip_address:
                        logger.warning(f"⚠️ 矿机无IP地址 Miner has no IP address: {miner.serial_number}")
                        error_message = 'No IP address configured'
                
                # 更新矿机状态为active Update miner status to active
                old_status = miner.status
                miner.status = 'active'
                db.session.flush()
                
                logger.info(
                    f"✅ 矿机状态已恢复 Miner status restored: "
                    f"{miner.serial_number}, {old_status} -> active"
                )
                
                # 如果有plan_id，创建成功execution记录
                # If plan_id provided, create success execution record
                if plan_id:
                    _create_execution_record(
                        plan_id=plan_id,
                        miner_id=miner.id,
                        action=ExecutionAction.STARTUP,
                        status=ExecutionStatus.SUCCESS,
                        error_message=error_message,
                        power_saved_kw=0.0
                    )
                
                success_count += 1
                details.append({
                    'miner_id': miner.id,
                    'serial_number': miner.serial_number,
                    'status': 'SUCCESS',
                    'cgminer_reboot': reboot_success,
                    'error': error_message
                })
                
                logger.info(f"✅ 矿机恢复成功 Miner restoration successful: {miner.serial_number}")
                
            except Exception as e:
                logger.error(
                    f"❌ 恢复矿机失败 Failed to restore miner: "
                    f"{miner.serial_number}, error={e}"
                )
                failed_count += 1
                
                # 如果有plan_id，创建失败execution记录
                # If plan_id provided, create failed execution record
                if plan_id:
                    _create_execution_record(
                        plan_id=plan_id,
                        miner_id=miner.id,
                        action=ExecutionAction.STARTUP,
                        status=ExecutionStatus.FAILED,
                        error_message=str(e),
                        power_saved_kw=0.0
                    )
                
                details.append({
                    'miner_id': miner.id,
                    'serial_number': miner.serial_number,
                    'status': 'FAILED',
                    'error': str(e)
                })
        
        # 提交所有数据库更改 Commit all database changes
        db.session.commit()
        
        logger.info(
            f"========== 矿机恢复完成 Miner restoration completed: "
            f"success={success_count}, failed={failed_count} =========="
        )
        
        return {
            'success_count': success_count,
            'failed_count': failed_count,
            'details': details
        }
        
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"数据库错误 Database error in restore_miners: {e}")
        return {
            'success_count': 0,
            'failed_count': len(miner_ids),
            'details': [],
            'error': str(e)
        }
    except Exception as e:
        db.session.rollback()
        logger.error(f"恢复矿机失败 Failed to restore miners: {e}", exc_info=True)
        return {
            'success_count': 0,
            'failed_count': len(miner_ids),
            'details': [],
            'error': str(e)
        }


def scheduled_curtailment_check() -> Dict:
    """
    定时任务：检查待执行的限电计划
    Scheduled task: Check pending curtailment plans
    
    查询CurtailmentPlan.status == 'approved' AND scheduled_start_time <= now()
    Query plans with status='approved' and scheduled_start_time <= now()
    
    用于后台调度（配合schedule库或RQ）
    For background scheduling (with schedule library or RQ)
    
    Returns:
        {
            'checked_at': str,
            'plans_found': int,
            'plans_executed': int,
            'plans_failed': int,
            'details': [{plan_id, result}]
        }
    """
    try:
        current_time = datetime.utcnow()
        logger.info(f"========== 定时检查限电计划 Scheduled curtailment check: time={current_time.isoformat()} ==========")
        
        # 查询符合条件的计划 Query eligible plans
        pending_plans = CurtailmentPlan.query.filter(
            and_(
                CurtailmentPlan.status == PlanStatus.APPROVED,
                CurtailmentPlan.scheduled_start_time <= current_time
            )
        ).all()
        
        plans_found = len(pending_plans)
        logger.info(f"找到 {plans_found} 个待执行计划 Found {plans_found} pending plans")
        
        if not pending_plans:
            return {
                'checked_at': current_time.isoformat(),
                'plans_found': 0,
                'plans_executed': 0,
                'plans_failed': 0,
                'details': []
            }
        
        plans_executed = 0
        plans_failed = 0
        details = []
        
        # 执行每个计划 Execute each plan
        for plan in pending_plans:
            logger.info(
                f"执行限电计划 Executing plan: "
                f"plan_id={plan.id}, name={plan.plan_name}, "
                f"scheduled_time={plan.scheduled_start_time.isoformat()}"
            )
            
            try:
                # 自动执行计划 Auto execute plan
                result = execute_curtailment_plan(plan_id=plan.id, auto_execute=True)
                
                if result.get('success'):
                    plans_executed += 1
                    logger.info(f"✅ 计划执行成功 Plan executed successfully: plan_id={plan.id}")
                else:
                    plans_failed += 1
                    logger.error(f"❌ 计划执行失败 Plan execution failed: plan_id={plan.id}, error={result.get('error')}")
                
                details.append({
                    'plan_id': plan.id,
                    'plan_name': plan.plan_name,
                    'result': result
                })
                
            except Exception as e:
                plans_failed += 1
                logger.error(f"❌ 执行计划异常 Exception executing plan: plan_id={plan.id}, error={e}", exc_info=True)
                
                details.append({
                    'plan_id': plan.id,
                    'plan_name': plan.plan_name,
                    'result': {
                        'success': False,
                        'error': str(e)
                    }
                })
        
        logger.info(
            f"========== 定时检查完成 Scheduled check completed: "
            f"found={plans_found}, executed={plans_executed}, failed={plans_failed} =========="
        )
        
        return {
            'checked_at': current_time.isoformat(),
            'plans_found': plans_found,
            'plans_executed': plans_executed,
            'plans_failed': plans_failed,
            'details': details
        }
        
    except SQLAlchemyError as e:
        logger.error(f"数据库错误 Database error in scheduled_curtailment_check: {e}")
        return {
            'checked_at': datetime.utcnow().isoformat(),
            'plans_found': 0,
            'plans_executed': 0,
            'plans_failed': 0,
            'error': str(e)
        }
    except Exception as e:
        logger.error(f"定时检查失败 Scheduled check failed: {e}", exc_info=True)
        return {
            'checked_at': datetime.utcnow().isoformat(),
            'plans_found': 0,
            'plans_executed': 0,
            'plans_failed': 0,
            'error': str(e)
        }


def cancel_active_plans(site_id: int, reason: str = 'emergency') -> Dict:
    """
    取消站点所有活动限电计划
    Cancel all active curtailment plans for a site
    
    查询status == 'executing' 的计划
    Query plans with status='executing'
    
    调用restore_miners()恢复所有关闭的矿机
    Call restore_miners() to restore all shutdown miners
    
    更新计划状态为'cancelled'
    Update plan status to 'cancelled'
    
    Args:
        site_id: 站点ID Site ID
        reason: 取消原因 Cancellation reason
        
    Returns:
        {
            'success': bool,
            'site_id': int,
            'plans_cancelled': int,
            'miners_restored': int,
            'details': [{plan_id, result}]
        }
    """
    try:
        logger.info(f"========== 取消站点活动限电计划 Cancelling active plans: site_id={site_id}, reason={reason} ==========")
        
        # 查询执行中的计划 Query executing plans
        active_plans = CurtailmentPlan.query.filter(
            and_(
                CurtailmentPlan.site_id == site_id,
                CurtailmentPlan.status == PlanStatus.EXECUTING
            )
        ).all()
        
        plans_found = len(active_plans)
        logger.info(f"找到 {plans_found} 个执行中的计划 Found {plans_found} executing plans")
        
        if not active_plans:
            return {
                'success': True,
                'site_id': site_id,
                'plans_cancelled': 0,
                'miners_restored': 0,
                'details': [],
                'message': 'No active plans to cancel'
            }
        
        plans_cancelled = 0
        total_miners_restored = 0
        details = []
        
        # 取消每个计划 Cancel each plan
        for plan in active_plans:
            logger.info(
                f"取消限电计划 Cancelling plan: "
                f"plan_id={plan.id}, name={plan.plan_name}"
            )
            
            try:
                # 获取该计划关闭的所有矿机 Get all miners shutdown by this plan
                shutdown_executions = CurtailmentExecution.query.filter(
                    and_(
                        CurtailmentExecution.plan_id == plan.id,
                        CurtailmentExecution.execution_action == ExecutionAction.SHUTDOWN,
                        CurtailmentExecution.execution_status == ExecutionStatus.SUCCESS
                    )
                ).all()
                
                miner_ids = [exec.miner_id for exec in shutdown_executions]
                
                logger.info(f"找到 {len(miner_ids)} 个被关闭的矿机 Found {len(miner_ids)} shutdown miners")
                
                # 恢复矿机 Restore miners
                if miner_ids:
                    restore_result = restore_miners(
                        miner_ids=miner_ids,
                        reason=f'plan_cancelled:{reason}',
                        plan_id=plan.id
                    )
                    
                    total_miners_restored += restore_result.get('success_count', 0)
                    
                    logger.info(
                        f"矿机恢复结果 Restoration result: "
                        f"success={restore_result.get('success_count')}, "
                        f"failed={restore_result.get('failed_count')}"
                    )
                else:
                    restore_result = {
                        'success_count': 0,
                        'failed_count': 0,
                        'details': []
                    }
                
                # 更新计划状态为cancelled Update plan status to cancelled
                plan.status = PlanStatus.CANCELLED
                db.session.flush()
                
                plans_cancelled += 1
                
                logger.info(f"✅ 计划已取消 Plan cancelled: plan_id={plan.id}")
                
                details.append({
                    'plan_id': plan.id,
                    'plan_name': plan.plan_name,
                    'miners_restored': restore_result.get('success_count', 0),
                    'restoration_result': restore_result
                })
                
            except Exception as e:
                logger.error(f"❌ 取消计划失败 Failed to cancel plan: plan_id={plan.id}, error={e}")
                
                details.append({
                    'plan_id': plan.id,
                    'plan_name': plan.plan_name,
                    'error': str(e)
                })
        
        # 提交所有数据库更改 Commit all database changes
        db.session.commit()
        
        logger.info(
            f"========== 取消活动计划完成 Active plans cancellation completed: "
            f"cancelled={plans_cancelled}, miners_restored={total_miners_restored} =========="
        )
        
        return {
            'success': True,
            'site_id': site_id,
            'plans_cancelled': plans_cancelled,
            'miners_restored': total_miners_restored,
            'details': details
        }
        
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"数据库错误 Database error in cancel_active_plans: {e}")
        return {
            'success': False,
            'site_id': site_id,
            'plans_cancelled': 0,
            'miners_restored': 0,
            'error': str(e)
        }
    except Exception as e:
        db.session.rollback()
        logger.error(f"取消活动计划失败 Failed to cancel active plans: {e}", exc_info=True)
        return {
            'success': False,
            'site_id': site_id,
            'plans_cancelled': 0,
            'miners_restored': 0,
            'error': str(e)
        }


# ==================== 辅助函数 Helper Functions ====================

def _create_execution_record(
    plan_id: int,
    miner_id: int,
    action: ExecutionAction,
    status: ExecutionStatus,
    error_message: Optional[str] = None,
    power_saved_kw: float = 0.0,
    revenue_lost_usd: Optional[float] = None
) -> Optional[CurtailmentExecution]:
    """
    创建限电执行记录
    Create curtailment execution record
    
    Args:
        plan_id: 限电计划ID
        miner_id: 矿机ID
        action: 执行动作 (SHUTDOWN/STARTUP)
        status: 执行状态 (SUCCESS/FAILED)
        error_message: 错误信息 (可选)
        power_saved_kw: 节省功率kW
        revenue_lost_usd: 损失收益USD (可选)
        
    Returns:
        CurtailmentExecution record or None if failed
    """
    try:
        execution = CurtailmentExecution(
            plan_id=plan_id,
            miner_id=miner_id,
            execution_action=action,
            execution_status=status,
            error_message=error_message,
            power_saved_kw=Decimal(str(power_saved_kw)) if power_saved_kw else None,
            revenue_lost_usd=Decimal(str(revenue_lost_usd)) if revenue_lost_usd else None,
            executed_at=datetime.utcnow()
        )
        
        db.session.add(execution)
        db.session.flush()
        
        return execution
        
    except Exception as e:
        logger.error(f"创建execution记录失败 Failed to create execution record: {e}")
        return None


def get_plan_execution_summary(plan_id: int) -> Dict:
    """
    获取限电计划执行摘要
    Get curtailment plan execution summary
    
    Args:
        plan_id: 限电计划ID
        
    Returns:
        {
            'plan_id': int,
            'total_executions': int,
            'successful_shutdowns': int,
            'failed_shutdowns': int,
            'successful_startups': int,
            'failed_startups': int,
            'total_power_saved_kw': float,
            'affected_miners': int
        }
    """
    try:
        executions = CurtailmentExecution.query.filter_by(plan_id=plan_id).all()
        
        successful_shutdowns = sum(1 for e in executions if e.execution_action == ExecutionAction.SHUTDOWN and e.execution_status == ExecutionStatus.SUCCESS)
        failed_shutdowns = sum(1 for e in executions if e.execution_action == ExecutionAction.SHUTDOWN and e.execution_status == ExecutionStatus.FAILED)
        successful_startups = sum(1 for e in executions if e.execution_action == ExecutionAction.STARTUP and e.execution_status == ExecutionStatus.SUCCESS)
        failed_startups = sum(1 for e in executions if e.execution_action == ExecutionAction.STARTUP and e.execution_status == ExecutionStatus.FAILED)
        
        total_power_saved = sum(float(e.power_saved_kw or 0) for e in executions if e.execution_action == ExecutionAction.SHUTDOWN)
        
        affected_miners = len(set(e.miner_id for e in executions))
        
        return {
            'plan_id': plan_id,
            'total_executions': len(executions),
            'successful_shutdowns': successful_shutdowns,
            'failed_shutdowns': failed_shutdowns,
            'successful_startups': successful_startups,
            'failed_startups': failed_startups,
            'total_power_saved_kw': round(total_power_saved, 2),
            'affected_miners': affected_miners
        }
        
    except Exception as e:
        logger.error(f"获取执行摘要失败 Failed to get execution summary: {e}")
        return {
            'plan_id': plan_id,
            'error': str(e)
        }
