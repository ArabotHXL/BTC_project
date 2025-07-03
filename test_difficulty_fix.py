#!/usr/bin/env python3
"""
测试难度显示修复
Test Difficulty Display Fix
"""

import requests
import json

def test_difficulty_display():
    """测试难度显示格式"""
    print("测试难度显示修复...")
    
    # 创建会话
    session = requests.Session()
    
    # 首先登录
    login_data = {
        'email': 'hxl2022hao@gmail.com'
    }
    
    login_response = session.post('http://0.0.0.0:5000/login', data=login_data)
    print(f"登录状态: {login_response.status_code}")
    
    # 获取网络统计
    network_response = session.get('http://0.0.0.0:5000/api/network-stats')
    
    if network_response.status_code == 200:
        data = network_response.json()
        if data.get('success'):
            difficulty_raw = data.get('difficulty', 0)
            difficulty_t = difficulty_raw / 1e12
            
            print(f"✅ 网络统计API响应成功")
            print(f"原始难度值: {difficulty_raw:,.0f}")
            print(f"格式化难度值: {difficulty_t:.1f}T")
            print(f"BTC价格: ${data.get('btc_price', 0):,.2f}")
            print(f"网络算力: {data.get('network_hashrate', 0):.2f} EH/s")
            
            # 检查难度是否在合理范围内
            if 100 <= difficulty_t <= 200:
                print("✅ 难度值在合理范围内 (100-200T)")
            else:
                print(f"⚠️ 难度值 {difficulty_t:.1f}T 可能不在预期范围内")
                
        else:
            print(f"❌ API返回错误: {data.get('error')}")
    else:
        print(f"❌ API请求失败: {network_response.status_code}")
        print(network_response.text)

if __name__ == "__main__":
    test_difficulty_display()