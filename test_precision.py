#!/usr/bin/env python3
"""测试批量计算的数字精度"""

import sys
import os
sys.path.append('.')

from fast_batch_processor import ultra_fast_batch_calculator

# 测试数据 - 单台矿机精度测试
test_miner = {
    'miner_number': '1',
    'model': 'Antminer S19 Pro',
    'quantity': 1,
    'power_consumption': 3250,
    'machine_price': 2500,
    'electricity_cost': 0.08,
    'decay_rate': 0.5,
    'hashrate': 110
}

# 模拟网络数据
test_network_data = {
    'btc_price': 117656.789123,  # 高精度价格
    'network_difficulty': 129435235580344,
    'network_hashrate': 1010.1788922629444,
    'block_reward': 3.14066851
}

print("=== 数字精度测试 ===")
print(f"输入BTC价格: ${test_network_data['btc_price']:.6f}")
print(f"算力: {test_miner['hashrate']} TH/s")
print(f"功耗: {test_miner['power_consumption']} W")
print(f"电费: ${test_miner['electricity_cost']:.3f}/kWh")

try:
    # 调用计算器
    result = ultra_fast_batch_calculator([test_miner], test_network_data)
    
    if result and 'results' in result and len(result['results']) > 0:
        miner_result = result['results'][0]
        
        print("\n=== 计算结果精度分析 ===")
        print(f"日收益: ${miner_result.get('daily_revenue', 0):.8f}")
        print(f"日成本: ${miner_result.get('daily_cost', 0):.8f}")
        print(f"日利润: ${miner_result.get('daily_profit', 0):.8f}")
        print(f"月利润: ${miner_result.get('monthly_profit', 0):.8f}")
        print(f"ROI天数: {miner_result.get('roi_days', 0):.2f}")
        
        # BTC精度测试
        daily_btc = miner_result.get('daily_btc', 0)
        monthly_btc = miner_result.get('monthly_btc', 0)
        print(f"\n=== BTC精度分析 ===")
        print(f"日BTC: {daily_btc:.12f}")
        print(f"月BTC: {monthly_btc:.12f}")
        
        # 验证精度一致性
        expected_monthly_btc = daily_btc * 30
        btc_precision_error = abs(monthly_btc - expected_monthly_btc)
        print(f"月BTC计算验证: {expected_monthly_btc:.12f}")
        print(f"精度误差: {btc_precision_error:.12f}")
        
        # 美元精度验证
        expected_monthly_profit = miner_result.get('daily_profit', 0) * 30
        monthly_profit_error = abs(miner_result.get('monthly_profit', 0) - expected_monthly_profit)
        print(f"\n=== 美元精度验证 ===")
        print(f"计算的月利润: ${miner_result.get('monthly_profit', 0):.6f}")
        print(f"验证的月利润: ${expected_monthly_profit:.6f}")
        print(f"精度误差: ${monthly_profit_error:.6f}")
        
        print(f"\n=== 精度评级 ===")
        if btc_precision_error < 1e-10:
            print("✓ BTC计算精度: 优秀 (误差 < 1e-10)")
        elif btc_precision_error < 1e-8:
            print("✓ BTC计算精度: 良好 (误差 < 1e-8)")
        else:
            print("⚠ BTC计算精度: 需改进")
            
        if monthly_profit_error < 0.001:
            print("✓ 美元计算精度: 优秀 (误差 < $0.001)")
        elif monthly_profit_error < 0.01:
            print("✓ 美元计算精度: 良好 (误差 < $0.01)")
        else:
            print("⚠ 美元计算精度: 需改进")
            
    else:
        print("❌ 计算失败，无法获取结果")
        
except Exception as e:
    print(f"❌ 测试失败: {e}")
    import traceback
    traceback.print_exc()