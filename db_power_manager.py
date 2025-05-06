"""
智能电力削减管理系统 - 基于数据库的核心管理类
"""
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy import desc, asc

from power_management_models import (
    MinerStatus, MinerOperation, PowerReductionPlan, 
    RotationSchedule, PerformanceSnapshot
)
from power_management_db import PowerManagementDB

class DBPowerManager:
    """基于数据库的电力管理系统核心类"""
    
    def __init__(self):
        """初始化电力管理系统"""
        self.db = PowerManagementDB
    
    def analyze_miners_health(self) -> Dict:
        """
        分析矿机健康状况
        
        返回:
            包含各类别统计信息的字典
        """
        # 获取所有矿机
        all_miners = self.db.get_all_miners()
        if not all_miners:
            return {}
        
        # 按类别分组
        categories = {'A': [], 'B': [], 'C': [], 'D': []}
        for miner in all_miners:
            if miner.category in categories:
                categories[miner.category].append(miner)
        
        # 计算每个类别的平均健康分和效率
        summary = {}
        for category, miners in categories.items():
            if not miners:
                summary[category] = {
                    'count': 0,
                    'avg_health_score': 0,
                    'avg_efficiency': 0,
                }
                continue
            
            avg_health = sum(m.health_score for m in miners) / len(miners)
            avg_efficiency = sum(m.efficiency for m in miners) / len(miners)
            
            summary[category] = {
                'count': len(miners),
                'avg_health_score': avg_health,
                'avg_efficiency': avg_efficiency,
            }
        
        return summary
    
    def apply_power_reduction(self, percentage: float) -> Dict:
        """
        应用电力削减策略
        
        参数:
            percentage: 电力削减百分比 (0-100)
            
        返回:
            执行结果
        """
        # 创建电力削减计划
        plan_name = f"电力削减计划 {percentage}% - {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"
        plan = self.db.create_power_reduction_plan({
            'name': plan_name,
            'reduction_percentage': percentage,
            'is_active': True,
            'created_by': 'system',
            'description': f'自动创建的{percentage}%电力削减计划',
            'miner_categories': 'DCBA'  # 关停优先级: D -> C -> B -> A
        })
        
        # 获取系统当前状态
        summary = self.db.get_miners_summary()
        total_power = summary.get('total_power', 0)
        
        # 计算需要削减的功率
        target_reduction = total_power * (percentage / 100)
        
        # 按类别和效率选择要关停的矿机
        miners_to_shutdown = []
        current_reduction = 0
        
        # 按优先级顺序依次选择矿机
        for category in plan.miner_categories:
            # 如果已达目标，退出循环
            if current_reduction >= target_reduction:
                break
            
            # 获取指定类别的运行中矿机，按效率升序排序
            miners = MinerStatus.query.filter_by(
                category=category, 
                status='running'
            ).order_by(asc(MinerStatus.efficiency)).all()
            
            for miner in miners:
                miners_to_shutdown.append(miner)
                current_reduction += miner.power
                
                # 如果达到目标，停止添加
                if current_reduction >= target_reduction:
                    break
        
        # 执行关停操作
        results = []
        for miner in miners_to_shutdown:
            success, message = self.db.change_miner_status(
                miner_id=miner.miner_id,
                status='shutdown',
                operator='system',
                reason=f'执行电力削减计划 #{plan.id}'
            )
            results.append({
                'miner_id': miner.miner_id,
                'category': miner.category,
                'status': 'success' if success else 'failed',
                'message': message
            })
        
        # 生成摘要数据
        categories_summary = {}
        for category in 'ABCD':
            categories_summary[category] = sum(
                1 for r in results if r.get('status') == 'success' and r.get('category') == category
            )
        
        # 重新获取更新后的系统状态
        updated_summary = self.db.get_miners_summary()
        
        return {
            'plan_id': plan.id,
            'plan_name': plan.name,
            'target_reduction_percentage': percentage,
            'target_reduction': target_reduction,
            'miners_shutdown': len(miners_to_shutdown),
            'successful_shutdown': sum(1 for r in results if r.get('status') == 'success'),
            'failed_shutdown': sum(1 for r in results if r.get('status') != 'success'),
            'total_power_before': total_power,
            'total_power_after': updated_summary.get('total_power', 0),
            'effective_reduction': updated_summary.get('effective_power_reduction', 0),
            'categories_summary': categories_summary,
            'detailed_results': results
        }
    
    def generate_rotation_plan(self) -> Dict:
        """
        生成矿机轮换计划
        
        返回:
            轮换计划数据
        """
        # 获取关停的C级矿机
        shutdown_c_miners = self.db.get_all_miners(status='shutdown', category='C')
        
        # 获取运行中的C级矿机
        running_c_miners = self.db.get_all_miners(status='running', category='C')
        
        # 如果没有足够的矿机用于轮换，返回空计划
        if not shutdown_c_miners or not running_c_miners:
            return {
                'plan_id': None,
                'message': '没有足够的C级矿机用于轮换',
                'miners_to_shutdown': [],
                'miners_to_start': []
            }
        
        # 确定轮换规模 (使用较小的值以确保平衡)
        rotation_size = min(len(shutdown_c_miners), len(running_c_miners))
        
        # 按健康分数选择健康分最低的运行中矿机进行关停
        miners_to_shutdown = sorted(
            running_c_miners, 
            key=lambda m: m.health_score
        )[:rotation_size]
        
        # 选择要启动的矿机 (已关停的C级矿机)
        miners_to_start = shutdown_c_miners[:rotation_size]
        
        # 创建轮换计划
        plan_name = f"矿机轮换计划 - {datetime.utcnow().strftime('%Y-%m-%d')}"
        
        try:
            schedule = self.db.create_rotation_schedule({
                'name': plan_name,
                'schedule_type': 'auto',
                'days_between_rotation': 14,
                'next_rotation_date': datetime.utcnow() + timedelta(days=14),
                'created_by': 'system',
                'miners_to_shutdown': [m.miner_id for m in miners_to_shutdown],
                'miners_to_start': [m.miner_id for m in miners_to_start]
            })
            
            return {
                'plan_id': schedule.id,
                'plan_name': schedule.name,
                'next_rotation_date': schedule.next_rotation_date.isoformat() if schedule.next_rotation_date else None,
                'days_between_rotation': schedule.days_between_rotation,
                'miners_to_shutdown': [m.miner_id for m in miners_to_shutdown],
                'miners_to_start': [m.miner_id for m in miners_to_start]
            }
        
        except Exception as e:
            return {
                'plan_id': None,
                'error': str(e),
                'message': '创建轮换计划失败'
            }
    
    def execute_rotation_plan(self, plan_id: int) -> Dict:
        """
        执行轮换计划
        
        参数:
            plan_id: 轮换计划ID
            
        返回:
            执行结果
        """
        results = self.db.execute_rotation(plan_id)
        
        return {
            'plan_id': plan_id,
            'execution_time': datetime.utcnow().isoformat(),
            'results': results,
            'success_count': sum(1 for r in results if r.get('status') == 'success'),
            'error_count': sum(1 for r in results if r.get('status') != 'success')
        }
    
    def get_system_status(self) -> Dict:
        """
        获取系统状态概览
        
        返回:
            系统状态数据
        """
        # 获取基本摘要数据
        summary = self.db.get_miners_summary()
        
        # 获取当前激活的电力削减计划
        active_plan = self.db.get_active_reduction_plan()
        if active_plan:
            summary['active_reduction_plan'] = {
                'id': active_plan.id,
                'name': active_plan.name,
                'reduction_percentage': active_plan.reduction_percentage,
                'created_at': active_plan.created_at.isoformat() if active_plan.created_at else None
            }
        
        # 获取当前激活的轮换计划
        active_schedule = self.db.get_active_rotation_schedule()
        if active_schedule:
            summary['active_rotation_schedule'] = {
                'id': active_schedule.id,
                'name': active_schedule.name,
                'next_rotation_date': active_schedule.next_rotation_date.isoformat() if active_schedule.next_rotation_date else None,
                'days_between_rotation': active_schedule.days_between_rotation
            }
        
        # 获取最近的操作记录
        recent_operations = self.db.get_recent_operations(10)
        summary['recent_operations'] = [op.to_dict() for op in recent_operations]
        
        return summary
    
    def initialize_test_data(self, count: int = 1000) -> int:
        """
        初始化测试数据
        将创建模拟矿机数据用于测试
        
        参数:
            count: 矿机数量
            
        返回:
            成功创建的矿机数量
        """
        miners_data = []
        
        for i in range(1, count + 1):
            miner_id = f"miner{i:03d}"
            
            # 基于ID生成一些伪随机但一致的值
            # 这样同一矿机总是有相同的数据，便于测试
            seed = i
            
            # 模拟不同健康状态的矿机
            if seed % 100 < 20:  # 前20%是D级
                health_base = 30
                hashrate_factor = 0.6
                error_factor = 5.0
                category = 'D'
            elif seed % 100 < 50:  # 接下来30%是C级
                health_base = 50
                hashrate_factor = 0.8
                error_factor = 2.0
                category = 'C'
            elif seed % 100 < 80:  # 接下来30%是B级
                health_base = 75
                hashrate_factor = 0.9
                error_factor = 0.5
                category = 'B'
            else:  # 最后20%是A级
                health_base = 90
                hashrate_factor = 1.0
                error_factor = 0.1
                category = 'A'
            
            # 设置基本属性，添加一些小的随机变化
            hashrate = 200 * hashrate_factor * (0.95 + (seed % 10) / 100)
            power = 3500 * (0.98 + (seed % 5) / 100)
            temperature = 65 + (seed % 15)
            fan_speed = 4000 + (seed % 2000)
            uptime = 86400 * (1 + (seed % 30))  # 1-30天
            error_rate = error_factor * (0.8 + (seed % 5) / 10)
            
            # 计算健康分数
            health_score = min(100, health_base + (seed % 20))
            
            # 计算效率 (TH/J)
            efficiency = (hashrate / power) * 1000
            
            miners_data.append({
                'miner_id': miner_id,
                'ip_address': f"192.168.1.{seed % 254 + 1}",
                'model': 'Antminer S21',
                'hashrate': hashrate,
                'power': power,
                'temperature': temperature,
                'fan_speed': fan_speed,
                'error_rate': error_rate,
                'uptime': uptime,
                'health_score': health_score,
                'efficiency': efficiency,
                'category': category,
                'status': 'running'
            })
        
        # 批量更新
        success_count = self.db.bulk_update_miners(miners_data)
        
        # 创建当日性能快照
        self.db.create_performance_snapshot()
        
        return success_count