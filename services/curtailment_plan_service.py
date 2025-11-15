"""
限电计划服务层 Curtailment Plan Service Layer
==========================================

封装限电计划的核心业务逻辑，实现完整的状态机和执行流程
Encapsulates core business logic for curtailment plans with complete state machine

Author: HashInsight Intelligence Team
Created: 2025-11-15
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

from app import db
from models import (
    CurtailmentPlan, PlanStatus, HostingMiner, 
    CurtailmentExecution, ExecutionAction, ExecutionStatus
)

logger = logging.getLogger(__name__)


class CurtailmentPlanService:
    """
    限电计划服务
    
    提供限电计划的执行和恢复功能，管理完整的生命周期：
    PENDING → EXECUTING → RECOVERY_PENDING → COMPLETED
    """
    
    @staticmethod
    def execute_plan(plan_id: int) -> Dict:
        """
        执行限电计划（关闭矿机）
        
        状态流转: PENDING/APPROVED → EXECUTING
        
        Args:
            plan_id: 计划ID
            
        Returns:
            {
                'success': bool,
                'plan_id': int,
                'plan_name': str,
                'miners_shutdown': int,
                'miners_failed': int,
                'total_power_saved_kw': float,
                'error': str (if failed)
            }
        """
        try:
            # 1. 获取计划并验证状态
            plan = CurtailmentPlan.query.get(plan_id)
            if not plan:
                logger.error(f"❌ 计划不存在: ID={plan_id}")
                return {
                    'success': False,
                    'error': f'Plan not found: {plan_id}'
                }
            
            # 验证状态：只接受PENDING或APPROVED
            if plan.status not in [PlanStatus.PENDING, PlanStatus.APPROVED]:
                logger.warning(f"⚠️ 计划状态不允许执行: {plan.plan_name}, status={plan.status.value}")
                return {
                    'success': False,
                    'error': f'Cannot execute plan with status: {plan.status.value}'
                }
            
            logger.info(f"⚡ 开始执行限电计划: {plan.plan_name} (ID={plan.id})")
            
            # 2. 更新计划状态为EXECUTING（使用flush而不是commit，以便失败时可以rollback）
            plan.status = PlanStatus.EXECUTING
            db.session.flush()
            
            # 3. 调用CurtailmentEngine选择矿机
            from intelligence.curtailment_engine import CurtailmentEngine
            
            engine = CurtailmentEngine(site_id=plan.site_id)
            
            if not plan.strategy_id:
                logger.error(f"❌ 计划没有选择策略: {plan.plan_name}")
                db.session.rollback()
                return {
                    'success': False,
                    'error': 'No strategy selected for plan'
                }
            
            result = engine.calculate_curtailment_plan(
                strategy_id=plan.strategy_id,
                target_reduction_kw=float(plan.target_power_reduction_kw)
            )
            
            if not result or not result.get('selected_miners'):
                logger.warning(f"⚠️ 计划 {plan.plan_name} 没有选中任何矿机，直接完成")
                plan.status = PlanStatus.COMPLETED
                plan.calculated_power_reduction_kw = 0
                db.session.commit()
                return {
                    'success': True,
                    'plan_id': plan.id,
                    'plan_name': plan.plan_name,
                    'miners_shutdown': 0,
                    'miners_failed': 0,
                    'total_power_saved_kw': 0.0,
                    'plan_status': plan.status.value,
                    'message': 'No miners selected for curtailment'
                }
            
            # 4. 获取选中的矿机列表
            selected_miner_ids = [m['miner_id'] for m in result.get('selected_miners', [])]
            miners_to_shutdown = HostingMiner.query.filter(
                HostingMiner.id.in_(selected_miner_ids),
                HostingMiner.status == 'active'
            ).all()
            
            logger.info(f"🔌 准备关闭 {len(miners_to_shutdown)} 台矿机")
            
            # 5. 循环关闭矿机并记录执行结果
            success_count = 0
            failed_count = 0
            total_power_saved = 0.0
            
            for miner in miners_to_shutdown:
                try:
                    # 更新矿机状态为maintenance（限电中）
                    miner.status = 'maintenance'
                    
                    # 计算节省的功率
                    power_saved_kw = (miner.actual_power or 
                                     miner.miner_model.reference_power_consumption) / 1000.0
                    total_power_saved += power_saved_kw
                    
                    # 创建执行记录（SHUTDOWN动作，成功）
                    execution = CurtailmentExecution(
                        plan_id=plan.id,
                        miner_id=miner.id,
                        execution_action=ExecutionAction.SHUTDOWN,
                        execution_status=ExecutionStatus.SUCCESS,
                        power_saved_kw=power_saved_kw
                    )
                    db.session.add(execution)
                    
                    success_count += 1
                    logger.debug(f"  ✅ 矿机已关闭: {miner.serial_number}, 节省功率={power_saved_kw:.2f}kW")
                    
                except Exception as e:
                    failed_count += 1
                    error_msg = str(e)
                    logger.error(f"  ❌ 矿机关闭失败: {miner.serial_number}, 错误={error_msg}")
                    
                    # 创建执行记录（SHUTDOWN动作，失败）
                    execution = CurtailmentExecution(
                        plan_id=plan.id,
                        miner_id=miner.id,
                        execution_action=ExecutionAction.SHUTDOWN,
                        execution_status=ExecutionStatus.FAILED,
                        error_message=error_msg
                    )
                    db.session.add(execution)
            
            # 6. 更新计划的实际削减功率
            plan.calculated_power_reduction_kw = total_power_saved
            
            # 检查全失败场景：所有矿机都关闭失败
            if success_count == 0 and failed_count > 0:
                logger.error(f"❌ 计划 {plan.plan_name} 执行失败：所有矿机关闭失败，回滚到PENDING")
                db.session.rollback()
                
                return {
                    'success': False,
                    'plan_id': plan.id,
                    'plan_name': plan.plan_name,
                    'miners_shutdown': 0,
                    'miners_failed': failed_count,
                    'total_power_saved_kw': 0.0,
                    'plan_status': PlanStatus.PENDING.value,
                    'error': 'All miners failed to shutdown'
                }
            
            # 7. 提交所有更改
            db.session.commit()
            db.session.refresh(plan)
            
            logger.info(
                f"✅ 限电计划执行完成: {plan.plan_name} | "
                f"成功={success_count}, 失败={failed_count}, "
                f"节省功率={total_power_saved:.2f}kW"
            )
            
            # 如果没有scheduled_end_time，立即恢复矿机（测试场景）
            if not plan.scheduled_end_time and success_count > 0:
                logger.info(f"⚡ 计划无结束时间，立即恢复矿机: {plan.plan_name}")
                
                try:
                    # 调用recover_plan立即恢复（这会自动设置COMPLETED状态）
                    recovery_result = CurtailmentPlanService.recover_plan(plan.id)
                    logger.info(f"✅ 计划自动完成: {plan.plan_name} | 恢复={recovery_result.get('miners_recovered', 0)}台")
                except Exception as e:
                    logger.error(f"❌ 自动恢复失败: {e}", exc_info=True)
            
            return {
                'success': success_count > 0,
                'plan_id': plan.id,
                'plan_name': plan.plan_name,
                'miners_shutdown': success_count,
                'miners_failed': failed_count,
                'total_power_saved_kw': round(total_power_saved, 2),
                'plan_status': plan.status.value
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"❌ 执行限电计划失败: {e}", exc_info=True)
            
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def recover_plan(plan_id: int) -> Dict:
        """
        恢复限电计划的所有矿机（开机）
        
        状态流转: EXECUTING/RECOVERY_PENDING → COMPLETED (全部成功)
                 EXECUTING/RECOVERY_PENDING → RECOVERY_PENDING (部分失败，允许重试)
        
        Args:
            plan_id: 计划ID
            
        Returns:
            {
                'success': bool,
                'plan_id': int,
                'plan_name': str,
                'miners_recovered': int,
                'miners_failed': int,
                'plan_status': str,
                'error': str (if failed)
            }
        """
        try:
            # 1. 获取计划并验证状态
            plan = CurtailmentPlan.query.get(plan_id)
            if not plan:
                logger.error(f"❌ 计划不存在: ID={plan_id}")
                return {
                    'success': False,
                    'error': f'Plan not found: {plan_id}'
                }
            
            # 验证状态：只接受EXECUTING或RECOVERY_PENDING
            if plan.status not in [PlanStatus.EXECUTING, PlanStatus.RECOVERY_PENDING]:
                logger.warning(f"⚠️ 计划状态不允许恢复: {plan.plan_name}, status={plan.status.value}")
                return {
                    'success': False,
                    'error': f'Cannot recover plan with status: {plan.status.value}'
                }
            
            logger.info(f"🔄 开始恢复限电计划: {plan.plan_name} (ID={plan.id})")
            
            # 2. 查找所有被该计划限电的矿机（status=maintenance）
            # 通过CurtailmentExecution表关联，找到成功关闭的矿机
            curtailed_miners = HostingMiner.query.join(
                CurtailmentExecution,
                HostingMiner.id == CurtailmentExecution.miner_id
            ).filter(
                CurtailmentExecution.plan_id == plan.id,
                CurtailmentExecution.execution_action == ExecutionAction.SHUTDOWN,
                CurtailmentExecution.execution_status == ExecutionStatus.SUCCESS,
                HostingMiner.status == 'maintenance'
            ).all()
            
            logger.info(f"  找到 {len(curtailed_miners)} 台需要恢复的矿机")
            
            if not curtailed_miners:
                # 没有需要恢复的矿机，直接标记为完成
                plan.status = PlanStatus.COMPLETED
                db.session.commit()
                logger.info(f"✅ 没有需要恢复的矿机，计划已完成: {plan.plan_name}")
                return {
                    'success': True,
                    'plan_id': plan.id,
                    'plan_name': plan.plan_name,
                    'miners_recovered': 0,
                    'miners_failed': 0,
                    'plan_status': PlanStatus.COMPLETED.value,
                    'message': 'No miners to recover'
                }
            
            # 3. 循环恢复矿机并记录执行结果
            success_count = 0
            failed_count = 0
            
            for miner in curtailed_miners:
                try:
                    # 更新矿机状态为active
                    miner.status = 'active'
                    
                    # 创建执行记录（STARTUP动作，成功）
                    execution = CurtailmentExecution(
                        plan_id=plan.id,
                        miner_id=miner.id,
                        execution_action=ExecutionAction.STARTUP,
                        execution_status=ExecutionStatus.SUCCESS
                    )
                    db.session.add(execution)
                    
                    success_count += 1
                    logger.debug(f"  ✅ 矿机已恢复: {miner.serial_number}")
                    
                except Exception as e:
                    failed_count += 1
                    error_msg = str(e)
                    logger.error(f"  ❌ 矿机恢复失败: {miner.serial_number}, 错误={error_msg}")
                    
                    # 创建执行记录（STARTUP动作，失败）
                    execution = CurtailmentExecution(
                        plan_id=plan.id,
                        miner_id=miner.id,
                        execution_action=ExecutionAction.STARTUP,
                        execution_status=ExecutionStatus.FAILED,
                        error_message=error_msg
                    )
                    db.session.add(execution)
            
            # 4. 根据恢复结果更新计划状态
            if failed_count == 0:
                # 全部恢复成功 → COMPLETED
                plan.status = PlanStatus.COMPLETED
                status_msg = "全部矿机恢复成功"
                logger.info(f"✅ {status_msg}: {plan.plan_name}")
            else:
                # 部分失败 → 保持RECOVERY_PENDING，允许重试
                plan.status = PlanStatus.RECOVERY_PENDING
                status_msg = f"部分矿机恢复失败，保持RECOVERY_PENDING状态以便重试"
                logger.warning(f"⚠️ {status_msg}: {plan.plan_name}")
            
            # 5. 提交所有更改
            db.session.commit()
            db.session.refresh(plan)
            
            logger.info(
                f"🔄 限电计划恢复完成: {plan.plan_name} | "
                f"成功={success_count}, 失败={failed_count}, "
                f"最终状态={plan.status.value}"
            )
            
            return {
                'success': success_count > 0,
                'plan_id': plan.id,
                'plan_name': plan.plan_name,
                'miners_recovered': success_count,
                'miners_failed': failed_count,
                'plan_status': plan.status.value,
                'message': status_msg
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"❌ 恢复限电计划失败: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }
