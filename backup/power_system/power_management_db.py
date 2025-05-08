"""
智能电力削减管理系统 - 数据库管理类
提供数据库交互的方法
"""
from datetime import datetime, date, timedelta
from typing import List, Dict, Tuple, Optional, Union
import random
import logging
from sqlalchemy import func, desc, asc
from sqlalchemy.exc import SQLAlchemyError

from power_management_models import db, MinerStatus, MinerOperation, PowerReductionPlan, RotationSchedule, PerformanceSnapshot

class PowerManagementDB:
    """电力管理系统数据库管理类"""
    
    @staticmethod
    def init_app(app):
        """初始化数据库与应用"""
        # 在主应用中已经初始化了数据库，此处不需要重复初始化
        pass
    
    @staticmethod
    def get_miner(miner_id: str) -> Optional[MinerStatus]:
        """获取单个矿机状态"""
        return MinerStatus.query.filter_by(miner_id=miner_id).first()
    
    @staticmethod
    def get_all_miners(status: str = None, category: str = None) -> List[MinerStatus]:
        """
        获取所有矿机状态
        
        参数:
            status: 可选的状态筛选 (running, shutdown, unknown)
            category: 可选的类别筛选 (A, B, C, D)
        """
        query = MinerStatus.query
        
        if status is not None:
            query = query.filter_by(status=status)
        
        if category is not None:
            query = query.filter_by(category=category)
        
        return query.order_by(MinerStatus.miner_id).all()
    
    @staticmethod
    def update_miner_status(miner_data: Dict) -> MinerStatus:
        """
        更新矿机状态或创建新记录
        
        参数:
            miner_data: 矿机数据字典，必须包含miner_id
        
        返回:
            更新后的矿机状态记录
        """
        if 'miner_id' not in miner_data:
            raise ValueError("矿机数据必须包含miner_id字段")
        
        # 查找现有记录或创建新记录
        miner = MinerStatus.query.filter_by(miner_id=miner_data['miner_id']).first()
        if not miner:
            miner = MinerStatus(miner_id=miner_data['miner_id'])
            db.session.add(miner)
        
        # 更新字段
        for key, value in miner_data.items():
            if hasattr(miner, key) and key != 'id':
                setattr(miner, key, value)
        
        # 确保更新last_updated字段
        miner.last_updated = datetime.utcnow()
        
        try:
            db.session.commit()
            return miner
        except SQLAlchemyError as e:
            db.session.rollback()
            logging.error(f"更新矿机状态失败: {str(e)}")
            raise
    
    @staticmethod
    def bulk_update_miners(miners_data: List[Dict]) -> int:
        """
        批量更新矿机状态
        
        参数:
            miners_data: 矿机数据字典列表
        
        返回:
            成功更新的记录数
        """
        success_count = 0
        for miner_data in miners_data:
            try:
                PowerManagementDB.update_miner_status(miner_data)
                success_count += 1
            except Exception as e:
                logging.error(f"批量更新矿机失败 {miner_data.get('miner_id', 'unknown')}: {str(e)}")
        
        return success_count
    
    @staticmethod
    def change_miner_status(miner_id: str, status: str, operator: str = None, reason: str = None) -> Tuple[bool, str]:
        """
        改变矿机状态并记录操作
        
        参数:
            miner_id: 矿机ID
            status: 新状态 (running, shutdown)
            operator: 操作人
            reason: 操作原因
        
        返回:
            (成功标志, 消息)
        """
        miner = PowerManagementDB.get_miner(miner_id)
        if not miner:
            return False, f"矿机 {miner_id} 不存在"
        
        if miner.status == status:
            return False, f"矿机 {miner_id} 已经是 {status} 状态"
        
        # 确定操作类型
        operation_type = 'shutdown' if status == 'shutdown' else 'startup'
        
        # 创建操作记录
        operation = MinerOperation(
            miner_id=miner_id,
            operation_type=operation_type,
            operator=operator or 'system',
            reason=reason or ('智能电力管理' if operation_type == 'shutdown' else '手动操作')
        )
        
        try:
            # 更新矿机状态
            miner.status = status
            miner.last_updated = datetime.utcnow()
            
            # 保存操作记录
            db.session.add(operation)
            db.session.commit()
            
            return True, f"成功将矿机 {miner_id} 状态更改为 {status}"
        except SQLAlchemyError as e:
            db.session.rollback()
            logging.error(f"改变矿机状态失败: {str(e)}")
            
            # 更新操作记录状态为失败
            operation.status = 'failed'
            operation.details = {'error': str(e)}
            db.session.add(operation)
            db.session.commit()
            
            return False, f"改变矿机状态失败: {str(e)}"
    
    @staticmethod
    def get_miners_summary() -> Dict:
        """获取矿机状态摘要"""
        # 总矿机数
        total_miners = MinerStatus.query.count()
        
        # 各状态数量
        status_counts = db.session.query(
            MinerStatus.status, func.count(MinerStatus.id)
        ).group_by(MinerStatus.status).all()
        
        # 各类别数量
        category_counts = db.session.query(
            MinerStatus.category, func.count(MinerStatus.id)
        ).group_by(MinerStatus.category).all()
        
        # 各类别各状态数量
        category_status_counts = db.session.query(
            MinerStatus.category, MinerStatus.status, func.count(MinerStatus.id)
        ).group_by(MinerStatus.category, MinerStatus.status).all()
        
        # 总算力
        total_hashrate = db.session.query(func.sum(MinerStatus.hashrate))\
            .filter(MinerStatus.status == 'running').scalar() or 0
        
        # 总功耗
        total_power = db.session.query(func.sum(MinerStatus.power))\
            .filter(MinerStatus.status == 'running').scalar() or 0
        
        # 格式化结果
        result = {
            'total_miners': total_miners,
            'status_counts': {status: count for status, count in status_counts},
            'category_counts': {category: count for category, count in category_counts},
            'category_status_counts': {},
            'total_hashrate': total_hashrate,
            'total_power': total_power
        }
        
        # 处理类别状态统计
        for category, status, count in category_status_counts:
            if category not in result['category_status_counts']:
                result['category_status_counts'][category] = {}
            result['category_status_counts'][category][status] = count
        
        # 添加活跃的削减计划
        active_plan = PowerManagementDB.get_active_reduction_plan()
        if active_plan:
            result['active_reduction_plan'] = active_plan.to_dict()
            
            # 计算实际电力削减比例
            target_power = total_power * (1 - active_plan.reduction_percentage / 100)
            if total_power > 0:
                result['effective_power_reduction'] = (1 - total_power / target_power) * 100
            else:
                result['effective_power_reduction'] = 0
        else:
            result['active_reduction_plan'] = None
            result['effective_power_reduction'] = 0
        
        return result
    
    @staticmethod
    def create_power_reduction_plan(plan_data: Dict) -> PowerReductionPlan:
        """创建电力削减计划"""
        plan = PowerReductionPlan(
            name=plan_data.get('name', f'电力削减计划 {datetime.now().strftime("%Y-%m-%d %H:%M")}'),
            reduction_percentage=float(plan_data.get('reduction_percentage', 20.0)),
            miner_categories=plan_data.get('miner_categories', 'DCBA'),
            created_by=plan_data.get('created_by', 'system'),
            is_active=plan_data.get('is_active', False)
        )
        
        # 如果设置为活跃，先停用其他活跃计划
        if plan.is_active:
            PowerManagementDB.deactivate_all_reduction_plans()
        
        db.session.add(plan)
        db.session.commit()
        
        return plan
    
    @staticmethod
    def get_active_reduction_plan() -> Optional[PowerReductionPlan]:
        """获取当前活跃的电力削减计划"""
        return PowerReductionPlan.query.filter_by(is_active=True).first()
    
    @staticmethod
    def get_all_reduction_plans() -> List[PowerReductionPlan]:
        """获取所有电力削减计划"""
        return PowerReductionPlan.query.order_by(
            PowerReductionPlan.is_active.desc(),
            PowerReductionPlan.created_at.desc()
        ).all()
    
    @staticmethod
    def deactivate_all_reduction_plans() -> bool:
        """停用所有电力削减计划"""
        try:
            PowerReductionPlan.query.update({'is_active': False})
            db.session.commit()
            return True
        except SQLAlchemyError as e:
            db.session.rollback()
            logging.error(f"停用削减计划失败: {str(e)}")
            return False
    
    @staticmethod
    def activate_reduction_plan(plan_id: int) -> bool:
        """激活指定的电力削减计划"""
        try:
            # 先停用所有计划
            PowerManagementDB.deactivate_all_reduction_plans()
            
            # 激活指定计划
            plan = PowerReductionPlan.query.get(plan_id)
            if not plan:
                return False
            
            plan.is_active = True
            db.session.commit()
            return True
        except SQLAlchemyError as e:
            db.session.rollback()
            logging.error(f"激活削减计划失败: {str(e)}")
            return False
    
    @staticmethod
    def create_rotation_schedule(schedule_data: Dict) -> RotationSchedule:
        """创建轮换计划"""
        # 计算下次轮换日期
        days_between = int(schedule_data.get('days_between_rotation', 14))
        next_rotation = date.today() + timedelta(days=days_between)
        
        schedule = RotationSchedule(
            name=schedule_data.get('name', f'矿机轮换计划 {datetime.now().strftime("%Y-%m-%d")}'),
            miner_category=schedule_data.get('miner_category', 'C'),
            days_between_rotation=days_between,
            next_rotation_date=next_rotation,
            created_by=schedule_data.get('created_by', 'system'),
            is_active=schedule_data.get('is_active', True),
            miners_to_shutdown=schedule_data.get('miners_to_shutdown'),
            miners_to_start=schedule_data.get('miners_to_start')
        )
        
        # 如果设置为活跃，先停用其他活跃计划
        if schedule.is_active:
            RotationSchedule.query.update({'is_active': False})
        
        db.session.add(schedule)
        db.session.commit()
        
        return schedule
    
    @staticmethod
    def get_active_rotation_schedule() -> Optional[RotationSchedule]:
        """获取活跃的轮换计划"""
        return RotationSchedule.query.filter_by(is_active=True).first()
    
    @staticmethod
    def update_rotation_schedule(schedule_id: int, data: Dict) -> bool:
        """更新轮换计划"""
        schedule = RotationSchedule.query.get(schedule_id)
        if not schedule:
            return False
        
        # 更新字段
        for key, value in data.items():
            if hasattr(schedule, key) and key not in ['id', 'created_at']:
                setattr(schedule, key, value)
        
        try:
            db.session.commit()
            return True
        except SQLAlchemyError as e:
            db.session.rollback()
            logging.error(f"更新轮换计划失败: {str(e)}")
            return False
    
    @staticmethod
    def execute_rotation(schedule_id: int, executor: str = 'system') -> List[Dict]:
        """
        执行轮换计划
        
        参数:
            schedule_id: 轮换计划ID
            executor: 执行人
        
        返回:
            操作结果列表
        """
        schedule = RotationSchedule.query.get(schedule_id)
        if not schedule:
            return [{'success': False, 'message': f'轮换计划 {schedule_id} 不存在'}]
        
        results = []
        success_count = 0
        error_count = 0
        
        # 关停计划中的矿机
        if schedule.miners_to_shutdown:
            for miner_id in schedule.miners_to_shutdown:
                success, message = PowerManagementDB.change_miner_status(
                    miner_id=miner_id,
                    status='shutdown',
                    operator=executor,
                    reason=f'执行轮换计划 {schedule.name}'
                )
                
                results.append({
                    'miner_id': miner_id,
                    'operation': 'shutdown',
                    'success': success,
                    'message': message
                })
                
                if success:
                    success_count += 1
                else:
                    error_count += 1
        
        # 启动计划中的矿机
        if schedule.miners_to_start:
            for miner_id in schedule.miners_to_start:
                success, message = PowerManagementDB.change_miner_status(
                    miner_id=miner_id,
                    status='running',
                    operator=executor,
                    reason=f'执行轮换计划 {schedule.name}'
                )
                
                results.append({
                    'miner_id': miner_id,
                    'operation': 'startup',
                    'success': success,
                    'message': message
                })
                
                if success:
                    success_count += 1
                else:
                    error_count += 1
        
        # 更新轮换计划状态
        schedule.last_executed = datetime.utcnow()
        schedule.execution_count += 1
        schedule.next_rotation_date = date.today() + timedelta(days=schedule.days_between_rotation)
        
        # 清空轮换列表，等待下次生成
        schedule.miners_to_shutdown = []
        schedule.miners_to_start = []
        
        db.session.commit()
        
        # 返回执行结果
        return {
            'results': results,
            'success_count': success_count,
            'error_count': error_count,
            'next_rotation_date': schedule.next_rotation_date.isoformat()
        }
    
    @staticmethod
    def create_performance_snapshot() -> PerformanceSnapshot:
        """创建当日性能快照"""
        today = date.today()
        
        # 检查今天是否已经创建过快照
        existing = PerformanceSnapshot.query.filter_by(snapshot_date=today).first()
        if existing:
            return existing
        
        # 获取系统状态
        status = PowerManagementDB.get_miners_summary()
        
        # 获取各类别统计
        category_stats = {}
        for category in ['A', 'B', 'C', 'D']:
            miners = PowerManagementDB.get_all_miners(category=category)
            if miners:
                running = sum(1 for m in miners if m.status == 'running')
                avg_health = sum(m.health_score for m in miners) / len(miners)
                avg_efficiency = sum(m.efficiency for m in miners) / len(miners)
                category_stats[category] = {
                    'count': len(miners),
                    'running': running,
                    'shutdown': len(miners) - running,
                    'avg_health_score': avg_health,
                    'avg_efficiency': avg_efficiency
                }
        
        # 创建快照
        snapshot = PerformanceSnapshot(
            snapshot_date=today,
            total_miners=status.get('total_miners', 0),
            running_miners=status.get('status_counts', {}).get('running', 0),
            shutdown_miners=status.get('status_counts', {}).get('shutdown', 0),
            total_hashrate=status.get('total_hashrate', 0),
            total_power=status.get('total_power', 0),
            category_stats=category_stats,
            effective_power_reduction=status.get('effective_power_reduction', 0)
        )
        
        db.session.add(snapshot)
        db.session.commit()
        
        return snapshot
    
    @staticmethod
    def get_performance_history(days: int = 30) -> List[Dict]:
        """获取性能历史数据"""
        start_date = date.today() - timedelta(days=days)
        
        snapshots = PerformanceSnapshot.query.filter(
            PerformanceSnapshot.snapshot_date >= start_date
        ).order_by(PerformanceSnapshot.snapshot_date).all()
        
        return [snapshot.to_dict() for snapshot in snapshots]
    
    @staticmethod
    def get_recent_operations(limit: int = 100) -> List[MinerOperation]:
        """获取最近的操作记录"""
        return MinerOperation.query.order_by(
            MinerOperation.operation_time.desc()
        ).limit(limit).all()
    
    @staticmethod
    def get_miner_operations(miner_id: str) -> List[MinerOperation]:
        """获取特定矿机的操作记录"""
        return MinerOperation.query.filter_by(
            miner_id=miner_id
        ).order_by(MinerOperation.operation_time.desc()).all()