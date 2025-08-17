"""
超高速批量计算器
专门针对速度优化的版本，牺牲部分精度以获得最快性能
"""

import logging
import time
import concurrent.futures
from multiprocessing import cpu_count
from mining_calculator import MINER_DATA, DEFAULT_BTC_PRICE, DEFAULT_NETWORK_DIFFICULTY, DEFAULT_NETWORK_HASHRATE, BLOCK_REWARD
from mining_calculator import get_real_time_btc_price, get_real_time_difficulty, get_real_time_btc_hashrate, get_real_time_block_reward

logger = logging.getLogger(__name__)

class FastBatchProcessor:
    """超高速批量处理器"""
    
    def __init__(self):
        self.cached_network_data = None
        self.cache_timestamp = 0
        
    def get_network_data_fast(self, use_real_time=True):
        """超快速网络数据获取（10分钟缓存）"""
        import time
        current_time = time.time()
        
        # 10分钟缓存
        if self.cached_network_data and (current_time - self.cache_timestamp) < 600:
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
            
            logger.info(f"快速网络数据已缓存: BTC=${btc_price:,.0f}")
            return self.cached_network_data
            
        except Exception as e:
            logger.error(f"网络数据获取失败: {e}")
            return {
                'btc_price': DEFAULT_BTC_PRICE,
                'difficulty': DEFAULT_NETWORK_DIFFICULTY,
                'hashrate': DEFAULT_NETWORK_HASHRATE,
                'block_reward': BLOCK_REWARD
            }
    
    def calculate_fast_roi(self, hashrate_th, power_w, price_usd, electricity_usd, decay_rate_monthly, network_data):
        """超快速ROI计算 - 简化版本"""
        btc_price = network_data['btc_price']
        network_hashrate_th = network_data['hashrate'] * 1e6
        block_reward = network_data['block_reward']
        
        # 计算日收益（不考虑衰减的简化计算）
        if network_hashrate_th > 0:
            miner_share = hashrate_th / network_hashrate_th
            daily_btc = miner_share * block_reward * 144  # 144 blocks/day
            daily_revenue = daily_btc * btc_price
        else:
            daily_revenue = 0
        
        # 日成本
        kwh_per_day = (power_w / 1000) * 24
        daily_cost = kwh_per_day * electricity_usd
        
        # 日净收益
        daily_profit = daily_revenue - daily_cost
        
        # 简化ROI计算
        if daily_profit > 0:
            # 考虑衰减的修正系数（近似）
            decay_factor = 1 + (decay_rate_monthly / 100) * 12  # 年衰减影响
            roi_days = (price_usd / daily_profit) * decay_factor
            return min(roi_days, 999999)
        else:
            return 999999
    
    def calculate_single_group_fast(self, model, quantity, power_consumption, electricity_cost, machine_price, network_data, decay_rate=0, custom_hashrate=None):
        """超高速单组计算"""
        try:
            # 获取矿机规格
            if custom_hashrate is not None:
                single_hashrate = custom_hashrate
                single_power = power_consumption / quantity if quantity > 0 else power_consumption
            elif model in MINER_DATA:
                single_hashrate = MINER_DATA[model]["hashrate"]
                single_power = MINER_DATA[model]["power_watt"]
            else:
                single_hashrate = 110  # 默认值
                single_power = power_consumption / quantity if quantity > 0 else 3250
            
            # 总算力和功率
            total_hashrate = single_hashrate * quantity
            total_power = single_power * quantity
            
            # 网络数据
            btc_price = network_data['btc_price']
            network_hashrate_th = network_data['hashrate'] * 1e6
            block_reward = network_data['block_reward']
            
            # 计算收益
            if network_hashrate_th > 0:
                miner_share = total_hashrate / network_hashrate_th
                daily_btc = miner_share * block_reward * 144
                daily_revenue = daily_btc * btc_price
            else:
                daily_revenue = 0
            
            # 计算成本
            kwh_per_day = (total_power / 1000) * 24
            daily_cost = kwh_per_day * electricity_cost
            
            # 净收益
            daily_profit = daily_revenue - daily_cost
            
            # 快速ROI计算
            roi_days = self.calculate_fast_roi(
                total_hashrate, total_power, machine_price * quantity,
                electricity_cost, decay_rate, network_data
            )
            
            return {
                'model': model,
                'quantity': quantity,
                'hash_rate': single_hashrate,
                'power_consumption': single_power,
                'electricity_cost': electricity_cost,
                'daily_revenue': round(daily_revenue, 2),
                'daily_cost': round(daily_cost, 2),
                'daily_profit': round(daily_profit, 2),
                'monthly_profit': round(daily_profit * 30, 2),
                'roi_days': round(roi_days) if roi_days < 999999 else 0,
                'decay_rate': decay_rate
            }
            
        except Exception as e:
            logger.error(f"计算失败: {e}")
            return None
    
    def process_fast_batch(self, miners_data, use_real_time_data=True):
        """超高速批量处理"""
        try:
            start_time = time.time()
            logger.info(f"开始超高速批量处理: {len(miners_data)} 个条目")
            
            # 获取网络数据
            network_data = self.get_network_data_fast(use_real_time_data)
            
            # 分组相同配置
            miner_groups = {}
            total_miners = 0
            
            for miner in miners_data:
                key = (
                    miner.get('model', 'Antminer S19 Pro'),
                    float(miner.get('power_consumption', 3250)),
                    float(miner.get('electricity_cost', 0.08)),
                    float(miner.get('machine_price', 2500)),
                    float(miner.get('decay_rate', 0)),
                    float(miner.get('hashrate', 0)) if miner.get('hashrate') else None
                )
                quantity = int(miner.get('quantity', 1))
                miner_number = miner.get('miner_number', 'undefined')
                
                if key not in miner_groups:
                    miner_groups[key] = {'quantity': 0, 'miner_numbers': []}
                miner_groups[key]['quantity'] += quantity
                miner_groups[key]['miner_numbers'].append(miner_number)
                total_miners += quantity
            
            logger.info(f"分组优化: {len(miners_data)} → {len(miner_groups)} 组")
            
            # 并行处理（如果组数较多）
            results = []
            total_daily_profit = 0
            total_daily_revenue = 0
            total_daily_cost = 0
            
            if len(miner_groups) > 10:
                # 并行处理大批量
                with concurrent.futures.ThreadPoolExecutor(max_workers=min(4, cpu_count())) as executor:
                    futures = []
                    for (model, power_consumption, electricity_cost, machine_price, decay_rate, custom_hashrate), group_info in miner_groups.items():
                        future = executor.submit(
                            self.calculate_single_group_fast,
                            model, group_info['quantity'], power_consumption,
                            electricity_cost, machine_price, network_data,
                            decay_rate, custom_hashrate
                        )
                        futures.append((future, group_info['miner_numbers']))
                    
                    for future, miner_numbers in futures:
                        result = future.result()
                        if result:
                            # 添加编号信息
                            if len(miner_numbers) == 1:
                                result['miner_number'] = miner_numbers[0]
                            else:
                                result['miner_number'] = f"{miner_numbers[0]}-{miner_numbers[-1]}"
                            
                            results.append(result)
                            total_daily_profit += result['daily_profit']
                            total_daily_revenue += result['daily_revenue']
                            total_daily_cost += result['daily_cost']
            else:
                # 串行处理小批量
                for (model, power_consumption, electricity_cost, machine_price, decay_rate, custom_hashrate), group_info in miner_groups.items():
                    result = self.calculate_single_group_fast(
                        model, group_info['quantity'], power_consumption,
                        electricity_cost, machine_price, network_data,
                        decay_rate, custom_hashrate
                    )
                    
                    if result:
                        miner_numbers = group_info['miner_numbers']
                        if len(miner_numbers) == 1:
                            result['miner_number'] = miner_numbers[0]
                        else:
                            result['miner_number'] = f"{miner_numbers[0]}-{miner_numbers[-1]}"
                        
                        results.append(result)
                        total_daily_profit += result['daily_profit']
                        total_daily_revenue += result['daily_revenue']
                        total_daily_cost += result['daily_cost']
            
            # 计算摘要
            valid_roi_results = [r for r in results if r.get('roi_days', 0) > 0]
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
            
            processing_time = time.time() - start_time
            logger.info(f"超高速处理完成: {len(results)}组, {total_miners}台矿机, 用时: {processing_time:.2f}秒")
            
            return {
                'success': True,
                'results': results,
                'summary': summary,
                'optimization_info': {
                    'original_entries': len(miners_data),
                    'optimized_groups': len(results),
                    'total_miners': total_miners,
                    'processing_time': round(processing_time, 2),
                    'memory_optimized': True,
                    'parallel_processing': len(miner_groups) > 10,
                    'speed_mode': 'ultra_fast'
                }
            }
            
        except Exception as e:
            logger.error(f"超高速处理失败: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'message': '超高速批量处理失败'
            }

# 全局快速处理器
fast_batch_processor = FastBatchProcessor()