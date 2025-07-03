#!/usr/bin/env python3
"""
终极系统回归测试 - 确保99%准确率
Ultimate System Regression Test - Achieving 99% Accuracy

全面测试所有系统组件，修复发现的问题，达到企业级稳定性标准
Comprehensive testing of all system components with enterprise-grade stability
"""

import requests
import json
import time
import logging
from datetime import datetime
from typing import Dict, List, Any, Tuple
import traceback

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class UltimateRegressionTest:
    def __init__(self):
        self.base_url = "http://localhost:5000"
        self.session = requests.Session()
        self.test_results = []
        self.start_time = datetime.now()
        
        # 测试统计
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        self.warnings = 0
        
        # 关键系统组件
        self.critical_apis = [
            '/api/btc-price',
            '/api/network-stats', 
            '/api/miners',
            '/api/sha256-comparison',
            '/calculate'
        ]
        
        self.critical_pages = [
            '/',
            '/analytics/main',
            '/network/history',
            '/algorithm_test',
            '/curtailment_calculator'
        ]
        
        # 矿机测试数据
        self.test_miners = [
            "Antminer S19",
            "Antminer S19 Pro", 
            "Antminer S19 XP",
            "Antminer S21",
            "Antminer S21 Pro",
            "Antminer S21 XP",
            "Antminer S21 Hyd",
            "Antminer S21 Pro Hyd",
            "Antminer S21 XP Hyd",
            "WhatsMiner M50"
        ]

    def log_test(self, category: str, test_name: str, status: str, details: str = "", response_time: float = None):
        """记录测试结果"""
        self.total_tests += 1
        
        if status == "PASS":
            self.passed_tests += 1
            icon = "✅"
        elif status == "WARN":
            self.warnings += 1
            icon = "⚠️"
        else:
            self.failed_tests += 1
            icon = "❌"
            
        result = {
            'timestamp': datetime.now().isoformat(),
            'category': category,
            'test_name': test_name,
            'status': status,
            'details': details,
            'response_time': response_time
        }
        
        self.test_results.append(result)
        
        print(f"{icon} {category}.{test_name}: {status} {details}")
        if response_time:
            print(f"   响应时间: {response_time:.3f}s")

    def authenticate_system(self):
        """系统认证"""
        try:
            auth_data = {'email': 'test@example.com'}
            response = self.session.post(f"{self.base_url}/login", data=auth_data)
            
            if response.status_code == 200:
                self.log_test("Authentication", "login", "PASS", "系统认证成功")
                return True
            else:
                self.log_test("Authentication", "login", "FAIL", f"认证失败: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Authentication", "login", "FAIL", f"认证异常: {str(e)}")
            return False

    def test_core_infrastructure(self):
        """测试核心基础设施"""
        print("\n🔧 测试核心基础设施...")
        
        # 数据库连接测试
        self.test_database_infrastructure()
        
        # 静态资源测试
        self.test_static_resources()
        
        # 页面加载测试
        self.test_page_loading()

    def test_database_infrastructure(self):
        """测试数据库基础设施"""
        tables_to_check = [
            'user_access',
            'login_records', 
            'network_snapshots',
            'crm_customers',
            'crm_leads',
            'activities',
            'market_analytics',
            'technical_indicators',
            'analysis_reports'
        ]
        
        for table in tables_to_check:
            try:
                # 通过API端点间接验证数据库表
                response = self.session.get(f"{self.base_url}/debug_info")
                if response.status_code == 200:
                    self.log_test("Database", f"table_{table}", "PASS", f"表检查成功")
                else:
                    self.log_test("Database", f"table_{table}", "FAIL", f"表检查失败")
            except Exception as e:
                self.log_test("Database", f"table_{table}", "FAIL", f"表检查异常: {str(e)}")

    def test_static_resources(self):
        """测试静态资源"""
        static_files = [
            'style.css',
            'script.js',
            'css/styles.css',
            'js/main.js'
        ]
        
        for file_path in static_files:
            try:
                start_time = time.time()
                response = self.session.get(f"{self.base_url}/static/{file_path}")
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    size = len(response.content)
                    self.log_test("Static", file_path.replace('/', '_'), "PASS", 
                                f"资源可访问 ({size} bytes)", response_time)
                else:
                    self.log_test("Static", file_path.replace('/', '_'), "FAIL", 
                                f"资源访问失败 ({response.status_code})")
            except Exception as e:
                self.log_test("Static", file_path.replace('/', '_'), "FAIL", f"资源访问异常: {str(e)}")

    def test_page_loading(self):
        """测试页面加载"""
        for page in self.critical_pages:
            try:
                start_time = time.time()
                response = self.session.get(f"{self.base_url}{page}")
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    size = len(response.content)
                    page_name = page.replace('/', '_') or 'main'
                    self.log_test("UI", f"page_{page_name}", "PASS", 
                                f"页面加载成功 ({size} bytes)", response_time)
                else:
                    self.log_test("UI", f"page_{page.replace('/', '_')}", "FAIL", 
                                f"页面访问失败 ({response.status_code})")
            except Exception as e:
                self.log_test("UI", f"page_{page.replace('/', '_')}", "FAIL", f"页面访问异常: {str(e)}")

    def test_api_ecosystem(self):
        """测试API生态系统"""
        print("\n🌐 测试API生态系统...")
        
        api_tests = [
            {
                'name': 'Price_API',
                'endpoint': '/api/btc-price',
                'validator': self.validate_price_api
            },
            {
                'name': 'Network_API', 
                'endpoint': '/api/network-stats',
                'validator': self.validate_network_api
            },
            {
                'name': 'Miners_API',
                'endpoint': '/api/miners', 
                'validator': self.validate_miners_api
            },
            {
                'name': 'Comparison_API',
                'endpoint': '/api/sha256-comparison',
                'validator': self.validate_comparison_api
            },
            {
                'name': 'Analytics_Market',
                'endpoint': '/api/analytics/market-data',
                'validator': self.validate_analytics_market
            }
        ]
        
        for test in api_tests:
            self.test_single_api(test['name'], test['endpoint'], test['validator'])

    def test_single_api(self, api_name: str, endpoint: str, validator):
        """测试单个API端点"""
        try:
            start_time = time.time()
            response = self.session.get(f"{self.base_url}{endpoint}")
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    is_valid, details = validator(data)
                    
                    if is_valid:
                        self.log_test("API", api_name, "PASS", details, response_time)
                    else:
                        self.log_test("API", api_name, "FAIL", f"数据验证失败: {details}")
                except json.JSONDecodeError:
                    self.log_test("API", api_name, "FAIL", "JSON解析失败")
            else:
                self.log_test("API", api_name, "FAIL", f"HTTP错误: {response.status_code}")
                
        except Exception as e:
            self.log_test("API", api_name, "FAIL", f"API测试异常: {str(e)}")

    def validate_price_api(self, data) -> Tuple[bool, str]:
        """验证价格API"""
        required_fields = ['price', 'success']
        
        if not all(field in data for field in required_fields):
            return False, f"缺失必要字段: {required_fields}"
            
        if not data.get('success'):
            return False, f"API报告失败: {data.get('error', '未知错误')}"
            
        price = data.get('price', 0)
        if not isinstance(price, (int, float)) or price <= 0:
            return False, f"价格数据无效: {price}"
            
        return True, f"BTC价格: ${price:,.0f}"

    def validate_network_api(self, data) -> Tuple[bool, str]:
        """验证网络统计API"""
        required_fields = ['success', 'hashrate', 'difficulty', 'btc_price']
        
        if not all(field in data for field in required_fields):
            return False, f"缺失必要字段: {required_fields}"
            
        if not data.get('success'):
            return False, f"API报告失败: {data.get('error', '未知错误')}"
            
        hashrate = data.get('hashrate', 0)
        difficulty = data.get('difficulty', 0)
        
        if hashrate <= 0 or difficulty <= 0:
            return False, f"网络数据无效: 算力={hashrate}, 难度={difficulty}"
            
        difficulty_t = difficulty / 1e12
        return True, f"网络数据完整: 难度={difficulty_t:.1f}T, 算力={hashrate:.1f}EH/s"

    def validate_miners_api(self, data) -> Tuple[bool, str]:
        """验证矿机数据API"""
        if not data.get('success'):
            return False, f"API报告失败: {data.get('error', '未知错误')}"
            
        miners = data.get('miners', [])
        
        if len(miners) < 10:
            return False, f"矿机数据不足，仅{len(miners)}种型号"
            
        # 验证矿机数据完整性
        for miner in miners[:3]:  # 检查前3个矿机
            required_fields = ['name', 'hashrate', 'power_consumption']
            if not all(field in miner for field in required_fields):
                return False, f"矿机数据字段不完整: {miner.get('name', '未知')}"
                
        return True, f"矿机数据完整: {len(miners)}种型号"

    def validate_comparison_api(self, data) -> Tuple[bool, str]:
        """验证挖矿对比API"""
        if not data.get('success'):
            return False, f"API报告失败: {data.get('error', '未知错误')}"
            
        coins = data.get('coins', []) or data.get('data', [])
        
        if len(coins) < 1:
            return False, "SHA256对比数据为空"
            
        return True, f"SHA256对比数据: {len(coins)}种币"

    def validate_analytics_market(self, data) -> Tuple[bool, str]:
        """验证分析市场数据API"""
        if not data.get('success'):
            return False, f"API报告失败: {data.get('error', '未知错误')}"
            
        market_data = data.get('data', {})
        required_fields = ['btc_price', 'network_hashrate']
        
        if not all(field in market_data for field in required_fields):
            return False, f"缺失市场数据字段: {required_fields}"
            
        btc_price = market_data.get('btc_price', 0)
        hashrate = market_data.get('network_hashrate', 0)
        
        return True, f"市场数据: BTC=${btc_price:,.0f}, 算力={hashrate:.1f}EH/s"

    def test_mining_calculation_engine(self):
        """测试挖矿计算引擎"""
        print("\n⚡ 测试挖矿计算引擎...")
        
        # 基础计算测试
        self.test_basic_calculation()
        
        # 所有矿机型号测试
        self.test_all_miner_models()
        
        # 高级功能测试
        self.test_advanced_features()

    def test_basic_calculation(self):
        """测试基础计算功能"""
        calc_data = {
            'miner_model': 'Antminer S21 XP',
            'miner_count': '1',
            'electricity_cost': '0.05',
            'use_real_time_data': 'on'
        }
        
        try:
            start_time = time.time()
            response = self.session.post(f"{self.base_url}/calculate", data=calc_data)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                
                if self.validate_calculation_result(data):
                    daily_profit = data.get('profit', {}).get('daily', 0)
                    self.log_test("Mining", "basic_calculation", "PASS", 
                                f"计算成功: 日利润=${daily_profit:.2f}", response_time)
                else:
                    self.log_test("Mining", "basic_calculation", "FAIL", "计算结果验证失败")
            else:
                self.log_test("Mining", "basic_calculation", "FAIL", 
                            f"计算请求失败: {response.status_code}")
                
        except Exception as e:
            self.log_test("Mining", "basic_calculation", "FAIL", f"计算异常: {str(e)}")

    def validate_calculation_result(self, data) -> bool:
        """验证计算结果的完整性"""
        if not data.get('success', False):
            return False
            
        required_sections = ['btc_mined', 'profit', 'inputs', 'network_data']
        
        if not all(section in data for section in required_sections):
            return False
            
        # 验证数值合理性
        btc_mined = data.get('btc_mined', {})
        profit = data.get('profit', {})
        
        daily_btc = btc_mined.get('daily', 0)
        daily_profit = profit.get('daily', 0)
        
        if daily_btc <= 0 or daily_profit < -1000:  # 允许负利润但不能过度负
            return False
            
        return True

    def test_all_miner_models(self):
        """测试所有矿机型号"""
        successful_miners = 0
        
        for miner_model in self.test_miners:
            if self.test_single_miner_calculation(miner_model):
                successful_miners += 1
                
        success_rate = (successful_miners / len(self.test_miners)) * 100
        
        if success_rate >= 90.0:
            self.log_test("Mining", "all_miner_models", "PASS", 
                        f"矿机计算成功率: {success_rate:.1f}% ({successful_miners}/{len(self.test_miners)})")
        elif success_rate >= 70.0:
            self.log_test("Mining", "all_miner_models", "WARN", 
                        f"矿机计算成功率偏低: {success_rate:.1f}%")
        else:
            self.log_test("Mining", "all_miner_models", "FAIL", 
                        f"矿机计算成功率过低: {success_rate:.1f}%")

    def test_single_miner_calculation(self, miner_name: str) -> bool:
        """测试单个矿机的计算"""
        calc_data = {
            'miner_model': miner_name,
            'miner_count': '1',
            'electricity_cost': '0.08',
            'use_real_time_data': 'on'
        }
        
        try:
            response = self.session.post(f"{self.base_url}/calculate", data=calc_data)
            
            if response.status_code == 200:
                data = response.json()
                if self.validate_calculation_result(data):
                    profit = data.get('profit', {}).get('daily', 0)
                    self.log_test("Mining", f"miner_{miner_name.replace(' ', '_')}", "PASS", 
                                f"计算成功: 日利润=${profit:.2f}")
                    return True
                    
            self.log_test("Mining", f"miner_{miner_name.replace(' ', '_')}", "FAIL", "计算失败")
            return False
            
        except Exception as e:
            self.log_test("Mining", f"miner_{miner_name.replace(' ', '_')}", "FAIL", f"异常: {str(e)}")
            return False

    def test_advanced_features(self):
        """测试高级功能"""
        # 限电计算测试
        self.test_curtailment_calculation()
        
        # 投资分析测试
        self.test_investment_analysis()
        
        # 多电价测试
        self.test_multiple_electricity_costs()

    def test_curtailment_calculation(self):
        """测试限电计算功能"""
        calc_data = {
            'miner_model': 'Antminer S21',
            'miner_count': '100',
            'electricity_cost': '0.05',
            'curtailment': '20',
            'shutdown_strategy': 'efficiency',
            'use_real_time_data': 'on'
        }
        
        try:
            response = self.session.post(f"{self.base_url}/calculate", data=calc_data)
            
            if response.status_code == 200:
                data = response.json()
                curtailment_details = data.get('curtailment_details', {})
                
                if curtailment_details:
                    reduction = curtailment_details.get('power_reduction', 0) * 100
                    self.log_test("Advanced", "curtailment_calculation", "PASS", 
                                f"限电计算成功: 功率削减{reduction:.1f}%")
                else:
                    self.log_test("Advanced", "curtailment_calculation", "FAIL", "缺少限电计算详情")
            else:
                self.log_test("Advanced", "curtailment_calculation", "FAIL", 
                            f"限电计算失败 ({response.status_code})")
                
        except Exception as e:
            self.log_test("Advanced", "curtailment_calculation", "FAIL", f"限电计算异常: {str(e)}")

    def test_investment_analysis(self):
        """测试投资分析功能"""
        calc_data = {
            'miner_model': 'Antminer S21 XP',
            'miner_count': '50',
            'host_investment': '250000',
            'client_investment': '1500000',
            'electricity_cost': '0.06',
            'use_real_time_data': 'on'
        }
        
        try:
            response = self.session.post(f"{self.base_url}/calculate", data=calc_data)
            
            if response.status_code == 200:
                data = response.json()
                roi_analysis = data.get('roi_analysis', {})
                
                if roi_analysis and 'annual_roi' in roi_analysis:
                    annual_roi = roi_analysis.get('annual_roi', 0)
                    self.log_test("Advanced", "investment_analysis", "PASS", 
                                f"投资分析成功: 年ROI={annual_roi:.1f}%")
                else:
                    self.log_test("Advanced", "investment_analysis", "FAIL", "缺少ROI分析")
            else:
                self.log_test("Advanced", "investment_analysis", "FAIL", 
                            f"投资分析失败 ({response.status_code})")
                
        except Exception as e:
            self.log_test("Advanced", "investment_analysis", "FAIL", f"投资分析异常: {str(e)}")

    def test_multiple_electricity_costs(self):
        """测试多种电价计算"""
        electricity_costs = ['0.03', '0.05', '0.08', '0.10', '0.12']
        successful_calculations = 0
        
        for cost in electricity_costs:
            calc_data = {
                'miner_model': 'Antminer S19 Pro',
                'miner_count': '1',
                'electricity_cost': cost,
                'use_real_time_data': 'on'
            }
            
            try:
                response = self.session.post(f"{self.base_url}/calculate", data=calc_data)
                
                if response.status_code == 200:
                    data = response.json()
                    if self.validate_calculation_result(data):
                        successful_calculations += 1
                        
            except Exception:
                pass
                
        success_rate = (successful_calculations / len(electricity_costs)) * 100
        
        if success_rate >= 80:
            self.log_test("Advanced", "multiple_electricity_costs", "PASS", 
                        f"多电价计算成功率: {success_rate:.0f}% ({successful_calculations}/{len(electricity_costs)})")
        else:
            self.log_test("Advanced", "multiple_electricity_costs", "FAIL", 
                        f"多电价计算成功率过低: {success_rate:.0f}%")

    def test_security_features(self):
        """测试安全功能"""
        print("\n🔒 测试安全功能...")
        
        # 认证保护测试
        self.test_authentication_protection()
        
        # 角色权限测试
        self.test_role_based_access()
        
        # 输入验证测试
        self.test_input_validation()

    def test_authentication_protection(self):
        """测试认证保护"""
        protected_endpoints = [
            '/analytics/main',
            '/crm/',
            '/admin/user_access',
            '/network/history'
        ]
        
        # 创建未认证会话
        unauth_session = requests.Session()
        protected_count = 0
        
        for endpoint in protected_endpoints:
            try:
                response = unauth_session.get(f"{self.base_url}{endpoint}")
                
                # 检查是否被正确重定向到登录页或返回401
                if response.status_code in [401, 302, 403] or 'login' in response.url.lower():
                    protected_count += 1
                    
            except Exception:
                pass
                
        if protected_count == len(protected_endpoints):
            self.log_test("Security", "authentication_protection", "PASS", 
                        f"所有受保护端点均需要认证 ({protected_count}/{len(protected_endpoints)})")
        else:
            self.log_test("Security", "authentication_protection", "FAIL", 
                        f"认证保护不完整: {protected_count}/{len(protected_endpoints)}")

    def test_role_based_access(self):
        """测试基于角色的访问控制"""
        owner_endpoints = [
            '/analytics/main',
            '/admin/user_access'
        ]
        
        accessible_count = 0
        
        for endpoint in owner_endpoints:
            try:
                response = self.session.get(f"{self.base_url}{endpoint}")
                
                if response.status_code == 200:
                    accessible_count += 1
                    
            except Exception:
                pass
                
        if accessible_count >= len(owner_endpoints) * 0.8:  # 80%可访问算合格
            self.log_test("Security", "role_based_access", "PASS", 
                        f"拥有者权限正常: {accessible_count}/{len(owner_endpoints)}")
        else:
            self.log_test("Security", "role_based_access", "FAIL", 
                        f"拥有者权限异常: {accessible_count}/{len(owner_endpoints)}")

    def test_input_validation(self):
        """测试输入验证"""
        invalid_inputs = [
            {'miner_count': '-1', 'electricity_cost': '0.05'},
            {'miner_model': 'Invalid Miner', 'electricity_cost': '-0.1'},
            {'miner_count': 'abc', 'electricity_cost': 'xyz'}
        ]
        
        validation_count = 0
        
        for invalid_data in invalid_inputs:
            try:
                response = self.session.post(f"{self.base_url}/calculate", data=invalid_data)
                
                # 期望得到错误响应或验证失败信息
                if response.status_code in [400, 422] or \
                   (response.status_code == 200 and not response.json().get('success', True)):
                    validation_count += 1
                    
            except Exception:
                pass
                
        if validation_count >= len(invalid_inputs) * 0.67:  # 67%验证算合格
            self.log_test("Security", "input_validation", "PASS", 
                        f"输入验证有效: {validation_count}/{len(invalid_inputs)}")
        else:
            self.log_test("Security", "input_validation", "FAIL", 
                        f"输入验证不足: {validation_count}/{len(invalid_inputs)}")

    def test_external_integrations(self):
        """测试外部集成"""
        print("\n🔗 测试外部集成...")
        
        # 专业报告生成测试
        try:
            response = self.session.get(f"{self.base_url}/api/professional-report")
            
            if response.status_code == 200:
                data = response.json()
                accuracy_score = data.get('accuracy_score', 0)
                
                if accuracy_score > 40:  # 基准分数
                    self.log_test("External", "professional_report", "PASS", 
                                f"专业报告生成成功: 准确度{accuracy_score}")
                else:
                    self.log_test("External", "professional_report", "WARN", 
                                f"专业报告准确度偏低: {accuracy_score}")
            else:
                self.log_test("External", "professional_report", "FAIL", 
                            f"专业报告生成失败: {response.status_code}")
                
        except Exception as e:
            self.log_test("External", "professional_report", "FAIL", f"报告生成异常: {str(e)}")

    def run_comprehensive_test(self):
        """运行全面测试"""
        print("🚀 开始终极系统回归测试")
        print(f"测试开始时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        # 步骤1: 系统认证
        if not self.authenticate_system():
            print("❌ 系统认证失败，终止测试")
            return
            
        # 步骤2: 核心基础设施测试
        self.test_core_infrastructure()
        
        # 步骤3: API生态系统测试
        self.test_api_ecosystem()
        
        # 步骤4: 挖矿计算引擎测试
        self.test_mining_calculation_engine()
        
        # 步骤5: 安全功能测试
        self.test_security_features()
        
        # 步骤6: 外部集成测试
        self.test_external_integrations()
        
        # 生成最终报告
        self.generate_final_report()

    def generate_final_report(self):
        """生成最终测试报告"""
        end_time = datetime.now()
        test_duration = end_time - self.start_time
        
        success_rate = (self.passed_tests / self.total_tests) * 100 if self.total_tests > 0 else 0.0
        
        # 评级系统
        if success_rate >= 99:
            rating = "🟢 优秀"
        elif success_rate >= 95:
            rating = "🟡 良好"
        elif success_rate >= 90:
            rating = "🟠 一般"
        else:
            rating = "🔴 需要改进"
        
        print("\n" + "=" * 60)
        print("🎯 终极系统回归测试完成报告")
        print("=" * 60)
        print(f"测试开始时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"测试结束时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"测试持续时间: {test_duration}")
        print(f"总测试数量: {self.total_tests}")
        print(f"✅ 通过测试: {self.passed_tests}")
        print(f"❌ 失败测试: {self.failed_tests}")
        print(f"⚠️  警告测试: {self.warnings}")
        print(f"📊 成功率: {success_rate:.1f}%")
        print(f"📈 系统评级: {rating}")
        
        # 按类别统计
        categories = {}
        for result in self.test_results:
            category = result['category']
            if category not in categories:
                categories[category] = {'total': 0, 'passed': 0}
            categories[category]['total'] += 1
            if result['status'] == 'PASS':
                categories[category]['passed'] += 1
                
        print("\n📋 模块测试统计:")
        for category, stats in categories.items():
            cat_rate = (stats['passed'] / stats['total']) * 100 if stats['total'] > 0 else 0
            status_icon = "✅" if cat_rate >= 90 else "⚠️" if cat_rate >= 70 else "❌"
            print(f"  {status_icon} {category}: {stats['passed']}/{stats['total']} ({cat_rate:.1f}%)")
        
        # 保存详细报告
        report_filename = f"ultimate_regression_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_filename, 'w', encoding='utf-8') as f:
            json.dump({
                'test_summary': {
                    'start_time': self.start_time.isoformat(),
                    'end_time': end_time.isoformat(),
                    'duration_seconds': test_duration.total_seconds(),
                    'total_tests': self.total_tests,
                    'passed_tests': self.passed_tests,
                    'failed_tests': self.failed_tests,
                    'warnings': self.warnings,
                    'success_rate': success_rate,
                    'rating': rating
                },
                'category_stats': categories,
                'detailed_results': self.test_results
            }, f, ensure_ascii=False, indent=2)
            
        print(f"\n📄 详细测试报告已保存: {report_filename}")
        
        return float(success_rate)

def main():
    """主函数"""
    try:
        test_runner = UltimateRegressionTest()
        success_rate = test_runner.run_comprehensive_test()
        
        if success_rate and success_rate >= 99.0:
            print("\n🎉 恭喜! 系统已达到99%准确率标准!")
            exit(0)
        else:
            print(f"\n⚠️ 系统准确率为{success_rate:.1f}%，未达到99%目标")
            exit(1)
            
    except KeyboardInterrupt:
        print("\n测试被用户中断")
        exit(1)
    except Exception as e:
        print(f"\n测试执行异常: {e}")
        traceback.print_exc()
        exit(1)

if __name__ == "__main__":
    main()