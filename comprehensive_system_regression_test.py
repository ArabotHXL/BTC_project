#!/usr/bin/env python3
"""
全面系统回归测试 - BTC挖矿计算器
Comprehensive System Regression Test - BTC Mining Calculator

测试所有核心功能模块的完整性和可用性
Tests completeness and availability of all core function modules
"""

import requests
import json
import time
from datetime import datetime
import psycopg2
import os
from typing import Dict, List, Tuple

class ComprehensiveRegressionTest:
    def __init__(self):
        self.base_url = "http://localhost:5000"
        self.session = requests.Session()
        self.test_results = []
        self.start_time = datetime.now()
        
    def log_test(self, module_name: str, function_name: str, status: str, details: str = "", response_time: float = None):
        """记录测试结果"""
        result = {
            'timestamp': datetime.now().isoformat(),
            'module': module_name,
            'function': function_name,
            'status': status,
            'details': details,
            'response_time': response_time
        }
        self.test_results.append(result)
        status_icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"{status_icon} {module_name}.{function_name}: {status} {details}")
        
    def authenticate_system(self):
        """系统认证"""
        try:
            login_data = {"email": "hxl2022hao@gmail.com"}
            start_time = time.time()
            response = self.session.post(f"{self.base_url}/login", data=login_data)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                self.log_test("Authentication", "login", "PASS", f"登录成功 ({response.status_code})", response_time)
                return True
            else:
                self.log_test("Authentication", "login", "FAIL", f"登录失败 ({response.status_code})", response_time)
                return False
        except Exception as e:
            self.log_test("Authentication", "login", "FAIL", f"认证异常: {str(e)}")
            return False
    
    def test_core_infrastructure(self):
        """测试核心基础设施"""
        print("\n🔧 测试核心基础设施...")
        
        # 测试主页访问
        try:
            start_time = time.time()
            response = self.session.get(self.base_url)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                self.log_test("Infrastructure", "main_page", "PASS", "主页可访问", response_time)
            else:
                self.log_test("Infrastructure", "main_page", "FAIL", f"主页访问失败 ({response.status_code})", response_time)
        except Exception as e:
            self.log_test("Infrastructure", "main_page", "FAIL", f"主页访问异常: {str(e)}")
        
        # 测试数据库连接
        self.test_database_infrastructure()
        
        # 测试静态资源
        self.test_static_resources()
    
    def test_database_infrastructure(self):
        """测试数据库基础设施"""
        try:
            conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
            cursor = conn.cursor()
            
            # 测试基础表
            tables_to_check = [
                'user_access', 'login_records', 'network_snapshots', 
                'customers', 'leads', 'activities', 'market_analytics',
                'technical_indicators', 'analysis_reports'
            ]
            
            for table in tables_to_check:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    self.log_test("Database", f"table_{table}", "PASS", f"表存在，{count}条记录")
                except Exception as e:
                    self.log_test("Database", f"table_{table}", "FAIL", f"表检查失败: {str(e)}")
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            self.log_test("Database", "connection", "FAIL", f"数据库连接失败: {str(e)}")
    
    def test_static_resources(self):
        """测试静态资源加载"""
        static_resources = [
            "/static/style.css",
            "/static/script.js"
        ]
        
        for resource in static_resources:
            try:
                start_time = time.time()
                response = self.session.get(f"{self.base_url}{resource}")
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    self.log_test("Static", resource.replace("/static/", ""), "PASS", f"资源可访问 ({len(response.content)} bytes)", response_time)
                else:
                    self.log_test("Static", resource.replace("/static/", ""), "FAIL", f"资源访问失败 ({response.status_code})", response_time)
            except Exception as e:
                self.log_test("Static", resource.replace("/static/", ""), "FAIL", f"资源访问异常: {str(e)}")
    
    def test_api_ecosystem(self):
        """测试API生态系统"""
        print("\n🌐 测试API生态系统...")
        
        api_endpoints = [
            ("Price", "/api/btc-price", self.validate_price_api),
            ("Network", "/api/network-stats", self.validate_network_api),
            ("Miners", "/api/miners", self.validate_miners_api),
            ("Comparison", "/api/sha256-comparison", self.validate_comparison_api),
            ("Analytics_Market", "/api/analytics/market-data", self.validate_analytics_market),
            ("Analytics_Report", "/api/analytics/latest-report", self.validate_analytics_report),
            ("Analytics_Indicators", "/api/analytics/technical-indicators", self.validate_analytics_indicators),
            ("Analytics_History", "/api/analytics/price-history", self.validate_analytics_history)
        ]
        
        for api_name, endpoint, validator in api_endpoints:
            self.test_single_api(api_name, endpoint, validator)
    
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
                        self.log_test("API", api_name, "FAIL", f"数据验证失败: {details}", response_time)
                except json.JSONDecodeError:
                    self.log_test("API", api_name, "FAIL", "JSON解析失败", response_time)
            else:
                self.log_test("API", api_name, "FAIL", f"API调用失败 ({response.status_code})", response_time)
                
        except Exception as e:
            self.log_test("API", api_name, "FAIL", f"API调用异常: {str(e)}")
    
    def validate_price_api(self, data) -> Tuple[bool, str]:
        """验证价格API"""
        if 'btc_price' in data and isinstance(data['btc_price'], (int, float)):
            return True, f"BTC价格: ${data['btc_price']:,.0f}"
        return False, "缺少有效的BTC价格数据"
    
    def validate_network_api(self, data) -> Tuple[bool, str]:
        """验证网络统计API"""
        required_fields = ['difficulty', 'hashrate', 'block_reward']
        missing_fields = [field for field in required_fields if field not in data]
        if not missing_fields:
            return True, f"网络数据完整: 难度={data.get('difficulty', 0):.1f}T, 算力={data.get('hashrate', 0):.1f}EH/s"
        return False, f"缺少字段: {missing_fields}"
    
    def validate_miners_api(self, data) -> Tuple[bool, str]:
        """验证矿机数据API"""
        if isinstance(data, list) and len(data) >= 5:
            miner_count = len(data)
            sample_miner = data[0] if data else {}
            has_specs = all(key in sample_miner for key in ['name', 'hashrate', 'power'])
            if has_specs:
                return True, f"{miner_count}种矿机型号，包含完整规格"
            else:
                return False, "矿机数据缺少必要规格信息"
        return False, f"矿机数据不足，仅{len(data) if isinstance(data, list) else 0}种型号"
    
    def validate_comparison_api(self, data) -> Tuple[bool, str]:
        """验证挖矿对比API"""
        if isinstance(data, list) and len(data) > 0:
            sample_coin = data[0] if data else {}
            has_profit_data = 'profitability' in sample_coin or 'profit_ratio' in sample_coin
            if has_profit_data:
                return True, f"SHA256对比数据: {len(data)}种币种"
            else:
                return False, "对比数据缺少收益信息"
        return False, "SHA256对比数据为空"
    
    def validate_analytics_market(self, data) -> Tuple[bool, str]:
        """验证分析市场数据API"""
        if 'data' in data and 'btc_price' in data['data']:
            market_data = data['data']
            return True, f"市场数据: BTC=${market_data['btc_price']:,.0f}, 算力={market_data.get('network_hashrate', 0):.1f}EH/s"
        return False, "分析市场数据格式错误"
    
    def validate_analytics_report(self, data) -> Tuple[bool, str]:
        """验证分析报告API"""
        if 'data' in data and isinstance(data['data'], dict):
            report = data['data']
            if 'title' in report and 'summary' in report:
                return True, f"分析报告: {report.get('title', 'N/A')}"
            else:
                return False, "分析报告缺少标题或摘要"
        return False, "分析报告数据格式错误"
    
    def validate_analytics_indicators(self, data) -> Tuple[bool, str]:
        """验证技术指标API"""
        if 'data' in data and isinstance(data['data'], dict):
            indicators = data['data']
            indicator_count = len([k for k in indicators.keys() if k != 'timestamp'])
            if indicator_count >= 3:
                return True, f"技术指标: {indicator_count}个指标"
            else:
                return False, f"技术指标不足，仅{indicator_count}个"
        return False, "技术指标数据格式错误"
    
    def validate_analytics_history(self, data) -> Tuple[bool, str]:
        """验证价格历史API"""
        if 'data' in data and isinstance(data['data'], list):
            history_count = len(data['data'])
            if history_count >= 5:
                return True, f"价格历史: {history_count}条记录"
            else:
                return False, f"价格历史数据不足，仅{history_count}条"
        return False, "价格历史数据格式错误"
    
    def test_mining_calculation_engine(self):
        """测试挖矿计算引擎"""
        print("\n⚡ 测试挖矿计算引擎...")
        
        # 测试基础挖矿计算
        self.test_basic_mining_calculation()
        
        # 测试所有矿机型号
        self.test_all_miner_models()
        
        # 测试高级计算功能
        self.test_advanced_calculations()
    
    def test_basic_mining_calculation(self):
        """测试基础挖矿计算"""
        calc_data = {
            'miner_model': 'Antminer S19 Pro',
            'miner_count': 100,
            'electricity_cost': 0.08,
            'site_power_mw': 10
        }
        
        try:
            start_time = time.time()
            response = self.session.post(f"{self.base_url}/calculate", 
                                       data=calc_data,
                                       headers={'Content-Type': 'application/x-www-form-urlencoded'})
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    if self.validate_calculation_result(data):
                        self.log_test("Mining", "basic_calculation", "PASS", 
                                    f"计算成功: 日收益=${data.get('daily_profit_usd', 0):,.2f}", response_time)
                    else:
                        self.log_test("Mining", "basic_calculation", "FAIL", "计算结果验证失败", response_time)
                except json.JSONDecodeError:
                    self.log_test("Mining", "basic_calculation", "FAIL", "计算结果JSON解析失败", response_time)
            else:
                self.log_test("Mining", "basic_calculation", "FAIL", f"计算请求失败 ({response.status_code})", response_time)
                
        except Exception as e:
            self.log_test("Mining", "basic_calculation", "FAIL", f"计算异常: {str(e)}")
    
    def validate_calculation_result(self, data) -> bool:
        """验证挖矿计算结果的完整性"""
        required_fields = [
            'daily_btc_output', 'daily_profit_usd', 'monthly_profit_usd',
            'yearly_profit_usd', 'roi_percentage', 'payback_days'
        ]
        
        for field in required_fields:
            if field not in data:
                return False
            if not isinstance(data[field], (int, float)):
                return False
        
        # 验证业务逻辑
        return self.validate_business_logic(data)
    
    def validate_business_logic(self, data):
        """验证业务逻辑正确性"""
        try:
            daily_profit = data.get('daily_profit_usd', 0)
            monthly_profit = data.get('monthly_profit_usd', 0)
            yearly_profit = data.get('yearly_profit_usd', 0)
            roi = data.get('roi_percentage', 0)
            
            # 基本逻辑检查
            if monthly_profit < daily_profit * 25 or monthly_profit > daily_profit * 35:
                return False
            if yearly_profit < monthly_profit * 11 or yearly_profit > monthly_profit * 13:
                return False
            if roi < 0 or roi > 1000:
                return False
                
            return True
        except:
            return False
    
    def test_all_miner_models(self):
        """测试所有矿机型号"""
        miner_models = [
            'Antminer S19', 'Antminer S19 Pro', 'Antminer S19 XP',
            'Antminer S21', 'Antminer S21 Pro', 'Antminer S21 XP',
            'Antminer S21 Hyd', 'Antminer S21 Pro Hyd', 'Antminer S21 XP Hyd',
            'WhatsMiner M50'
        ]
        
        for miner in miner_models:
            success = self.test_single_miner_calculation(miner)
            if success:
                self.log_test("Mining", f"miner_{miner.replace(' ', '_')}", "PASS", "矿机计算正常")
            else:
                self.log_test("Mining", f"miner_{miner.replace(' ', '_')}", "FAIL", "矿机计算失败")
    
    def test_single_miner_calculation(self, miner_name: str) -> bool:
        """测试单个矿机的计算"""
        calc_data = {
            'miner_model': miner_name,
            'miner_count': 10,
            'electricity_cost': 0.08,
            'site_power_mw': 2
        }
        
        try:
            response = self.session.post(f"{self.base_url}/calculate", data=calc_data)
            if response.status_code == 200:
                data = response.json()
                return self.validate_calculation_result(data)
        except:
            pass
        return False
    
    def test_advanced_calculations(self):
        """测试高级计算功能"""
        # 测试限电计算
        self.test_curtailment_calculation()
        
        # 测试投资分析
        self.test_investment_analysis()
        
        # 测试多种电价
        self.test_multiple_electricity_costs()
        
        # 测试盈亏平衡分析
        self.test_breakeven_analysis()
    
    def test_curtailment_calculation(self):
        """测试限电计算功能"""
        curtailment_data = {
            'miner_model': 'Antminer S19 Pro',
            'total_miners': 1000,
            'curtailment_hours': 120,
            'electricity_cost': 0.08
        }
        
        try:
            start_time = time.time()
            response = self.session.post(f"{self.base_url}/calculate-curtailment", data=curtailment_data)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                if 'curtailment_savings' in data and 'optimal_shutdown_strategy' in data:
                    self.log_test("Advanced", "curtailment_calculation", "PASS", 
                                f"限电计算成功: 节省${data.get('curtailment_savings', 0):,.0f}", response_time)
                else:
                    self.log_test("Advanced", "curtailment_calculation", "FAIL", "限电计算结果不完整", response_time)
            else:
                self.log_test("Advanced", "curtailment_calculation", "FAIL", f"限电计算失败 ({response.status_code})", response_time)
        except Exception as e:
            self.log_test("Advanced", "curtailment_calculation", "FAIL", f"限电计算异常: {str(e)}")
    
    def test_investment_analysis(self):
        """测试投资分析功能"""
        # 测试详细分析报告API
        try:
            start_time = time.time()
            response = self.session.get(f"{self.base_url}/api/generate-detailed-report")
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                if 'detailed_report' in data and 'accuracy_score' in data['detailed_report']:
                    accuracy_score = data['detailed_report']['accuracy_score']
                    self.log_test("Advanced", "investment_analysis", "PASS", 
                                f"投资分析成功: 准确度{accuracy_score}%", response_time)
                else:
                    self.log_test("Advanced", "investment_analysis", "FAIL", "投资分析结果不完整", response_time)
            else:
                self.log_test("Advanced", "investment_analysis", "FAIL", f"投资分析失败 ({response.status_code})", response_time)
        except Exception as e:
            self.log_test("Advanced", "investment_analysis", "FAIL", f"投资分析异常: {str(e)}")
    
    def test_multiple_electricity_costs(self):
        """测试多种电价计算"""
        electricity_costs = [0.05, 0.08, 0.10, 0.12, 0.15]
        passed_tests = 0
        
        for cost in electricity_costs:
            calc_data = {
                'miner_model': 'Antminer S19 Pro',
                'miner_count': 50,
                'electricity_cost': cost
            }
            
            try:
                response = self.session.post(f"{self.base_url}/calculate", data=calc_data)
                if response.status_code == 200:
                    data = response.json()
                    if self.validate_calculation_result(data):
                        passed_tests += 1
            except:
                pass
        
        if passed_tests >= 4:
            self.log_test("Advanced", "multiple_electricity_costs", "PASS", f"{passed_tests}/5电价计算成功")
        else:
            self.log_test("Advanced", "multiple_electricity_costs", "FAIL", f"仅{passed_tests}/5电价计算成功")
    
    def test_breakeven_analysis(self):
        """测试盈亏平衡分析"""
        # 测试布林带回测API
        try:
            start_time = time.time()
            response = self.session.get(f"{self.base_url}/api/bollinger-backtest")
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                if 'strategy_return' in data and 'win_rate' in data:
                    win_rate = data.get('win_rate', 0)
                    self.log_test("Advanced", "breakeven_analysis", "PASS", 
                                f"盈亏分析成功: 胜率{win_rate:.1f}%", response_time)
                else:
                    self.log_test("Advanced", "breakeven_analysis", "FAIL", "盈亏分析结果不完整", response_time)
            else:
                self.log_test("Advanced", "breakeven_analysis", "FAIL", f"盈亏分析失败 ({response.status_code})", response_time)
        except Exception as e:
            self.log_test("Advanced", "breakeven_analysis", "FAIL", f"盈亏分析异常: {str(e)}")
    
    def test_user_interface(self):
        """测试用户界面功能"""
        print("\n🎨 测试用户界面功能...")
        
        # 测试主要页面
        pages_to_test = [
            ("Main", "/"),
            ("Analytics", "/analytics"),
            ("Curtailment", "/curtailment"),
            ("Network_History", "/network-history"),
            ("Algorithm_Test", "/algorithm-test")
        ]
        
        for page_name, path in pages_to_test:
            self.test_page_load(page_name, path)
        
        # 测试响应式设计
        self.test_responsive_design()
    
    def test_page_load(self, page_name: str, path: str):
        """测试页面加载"""
        try:
            start_time = time.time()
            response = self.session.get(f"{self.base_url}{path}")
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                content_length = len(response.content)
                if content_length > 1000:  # 基本内容检查
                    self.log_test("UI", f"page_{page_name}", "PASS", 
                                f"页面加载成功 ({content_length} bytes)", response_time)
                else:
                    self.log_test("UI", f"page_{page_name}", "FAIL", "页面内容过少", response_time)
            else:
                self.log_test("UI", f"page_{page_name}", "FAIL", f"页面访问失败 ({response.status_code})", response_time)
        except Exception as e:
            self.log_test("UI", f"page_{page_name}", "FAIL", f"页面访问异常: {str(e)}")
    
    def test_responsive_design(self):
        """测试响应式设计"""
        # 通过检查CSS文件中的媒体查询来验证响应式设计
        try:
            response = self.session.get(f"{self.base_url}/static/style.css")
            if response.status_code == 200:
                css_content = response.text
                has_media_queries = "@media" in css_content
                has_bootstrap = "bootstrap" in css_content.lower() or "col-" in css_content
                
                if has_media_queries or has_bootstrap:
                    self.log_test("UI", "responsive_design", "PASS", "检测到响应式设计元素")
                else:
                    self.log_test("UI", "responsive_design", "WARN", "未检测到明显的响应式设计")
            else:
                self.log_test("UI", "responsive_design", "FAIL", "无法访问CSS文件")
        except Exception as e:
            self.log_test("UI", "responsive_design", "FAIL", f"响应式设计检查异常: {str(e)}")
    
    def test_external_integrations(self):
        """测试外部集成"""
        print("\n🔗 测试外部集成...")
        
        # 测试专业报告生成
        try:
            start_time = time.time()
            response = self.session.post(f"{self.base_url}/api/professional-report/generate",
                                       json={"output_formats": ["pdf"], "distribution_methods": []})
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success') and 'summary' in data:
                    self.log_test("External", "professional_report", "PASS", 
                                f"专业报告生成成功: 准确度{data['summary'].get('accuracy_score', 'N/A')}", response_time)
                else:
                    self.log_test("External", "professional_report", "FAIL", "专业报告生成失败", response_time)
            else:
                self.log_test("External", "professional_report", "FAIL", f"专业报告请求失败 ({response.status_code})", response_time)
        except Exception as e:
            self.log_test("External", "professional_report", "FAIL", f"专业报告异常: {str(e)}")
    
    def test_security_features(self):
        """测试安全功能"""
        print("\n🔒 测试安全功能...")
        
        # 测试认证保护
        self.test_authentication_protection()
        
        # 测试角色访问控制
        self.test_role_based_access()
        
        # 测试输入验证
        self.test_input_validation()
    
    def test_authentication_protection(self):
        """测试认证保护"""
        # 创建未认证会话
        unauth_session = requests.Session()
        
        protected_endpoints = [
            "/analytics",
            "/api/analytics/market-data",
            "/crm",
            "/user-access"
        ]
        
        protected_count = 0
        for endpoint in protected_endpoints:
            try:
                response = unauth_session.get(f"{self.base_url}{endpoint}")
                if response.status_code in [302, 401, 403]:  # 重定向到登录或拒绝访问
                    protected_count += 1
            except:
                pass
        
        if protected_count >= len(protected_endpoints) * 0.8:
            self.log_test("Security", "authentication_protection", "PASS", f"{protected_count}/{len(protected_endpoints)}端点受保护")
        else:
            self.log_test("Security", "authentication_protection", "FAIL", f"仅{protected_count}/{len(protected_endpoints)}端点受保护")
    
    def test_role_based_access(self):
        """测试基于角色的访问控制"""
        # 测试拥有者专属功能
        owner_endpoints = [
            "/login-records",
            "/user-access"
        ]
        
        accessible_count = 0
        for endpoint in owner_endpoints:
            try:
                response = self.session.get(f"{self.base_url}{endpoint}")
                if response.status_code == 200:
                    accessible_count += 1
            except:
                pass
        
        if accessible_count >= len(owner_endpoints) * 0.8:
            self.log_test("Security", "role_based_access", "PASS", f"拥有者权限正常: {accessible_count}/{len(owner_endpoints)}")
        else:
            self.log_test("Security", "role_based_access", "FAIL", f"拥有者权限异常: {accessible_count}/{len(owner_endpoints)}")
    
    def test_input_validation(self):
        """测试输入验证"""
        # 测试无效的挖矿计算输入
        invalid_inputs = [
            {'miner_model': '', 'miner_count': -1},
            {'miner_model': 'Invalid Miner', 'electricity_cost': -0.1},
            {'miner_count': 'abc', 'electricity_cost': 'xyz'}
        ]
        
        validation_passed = 0
        for invalid_input in invalid_inputs:
            try:
                response = self.session.post(f"{self.base_url}/calculate", data=invalid_input)
                # 期望返回错误或验证失败
                if response.status_code != 200 or 'error' in response.text.lower():
                    validation_passed += 1
            except:
                validation_passed += 1  # 异常也算验证通过
        
        if validation_passed >= len(invalid_inputs) * 0.8:
            self.log_test("Security", "input_validation", "PASS", f"输入验证正常: {validation_passed}/{len(invalid_inputs)}")
        else:
            self.log_test("Security", "input_validation", "FAIL", f"输入验证不足: {validation_passed}/{len(invalid_inputs)}")
    
    def run_complete_system_test(self):
        """运行完整系统测试"""
        print("🚀 开始全面系统回归测试")
        print(f"测试开始时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        # 系统认证
        if not self.authenticate_system():
            print("❌ 系统认证失败，无法继续测试")
            return
        
        # 核心测试模块
        test_modules = [
            self.test_core_infrastructure,
            self.test_api_ecosystem,
            self.test_mining_calculation_engine,
            self.test_user_interface,
            self.test_external_integrations,
            self.test_security_features
        ]
        
        for test_module in test_modules:
            try:
                test_module()
            except Exception as e:
                print(f"❌ 测试模块执行失败: {test_module.__name__}: {e}")
        
        # 生成最终报告
        self.generate_final_report()
    
    def generate_final_report(self):
        """生成最终测试报告"""
        end_time = datetime.now()
        duration = end_time - self.start_time
        
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r['status'] == 'PASS'])
        failed_tests = len([r for r in self.test_results if r['status'] == 'FAIL'])
        warning_tests = len([r for r in self.test_results if r['status'] == 'WARN'])
        
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        print("\n" + "=" * 60)
        print("🎯 全面系统回归测试完成报告")
        print("=" * 60)
        print(f"测试开始时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"测试结束时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"测试持续时间: {duration}")
        print(f"总测试数量: {total_tests}")
        print(f"✅ 通过测试: {passed_tests}")
        print(f"❌ 失败测试: {failed_tests}")
        print(f"⚠️  警告测试: {warning_tests}")
        print(f"📊 成功率: {success_rate:.1f}%")
        
        print(f"\n📈 系统评级: {'🟢 优秀' if success_rate >= 90 else '🟡 良好' if success_rate >= 80 else '🟠 一般' if success_rate >= 70 else '🔴 需要改进'}")
        
        # 模块统计
        modules = {}
        for result in self.test_results:
            module = result['module']
            if module not in modules:
                modules[module] = {'total': 0, 'passed': 0}
            modules[module]['total'] += 1
            if result['status'] == 'PASS':
                modules[module]['passed'] += 1
        
        print("\n📋 模块测试统计:")
        for module, stats in modules.items():
            module_success_rate = stats['passed'] / stats['total'] * 100
            status_icon = "✅" if module_success_rate >= 90 else "⚠️" if module_success_rate >= 70 else "❌"
            print(f"  {status_icon} {module}: {stats['passed']}/{stats['total']} ({module_success_rate:.1f}%)")
        
        # 保存详细结果
        report_filename = f"regression_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_filename, 'w', encoding='utf-8') as f:
            json.dump({
                'test_summary': {
                    'start_time': self.start_time.isoformat(),
                    'end_time': end_time.isoformat(),
                    'duration_seconds': duration.total_seconds(),
                    'total_tests': total_tests,
                    'passed_tests': passed_tests,
                    'failed_tests': failed_tests,
                    'warning_tests': warning_tests,
                    'success_rate': success_rate
                },
                'module_statistics': modules,
                'detailed_results': self.test_results
            }, f, indent=2, ensure_ascii=False)
        
        print(f"\n📄 详细测试报告已保存: {report_filename}")

def main():
    """主函数"""
    tester = ComprehensiveRegressionTest()
    tester.run_complete_system_test()

if __name__ == "__main__":
    main()