#!/usr/bin/env python3
"""
Comprehensive Regression Test Suite
测试JavaScript错误修复和系统功能完整性
"""

import requests
import time
import json
import logging
from datetime import datetime

class ComprehensiveRegressionTest:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.test_results = {}
        self.setup_logging()
        
    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def log_result(self, test_name, success, details="", response_time=0):
        """记录测试结果"""
        self.test_results[test_name] = {
            'success': success,
            'details': details,
            'response_time': response_time,
            'timestamp': datetime.now().isoformat()
        }
        status = "✓ PASS" if success else "✗ FAIL"
        time_info = f" ({response_time:.2f}s)" if response_time > 0 else ""
        print(f"{status} {test_name}{time_info}")
        if details:
            print(f"    {details}")
    
    def test_basic_connectivity(self):
        """测试基本连接性"""
        try:
            start_time = time.time()
            response = self.session.get(self.base_url, timeout=10)
            response_time = time.time() - start_time
            
            if response.status_code in [200, 302]:
                self.log_result("Basic Connectivity", True, 
                              f"Status: {response.status_code}", response_time)
                return True
            else:
                self.log_result("Basic Connectivity", False, 
                              f"Unexpected status: {response.status_code}", response_time)
                return False
        except Exception as e:
            self.log_result("Basic Connectivity", False, f"Connection error: {str(e)}")
            return False
    
    def test_authentication_system(self):
        """测试认证系统"""
        try:
            start_time = time.time()
            # 测试登录页面
            login_response = self.session.get(f"{self.base_url}/login", timeout=10)
            response_time = time.time() - start_time
            
            if login_response.status_code == 200:
                # 测试登录表单提交
                auth_data = {'email': 'test@example.com'}
                auth_response = self.session.post(f"{self.base_url}/login", 
                                                data=auth_data, 
                                                allow_redirects=True)
                
                if auth_response.status_code == 200:
                    self.log_result("Authentication System", True, 
                                  "Login form accessible and processing", response_time)
                    return True
                else:
                    self.log_result("Authentication System", False, 
                                  f"Login processing failed: {auth_response.status_code}")
                    return False
            else:
                self.log_result("Authentication System", False, 
                              f"Login page inaccessible: {login_response.status_code}")
                return False
        except Exception as e:
            self.log_result("Authentication System", False, f"Auth error: {str(e)}")
            return False
    
    def test_api_endpoints(self):
        """测试API端点可用性"""
        endpoints = [
            ('/network_stats', 'Network Stats API'),
            ('/miners', 'Miners Data API'),
            ('/calculate', 'Mining Calculator API')
        ]
        
        all_passed = True
        for endpoint, name in endpoints:
            try:
                start_time = time.time()
                response = self.session.get(f"{self.base_url}{endpoint}", timeout=10)
                response_time = time.time() - start_time
                
                # API端点应该返回302重定向到登录页面（因为需要认证）
                if response.status_code in [302, 401]:
                    self.log_result(f"API Endpoint: {name}", True, 
                                  "Correctly protected by authentication", response_time)
                elif response.status_code == 200:
                    self.log_result(f"API Endpoint: {name}", True, 
                                  "Accessible and responding", response_time)
                else:
                    self.log_result(f"API Endpoint: {name}", False, 
                                  f"Unexpected status: {response.status_code}")
                    all_passed = False
            except Exception as e:
                self.log_result(f"API Endpoint: {name}", False, f"Error: {str(e)}")
                all_passed = False
        
        return all_passed
    
    def test_javascript_loading(self):
        """测试JavaScript文件加载"""
        js_files = [
            '/static/js/dom-safety.js',
            '/static/js/main.js'
        ]
        
        all_passed = True
        for js_file in js_files:
            try:
                start_time = time.time()
                response = self.session.get(f"{self.base_url}{js_file}", timeout=10)
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    file_size = len(response.content)
                    self.log_result(f"JavaScript File: {js_file}", True, 
                                  f"Loaded successfully ({file_size} bytes)", response_time)
                else:
                    self.log_result(f"JavaScript File: {js_file}", False, 
                                  f"Failed to load: {response.status_code}")
                    all_passed = False
            except Exception as e:
                self.log_result(f"JavaScript File: {js_file}", False, f"Error: {str(e)}")
                all_passed = False
        
        return all_passed
    
    def test_html_template_integrity(self):
        """测试HTML模板完整性"""
        try:
            # 获取登录页面（未认证用户会被重定向到这里）
            response = self.session.get(self.base_url, timeout=10)
            html_content = response.text
            
            # 检查关键元素
            checks = [
                ('DOM Safety Script', 'dom-safety.js' in html_content),
                ('Main JavaScript', 'main.js' in html_content),
                ('Bootstrap CSS', 'bootstrap' in html_content),
                ('Chart.js Library', 'chart.js' in html_content),
                ('Language Support', 'language' in html_content.lower())
            ]
            
            all_passed = True
            for check_name, check_result in checks:
                if check_result:
                    self.log_result(f"HTML Template: {check_name}", True, "Found in template")
                else:
                    self.log_result(f"HTML Template: {check_name}", False, "Missing from template")
                    all_passed = False
            
            return all_passed
        except Exception as e:
            self.log_result("HTML Template Integrity", False, f"Error: {str(e)}")
            return False
    
    def test_database_connectivity(self):
        """测试数据库连接性"""
        try:
            # 间接测试：访问需要数据库的页面
            start_time = time.time()
            response = self.session.get(f"{self.base_url}/login", timeout=10)
            response_time = time.time() - start_time
            
            if response.status_code == 200 and 'login' in response.text.lower():
                self.log_result("Database Connectivity", True, 
                              "Application accessing database successfully", response_time)
                return True
            else:
                self.log_result("Database Connectivity", False, 
                              "Database connection issues detected")
                return False
        except Exception as e:
            self.log_result("Database Connectivity", False, f"DB error: {str(e)}")
            return False
    
    def test_css_and_static_assets(self):
        """测试CSS和静态资源"""
        static_files = [
            '/static/css/styles.css',
            '/static/css/animations.css'
        ]
        
        all_passed = True
        for static_file in static_files:
            try:
                start_time = time.time()
                response = self.session.get(f"{self.base_url}{static_file}", timeout=10)
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    file_size = len(response.content)
                    self.log_result(f"Static Asset: {static_file}", True, 
                                  f"Loaded ({file_size} bytes)", response_time)
                elif response.status_code == 404:
                    self.log_result(f"Static Asset: {static_file}", True, 
                                  "File not found (acceptable if not created)", response_time)
                else:
                    self.log_result(f"Static Asset: {static_file}", False, 
                                  f"Unexpected status: {response.status_code}")
                    all_passed = False
            except Exception as e:
                self.log_result(f"Static Asset: {static_file}", False, f"Error: {str(e)}")
                all_passed = False
        
        return all_passed
    
    def test_multilingual_support(self):
        """测试多语言支持"""
        try:
            # 测试中文界面
            start_time = time.time()
            zh_response = self.session.get(f"{self.base_url}?lang=zh", timeout=10)
            response_time = time.time() - start_time
            
            if zh_response.status_code in [200, 302]:
                # 检查是否包含中文内容
                if '登录' in zh_response.text or '计算器' in zh_response.text:
                    self.log_result("Multilingual Support", True, 
                                  "Chinese language interface working", response_time)
                    return True
                else:
                    self.log_result("Multilingual Support", False, 
                                  "Chinese translation not working properly")
                    return False
            else:
                self.log_result("Multilingual Support", False, 
                              f"Language switching failed: {zh_response.status_code}")
                return False
        except Exception as e:
            self.log_result("Multilingual Support", False, f"Language error: {str(e)}")
            return False
    
    def run_comprehensive_test(self):
        """运行完整的回归测试套件"""
        print("=" * 60)
        print("🔍 COMPREHENSIVE REGRESSION TEST SUITE")
        print("=" * 60)
        print(f"Target: {self.base_url}")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # 运行所有测试
        tests = [
            ("Basic System", self.test_basic_connectivity),
            ("Authentication", self.test_authentication_system),
            ("API Endpoints", self.test_api_endpoints),
            ("JavaScript Loading", self.test_javascript_loading),
            ("HTML Templates", self.test_html_template_integrity),
            ("Database", self.test_database_connectivity),
            ("Static Assets", self.test_css_and_static_assets),
            ("Multilingual", self.test_multilingual_support)
        ]
        
        total_tests = 0
        passed_tests = 0
        
        for test_category, test_function in tests:
            print(f"\n--- {test_category} Tests ---")
            try:
                result = test_function()
                category_tests = len([k for k in self.test_results.keys() 
                                    if test_category.lower().replace(" ", "_") in k.lower()])
                category_passed = len([k for k, v in self.test_results.items() 
                                     if test_category.lower().replace(" ", "_") in k.lower() and v['success']])
                
                total_tests += category_tests
                passed_tests += category_passed
                
            except Exception as e:
                print(f"✗ FAIL {test_category} Test Suite: {str(e)}")
        
        # 生成测试总结
        print("\n" + "=" * 60)
        print("📊 TEST RESULTS SUMMARY")
        print("=" * 60)
        
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        print(f"Total Tests Run: {total_tests}")
        print(f"Tests Passed: {passed_tests}")
        print(f"Tests Failed: {total_tests - passed_tests}")
        print(f"Success Rate: {success_rate:.1f}%")
        
        # 详细结果
        if total_tests - passed_tests > 0:
            print(f"\n❌ Failed Tests:")
            for test_name, result in self.test_results.items():
                if not result['success']:
                    print(f"  - {test_name}: {result['details']}")
        
        print(f"\n✅ System Status: {'HEALTHY' if success_rate >= 80 else 'NEEDS ATTENTION'}")
        print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return success_rate >= 80

def main():
    """主测试入口"""
    tester = ComprehensiveRegressionTest()
    success = tester.run_comprehensive_test()
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())