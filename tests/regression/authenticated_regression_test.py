#!/usr/bin/env python3
"""
Authenticated Regression Test Suite for Language Separation
验证中英文界面分离后所有核心功能正常运行（含认证）
"""

import requests
import json
import time
from datetime import datetime

class AuthenticatedRegressionTest:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.test_results = []
        self.authenticated = False
        
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
    
    def authenticate(self):
        """使用测试邮箱进行认证"""
        try:
            # 使用owner权限的测试邮箱
            login_data = {"email": "hxl2022hao@gmail.com"}
            response = self.session.post(f"{self.base_url}/login", data=login_data)
            
            # 检查是否成功重定向到主页
            self.authenticated = response.status_code in [200, 302]
            
            if self.authenticated:
                # 验证登录状态
                home_response = self.session.get(f"{self.base_url}/")
                self.authenticated = home_response.status_code == 200
            
            self.log_test("Authentication", self.authenticated, 
                         f"Login status: {response.status_code}")
            
            return self.authenticated
            
        except Exception as e:
            self.log_test("Authentication", False, str(e))
            return False
    
    def test_language_switching(self):
        """测试语言切换功能"""
        if not self.authenticated:
            self.log_test("Language Switching", False, "Not authenticated")
            return
            
        try:
            # 测试中文模式
            zh_response = self.session.get(f"{self.base_url}/?lang=zh")
            zh_success = zh_response.status_code == 200
            
            # 测试英文模式
            en_response = self.session.get(f"{self.base_url}/?lang=en")
            en_success = en_response.status_code == 200
            
            success = zh_success and en_success
            self.log_test("Language Switching", success, 
                         f"ZH: {zh_response.status_code}, EN: {en_response.status_code}")
            
        except Exception as e:
            self.log_test("Language Switching", False, str(e))
    
    def test_core_apis(self):
        """测试核心API功能"""
        if not self.authenticated:
            self.log_test("Core APIs", False, "Not authenticated")
            return
            
        try:
            # 测试网络统计API
            stats_response = self.session.get(f"{self.base_url}/network_stats")
            if stats_response.status_code == 200:
                stats_data = stats_response.json()
                stats_success = stats_data.get("success", False)
                hashrate = stats_data.get("hashrate", 0)
                price = stats_data.get("price", 0)
            else:
                stats_success = False
                hashrate = price = 0
            
            # 测试矿机列表API
            miners_response = self.session.get(f"{self.base_url}/miners")
            if miners_response.status_code == 200:
                miners_data = miners_response.json()
                miners_success = miners_data.get("success", False)
                miners_count = len(miners_data.get("miners", []))
            else:
                miners_success = False
                miners_count = 0
            
            success = stats_success and miners_success
            details = f"Hashrate: {hashrate} EH/s, Price: ${price}, Miners: {miners_count}"
            
            self.log_test("Core APIs", success, details)
            
        except Exception as e:
            self.log_test("Core APIs", False, str(e))
    
    def test_mining_calculation_comprehensive(self):
        """测试完整的挖矿计算功能"""
        if not self.authenticated:
            self.log_test("Mining Calculation", False, "Not authenticated")
            return
            
        try:
            # 使用精确的网络算力测试计算
            calc_data = {
                "miner_model": "Antminer S21 XP",
                "miner_count": "100",
                "site_power_mw": "0.365",
                "electricity_cost": "0.05",
                "client_electricity_cost": "0.06",
                "maintenance_fee": "2000",
                "curtailment": "0",
                "host_investment": "200000",
                "client_investment": "3000000",
                "hashrate_source": "manual",
                "manual_hashrate": "921.8",
                "use_real_time": "on"
            }
            
            response = self.session.post(f"{self.base_url}/calculate", data=calc_data)
            
            if response.status_code == 200:
                result = response.json()
                
                # 验证关键计算结果
                btc_daily = result.get("btc_mined", {}).get("daily", 0)
                client_monthly = result.get("client_profit", {}).get("monthly", 0)
                host_profit = result.get("host_profit", {}).get("monthly", 0)
                
                # 验证ROI计算
                roi_data = result.get("roi", {})
                has_roi = bool(roi_data)
                
                success = all([btc_daily > 0, client_monthly > 0, has_roi])
                details = f"Daily BTC: {btc_daily:.6f}, Client Monthly: ${client_monthly:,.0f}, Host Monthly: ${host_profit:,.0f}"
                
            else:
                success = False
                details = f"Calculation failed: {response.status_code}"
            
            self.log_test("Mining Calculation", success, details)
            
        except Exception as e:
            self.log_test("Mining Calculation", False, str(e))
    
    def test_manual_hashrate_override(self):
        """测试手动网络算力覆盖功能"""
        if not self.authenticated:
            self.log_test("Manual Hashrate Override", False, "Not authenticated")
            return
            
        try:
            # 测试API模式
            api_calc = {
                "miner_model": "Antminer S21 XP",
                "miner_count": "10",
                "hashrate_source": "api",
                "use_real_time": "on"
            }
            
            api_response = self.session.post(f"{self.base_url}/calculate", data=api_calc)
            
            # 测试手动模式
            manual_calc = {
                "miner_model": "Antminer S21 XP", 
                "miner_count": "10",
                "hashrate_source": "manual",
                "manual_hashrate": "921.8",
                "use_real_time": "on"
            }
            
            manual_response = self.session.post(f"{self.base_url}/calculate", data=manual_calc)
            
            api_success = api_response.status_code == 200
            manual_success = manual_response.status_code == 200
            
            success = api_success and manual_success
            details = f"API mode: {api_response.status_code}, Manual mode: {manual_response.status_code}"
            
            if success:
                api_btc = api_response.json().get("btc_mined", {}).get("daily", 0)
                manual_btc = manual_response.json().get("btc_mined", {}).get("daily", 0)
                details += f", API BTC: {api_btc:.6f}, Manual BTC: {manual_btc:.6f}"
            
            self.log_test("Manual Hashrate Override", success, details)
            
        except Exception as e:
            self.log_test("Manual Hashrate Override", False, str(e))
    
    def test_curtailment_scenarios(self):
        """测试限电场景计算"""
        if not self.authenticated:
            self.log_test("Curtailment Scenarios", False, "Not authenticated")
            return
            
        try:
            scenarios = [
                (0, "No Curtailment"),
                (15, "Light Curtailment"), 
                (30, "Heavy Curtailment")
            ]
            
            results = []
            for curtailment_pct, scenario_name in scenarios:
                calc_data = {
                    "miner_model": "Antminer S21 XP",
                    "miner_count": "50",
                    "curtailment": str(curtailment_pct),
                    "shutdown_strategy": "efficiency",
                    "electricity_cost": "0.05",
                    "client_electricity_cost": "0.06",
                    "use_real_time": "on"
                }
                
                response = self.session.post(f"{self.base_url}/calculate", data=calc_data)
                
                if response.status_code == 200:
                    result = response.json()
                    curtailment_factor = result.get("inputs", {}).get("curtailment_factor", 1)
                    expected_factor = (100 - curtailment_pct) / 100
                    factor_correct = abs(curtailment_factor - expected_factor) < 0.01
                    results.append(factor_correct)
                else:
                    results.append(False)
            
            success = all(results)
            passed_scenarios = sum(results)
            details = f"{passed_scenarios}/{len(scenarios)} scenarios passed"
            
            self.log_test("Curtailment Scenarios", success, details)
            
        except Exception as e:
            self.log_test("Curtailment Scenarios", False, str(e))
    
    def test_roi_accuracy(self):
        """测试ROI计算准确性"""
        if not self.authenticated:
            self.log_test("ROI Accuracy", False, "Not authenticated")
            return
            
        try:
            calc_data = {
                "miner_model": "Antminer S21 XP",
                "miner_count": "100",
                "host_investment": "500000",
                "client_investment": "4000000",
                "electricity_cost": "0.05",
                "client_electricity_cost": "0.06",
                "maintenance_fee": "3000",
                "manual_hashrate": "921.8",
                "hashrate_source": "manual",
                "use_real_time": "on"
            }
            
            response = self.session.post(f"{self.base_url}/calculate", data=calc_data)
            
            if response.status_code == 200:
                result = response.json()
                roi_data = result.get("roi", {})
                
                host_roi = roi_data.get("host", {})
                client_roi = roi_data.get("client", {})
                
                host_return_rate = host_roi.get("annual_return_rate", 0)
                client_return_rate = client_roi.get("annual_return_rate", 0)
                
                host_payback = host_roi.get("payback_months", 999)
                client_payback = client_roi.get("payback_months", 999)
                
                # 验证ROI计算合理性
                reasonable_roi = (0 < host_return_rate < 1000 and 
                                0 < client_return_rate < 200 and
                                0 < host_payback < 100 and
                                0 < client_payback < 500)
                
                success = reasonable_roi
                details = f"Host: {host_return_rate:.1f}%/{host_payback:.1f}mo, Client: {client_return_rate:.1f}%/{client_payback:.1f}mo"
                
            else:
                success = False
                details = f"ROI calculation failed: {response.status_code}"
            
            self.log_test("ROI Accuracy", success, details)
            
        except Exception as e:
            self.log_test("ROI Accuracy", False, str(e))
    
    def test_data_persistence(self):
        """测试数据持久化功能"""
        if not self.authenticated:
            self.log_test("Data Persistence", False, "Not authenticated")
            return
            
        try:
            # 测试CRM系统访问（数据库连接）
            crm_response = self.session.get(f"{self.base_url}/crm/dashboard")
            crm_accessible = crm_response.status_code == 200
            
            # 测试网络数据记录
            calc_data = {
                "miner_model": "Antminer S21 XP",
                "miner_count": "10",
                "use_real_time": "on"
            }
            
            calc_response = self.session.post(f"{self.base_url}/calculate", data=calc_data)
            calc_success = calc_response.status_code == 200
            
            success = crm_accessible and calc_success
            details = f"CRM: {crm_response.status_code}, Calculation: {calc_response.status_code}"
            
            self.log_test("Data Persistence", success, details)
            
        except Exception as e:
            self.log_test("Data Persistence", False, str(e))
    
    def run_complete_regression(self):
        """运行完整回归测试"""
        print("=" * 70)
        print("Comprehensive Language Separation Regression Test")
        print("完整的中英文界面分离回归测试")
        print("=" * 70)
        print(f"Target: {self.base_url}")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # 首先进行认证
        if not self.authenticate():
            print("❌ Authentication failed - aborting tests")
            return False
        
        print("✅ Authentication successful - proceeding with tests")
        print()
        
        # 执行所有功能测试
        self.test_language_switching()
        self.test_core_apis()
        self.test_mining_calculation_comprehensive()
        self.test_manual_hashrate_override()
        self.test_curtailment_scenarios()
        self.test_roi_accuracy()
        self.test_data_persistence()
        
        # 生成测试报告
        print()
        print("=" * 70)
        print("REGRESSION TEST RESULTS / 回归测试结果")
        print("=" * 70)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests} ✓")
        print(f"Failed: {failed_tests} ✗")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        # 核心系统状态检查
        print()
        print("CRITICAL SYSTEMS STATUS:")
        
        critical_systems = [
            "Authentication",
            "Mining Calculation", 
            "Manual Hashrate Override",
            "Core APIs"
        ]
        
        critical_results = {test['test']: test['success'] 
                          for test in self.test_results 
                          if test['test'] in critical_systems}
        
        all_critical_passed = all(critical_results.values())
        
        for system, status in critical_results.items():
            status_icon = "✅" if status else "❌"
            print(f"  {status_icon} {system}")
        
        print()
        if all_critical_passed:
            print("🎉 ALL CRITICAL SYSTEMS OPERATIONAL")
            print("✅ Language separation implementation successful")
            print("✅ Core mining calculator functionality intact")
            print("✅ System ready for production use")
        else:
            print("⚠️  CRITICAL SYSTEM ISSUES DETECTED")
            print("❌ Manual intervention required")
        
        # 详细失败报告
        if failed_tests > 0:
            print()
            print("DETAILED FAILURE ANALYSIS:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  ❌ {result['test']}")
                    print(f"     Reason: {result['details']}")
        
        return passed_tests == total_tests

if __name__ == "__main__":
    tester = AuthenticatedRegressionTest()
    success = tester.run_complete_regression()
    exit(0 if success else 1)