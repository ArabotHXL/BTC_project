#!/usr/bin/env python3
"""
最终数值回归测试 - 完整验证所有计算准确性
Final Numerical Regression Test - Complete verification of all calculation accuracy
"""

import requests
import json
from datetime import datetime

class FinalNumericalTest:
    def __init__(self):
        self.base_url = "http://localhost:5000"
        self.session = requests.Session()
        self.test_results = []
        
    def log_result(self, category, test_name, status, expected, actual, details=""):
        """记录测试结果"""
        result = {
            'category': category,
            'test_name': test_name,
            'status': status,
            'expected': expected,
            'actual': actual,
            'details': details,
            'timestamp': datetime.now().strftime('%H:%M:%S')
        }
        self.test_results.append(result)
        
        # 输出结果
        status_symbol = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"{status_symbol} [{category}] {test_name}")
        if expected is not None and actual is not None:
            print(f"   期望: {expected}, 实际: {actual}")
        if details:
            print(f"   详情: {details}")

    def authenticate(self):
        """进行认证"""
        response = self.session.post(f"{self.base_url}/login", 
                                   data={'email': 'hxl2022hao@gmail.com'})
        return response.status_code in [200, 302]

    def test_api_data_consistency(self):
        """测试API数据一致性"""
        print("\n=== API数据一致性测试 ===")
        
        # 获取BTC价格
        btc_price_response = self.session.get(f"{self.base_url}/api/btc-price")
        btc_price = 0
        if btc_price_response.status_code == 200:
            btc_price = btc_price_response.json().get('btc_price', 0)
        
        # 获取网络统计
        network_response = self.session.get(f"{self.base_url}/api/network-stats")
        network_hashrate = 0
        network_difficulty = 0
        if network_response.status_code == 200:
            data = network_response.json()
            network_hashrate = data.get('network_hashrate', 0)
            network_difficulty = data.get('difficulty', 0)
        
        # 获取分析数据
        analytics_response = self.session.get(f"{self.base_url}/api/analytics/market-data")
        analytics_price = 0
        analytics_hashrate = 0
        if analytics_response.status_code == 200:
            data = analytics_response.json().get('data', {})
            analytics_price = data.get('btc_price', 0)
            analytics_hashrate = data.get('network_hashrate', 0)
        
        # 验证BTC价格一致性
        if btc_price > 0 and analytics_price > 0:
            price_diff_pct = abs(btc_price - analytics_price) / max(btc_price, analytics_price) * 100
            if price_diff_pct <= 1.0:  # 1%容差
                self.log_result("API一致性", "BTC价格对比", "PASS", 
                              f"${analytics_price:,.0f}", f"${btc_price:,.0f}", 
                              f"差异 {price_diff_pct:.2f}%")
            else:
                self.log_result("API一致性", "BTC价格对比", "FAIL", 
                              f"${analytics_price:,.0f}", f"${btc_price:,.0f}", 
                              f"差异 {price_diff_pct:.2f}% 超出1%容差")
        
        # 验证算力数据合理性
        if network_hashrate > 300 and network_hashrate < 2000:
            self.log_result("API数据", "网络算力范围", "PASS", 
                          "300-2000 EH/s", f"{network_hashrate:.1f} EH/s")
        else:
            self.log_result("API数据", "网络算力范围", "FAIL", 
                          "300-2000 EH/s", f"{network_hashrate:.1f} EH/s")
        
        # 验证难度数据合理性
        difficulty_t = network_difficulty / 1e12 if network_difficulty > 1000 else network_difficulty
        if 50 <= difficulty_t <= 200:
            self.log_result("API数据", "网络难度范围", "PASS", 
                          "50-200T", f"{difficulty_t:.1f}T")
        else:
            self.log_result("API数据", "网络难度范围", "FAIL", 
                          "50-200T", f"{difficulty_t:.1f}T")

    def test_mining_calculations_with_real_data(self):
        """使用真实数据测试挖矿计算"""
        print("\n=== 挖矿计算准确性测试 ===")
        
        # 获取矿机列表
        miners_response = self.session.get(f"{self.base_url}/api/miners")
        if miners_response.status_code != 200:
            self.log_result("挖矿计算", "矿机列表获取", "FAIL", "HTTP 200", 
                          f"HTTP {miners_response.status_code}")
            return
        
        miners_data = miners_response.json().get('miners', [])
        if len(miners_data) < 5:
            self.log_result("挖矿计算", "矿机数量", "FAIL", "≥5", len(miners_data))
            return
        
        # 测试主要矿机型号
        test_miners = [
            {"name": "Antminer S19 Pro", "expected_hashrate": 110, "expected_power": 3250},
            {"name": "Antminer S19", "expected_hashrate": 95, "expected_power": 3250},
            {"name": "Antminer S21 XP", "expected_hashrate": 473, "expected_power": 5676}
        ]
        
        # 验证矿机数据
        for test_miner in test_miners:
            found_miner = None
            for miner in miners_data:
                if test_miner["name"] in miner.get("name", ""):
                    found_miner = miner
                    break
            
            if found_miner:
                # 验证算力
                actual_hashrate = found_miner.get("hashrate", 0)
                expected_hashrate = test_miner["expected_hashrate"]
                hashrate_diff_pct = abs(actual_hashrate - expected_hashrate) / expected_hashrate * 100
                
                if hashrate_diff_pct <= 10:  # 10%容差
                    self.log_result("矿机数据", f"{test_miner['name']} 算力", "PASS",
                                  f"{expected_hashrate} TH/s", f"{actual_hashrate} TH/s")
                else:
                    self.log_result("矿机数据", f"{test_miner['name']} 算力", "FAIL",
                                  f"{expected_hashrate} TH/s", f"{actual_hashrate} TH/s")
                
                # 验证功耗
                actual_power = found_miner.get("power_consumption", 0)
                expected_power = test_miner["expected_power"]
                power_diff_pct = abs(actual_power - expected_power) / expected_power * 100
                
                if power_diff_pct <= 10:  # 10%容差
                    self.log_result("矿机数据", f"{test_miner['name']} 功耗", "PASS",
                                  f"{expected_power} W", f"{actual_power} W")
                else:
                    self.log_result("矿机数据", f"{test_miner['name']} 功耗", "FAIL",
                                  f"{expected_power} W", f"{actual_power} W")
        
        # 测试实际挖矿计算
        print("\n--- 挖矿计算测试 ---")
        
        # 使用S19 Pro进行计算测试
        s19_pro = None
        for miner in miners_data:
            if "S19 Pro" in miner.get("name", ""):
                s19_pro = miner
                break
        
        if s19_pro:
            # 构建计算请求（基于实际矿机数据结构）
            calc_requests = [
                {"electricity_cost": 0.05, "miner_count": 100, "description": "标准电价"},
                {"electricity_cost": 0.08, "miner_count": 100, "description": "中等电价"},
                {"electricity_cost": 0.12, "miner_count": 100, "description": "高电价"}
            ]
            
            for req in calc_requests:
                try:
                    # 根据矿机数据格式构建请求
                    calc_data = {
                        'hashrate': s19_pro.get('hashrate', 110),  # 直接使用算力
                        'power_consumption': s19_pro.get('power_consumption', 3250),  # 直接使用功耗
                        'electricity_cost': req['electricity_cost'],
                        'miner_count': req['miner_count'],
                        'site_power_mw': 10,
                        'use_real_time_data': True
                    }
                    
                    response = self.session.post(f"{self.base_url}/calculate", 
                                               json=calc_data,
                                               headers={'Content-Type': 'application/json'})
                    
                    if response.status_code == 200:
                        result = response.json()
                        daily_profit = result.get('daily_profit_usd', 0)
                        btc_output = result.get('site_daily_btc_output', 0)
                        # 正确解析电费数据结构
                        electricity_cost_data = result.get('electricity_cost', {})
                        electricity_cost_daily = electricity_cost_data.get('daily', 0) if isinstance(electricity_cost_data, dict) else 0
                        
                        # 验证计算结果合理性
                        if daily_profit != 0 and btc_output > 0 and electricity_cost_daily > 0:
                            self.log_result("挖矿计算", f"S19 Pro - {req['description']}", "PASS",
                                          "合理数值", f"利润${daily_profit:.2f}, BTC{btc_output:.6f}")
                            
                            # 验证电价与利润的关系
                            profit_per_kwh = daily_profit / (s19_pro.get('power_consumption', 3250) * 24 / 1000)
                            expected_profit_range = (-20, 50)  # 合理的每日利润范围
                            
                            if expected_profit_range[0] <= daily_profit <= expected_profit_range[1]:
                                self.log_result("计算逻辑", f"利润范围 - {req['description']}", "PASS",
                                              f"${expected_profit_range[0]}-${expected_profit_range[1]}", 
                                              f"${daily_profit:.2f}")
                            else:
                                self.log_result("计算逻辑", f"利润范围 - {req['description']}", "WARN",
                                              f"${expected_profit_range[0]}-${expected_profit_range[1]}", 
                                              f"${daily_profit:.2f}")
                        else:
                            self.log_result("挖矿计算", f"S19 Pro - {req['description']}", "FAIL",
                                          "非零数值", f"利润${daily_profit}, BTC{btc_output}, 电费${electricity_cost_daily}")
                    else:
                        self.log_result("挖矿计算", f"S19 Pro - {req['description']}", "FAIL",
                                      "HTTP 200", f"HTTP {response.status_code}")
                        
                except Exception as e:
                    self.log_result("挖矿计算", f"S19 Pro - {req['description']}", "ERROR",
                                  "成功执行", str(e))

    def test_analytics_technical_data(self):
        """测试分析系统技术数据"""
        print("\n=== 分析系统技术数据测试 ===")
        
        # 测试技术指标
        tech_response = self.session.get(f"{self.base_url}/api/analytics/technical-indicators")
        if tech_response.status_code == 200:
            data = tech_response.json().get('data', {})
            
            # RSI检验
            rsi = data.get('rsi_14')
            if rsi is not None:
                if 0 <= rsi <= 100:
                    self.log_result("技术指标", "RSI范围", "PASS", "0-100", f"{rsi:.1f}")
                else:
                    self.log_result("技术指标", "RSI范围", "FAIL", "0-100", f"{rsi:.1f}")
            else:
                self.log_result("技术指标", "RSI数据", "WARN", "有数值", "None")
            
            # 移动平均线检验
            sma_20 = data.get('sma_20')
            sma_50 = data.get('sma_50')
            if sma_20 and sma_50:
                if 50000 <= sma_20 <= 200000 and 50000 <= sma_50 <= 200000:
                    self.log_result("技术指标", "SMA范围", "PASS", "50k-200k", 
                                  f"SMA20: ${sma_20:,.0f}, SMA50: ${sma_50:,.0f}")
                else:
                    self.log_result("技术指标", "SMA范围", "FAIL", "50k-200k", 
                                  f"SMA20: ${sma_20:,.0f}, SMA50: ${sma_50:,.0f}")
            else:
                self.log_result("技术指标", "SMA数据", "WARN", "有数值", "部分缺失")
        
        # 测试价格历史
        history_response = self.session.get(f"{self.base_url}/api/analytics/price-history")
        if history_response.status_code == 200:
            history_data = history_response.json()
            price_history = history_data.get('price_history', [])
            
            if len(price_history) >= 10:
                self.log_result("历史数据", "价格历史数量", "PASS", "≥10条", f"{len(price_history)}条")
                
                # 验证价格数据合理性
                valid_prices = 0
                for record in price_history[:10]:
                    price = record.get('btc_price', 0)
                    if 50000 <= price <= 200000:
                        valid_prices += 1
                
                if valid_prices >= 8:  # 80%的数据有效
                    self.log_result("历史数据", "价格数据质量", "PASS", "≥80%有效", f"{valid_prices}/10有效")
                else:
                    self.log_result("历史数据", "价格数据质量", "FAIL", "≥80%有效", f"{valid_prices}/10有效")
            else:
                self.log_result("历史数据", "价格历史数量", "FAIL", "≥10条", f"{len(price_history)}条")

    def generate_final_report(self):
        """生成最终测试报告"""
        print("\n" + "="*70)
        print("🔍 FINAL NUMERICAL REGRESSION TEST REPORT")
        print("最终数值回归测试报告")
        print("="*70)
        
        # 统计结果
        total = len(self.test_results)
        passed = len([r for r in self.test_results if r['status'] == 'PASS'])
        failed = len([r for r in self.test_results if r['status'] == 'FAIL'])
        warned = len([r for r in self.test_results if r['status'] == 'WARN'])
        errors = len([r for r in self.test_results if r['status'] == 'ERROR'])
        
        success_rate = (passed / total * 100) if total > 0 else 0
        
        print(f"\n📊 总体统计:")
        print(f"   总测试数: {total}")
        print(f"   通过: {passed} ✅")
        print(f"   失败: {failed} ❌")
        print(f"   警告: {warned} ⚠️")
        print(f"   错误: {errors} 🚫")
        print(f"   成功率: {success_rate:.1f}%")
        
        # 按分类统计
        categories = {}
        for result in self.test_results:
            cat = result['category']
            if cat not in categories:
                categories[cat] = {'PASS': 0, 'FAIL': 0, 'WARN': 0, 'ERROR': 0}
            categories[cat][result['status']] += 1
        
        print(f"\n📋 分类统计:")
        for category, stats in categories.items():
            cat_total = sum(stats.values())
            cat_passed = stats['PASS']
            cat_rate = (cat_passed / cat_total * 100) if cat_total > 0 else 0
            print(f"   {category}: {cat_passed}/{cat_total} ({cat_rate:.1f}%)")
        
        # 关键问题
        failed_tests = [r for r in self.test_results if r['status'] in ['FAIL', 'ERROR']]
        if failed_tests:
            print(f"\n❌ 需要关注的问题:")
            for test in failed_tests:
                print(f"   [{test['category']}] {test['test_name']}: {test['status']}")
                if test['details']:
                    print(f"      → {test['details']}")
        
        # 数值准确性评估
        numerical_tests = [r for r in self.test_results if any(keyword in r['test_name'].lower() 
                          for keyword in ['算力', '功耗', '价格', '范围', '计算'])]
        numerical_passed = len([r for r in numerical_tests if r['status'] == 'PASS'])
        numerical_rate = (numerical_passed / len(numerical_tests) * 100) if numerical_tests else 0
        
        print(f"\n🔢 数值准确性评估:")
        print(f"   数值相关测试: {len(numerical_tests)}")
        print(f"   数值测试通过: {numerical_passed}")
        print(f"   数值准确率: {numerical_rate:.1f}%")
        
        # 最终评级
        if success_rate >= 95:
            grade = "优秀 (A+)"
            recommendation = "系统数值计算准确性非常高，可以放心使用"
        elif success_rate >= 90:
            grade = "良好 (A)"
            recommendation = "系统整体表现良好，少数问题需要优化"
        elif success_rate >= 80:
            grade = "一般 (B)"
            recommendation = "系统基本可用，但需要解决一些数值问题"
        elif success_rate >= 70:
            grade = "较差 (C)"
            recommendation = "系统存在较多问题，需要重点修复"
        else:
            grade = "失败 (D)"
            recommendation = "系统存在严重问题，需要全面检查"
        
        print(f"\n🎯 最终评级: {grade}")
        print(f"💡 建议: {recommendation}")
        print("="*70)
        
        return success_rate

    def run_full_test(self):
        """运行完整的数值测试"""
        print("🚀 启动最终数值回归测试...")
        
        # 认证
        if not self.authenticate():
            print("❌ 认证失败，无法继续测试")
            return 0
        print("✅ 认证成功")
        
        # 执行测试
        self.test_api_data_consistency()
        self.test_mining_calculations_with_real_data()
        self.test_analytics_technical_data()
        
        # 生成报告
        return self.generate_final_report()

if __name__ == "__main__":
    tester = FinalNumericalTest()
    success_rate = tester.run_full_test()
    
    # 设置退出码
    if success_rate >= 80:
        exit(0)  # 成功
    else:
        exit(1)  # 需要改进