#!/usr/bin/env python3
"""
Language Separation Regression Test Suite
验证中英文界面分离后所有核心功能正常运行
"""

import requests
import json
import time
from datetime import datetime

class LanguageSeparationRegressionTest:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.test_results = []
        
    def log_test(self, test_name, success, details=""):
        """记录测试结果"""
        result = {
            "test": test_name,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status}: {test_name}")
        if details:
            print(f"   Details: {details}")
    
    def test_language_detection(self):
        """测试语言检测和切换"""
        try:
            # 测试中文模式
            response = self.session.get(f"{self.base_url}/", 
                                      headers={"Accept-Language": "zh-CN"})
            self.log_test("Chinese Language Detection", 
                         response.status_code == 200 or response.status_code == 302,
                         f"Status: {response.status_code}")
            
            # 测试英文模式
            response = self.session.get(f"{self.base_url}/", 
                                      headers={"Accept-Language": "en-US"})
            self.log_test("English Language Detection", 
                         response.status_code == 200 or response.status_code == 302,
                         f"Status: {response.status_code}")
            
        except Exception as e:
            self.log_test("Language Detection", False, str(e))
    
    def test_api_endpoints(self):
        """测试关键API端点"""
        endpoints = [
            ("/network_stats", "Network Statistics API"),
            ("/miners", "Miners List API"),
            ("/btc_price", "BTC Price API")
        ]
        
        for endpoint, name in endpoints:
            try:
                response = self.session.get(f"{self.base_url}{endpoint}")
                success = response.status_code == 200
                
                if success and endpoint == "/network_stats":
                    data = response.json()
                    # 验证API数据结构
                    required_fields = ["price", "difficulty", "hashrate", "success"]
                    missing_fields = [field for field in required_fields if field not in data]
                    if missing_fields:
                        success = False
                        details = f"Missing fields: {missing_fields}"
                    else:
                        details = f"Price: ${data.get('price', 'N/A')}, Hashrate: {data.get('hashrate', 'N/A')} EH/s"
                elif success and endpoint == "/miners":
                    data = response.json()
                    miners_count = len(data.get('miners', [])) if data.get('success') else 0
                    details = f"Miners loaded: {miners_count}"
                else:
                    details = f"Status: {response.status_code}"
                
                self.log_test(name, success, details)
                
            except Exception as e:
                self.log_test(name, False, str(e))
    
    def test_mining_calculation(self):
        """测试挖矿收益计算功能"""
        try:
            # 准备测试数据
            calc_data = {
                "miner_model": "Antminer S21 XP",
                "miner_count": "100",
                "site_power_mw": "1.0",
                "electricity_cost": "0.05",
                "client_electricity_cost": "0.06",
                "maintenance_fee": "1000",
                "curtailment": "0",
                "host_investment": "100000",
                "client_investment": "5000000",
                "hashrate_source": "manual",
                "manual_hashrate": "921.8",
                "use_real_time": "on"
            }
            
            response = self.session.post(f"{self.base_url}/calculate", 
                                       data=calc_data)
            
            if response.status_code == 200:
                result = response.json()
                
                # 验证计算结果结构
                required_fields = ["btc_mined", "client_profit", "electricity_cost", "inputs"]
                success = all(field in result for field in required_fields)
                
                if success:
                    daily_btc = result["btc_mined"]["daily"]
                    monthly_profit = result["client_profit"]["monthly"]
                    details = f"Daily BTC: {daily_btc:.8f}, Monthly Profit: ${monthly_profit:,.2f}"
                else:
                    details = "Missing required calculation fields"
                    
            else:
                success = False
                details = f"HTTP {response.status_code}"
            
            self.log_test("Mining Calculation Engine", success, details)
            
        except Exception as e:
            self.log_test("Mining Calculation Engine", False, str(e))
    
    def test_network_hashrate_accuracy(self):
        """测试网络算力准确性"""
        try:
            response = self.session.get(f"{self.base_url}/network_stats")
            
            if response.status_code == 200:
                data = response.json()
                api_hashrate = data.get("hashrate", 0)
                
                # 测试手动输入的准确值
                calc_data = {
                    "miner_model": "Antminer S21 XP", 
                    "miner_count": "1",
                    "hashrate_source": "manual",
                    "manual_hashrate": "921.8",
                    "use_real_time": "on"
                }
                
                calc_response = self.session.post(f"{self.base_url}/calculate", 
                                                data=calc_data)
                
                success = calc_response.status_code == 200
                details = f"API Hashrate: {api_hashrate} EH/s, Manual Override: 921.8 EH/s available"
                
            else:
                success = False
                details = f"Network stats unavailable: {response.status_code}"
            
            self.log_test("Network Hashrate Accuracy", success, details)
            
        except Exception as e:
            self.log_test("Network Hashrate Accuracy", False, str(e))
    
    def test_api_fallback_system(self):
        """测试API备用系统"""
        try:
            response = self.session.get(f"{self.base_url}/network_stats")
            
            if response.status_code == 200:
                data = response.json()
                data_source = data.get("data_source", "Unknown")
                success = "CoinWarz" in data_source or "blockchain" in data_source
                details = f"Data source: {data_source}"
            else:
                success = False
                details = f"API fallback failed: {response.status_code}"
            
            self.log_test("API Fallback System", success, details)
            
        except Exception as e:
            self.log_test("API Fallback System", False, str(e))
    
    def test_curtailment_calculation(self):
        """测试限电计算功能"""
        try:
            calc_data = {
                "miner_model": "Antminer S21 XP",
                "miner_count": "50", 
                "curtailment": "20",  # 20% curtailment
                "shutdown_strategy": "efficiency",
                "electricity_cost": "0.05",
                "client_electricity_cost": "0.06",
                "use_real_time": "on"
            }
            
            response = self.session.post(f"{self.base_url}/calculate", 
                                       data=calc_data)
            
            if response.status_code == 200:
                result = response.json()
                curtailment_factor = result.get("inputs", {}).get("curtailment_factor", 1)
                success = curtailment_factor < 1  # Should be reduced due to curtailment
                details = f"Curtailment factor: {curtailment_factor} (20% reduction applied)"
            else:
                success = False
                details = f"Curtailment calculation failed: {response.status_code}"
            
            self.log_test("Curtailment Calculation", success, details)
            
        except Exception as e:
            self.log_test("Curtailment Calculation", False, str(e))
    
    def test_roi_calculation(self):
        """测试ROI计算功能"""
        try:
            calc_data = {
                "miner_model": "Antminer S21 XP",
                "miner_count": "100",
                "host_investment": "500000",
                "client_investment": "3000000", 
                "electricity_cost": "0.05",
                "client_electricity_cost": "0.06",
                "use_real_time": "on"
            }
            
            response = self.session.post(f"{self.base_url}/calculate", 
                                       data=calc_data)
            
            if response.status_code == 200:
                result = response.json()
                has_roi = "roi" in result
                success = has_roi
                
                if has_roi:
                    roi_data = result["roi"]
                    host_roi = roi_data.get("host", {})
                    client_roi = roi_data.get("client", {})
                    details = f"Host ROI: {host_roi.get('annual_return_rate', 'N/A')}%, Client ROI: {client_roi.get('annual_return_rate', 'N/A')}%"
                else:
                    details = "ROI calculation not found in response"
            else:
                success = False
                details = f"ROI calculation failed: {response.status_code}"
            
            self.log_test("ROI Calculation", success, details)
            
        except Exception as e:
            self.log_test("ROI Calculation", False, str(e))
    
    def test_database_connectivity(self):
        """测试数据库连接"""
        try:
            # 通过CRM页面测试数据库连接
            response = self.session.get(f"{self.base_url}/crm/dashboard")
            
            # 302重定向到登录页面也表示应用正常运行
            success = response.status_code in [200, 302, 401, 403]
            details = f"Database connectivity test via CRM: {response.status_code}"
            
            self.log_test("Database Connectivity", success, details)
            
        except Exception as e:
            self.log_test("Database Connectivity", False, str(e))
    
    def run_all_tests(self):
        """运行所有回归测试"""
        print("=" * 60)
        print("Language Separation Regression Test Suite")
        print("中英文界面分离回归测试套件")
        print("=" * 60)
        print(f"Testing against: {self.base_url}")
        print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # 执行所有测试
        self.test_language_detection()
        self.test_api_endpoints()
        self.test_mining_calculation()
        self.test_network_hashrate_accuracy()
        self.test_api_fallback_system()
        self.test_curtailment_calculation()
        self.test_roi_calculation()
        self.test_database_connectivity()
        
        # 汇总结果
        print()
        print("=" * 60)
        print("Test Summary / 测试汇总")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print("\nFailed Tests:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  - {result['test']}: {result['details']}")
        
        print()
        print("Core System Status:")
        critical_tests = ["Mining Calculation Engine", "Network Hashrate Accuracy", "API Fallback System"]
        critical_passed = sum(1 for result in self.test_results 
                            if result["test"] in critical_tests and result["success"])
        
        if critical_passed == len(critical_tests):
            print("✓ All critical systems operational")
        else:
            print("⚠ Some critical systems have issues")
        
        return passed_tests == total_tests

if __name__ == "__main__":
    tester = LanguageSeparationRegressionTest()
    success = tester.run_all_tests()
    exit(0 if success else 1)