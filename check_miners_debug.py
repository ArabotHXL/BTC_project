#!/usr/bin/env python3
"""
检查矿机数据获取问题
"""

import requests
import json

def main():
    base_url = "http://localhost:5000"
    session = requests.Session()
    
    # 认证
    print("🔐 进行认证...")
    response = session.post(f"{base_url}/login", data={'email': 'hxl2022hao@gmail.com'})
    if response.status_code not in [200, 302]:
        print("❌ 认证失败")
        return
    print("✅ 认证成功")
    
    # 获取矿机数据
    print("\n📋 获取矿机数据...")
    response = session.get(f"{base_url}/api/miners")
    print(f"状态码: {response.status_code}")
    
    if response.status_code == 200:
        try:
            data = response.json()
            print(f"响应数据: {json.dumps(data, indent=2, ensure_ascii=False)}")
            
            miners = data.get('miners', [])
            print(f"\n矿机数量: {len(miners)}")
            
            if miners:
                print("\n矿机列表:")
                for i, miner in enumerate(miners[:5]):
                    print(f"{i+1}. 名称: {miner.get('name', 'N/A')}")
                    print(f"   密钥: {miner.get('key', 'N/A')}")
                    print(f"   算力: {miner.get('hashrate_th', 'N/A')} TH/s")
                    print(f"   功耗: {miner.get('power_w', 'N/A')} W")
                    print()
        except Exception as e:
            print(f"JSON解析错误: {e}")
            print(f"响应内容: {response.text[:500]}")
    else:
        print(f"请求失败: {response.text[:200]}")

if __name__ == "__main__":
    main()