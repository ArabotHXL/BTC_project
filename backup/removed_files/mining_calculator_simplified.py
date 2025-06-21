"""简化的挖矿计算器模块"""
import logging
from typing import Dict, Any
from utils.api_client import APIClient

# 矿机数据
MINER_DATA = {
    "Antminer S19 Pro": {"hashrate": 110, "power": 3250},
    "Antminer S19j Pro": {"hashrate": 100, "power": 3050},
    "Antminer S19 XP": {"hashrate": 140, "power": 3010},
    "Whatsminer M30S++": {"hashrate": 112, "power": 3472},
    "Whatsminer M50S": {"hashrate": 126, "power": 3276},
    "Antminer T19": {"hashrate": 84, "power": 3150},
    "AvalonMiner 1246": {"hashrate": 90, "power": 3420},
    "Antminer S17 Pro": {"hashrate": 53, "power": 2094},
    "Whatsminer M20S": {"hashrate": 68, "power": 3360},
    "Antminer S9": {"hashrate": 13.5, "power": 1372}
}

class MiningCalculator:
    """挖矿收益计算器"""
    
    def __init__(self):
        self.api_client = APIClient()
    
    def calculate_profitability(self, 
                              miner_model: str,
                              miner_count: int = 1,
                              electricity_cost: float = 0.05,
                              use_real_time_data: bool = True,
                              **kwargs) -> Dict[str, Any]:
        """计算挖矿收益"""
        
        if miner_model not in MINER_DATA:
            raise ValueError(f"未知矿机型号: {miner_model}")
        
        miner_info = MINER_DATA[miner_model]
        
        # 获取网络数据
        if use_real_time_data:
            network_stats = self.api_client.get_all_network_stats()
        else:
            network_stats = {
                'btc_price': kwargs.get('btc_price', 80000),
                'difficulty': kwargs.get('difficulty', 119.12),
                'hashrate': kwargs.get('hashrate', 900),
                'block_reward': kwargs.get('block_reward', 3.125)
            }
        
        # 基础计算
        total_hashrate = miner_info['hashrate'] * miner_count  # TH/s
        total_power = miner_info['power'] * miner_count / 1000  # kW
        
        # 每日挖矿收益计算
        # 公式: (矿机算力 / 全网算力) * 每日产出BTC * BTC价格
        network_hashrate_th = network_stats['hashrate'] * 1e6  # 转换为TH/s
        daily_btc_production = 144 * network_stats['block_reward']  # 每天约144个区块
        
        daily_btc_mined = (total_hashrate / network_hashrate_th) * daily_btc_production
        daily_revenue = daily_btc_mined * network_stats['btc_price']
        
        # 电费成本
        daily_power_cost = total_power * 24 * electricity_cost
        
        # 净收益
        daily_profit = daily_revenue - daily_power_cost
        monthly_profit = daily_profit * 30
        yearly_profit = daily_profit * 365
        
        # 收益率计算
        revenue_per_th = daily_revenue / total_hashrate if total_hashrate > 0 else 0
        
        return {
            'miner_info': {
                'model': miner_model,
                'count': miner_count,
                'total_hashrate': total_hashrate,
                'total_power': total_power
            },
            'network_stats': network_stats,
            'daily': {
                'btc_mined': daily_btc_mined,
                'revenue': daily_revenue,
                'power_cost': daily_power_cost,
                'profit': daily_profit
            },
            'monthly': {
                'revenue': daily_revenue * 30,
                'power_cost': daily_power_cost * 30,
                'profit': monthly_profit
            },
            'yearly': {
                'revenue': daily_revenue * 365,
                'power_cost': daily_power_cost * 365,
                'profit': yearly_profit
            },
            'metrics': {
                'revenue_per_th': revenue_per_th,
                'profit_margin': (daily_profit / daily_revenue * 100) if daily_revenue > 0 else 0,
                'breakeven_btc_price': daily_power_cost / daily_btc_mined if daily_btc_mined > 0 else 0
            }
        }
    
    def calculate_roi(self, 
                     initial_investment: float,
                     monthly_profit: float,
                     forecast_months: int = 36) -> Dict[str, Any]:
        """计算投资回报率"""
        
        if monthly_profit <= 0:
            return {
                'roi_months': float('inf'),
                'roi_percentage': 0,
                'total_return': 0,
                'forecast': []
            }
        
        roi_months = initial_investment / monthly_profit
        total_return = monthly_profit * forecast_months
        roi_percentage = ((total_return - initial_investment) / initial_investment * 100) if initial_investment > 0 else 0
        
        # 生成预测数据
        forecast = []
        cumulative_profit = 0
        for month in range(1, forecast_months + 1):
            cumulative_profit += monthly_profit
            net_profit = cumulative_profit - initial_investment
            
            forecast.append({
                'month': month,
                'cumulative_revenue': cumulative_profit,
                'net_profit': net_profit,
                'roi_percentage': (net_profit / initial_investment * 100) if initial_investment > 0 else 0
            })
        
        return {
            'roi_months': roi_months,
            'roi_percentage': roi_percentage,
            'total_return': total_return,
            'forecast': forecast
        }

# 为了向后兼容，保留原函数接口
def calculate_mining_profitability(**kwargs):
    """向后兼容的函数接口"""
    calculator = MiningCalculator()
    return calculator.calculate_profitability(**kwargs)

def generate_profit_chart_data(miner_model, electricity_costs, btc_prices, miner_count=1):
    """生成收益图表数据"""
    calculator = MiningCalculator()
    chart_data = []
    
    for btc_price in btc_prices:
        for elec_cost in electricity_costs:
            try:
                result = calculator.calculate_profitability(
                    miner_model=miner_model,
                    miner_count=miner_count,
                    electricity_cost=elec_cost,
                    use_real_time_data=False,
                    btc_price=btc_price,
                    difficulty=119.12,
                    hashrate=900,
                    block_reward=3.125
                )
                
                chart_data.append({
                    'btc_price': btc_price,
                    'electricity_cost': elec_cost,
                    'monthly_profit': result['monthly']['profit']
                })
            except Exception as e:
                logging.error(f"生成图表数据时出错: {str(e)}")
    
    return {'profit_data': chart_data}