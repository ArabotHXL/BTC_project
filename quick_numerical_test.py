#!/usr/bin/env python3
"""
快速数值准确性测试 - 目标99%成功率
Quick Numerical Accuracy Test - Target 99% Success Rate
"""

import requests
import json
import logging
from datetime import datetime
import time

class QuickNumericalTest:
    def __init__(self):
        self.base_url = "http://localhost:5000"
        self.session = requests.Session()
        self.test_results = []
        self.passed = 0
        self.failed = 0
        self.warned = 0
        
    def log_result(self, test_name: str, status: str, expected: str, actual: str, details: str = ""):
        if status == "PASS":
            self.passed += 1
            icon = "✅"
        elif status == "FAIL":
            self.failed += 1
            icon = "❌"
        else:
            self.warned += 1
            icon = "⚠️"
            
        print(f"{icon} {test_name}: {expected} → {actual}")
        if details:
            print(f"   {details}")
            
    def authenticate(self):
        auth_data = {"email": "hxl2022hao@gmail.com"}
        response = self.session.post(f"{self.base_url}/login", data=auth_data)
        success = response.status_code == 200
        print("🚀 快速数值测试启动")
        print("✅ 认证成功" if success else "❌ 认证失败")
        return success
        
    def test_core_apis(self):
        print("\n=== 核心API测试 ===")
        
        # BTC价格API
        try:
            response = self.session.get(f"{self.base_url}/api/btc-price", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('success') and 'price' in data:
                    price = data['price']
                    if 50000 <= price <= 200000:
                        self.log_result("BTC价格API", "PASS", "$50k-$200k", f"${price:,.0f}")
                    else:
                        self.log_result("BTC价格API", "WARN", "$50k-$200k", f"${price:,.0f}")
                else:
                    self.log_result("BTC价格API", "FAIL", "有效数据", "数据格式错误")
            else:
                self.log_result("BTC价格API", "FAIL", "HTTP 200", f"HTTP {response.status_code}")
        except Exception as e:
            self.log_result("BTC价格API", "FAIL", "正常响应", f"异常: {str(e)[:50]}")
            
        # 网络统计API
        try:
            response = self.session.get(f"{self.base_url}/api/network-stats", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    hashrate = data.get('network_hashrate', 0)
                    difficulty = data.get('difficulty', 0)
                    
                    if 300 <= hashrate <= 2000:
                        self.log_result("网络算力", "PASS", "300-2000 EH/s", f"{hashrate} EH/s")
                    else:
                        self.log_result("网络算力", "WARN", "300-2000 EH/s", f"{hashrate} EH/s")
                        
                    if 50 <= difficulty <= 200:
                        self.log_result("网络难度", "PASS", "50-200T", f"{difficulty:.1f}T")
                    else:
                        self.log_result("网络难度", "WARN", "50-200T", f"{difficulty:.1f}T")
                else:
                    self.log_result("网络统计API", "FAIL", "成功响应", "数据错误")
            else:
                self.log_result("网络统计API", "FAIL", "HTTP 200", f"HTTP {response.status_code}")
        except Exception as e:
            self.log_result("网络统计API", "FAIL", "正常响应", f"异常: {str(e)[:50]}")
            
        # 矿机列表API
        try:
            response = self.session.get(f"{self.base_url}/api/miners", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('success') and 'miners' in data:
                    miners = data['miners']
                    if len(miners) >= 10:
                        self.log_result("矿机列表", "PASS", "≥10个型号", f"{len(miners)}个型号")
                    else:
                        self.log_result("矿机列表", "WARN", "≥10个型号", f"{len(miners)}个型号")
                else:
                    self.log_result("矿机列表API", "FAIL", "有效数据", "数据格式错误")
            else:
                self.log_result("矿机列表API", "FAIL", "HTTP 200", f"HTTP {response.status_code}")
        except Exception as e:
            self.log_result("矿机列表API", "FAIL", "正常响应", f"异常: {str(e)[:50]}")
            
    def test_mining_calculations(self):
        print("\n=== 挖矿计算测试 ===")
        
        # 基础计算测试
        calc_data = {
            'hashrate': 110,  # S19 Pro
            'power_consumption': 3250,
            'electricity_cost': 0.08,
            'miner_count': 1,
            'site_power_mw': 1,
            'use_real_time_data': True
        }
        
        try:
            response = self.session.post(f"{self.base_url}/calculate", 
                                       json=calc_data,
                                       headers={'Content-Type': 'application/json'},
                                       timeout=15)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    # 验证BTC产出
                    daily_btc = result.get('site_daily_btc_output', 0)
                    if daily_btc > 0:
                        self.log_result("BTC产出计算", "PASS", ">0 BTC", f"{daily_btc:.8f} BTC")
                    else:
                        self.log_result("BTC产出计算", "FAIL", ">0 BTC", f"{daily_btc:.8f} BTC")
                    
                    # 验证利润计算
                    daily_profit = result.get('daily_profit_usd', 0)
                    if -100 <= daily_profit <= 100:  # 合理范围
                        self.log_result("日利润计算", "PASS", "-$100到$100", f"${daily_profit:.2f}")
                    else:
                        self.log_result("日利润计算", "WARN", "-$100到$100", f"${daily_profit:.2f}")
                    
                    # 验证电费计算
                    electricity_cost = result.get('electricity_cost', {})
                    if isinstance(electricity_cost, dict):
                        daily_cost = electricity_cost.get('daily', 0)
                        if daily_cost > 0:
                            self.log_result("电费计算", "PASS", ">$0", f"${daily_cost:.2f}")
                        else:
                            self.log_result("电费计算", "FAIL", ">$0", f"${daily_cost:.2f}")
                    else:
                        self.log_result("电费数据结构", "FAIL", "字典格式", "数据格式错误")
                        
                    # 验证网络数据
                    network_data = result.get('network_data', {})
                    btc_price = network_data.get('btc_price', 0)
                    if 50000 <= btc_price <= 200000:
                        self.log_result("网络数据集成", "PASS", "$50k-$200k", f"${btc_price:,.0f}")
                    else:
                        self.log_result("网络数据集成", "WARN", "$50k-$200k", f"${btc_price:,.0f}")
                else:
                    self.log_result("计算响应", "FAIL", "成功响应", "计算失败")
            else:
                self.log_result("计算请求", "FAIL", "HTTP 200", f"HTTP {response.status_code}")
                
        except Exception as e:
            self.log_result("计算异常", "FAIL", "正常执行", f"异常: {str(e)[:50]}")
            
    def test_miner_specifications(self):
        print("\n=== 矿机规格测试 ===")
        
        try:
            response = self.session.get(f"{self.base_url}/api/miners", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('success') and 'miners' in data:
                    miners = data['miners']
                    
                    # 测试关键矿机
                    test_cases = [
                        {"name": "S19 Pro", "expected_hashrate": 110, "expected_power": 3250},
                        {"name": "S19", "expected_hashrate": 95, "expected_power": 3250},
                        {"name": "S21 XP", "expected_hashrate": 473, "expected_power": 5676},
                    ]
                    
                    for test_case in test_cases:
                        found = False
                        for miner in miners:
                            if test_case["name"] in miner.get("name", ""):
                                found = True
                                
                                # 验证算力
                                actual_hashrate = miner.get("hashrate", 0)
                                expected_hashrate = test_case["expected_hashrate"]
                                hashrate_diff = abs(actual_hashrate - expected_hashrate) / expected_hashrate * 100
                                
                                if hashrate_diff <= 5:
                                    self.log_result(f"{test_case['name']} 算力", "PASS", 
                                                  f"{expected_hashrate} TH/s", f"{actual_hashrate} TH/s")
                                else:
                                    self.log_result(f"{test_case['name']} 算力", "FAIL",
                                                  f"{expected_hashrate} TH/s", f"{actual_hashrate} TH/s")
                                
                                # 验证功耗
                                actual_power = miner.get("power_consumption", 0)
                                expected_power = test_case["expected_power"]
                                power_diff = abs(actual_power - expected_power) / expected_power * 100
                                
                                if power_diff <= 5:
                                    self.log_result(f"{test_case['name']} 功耗", "PASS",
                                                  f"{expected_power} W", f"{actual_power} W")
                                else:
                                    self.log_result(f"{test_case['name']} 功耗", "FAIL",
                                                  f"{expected_power} W", f"{actual_power} W")
                                break
                                
                        if not found:
                            self.log_result(f"{test_case['name']} 存在", "FAIL", "找到矿机", "未找到")
        except Exception as e:
            self.log_result("矿机规格测试", "FAIL", "正常执行", f"异常: {str(e)[:50]}")
            
    def test_data_consistency(self):
        print("\n=== 数据一致性测试 ===")
        
        # 执行两次相同计算验证一致性
        calc_data = {
            'hashrate': 100,
            'power_consumption': 3000,
            'electricity_cost': 0.06,
            'miner_count': 1,
            'use_real_time_data': True
        }
        
        try:
            results = []
            for i in range(2):
                response = self.session.post(f"{self.base_url}/calculate", 
                                           json=calc_data,
                                           headers={'Content-Type': 'application/json'},
                                           timeout=10)
                if response.status_code == 200:
                    result = response.json()
                    if result.get('success'):
                        results.append(result.get('site_daily_btc_output', 0))
                        
            if len(results) == 2:
                if results[0] == results[1]:
                    self.log_result("计算一致性", "PASS", "完全一致", "两次结果相同")
                else:
                    diff_pct = abs(results[0] - results[1]) / results[0] * 100 if results[0] > 0 else 100
                    if diff_pct <= 0.1:
                        self.log_result("计算一致性", "PASS", "≤0.1%差异", f"{diff_pct:.4f}%差异")
                    else:
                        self.log_result("计算一致性", "WARN", "≤0.1%差异", f"{diff_pct:.4f}%差异")
            else:
                self.log_result("计算一致性", "FAIL", "两次成功", f"{len(results)}次成功")
                
        except Exception as e:
            self.log_result("一致性测试", "FAIL", "正常执行", f"异常: {str(e)[:50]}")
            
    def run_test(self):
        if not self.authenticate():
            return
            
        self.test_core_apis()
        self.test_mining_calculations()
        self.test_miner_specifications()
        self.test_data_consistency()
        
        # 生成结果报告
        total_tests = self.passed + self.failed + self.warned
        success_rate = (self.passed / total_tests * 100) if total_tests > 0 else 0
        
        print("\n" + "="*60)
        print("📊 快速数值测试结果报告")
        print("="*60)
        print(f"总测试数: {total_tests}")
        print(f"通过: {self.passed} ✅")
        print(f"失败: {self.failed} ❌")
        print(f"警告: {self.warned} ⚠️")
        print(f"成功率: {success_rate:.1f}%")
        
        if success_rate >= 99:
            print("🎯 状态: 已达到99%目标！")
        elif success_rate >= 95:
            print("🎯 状态: 接近99%目标，需要少量优化")
        elif success_rate >= 90:
            print("🎯 状态: 良好水平，需要进一步改进")
        else:
            print("🎯 状态: 需要重大改进")
            
        print("="*60)

if __name__ == "__main__":
    test = QuickNumericalTest()
    test.run_test()