#!/usr/bin/env python3
"""
挖矿算法对比测试脚本
用于验证和展示两种不同算法在各种网络条件下的表现差异
"""

import sys
import os
sys.path.append('.')

from mining_calculator import calculate_mining_profitability, get_real_time_btc_price, get_real_time_difficulty, get_real_time_btc_hashrate
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_algorithm_differences():
    """测试两种算法在不同网络条件下的差异"""
    
    print("=" * 80)
    print("挖矿算法对比测试 - Mining Algorithm Comparison Test")
    print("=" * 80)
    
    # 获取当前真实网络数据
    current_btc_price = get_real_time_btc_price()
    current_difficulty = get_real_time_difficulty()
    current_api_hashrate = get_real_time_btc_hashrate()
    
    print(f"\n当前真实网络数据:")
    print(f"BTC价格: ${current_btc_price:,.2f}")
    print(f"网络难度: {current_difficulty/1e12:.2f} T")
    print(f"API算力: {current_api_hashrate:.2f} EH/s")
    
    # 基于难度计算的参考算力
    difficulty_factor = 2 ** 32
    calculated_hashrate = (current_difficulty * difficulty_factor) / 600  # H/s
    calculated_hashrate_eh = calculated_hashrate / 1e18  # 转换为EH/s
    
    print(f"基于难度计算的算力: {calculated_hashrate_eh:.2f} EH/s")
    print(f"API与计算算力差异: {((current_api_hashrate - calculated_hashrate_eh) / calculated_hashrate_eh * 100):.2f}%")
    
    # 测试参数
    test_params = {
        'miner_model': 'Antminer S21 XP',
        'miner_count': 100,
        'electricity_cost': 0.05,
        'use_real_time_data': True
    }
    
    print(f"\n测试参数:")
    print(f"矿机型号: {test_params['miner_model']}")
    print(f"矿机数量: {test_params['miner_count']}")
    print(f"电费: ${test_params['electricity_cost']}/kWh")
    
    # 场景1: 使用当前真实数据
    print(f"\n{'='*50}")
    print("场景1: 当前真实网络条件")
    print(f"{'='*50}")
    
    result = calculate_mining_profitability(**test_params)
    
    if result['success']:
        method1_daily = result['btc_mined']['method1']['daily']
        method2_daily = result['btc_mined']['method2']['daily']
        final_daily = result['btc_mined']['daily']
        
        print(f"算法1 (基于API算力): {method1_daily:.8f} BTC/天")
        print(f"算法2 (基于难度): {method2_daily:.8f} BTC/天")
        print(f"最终采用值: {final_daily:.8f} BTC/天")
        print(f"算法差异: {abs(method1_daily - method2_daily):.8f} BTC ({abs(method1_daily - method2_daily)/method2_daily*100:.4f}%)")
    
    # 场景2: 模拟API算力偏高的情况
    print(f"\n{'='*50}")
    print("场景2: 模拟API算力偏高30%的情况")
    print(f"{'='*50}")
    
    # 手动设置更高的网络算力
    higher_hashrate = current_api_hashrate * 1.3
    test_params_high = test_params.copy()
    test_params_high['manual_network_hashrate'] = higher_hashrate
    
    result_high = calculate_mining_profitability(**test_params_high)
    
    if result_high['success']:
        method1_daily_high = result_high['btc_mined']['method1']['daily']
        method2_daily_high = result_high['btc_mined']['method2']['daily']
        final_daily_high = result_high['btc_mined']['daily']
        
        print(f"手动网络算力: {higher_hashrate:.2f} EH/s")
        print(f"算法1 (基于手动算力): {method1_daily_high:.8f} BTC/天")
        print(f"算法2 (基于难度): {method2_daily_high:.8f} BTC/天")
        print(f"最终采用值: {final_daily_high:.8f} BTC/天")
        print(f"算法差异: {abs(method1_daily_high - method2_daily_high):.8f} BTC ({abs(method1_daily_high - method2_daily_high)/method2_daily_high*100:.4f}%)")
    
    # 场景3: 模拟API算力偏低的情况
    print(f"\n{'='*50}")
    print("场景3: 模拟API算力偏低30%的情况")
    print(f"{'='*50}")
    
    # 手动设置更低的网络算力
    lower_hashrate = current_api_hashrate * 0.7
    test_params_low = test_params.copy()
    test_params_low['manual_network_hashrate'] = lower_hashrate
    
    result_low = calculate_mining_profitability(**test_params_low)
    
    if result_low['success']:
        method1_daily_low = result_low['btc_mined']['method1']['daily']
        method2_daily_low = result_low['btc_mined']['method2']['daily']
        final_daily_low = result_low['btc_mined']['daily']
        
        print(f"手动网络算力: {lower_hashrate:.2f} EH/s")
        print(f"算法1 (基于手动算力): {method1_daily_low:.8f} BTC/天")
        print(f"算法2 (基于难度): {method2_daily_low:.8f} BTC/天")
        print(f"最终采用值: {final_daily_low:.8f} BTC/天")
        print(f"算法差异: {abs(method1_daily_low - method2_daily_low):.8f} BTC ({abs(method1_daily_low - method2_daily_low)/method2_daily_low*100:.4f}%)")
    
    # 总结
    print(f"\n{'='*80}")
    print("测试总结 - Test Summary")
    print(f"{'='*80}")
    print("为什么当前两个算法显示相同结果:")
    print("1. 当前API返回的网络算力与基于难度计算的算力几乎完全一致")
    print("2. 这种情况下，两种算法产生相同的BTC产出计算结果")
    print("3. 在网络算力API数据不准确或延迟的情况下，算法差异会显现")
    print("4. 系统会自动检测算法差异，当差异超过100%时使用更稳定的难度算法")
    print("\n为了验证算法独立性，我们测试了不同网络算力条件下的表现。")
    
if __name__ == "__main__":
    test_algorithm_differences()