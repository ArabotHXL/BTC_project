#!/usr/bin/env python3
"""
批量计算性能测试脚本
"""
import time
import requests
import json

def test_batch_performance():
    print("测试优化后的批量计算性能...")
    
    try:
        payload = {
            'miners': [
                {
                    'miner_number': '1',
                    'model': 'Antminer S19 Pro',
                    'quantity': 1,
                    'power_consumption': 3250,
                    'machine_price': 2500,
                    'electricity_cost': 0.08,
                    'decay_rate': 0.5,
                    'hashrate': 110
                },
                {
                    'miner_number': '2',
                    'model': 'WhatsMiner M53S',
                    'quantity': 1,
                    'power_consumption': 6554,
                    'machine_price': 4500,
                    'electricity_cost': 0.07,
                    'decay_rate': 0.3,
                    'hashrate': 226
                },
                {
                    'miner_number': '3',
                    'model': 'Antminer S21',
                    'quantity': 1,
                    'power_consumption': 3550,
                    'machine_price': 3200,
                    'electricity_cost': 0.08,
                    'decay_rate': 0.4,
                    'hashrate': 200
                }
            ],
            'settings': {
                'btc_price': None,
                'use_realtime': True
            }
        }
        
        start_time = time.time()
        response = requests.post('http://localhost:5000/api/batch-calculate', 
                               json=payload, timeout=30)
        end_time = time.time()
        
        calculation_time = end_time - start_time
        
        print(f"优化后API响应时间: {calculation_time:.2f}秒")
        print(f"API状态: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ 批量计算性能优化成功!")
            data = response.json()
            
            if 'results' in data and len(data['results']) > 0:
                print(f"✅ 返回了 {len(data['results'])} 个结果")
                print(f"✅ 优化信息: {data.get('optimization_info', {})}")
                
                # 显示第一个结果的关键数据
                first_result = data['results'][0]
                print(f"✅ 示例结果 - 型号: {first_result.get('model')}, 日利润: ${first_result.get('daily_profit', 0):.2f}")
            else:
                print("⚠️ 没有返回结果数据")
                
            if calculation_time < 3:
                print(f"🚀 性能优化成功！响应时间从 12+ 秒缩短到 {calculation_time:.2f} 秒")
            else:
                print(f"⚠️ 响应时间仍需进一步优化: {calculation_time:.2f} 秒")
                
        else:
            print(f"❌ API错误: {response.status_code}")
            try:
                error_data = response.json()
                print(f"错误详情: {error_data}")
            except:
                print("响应内容:", response.text[:200])
                
    except Exception as e:
        print(f"❌ 测试异常: {e}")

if __name__ == "__main__":
    test_batch_performance()