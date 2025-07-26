#!/usr/bin/env python3
"""
比特币挖矿计算器 - 全面系统测试
Bitcoin Mining Calculator - Comprehensive System Testing
"""

import requests
import json
import time
import logging
from datetime import datetime
import sys
import os

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BTCMiningCalculatorTester:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.test_results = []
        self.test_emails = [
            "testing@example.com",
            "admin@example.com", 
            "site@example.com",
            "hxl2022hao@gmail.com",
            "owner@example.com"
        ]
        
    def log_test(self, test_name, success, details="", response_time=0):
        """记录测试结果"""
        result = {
            "test_name": test_name,
            "success": success,
            "details": details,
            "response_time": response_time,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        status = "✅ PASS" if success else "❌ FAIL"
        logger.info(f"{status} {test_name} - {details} ({response_time:.3f}s)")
        
    def test_health_endpoints(self):
        """测试健康检查端点"""
        logger.info("=== 健康检查测试 ===")
        
        # 测试 /health 端点
        try:
            start_time = time.time()
            response = self.session.get(f"{self.base_url}/health", timeout=10)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("Health Check", True, f"Status: {data.get('status')}", response_time)
            else:
                self.log_test("Health Check", False, f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("Health Check", False, f"Error: {str(e)}")
            
        # 测试 /status 端点
        try:
            start_time = time.time()
            response = self.session.get(f"{self.base_url}/status", timeout=5)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                self.log_test("Status Check", True, "Ready", response_time)
            else:
                self.log_test("Status Check", False, f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("Status Check", False, f"Error: {str(e)}")
    
    def test_authentication_system(self):
        """测试认证系统"""
        logger.info("=== 认证系统测试 ===")
        
        success_count = 0
        for email in self.test_emails:
            try:
                start_time = time.time()
                response = self.session.post(f"{self.base_url}/login", 
                                           data={"email": email}, 
                                           timeout=10)
                response_time = time.time() - start_time
                
                if response.status_code == 302 or "dashboard" in response.url:
                    self.log_test(f"Login - {email}", True, "Authenticated", response_time)
                    success_count += 1
                else:
                    self.log_test(f"Login - {email}", False, f"HTTP {response.status_code}")
            except Exception as e:
                self.log_test(f"Login - {email}", False, f"Error: {str(e)}")
        
        # 总体认证成功率
        success_rate = (success_count / len(self.test_emails)) * 100
        self.log_test("Authentication System", success_count > 0, f"{success_rate:.1f}% success rate")
    
    def test_api_endpoints(self):
        """测试主要API端点"""
        logger.info("=== API端点测试 ===")
        
        # 先进行登录
        try:
            self.session.post(f"{self.base_url}/login", data={"email": "testing@example.com"})
        except:
            pass
        
        api_endpoints = [
            ("/api/network-stats", "Network Stats"),
            ("/api/miners", "Miner Models"),
            ("/api/calculate", "Mining Calculator"),
            ("/api/analytics/market-data", "Analytics Market Data")
        ]
        
        for endpoint, name in api_endpoints:
            try:
                start_time = time.time()
                response = self.session.get(f"{self.base_url}{endpoint}", timeout=15)
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        if data.get('success', True):  # 某些API可能没有success字段
                            self.log_test(f"API - {name}", True, "Valid response", response_time)
                        else:
                            self.log_test(f"API - {name}", False, f"API error: {data.get('error', 'Unknown')}")
                    except:
                        self.log_test(f"API - {name}", False, "Invalid JSON response")
                else:
                    self.log_test(f"API - {name}", False, f"HTTP {response.status_code}")
            except Exception as e:
                self.log_test(f"API - {name}", False, f"Error: {str(e)}")
    
    def test_mining_calculation(self):
        """测试挖矿计算功能"""
        logger.info("=== 挖矿计算测试 ===")
        
        # 先登录
        try:
            self.session.post(f"{self.base_url}/login", data={"email": "testing@example.com"})
        except:
            pass
        
        test_data = {
            "miner_model": "Antminer S19 Pro",
            "miner_count": "100",
            "electricity_cost": "0.08",
            "client_electricity_cost": "0.10",
            "use_real_time": "on"
        }
        
        try:
            start_time = time.time()
            response = self.session.post(f"{self.base_url}/calculate", 
                                       data=test_data, 
                                       timeout=20)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    if data.get('success'):
                        btc_output = data.get('site_daily_btc_output', 0)
                        daily_profit = data.get('daily_profit_usd', 0)
                        details = f"BTC: {btc_output:.6f}, Profit: ${daily_profit:.2f}"
                        self.log_test("Mining Calculation", True, details, response_time)
                    else:
                        self.log_test("Mining Calculation", False, f"Calc error: {data.get('error')}")
                except:
                    self.log_test("Mining Calculation", False, "Invalid response format")
            else:
                self.log_test("Mining Calculation", False, f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("Mining Calculation", False, f"Error: {str(e)}")
    
    def test_frontend_pages(self):
        """测试前端页面加载"""
        logger.info("=== 前端页面测试 ===")
        
        # 先登录
        try:
            self.session.post(f"{self.base_url}/login", data={"email": "testing@example.com"})
        except:
            pass
        
        pages = [
            ("/", "Main Page"),
            ("/analytics_dashboard", "Analytics Dashboard"),
            ("/curtailment_calculator", "Curtailment Calculator"),
            ("/crm/dashboard", "CRM Dashboard")
        ]
        
        for url, name in pages:
            try:
                start_time = time.time()
                response = self.session.get(f"{self.base_url}{url}", timeout=15)
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    content_length = len(response.text)
                    if content_length > 1000:  # 页面应该有实际内容
                        self.log_test(f"Page - {name}", True, f"{content_length} chars", response_time)
                    else:
                        self.log_test(f"Page - {name}", False, f"Too small: {content_length} chars")
                else:
                    self.log_test(f"Page - {name}", False, f"HTTP {response.status_code}")
            except Exception as e:
                self.log_test(f"Page - {name}", False, f"Error: {str(e)}")
    
    def test_real_time_data(self):
        """测试实时数据功能"""
        logger.info("=== 实时数据测试 ===")
        
        # 先登录
        try:
            self.session.post(f"{self.base_url}/login", data={"email": "testing@example.com"})
        except:
            pass
        
        try:
            start_time = time.time()
            response = self.session.get(f"{self.base_url}/api/network-stats", timeout=15)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                btc_price = data.get('btc_price', 0)
                network_hashrate = data.get('network_hashrate', 0)
                difficulty = data.get('difficulty', 0)
                
                if btc_price > 50000 and network_hashrate > 500:  # 合理范围
                    details = f"BTC: ${btc_price:,.0f}, Hashrate: {network_hashrate:.1f} EH/s"
                    self.log_test("Real-time Data", True, details, response_time)
                else:
                    self.log_test("Real-time Data", False, f"Invalid data: BTC=${btc_price}, HR={network_hashrate}")
            else:
                self.log_test("Real-time Data", False, f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("Real-time Data", False, f"Error: {str(e)}")
    
    def test_multilingual_support(self):
        """测试多语言支持"""
        logger.info("=== 多语言支持测试 ===")
        
        languages = [("zh", "Chinese"), ("en", "English")]
        
        for lang_code, lang_name in languages:
            try:
                start_time = time.time()
                response = self.session.get(f"{self.base_url}/?lang={lang_code}", timeout=10)
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    content = response.text
                    # 检查语言特定的内容
                    if lang_code == "zh" and ("比特币" in content or "挖矿" in content):
                        self.log_test(f"Language - {lang_name}", True, "Content localized", response_time)
                    elif lang_code == "en" and ("Bitcoin" in content or "Mining" in content):
                        self.log_test(f"Language - {lang_name}", True, "Content localized", response_time)
                    else:
                        self.log_test(f"Language - {lang_name}", False, "Localization not detected")
                else:
                    self.log_test(f"Language - {lang_name}", False, f"HTTP {response.status_code}")
            except Exception as e:
                self.log_test(f"Language - {lang_name}", False, f"Error: {str(e)}")
    
    def run_all_tests(self):
        """运行所有测试"""
        logger.info("🚀 开始全面系统测试")
        start_time = time.time()
        
        # 运行所有测试模块
        self.test_health_endpoints()
        self.test_authentication_system()
        self.test_api_endpoints()
        self.test_mining_calculation()
        self.test_frontend_pages()
        self.test_real_time_data()
        self.test_multilingual_support()
        
        # 计算总体结果
        total_time = time.time() - start_time
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r['success'])
        success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        
        # 生成报告
        self.generate_report(total_time, total_tests, passed_tests, success_rate)
        
        return success_rate >= 80  # 80%以上通过率算成功
    
    def generate_report(self, total_time, total_tests, passed_tests, success_rate):
        """生成测试报告"""
        logger.info("\n" + "="*60)
        logger.info("📊 测试报告摘要")
        logger.info("="*60)
        logger.info(f"总测试数量: {total_tests}")
        logger.info(f"通过测试: {passed_tests}")
        logger.info(f"失败测试: {total_tests - passed_tests}")
        logger.info(f"成功率: {success_rate:.1f}%")
        logger.info(f"总耗时: {total_time:.2f}秒")
        
        # 系统等级评估
        if success_rate >= 95:
            grade = "A+ 完美级别"
        elif success_rate >= 90:
            grade = "A 优秀级别"
        elif success_rate >= 80:
            grade = "B+ 良好级别"
        elif success_rate >= 70:
            grade = "B 合格级别"
        else:
            grade = "C 需要改进"
        
        logger.info(f"系统等级: {grade}")
        
        # 保存详细报告
        report_file = f"system_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump({
                "summary": {
                    "total_tests": total_tests,
                    "passed_tests": passed_tests,
                    "success_rate": success_rate,
                    "grade": grade,
                    "total_time": total_time,
                    "timestamp": datetime.now().isoformat()
                },
                "test_results": self.test_results
            }, f, indent=2, ensure_ascii=False)
        
        logger.info(f"详细报告已保存: {report_file}")

if __name__ == "__main__":
    tester = BTCMiningCalculatorTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)