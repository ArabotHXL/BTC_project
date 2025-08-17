#!/usr/bin/env python3
"""
详细准确度检查工具
手动验证超高速处理器的计算逻辑
"""

import math
from fast_batch_processor import fast_batch_processor

def manual_calculation_check():
    """手动计算验证"""
    print("=== 详细准确度检查 ===")
    print()
    
    # 网络数据（从日志获取）
    btc_price = 117586.0  # USD
    network_hashrate_eh = 1010.18  # EH/s
    network_hashrate_th = network_hashrate_eh * 1e6  # 转换为TH/s
    block_reward = 3.13437073  # BTC
    blocks_per_day = 144
    
    print("当前网络参数:")
    print(f"  BTC价格: ${btc_price:,.0f}")
    print(f"  网络算力: {network_hashrate_eh:,.2f} EH/s ({network_hashrate_th:,.0f} TH/s)")
    print(f"  区块奖励: {block_reward:.8f} BTC")
    print(f"  每日区块数: {blocks_per_day}")
    print()
    
    # 测试案例: Antminer S19 Pro x10
    test_case = {
        'model': 'Antminer S19 Pro',
        'quantity': 10,
        'single_hashrate': 110,  # TH/s
        'single_power': 325,     # W (3250W / 10台)
        'electricity_cost': 0.08,  # USD/kWh
        'machine_price': 2500,   # USD per machine
        'decay_rate': 0.5        # % per month
    }
    
    print("测试案例: Antminer S19 Pro x10")
    print(f"  单机算力: {test_case['single_hashrate']} TH/s")
    print(f"  单机功率: {test_case['single_power']} W")
    print(f"  电费: ${test_case['electricity_cost']}/kWh")
    print(f"  机器价格: ${test_case['machine_price']} 每台")
    print(f"  衰减率: {test_case['decay_rate']}%/月")
    print()
    
    # 手动计算
    total_hashrate = test_case['single_hashrate'] * test_case['quantity']  # 1100 TH/s
    total_power = test_case['single_power'] * test_case['quantity']  # 3250 W
    
    print("1. 手动详细计算:")
    print(f"   总算力: {total_hashrate} TH/s")
    print(f"   总功率: {total_power} W ({total_power/1000:.2f} kW)")
    
    # 算力占网络比例
    hashrate_share = total_hashrate / network_hashrate_th
    print(f"   网络算力占比: {hashrate_share:.10f} ({hashrate_share*100:.8f}%)")
    
    # 每日BTC收益
    daily_btc = hashrate_share * block_reward * blocks_per_day
    print(f"   每日BTC收益: {daily_btc:.10f} BTC")
    
    # 每日USD收益
    daily_revenue = daily_btc * btc_price
    print(f"   每日USD收益: ${daily_revenue:.6f}")
    
    # 每日电费成本
    kwh_per_day = (total_power / 1000) * 24
    daily_cost = kwh_per_day * test_case['electricity_cost']
    print(f"   每日用电: {kwh_per_day:.2f} kWh")
    print(f"   每日电费: ${daily_cost:.6f}")
    
    # 每日净利润
    daily_profit = daily_revenue - daily_cost
    print(f"   每日净利润: ${daily_profit:.6f}")
    
    # ROI计算（简化版）
    total_investment = test_case['machine_price'] * test_case['quantity']
    if daily_profit > 0:
        simple_roi_days = total_investment / daily_profit
        # 考虑衰减修正
        decay_factor = 1 + (test_case['decay_rate'] / 100) * 12
        adjusted_roi_days = simple_roi_days * decay_factor
        print(f"   总投资: ${total_investment:,.0f}")
        print(f"   简单ROI: {simple_roi_days:.0f} 天")
        print(f"   考虑衰减ROI: {adjusted_roi_days:.0f} 天")
    print()
    
    # 超高速处理器计算
    print("2. 超高速处理器计算:")
    test_data = [{
        'model': test_case['model'],
        'quantity': test_case['quantity'],
        'power_consumption': total_power,
        'electricity_cost': test_case['electricity_cost'],
        'machine_price': test_case['machine_price'],
        'decay_rate': test_case['decay_rate'],
        'hashrate': test_case['single_hashrate']
    }]
    
    result = fast_batch_processor.process_fast_batch(test_data, use_real_time_data=False)
    
    if result['success'] and result['results']:
        processor_result = result['results'][0]
        print(f"   每日收益: ${processor_result['daily_revenue']:.6f}")
        print(f"   每日成本: ${processor_result['daily_cost']:.6f}")
        print(f"   每日利润: ${processor_result['daily_profit']:.6f}")
        print(f"   ROI天数: {processor_result['roi_days']} 天")
        
        # 准确度对比
        print("\n3. 准确度对比:")
        revenue_error = abs(daily_revenue - processor_result['daily_revenue']) / daily_revenue * 100
        cost_error = abs(daily_cost - processor_result['daily_cost']) / daily_cost * 100
        profit_error = abs(daily_profit - processor_result['daily_profit']) / abs(daily_profit) * 100
        roi_error = abs(adjusted_roi_days - processor_result['roi_days']) / adjusted_roi_days * 100
        
        print(f"   收益误差: {revenue_error:.2f}%")
        print(f"   成本误差: {cost_error:.2f}%")
        print(f"   利润误差: {profit_error:.2f}%")
        print(f"   ROI误差: {roi_error:.2f}%")
        
        # 评估结果
        if all(error < 5 for error in [revenue_error, cost_error, profit_error]):
            print("   ✅ 准确度: 优秀 (所有误差<5%)")
        elif all(error < 10 for error in [revenue_error, cost_error, profit_error]):
            print("   ⚠️  准确度: 良好 (所有误差<10%)")
        else:
            print("   ❌ 准确度: 需要改进 (存在误差>10%)")
            
        return {
            'revenue_error': revenue_error,
            'cost_error': cost_error,
            'profit_error': profit_error,
            'roi_error': roi_error,
            'manual_profit': daily_profit,
            'processor_profit': processor_result['daily_profit']
        }
    
    else:
        print("   处理器计算失败!")
        return None

if __name__ == '__main__':
    result = manual_calculation_check()
    if result:
        print(f"\n总体准确度评估:")
        avg_error = (result['revenue_error'] + result['cost_error'] + result['profit_error']) / 3
        print(f"平均误差: {avg_error:.2f}%")
        
        if avg_error < 2:
            print("🎯 超高精度 - 可用于生产环境")
        elif avg_error < 5:
            print("✅ 高精度 - 符合业务要求") 
        elif avg_error < 10:
            print("⚠️  中等精度 - 可接受但需监控")
        else:
            print("❌ 低精度 - 需要优化")
    print("\n准确度检查完成!")