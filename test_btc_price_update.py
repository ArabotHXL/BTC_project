#!/usr/bin/env python3
"""
Test BTC Price Update Functionality
测试BTC价格实时更新功能
"""

import requests
import json

def test_btc_price_update():
    """测试BTC价格更新功能"""
    base_url = "http://localhost:5000"
    session = requests.Session()
    
    print("Testing BTC Price Real-time Update")
    print("=" * 40)
    
    # 认证
    auth_response = session.post(f"{base_url}/login", 
                               data={'email': 'user@example.com'})
    
    if auth_response.status_code == 200:
        # 测试主页数据嵌入
        home_response = session.get(base_url)
        if 'window.initialData' in home_response.text:
            print("✓ Initial data embedded in page")
            
            # 提取初始数据
            start = home_response.text.find('window.initialData = {')
            end = home_response.text.find('};', start) + 2
            if start != -1 and end != -1:
                data_str = home_response.text[start:end].replace('window.initialData = ', '')
                try:
                    # 由于JSON可能包含模板语法，直接检查字符串
                    if 'btc_price' in data_str:
                        print("✓ BTC price data found in initial data")
                    else:
                        print("✗ BTC price data missing from initial data")
                except:
                    print("! Could not parse initial data JSON")
        
        # 测试网络统计API
        network_response = session.get(f"{base_url}/network_stats")
        if network_response.status_code == 200:
            data = network_response.json()
            if data.get('success') and data.get('btc_price'):
                current_price = data['btc_price']
                print(f"✓ Network Stats API returning BTC price: ${current_price:,.0f}")
                
                # 检查价格是否为实时数据（大于100,000表示当前市场价格）
                if current_price > 100000:
                    print("✓ Price appears to be real-time market data")
                else:
                    print("! Price appears to be default/static value")
                    
                return current_price
            else:
                print("✗ Network Stats API not returning BTC price")
        else:
            print(f"✗ Network Stats API failed: {network_response.status_code}")
    else:
        print(f"✗ Authentication failed: {auth_response.status_code}")
    
    return None

if __name__ == "__main__":
    test_btc_price_update()