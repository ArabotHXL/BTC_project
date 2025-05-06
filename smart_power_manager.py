"""
智能电力削减管理系统
该系统基于矿机健康状况和效率自动管理电力削减策略
"""
import json
import math
import os
import time
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any

class MinerData:
    """矿机数据模型"""
    def __init__(self, miner_id: str, ip: str, model: str = "Antminer S21"):
        self.miner_id = miner_id
        self.ip = ip
        self.model = model
        self.hashrate = 0.0  # TH/s
        self.power = 0.0  # W
        self.temperature = 0.0  # °C
        self.fan_speed = 0  # RPM
        self.uptime = 0  # seconds
        self.error_rate = 0.0  # %
        self.health_score = 0  # 0-100
        self.efficiency = 0.0  # TH/J
        self.category = 'D'  # A, B, C, D
        self.status = "unknown"  # "running", "shutdown", "unknown"
        self.last_updated = datetime.now()

    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            'miner_id': self.miner_id,
            'ip': self.ip,
            'model': self.model,
            'hashrate': self.hashrate,
            'power': self.power,
            'temperature': self.temperature,
            'fan_speed': self.fan_speed,
            'uptime': self.uptime,
            'error_rate': self.error_rate,
            'health_score': self.health_score,
            'efficiency': self.efficiency,
            'category': self.category,
            'status': self.status,
            'last_updated': self.last_updated.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'MinerData':
        """从字典创建实例"""
        miner = cls(data['miner_id'], data['ip'], data.get('model', 'Antminer S21'))
        miner.hashrate = data.get('hashrate', 0.0)
        miner.power = data.get('power', 0.0)
        miner.temperature = data.get('temperature', 0.0)
        miner.fan_speed = data.get('fan_speed', 0)
        miner.uptime = data.get('uptime', 0)
        miner.error_rate = data.get('error_rate', 0.0)
        miner.health_score = data.get('health_score', 0)
        miner.efficiency = data.get('efficiency', 0.0)
        miner.category = data.get('category', 'D')
        miner.status = data.get('status', 'unknown')
        if 'last_updated' in data:
            try:
                miner.last_updated = datetime.fromisoformat(data['last_updated'])
            except:
                miner.last_updated = datetime.now()
        return miner


class MinerMonitor:
    """矿机监控系统，负责采集矿机数据"""
    
    def __init__(self):
        self.miners_cache_file = "miners_data_cache.json"
    
    def collect_miner_data(self, miner_ip: str, miner_id: str) -> Optional[MinerData]:
        """
        从单个矿机采集运行数据
        实际实现中，这应该通过矿机API获取真实数据
        
        目前为演示，使用模拟数据
        """
        try:
            # 这里应该是实际API调用
            # 为了演示，我们生成一些随机数据
            miner = MinerData(miner_id, miner_ip)
            
            # 基于ID生成一些伪随机但一致的值
            # 这样同一矿机总是有相同的数据，便于演示
            seed = int(miner_id.replace('miner', ''))
            
            # 模拟不同健康状态的矿机
            if seed % 100 < 20:  # 前20个是D级
                health_base = 30
                hashrate_factor = 0.6
                error_factor = 5.0
            elif seed % 100 < 50:  # 接下来30个是C级
                health_base = 50
                hashrate_factor = 0.8
                error_factor = 2.0
            elif seed % 100 < 80:  # 接下来30个是B级
                health_base = 75
                hashrate_factor = 0.9
                error_factor = 0.5
            else:  # 最后20个是A级
                health_base = 90
                hashrate_factor = 1.0
                error_factor = 0.1
            
            # 设置基本属性，添加一些小的随机变化
            miner.hashrate = 200 * hashrate_factor * (0.95 + (seed % 10) / 100)
            miner.power = 3500 * (0.98 + (seed % 5) / 100)
            miner.temperature = 65 + (seed % 15)
            miner.fan_speed = 4000 + (seed % 2000)
            miner.uptime = 86400 * (1 + (seed % 30))  # 1-30天
            miner.error_rate = error_factor * (0.8 + (seed % 5) / 10)
            
            # 标记为运行状态
            miner.status = "running"
            miner.last_updated = datetime.now()
            
            return miner
            
        except Exception as e:
            print(f"Error collecting data from miner {miner_id} at {miner_ip}: {e}")
            return None
    
    def batch_collect_data(self, miners_list: List[Dict]) -> List[MinerData]:
        """批量采集所有矿机数据"""
        results = []
        
        for miner_info in miners_list:
            miner_data = self.collect_miner_data(
                miner_info.get('ip', '192.168.1.' + miner_info['miner_id'].replace('miner', '')), 
                miner_info['miner_id']
            )
            if miner_data:
                results.append(miner_data)
        
        return results
    
    def save_miners_data(self, miners_data: List[MinerData]) -> None:
        """保存矿机数据到缓存文件"""
        data_to_save = [miner.to_dict() for miner in miners_data]
        with open(self.miners_cache_file, 'w') as f:
            json.dump(data_to_save, f, indent=2)
    
    def load_miners_data(self) -> List[MinerData]:
        """从缓存文件加载矿机数据"""
        if not os.path.exists(self.miners_cache_file):
            return []
        
        try:
            with open(self.miners_cache_file, 'r') as f:
                data = json.load(f)
            return [MinerData.from_dict(item) for item in data]
        except Exception as e:
            print(f"Error loading miners data: {e}")
            return []


class MinerHealthAnalyzer:
    """矿机健康分析系统，评估矿机状态并分类"""
    
    def calculate_health_score(self, miner: MinerData) -> int:
        """
        计算矿机健康分数 (0-100)
        考虑因素：
        - 算力与额定值的比例
        - 错误率
        - 温度是否过高
        - 风扇速度是否异常
        """
        # 这里使用简化的算法，实际应用可能更复杂
        
        # 算力表现 (0-40分)
        # 计算实际算力与标称算力的比例
        hashrate_ratio = miner.hashrate / 200  # 假设标称算力是200 TH/s
        hashrate_score = min(40, int(hashrate_ratio * 40))
        
        # 错误率 (0-30分)
        # 错误率越低越好
        error_score = max(0, 30 - int(miner.error_rate * 6))  # 错误率每1%扣6分
        
        # 温度 (0-20分)
        # 温度超过80度开始扣分
        if miner.temperature < 80:
            temp_score = 20
        else:
            temp_score = max(0, 20 - int((miner.temperature - 80) * 2))
        
        # 风扇速度 (0-10分)
        # 假设正常风扇速度在3000-6000 RPM
        if 3000 <= miner.fan_speed <= 6000:
            fan_score = 10
        elif miner.fan_speed > 6000:
            # 风扇速度过高，可能表示散热问题
            fan_score = max(0, 10 - int((miner.fan_speed - 6000) / 200))
        else:
            # 风扇速度过低，可能是风扇故障
            fan_score = max(0, int(miner.fan_speed / 300))
        
        # 综合得分
        total_score = hashrate_score + error_score + temp_score + fan_score
        
        return total_score
    
    def calculate_efficiency(self, miner: MinerData) -> float:
        """
        计算矿机效率 (TH/J)
        效率 = 算力(TH/s) / 功耗(W) * 1000
        """
        if miner.power <= 0:
            return 0.0
        
        # 计算TH/J (每焦耳产生的太哈希算力)
        # 1W = 1J/s，所以算力(TH/s)除以功率(W)就得到TH/J
        efficiency = (miner.hashrate / miner.power) * 1000
        return round(efficiency, 6)
    
    def categorize_miners(self, miners: List[MinerData]) -> Dict[str, List[MinerData]]:
        """
        将矿机分类为A/B/C/D四个等级
        A: 90-100分 - 状态优秀
        B: 70-89分 - 状态良好
        C: 50-69分 - 状态一般
        D: 0-49分 - 状态较差
        """
        categorized = {
            'A': [],
            'B': [],
            'C': [],
            'D': []
        }
        
        for miner in miners:
            # 计算健康分数和效率
            miner.health_score = self.calculate_health_score(miner)
            miner.efficiency = self.calculate_efficiency(miner)
            
            # 分类
            if miner.health_score >= 90:
                miner.category = 'A'
                categorized['A'].append(miner)
            elif miner.health_score >= 70:
                miner.category = 'B'
                categorized['B'].append(miner)
            elif miner.health_score >= 50:
                miner.category = 'C'
                categorized['C'].append(miner)
            else:
                miner.category = 'D'
                categorized['D'].append(miner)
        
        return categorized


class PowerReductionManager:
    """电力削减管理器，决定哪些矿机应该关闭"""
    
    def calculate_shutdown_target(self, total_power: float, reduction_percentage: float) -> float:
        """
        计算需要削减的总功率
        
        参数:
            total_power: 总功率 (W)
            reduction_percentage: 削减百分比 (0-100)
            
        返回:
            需要削减的功率 (W)
        """
        return total_power * (reduction_percentage / 100)
    
    def select_miners_to_shutdown(self, 
                                 categorized_miners: Dict[str, List[MinerData]], 
                                 target_reduction: float) -> List[MinerData]:
        """
        智能选择需要关停的矿机
        
        策略:
        1. 首先关停所有D类矿机
        2. 如果还需要更多削减，按效率从低到高关停C类矿机
        3. 如果仍不够，按效率从低到高关停B类矿机
        4. 如果还不够，按效率从低到高关停A类矿机
        
        参数:
            categorized_miners: 分类后的矿机
            target_reduction: 目标削减功率
            
        返回:
            应关停的矿机列表
        """
        miners_to_shutdown = []
        current_reduction = 0.0
        
        # 定义关停顺序
        categories_order = ['D', 'C', 'B', 'A']
        
        for category in categories_order:
            # 如果已经达到目标，退出循环
            if current_reduction >= target_reduction:
                break
                
            # 按效率排序 (从低到高)
            sorted_miners = sorted(
                categorized_miners[category], 
                key=lambda m: (m.efficiency, m.health_score)
            )
            
            # 从效率最低的开始关停
            for miner in sorted_miners:
                miners_to_shutdown.append(miner)
                current_reduction += miner.power
                
                # 如果达到目标，停止添加
                if current_reduction >= target_reduction:
                    break
        
        return miners_to_shutdown
    
    def generate_rotation_schedule(self, 
                                  all_miners: List[MinerData], 
                                  miners_to_shutdown: List[MinerData],
                                  days_between_rotation: int = 14) -> Dict:
        """
        生成矿机轮换计划
        
        参数:
            all_miners: 所有矿机
            miners_to_shutdown: 当前关停的矿机
            days_between_rotation: 轮换间隔天数
            
        返回:
            轮换计划
        """
        from datetime import timedelta
        
        shutdown_ids = [m.miner_id for m in miners_to_shutdown]
        
        # 创建基础计划
        next_date = datetime.now().date() + timedelta(days=days_between_rotation)
        rotation_schedule = {
            'next_rotation_date': next_date.isoformat(),
            'days_between_rotation': days_between_rotation,
            'current_shutdown_miners': shutdown_ids,
            'next_rotation_plan': {}
        }
        
        # 对于C级和部分B级矿机，创建轮换计划
        running_c_miners = [m for m in all_miners if m.category == 'C' and m.miner_id not in shutdown_ids]
        shutdown_c_miners = [m for m in miners_to_shutdown if m.category == 'C']
        
        # 如果有足够的C级矿机可以轮换
        if running_c_miners and shutdown_c_miners:
            # 按健康分数排序，选择健康分数最低的运行中C级矿机进行轮换
            running_to_shutdown = sorted(running_c_miners, key=lambda m: m.health_score)[:len(shutdown_c_miners)]
            shutdown_to_run = shutdown_c_miners
            
            rotation_schedule['next_rotation_plan'] = {
                'miners_to_shutdown': [m.miner_id for m in running_to_shutdown],
                'miners_to_start': [m.miner_id for m in shutdown_to_run]
            }
        
        return rotation_schedule


class MinerController:
    """矿机控制器，执行实际的开关机操作"""
    
    def __init__(self):
        self.operations_log_file = "power_operations_log.json"
    
    def shutdown_miner(self, miner: MinerData) -> bool:
        """
        关停指定矿机
        在实际实现中，这应该通过API发送关机命令
        
        目前为演示，只修改状态
        """
        try:
            # 实际应发送API命令
            # 假设命令成功
            miner.status = "shutdown"
            print(f"关停矿机: {miner.miner_id} (IP: {miner.ip})")
            return True
        except Exception as e:
            print(f"关停矿机 {miner.miner_id} 失败: {e}")
            return False
    
    def start_miner(self, miner: MinerData) -> bool:
        """
        启动指定矿机
        在实际实现中，这应该通过API发送开机命令
        
        目前为演示，只修改状态
        """
        try:
            # 实际应发送API命令
            # 假设命令成功
            miner.status = "running"
            print(f"启动矿机: {miner.miner_id} (IP: {miner.ip})")
            return True
        except Exception as e:
            print(f"启动矿机 {miner.miner_id} 失败: {e}")
            return False
    
    def execute_power_plan(self, 
                          miners_to_shutdown: List[MinerData], 
                          miners_to_start: List[MinerData]) -> Dict:
        """
        执行电力计划，关停和启动指定的矿机
        
        参数:
            miners_to_shutdown: 要关停的矿机列表
            miners_to_start: 要启动的矿机列表
            
        返回:
            操作结果统计
        """
        results = {
            'total_shutdown': len(miners_to_shutdown),
            'successful_shutdown': 0,
            'total_start': len(miners_to_start),
            'successful_start': 0,
            'timestamp': datetime.now().isoformat(),
            'details': {
                'shutdown': [],
                'start': []
            }
        }
        
        # 执行关机操作
        for miner in miners_to_shutdown:
            success = self.shutdown_miner(miner)
            if success:
                results['successful_shutdown'] += 1
                results['details']['shutdown'].append({
                    'miner_id': miner.miner_id,
                    'ip': miner.ip,
                    'status': 'success'
                })
            else:
                results['details']['shutdown'].append({
                    'miner_id': miner.miner_id,
                    'ip': miner.ip,
                    'status': 'failed'
                })
        
        # 执行开机操作
        for miner in miners_to_start:
            success = self.start_miner(miner)
            if success:
                results['successful_start'] += 1
                results['details']['start'].append({
                    'miner_id': miner.miner_id,
                    'ip': miner.ip,
                    'status': 'success'
                })
            else:
                results['details']['start'].append({
                    'miner_id': miner.miner_id,
                    'ip': miner.ip,
                    'status': 'failed'
                })
        
        # 记录操作日志
        self.log_operation(results)
        
        return results
    
    def log_operation(self, operation_results: Dict) -> None:
        """记录操作日志"""
        if os.path.exists(self.operations_log_file):
            try:
                with open(self.operations_log_file, 'r') as f:
                    logs = json.load(f)
            except:
                logs = []
        else:
            logs = []
        
        logs.append(operation_results)
        
        with open(self.operations_log_file, 'w') as f:
            json.dump(logs, f, indent=2)


class PowerManagementSystem:
    """智能电力管理系统整合类"""
    
    def __init__(self):
        self.miner_monitor = MinerMonitor()
        self.health_analyzer = MinerHealthAnalyzer()
        self.power_manager = PowerReductionManager()
        self.miner_controller = MinerController()
        
        # 系统状态
        self.all_miners = []
        self.categorized_miners = {}
        self.current_shutdown_miners = []
        self.target_reduction_percentage = 20.0
        self.state_file = "power_management_state.json"
        
        # 加载状态
        self.load_state()
    
    def initialize_miners(self, count: int = 1000) -> None:
        """
        初始化矿机列表
        用于演示，在实际系统中应该从实际设备发现或配置文件读取
        """
        miners_list = []
        
        for i in range(1, count + 1):
            miner_id = f"miner{i:03d}"
            miners_list.append({
                'miner_id': miner_id,
                'ip': f"192.168.1.{i % 254 + 1}"
            })
        
        self.all_miners = self.miner_monitor.batch_collect_data(miners_list)
        self.miner_monitor.save_miners_data(self.all_miners)
        print(f"已初始化 {len(self.all_miners)} 台矿机数据")
    
    def analyze_miners_health(self) -> Dict:
        """分析矿机健康状况"""
        self.categorized_miners = self.health_analyzer.categorize_miners(self.all_miners)
        
        # 构建摘要
        summary = {}
        for category in ['A', 'B', 'C', 'D']:
            miners_in_category = self.categorized_miners[category]
            summary[category] = {
                'count': len(miners_in_category),
                'avg_health_score': sum(m.health_score for m in miners_in_category) / max(1, len(miners_in_category)),
                'avg_efficiency': sum(m.efficiency for m in miners_in_category) / max(1, len(miners_in_category)),
            }
        
        return summary
    
    def apply_power_reduction(self, percentage: float = None) -> Dict:
        """
        应用电力削减策略
        
        参数:
            percentage: 削减百分比 (0-100)，如果不提供则使用当前设置
        """
        if percentage is not None:
            self.target_reduction_percentage = max(0, min(100, percentage))
        
        # 计算总功率
        total_power = sum(miner.power for miner in self.all_miners if miner.status == "running")
        
        # 计算目标削减功率
        target_reduction = self.power_manager.calculate_shutdown_target(
            total_power, self.target_reduction_percentage
        )
        
        # 选择要关停的矿机
        miners_to_shutdown = self.power_manager.select_miners_to_shutdown(
            self.categorized_miners, target_reduction
        )
        
        # 执行关停
        results = self.miner_controller.execute_power_plan(
            miners_to_shutdown=miners_to_shutdown,
            miners_to_start=[]
        )
        
        # 更新当前关停矿机列表
        self.current_shutdown_miners = miners_to_shutdown
        
        # 保存状态
        self.save_state()
        
        return {
            'target_reduction_percentage': self.target_reduction_percentage,
            'total_power': total_power,
            'target_reduction': target_reduction,
            'miners_to_shutdown': len(miners_to_shutdown),
            'results': results,
            'categories_summary': {
                'A': sum(1 for m in miners_to_shutdown if m.category == 'A'),
                'B': sum(1 for m in miners_to_shutdown if m.category == 'B'),
                'C': sum(1 for m in miners_to_shutdown if m.category == 'C'),
                'D': sum(1 for m in miners_to_shutdown if m.category == 'D')
            }
        }
    
    def generate_rotation_plan(self) -> Dict:
        """生成矿机轮换计划"""
        rotation_plan = self.power_manager.generate_rotation_schedule(
            self.all_miners, self.current_shutdown_miners
        )
        return rotation_plan
    
    def execute_rotation(self) -> Dict:
        """执行矿机轮换"""
        rotation_plan = self.generate_rotation_plan()
        
        # 获取要关停和启动的矿机ID
        miners_to_shutdown_ids = rotation_plan['next_rotation_plan'].get('miners_to_shutdown', [])
        miners_to_start_ids = rotation_plan['next_rotation_plan'].get('miners_to_start', [])
        
        # 找到对应的矿机对象
        miners_to_shutdown = [m for m in self.all_miners if m.miner_id in miners_to_shutdown_ids]
        miners_to_start = [m for m in self.all_miners if m.miner_id in miners_to_start_ids]
        
        # 执行轮换
        results = self.miner_controller.execute_power_plan(
            miners_to_shutdown=miners_to_shutdown,
            miners_to_start=miners_to_start
        )
        
        # 更新当前关停矿机列表
        for miner in miners_to_start:
            if miner in self.current_shutdown_miners:
                self.current_shutdown_miners.remove(miner)
        
        for miner in miners_to_shutdown:
            self.current_shutdown_miners.append(miner)
        
        # 保存状态
        self.save_state()
        
        return results
    
    def get_system_status(self) -> Dict:
        """获取系统状态概览"""
        # 计算总体统计
        total_miners = len(self.all_miners)
        running_miners = sum(1 for m in self.all_miners if m.status == "running")
        shutdown_miners = sum(1 for m in self.all_miners if m.status == "shutdown")
        
        total_hashrate = sum(m.hashrate for m in self.all_miners if m.status == "running")
        total_power = sum(m.power for m in self.all_miners if m.status == "running")
        
        # 计算分类统计
        categories_count = {
            'A': len(self.categorized_miners.get('A', [])),
            'B': len(self.categorized_miners.get('B', [])),
            'C': len(self.categorized_miners.get('C', [])),
            'D': len(self.categorized_miners.get('D', []))
        }
        
        # 计算每个类别中关停的矿机数量
        shutdown_by_category = {
            'A': sum(1 for m in self.all_miners if m.category == 'A' and m.status == "shutdown"),
            'B': sum(1 for m in self.all_miners if m.category == 'B' and m.status == "shutdown"),
            'C': sum(1 for m in self.all_miners if m.category == 'C' and m.status == "shutdown"),
            'D': sum(1 for m in self.all_miners if m.category == 'D' and m.status == "shutdown")
        }
        
        return {
            'timestamp': datetime.now().isoformat(),
            'total_miners': total_miners,
            'running_miners': running_miners,
            'shutdown_miners': shutdown_miners,
            'total_hashrate': round(total_hashrate, 2),
            'total_power': round(total_power, 2),
            'power_reduction_percentage': self.target_reduction_percentage,
            'categories': categories_count,
            'shutdown_by_category': shutdown_by_category,
            'effective_power_reduction': round(100 * (1 - total_power / (total_power + sum(m.power for m in self.all_miners if m.status == "shutdown"))), 2) if shutdown_miners > 0 else 0
        }
    
    def save_state(self) -> None:
        """保存系统状态"""
        state = {
            'timestamp': datetime.now().isoformat(),
            'target_reduction_percentage': self.target_reduction_percentage,
            'current_shutdown_miners': [m.miner_id for m in self.current_shutdown_miners],
            'miners_status': {m.miner_id: m.status for m in self.all_miners}
        }
        
        with open(self.state_file, 'w') as f:
            json.dump(state, f, indent=2)
    
    def load_state(self) -> None:
        """加载系统状态"""
        if not os.path.exists(self.state_file):
            return
        
        try:
            with open(self.state_file, 'r') as f:
                state = json.load(f)
            
            self.target_reduction_percentage = state.get('target_reduction_percentage', 20.0)
            
            # 加载矿机数据
            self.all_miners = self.miner_monitor.load_miners_data()
            
            # 如果有矿机数据，恢复状态
            if self.all_miners:
                # 恢复矿机状态
                miners_status = state.get('miners_status', {})
                for miner in self.all_miners:
                    if miner.miner_id in miners_status:
                        miner.status = miners_status[miner.miner_id]
                
                # 重新分析健康状态
                self.categorized_miners = self.health_analyzer.categorize_miners(self.all_miners)
                
                # 恢复关停矿机列表
                shutdown_miner_ids = state.get('current_shutdown_miners', [])
                self.current_shutdown_miners = [
                    m for m in self.all_miners if m.miner_id in shutdown_miner_ids
                ]
                
                print(f"已加载系统状态: {len(self.all_miners)} 台矿机, {len(self.current_shutdown_miners)} 台关停")
            
        except Exception as e:
            print(f"加载系统状态失败: {e}")


# 测试运行
if __name__ == "__main__":
    # 创建系统实例
    system = PowerManagementSystem()
    
    # 如果还没有矿机数据，初始化一些
    if not system.all_miners:
        system.initialize_miners(1000)
    
    # 分析矿机健康状况
    health_summary = system.analyze_miners_health()
    print("矿机健康状况摘要:")
    for category, stats in health_summary.items():
        print(f"  {category}级: {stats['count']}台, 平均健康分: {stats['avg_health_score']:.1f}, 平均效率: {stats['avg_efficiency']:.6f}")
    
    # 应用电力削减策略 (20%)
    reduction_results = system.apply_power_reduction(20.0)
    print(f"\n应用电力削减策略 (20%):")
    print(f"  总功率: {reduction_results['total_power']:.2f}W")
    print(f"  目标削减: {reduction_results['target_reduction']:.2f}W")
    print(f"  关停矿机: {reduction_results['miners_to_shutdown']}台")
    print("  按类别统计关停数量:")
    for category, count in reduction_results['categories_summary'].items():
        print(f"    {category}级: {count}台")
    
    # 获取系统状态
    status = system.get_system_status()
    print("\n系统状态:")
    print(f"  总矿机数: {status['total_miners']}台")
    print(f"  运行中: {status['running_miners']}台")
    print(f"  已关停: {status['shutdown_miners']}台")
    print(f"  总算力: {status['total_hashrate']:.2f} TH/s")
    print(f"  总功耗: {status['total_power']:.2f}W")
    print(f"  实际电力削减比例: {status['effective_power_reduction']:.2f}%")
    
    # 生成轮换计划
    rotation_plan = system.generate_rotation_plan()
    print("\n矿机轮换计划:")
    print(f"  下次轮换日期: {rotation_plan['next_rotation_date']}")
    print(f"  轮换间隔: {rotation_plan['days_between_rotation']}天")
    to_shutdown = len(rotation_plan['next_rotation_plan'].get('miners_to_shutdown', []))
    to_start = len(rotation_plan['next_rotation_plan'].get('miners_to_start', []))
    print(f"  计划关停: {to_shutdown}台, 计划启动: {to_start}台")