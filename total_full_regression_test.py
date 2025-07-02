#!/usr/bin/env python3
"""
完整数值回归测试 - 模块化详细报告
Total Full Regression Test - Modular Detailed Report

目标: 达到99%+成功率，详细显示每个测试模块
Target: Achieve 99%+ success rate with detailed module information
"""

import requests
import json
import logging
from datetime import datetime
import time
from typing import Dict, List, Any

class TotalFullRegressionTest:
    def __init__(self):
        self.base_url = "http://localhost:5000"
        self.session = requests.Session()
        self.results = {
            "核心API端点模块": {"passed": 0, "failed": 0, "warned": 0, "tests": []},
            "矿机数据验证模块": {"passed": 0, "failed": 0, "warned": 0, "tests": []},
            "挖矿计算引擎模块": {"passed": 0, "failed": 0, "warned": 0, "tests": []},
            "网络数据处理模块": {"passed": 0, "failed": 0, "warned": 0, "tests": []},
            "投资分析模块": {"passed": 0, "failed": 0, "warned": 0, "tests": []},
            "技术指标分析模块": {"passed": 0, "failed": 0, "warned": 0, "tests": []},
            "数据一致性验证模块": {"passed": 0, "failed": 0, "warned": 0, "tests": []},
            "限电管理系统模块": {"passed": 0, "failed": 0, "warned": 0, "tests": []}
        }
        
    def log_test(self, module: str, test_name: str, status: str, expected: str, actual: str, details: str = ""):
        """记录测试结果到指定模块"""
        if module not in self.results:
            self.results[module] = {"passed": 0, "failed": 0, "warned": 0, "tests": []}
            
        test_result = {
            "name": test_name,
            "status": status,
            "expected": expected,
            "actual": actual,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        
        self.results[module]["tests"].append(test_result)
        
        if status == "PASS":
            self.results[module]["passed"] += 1
            icon = "✅"
        elif status == "FAIL":
            self.results[module]["failed"] += 1
            icon = "❌"
        else:
            self.results[module]["warned"] += 1
            icon = "⚠️"
            
        print(f"{icon} [{module}] {test_name}")
        print(f"   期望: {expected} | 实际: {actual}")
        if details:
            print(f"   详情: {details}")
            
    def authenticate(self):
        """认证系统"""
        try:
            auth_data = {"email": "hxl2022hao@gmail.com"}
            response = self.session.post(f"{self.base_url}/login", data=auth_data)
            success = response.status_code == 200
            print("🚀 启动完整数值回归测试 - 模块化详细分析")
            print("✅ 系统认证成功" if success else "❌ 系统认证失败")
            return success
        except Exception as e:
            print(f"❌ 认证异常: {e}")
            return False
            
    def test_core_api_endpoints(self):
        """测试核心API端点模块"""
        module = "核心API端点模块"
        print(f"\n=== {module} ===")
        
        # Test 1: BTC价格API
        try:
            response = self.session.get(f"{self.base_url}/api/btc-price", timeout=8)
            if response.status_code == 200:
                data = response.json()
                if data.get('success') and 'price' in data:
                    price = data['price']
                    if 50000 <= price <= 200000:
                        self.log_test(module, "BTC价格API响应", "PASS", "$50,000-$200,000", f"${price:,.0f}")
                    else:
                        self.log_test(module, "BTC价格API响应", "WARN", "$50,000-$200,000", f"${price:,.0f}")
                else:
                    self.log_test(module, "BTC价格API响应", "FAIL", "有效价格数据", "数据格式错误")
            else:
                self.log_test(module, "BTC价格API响应", "FAIL", "HTTP 200", f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test(module, "BTC价格API响应", "FAIL", "正常响应", f"异常: {str(e)[:30]}")
            
        # Test 2: 网络统计API
        try:
            response = self.session.get(f"{self.base_url}/api/network-stats", timeout=8)
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    hashrate = data.get('network_hashrate', 0)
                    difficulty = data.get('difficulty', 0)
                    
                    if 300 <= hashrate <= 2000:
                        self.log_test(module, "网络算力数据", "PASS", "300-2000 EH/s", f"{hashrate} EH/s")
                    else:
                        self.log_test(module, "网络算力数据", "WARN", "300-2000 EH/s", f"{hashrate} EH/s")
                        
                    if 50 <= difficulty <= 200:
                        self.log_test(module, "网络难度数据", "PASS", "50-200T", f"{difficulty:.1f}T")
                    else:
                        self.log_test(module, "网络难度数据", "WARN", "50-200T", f"{difficulty:.1f}T")
                else:
                    self.log_test(module, "网络统计API响应", "FAIL", "成功响应", "API错误")
            else:
                self.log_test(module, "网络统计API响应", "FAIL", "HTTP 200", f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test(module, "网络统计API响应", "FAIL", "正常响应", f"异常: {str(e)[:30]}")
            
        # Test 3: 矿机列表API
        try:
            response = self.session.get(f"{self.base_url}/api/miners", timeout=8)
            if response.status_code == 200:
                data = response.json()
                if data.get('success') and 'miners' in data:
                    miners = data['miners']
                    if len(miners) >= 10:
                        self.log_test(module, "矿机列表完整性", "PASS", "≥10个型号", f"{len(miners)}个型号")
                    else:
                        self.log_test(module, "矿机列表完整性", "WARN", "≥10个型号", f"{len(miners)}个型号")
                else:
                    self.log_test(module, "矿机列表API响应", "FAIL", "有效矿机数据", "数据错误")
            else:
                self.log_test(module, "矿机列表API响应", "FAIL", "HTTP 200", f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test(module, "矿机列表API响应", "FAIL", "正常响应", f"异常: {str(e)[:30]}")
            
    def test_miner_data_validation(self):
        """测试矿机数据验证模块"""
        module = "矿机数据验证模块"
        print(f"\n=== {module} ===")
        
        try:
            response = self.session.get(f"{self.base_url}/api/miners", timeout=8)
            if response.status_code == 200:
                data = response.json()
                if data.get('success') and 'miners' in data:
                    miners = data['miners']
                    
                    # 关键矿机验证
                    test_miners = [
                        {"name": "S19 Pro", "expected_hashrate": 110, "expected_power": 3250},
                        {"name": "S19", "expected_hashrate": 95, "expected_power": 3250},
                        {"name": "S21 XP", "expected_hashrate": 473, "expected_power": 5676}
                    ]
                    
                    for test_miner in test_miners:
                        found = False
                        for miner in miners:
                            if test_miner["name"] in miner.get("name", ""):
                                found = True
                                
                                # 算力验证
                                actual_hashrate = miner.get("hashrate", 0)
                                expected_hashrate = test_miner["expected_hashrate"]
                                hashrate_diff = abs(actual_hashrate - expected_hashrate) / expected_hashrate * 100
                                
                                if hashrate_diff <= 5:
                                    self.log_test(module, f"{test_miner['name']} 算力规格", "PASS",
                                                f"{expected_hashrate} TH/s", f"{actual_hashrate} TH/s")
                                else:
                                    self.log_test(module, f"{test_miner['name']} 算力规格", "FAIL",
                                                f"{expected_hashrate} TH/s", f"{actual_hashrate} TH/s")
                                
                                # 功耗验证
                                actual_power = miner.get("power_consumption", 0)
                                expected_power = test_miner["expected_power"]
                                power_diff = abs(actual_power - expected_power) / expected_power * 100
                                
                                if power_diff <= 5:
                                    self.log_test(module, f"{test_miner['name']} 功耗规格", "PASS",
                                                f"{expected_power} W", f"{actual_power} W")
                                else:
                                    self.log_test(module, f"{test_miner['name']} 功耗规格", "FAIL",
                                                f"{expected_power} W", f"{actual_power} W")
                                
                                # 效率验证
                                if actual_power > 0:
                                    efficiency = actual_hashrate / (actual_power / 1000)
                                    if 15 <= efficiency <= 200:
                                        self.log_test(module, f"{test_miner['name']} 效率比", "PASS",
                                                    "15-200 TH/s/kW", f"{efficiency:.1f} TH/s/kW")
                                    else:
                                        self.log_test(module, f"{test_miner['name']} 效率比", "WARN",
                                                    "15-200 TH/s/kW", f"{efficiency:.1f} TH/s/kW")
                                break
                                
                        if not found:
                            self.log_test(module, f"{test_miner['name']} 型号存在性", "FAIL", "找到矿机", "矿机未找到")
        except Exception as e:
            self.log_test(module, "矿机数据获取", "FAIL", "正常获取", f"异常: {str(e)[:30]}")
            
    def test_mining_calculation_engine(self):
        """测试挖矿计算引擎模块"""
        module = "挖矿计算引擎模块"
        print(f"\n=== {module} ===")
        
        # 基础计算测试
        calc_data = {
            'hashrate': 110,
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
                                       timeout=12)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    # BTC产出验证
                    daily_btc = result.get('site_daily_btc_output', 0)
                    if daily_btc > 0:
                        self.log_test(module, "BTC日产出计算", "PASS", ">0 BTC", f"{daily_btc:.8f} BTC")
                    else:
                        self.log_test(module, "BTC日产出计算", "FAIL", ">0 BTC", f"{daily_btc:.8f} BTC")
                    
                    # 利润计算验证
                    daily_profit = result.get('daily_profit_usd', 0)
                    if -200 <= daily_profit <= 200:
                        self.log_test(module, "日利润计算", "PASS", "-$200到$200", f"${daily_profit:.2f}")
                    else:
                        self.log_test(module, "日利润计算", "WARN", "-$200到$200", f"${daily_profit:.2f}")
                    
                    # 电费计算验证
                    electricity_cost = result.get('electricity_cost', {})
                    if isinstance(electricity_cost, dict):
                        daily_cost = electricity_cost.get('daily', 0)
                        if daily_cost > 0:
                            self.log_test(module, "电费计算", "PASS", ">$0", f"${daily_cost:.2f}")
                        else:
                            self.log_test(module, "电费计算", "FAIL", ">$0", f"${daily_cost:.2f}")
                    else:
                        self.log_test(module, "电费数据结构", "FAIL", "字典格式", "格式错误")
                        
                    # 网络数据集成验证
                    network_data = result.get('network_data', {})
                    btc_price = network_data.get('btc_price', 0)
                    if 50000 <= btc_price <= 200000:
                        self.log_test(module, "网络数据集成", "PASS", "$50k-$200k", f"${btc_price:,.0f}")
                    else:
                        self.log_test(module, "网络数据集成", "WARN", "$50k-$200k", f"${btc_price:,.0f}")
                else:
                    self.log_test(module, "计算引擎响应", "FAIL", "成功计算", "计算失败")
            else:
                self.log_test(module, "计算引擎请求", "FAIL", "HTTP 200", f"HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test(module, "计算引擎异常", "FAIL", "正常执行", f"异常: {str(e)[:30]}")
            
    def test_data_consistency_validation(self):
        """测试数据一致性验证模块"""
        module = "数据一致性验证模块"
        print(f"\n=== {module} ===")
        
        # 计算一致性验证
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
                    self.log_test(module, "计算结果一致性", "PASS", "完全一致", "两次计算相同")
                else:
                    diff_pct = abs(results[0] - results[1]) / results[0] * 100 if results[0] > 0 else 100
                    if diff_pct <= 0.1:
                        self.log_test(module, "计算结果一致性", "PASS", "≤0.1%差异", f"{diff_pct:.4f}%差异")
                    else:
                        self.log_test(module, "计算结果一致性", "WARN", "≤0.1%差异", f"{diff_pct:.4f}%差异")
            else:
                self.log_test(module, "计算结果一致性", "FAIL", "两次成功计算", f"{len(results)}次成功")
                
        except Exception as e:
            self.log_test(module, "一致性验证", "FAIL", "正常执行", f"异常: {str(e)[:30]}")
            
    def test_technical_analysis_module(self):
        """测试技术指标分析模块"""
        module = "技术指标分析模块"
        print(f"\n=== {module} ===")
        
        # 分析市场数据验证
        try:
            response = self.session.get(f"{self.base_url}/api/analytics/market-data", timeout=8)
            if response.status_code == 200:
                data = response.json()
                if data.get('success') and 'data' in data:
                    market_data = data['data']
                    
                    # BTC价格验证
                    btc_price = market_data.get('btc_price')
                    if btc_price and 50000 <= btc_price <= 200000:
                        self.log_test(module, "分析系统BTC价格", "PASS", "$50k-$200k", f"${btc_price:,.0f}")
                    else:
                        self.log_test(module, "分析系统BTC价格", "WARN", "$50k-$200k", f"${btc_price}")
                        
                    # 恐惧贪婪指数验证
                    fear_greed = market_data.get('fear_greed_index')
                    if fear_greed and 0 <= fear_greed <= 100:
                        self.log_test(module, "恐惧贪婪指数", "PASS", "0-100", f"{fear_greed}")
                    else:
                        self.log_test(module, "恐惧贪婪指数", "WARN", "0-100", f"{fear_greed}")
                else:
                    self.log_test(module, "分析系统数据", "FAIL", "有效数据", "数据格式错误")
            else:
                self.log_test(module, "分析系统API", "FAIL", "HTTP 200", f"HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test(module, "技术分析模块", "FAIL", "正常执行", f"异常: {str(e)[:30]}")
            
        # 价格历史数据验证
        try:
            response = self.session.get(f"{self.base_url}/api/analytics/price-history", timeout=8)
            if response.status_code == 200:
                data = response.json()
                if data.get('success') and 'data' in data:
                    price_history = data['data']
                    if len(price_history) >= 10:
                        self.log_test(module, "价格历史数据量", "PASS", "≥10条记录", f"{len(price_history)}条")
                        
                        # 数据质量验证
                        valid_records = sum(1 for record in price_history[:10] 
                                          if record.get('btc_price') and record.get('btc_price') > 0)
                        if valid_records >= 8:
                            self.log_test(module, "价格数据质量", "PASS", "≥80%有效", f"{valid_records}/10有效")
                        else:
                            self.log_test(module, "价格数据质量", "WARN", "≥80%有效", f"{valid_records}/10有效")
                    else:
                        self.log_test(module, "价格历史数据量", "WARN", "≥10条记录", f"{len(price_history)}条")
                else:
                    self.log_test(module, "价格历史API", "FAIL", "有效数据", "数据错误")
            else:
                self.log_test(module, "价格历史API", "FAIL", "HTTP 200", f"HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test(module, "价格历史验证", "FAIL", "正常执行", f"异常: {str(e)[:30]}")
            
    def run_full_test(self):
        """运行完整测试"""
        if not self.authenticate():
            return
            
        # 执行所有模块测试
        self.test_core_api_endpoints()
        self.test_miner_data_validation()
        self.test_mining_calculation_engine()
        self.test_data_consistency_validation()
        self.test_technical_analysis_module()
        
        # 生成详细报告
        self.generate_detailed_report()
        
    def generate_detailed_report(self):
        """生成详细测试报告"""
        total_passed = sum(module["passed"] for module in self.results.values())
        total_failed = sum(module["failed"] for module in self.results.values())
        total_warned = sum(module["warned"] for module in self.results.values())
        total_tests = total_passed + total_failed + total_warned
        
        success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
        
        print("\n" + "="*80)
        print("📊 完整数值回归测试详细报告")
        print("Total Full Numerical Regression Test - Detailed Report")
        print("="*80)
        
        print(f"\n🎯 总体统计:")
        print(f"   总测试数: {total_tests}")
        print(f"   通过: {total_passed} ✅")
        print(f"   失败: {total_failed} ❌")
        print(f"   警告: {total_warned} ⚠️")
        print(f"   成功率: {success_rate:.1f}%")
        
        print(f"\n📋 各模块详细统计:")
        for module_name, module_data in self.results.items():
            total_module = module_data["passed"] + module_data["failed"] + module_data["warned"]
            if total_module > 0:
                module_success_rate = (module_data["passed"] / total_module * 100)
                status_icon = "🟢" if module_success_rate >= 90 else "🟡" if module_success_rate >= 75 else "🔴"
                print(f"   {status_icon} {module_name}:")
                print(f"      通过: {module_data['passed']}/{total_module} ({module_success_rate:.1f}%)")
                if module_data["failed"] > 0:
                    print(f"      失败: {module_data['failed']} 项")
                if module_data["warned"] > 0:
                    print(f"      警告: {module_data['warned']} 项")
        
        # 成功率评级
        if success_rate >= 99:
            grade = "优秀 (A+)"
            status = "🎯 已达到99%目标！系统准备就绪"
        elif success_rate >= 95:
            grade = "良好 (A)"
            status = "🎯 接近99%目标，系统基本就绪"
        elif success_rate >= 90:
            grade = "中等 (B)"
            status = "🎯 需要少量优化达到99%目标"
        elif success_rate >= 80:
            grade = "较差 (C)"
            status = "🎯 需要重点改进才能达到99%目标"
        else:
            grade = "失败 (D)"
            status = "🎯 需要大幅改进"
            
        print(f"\n🏆 最终评级: {grade}")
        print(f"📈 状态: {status}")
        
        # 显示失败测试详情
        if total_failed > 0:
            print(f"\n❌ 失败测试详情:")
            for module_name, module_data in self.results.items():
                failed_tests = [test for test in module_data["tests"] if test["status"] == "FAIL"]
                if failed_tests:
                    print(f"   [{module_name}]:")
                    for test in failed_tests:
                        print(f"      • {test['name']}: {test['details']}")
                        
        print("="*80)

def main():
    """主函数"""
    test = TotalFullRegressionTest()
    test.run_full_test()

if __name__ == "__main__":
    main()