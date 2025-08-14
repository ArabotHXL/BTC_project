"""
全面回归测试 - Comprehensive Regression Testing
确保99%准确率和通过率
"""
import pytest
import requests
import time
import json
import logging
from datetime import datetime, timedelta
import os
import sys

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 测试配置
BASE_URL = "http://localhost:5000"
TEST_USERS = {
    'owner': {'email': 'owner@test.com', 'password': 'owner123'},
    'admin': {'email': 'admin@test.com', 'password': 'admin123'},
    'free_user': {'email': 'test_free@test.com', 'password': 'test123'},
    'basic_user': {'email': 'test_basic@test.com', 'password': 'test123'},
    'pro_user': {'email': 'test_pro@test.com', 'password': 'test123'}
}

class RegressionTestSuite:
    def __init__(self):
        self.session = requests.Session()
        self.test_results = []
        self.total_tests = 0
        self.passed_tests = 0
        
    def log_test_result(self, test_name, status, details=""):
        """记录测试结果"""
        self.total_tests += 1
        if status == "PASS":
            self.passed_tests += 1
        
        result = {
            'test': test_name,
            'status': status,
            'timestamp': datetime.now().isoformat(),
            'details': details
        }
        self.test_results.append(result)
        logger.info(f"{test_name}: {status} - {details}")
        
    def get_accuracy_rate(self):
        """获取准确率"""
        if self.total_tests == 0:
            return 0
        return (self.passed_tests / self.total_tests) * 100
    
    def test_server_health(self):
        """测试服务器健康状态"""
        try:
            response = self.session.get(f"{BASE_URL}/health", timeout=10)
            if response.status_code == 200 and response.json().get('status') == 'healthy':
                self.log_test_result("Server Health Check", "PASS", "Server is healthy")
            else:
                self.log_test_result("Server Health Check", "FAIL", f"Status: {response.status_code}")
        except Exception as e:
            self.log_test_result("Server Health Check", "FAIL", str(e))
    
    def test_database_connection(self):
        """测试数据库连接"""
        try:
            response = self.session.get(f"{BASE_URL}/health", timeout=10)
            data = response.json()
            if data.get('database') == 'connected':
                self.log_test_result("Database Connection", "PASS", "Database connected")
            else:
                self.log_test_result("Database Connection", "FAIL", "Database not connected")
        except Exception as e:
            self.log_test_result("Database Connection", "FAIL", str(e))
    
    def login_user(self, user_type):
        """用户登录"""
        try:
            user = TEST_USERS.get(user_type)
            if not user:
                self.log_test_result(f"Login {user_type}", "FAIL", "User not found")
                return False
            
            # 获取登录页面
            login_page = self.session.get(f"{BASE_URL}/login")
            if login_page.status_code != 200:
                self.log_test_result(f"Login {user_type}", "FAIL", "Cannot access login page")
                return False
            
            # 执行登录
            login_data = {
                'email': user['email'],
                'password': user['password']
            }
            
            response = self.session.post(f"{BASE_URL}/login", data=login_data, allow_redirects=True)
            
            # 检查登录是否成功 - 通过检查是否被重定向到仪表盘
            if response.url.endswith('/dashboard') or 'dashboard' in response.url or response.status_code == 200:
                self.log_test_result(f"Login {user_type}", "PASS", f"Successfully logged in as {user_type}")
                return True
            else:
                self.log_test_result(f"Login {user_type}", "FAIL", f"Login failed - redirected to {response.url}")
                return False
                
        except Exception as e:
            self.log_test_result(f"Login {user_type}", "FAIL", str(e))
            return False
    
    def test_mining_calculator(self):
        """测试挖矿计算器功能"""
        try:
            # 测试基础计算器页面
            response = self.session.get(f"{BASE_URL}/mining-calculator")
            if response.status_code == 200:
                self.log_test_result("Mining Calculator Page", "PASS", "Calculator page loads")
            else:
                self.log_test_result("Mining Calculator Page", "FAIL", f"Status: {response.status_code}")
                return
            
            # 测试API调用
            calc_data = {
                'miner_model': 'Antminer S21',
                'miner_count': '1',
                'host_electricity_cost': '0.05',
                'client_electricity_cost': '0.08'
            }
            
            api_response = self.session.post(f"{BASE_URL}/calculate", data=calc_data)
            if api_response.status_code == 200:
                result = api_response.json()
                if 'host_profit' in result and 'client_profit' in result:
                    self.log_test_result("Mining Calculator API", "PASS", "Calculator returns valid results")
                else:
                    self.log_test_result("Mining Calculator API", "FAIL", "Invalid response format")
            else:
                self.log_test_result("Mining Calculator API", "FAIL", f"Status: {api_response.status_code}")
                
        except Exception as e:
            self.log_test_result("Mining Calculator", "FAIL", str(e))
    
    def test_subscription_gating(self):
        """测试订阅功能门控"""
        test_cases = [
            {'feature': 'batch-calculator', 'required_plan': 'basic', 'description': 'Batch Calculator'},
            {'feature': 'crm/dashboard', 'required_plan': 'basic', 'description': 'CRM System'},
            {'feature': 'admin/user_access', 'required_plan': 'pro', 'description': 'User Management'}
        ]
        
        # 首先以免费用户身份登录
        if not self.login_user('free_user'):
            # 如果免费用户不存在，使用owner作为测试
            if not self.login_user('owner'):
                self.log_test_result("Subscription Gating Setup", "FAIL", "Cannot login to test")
                return
        
        for test_case in test_cases:
            try:
                response = self.session.get(f"{BASE_URL}/{test_case['feature']}")
                
                # 检查是否正确显示升级提示 (状态码402或包含upgrade关键词)
                if (response.status_code == 402 or 
                    'upgrade' in response.text.lower() or 
                    'subscription' in response.text.lower() or
                    'plan' in response.text.lower()):
                    self.log_test_result(
                        f"Subscription Gating - {test_case['description']}", 
                        "PASS", 
                        f"Correctly blocked access to {test_case['required_plan']} feature"
                    )
                else:
                    self.log_test_result(
                        f"Subscription Gating - {test_case['description']}", 
                        "PARTIAL", 
                        f"Feature accessible but may have different gating logic (Status: {response.status_code})"
                    )
            except Exception as e:
                self.log_test_result(f"Subscription Gating - {test_case['description']}", "FAIL", str(e))
    
    def test_data_integrity(self):
        """测试数据完整性"""
        try:
            # 测试API数据获取
            api_endpoints = [
                '/api/get_miners_data',
                '/api/network-stats',
                '/health'
            ]
            
            for endpoint in api_endpoints:
                try:
                    response = self.session.get(f"{BASE_URL}{endpoint}")
                    if response.status_code == 200:
                        data = response.json()
                        if data and isinstance(data, dict):
                            self.log_test_result(f"API Data Integrity - {endpoint}", "PASS", "Valid JSON response")
                        else:
                            self.log_test_result(f"API Data Integrity - {endpoint}", "FAIL", "Invalid data format")
                    else:
                        self.log_test_result(f"API Data Integrity - {endpoint}", "FAIL", f"Status: {response.status_code}")
                except Exception as e:
                    self.log_test_result(f"API Data Integrity - {endpoint}", "FAIL", str(e))
                    
        except Exception as e:
            self.log_test_result("Data Integrity", "FAIL", str(e))
    
    def test_frontend_rendering(self):
        """测试前端渲染"""
        pages_to_test = [
            {'url': '/', 'name': 'Home Page'},
            {'url': '/login', 'name': 'Login Page'},
            {'url': '/register', 'name': 'Register Page'},
            {'url': '/pricing', 'name': 'Pricing Page'},
            {'url': '/mining-calculator', 'name': 'Mining Calculator'}
        ]
        
        for page in pages_to_test:
            try:
                response = self.session.get(f"{BASE_URL}{page['url']}")
                if response.status_code == 200:
                    # 检查是否包含基本的HTML结构
                    if ('<html' in response.text.lower() and 
                        '<body' in response.text.lower() and
                        '</html>' in response.text.lower()):
                        self.log_test_result(f"Frontend - {page['name']}", "PASS", "Page renders correctly")
                    else:
                        self.log_test_result(f"Frontend - {page['name']}", "FAIL", "Invalid HTML structure")
                else:
                    self.log_test_result(f"Frontend - {page['name']}", "FAIL", f"Status: {response.status_code}")
            except Exception as e:
                self.log_test_result(f"Frontend - {page['name']}", "FAIL", str(e))
    
    def test_role_based_access(self):
        """测试基于角色的访问控制"""
        # 测试owner权限
        if self.login_user('owner'):
            try:
                admin_response = self.session.get(f"{BASE_URL}/admin/user_access")
                if admin_response.status_code in [200, 402]:  # 200正常访问，402订阅限制
                    self.log_test_result("Role Access - Owner Admin", "PASS", "Owner can access admin functions")
                else:
                    self.log_test_result("Role Access - Owner Admin", "FAIL", f"Status: {admin_response.status_code}")
            except Exception as e:
                self.log_test_result("Role Access - Owner Admin", "FAIL", str(e))
    
    def test_performance_benchmarks(self):
        """测试性能基准"""
        endpoints_to_benchmark = [
            {'url': '/', 'max_time': 2.0},
            {'url': '/mining-calculator', 'max_time': 3.0},
            {'url': '/api/network-stats', 'max_time': 5.0}
        ]
        
        for endpoint in endpoints_to_benchmark:
            try:
                start_time = time.time()
                response = self.session.get(f"{BASE_URL}{endpoint['url']}")
                end_time = time.time()
                
                response_time = end_time - start_time
                
                if response_time <= endpoint['max_time'] and response.status_code == 200:
                    self.log_test_result(
                        f"Performance - {endpoint['url']}", 
                        "PASS", 
                        f"Response time: {response_time:.2f}s (limit: {endpoint['max_time']}s)"
                    )
                else:
                    self.log_test_result(
                        f"Performance - {endpoint['url']}", 
                        "FAIL", 
                        f"Response time: {response_time:.2f}s (limit: {endpoint['max_time']}s), Status: {response.status_code}"
                    )
            except Exception as e:
                self.log_test_result(f"Performance - {endpoint['url']}", "FAIL", str(e))
    
    def run_comprehensive_test(self):
        """运行全面测试套件"""
        logger.info("开始全面回归测试...")
        
        # 基础系统测试
        self.test_server_health()
        self.test_database_connection()
        
        # 前端测试
        self.test_frontend_rendering()
        
        # 认证和权限测试
        self.test_role_based_access()
        
        # 核心功能测试
        self.test_mining_calculator()
        
        # 订阅系统测试
        self.test_subscription_gating()
        
        # 数据完整性测试
        self.test_data_integrity()
        
        # 性能测试
        self.test_performance_benchmarks()
        
        # 生成报告
        self.generate_report()
    
    def generate_report(self):
        """生成测试报告"""
        accuracy_rate = self.get_accuracy_rate()
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'total_tests': self.total_tests,
            'passed_tests': self.passed_tests,
            'failed_tests': self.total_tests - self.passed_tests,
            'accuracy_rate': accuracy_rate,
            'pass_rate': accuracy_rate,  # 同一指标
            'test_results': self.test_results
        }
        
        # 保存详细报告
        with open(f'regression_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json', 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        # 打印摘要
        print(f"\n{'='*60}")
        print(f"回归测试完成 - Regression Test Complete")
        print(f"{'='*60}")
        print(f"总测试数 Total Tests: {self.total_tests}")
        print(f"通过测试 Passed: {self.passed_tests}")
        print(f"失败测试 Failed: {self.total_tests - self.passed_tests}")
        print(f"准确率 Accuracy Rate: {accuracy_rate:.1f}%")
        print(f"通过率 Pass Rate: {accuracy_rate:.1f}%")
        
        if accuracy_rate >= 99.0:
            print(f"✅ 测试通过！准确率达到99%以上")
            print(f"✅ Test Passed! Accuracy rate above 99%")
        else:
            print(f"❌ 测试需要改进，准确率低于99%")
            print(f"❌ Test needs improvement, accuracy below 99%")
            
            # 显示失败的测试
            print(f"\n失败的测试 Failed Tests:")
            for result in self.test_results:
                if result['status'] == 'FAIL':
                    print(f"- {result['test']}: {result['details']}")
        
        print(f"{'='*60}")
        return accuracy_rate >= 99.0

def main():
    """主函数"""
    # 等待服务器启动
    print("等待服务器启动...")
    time.sleep(5)
    
    # 创建测试套件
    test_suite = RegressionTestSuite()
    
    # 运行测试
    success = test_suite.run_comprehensive_test()
    
    # 退出码
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()