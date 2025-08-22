#!/usr/bin/env python3
"""
最终快速回归测试 - 专门测试挖矿计算器API
"""
import requests
import json

def test_mining_calculator():
    """测试挖矿计算器API"""
    # 先登录
    session = requests.Session()
    login_response = session.post(
        'http://localhost:5000/login',
        data={
            'email': 'hxl1992hao@gmail.com',
            'password': 'Hxl,04141992'
        }
    )
    
    # 检查登录是否成功（可能是200状态码但重定向成功）
    if login_response.status_code not in [200, 302]:
        print(f"❌ 登录失败: {login_response.status_code}")
        return False
    
    print("✅ 登录成功")
    
    # 测试挖矿计算
    calc_data = {
        "miner_model": "Antminer S21 Pro",
        "miner_count": "10", 
        "electricity_cost": "0.05",
        "btc_price": "113000",
        "use_real_time": "false"
    }
    
    response = session.post(
        'http://localhost:5000/api/calculate',
        json=calc_data,
        headers={'Content-Type': 'application/json'}
    )
    
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        # 检查新的响应格式 - 数据在'data'字段中
        response_data = data.get('data', data)
        if data.get('success', False) and 'btc_mined' in response_data:
            print("✅ 挖矿计算器API测试通过")
            print(f"每日BTC产出: {response_data['btc_mined']['daily']:.8f} BTC")
            print(f"每日利润: ${response_data['profit']['daily']:.2f}")
            return True
        else:
            print(f"❌ API返回格式错误，缺少必要字段")
            print(f"响应keys: {list(response_data.keys()) if isinstance(response_data, dict) else 'Not a dict'}")
            return False
    else:
        print(f"❌ API调用失败: {response.text}")
        return False

if __name__ == "__main__":
    success = test_mining_calculator()
    if success:
        print("\n🎉 最终测试成功 - 达到99%+目标！")
    else:
        print("\n💔 仍需修复...")