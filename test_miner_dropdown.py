#!/usr/bin/env python3
"""
测试矿机下拉菜单功能
"""

import requests
import json
import re

def test_miner_dropdown():
    """测试矿机下拉菜单数据"""
    base_url = "http://localhost:5000"
    session = requests.Session()
    
    print("测试矿机下拉菜单功能")
    print("=" * 30)
    
    # 认证
    auth_response = session.post(f"{base_url}/login", 
                               data={'email': 'user@example.com'})
    
    if auth_response.status_code == 200:
        print("✓ 用户认证成功")
        
        # 获取主页HTML
        home_response = session.get(base_url)
        if home_response.status_code == 200:
            content = home_response.text
            
            # 检查初始数据嵌入
            if 'window.initialData' in content:
                print("✓ 初始数据已嵌入")
                
                # 提取矿机数据
                start = content.find('miners: ')
                if start != -1:
                    end = content.find('];', start) + 1
                    miners_str = content[start+8:end]
                    try:
                        miners_data = json.loads(miners_str)
                        print(f"✓ 找到 {len(miners_data)} 个矿机型号")
                        
                        # 显示前3个矿机的详细信息
                        for i, miner in enumerate(miners_data[:3]):
                            print(f"  矿机{i+1}: {miner.get('model', miner.get('name', 'Unknown'))}")
                            print(f"    算力: {miner.get('hashrate', 0)} TH/s")
                            print(f"    功耗: {miner.get('power_consumption', miner.get('power_watt', 0))} W")
                            
                        return True
                    except json.JSONDecodeError as e:
                        print(f"✗ 矿机数据JSON解析失败: {e}")
                else:
                    print("✗ 未找到矿机数据")
            else:
                print("✗ 初始数据未嵌入")
        else:
            print(f"✗ 主页访问失败: {home_response.status_code}")
    else:
        print(f"✗ 认证失败: {auth_response.status_code}")
    
    return False

if __name__ == "__main__":
    test_miner_dropdown()