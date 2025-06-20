#!/usr/bin/env python3
"""
测试自动计算功能
Test automatic calculation functionality
"""

import requests
import json

def test_auto_calculations():
    """测试矿场功率变化时的自动计算"""
    base_url = "http://localhost:5000"
    session = requests.Session()
    
    print("测试自动计算功能")
    print("=" * 30)
    
    # 认证
    auth_response = session.post(f"{base_url}/login", 
                               data={'email': 'user@example.com'})
    
    if auth_response.status_code == 200:
        print("✓ 用户认证成功")
        
        # 获取主页以检查初始数据
        home_response = session.get(base_url)
        if 'window.initialData' in home_response.text:
            print("✓ 初始数据已嵌入页面")
            
            # 检查矿机数据
            if '"miners"' in home_response.text:
                print("✓ 矿机数据可用")
                
                # 模拟计算请求来验证后端计算逻辑
                calc_data = {
                    'miner_model': 'Antminer S21 Pro',
                    'site_power_mw': '5.0',  # 5MW矿场
                    'btc_price': '103000',
                    'electricity_cost': '0.05'
                }
                
                response = session.post(f"{base_url}/calculate", data=calc_data)
                if response.status_code == 200:
                    data = response.json()
                    if data.get('success'):
                        # 检查计算结果
                        miner_count = data.get('miner_count', 0)
                        total_hashrate = data.get('total_hashrate_th', 0)
                        total_power = data.get('total_power_w', 0)
                        
                        print(f"✓ 计算结果:")
                        print(f"  - 矿机数量: {miner_count:,}")
                        print(f"  - 总算力: {total_hashrate:,.0f} TH/s")
                        print(f"  - 总功耗: {total_power:,.0f} W")
                        print(f"  - 月度收益: ${data.get('monthly_profit_usd', 0):,.0f}")
                        
                        # 验证计算逻辑
                        if miner_count > 0 and total_hashrate > 0 and total_power > 0:
                            print("✓ 自动计算功能正常工作")
                            return True
                        else:
                            print("✗ 计算结果为零，可能有问题")
                    else:
                        print("✗ 计算请求失败")
                else:
                    print(f"✗ 计算请求错误: {response.status_code}")
            else:
                print("✗ 矿机数据缺失")
        else:
            print("✗ 初始数据未嵌入")
    else:
        print(f"✗ 认证失败: {auth_response.status_code}")
    
    return False

if __name__ == "__main__":
    test_auto_calculations()