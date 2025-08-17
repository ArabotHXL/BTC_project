#!/usr/bin/env python3
"""
批量计算器准确度测试工具
对比超高速处理器和标准处理器的计算结果
"""

import time
import json
from mining_calculator import calculate_mining_profitability, MINER_DATA
from fast_batch_processor import fast_batch_processor
from optimized_batch_processor import batch_processor

def test_calculation_accuracy():
    """测试计算准确度"""
    print("=== 批量计算器准确度测试 ===")
    print()
    
    # 测试数据
    test_cases = [
        {
            'model': 'Antminer S19 Pro',
            'quantity': 10,
            'power_consumption': 3250,
            'machine_price': 2500,
            'electricity_cost': 0.08,
            'decay_rate': 0.5,
            'hashrate': 110
        },
        {
            'model': 'WhatsMiner M53S', 
            'quantity': 5,
            'power_consumption': 6554,
            'machine_price': 4500,
            'electricity_cost': 0.07,
            'decay_rate': 0.3,
            'hashrate': 226
        },
        {
            'model': 'Antminer S21',
            'quantity': 8,
            'power_consumption': 3550,
            'machine_price': 3200,
            'electricity_cost': 0.08,
            'decay_rate': 0.4,
            'hashrate': 200
        }
    ]
    
    print("测试案例:")
    for i, case in enumerate(test_cases, 1):
        print(f"  {i}. {case['model']} x{case['quantity']} - 算力:{case['hashrate']}TH/s")
    print()
    
    # 测试超高速处理器
    print("1. 超高速处理器结果:")
    fast_start = time.time()
    fast_result = fast_batch_processor.process_fast_batch(test_cases)
    fast_time = time.time() - fast_start
    
    if fast_result['success']:
        print(f"   处理时间: {fast_time:.3f}秒")
        print(f"   总矿机数: {fast_result['summary']['total_miners']}")
        print(f"   日总收益: ${fast_result['summary']['total_daily_profit']:.2f}")
        print(f"   日总成本: ${fast_result['summary']['total_daily_cost']:.2f}")
        print("   详细结果:")
        for r in fast_result['results']:
            roi_display = f"{r['roi_days']}天" if r['roi_days'] > 0 else "无回本"
            print(f"     {r['model']} x{r['quantity']}: 日收益${r['daily_profit']:.2f}, ROI:{roi_display}")
    else:
        print(f"   失败: {fast_result.get('error', 'Unknown error')}")
    print()
    
    # 测试标准处理器
    print("2. 标准处理器结果:")
    standard_start = time.time()
    
    # 使用标准calculate_mining_profitability函数进行对比
    standard_results = []
    total_standard_profit = 0
    total_standard_cost = 0
    
    for case in test_cases:
        try:
            # 计算单台矿机再乘以数量
            single_result = calculate_mining_profitability(
                hashrate=case['hashrate'],
                power_consumption=case['power_consumption'] / case['quantity'],
                electricity_cost=case['electricity_cost'],
                _batch_mode=True
            )
            
            if single_result and single_result.get('success'):
                daily_profit = single_result['daily_profit'] * case['quantity']
                daily_cost = single_result['daily_cost'] * case['quantity']
                daily_revenue = single_result['daily_revenue'] * case['quantity']
                
                standard_results.append({
                    'model': case['model'],
                    'quantity': case['quantity'],
                    'daily_profit': daily_profit,
                    'daily_cost': daily_cost,
                    'daily_revenue': daily_revenue,
                    'roi_days': single_result.get('roi_days', 0)
                })
                
                total_standard_profit += daily_profit
                total_standard_cost += daily_cost
                
        except Exception as e:
            print(f"   标准处理器计算失败: {case['model']} - {e}")
    
    standard_time = time.time() - standard_start
    
    print(f"   处理时间: {standard_time:.3f}秒")
    print(f"   总矿机数: {sum(c['quantity'] for c in test_cases)}")
    print(f"   日总收益: ${total_standard_profit:.2f}")
    print(f"   日总成本: ${total_standard_cost:.2f}")
    print("   详细结果:")
    for r in standard_results:
        roi_display = f"{r['roi_days']}天" if r['roi_days'] > 0 else "无回本"
        print(f"     {r['model']} x{r['quantity']}: 日收益${r['daily_profit']:.2f}, ROI:{roi_display}")
    print()
    
    # 准确度对比
    if fast_result['success'] and standard_results:
        print("3. 准确度对比:")
        
        # 总收益对比
        fast_total = fast_result['summary']['total_daily_profit']
        standard_total = total_standard_profit
        profit_diff = abs(fast_total - standard_total)
        profit_error = (profit_diff / max(standard_total, 0.01)) * 100
        
        print(f"   日总收益差异: ${profit_diff:.2f} ({profit_error:.1f}%)")
        
        # 逐项对比
        print("   逐项对比:")
        for i, (fast_item, std_item) in enumerate(zip(fast_result['results'], standard_results)):
            model = fast_item['model']
            fast_profit = fast_item['daily_profit']
            std_profit = std_item['daily_profit']
            diff = abs(fast_profit - std_profit)
            error_pct = (diff / max(std_profit, 0.01)) * 100
            
            status = "✓" if error_pct < 5 else "⚠" if error_pct < 10 else "✗"
            print(f"     {status} {model}: 快速${fast_profit:.2f} vs 标准${std_profit:.2f} (误差{error_pct:.1f}%)")
        
        # 速度对比
        speed_improvement = ((standard_time - fast_time) / max(standard_time, 0.001)) * 100
        print(f"   速度提升: {speed_improvement:.1f}%")
        
        # 总结
        print("\n4. 测试总结:")
        if profit_error < 5:
            print("   ✅ 准确度: 优秀 (误差<5%)")
        elif profit_error < 10:
            print("   ⚠️  准确度: 良好 (误差<10%)")
        else:
            print("   ❌ 准确度: 需要改进 (误差>10%)")
            
        if speed_improvement > 30:
            print("   ⚡ 速度: 显著提升")
        elif speed_improvement > 0:
            print("   🚀 速度: 有所提升") 
        else:
            print("   ⏱️  速度: 无明显提升")
    
    return {
        'fast_time': fast_time,
        'standard_time': standard_time,
        'accuracy_error': profit_error if 'profit_error' in locals() else 0,
        'speed_improvement': speed_improvement if 'speed_improvement' in locals() else 0
    }

if __name__ == '__main__':
    result = test_calculation_accuracy()
    print("\n测试完成! 🎯")