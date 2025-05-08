"""
智能电力削减管理系统 - 基于数据库的核心管理类
"""
from typing import List, Dict, Tuple, Optional
import random
from datetime import datetime, date, timedelta
import logging
from sqlalchemy import func, desc
import json

from power_management_models import db, MinerStatus, MinerOperation, PowerReductionPlan, RotationSchedule
from power_management_db import PowerManagementDB

class DBPowerManager:
    """基于数据库的电力管理系统核心类"""
    
    def __init__(self):
        """初始化电力管理系统"""
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        self.logger.info("电力管理系统初始化完成")
    
    def analyze_miners_health(self) -> Dict:
        """
        分析矿机健康状况
        
        返回:
            包含各类别统计信息的字典
        """
        result = {}
        categories = ['A', 'B', 'C', 'D']
        
        for category in categories:
            miners = PowerManagementDB.get_all_miners(category=category)
            
            if not miners:
                result[category] = {
                    'count': 0,
                    'running': 0,
                    'shutdown': 0,
                    'avg_health_score': 0,
                    'avg_efficiency': 0
                }
                continue
            
            running = sum(1 for m in miners if m.status == 'running')
            health_scores = [m.health_score for m in miners]
            efficiencies = [m.efficiency for m in miners]
            
            result[category] = {
                'count': len(miners),
                'running': running,
                'shutdown': len(miners) - running,
                'avg_health_score': sum(health_scores) / len(miners) if miners else 0,
                'avg_efficiency': sum(efficiencies) / len(miners) if miners else 0
            }
        
        return result
    
    def apply_power_reduction(self, percentage: float) -> Dict:
        """
        应用电力削减策略
        
        参数:
            percentage: 电力削减百分比 (0-100)
            
        返回:
            执行结果
        """
        if percentage < 0 or percentage > 100:
            return {
                'success': False,
                'message': f'电力削减百分比无效: {percentage}%，应为0-100之间的值'
            }
        
        # 获取系统状态
        status = PowerManagementDB.get_miners_summary()
        total_power = status.get('total_power', 0)
        
        if total_power == 0:
            return {
                'success': False,
                'message': '无法应用电力削减策略，当前总功耗为0'
            }
        
        # 获取活跃的减电计划，如果没有则创建
        active_plan = PowerManagementDB.get_active_reduction_plan()
        
        if active_plan:
            # 更新现有计划
            PowerManagementDB.deactivate_all_reduction_plans()
            plan = PowerReductionPlan(
                name=f'电力削减计划 {percentage}% ({datetime.now().strftime("%Y-%m-%d %H:%M")})',
                reduction_percentage=percentage,
                is_active=True
            )
            db.session.add(plan)
            db.session.commit()
        else:
            # 创建新计划
            plan = PowerReductionPlan(
                name=f'电力削减计划 {percentage}% ({datetime.now().strftime("%Y-%m-%d %H:%M")})',
                reduction_percentage=percentage,
                is_active=True
            )
            db.session.add(plan)
            db.session.commit()
        
        # 计算目标功耗和需要关停的功耗值
        target_power = total_power * (1 - percentage / 100)
        power_to_reduce = total_power - target_power
        
        self.logger.info(f"应用电力削减策略: 当前功耗 {total_power}W, 目标功耗 {target_power}W, 需要削减 {power_to_reduce}W")
        
        # 获取所有运行中的矿机，按健康分数和效率排序
        running_miners = PowerManagementDB.get_all_miners(status='running')
        
        # 首先按类别排序 (D > C > B > A)
        category_order = {'D': 0, 'C': 1, 'B': 2, 'A': 3}
        running_miners.sort(key=lambda m: (category_order[m.category], m.efficiency))
        
        # 关停矿机直到达到目标
        power_reduced = 0
        miners_shutdown = 0
        
        for miner in running_miners:
            if power_reduced >= power_to_reduce:
                break
                
            # 关停此矿机
            success, message = PowerManagementDB.change_miner_status(
                miner_id=miner.miner_id,
                status='shutdown',
                operator='system',
                reason=f'电力削减策略 {percentage}%'
            )
            
            if success:
                power_reduced += miner.power
                miners_shutdown += 1
                self.logger.info(f"关停矿机 {miner.miner_id}, 类别 {miner.category}, 功耗 {miner.power}W, 效率 {miner.efficiency}")
        
        # 计算实际削减比例
        effective_reduction = (power_reduced / total_power * 100) if total_power > 0 else 0
        
        self.logger.info(f"电力削减完成: 关停 {miners_shutdown} 台矿机, 削减功耗 {power_reduced}W ({effective_reduction:.2f}%)")
        
        return {
            'success': True,
            'message': f'成功应用电力削减策略 {percentage}%',
            'target_percentage': percentage,
            'effective_reduction': effective_reduction,
            'power_reduced': power_reduced,
            'successful_shutdown': miners_shutdown
        }
    
    def generate_rotation_plan(self) -> Dict:
        """
        生成矿机轮换计划
        
        返回:
            轮换计划数据
        """
        # 选择合适的类别进行轮换，优先选择C级矿机
        category_candidates = ['C', 'B', 'D', 'A']
        selected_category = None
        
        for category in category_candidates:
            # 检查此类别是否有足够矿机进行轮换
            running_count = MinerStatus.query.filter_by(
                category=category, status='running'
            ).count()
            
            shutdown_count = MinerStatus.query.filter_by(
                category=category, status='shutdown'
            ).count()
            
            if running_count > 0 and shutdown_count > 0:
                selected_category = category
                break
        
        if not selected_category:
            return {
                'success': False,
                'message': '无法生成轮换计划，没有合适的矿机配置'
            }
        
        # 确定轮换数量，最多为类别中运行矿机和关停矿机数量的最小值，且不超过10%
        running_miners = list(MinerStatus.query.filter_by(
            category=selected_category, status='running'
        ).order_by(MinerStatus.health_score.asc()).all())
        
        shutdown_miners = list(MinerStatus.query.filter_by(
            category=selected_category, status='shutdown'
        ).order_by(MinerStatus.health_score.desc()).all())
        
        # 确定轮换数量，最多10%，至少1台
        rotation_count = min(
            max(1, int(len(running_miners) * 0.1)),
            len(running_miners),
            len(shutdown_miners)
        )
        
        # 选择健康分数最低的运行中矿机关停
        miners_to_shutdown = [m.miner_id for m in running_miners[:rotation_count]]
        
        # 选择健康分数最高的关停矿机启动
        miners_to_start = [m.miner_id for m in shutdown_miners[:rotation_count]]
        
        # 创建轮换计划
        plan_data = {
            'name': f'{selected_category}级矿机轮换计划 ({datetime.now().strftime("%Y-%m-%d")})',
            'miner_category': selected_category,
            'days_between_rotation': 14,
            'is_active': True,
            'miners_to_shutdown': miners_to_shutdown,
            'miners_to_start': miners_to_start
        }
        
        schedule = PowerManagementDB.create_rotation_schedule(plan_data)
        
        return {
            'success': True,
            'message': f'成功生成{selected_category}级矿机轮换计划',
            'plan_id': schedule.id,
            'category': selected_category,
            'miners_count': rotation_count,
            'days_between_rotation': 14,
            'next_rotation_date': schedule.next_rotation_date.isoformat(),
            'miners_to_shutdown': miners_to_shutdown,
            'miners_to_start': miners_to_start
        }
    
    def execute_rotation_plan(self, plan_id: int) -> Dict:
        """
        执行轮换计划
        
        参数:
            plan_id: 轮换计划ID
            
        返回:
            执行结果
        """
        try:
            results = PowerManagementDB.execute_rotation(plan_id, executor='system')
            return {
                'success': True,
                'message': '成功执行轮换计划',
                'results': results
            }
        except Exception as e:
            self.logger.error(f"执行轮换计划失败: {str(e)}")
            return {
                'success': False,
                'message': f'执行轮换计划失败: {str(e)}'
            }
    
    def get_system_status(self) -> Dict:
        """
        获取系统状态概览
        
        返回:
            系统状态数据
        """
        return PowerManagementDB.get_miners_summary()
    
    def initialize_test_data(self, count: int = 1000) -> int:
        """
        初始化测试数据
        将创建模拟矿机数据用于测试
        
        参数:
            count: 矿机数量
            
        返回:
            成功创建的矿机数量
        """
        # 清空现有数据
        try:
            MinerOperation.query.delete()
            MinerStatus.query.delete()
            PowerReductionPlan.query.delete()
            RotationSchedule.query.delete()
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"清空数据失败: {str(e)}")
        
        # 创建模拟矿机数据
        miners_data = []
        
        # 矿机类别分布: A=20%, B=30%, C=30%, D=20%
        category_weights = {
            'A': 0.2,
            'B': 0.3,
            'C': 0.3,
            'D': 0.2
        }
        
        category_counts = {
            category: int(count * weight) for category, weight in category_weights.items()
        }
        
        # 确保总数等于count
        category_counts['A'] += count - sum(category_counts.values())
        
        # 按类别生成矿机
        for category, category_count in category_counts.items():
            for i in range(category_count):
                # 生成基本属性
                miner_id = f"{category}-{i+1:04d}"
                
                # 生成健康分数 (按类别不同)
                if category == 'A':
                    health_score = random.uniform(85, 100)
                elif category == 'B':
                    health_score = random.uniform(70, 85)
                elif category == 'C':
                    health_score = random.uniform(50, 70)
                else:  # D
                    health_score = random.uniform(20, 50)
                
                # 计算效率 (越高越好)
                base_efficiency = random.uniform(0.030, 0.040)
                
                # 类别越好，效率越高，健康分数越高，效率越高
                category_factor = {'A': 1.0, 'B': 0.9, 'C': 0.8, 'D': 0.7}[category]
                health_factor = health_score / 100
                
                efficiency = base_efficiency * category_factor * health_factor
                
                # 默认80%矿机运行，20%关停
                status = 'running' if random.random() < 0.8 else 'shutdown'
                
                # 生成算力 (90-130 TH/s)
                hashrate = random.uniform(90, 130)
                
                # 生成功耗 (3000-3500 W)
                power = random.uniform(3000, 3500)
                
                # 生成温度 (40-70°C, 健康越好温度越低)
                temp_max = 70 - (health_score / 100 * 30)
                temperature = random.uniform(40, temp_max)
                
                # 生成风扇转速 (3000-7000 RPM, 温度越高转速越高)
                fan_base = 3000
                fan_temp_factor = (temperature - 40) / 30  # 温度影响因子
                fan_speed = int(fan_base + fan_temp_factor * 4000)
                
                # 生成错误率 (0-10%, 健康越好错误率越低)
                error_rate = (100 - health_score) / 10
                
                miner_data = {
                    'miner_id': miner_id,
                    'ip_address': f"192.168.1.{random.randint(2, 254)}",
                    'model': f"Miner-{random.choice(['S19', 'S21', 'M30', 'M50'])}",
                    'status': status,
                    'category': category,
                    'hashrate': hashrate,
                    'power': power,
                    'temperature': temperature,
                    'fan_speed': fan_speed,
                    'error_rate': error_rate,
                    'health_score': health_score,
                    'efficiency': efficiency,
                    'created_at': datetime.utcnow(),
                    'last_updated': datetime.utcnow()
                }
                
                miners_data.append(miner_data)
        
        # 批量创建矿机数据
        success_count = PowerManagementDB.bulk_update_miners(miners_data)
        self.logger.info(f"成功创建 {success_count} 台矿机测试数据")
        
        # 创建默认的电力削减计划
        try:
            plan = PowerReductionPlan(
                name="默认电力削减计划 (20%)",
                reduction_percentage=20.0,
                miner_categories="DCBA", # 关停优先级
                is_active=True
            )
            db.session.add(plan)
            db.session.commit()
            self.logger.info("成功创建默认电力削减计划")
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"创建默认电力削减计划失败: {str(e)}")
        
        # 创建一个性能快照
        try:
            PowerManagementDB.create_performance_snapshot()
            self.logger.info("成功创建初始性能快照")
        except Exception as e:
            self.logger.error(f"创建初始性能快照失败: {str(e)}")
        
        return success_count