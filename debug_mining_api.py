#!/usr/bin/env python3
"""
调试挖矿计算API返回字段问题
"""
import requests
import json

def test_mining_api():
    # 模拟认证登录
    login_data = {'email': 'hxl2022hao@gmail.com'}
    
    with requests.Session() as session:
        # 登录
        login_response = session.post('http://localhost:5000/login', data=login_data)
        print(f"登录状态: {login_response.status_code}")
        
        # 测试挖矿计算
        calc_data = {
            'miner_model': 'antminer_s19_pro',
            'miner_count': '1',
            'electricity_cost': '0.08',
            'use_real_time': 'true'
        }
        
        calc_response = session.post('http://localhost:5000/calculate', data=calc_data)
        print(f"计算状态: {calc_response.status_code}")
        
        if calc_response.status_code == 200:
            result = calc_response.json()
            print("\n返回的字段:")
            for key in sorted(result.keys()):
                print(f"  {key}: {type(result[key])}")
            
            # 检查缺失字段
            required_fields = ['monthly_profit_usd', 'annual_roi_percentage', 'breakeven_electricity_cost', 'network_hashrate']
            missing_fields = [field for field in required_fields if field not in result]
            
            if missing_fields:
                print(f"\n❌ 缺失字段: {missing_fields}")
            else:
                print("\n✅ 所有必需字段都存在")
            
            # 显示具体数据
            print(f"\n💰 利润数据:")
            if 'profit' in result:
                print(f"  profit结构: {result['profit']}")
            if 'monthly_profit_usd' in result:
                print(f"  monthly_profit_usd: {result['monthly_profit_usd']}")
            
            print(f"\n📊 ROI数据:")
            if 'roi' in result:
                print(f"  roi结构: {result['roi']}")
            if 'annual_roi_percentage' in result:
                print(f"  annual_roi_percentage: {result['annual_roi_percentage']}")
            
            print(f"\n⚡ 盈亏平衡:")
            if 'break_even' in result:
                print(f"  break_even结构: {result['break_even']}")
            if 'breakeven_electricity_cost' in result:
                print(f"  breakeven_electricity_cost: {result['breakeven_electricity_cost']}")
            
            print(f"\n🌐 网络数据:")
            if 'network_data' in result:
                print(f"  network_data结构: {result['network_data']}")
            if 'network_hashrate' in result:
                print(f"  network_hashrate: {result['network_hashrate']}")
        else:
            print(f"错误: {calc_response.text}")

if __name__ == "__main__":
    test_mining_api()