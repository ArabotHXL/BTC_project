#!/usr/bin/env python3
"""
比特币挖矿计算器 - 回归测试套件
Bitcoin Mining Calculator - Regression Test Suite
"""

import requests
import json
import time
import logging
from datetime import datetime
import sys
import os
import threading
from concurrent.futures import ThreadPoolExecutor

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RegressionTestSuite:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.test_results = []
        self.performance_metrics = []
        
        # 测试用户邮箱
        self.test_emails = [
            "testing@example.com",
            "admin@example.com", 
            "site@example.com",
            "hxl2022hao@gmail.com",
            "owner@example.com"
        ]
        
        # 矿机测试数据
        self.miner_test_cases = [
            {"model": "Antminer S19 Pro", "count": 100, "expected_hashrate": 11000},
            {"model": "Antminer S19", "count": 50, "expected_hashrate": 9500},
            {"model": "Antminer S21", "count": 75, "expected_hashrate": 20000}
        ]
        
    def log_test(self, category, test_name, success, details="", response_time=0, data=None):
        """记录测试结果"""
        result = {
            "category": category,
            "test_name": test_name,
            "success": success,
            "details": details,
            "response_time": response_time,
            "timestamp": datetime.now().isoformat(),
            "data": data
        }
        self.test_results.append(result)
        status = "✅" if success else "❌"
        logger.info(f"{status} [{category}] {test_name} - {details} ({response_time:.3f}s)")
        
    def authenticate_user(self, email):
        """用户认证"""
        try:
            response = self.session.post(f"{self.base_url}/login", 
                                       data={"email": email}, 
                                       timeout=10)
            return response.status_code in [200, 302]
        except:
            return False
    
    def test_database_integrity(self):
        """数据库完整性测试"""
        logger.info("=== 数据库完整性测试 ===")
        
        # 测试用户认证表
        auth_success = 0
        for email in self.test_emails:
            start_time = time.time()
            success = self.authenticate_user(email)
            response_time = time.time() - start_time
            
            if success:
                auth_success += 1
                self.log_test("Database", f"User Auth - {email}", True, "Valid", response_time)
            else:
                self.log_test("Database", f"User Auth - {email}", False, "Invalid", response_time)
        
        # 总体数据库健康度
        db_health = (auth_success / len(self.test_emails)) * 100
        self.log_test("Database", "User Authentication", db_health > 60, f"{db_health:.1f}% success rate")
        
        # 测试网络数据快照
        try:
            start_time = time.time()
            self.authenticate_user("testing@example.com")
            response = self.session.get(f"{self.base_url}/api/network-stats", timeout=10)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("Database", "Network Snapshots", True, 
                            f"BTC: ${data.get('btc_price', 0):,.0f}", response_time, data)
            else:
                self.log_test("Database", "Network Snapshots", False, f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("Database", "Network Snapshots", False, f"Error: {str(e)}")
    
    def test_api_consistency(self):
        """API一致性测试"""
        logger.info("=== API一致性测试 ===")
        
        self.authenticate_user("testing@example.com")
        
        # 多次调用同一API，检查数据一致性
        api_calls = []
        for i in range(3):
            try:
                start_time = time.time()
                response = self.session.get(f"{self.base_url}/api/network-stats", timeout=10)
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    data = response.json()
                    api_calls.append({
                        "call": i+1,
                        "btc_price": data.get('btc_price', 0),
                        "network_hashrate": data.get('network_hashrate', 0),
                        "response_time": response_time
                    })
                    self.log_test("API", f"Network Stats Call {i+1}", True, 
                                f"BTC: ${data.get('btc_price', 0):,.0f}", response_time)
                else:
                    self.log_test("API", f"Network Stats Call {i+1}", False, f"HTTP {response.status_code}")
            except Exception as e:
                self.log_test("API", f"Network Stats Call {i+1}", False, f"Error: {str(e)}")
            
            time.sleep(1)  # 间隔1秒
        
        # 检查数据一致性
        if len(api_calls) >= 2:
            price_variance = max([call['btc_price'] for call in api_calls]) - min([call['btc_price'] for call in api_calls])
            hashrate_variance = max([call['network_hashrate'] for call in api_calls]) - min([call['network_hashrate'] for call in api_calls])
            
            consistent = price_variance < 1000 and hashrate_variance < 50  # 允许小幅波动
            self.log_test("API", "Data Consistency", consistent, 
                        f"Price variance: ${price_variance:.0f}, Hashrate variance: {hashrate_variance:.1f}")
    
    def test_mining_calculations_accuracy(self):
        """挖矿计算精度测试"""
        logger.info("=== 挖矿计算精度测试 ===")
        
        self.authenticate_user("testing@example.com")
        
        calculation_results = []
        for test_case in self.miner_test_cases:
            try:
                start_time = time.time()
                
                calc_data = {
                    "miner_model": test_case["model"],
                    "miner_count": str(test_case["count"]),
                    "electricity_cost": "0.08",
                    "client_electricity_cost": "0.10",
                    "use_real_time": "on"
                }
                
                response = self.session.post(f"{self.base_url}/calculate", 
                                           data=calc_data, 
                                           timeout=20)
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('success'):
                        btc_output = float(data.get('site_daily_btc_output', 0))
                        daily_profit = float(data.get('daily_profit_usd', 0))
                        
                        calculation_results.append({
                            "model": test_case["model"],
                            "btc_output": btc_output,
                            "daily_profit": daily_profit,
                            "response_time": response_time
                        })
                        
                        details = f"BTC: {btc_output:.6f}/day, Profit: ${daily_profit:,.2f}/day"
                        self.log_test("Calculation", f"{test_case['model']}", True, details, response_time)
                    else:
                        self.log_test("Calculation", f"{test_case['model']}", False, 
                                    f"Error: {data.get('error', 'Unknown')}")
                else:
                    self.log_test("Calculation", f"{test_case['model']}", False, f"HTTP {response.status_code}")
            except Exception as e:
                self.log_test("Calculation", f"{test_case['model']}", False, f"Error: {str(e)}")
        
        # 验证计算合理性
        if calculation_results:
            avg_btc_per_th = sum([r['btc_output']/100 for r in calculation_results]) / len(calculation_results)
            reasonable = 0.00001 < avg_btc_per_th < 0.001  # 合理的BTC产出范围
            self.log_test("Calculation", "Reasonableness Check", reasonable, 
                        f"Avg BTC/TH: {avg_btc_per_th:.8f}")
    
    def test_frontend_functionality(self):
        """前端功能测试"""
        logger.info("=== 前端功能测试 ===")
        
        self.authenticate_user("testing@example.com")
        
        # 测试主要页面
        pages = [
            ("/", "Main Dashboard", 5000),
            ("/analytics_dashboard", "Analytics Dashboard", 8000),
            ("/curtailment_calculator", "Curtailment Calculator", 3000),
            ("/crm/dashboard", "CRM Dashboard", 4000)
        ]
        
        for url, name, min_size in pages:
            try:
                start_time = time.time()
                response = self.session.get(f"{self.base_url}{url}", timeout=15)
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    content_size = len(response.text)
                    if content_size > min_size:
                        self.log_test("Frontend", name, True, 
                                    f"{content_size:,} chars loaded", response_time)
                    else:
                        self.log_test("Frontend", name, False, 
                                    f"Content too small: {content_size} chars")
                else:
                    self.log_test("Frontend", name, False, f"HTTP {response.status_code}")
            except Exception as e:
                self.log_test("Frontend", name, False, f"Error: {str(e)}")
    
    def test_performance_benchmarks(self):
        """性能基准测试"""
        logger.info("=== 性能基准测试 ===")
        
        self.authenticate_user("testing@example.com")
        
        # API响应时间测试
        api_endpoints = [
            ("/api/network-stats", "Network Stats", 2.0),
            ("/api/miners", "Miner Models", 1.0),
            ("/api/analytics/market-data", "Market Data", 3.0)
        ]
        
        for endpoint, name, max_time in api_endpoints:
            try:
                start_time = time.time()
                response = self.session.get(f"{self.base_url}{endpoint}", timeout=max_time*2)
                response_time = time.time() - start_time
                
                if response.status_code == 200 and response_time <= max_time:
                    self.log_test("Performance", f"{name} Response Time", True, 
                                f"{response_time:.3f}s (target: <{max_time}s)", response_time)
                elif response.status_code == 200:
                    self.log_test("Performance", f"{name} Response Time", False, 
                                f"{response_time:.3f}s (target: <{max_time}s)", response_time)
                else:
                    self.log_test("Performance", f"{name} Response Time", False, 
                                f"HTTP {response.status_code}")
            except Exception as e:
                self.log_test("Performance", f"{name} Response Time", False, f"Error: {str(e)}")
    
    def test_security_features(self):
        """安全功能测试"""
        logger.info("=== 安全功能测试 ===")
        
        # 测试未授权访问
        try:
            new_session = requests.Session()
            start_time = time.time()
            response = new_session.get(f"{self.base_url}/", timeout=10)
            response_time = time.time() - start_time
            
            if "login" in response.url.lower() or response.status_code == 401:
                self.log_test("Security", "Unauthorized Access Protection", True, 
                            "Redirected to login", response_time)
            else:
                self.log_test("Security", "Unauthorized Access Protection", False, 
                            "No access control")
        except Exception as e:
            self.log_test("Security", "Unauthorized Access Protection", False, f"Error: {str(e)}")
        
        # 测试NaN注入防护
        self.authenticate_user("testing@example.com")
        
        malicious_data = {
            "miner_model": "Antminer S19 Pro",
            "miner_count": "NaN",
            "electricity_cost": "Infinity",
            "client_electricity_cost": "-Infinity",
            "use_real_time": "on"
        }
        
        try:
            start_time = time.time()
            response = self.session.post(f"{self.base_url}/calculate", 
                                       data=malicious_data, 
                                       timeout=10)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                if not data.get('success') or data.get('error'):
                    self.log_test("Security", "NaN Injection Protection", True, 
                                "Malicious input rejected", response_time)
                else:
                    self.log_test("Security", "NaN Injection Protection", False, 
                                "Malicious input accepted")
            else:
                self.log_test("Security", "NaN Injection Protection", True, 
                            f"HTTP {response.status_code} (rejected)", response_time)
        except Exception as e:
            self.log_test("Security", "NaN Injection Protection", False, f"Error: {str(e)}")
    
    def run_regression_tests(self):
        """运行完整回归测试"""
        logger.info("🔄 开始回归测试套件")
        start_time = time.time()
        
        # 运行所有测试模块
        test_modules = [
            self.test_database_integrity,
            self.test_api_consistency,
            self.test_mining_calculations_accuracy,
            self.test_frontend_functionality,
            self.test_performance_benchmarks,
            self.test_security_features
        ]
        
        for test_module in test_modules:
            try:
                test_module()
            except Exception as e:
                logger.error(f"测试模块失败: {test_module.__name__} - {str(e)}")
        
        # 生成回归测试报告
        total_time = time.time() - start_time
        self.generate_regression_report(total_time)
        
        # 计算成功率
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r['success'])
        success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        
        return success_rate >= 85  # 85%以上通过率算回归测试成功
    
    def generate_regression_report(self, total_time):
        """生成回归测试报告"""
        # 按类别统计结果
        categories = {}
        for result in self.test_results:
            cat = result['category']
            if cat not in categories:
                categories[cat] = {'total': 0, 'passed': 0}
            categories[cat]['total'] += 1
            if result['success']:
                categories[cat]['passed'] += 1
        
        # 计算总体指标
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r['success'])
        success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        
        # 输出报告
        logger.info("\n" + "="*70)
        logger.info("📋 回归测试报告")
        logger.info("="*70)
        
        for cat, stats in categories.items():
            cat_rate = (stats['passed'] / stats['total']) * 100
            logger.info(f"{cat:15}: {stats['passed']:2}/{stats['total']:2} ({cat_rate:5.1f}%)")
        
        logger.info("-"*70)
        logger.info(f"{'总计':15}: {passed_tests:2}/{total_tests:2} ({success_rate:5.1f}%)")
        logger.info(f"总耗时: {total_time:.2f}秒")
        
        # 系统稳定性评估
        if success_rate >= 95:
            stability = "🟢 极稳定 (Excellent)"
        elif success_rate >= 90:
            stability = "🟡 稳定 (Good)"
        elif success_rate >= 80:
            stability = "🟠 基本稳定 (Fair)"
        else:
            stability = "🔴 不稳定 (Poor)"
        
        logger.info(f"系统稳定性: {stability}")
        
        # 性能指标
        response_times = [r['response_time'] for r in self.test_results if r['response_time'] > 0]
        if response_times:
            avg_response = sum(response_times) / len(response_times)
            logger.info(f"平均响应时间: {avg_response:.3f}秒")
        
        # 保存详细报告
        report_file = f"regression_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump({
                "summary": {
                    "total_tests": total_tests,
                    "passed_tests": passed_tests,
                    "success_rate": success_rate,
                    "stability": stability,
                    "total_time": total_time,
                    "avg_response_time": sum(response_times) / len(response_times) if response_times else 0,
                    "timestamp": datetime.now().isoformat()
                },
                "categories": categories,
                "test_results": self.test_results
            }, f, indent=2, ensure_ascii=False)
        
        logger.info(f"详细报告已保存: {report_file}")

if __name__ == "__main__":
    tester = RegressionTestSuite()
    success = tester.run_regression_tests()
    sys.exit(0 if success else 1)