"""
优化的批量挖矿计算处理器
专门用于处理大规模矿机数据（5000+）的内存优化计算
"""

import logging
import gc
from mining_calculator import MINER_DATA, DEFAULT_BTC_PRICE, DEFAULT_NETWORK_DIFFICULTY, DEFAULT_NETWORK_HASHRATE, BLOCK_REWARD
from mining_calculator import get_real_time_btc_price, get_real_time_difficulty, get_real_time_btc_hashrate, get_real_time_block_reward

logger = logging.getLogger(__name__)

class OptimizedBatchProcessor:
    """内存优化的批量处理器"""
    
    def __init__(self):
        self.cached_network_data = None
        self.cache_timestamp = 0
        
    def get_network_data(self, use_real_time=True):
        """缓存网络数据以避免重复API调用"""
        import time
        current_time = time.time()
        
        # 缓存5分钟
        if self.cached_network_data and (current_time - self.cache_timestamp) < 300:
            return self.cached_network_data
            
        try:
            if use_real_time:
                btc_price = get_real_time_btc_price()
                difficulty = get_real_time_difficulty()
                hashrate = get_real_time_btc_hashrate()
                block_reward = get_real_time_block_reward()
            else:
                btc_price = DEFAULT_BTC_PRICE
                difficulty = DEFAULT_NETWORK_DIFFICULTY
                hashrate = DEFAULT_NETWORK_HASHRATE
                block_reward = BLOCK_REWARD
                
            self.cached_network_data = {
                'btc_price': btc_price,
                'difficulty': difficulty,
                'hashrate': hashrate,
                'block_reward': block_reward
            }
            self.cache_timestamp = current_time
            
            logger.info(f"网络数据已缓存: BTC=${btc_price:,.0f}, 难度={difficulty/1e12:.2f}T")
            return self.cached_network_data
            
        except Exception as e:
            logger.error(f"获取网络数据失败: {e}")
            return {
                'btc_price': DEFAULT_BTC_PRICE,
                'difficulty': DEFAULT_NETWORK_DIFFICULTY,
                'hashrate': DEFAULT_NETWORK_HASHRATE,
                'block_reward': BLOCK_REWARD
            }
    
    def calculate_single_miner_group(self, model, quantity, power_consumption, electricity_cost, machine_price, network_data):
        """计算单个矿机组的收益（内存优化版本）"""
        try:
            # 获取矿机规格
            if model in MINER_DATA:
                single_hashrate = MINER_DATA[model]["hashrate"]
                single_power = MINER_DATA[model]["power_watt"]
            else:
                # 使用提供的数据
                single_hashrate = 110  # 默认算力
                single_power = power_consumption / quantity if quantity > 0 else power_consumption
            
            # 计算总算力和功耗
            total_hashrate = single_hashrate * quantity  # TH/s
            total_power = single_power * quantity  # Watts
            total_machine_cost = machine_price * quantity  # Total cost
            
            # 网络数据
            btc_price = network_data['btc_price']
            difficulty = network_data['difficulty']
            network_hashrate_eh = network_data['hashrate']  # EH/s
            block_reward = network_data['block_reward']
            
            # 核心计算（简化版，避免复杂的限电逻辑）
            network_hashrate_th = network_hashrate_eh * 1e6  # 转换为TH/s
            blocks_per_day = 144
            
            # 每日收益计算
            if network_hashrate_th > 0:
                miner_share = total_hashrate / network_hashrate_th
                daily_btc = miner_share * block_reward * blocks_per_day
                daily_revenue = daily_btc * btc_price
            else:
                daily_btc = 0
                daily_revenue = 0
            
            # 每日成本
            daily_power_kwh = (total_power * 24) / 1000  # kWh
            daily_cost = daily_power_kwh * electricity_cost
            
            # 净利润
            daily_profit = daily_revenue - daily_cost
            monthly_profit = daily_profit * 30
            
            # ROI计算（真实回本计算）
            if daily_profit > 0 and total_machine_cost > 0:
                roi_days = total_machine_cost / daily_profit  # 总成本 ÷ 日净利润
                # 限制在合理范围内，避免极大值
                roi_days = min(roi_days, 999999)
            else:
                roi_days = 999999  # 无法回本或亏损
            
            return {
                'model': model,
                'quantity': quantity,
                'power_consumption': single_power,
                'electricity_cost': electricity_cost,
                'machine_price': machine_price,
                'total_machine_cost': total_machine_cost,
                'daily_profit': round(daily_profit, 2),
                'daily_revenue': round(daily_revenue, 2),
                'daily_cost': round(daily_cost, 2),
                'monthly_profit': round(monthly_profit, 2),
                'roi_days': round(roi_days, 0),
                'hash_rate': total_hashrate,
                'daily_btc': daily_btc,
                'monthly_btc': daily_btc * 30
            }
            
        except Exception as e:
            logger.error(f"计算矿机组 {model} 时出错: {e}")
            return None
    
    def process_large_batch(self, miners_data, use_real_time_data=True):
        """处理大批量矿机数据（内存优化）"""
        try:
            logger.info(f"开始处理大批量数据: {len(miners_data)} 个条目")
            
            # 获取网络数据（缓存）
            network_data = self.get_network_data(use_real_time_data)
            
            # 分组相同的矿机配置
            miner_groups = {}
            total_miners = 0
            
            for miner in miners_data:
                key = (
                    miner.get('model', 'Antminer S19 Pro'),
                    float(miner.get('power_consumption', 3250)),
                    float(miner.get('electricity_cost', 0.08)),
                    float(miner.get('machine_price', 2500))
                )
                quantity = int(miner.get('quantity', 1))
                
                if key not in miner_groups:
                    miner_groups[key] = 0
                miner_groups[key] += quantity
                total_miners += quantity
            
            logger.info(f"优化: {len(miners_data)} 条目 → {len(miner_groups)} 组, 总矿机: {total_miners}")
            
            # 处理每个组
            results = []
            total_daily_profit = 0
            total_daily_revenue = 0
            total_daily_cost = 0
            
            for (model, power_consumption, electricity_cost, machine_price), quantity in miner_groups.items():
                result = self.calculate_single_miner_group(
                    model, quantity, power_consumption, electricity_cost, machine_price, network_data
                )
                
                if result:
                    results.append(result)
                    total_daily_profit += result['daily_profit']
                    total_daily_revenue += result['daily_revenue']
                    total_daily_cost += result['daily_cost']
                
                # 清理内存
                if len(results) % 100 == 0:
                    gc.collect()
            
            # 创建摘要
            # 计算平均ROI（排除无效值）
            valid_roi_results = [r for r in results if r.get('roi_days', 0) < 999999 and r.get('roi_days', 0) > 0]
            average_roi = round(sum(r.get('roi_days', 0) for r in valid_roi_results) / max(1, len(valid_roi_results)), 1) if valid_roi_results else 999999
            
            summary = {
                'total_miners': total_miners,
                'total_daily_profit': round(total_daily_profit, 2),
                'total_daily_revenue': round(total_daily_revenue, 2),
                'total_daily_cost': round(total_daily_cost, 2),
                'total_monthly_profit': round(total_daily_profit * 30, 2),
                'unique_groups': len(results),
                'average_roi_days': average_roi
            }
            
            logger.info(f"批量处理完成: {len(results)} 组, 总矿机: {total_miners}, 日收益: ${total_daily_profit:,.2f}")
            
            return {
                'success': True,
                'results': results,
                'summary': summary,
                'optimization_info': {
                    'original_entries': len(miners_data),
                    'optimized_groups': len(results),
                    'total_miners': total_miners,
                    'memory_optimized': True,
                    'network_data_cached': True
                }
            }
            
        except Exception as e:
            logger.error(f"批量处理失败: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'message': '批量计算处理失败'
            }
        finally:
            # 强制垃圾回收
            gc.collect()

# 全局处理器实例
batch_processor = OptimizedBatchProcessor()