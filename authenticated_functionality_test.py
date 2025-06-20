#!/usr/bin/env python3
"""
Authenticated Functionality Test
测试登录后的核心功能，特别是矿机选择和数据加载
"""

import requests
import json
import time

def test_authenticated_functionality():
    """测试认证后的功能"""
    base_url = "http://localhost:5000"
    session = requests.Session()
    
    print("🔐 Authenticated Functionality Test")
    print("=" * 50)
    
    # 1. 认证测试用户
    print("1. 执行用户认证...")
    auth_response = session.post(f"{base_url}/login", 
                               data={'email': 'user@example.com'},
                               allow_redirects=True)
    
    if auth_response.status_code == 200:
        print("✓ 用户认证成功")
        
        # 2. 测试主页访问
        print("\n2. 测试主页访问...")
        home_response = session.get(base_url)
        if home_response.status_code == 200:
            print("✓ 主页访问成功")
            
            # 检查初始数据是否嵌入
            if 'window.initialData' in home_response.text:
                print("✓ 初始数据已正确嵌入页面")
            else:
                print("✗ 初始数据未找到")
        
        # 3. 测试API端点
        print("\n3. 测试API端点...")
        
        # 网络数据API
        network_response = session.get(f"{base_url}/network_stats")
        if network_response.status_code == 200:
            data = network_response.json()
            if data.get('success'):
                print(f"✓ 网络数据API正常 - BTC价格: ${data.get('btc_price', 'N/A')}")
            else:
                print("✗ 网络数据API返回失败状态")
        else:
            print(f"✗ 网络数据API失败: {network_response.status_code}")
        
        # 矿机数据API
        miners_response = session.get(f"{base_url}/miners")
        if miners_response.status_code == 200:
            data = miners_response.json()
            if data.get('success') and data.get('miners'):
                miner_count = len(data['miners'])
                print(f"✓ 矿机数据API正常 - 共{miner_count}个矿机型号")
                
                # 显示前3个矿机
                for i, miner in enumerate(data['miners'][:3]):
                    print(f"  - {miner['name']}: {miner['hashrate']}TH/s, {miner['power_consumption']}W")
            else:
                print("✗ 矿机数据API返回无效数据")
        else:
            print(f"✗ 矿机数据API失败: {miners_response.status_code}")
        
        # 4. 测试计算功能
        print("\n4. 测试挖矿计算功能...")
        calc_data = {
            'miner_model': 'Antminer S21 XP',
            'miner_count': '5',
            'electricity_cost': '0.05',
            'use_real_time': 'on'
        }
        
        calc_response = session.post(f"{base_url}/calculate", data=calc_data)
        if calc_response.status_code == 200:
            try:
                calc_result = calc_response.json()
                if calc_result.get('success'):
                    daily_btc = calc_result.get('btc_mined', {}).get('daily', 0)
                    daily_profit = calc_result.get('profit_usd', {}).get('daily', 0)
                    print(f"✓ 计算功能正常 - 日产出: {daily_btc:.6f} BTC, 日收益: ${daily_profit:.2f}")
                else:
                    print(f"✗ 计算失败: {calc_result.get('error', '未知错误')}")
            except json.JSONDecodeError:
                print("✗ 计算API返回非JSON响应")
        else:
            print(f"✗ 计算API失败: {calc_response.status_code}")
        
        print("\n" + "=" * 50)
        print("✅ 认证功能测试完成")
        return True
        
    else:
        print(f"✗ 用户认证失败: {auth_response.status_code}")
        return False

if __name__ == "__main__":
    test_authenticated_functionality()