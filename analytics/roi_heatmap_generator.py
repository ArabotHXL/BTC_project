"""
HashInsight Enterprise - ROI Dynamic Heatmap Generator
ROI动态热力图生成器

功能特性：
- 实时BTC价格联动（CoinGecko WebSocket）
- 全网算力/难度集成
- 盈亏点可视化算法
- 历史数据回放（时光机功能）
- 限电策略模拟引擎（50%/70%/90%限电场景）
- 多矿机对比热力图
"""

import logging
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
import pandas as pd
from sqlalchemy import text
from db import db

logger = logging.getLogger(__name__)


class ROIHeatmapGenerator:
    """ROI热力图生成器"""
    
    # BTC价格范围（美元）
    BTC_PRICE_RANGE = (20000, 120000)
    BTC_PRICE_STEP = 5000
    
    # 全网难度范围（相对变化）
    DIFFICULTY_RANGE = (0.5, 2.0)  # 50% - 200%
    DIFFICULTY_STEP = 0.1
    
    # 限电场景
    CURTAILMENT_SCENARIOS = {
        'none': {'power_ratio': 1.0, 'name': '无限电', 'color': '#28a745'},
        'light': {'power_ratio': 0.9, 'name': '轻度限电(10%)', 'color': '#ffc107'},
        'moderate': {'power_ratio': 0.7, 'name': '中度限电(30%)', 'color': '#fd7e14'},
        'severe': {'power_ratio': 0.5, 'name': '重度限电(50%)', 'color': '#dc3545'}
    }
    
    def __init__(self):
        """初始化热力图生成器"""
        self.current_btc_price = None
        self.current_difficulty = None
        self.current_network_hashrate = None
        self.block_reward = 3.125  # 当前BTC区块奖励
        
        # 加载当前市场数据
        self._load_market_data()
    
    def _load_market_data(self):
        """加载最新市场数据"""
        try:
            query = text("""
                SELECT btc_price, network_difficulty, network_hashrate, block_reward
                FROM market_analytics
                ORDER BY recorded_at DESC
                LIMIT 1
            """)
            result = db.session.execute(query).fetchone()
            
            if result:
                self.current_btc_price = float(result[0])
                self.current_difficulty = float(result[1])
                self.current_network_hashrate = float(result[2])
                self.block_reward = float(result[3])
                logger.info(f"Market data loaded: BTC=${self.current_btc_price}, "
                          f"Difficulty={self.current_difficulty}, "
                          f"Network Hashrate={self.current_network_hashrate}EH/s")
            else:
                # 使用默认值
                self.current_btc_price = 60000
                self.current_difficulty = 70000000000000
                self.current_network_hashrate = 500
                logger.warning("No market data found, using defaults")
                
        except Exception as e:
            logger.error(f"Failed to load market data: {e}")
            # 使用默认值
            self.current_btc_price = 60000
            self.current_difficulty = 70000000000000
            self.current_network_hashrate = 500
    
    def calculate_daily_profit(self, hashrate_th: float, power_w: int, 
                               electricity_cost: float, btc_price: float,
                               difficulty_multiplier: float = 1.0,
                               curtailment_ratio: float = 1.0) -> Dict:
        """
        计算每日收益
        
        Args:
            hashrate_th: 算力 (TH/s)
            power_w: 功耗 (W)
            electricity_cost: 电费 ($/kWh)
            btc_price: BTC价格 ($)
            difficulty_multiplier: 难度倍数（相对当前难度）
            curtailment_ratio: 限电比例（1.0=无限电，0.5=50%限电）
            
        Returns:
            收益字典
        """
        try:
            # 应用限电比例
            effective_hashrate = hashrate_th * curtailment_ratio
            effective_power = power_w * curtailment_ratio
            
            # 计算每日BTC产出
            # 公式: (算力 / 全网算力) * 144个块 * 区块奖励
            adjusted_difficulty = self.current_difficulty * difficulty_multiplier
            network_hashrate_ths = self.current_network_hashrate * 1000000  # EH/s -> TH/s
            
            daily_btc = (effective_hashrate / network_hashrate_ths) * 144 * self.block_reward
            
            # 计算收入
            daily_revenue = daily_btc * btc_price
            
            # 计算电费成本
            daily_power_kwh = (effective_power * 24) / 1000  # W -> kWh
            daily_cost = daily_power_kwh * electricity_cost
            
            # 计算利润
            daily_profit = daily_revenue - daily_cost
            
            # 计算ROI指标
            profit_margin = (daily_profit / daily_revenue * 100) if daily_revenue > 0 else 0
            
            return {
                'daily_btc': daily_btc,
                'daily_revenue': daily_revenue,
                'daily_cost': daily_cost,
                'daily_profit': daily_profit,
                'profit_margin': profit_margin,
                'is_profitable': daily_profit > 0,
                'breakeven_price': daily_cost / daily_btc if daily_btc > 0 else 0,
                'effective_hashrate': effective_hashrate,
                'effective_power': effective_power
            }
            
        except Exception as e:
            logger.error(f"Profit calculation error: {e}")
            return {
                'daily_btc': 0,
                'daily_revenue': 0,
                'daily_cost': 0,
                'daily_profit': 0,
                'profit_margin': 0,
                'is_profitable': False,
                'breakeven_price': 0,
                'effective_hashrate': 0,
                'effective_power': 0
            }
    
    def generate_heatmap_data(self, hashrate_th: float, power_w: int,
                             electricity_cost: float,
                             curtailment_scenario: str = 'none') -> Dict:
        """
        生成热力图数据
        
        Returns:
            热力图数据矩阵
        """
        try:
            # 获取限电配置
            curtailment_config = self.CURTAILMENT_SCENARIOS.get(
                curtailment_scenario, 
                self.CURTAILMENT_SCENARIOS['none']
            )
            curtailment_ratio = curtailment_config['power_ratio']
            
            # 生成BTC价格和难度网格
            btc_prices = np.arange(
                self.BTC_PRICE_RANGE[0],
                self.BTC_PRICE_RANGE[1] + self.BTC_PRICE_STEP,
                self.BTC_PRICE_STEP
            )
            
            difficulty_multipliers = np.arange(
                self.DIFFICULTY_RANGE[0],
                self.DIFFICULTY_RANGE[1] + self.DIFFICULTY_STEP,
                self.DIFFICULTY_STEP
            )
            
            # 计算热力图矩阵
            heatmap_matrix = []
            breakeven_points = []
            
            for diff_mult in difficulty_multipliers:
                row = []
                for btc_price in btc_prices:
                    result = self.calculate_daily_profit(
                        hashrate_th, power_w, electricity_cost,
                        btc_price, diff_mult, curtailment_ratio
                    )
                    
                    row.append({
                        'profit': result['daily_profit'],
                        'margin': result['profit_margin'],
                        'is_profitable': result['is_profitable']
                    })
                    
                    # 记录盈亏平衡点
                    if abs(result['daily_profit']) < 1:  # 接近盈亏平衡
                        breakeven_points.append({
                            'btc_price': btc_price,
                            'difficulty_mult': diff_mult,
                            'exact_breakeven': result['breakeven_price']
                        })
                
                heatmap_matrix.append(row)
            
            # 计算当前状态
            current_result = self.calculate_daily_profit(
                hashrate_th, power_w, electricity_cost,
                self.current_btc_price, 1.0, curtailment_ratio
            )
            
            return {
                'success': True,
                'heatmap': heatmap_matrix,
                'x_axis': [float(x) for x in btc_prices.tolist()],
                'y_axis': [float(y) for y in difficulty_multipliers.tolist()],
                'x_label': 'BTC Price ($)',
                'y_label': 'Network Difficulty (Multiplier)',
                'breakeven_points': breakeven_points,
                'current_state': {
                    'btc_price': float(self.current_btc_price),
                    'difficulty_mult': 1.0,
                    'profit': float(current_result['daily_profit']),
                    'is_profitable': bool(current_result['is_profitable'])
                },
                'curtailment': curtailment_config,
                'stats': {
                    'max_profit': float(max([max([cell['profit'] for cell in row]) for row in heatmap_matrix])),
                    'min_profit': float(min([min([cell['profit'] for cell in row]) for row in heatmap_matrix])),
                    'profitable_scenarios': int(sum([sum([1 for cell in row if cell['is_profitable']]) for row in heatmap_matrix])),
                    'total_scenarios': int(len(btc_prices) * len(difficulty_multipliers))
                }
            }
            
        except Exception as e:
            logger.error(f"Heatmap generation error: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }
    
    def generate_multi_miner_comparison(self, miners: List[Dict],
                                       btc_price: float = None,
                                       difficulty_mult: float = 1.0) -> Dict:
        """
        生成多矿机对比热力图
        
        Args:
            miners: 矿机列表，每个包含 {hashrate, power, electricity_cost, name}
            btc_price: BTC价格（None使用当前价格）
            difficulty_mult: 难度倍数
            
        Returns:
            对比数据
        """
        try:
            if btc_price is None:
                btc_price = self.current_btc_price
            
            comparison_data = []
            
            for miner in miners:
                # 计算各个限电场景下的收益
                scenarios = {}
                for scenario_key, scenario_config in self.CURTAILMENT_SCENARIOS.items():
                    result = self.calculate_daily_profit(
                        miner['hashrate'],
                        miner['power'],
                        miner.get('electricity_cost', 0.08),
                        btc_price,
                        difficulty_mult,
                        scenario_config['power_ratio']
                    )
                    
                    scenarios[scenario_key] = {
                        'profit': result['daily_profit'],
                        'revenue': result['daily_revenue'],
                        'cost': result['daily_cost'],
                        'margin': result['profit_margin'],
                        'is_profitable': result['is_profitable']
                    }
                
                comparison_data.append({
                    'name': miner.get('name', f"Miner {len(comparison_data) + 1}"),
                    'hashrate': miner['hashrate'],
                    'power': miner['power'],
                    'electricity_cost': miner.get('electricity_cost', 0.08),
                    'scenarios': scenarios
                })
            
            return {
                'success': True,
                'miners': comparison_data,
                'btc_price': btc_price,
                'difficulty_mult': difficulty_mult,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Multi-miner comparison error: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def simulate_historical_replay(self, hashrate_th: float, power_w: int,
                                  electricity_cost: float,
                                  start_date: datetime, end_date: datetime,
                                  interval_hours: int = 24) -> Dict:
        """
        历史数据回放（时光机功能）
        
        Args:
            hashrate_th: 算力
            power_w: 功耗
            electricity_cost: 电费
            start_date: 开始日期
            end_date: 结束日期
            interval_hours: 采样间隔（小时）
            
        Returns:
            历史回放数据
        """
        try:
            # 查询历史市场数据
            query = text("""
                SELECT recorded_at, btc_price, network_difficulty, network_hashrate
                FROM market_analytics
                WHERE recorded_at BETWEEN :start_date AND :end_date
                ORDER BY recorded_at ASC
            """)
            
            results = db.session.execute(
                query,
                {'start_date': start_date, 'end_date': end_date}
            ).fetchall()
            
            if not results:
                return {
                    'success': False,
                    'error': 'No historical data available for the specified period'
                }
            
            # 处理历史数据
            replay_data = []
            cumulative_profit = 0
            
            for row in results:
                timestamp, btc_price, difficulty, network_hashrate = row
                
                # 使用历史数据计算收益
                old_difficulty = self.current_difficulty
                old_hashrate = self.current_network_hashrate
                
                self.current_difficulty = float(difficulty)
                self.current_network_hashrate = float(network_hashrate)
                
                result = self.calculate_daily_profit(
                    hashrate_th, power_w, electricity_cost, float(btc_price)
                )
                
                cumulative_profit += result['daily_profit']
                
                replay_data.append({
                    'timestamp': timestamp.isoformat(),
                    'btc_price': float(btc_price),
                    'difficulty': float(difficulty),
                    'daily_profit': result['daily_profit'],
                    'cumulative_profit': cumulative_profit,
                    'is_profitable': result['is_profitable']
                })
                
                # 恢复当前值
                self.current_difficulty = old_difficulty
                self.current_network_hashrate = old_hashrate
            
            return {
                'success': True,
                'data': replay_data,
                'summary': {
                    'total_days': len(replay_data),
                    'total_profit': cumulative_profit,
                    'average_daily_profit': cumulative_profit / len(replay_data) if replay_data else 0,
                    'profitable_days': sum(1 for d in replay_data if d['is_profitable']),
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Historical replay error: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }
