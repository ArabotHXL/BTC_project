#!/usr/bin/env python3
"""
快速数值回归测试 - 专注核心计算准确性
Quick Numerical Regression Test - Focus on Core Calculation Accuracy
"""

import requests
import json
from datetime import datetime

class QuickNumericalTest:
    def __init__(self):
        self.base_url = "http://localhost:5000"
        self.session = requests.Session()
        
    def authenticate(self):
        """进行认证"""
        response = self.session.post(f"{self.base_url}/login", 
                                   data={'email': 'hxl2022hao@gmail.com'})
        return response.status_code in [200, 302]

    def test_core_apis(self):
        """测试核心API数值"""
        print("=== 核心API数值测试 ===")
        
        # 1. BTC价格API
        try:
            response = self.session.get(f"{self.base_url}/api/btc-price")
            if response.status_code == 200:
                data = response.json()
                btc_price = data.get('btc_price', 0)
                print(f"✓ BTC价格API: ${btc_price:,.2f}")
                if btc_price > 50000:
                    print(f"  ✅ 价格范围正常 (${btc_price:,.2f})")
                else:
                    print(f"  ❌ 价格异常: ${btc_price:,.2f}")
            else:
                print(f"❌ BTC价格API失败: HTTP {response.status_code}")
        except Exception as e:
            print(f"❌ BTC价格API错误: {e}")

        # 2. 网络统计API
        try:
            response = self.session.get(f"{self.base_url}/api/network-stats")
            if response.status_code == 200:
                data = response.json()
                hashrate = data.get('network_hashrate', 0)
                difficulty = data.get('difficulty', 0)
                print(f"✓ 网络统计API: 算力 {hashrate:.1f} EH/s, 难度 {difficulty/1e12:.1f}T")
                if hashrate > 300 and difficulty > 30e12:
                    print(f"  ✅ 网络数据正常")
                else:
                    print(f"  ❌ 网络数据异常")
            else:
                print(f"❌ 网络统计API失败: HTTP {response.status_code}")
        except Exception as e:
            print(f"❌ 网络统计API错误: {e}")

        # 3. 矿机列表API
        try:
            response = self.session.get(f"{self.base_url}/api/miners")
            if response.status_code == 200:
                data = response.json()
                miners = data.get('miners', [])
                print(f"✓ 矿机列表API: 找到 {len(miners)} 个矿机型号")
                if len(miners) >= 8:
                    print(f"  ✅ 矿机数据完整")
                    return miners
                else:
                    print(f"  ❌ 矿机数据不足")
            else:
                print(f"❌ 矿机列表API失败: HTTP {response.status_code}")
        except Exception as e:
            print(f"❌ 矿机列表API错误: {e}")
        
        return []

    def test_mining_calculations(self, miners):
        """测试挖矿计算数值准确性"""
        print("\n=== 挖矿计算数值测试 ===")
        
        # 选择几个主要矿机进行测试
        test_miners = ['antminer_s19_pro', 'antminer_s19', 'antminer_s21_xp']
        
        for miner_key in test_miners:
            # 找到矿机详细信息
            miner_info = None
            for m in miners:
                if m.get('key') == miner_key:
                    miner_info = m
                    break
            
            if not miner_info:
                print(f"❌ 找不到矿机: {miner_key}")
                continue
                
            miner_name = miner_info.get('name', miner_key)
            hashrate_th = miner_info.get('hashrate_th', 0)
            power_w = miner_info.get('power_w', 0)
            
            print(f"\n--- 测试 {miner_name} ---")
            print(f"   规格: {hashrate_th} TH/s, {power_w} W")
            
            # 测试不同电价下的计算
            electricity_costs = [0.03, 0.05, 0.08]
            
            for elec_cost in electricity_costs:
                try:
                    calc_data = {
                        'miner_model': miner_key,
                        'site_power_mw': 10,
                        'miner_count': 100,
                        'electricity_cost': elec_cost,
                        'use_real_time_data': True
                    }
                    
                    response = self.session.post(f"{self.base_url}/calculate", 
                                               json=calc_data,
                                               headers={'Content-Type': 'application/json'})
                    
                    if response.status_code == 200:
                        result = response.json()
                        
                        daily_profit = result.get('daily_profit_usd', 0)
                        btc_output = result.get('site_daily_btc_output', 0)
                        electricity_cost_daily = result.get('daily_electricity_cost', 0)
                        
                        print(f"   电价 ${elec_cost}/kWh:")
                        print(f"     每日利润: ${daily_profit:.2f}")
                        print(f"     BTC产出: {btc_output:.6f}")
                        print(f"     电费成本: ${electricity_cost_daily:.2f}")
                        
                        # 数值合理性检查
                        if daily_profit != 0 and btc_output > 0 and electricity_cost_daily > 0:
                            print(f"     ✅ 数值合理")
                        else:
                            print(f"     ❌ 数值异常 (利润={daily_profit}, BTC={btc_output}, 电费={electricity_cost_daily})")
                            
                            # 详细诊断
                            print(f"     诊断信息:")
                            print(f"       - 总算力: {result.get('site_total_hashrate_th', 0)} TH/s")
                            print(f"       - 总功耗: {result.get('site_total_power_kw', 0)} kW")
                            print(f"       - 网络算力: {result.get('network_hashrate_eh', 0)} EH/s")
                            print(f"       - BTC价格: ${result.get('btc_price', 0)}")
                            
                    else:
                        print(f"   ❌ 计算失败: HTTP {response.status_code}")
                        if response.status_code == 401:
                            print(f"      认证问题")
                        else:
                            try:
                                error_data = response.json()
                                print(f"      错误: {error_data}")
                            except:
                                print(f"      响应: {response.text[:200]}")
                                
                except Exception as e:
                    print(f"   ❌ 计算错误: {e}")

    def test_analytics_numbers(self):
        """测试分析系统数值"""
        print("\n=== 分析系统数值测试 ===")
        
        # 1. 市场数据
        try:
            response = self.session.get(f"{self.base_url}/api/analytics/market-data")
            if response.status_code == 200:
                data = response.json().get('data', {})
                btc_price = data.get('btc_price', 0)
                hashrate = data.get('network_hashrate', 0)
                fear_greed = data.get('fear_greed_index')
                
                print(f"✓ 分析市场数据:")
                print(f"  BTC价格: ${btc_price:,.2f}")
                print(f"  网络算力: {hashrate:.1f} EH/s")
                print(f"  恐惧贪婪指数: {fear_greed}")
                
                if btc_price > 50000 and hashrate > 300:
                    print(f"  ✅ 市场数据正常")
                else:
                    print(f"  ❌ 市场数据异常")
            else:
                print(f"❌ 分析市场数据失败: HTTP {response.status_code}")
        except Exception as e:
            print(f"❌ 分析市场数据错误: {e}")

        # 2. 技术指标
        try:
            response = self.session.get(f"{self.base_url}/api/analytics/technical-indicators")
            if response.status_code == 200:
                data = response.json().get('data', {})
                rsi = data.get('rsi_14')
                sma_20 = data.get('sma_20')
                volatility = data.get('volatility_30d')
                
                print(f"✓ 技术指标:")
                print(f"  RSI: {rsi:.1f}" if rsi else "  RSI: None")
                print(f"  SMA20: ${sma_20:,.2f}" if sma_20 else "  SMA20: None")
                print(f"  波动率: {volatility:.3f}" if volatility else "  波动率: None")
                
                if rsi and 0 <= rsi <= 100:
                    print(f"  ✅ 技术指标正常")
                else:
                    print(f"  ❌ 技术指标异常")
            else:
                print(f"❌ 技术指标失败: HTTP {response.status_code}")
        except Exception as e:
            print(f"❌ 技术指标错误: {e}")

    def run_test(self):
        """运行快速数值测试"""
        print("="*60)
        print("快速数值回归测试")
        print("Quick Numerical Regression Test")
        print("="*60)
        
        # 1. 认证
        print("🔐 进行认证...")
        if not self.authenticate():
            print("❌ 认证失败")
            return
        print("✅ 认证成功")
        
        # 2. 测试核心API
        miners = self.test_core_apis()
        
        # 3. 测试挖矿计算
        if miners:
            self.test_mining_calculations(miners)
        
        # 4. 测试分析系统
        self.test_analytics_numbers()
        
        print("\n" + "="*60)
        print("测试完成")
        print("="*60)

if __name__ == "__main__":
    tester = QuickNumericalTest()
    tester.run_test()