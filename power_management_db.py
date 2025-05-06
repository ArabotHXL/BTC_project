"""
智能电力削减管理系统 - 数据库管理类
提供数据库交互的方法
"""
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Tuple
from sqlalchemy import desc, asc, func, and_, or_
from sqlalchemy.exc import SQLAlchemyError

from power_management_models import (
    db, MinerStatus, MinerOperation, PowerReductionPlan, 
    RotationSchedule, PerformanceSnapshot
)

class PowerManagementDB:
    """电力管理系统数据库管理类"""
    
    @staticmethod
    def init_app(app):
        """初始化数据库与应用"""
        db.init_app(app)
        with app.app_context():
            db.create_all()
    
    # --------- 矿机状态管理 ---------
    
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
        
        if status:
            query = query.filter_by(status=status)
        
        if category:
            query = query.filter_by(category=category)
        
        return query.all()
    
    @staticmethod
    def update_miner_status(miner_data: Dict) -> MinerStatus:
        """
        更新矿机状态或创建新记录
        
        参数:
            miner_data: 矿机数据字典，必须包含miner_id
        
        返回:
            更新后的矿机状态记录
        """
        miner_id = miner_data.get('miner_id')
        if not miner_id:
            raise ValueError("矿机ID不能为空")
        
        # 查找现有记录
        miner = MinerStatus.query.filter_by(miner_id=miner_id).first()
        
        # 如果不存在则创建新记录
        if not miner:
            miner = MinerStatus(miner_id=miner_id)
            db.session.add(miner)
        
        # 更新属性
        for key, value in miner_data.items():
            if hasattr(miner, key) and key != 'id':
                setattr(miner, key, value)
        
        # 更新最后更新时间
        miner.last_updated = datetime.utcnow()
        
        try:
            db.session.commit()
            return miner
        except SQLAlchemyError as e:
            db.session.rollback()
            raise e
    
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
                print(f"更新矿机 {miner_data.get('miner_id')} 失败: {e}")
                continue
        
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
        # 确保状态有效
        if status not in ['running', 'shutdown']:
            return False, f"无效的状态: {status}"
        
        # 查找矿机
        miner = MinerStatus.query.filter_by(miner_id=miner_id).first()
        if not miner:
            return False, f"矿机 {miner_id} 不存在"
        
        # 如果状态已经是目标状态，不需要变更
        if miner.status == status:
            return True, f"矿机 {miner_id} 已经是 {status} 状态"
        
        try:
            # 更新状态
            old_status = miner.status
            miner.status = status
            miner.last_updated = datetime.utcnow()
            
            # 记录操作
            operation_type = 'startup' if status == 'running' else 'shutdown'
            operation = MinerOperation(
                miner_id=miner_id,
                operation_type=operation_type,
                operator=operator,
                reason=reason,
                details=json.dumps({
                    'old_status': old_status,
                    'new_status': status,
                    'category': miner.category,
                    'health_score': miner.health_score
                })
            )
            
            db.session.add(operation)
            db.session.commit()
            
            return True, f"成功将矿机 {miner_id} 状态从 {old_status} 更改为 {status}"
        
        except SQLAlchemyError as e:
            db.session.rollback()
            return False, f"数据库错误: {str(e)}"
    
    @staticmethod
    def get_miners_summary() -> Dict:
        """获取矿机状态摘要"""
        try:
            # 获取总计数
            total_miners = db.session.query(func.count(MinerStatus.id)).scalar() or 0
            
            # 获取按状态分组的计数
            status_counts = dict(
                db.session.query(
                    MinerStatus.status, 
                    func.count(MinerStatus.id)
                ).group_by(MinerStatus.status).all()
            )
            
            # 获取按类别分组的计数
            category_counts = dict(
                db.session.query(
                    MinerStatus.category, 
                    func.count(MinerStatus.id)
                ).group_by(MinerStatus.category).all()
            )
            
            # 获取按类别和状态分组的计数
            category_status_counts = {}
            for category in ['A', 'B', 'C', 'D']:
                category_status_counts[category] = dict(
                    db.session.query(
                        MinerStatus.status, 
                        func.count(MinerStatus.id)
                    ).filter_by(category=category)
                    .group_by(MinerStatus.status).all()
                )
            
            # 计算总算力和功率
            total_stats = db.session.query(
                func.sum(MinerStatus.hashrate).label('total_hashrate'),
                func.sum(MinerStatus.power).label('total_power')
            ).filter_by(status='running').first()
            
            total_hashrate = total_stats.total_hashrate or 0 if total_stats else 0
            total_power = total_stats.total_power or 0 if total_stats else 0
            
            # 计算有效电力削减比例
            shutdown_power = db.session.query(
                func.sum(MinerStatus.power)
            ).filter_by(status='shutdown').scalar() or 0
            
            effective_reduction = 0
            if total_power + shutdown_power > 0:
                effective_reduction = round(100 * shutdown_power / (total_power + shutdown_power), 2)
            
            # 构建结果
            return {
                'timestamp': datetime.utcnow().isoformat(),
                'total_miners': total_miners,
                'status_counts': status_counts,
                'category_counts': category_counts,
                'category_status_counts': category_status_counts,
                'total_hashrate': round(total_hashrate, 2),
                'total_power': round(total_power, 2),
                'effective_power_reduction': effective_reduction
            }
        
        except SQLAlchemyError as e:
            print(f"获取矿机摘要错误: {e}")
            return {
                'timestamp': datetime.utcnow().isoformat(),
                'error': str(e)
            }
    
    # --------- 电力削减计划管理 ---------
    
    @staticmethod
    def create_power_reduction_plan(plan_data: Dict) -> PowerReductionPlan:
        """创建电力削减计划"""
        plan = PowerReductionPlan(**plan_data)
        
        try:
            # 如果设置为活跃，需要将其他计划设为非活跃
            if plan.is_active:
                PowerReductionPlan.query.filter_by(is_active=True).update({'is_active': False})
            
            db.session.add(plan)
            db.session.commit()
            return plan
        except SQLAlchemyError as e:
            db.session.rollback()
            raise e
    
    @staticmethod
    def get_active_reduction_plan() -> Optional[PowerReductionPlan]:
        """获取当前活跃的电力削减计划"""
        return PowerReductionPlan.query.filter_by(is_active=True).first()
    
    @staticmethod
    def get_all_reduction_plans() -> List[PowerReductionPlan]:
        """获取所有电力削减计划"""
        return PowerReductionPlan.query.order_by(desc(PowerReductionPlan.created_at)).all()
    
    @staticmethod
    def activate_reduction_plan(plan_id: int) -> bool:
        """激活指定的电力削减计划"""
        try:
            # 先将所有计划设为非活跃
            PowerReductionPlan.query.filter_by(is_active=True).update({'is_active': False})
            
            # 激活指定计划
            plan = PowerReductionPlan.query.get(plan_id)
            if not plan:
                return False
            
            plan.is_active = True
            db.session.commit()
            return True
        except SQLAlchemyError:
            db.session.rollback()
            return False
    
    # --------- 轮换计划管理 ---------
    
    @staticmethod
    def create_rotation_schedule(schedule_data: Dict) -> RotationSchedule:
        """创建轮换计划"""
        schedule = RotationSchedule(**schedule_data)
        
        try:
            db.session.add(schedule)
            db.session.commit()
            return schedule
        except SQLAlchemyError as e:
            db.session.rollback()
            raise e
    
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
        
        try:
            for key, value in data.items():
                if hasattr(schedule, key):
                    setattr(schedule, key, value)
            
            db.session.commit()
            return True
        except SQLAlchemyError:
            db.session.rollback()
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
        if not schedule or not schedule.is_active:
            return [{'status': 'error', 'message': '轮换计划不存在或未激活'}]
        
        if not schedule.miners_to_shutdown and not schedule.miners_to_start:
            return [{'status': 'error', 'message': '轮换计划中没有指定要关停或启动的矿机'}]
        
        results = []
        
        # 处理需要关停的矿机
        for miner_id in schedule.miners_to_shutdown or []:
            success, message = PowerManagementDB.change_miner_status(
                miner_id=miner_id,
                status='shutdown',
                operator=executor,
                reason=f'执行轮换计划 #{schedule_id}'
            )
            results.append({
                'miner_id': miner_id,
                'operation': 'shutdown',
                'status': 'success' if success else 'error',
                'message': message
            })
        
        # 处理需要启动的矿机
        for miner_id in schedule.miners_to_start or []:
            success, message = PowerManagementDB.change_miner_status(
                miner_id=miner_id,
                status='running',
                operator=executor,
                reason=f'执行轮换计划 #{schedule_id}'
            )
            results.append({
                'miner_id': miner_id,
                'operation': 'startup',
                'status': 'success' if success else 'error',
                'message': message
            })
        
        # 更新轮换计划的执行情况
        schedule.last_rotation_date = datetime.utcnow()
        schedule.next_rotation_date = datetime.utcnow() + timedelta(days=schedule.days_between_rotation)
        db.session.commit()
        
        return results
    
    # --------- 性能快照管理 ---------
    
    @staticmethod
    def create_performance_snapshot() -> PerformanceSnapshot:
        """创建当日性能快照"""
        today = datetime.utcnow().date()
        
        # 检查是否已有今日快照
        existing = PerformanceSnapshot.query.filter_by(snapshot_date=today).first()
        if existing:
            return existing
        
        # 获取矿机摘要
        summary = PowerManagementDB.get_miners_summary()
        
        # 获取分类统计
        category_counts = {c: 0 for c in 'ABCD'}
        for category, count in summary.get('category_counts', {}).items():
            if category in category_counts:
                category_counts[category] = count
        
        # 获取分类关停统计
        shutdown_counts = {c: 0 for c in 'ABCD'}
        for category, status_counts in summary.get('category_status_counts', {}).items():
            if category in shutdown_counts:
                shutdown_counts[category] = status_counts.get('shutdown', 0)
        
        # 创建快照
        snapshot = PerformanceSnapshot(
            snapshot_date=today,
            total_miners=summary.get('total_miners', 0),
            running_miners=summary.get('status_counts', {}).get('running', 0),
            shutdown_miners=summary.get('status_counts', {}).get('shutdown', 0),
            total_hashrate=summary.get('total_hashrate', 0.0),
            total_power=summary.get('total_power', 0.0),
            effective_power_reduction=summary.get('effective_power_reduction', 0.0),
            a_category_count=category_counts.get('A', 0),
            b_category_count=category_counts.get('B', 0),
            c_category_count=category_counts.get('C', 0),
            d_category_count=category_counts.get('D', 0),
            a_shutdown_count=shutdown_counts.get('A', 0),
            b_shutdown_count=shutdown_counts.get('B', 0),
            c_shutdown_count=shutdown_counts.get('C', 0),
            d_shutdown_count=shutdown_counts.get('D', 0)
        )
        
        try:
            db.session.add(snapshot)
            db.session.commit()
            return snapshot
        except SQLAlchemyError as e:
            db.session.rollback()
            raise e
    
    @staticmethod
    def get_performance_history(days: int = 30) -> List[Dict]:
        """获取性能历史数据"""
        start_date = datetime.utcnow().date() - timedelta(days=days)
        
        snapshots = PerformanceSnapshot.query.filter(
            PerformanceSnapshot.snapshot_date >= start_date
        ).order_by(asc(PerformanceSnapshot.snapshot_date)).all()
        
        return [snapshot.to_dict() for snapshot in snapshots]
    
    # --------- 操作记录管理 ---------
    
    @staticmethod
    def get_recent_operations(limit: int = 100) -> List[MinerOperation]:
        """获取最近的操作记录"""
        return MinerOperation.query.order_by(
            desc(MinerOperation.operation_time)
        ).limit(limit).all()
    
    @staticmethod
    def get_miner_operations(miner_id: str) -> List[MinerOperation]:
        """获取特定矿机的操作记录"""
        return MinerOperation.query.filter_by(
            miner_id=miner_id
        ).order_by(desc(MinerOperation.operation_time)).all()