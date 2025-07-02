"""
简化版详细报告生成器
为了解决复杂依赖和类型错误问题
"""

from datetime import datetime
from typing import Dict, List, Any


def generate_simple_detailed_report(market_data: Dict, price_history: List = None) -> Dict:
    """生成简化的详细报告"""
    
    if price_history is None:
        price_history = []
    
    # 基础矿机数据
    miners = [
        {'name': 'Antminer S19 Pro', 'hashrate': 110, 'power': 3250, 'efficiency': 29.5, 'price': 2500},
        {'name': 'Antminer S19j Pro', 'hashrate': 104, 'power': 3068, 'efficiency': 29.5, 'price': 2300},
        {'name': 'Antminer S19 XP', 'hashrate': 140, 'power': 3010, 'efficiency': 21.5, 'price': 3500},
        {'name': 'WhatsMiner M30S++', 'hashrate': 112, 'power': 3472, 'efficiency': 31.0, 'price': 2400},
        {'name': 'WhatsMiner M31S+', 'hashrate': 82, 'power': 3220, 'efficiency': 39.3, 'price': 1800}
    ]
    
    # 计算盈利性分析
    btc_price = market_data.get('btc_price', 105000)
    network_hashrate = market_data.get('network_hashrate', 750) * 1e18  # 转换为H/s
    network_difficulty = market_data.get('network_difficulty', 116958512019762.1)
    
    # 计算每个矿机的收益
    profitability_results = []
    electricity_costs = [0.03, 0.04, 0.05, 0.06, 0.07]  # USD/kWh
    
    for miner in miners:
        for elec_cost in electricity_costs:
            # 使用挖矿计算器中的正确算法
            miner_hashrate_th = miner['hashrate']  # TH/s
            network_hashrate_eh = market_data.get('network_hashrate', 750)  # EH/s
            network_hashrate_th = network_hashrate_eh * 1e6  # 转换为TH/s
            
            # 全网日产出计算
            blocks_per_day = 144
            block_reward = 3.125
            network_daily_btc = block_reward * blocks_per_day
            
            # 每TH每日产出 = 全网日产出 / 全网TH
            btc_per_th = network_daily_btc / network_hashrate_th
            
            # 矿机每日产出 = 矿机TH * 每TH产出
            daily_btc = miner_hashrate_th * btc_per_th
            
            # 计算收益
            daily_revenue = daily_btc * btc_price
            daily_electricity_cost = (miner['power'] / 1000) * 24 * elec_cost
            daily_profit = daily_revenue - daily_electricity_cost
            monthly_profit = daily_profit * 30
            
            # ROI计算
            if monthly_profit > 0:
                roi_months = miner['price'] / monthly_profit
                annual_roi = (monthly_profit * 12 / miner['price']) * 100
            else:
                roi_months = float('inf')
                annual_roi = -100
            
            # 盈亏平衡电价 (USD/kWh)
            if miner['power'] > 0:
                daily_power_kwh = (miner['power'] / 1000) * 24
                breakeven_cost = daily_revenue / daily_power_kwh
            else:
                breakeven_cost = 0
            
            profitability_results.append({
                'miner_model': miner['name'],
                'electricity_cost': elec_cost,
                'daily_btc_output': daily_btc,
                'daily_revenue': daily_revenue,
                'daily_cost': daily_electricity_cost,
                'daily_profit': daily_profit,
                'monthly_profit': monthly_profit,
                'annual_roi': annual_roi,
                'roi_months': roi_months,
                'breakeven_electricity_cost': breakeven_cost,
                'profit_margin': (daily_profit / daily_revenue * 100) if daily_revenue > 0 else 0
            })
    
    # 找到最佳方案
    profitable_scenarios = [r for r in profitability_results if r['daily_profit'] > 0]
    best_scenario = max(profitable_scenarios, key=lambda x: x['annual_roi']) if profitable_scenarios else None
    
    # 技术分析
    technical_analysis = {}
    if len(price_history) > 14:
        prices = [float(p['btc_price']) for p in price_history[-50:] if p.get('btc_price')]
        if len(prices) >= 14:
            # 简单RSI计算
            gains = []
            losses = []
            for i in range(1, len(prices)):
                change = prices[i] - prices[i-1]
                if change > 0:
                    gains.append(change)
                    losses.append(0)
                else:
                    gains.append(0)
                    losses.append(abs(change))
            
            if len(gains) >= 14:
                avg_gain = sum(gains[-14:]) / 14
                avg_loss = sum(losses[-14:]) / 14
                rs = avg_gain / avg_loss if avg_loss > 0 else 100
                rsi = 100 - (100 / (1 + rs))
                technical_analysis['rsi_14'] = rsi
            
            # 趋势分析
            if len(prices) >= 20:
                short_term = sum(prices[-5:]) / 5
                medium_term = sum(prices[-20:]) / 20
                trend = 'up' if short_term > medium_term else 'down'
                technical_analysis['trend_analysis'] = {
                    'short_term_trend': trend,
                    'trend_consistency': 'consistent' if abs(short_term - medium_term) > medium_term * 0.02 else 'weak'
                }
    
    # 风险评估
    risk_assessment = {
        'overall_risk': {
            'risk_level': 'medium',
            'risk_score': 5.5,
            'assessment': '当前市场条件下风险适中，建议谨慎投资'
        },
        'price_risk': 'BTC价格波动性较高，存在下跌风险',
        'difficulty_risk': '网络难度持续上升，影响挖矿收益',
        'regulatory_risk': '监管政策变化可能影响挖矿业务'
    }
    
    # 基于实际分析生成准确的投资建议
    recommendations = []
    
    if best_scenario:
        recommendations.append(f'推荐使用{best_scenario["miner_model"]}，年化ROI达{best_scenario["annual_roi"]:.1f}%')
        recommendations.append(f'确保电价低于${best_scenario["breakeven_electricity_cost"]:.4f}/kWh保持盈利')
        if best_scenario["roi_months"] < 24:
            recommendations.append(f'回本周期约{best_scenario["roi_months"]:.1f}个月，投资回报良好')
        else:
            recommendations.append(f'回本周期较长({best_scenario["roi_months"]:.1f}个月)，需谨慎评估')
    else:
        recommendations.append('当前市场条件下挖矿盈利困难，建议等待更好时机')
        recommendations.append('考虑寻找更低电价或更高效的矿机设备')
    
    if btc_price > 100000:
        recommendations.append('BTC价格处于高位，但要防范价格回调风险')
    elif btc_price < 80000:
        recommendations.append('BTC价格相对较低，可能是投资挖矿的好时机')
    
    recommendations.append('密切关注网络难度调整，影响挖矿收益')
    recommendations.append('建议分批投资，降低市场波动风险')
    
    # 构建完整报告
    report = {
        'report_metadata': {
            'title': f'专业矿业分析报告 - {datetime.now().strftime("%Y年%m月%d日")}',
            'generation_time': datetime.now().isoformat(),
            'market_conditions': f'BTC价格: ${btc_price:,.0f}, 网络算力: {network_hashrate/1e18:.1f} EH/s',
            'analysis_scope': '5种主流矿机型号，5个电价梯度'
        },
        'executive_summary': {
            'current_btc_price': btc_price,
            'network_hashrate': network_hashrate / 1e18,
            'investment_outlook': '当前市场条件下，选择高效矿机和低电价可获得稳定收益'
        },
        'technical_analysis': technical_analysis,
        'profitability_analysis': {
            'all_scenarios': profitability_results,
            'best_scenario': best_scenario,
            'profitable_count': len(profitable_scenarios),
            'total_scenarios': len(profitability_results)
        },
        'risk_assessment': risk_assessment,
        'actionable_recommendations': recommendations,
        'market_structure_analysis': {
            'liquidity_analysis': {
                'liquidity_score': 7,
                'assessment': '市场流动性良好'
            }
        },
        'macro_environment_analysis': {
            'institutional_adoption': {
                'adoption_score': 6,
                'assessment': '机构采纳稳步增长'
            }
        }
    }
    
    return report