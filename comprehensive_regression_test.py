#!/usr/bin/env python3
"""
Bitcoin Mining Calculator System - Comprehensive Regression Test Suite
Target Accuracy: 99%+ (based on system's previous 99.75% achievement)
Tests all core functionality after JavaScript ES6→ES5 conversion
"""

import requests
import json
import time
import random
import subprocess
import sqlite3
import psycopg2
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any
import os
import sys

class ComprehensiveRegressionTest:
    def __init__(self):
        self.base_url = "http://0.0.0.0:5000"
        self.test_results = []
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = []
        self.accuracy_threshold = 99.0
        
        # Test user credentials (from replit.md achievements)
        self.test_emails = [
            "admin@example.com",
            "hxl2022hao@gmail.com", 
            "user@example.com",
            "site@example.com",
            "testing123@example.com"
        ]
        
        print(f"🚀 启动全面回归测试 - 目标准确率: {self.accuracy_threshold}%")
        print(f"🔗 测试目标: {self.base_url}")
        print("=" * 80)

    def log_test(self, test_name: str, passed: bool, details: str = "", critical: bool = False):
        """记录测试结果"""
        self.total_tests += 1
        status = "✅ PASS" if passed else "❌ FAIL"
        priority = "🔴 CRITICAL" if critical and not passed else ""
        
        result = {
            'test_name': test_name,
            'passed': passed,
            'details': details,
            'critical': critical,
            'timestamp': datetime.now().isoformat()
        }
        
        self.test_results.append(result)
        
        if passed:
            self.passed_tests += 1
        else:
            self.failed_tests.append(result)
            
        print(f"{status} {priority} {test_name}")
        if details:
            print(f"    📝 {details}")

    def test_system_health(self):
        """测试系统基础健康状态"""
        print("\n🏥 系统健康检查")
        print("-" * 40)
        
        try:
            # 测试服务器响应
            response = requests.get(f"{self.base_url}/", timeout=10)
            if response.status_code in [200, 302]:  # 200 或重定向到登录页
                self.log_test("系统服务器响应", True, f"状态码: {response.status_code}")
            else:
                self.log_test("系统服务器响应", False, f"异常状态码: {response.status_code}", critical=True)
                
        except Exception as e:
            self.log_test("系统服务器响应", False, f"连接失败: {str(e)}", critical=True)

        # 测试数据库连接
        try:
            response = requests.get(f"{self.base_url}/api/health", timeout=5)
            db_ok = response.status_code == 200
            self.log_test("数据库连接", db_ok, "PostgreSQL数据库" if db_ok else "数据库连接异常")
        except:
            self.log_test("数据库连接", False, "健康检查API不可用")

    def test_authentication_system(self):
        """测试认证系统 - 100%成功率要求"""
        print("\n🔐 认证系统测试")
        print("-" * 40)
        
        auth_success_count = 0
        
        for email in self.test_emails:
            try:
                # 测试登录请求
                login_data = {"email": email}
                response = requests.post(
                    f"{self.base_url}/login", 
                    data=login_data,
                    timeout=10,
                    allow_redirects=False
                )
                
                # 检查响应 (302重定向表示成功)
                success = response.status_code in [200, 302]
                if success:
                    auth_success_count += 1
                    
                self.log_test(
                    f"用户认证: {email}", 
                    success, 
                    f"响应码: {response.status_code}",
                    critical=True
                )
                
            except Exception as e:
                self.log_test(f"用户认证: {email}", False, f"请求异常: {str(e)}", critical=True)
        
        # 计算认证成功率
        auth_success_rate = (auth_success_count / len(self.test_emails)) * 100
        self.log_test(
            "认证系统整体", 
            auth_success_rate >= 100.0, 
            f"成功率: {auth_success_rate:.1f}% ({auth_success_count}/{len(self.test_emails)})",
            critical=True
        )

    def test_api_data_collection(self):
        """测试API数据收集 - 要求100%数据可靠性"""
        print("\n📡 API数据收集测试")
        print("-" * 40)
        
        # 测试实时数据API
        try:
            response = requests.get(f"{self.base_url}/api/analytics/data", timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success') and data.get('data'):
                    market_data = data['data']
                    
                    # 验证关键数据字段
                    required_fields = ['btc_price', 'network_hashrate', 'network_difficulty', 'fear_greed_index']
                    missing_fields = []
                    
                    for field in required_fields:
                        if field not in market_data or market_data[field] is None:
                            missing_fields.append(field)
                    
                    if not missing_fields:
                        self.log_test("实时市场数据", True, f"BTC: ${market_data['btc_price']:,.0f}, 算力: {market_data['network_hashrate']:.1f} EH/s")
                        
                        # 验证数据合理性
                        btc_price = market_data['btc_price']
                        hashrate = market_data['network_hashrate']
                        
                        price_valid = 50000 <= btc_price <= 200000  # 合理价格范围
                        hashrate_valid = 500 <= hashrate <= 2000   # 合理算力范围
                        
                        self.log_test("数据合理性验证", price_valid and hashrate_valid, 
                                    f"价格合理: {price_valid}, 算力合理: {hashrate_valid}")
                    else:
                        self.log_test("实时市场数据", False, f"缺失字段: {missing_fields}", critical=True)
                else:
                    self.log_test("实时市场数据", False, "API响应格式错误", critical=True)
            else:
                self.log_test("实时市场数据", False, f"API请求失败: {response.status_code}", critical=True)
                
        except Exception as e:
            self.log_test("实时市场数据", False, f"请求异常: {str(e)}", critical=True)

    def test_mining_calculations(self):
        """测试挖矿计算引擎 - 要求99%精度"""
        print("\n⛏️ 挖矿计算引擎测试")
        print("-" * 40)
        
        test_scenarios = [
            {
                "miner": "Antminer S19 Pro",
                "count": 100,
                "electricity_cost": 0.05,
                "expected_positive_profit": True
            },
            {
                "miner": "Antminer S21",
                "count": 50,
                "electricity_cost": 0.08,
                "expected_positive_profit": True
            },
            {
                "miner": "WhatsMiner M50",
                "count": 200,
                "electricity_cost": 0.12,
                "expected_positive_profit": False  # 高电费场景
            }
        ]
        
        calculation_success_count = 0
        
        for i, scenario in enumerate(test_scenarios):
            try:
                calc_data = {
                    "miner_model": scenario["miner"],
                    "miner_count": scenario["count"],
                    "electricity_cost": scenario["electricity_cost"],
                    "use_real_time_data": True
                }
                
                response = requests.post(
                    f"{self.base_url}/api/test/calculate",
                    data=calc_data,
                    timeout=15
                )
                
                if response.status_code == 200:
                    # 检查JSON响应是否包含计算结果
                    try:
                        json_data = response.json()
                        has_results = (
                            json_data.get('success') == True and
                            'btc_mined' in json_data and
                            'profit' in json_data and
                            json_data.get('btc_mined', {}).get('daily', 0) > 0
                        )
                        
                        if has_results:
                            calculation_success_count += 1
                            btc_daily = json_data['btc_mined']['daily']
                            profit_daily = json_data['profit']['daily']
                            self.log_test(f"挖矿计算场景 {i+1}", True, 
                                        f"{scenario['miner']} x{scenario['count']}, 日产出: {btc_daily:.6f}BTC, 日利润: ${profit_daily:.2f}")
                        else:
                            self.log_test(f"挖矿计算场景 {i+1}", False, "JSON响应格式异常或计算结果为零")
                    except json.JSONDecodeError:
                        self.log_test(f"挖矿计算场景 {i+1}", False, "响应不是有效的JSON格式")
                else:
                    self.log_test(f"挖矿计算场景 {i+1}", False, f"计算请求失败: {response.status_code}")
                    
            except Exception as e:
                self.log_test(f"挖矿计算场景 {i+1}", False, f"计算异常: {str(e)}")
        
        # 计算成功率
        calc_success_rate = (calculation_success_count / len(test_scenarios)) * 100
        self.log_test(
            "挖矿计算引擎整体", 
            calc_success_rate >= 99.0, 
            f"成功率: {calc_success_rate:.1f}% ({calculation_success_count}/{len(test_scenarios)})"
        )

    def test_responsive_design(self):
        """测试响应式设计 - 要求100%兼容性"""
        print("\n📱 响应式设计测试")
        print("-" * 40)
        
        # 模拟不同屏幕尺寸的请求
        user_agents = [
            ("Mobile", "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15"),
            ("Tablet", "Mozilla/5.0 (iPad; CPU OS 13_0 like Mac OS X) AppleWebKit/605.1.15"),
            ("Desktop", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"),
            ("Large Desktop", "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36")
        ]
        
        responsive_success_count = 0
        
        for device_type, user_agent in user_agents:
            try:
                headers = {"User-Agent": user_agent}
                response = requests.get(f"{self.base_url}/", headers=headers, timeout=10)
                
                if response.status_code in [200, 302]:
                    # 检查响应式CSS类是否存在
                    content = response.text
                    responsive_indicators = [
                        "col-md", "col-lg", "col-sm", "d-md-block", 
                        "responsive", "mobile", "bootstrap"
                    ]
                    
                    has_responsive = any(indicator in content for indicator in responsive_indicators)
                    
                    if has_responsive:
                        responsive_success_count += 1
                        self.log_test(f"响应式设计: {device_type}", True, "包含响应式布局")
                    else:
                        self.log_test(f"响应式设计: {device_type}", False, "缺少响应式元素")
                else:
                    self.log_test(f"响应式设计: {device_type}", False, f"页面加载失败: {response.status_code}")
                    
            except Exception as e:
                self.log_test(f"响应式设计: {device_type}", False, f"测试异常: {str(e)}")
        
        # 计算兼容性
        responsive_success_rate = (responsive_success_count / len(user_agents)) * 100
        self.log_test(
            "响应式设计整体", 
            responsive_success_rate >= 100.0, 
            f"兼容性: {responsive_success_rate:.1f}% ({responsive_success_count}/{len(user_agents)})"
        )

    def test_javascript_functionality(self):
        """测试JavaScript功能 - 验证ES5转换后的兼容性"""
        print("\n🔧 JavaScript功能测试")
        print("-" * 40)
        
        js_tests = [
            ("页面加载", "/"),
            ("分析仪表盘", "/"),
            ("图表渲染", "/api/analytics/data"),
            ("多语言支持", "/"),
        ]
        
        js_success_count = 0
        
        for test_name, endpoint in js_tests:
            try:
                response = requests.get(f"{self.base_url}{endpoint}", timeout=10)
                
                if response.status_code in [200, 302]:
                    content = response.text
                    
                    # 检查JavaScript语法错误指标
                    no_syntax_errors = not any(error in content for error in [
                        "SyntaxError", "missing )", "unexpected token", 
                        "illegal character", "unterminated string"
                    ])
                    
                    # 检查现代JavaScript功能已转换
                    es5_compatible = not any(es6_feature in content for es6_feature in [
                        "=>", "`${", "const ", "let ", "...spread", "?.optional"
                    ])
                    
                    if no_syntax_errors and es5_compatible:
                        js_success_count += 1
                        self.log_test(f"JS功能: {test_name}", True, "ES5兼容，无语法错误")
                    else:
                        self.log_test(f"JS功能: {test_name}", False, 
                                    f"语法问题: {not no_syntax_errors}, ES6残留: {not es5_compatible}")
                else:
                    self.log_test(f"JS功能: {test_name}", False, f"页面加载失败: {response.status_code}")
                    
            except Exception as e:
                self.log_test(f"JS功能: {test_name}", False, f"测试异常: {str(e)}")
        
        js_success_rate = (js_success_count / len(js_tests)) * 100
        self.log_test(
            "JavaScript功能整体", 
            js_success_rate >= 99.0, 
            f"兼容性: {js_success_rate:.1f}% ({js_success_count}/{len(js_tests)})"
        )

    def test_multilingual_support(self):
        """测试多语言支持 - 中英文切换"""
        print("\n🌍 多语言支持测试")
        print("-" * 40)
        
        languages = [("中文", "zh"), ("English", "en")]
        lang_success_count = 0
        
        for lang_name, lang_code in languages:
            try:
                # 测试语言切换
                response = requests.get(
                    f"{self.base_url}/?lang={lang_code}", 
                    timeout=10,
                    allow_redirects=True
                )
                
                if response.status_code in [200, 302]:
                    content = response.text
                    
                    # 检查语言特定内容
                    if lang_code == "zh":
                        has_chinese = any(char in content for char in ["挖矿", "计算", "登录", "系统"])
                        lang_success = has_chinese
                    else:
                        has_english = any(word in content for word in ["Mining", "Calculator", "Login", "System"])
                        lang_success = has_english
                    
                    if lang_success:
                        lang_success_count += 1
                        self.log_test(f"语言支持: {lang_name}", True, f"语言代码: {lang_code}")
                    else:
                        self.log_test(f"语言支持: {lang_name}", False, "语言内容未正确显示")
                else:
                    self.log_test(f"语言支持: {lang_name}", False, f"语言切换失败: {response.status_code}")
                    
            except Exception as e:
                self.log_test(f"语言支持: {lang_name}", False, f"测试异常: {str(e)}")
        
        lang_success_rate = (lang_success_count / len(languages)) * 100
        self.log_test(
            "多语言支持整体", 
            lang_success_rate >= 100.0, 
            f"支持率: {lang_success_rate:.1f}% ({lang_success_count}/{len(languages)})"
        )

    def test_performance_benchmarks(self):
        """测试系统性能 - 要求亚秒级响应"""
        print("\n⚡ 性能基准测试")
        print("-" * 40)
        
        performance_tests = [
            ("首页加载", "/", 2.0),
            ("API数据", "/api/analytics/data", 3.0),
            ("挖矿计算", "/api/test/calculate", 5.0),
        ]
        
        perf_success_count = 0
        
        for test_name, endpoint, max_time in performance_tests:
            try:
                start_time = time.time()
                
                if endpoint == "/api/test/calculate":
                    # POST请求用于计算
                    response = requests.post(
                        f"{self.base_url}{endpoint}",
                        data={
                            "miner_model": "Antminer S19 Pro",
                            "miner_count": 10,
                            "electricity_cost": 0.05
                        },
                        timeout=max_time + 1
                    )
                else:
                    response = requests.get(f"{self.base_url}{endpoint}", timeout=max_time + 1)
                
                elapsed_time = time.time() - start_time
                
                if response.status_code in [200, 302] and elapsed_time <= max_time:
                    perf_success_count += 1
                    self.log_test(f"性能: {test_name}", True, f"响应时间: {elapsed_time:.2f}s (目标: ≤{max_time}s)")
                else:
                    self.log_test(f"性能: {test_name}", False, 
                                f"响应时间: {elapsed_time:.2f}s, 状态: {response.status_code}")
                    
            except Exception as e:
                self.log_test(f"性能: {test_name}", False, f"性能测试异常: {str(e)}")
        
        perf_success_rate = (perf_success_count / len(performance_tests)) * 100
        self.log_test(
            "系统性能整体", 
            perf_success_rate >= 100.0, 
            f"效率: {perf_success_rate:.1f}% ({perf_success_count}/{len(performance_tests)})"
        )

    def generate_comprehensive_report(self):
        """生成全面测试报告"""
        print("\n" + "="*80)
        print("📊 全面回归测试报告")
        print("="*80)
        
        # 计算总体准确率
        overall_accuracy = (self.passed_tests / self.total_tests) * 100
        
        print(f"🎯 总体准确率: {overall_accuracy:.2f}% (目标: ≥{self.accuracy_threshold}%)")
        print(f"✅ 通过测试: {self.passed_tests}")
        print(f"❌ 失败测试: {len(self.failed_tests)}")
        print(f"📝 总测试数: {self.total_tests}")
        
        # 准确率状态
        if overall_accuracy >= self.accuracy_threshold:
            print("🏆 测试状态: PASS - 达到目标准确率")
            print("🎉 系统已通过全面回归测试验证")
        else:
            print("🚨 测试状态: FAIL - 未达到目标准确率")
            print("⚠️  需要修复以下问题:")
            
            for failed in self.failed_tests:
                priority = "🔴 [CRITICAL]" if failed['critical'] else "🟡 [NORMAL]"
                print(f"   {priority} {failed['test_name']}: {failed['details']}")
        
        # 生成测试报告文件
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'overall_accuracy': overall_accuracy,
            'target_accuracy': self.accuracy_threshold,
            'passed_tests': self.passed_tests,
            'failed_tests': len(self.failed_tests),
            'total_tests': self.total_tests,
            'test_results': self.test_results,
            'status': 'PASS' if overall_accuracy >= self.accuracy_threshold else 'FAIL'
        }
        
        with open('regression_test_report.json', 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n📄 详细报告已保存: regression_test_report.json")
        print("="*80)
        
        return overall_accuracy >= self.accuracy_threshold

    def run_all_tests(self):
        """运行所有测试套件"""
        print("🚀 开始执行全面回归测试套件")
        
        # 按优先级执行测试
        test_suites = [
            ("系统健康", self.test_system_health),
            ("认证系统", self.test_authentication_system),
            ("API数据收集", self.test_api_data_collection),
            ("挖矿计算", self.test_mining_calculations),
            ("JavaScript功能", self.test_javascript_functionality),
            ("响应式设计", self.test_responsive_design),
            ("多语言支持", self.test_multilingual_support),
            ("性能基准", self.test_performance_benchmarks),
        ]
        
        for suite_name, test_func in test_suites:
            try:
                test_func()
            except Exception as e:
                self.log_test(f"{suite_name}测试套件", False, f"套件执行异常: {str(e)}", critical=True)
            
            # 测试间隔
            time.sleep(1)
        
        # 生成最终报告
        return self.generate_comprehensive_report()

def main():
    """主函数"""
    print("Bitcoin Mining Calculator - Comprehensive Regression Test")
    print("Target: 99%+ Accuracy Rate")
    print("Testing JavaScript ES6→ES5 conversion compatibility")
    print()
    
    # 等待系统启动
    print("⏳ 等待系统启动...")
    time.sleep(3)
    
    # 创建并运行测试
    test_suite = ComprehensiveRegressionTest()
    success = test_suite.run_all_tests()
    
    # 返回适当的退出码
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()