#!/usr/bin/env python3
"""
模拟完整的挖矿计算过程
"""

import requests
import json

def simulate_calculation():
    """模拟完整的计算流程"""
    base_url = "http://localhost:5000"
    session = requests.Session()
    
    print("模拟挖矿计算流程")
    print("=" * 30)
    
    # 1. 用户认证
    print("1. 进行用户认证...")
    auth_response = session.post(f"{base_url}/login", 
                               data={'email': 'user@example.com'})
    
    if auth_response.status_code != 200:
        print(f"✗ 认证失败: {auth_response.status_code}")
        return False
    print("✓ 认证成功")
    
    # 2. 获取主页并检查数据
    print("\n2. 获取主页数据...")
    home_response = session.get(base_url)
    if home_response.status_code != 200:
        print(f"✗ 主页访问失败: {home_response.status_code}")
        return False
    print("✓ 主页加载成功")
    
    # 3. 模拟用户选择参数
    print("\n3. 模拟用户输入参数...")
    calc_data = {
        'miner_model': 'Antminer S21 Pro',
        'site_power_mw': '5.0',
        'miner_count': '1000',
        'hashrate': '200',
        'power_consumption': '3500',
        'total_hashrate': '200000',
        'total_power': '3500000',
        'electricity_cost': '0.05',
        'client_electricity_cost': '0.06',
        'maintenance_fee': '5000',
        'host_investment': '1000000',
        'client_investment': '0',
        'btc_price': '103500',
        'use_real_time': 'on'
    }
    
    print("输入参数:")
    for key, value in calc_data.items():
        print(f"  {key}: {value}")
    
    # 4. 发送计算请求
    print("\n4. 发送计算请求...")
    calc_response = session.post(f"{base_url}/calculate", data=calc_data)
    
    if calc_response.status_code != 200:
        print(f"✗ 计算请求失败: {calc_response.status_code}")
        print(f"响应内容: {calc_response.text[:500]}")
        return False
    
    # 5. 解析计算结果
    print("✓ 计算请求成功")
    try:
        result = calc_response.json()
        print("\n5. 计算结果:")
        
        if result.get('success'):
            print("✓ 计算成功")
            
            # 显示关键结果
            print(f"\n挖矿收益:")
            if 'btc_mined' in result:
                btc_mined = result['btc_mined']
                print(f"  每日BTC: {btc_mined.get('daily', 0):.8f}")
                print(f"  每月BTC: {btc_mined.get('monthly', 0):.6f}")
                print(f"  每年BTC: {btc_mined.get('yearly', 0):.4f}")
            
            print(f"\n收益分析:")
            if 'profitability' in result:
                profit = result['profitability']
                print(f"  每日收益: ${profit.get('daily_profit', 0):,.2f}")
                print(f"  每月收益: ${profit.get('monthly_profit', 0):,.2f}")
                print(f"  每年收益: ${profit.get('yearly_profit', 0):,.2f}")
            
            print(f"\n设备信息:")
            print(f"  矿机数量: {result.get('miner_count', 0):,}")
            print(f"  总算力: {result.get('total_hashrate_th', 0):,.0f} TH/s")
            print(f"  总功耗: {result.get('total_power_w', 0):,.0f} W")
            
            print(f"\nROI分析:")
            if 'roi' in result:
                roi = result['roi']
                if 'client' in roi:
                    client_roi = roi['client']
                    print(f"  客户年化回报: {client_roi.get('annual_return_rate', 0):.2f}%")
                    print(f"  投资回收期: {client_roi.get('payback_months', 0):.1f}月")
            
            return True
        else:
            print("✗ 计算失败")
            print(f"错误信息: {result.get('error', '未知错误')}")
            return False
            
    except json.JSONDecodeError as e:
        print(f"✗ 结果解析失败: {e}")
        print(f"原始响应: {calc_response.text[:500]}")
        return False

if __name__ == "__main__":
    simulate_calculation()