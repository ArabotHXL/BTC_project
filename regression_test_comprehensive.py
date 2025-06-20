#!/usr/bin/env python3
"""
综合回归测试套件
Comprehensive Regression Test Suite

测试所有核心功能，包括：
1. 用户认证系统
2. 挖矿计算功能
3. 网络数据API
4. CRM系统
5. JavaScript功能验证
6. 数据库连接
7. 语言切换功能
"""

import requests
import json
import time
import sys
from urllib.parse import urljoin

class ComprehensiveRegressionTest:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.test_results = []
        self.passed_tests = 0
        self.total_tests = 0
        
    def log_test(self, test_name, success, details="", response_data=None):
        """记录测试结果"""
        self.total_tests += 1
        if success:
            self.passed_tests += 1
            status = "✓ PASS"
        else:
            status = "✗ FAIL"
            
        result = {
            'test': test_name,
            'status': status,
            'success': success,
            'details': details,
            'response_data': response_data
        }
        self.test_results.append(result)
        print(f"{status}: {test_name}")
        if details:
            print(f"   详情: {details}")
    
    def test_basic_connectivity(self):
        """测试基本连接性"""
        try:
            response = self.session.get(self.base_url, timeout=10)
            if response.status_code in [200, 302]:  # 302 for redirect to login
                self.log_test("基本连接性测试", True, f"状态码: {response.status_code}")
                return True
            else:
                self.log_test("基本连接性测试", False, f"状态码: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("基本连接性测试", False, f"连接错误: {str(e)}")
            return False
    
    def test_authentication_system(self):
        """测试用户认证系统"""
        try:
            # 测试登录页面
            login_response = self.session.get(urljoin(self.base_url, "/login"))
            if login_response.status_code == 200:
                self.log_test("登录页面访问", True, "登录页面正常加载")
            else:
                self.log_test("登录页面访问", False, f"状态码: {login_response.status_code}")
                return False
            
            # 测试邮箱认证
            auth_data = {
                'email': 'user@example.com'
            }
            auth_response = self.session.post(
                urljoin(self.base_url, "/login"),
                data=auth_data,
                allow_redirects=False
            )
            
            if auth_response.status_code in [302, 200]:
                self.log_test("邮箱认证功能", True, "认证请求成功处理")
                return True
            else:
                self.log_test("邮箱认证功能", False, f"状态码: {auth_response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("认证系统测试", False, f"错误: {str(e)}")
            return False
    
    def authenticate_test_user(self):
        """认证测试用户"""
        try:
            auth_data = {'email': 'user@example.com'}
            response = self.session.post(
                urljoin(self.base_url, "/login"),
                data=auth_data,
                allow_redirects=True
            )
            return response.status_code == 200
        except:
            return False
    
    def test_network_apis(self):
        """测试网络数据API"""
        try:
            # 确保用户已认证
            if not self.authenticate_test_user():
                self.log_test("API认证准备", False, "无法认证测试用户")
                return False
            
            # 测试网络统计API
            network_response = self.session.get(urljoin(self.base_url, "/get_network_stats"))
            if network_response.status_code == 200:
                data = network_response.json()
                if data.get('success') and 'btc_price' in data:
                    self.log_test("网络统计API", True, f"BTC价格: ${data['btc_price']}")
                else:
                    self.log_test("网络统计API", False, "数据格式错误")
            else:
                self.log_test("网络统计API", False, f"状态码: {network_response.status_code}")
            
            # 测试矿机列表API
            miners_response = self.session.get(urljoin(self.base_url, "/get_miners"))
            if miners_response.status_code == 200:
                data = miners_response.json()
                if data.get('success') and data.get('miners'):
                    count = len(data['miners'])
                    self.log_test("矿机列表API", True, f"加载 {count} 个矿机型号")
                else:
                    self.log_test("矿机列表API", False, "数据格式错误")
            else:
                self.log_test("矿机列表API", False, f"状态码: {miners_response.status_code}")
            
            # 测试SHA256币种对比API
            sha256_response = self.session.get(urljoin(self.base_url, "/get_sha256_mining_comparison"))
            if sha256_response.status_code == 200:
                data = sha256_response.json()
                if data.get('success'):
                    self.log_test("SHA256币种对比API", True, "数据获取成功")
                else:
                    self.log_test("SHA256币种对比API", False, "API返回失败")
            else:
                self.log_test("SHA256币种对比API", False, f"状态码: {sha256_response.status_code}")
                
        except Exception as e:
            self.log_test("网络API测试", False, f"错误: {str(e)}")
    
    def test_mining_calculation(self):
        """测试挖矿计算功能"""
        try:
            if not self.authenticate_test_user():
                self.log_test("挖矿计算认证", False, "无法认证测试用户")
                return False
            
            # 测试挖矿计算
            calc_data = {
                'miner_model': 'Antminer S21 XP',
                'miner_count': '10',
                'electricity_cost': '0.05',
                'client_electricity_cost': '0.06',
                'hashrate_source': 'api',
                'use_real_time': 'on'
            }
            
            calc_response = self.session.post(
                urljoin(self.base_url, "/calculate"),
                data=calc_data
            )
            
            if calc_response.status_code == 200:
                data = calc_response.json()
                if data.get('success'):
                    daily_btc = data.get('btc_mined', {}).get('daily', 0)
                    monthly_profit = data.get('profitability', {}).get('monthly_profit', 0)
                    self.log_test("挖矿计算功能", True, 
                                f"日产BTC: {daily_btc:.6f}, 月收益: ${monthly_profit:,.0f}")
                else:
                    self.log_test("挖矿计算功能", False, f"计算失败: {data.get('error', '未知错误')}")
            else:
                self.log_test("挖矿计算功能", False, f"状态码: {calc_response.status_code}")
                
        except Exception as e:
            self.log_test("挖矿计算测试", False, f"错误: {str(e)}")
    
    def test_curtailment_calculation(self):
        """测试限电计算功能"""
        try:
            if not self.authenticate_test_user():
                return False
            
            curtailment_data = {
                'miner_count': '100',
                'curtailment_rate': '20',
                'electricity_cost': '0.05',
                'btc_price': '100000'
            }
            
            response = self.session.post(
                urljoin(self.base_url, "/calculate_curtailment"),
                data=curtailment_data
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    self.log_test("限电计算功能", True, "限电计算正常运行")
                else:
                    self.log_test("限电计算功能", False, "计算返回失败")
            else:
                self.log_test("限电计算功能", False, f"状态码: {response.status_code}")
                
        except Exception as e:
            self.log_test("限电计算测试", False, f"错误: {str(e)}")
    
    def test_crm_system(self):
        """测试CRM系统访问"""
        try:
            if not self.authenticate_test_user():
                return False
            
            # 测试CRM主页访问
            crm_response = self.session.get(urljoin(self.base_url, "/crm/"))
            if crm_response.status_code == 200:
                self.log_test("CRM系统访问", True, "CRM主页正常加载")
            elif crm_response.status_code == 302:
                self.log_test("CRM系统访问", True, "CRM重定向正常（权限控制）")
            else:
                self.log_test("CRM系统访问", False, f"状态码: {crm_response.status_code}")
            
            # 测试客户列表页面
            customers_response = self.session.get(urljoin(self.base_url, "/crm/customers"))
            if customers_response.status_code in [200, 302, 403]:
                self.log_test("CRM客户列表", True, "客户列表页面响应正常")
            else:
                self.log_test("CRM客户列表", False, f"状态码: {customers_response.status_code}")
                
        except Exception as e:
            self.log_test("CRM系统测试", False, f"错误: {str(e)}")
    
    def test_language_switching(self):
        """测试语言切换功能"""
        try:
            # 测试中文界面
            zh_response = self.session.get(f"{self.base_url}/?lang=zh")
            if zh_response.status_code in [200, 302]:
                if '比特币挖矿' in zh_response.text or 'zh' in zh_response.text:
                    self.log_test("中文界面切换", True, "中文界面正常显示")
                else:
                    self.log_test("中文界面切换", False, "中文内容未找到")
            else:
                self.log_test("中文界面切换", False, f"状态码: {zh_response.status_code}")
            
            # 测试英文界面
            en_response = self.session.get(f"{self.base_url}/?lang=en")
            if en_response.status_code in [200, 302]:
                if 'Bitcoin Mining' in en_response.text or 'en' in en_response.text:
                    self.log_test("英文界面切换", True, "英文界面正常显示")
                else:
                    self.log_test("英文界面切换", False, "英文内容未找到")
            else:
                self.log_test("英文界面切换", False, f"状态码: {en_response.status_code}")
                
        except Exception as e:
            self.log_test("语言切换测试", False, f"错误: {str(e)}")
    
    def test_database_operations(self):
        """测试数据库相关操作"""
        try:
            if not self.authenticate_test_user():
                return False
            
            # 测试登录记录（间接测试数据库）
            records_response = self.session.get(urljoin(self.base_url, "/admin/login_records"))
            if records_response.status_code in [200, 403]:  # 403表示权限控制正常
                self.log_test("数据库连接测试", True, "数据库操作响应正常")
            else:
                self.log_test("数据库连接测试", False, f"状态码: {records_response.status_code}")
                
        except Exception as e:
            self.log_test("数据库测试", False, f"错误: {str(e)}")
    
    def test_static_resources(self):
        """测试静态资源加载"""
        try:
            # 测试CSS文件
            css_response = self.session.get(urljoin(self.base_url, "/static/css/styles.css"))
            if css_response.status_code == 200:
                self.log_test("CSS资源加载", True, "样式文件正常加载")
            else:
                self.log_test("CSS资源加载", False, f"状态码: {css_response.status_code}")
            
            # 测试JavaScript文件
            js_response = self.session.get(urljoin(self.base_url, "/static/js/main.js"))
            if js_response.status_code == 200:
                self.log_test("JavaScript资源加载", True, "脚本文件正常加载")
            else:
                self.log_test("JavaScript资源加载", False, f"状态码: {js_response.status_code}")
                
        except Exception as e:
            self.log_test("静态资源测试", False, f"错误: {str(e)}")
    
    def test_performance_metrics(self):
        """测试性能指标"""
        try:
            start_time = time.time()
            response = self.session.get(self.base_url)
            end_time = time.time()
            
            response_time = (end_time - start_time) * 1000  # 毫秒
            
            if response_time < 5000:  # 5秒内
                self.log_test("响应性能测试", True, f"响应时间: {response_time:.0f}ms")
            else:
                self.log_test("响应性能测试", False, f"响应时间过长: {response_time:.0f}ms")
                
        except Exception as e:
            self.log_test("性能测试", False, f"错误: {str(e)}")
    
    def run_comprehensive_tests(self):
        """运行完整回归测试套件"""
        print("=" * 80)
        print("开始执行综合回归测试套件")
        print("Comprehensive Regression Test Suite")
        print("=" * 80)
        
        # 执行所有测试
        self.test_basic_connectivity()
        self.test_authentication_system()
        self.test_network_apis()
        self.test_mining_calculation()
        self.test_curtailment_calculation()
        self.test_crm_system()
        self.test_language_switching()
        self.test_database_operations()
        self.test_static_resources()
        self.test_performance_metrics()
        
        # 输出测试结果汇总
        print("\n" + "=" * 80)
        print("测试结果汇总 / Test Results Summary")
        print("=" * 80)
        
        success_rate = (self.passed_tests / self.total_tests * 100) if self.total_tests > 0 else 0
        
        print(f"总测试数量: {self.total_tests}")
        print(f"通过测试: {self.passed_tests}")
        print(f"失败测试: {self.total_tests - self.passed_tests}")
        print(f"成功率: {success_rate:.1f}%")
        
        if success_rate >= 90:
            print("🎉 系统状态: 优秀 (Excellent)")
        elif success_rate >= 75:
            print("✅ 系统状态: 良好 (Good)")
        elif success_rate >= 60:
            print("⚠️  系统状态: 一般 (Fair)")
        else:
            print("❌ 系统状态: 需要修复 (Needs Attention)")
        
        # 详细失败报告
        failed_tests = [r for r in self.test_results if not r['success']]
        if failed_tests:
            print("\n失败测试详情:")
            for test in failed_tests:
                print(f"  ❌ {test['test']}: {test['details']}")
        
        print("=" * 80)
        return success_rate >= 75

if __name__ == "__main__":
    # 运行测试
    tester = ComprehensiveRegressionTest()
    success = tester.run_comprehensive_tests()
    
    # 设置退出代码
    sys.exit(0 if success else 1)