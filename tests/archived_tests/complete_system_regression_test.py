#!/usr/bin/env python3
"""
完整系统回归测试 (Complete System Regression Test)
全面测试系统所有组件和功能模块
"""
import requests
import time
import json
import logging
import psycopg2
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class CompleteSystemRegressionTest:
    def __init__(self):
        self.base_url = "http://127.0.0.1:5000"
        self.session = requests.Session()
        self.test_results = []
        self.test_start_time = time.time()
        self.test_user_email = "hxl2022hao@gmail.com"
        
        # 测试统计
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        
        # 性能指标
        self.response_times = []
        
    def authenticate(self):
        """用户认证"""
        try:
            login_data = {'email': self.test_user_email}
            response = self.session.post(f"{self.base_url}/login", data=login_data)
            if response.status_code == 200 and "logout" in response.text.lower():
                logging.info("✅ 用户认证成功")
                return True
            else:
                logging.error(f"❌ 用户认证失败: {response.status_code}")
                return False
        except Exception as e:
            logging.error(f"认证异常: {e}")
            return False

    def log_test(self, test_name: str, status: str, details: str = "", response_time: float = None, test_category: str = "general"):
        """记录测试结果"""
        self.total_tests += 1
        if status == "PASS":
            self.passed_tests += 1
        else:
            self.failed_tests += 1
            
        if response_time:
            self.response_times.append(response_time)
        
        result = {
            'test_name': test_name,
            'status': status,
            'details': details,
            'response_time': response_time,
            'test_category': test_category,
            'timestamp': datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        status_icon = "✅" if status == "PASS" else "❌"
        msg = f"{status_icon} {test_name}"
        if details:
            msg += f": {details}"
        if response_time:
            msg += f" ({response_time:.3f}s)"
        logging.info(msg)

    def test_database_infrastructure(self):
        """测试数据库基础设施"""
        logging.info("=== 测试数据库基础设施 ===")
        
        try:
            conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
            cursor = conn.cursor()
            
            # 测试所有核心表的存在性和结构
            core_tables = [
                'market_analytics',
                'network_snapshots', 
                'user_access',
                'crm_customers',
                'crm_contacts',
                'crm_leads',
                'crm_deals',
                'crm_activities',
                'login_records',
                'technical_indicators'
            ]
            
            for table in core_tables:
                try:
                    start_time = time.time()
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    query_time = time.time() - start_time
                    
                    self.log_test(f"数据库表-{table}", "PASS", 
                                f"记录数: {count}", query_time, "database")
                except Exception as e:
                    self.log_test(f"数据库表-{table}", "FAIL", 
                                f"查询失败: {str(e)}", None, "database")
            
            # 测试数据完整性和关联
            start_time = time.time()
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_snapshots,
                    AVG(btc_price) as avg_price,
                    MAX(recorded_at) as latest_time
                FROM network_snapshots 
                WHERE btc_price > 0
            """)
            result = cursor.fetchone()
            query_time = time.time() - start_time
            
            if result and result[0] > 0:
                total_count = int(result[0])
                avg_price = float(result[1]) if result[1] else 0
                latest_time = result[2]
                
                self.log_test("数据库完整性-网络快照", "PASS",
                            f"总记录: {total_count}, 平均价格: ${avg_price:,.0f}, 最新: {latest_time}",
                            query_time, "database")
            else:
                self.log_test("数据库完整性-网络快照", "FAIL",
                            "无有效数据", query_time, "database")
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            self.log_test("数据库基础设施-连接", "FAIL",
                        f"数据库连接失败: {str(e)}", None, "database")

    def test_api_endpoints_comprehensive(self):
        """全面测试API端点"""
        logging.info("=== 全面测试API端点 ===")
        
        # 核心API端点完整测试
        api_endpoints = [
            # 价格相关API
            {'url': '/get_btc_price', 'name': 'BTC价格API-主路径'},
            {'url': '/api/btc_price', 'name': 'BTC价格API-标准路径'},
            {'url': '/api/btc-price', 'name': 'BTC价格API-连字符路径'},
            
            # 网络统计API
            {'url': '/get_network_stats', 'name': '网络统计API-主路径'},
            {'url': '/api/network_stats', 'name': '网络统计API-标准路径'},
            {'url': '/api/network-stats', 'name': '网络统计API-连字符路径'},
            
            # 矿机信息API
            {'url': '/get_miners', 'name': '矿机列表API-主路径'},
            {'url': '/api/miners', 'name': '矿机列表API-标准路径'},
            
            # SHA256对比API
            {'url': '/get_sha256_mining_comparison', 'name': 'SHA256对比API'},
            
            # 分析系统API
            {'url': '/api/analytics/market-data', 'name': '分析系统-市场数据'},
            {'url': '/api/analytics/latest-report', 'name': '分析系统-最新报告'},
            {'url': '/api/analytics/technical-indicators', 'name': '分析系统-技术指标'},
            {'url': '/api/analytics/price-history', 'name': '分析系统-价格历史'},
            
            # 网络历史API
            {'url': '/api/network-stats-overview', 'name': '网络概览API'},
            {'url': '/api/price-trend', 'name': '价格趋势API'},
            {'url': '/api/difficulty-trend', 'name': '难度趋势API'},
            {'url': '/api/hashrate-analysis', 'name': '算力分析API'},
        ]
        
        for endpoint in api_endpoints:
            try:
                start_time = time.time()
                response = self.session.get(f"{self.base_url}{endpoint['url']}")
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        
                        # 基本数据验证
                        has_data = bool(data)
                        
                        # 特定验证逻辑
                        data_valid = True
                        key_info = ""
                        
                        if 'price' in endpoint['url'] or 'btc' in endpoint['url']:
                            price = data.get('price', 0)
                            if price > 50000:
                                key_info = f"价格: ${price:,.0f}"
                            else:
                                data_valid = False
                                
                        elif 'network' in endpoint['url'] and 'stats' in endpoint['url']:
                            hashrate = data.get('hashrate', 0)
                            if hashrate > 500:
                                key_info = f"算力: {hashrate:.1f}EH/s"
                            else:
                                data_valid = False
                                
                        elif 'miners' in endpoint['url']:
                            miners = data.get('miners', [])
                            if len(miners) >= 8:
                                key_info = f"矿机: {len(miners)}种"
                            else:
                                data_valid = False
                                
                        elif 'analytics' in endpoint['url']:
                            if data.get('success') or data.get('data') or data.get('rsi_14') is not None:
                                key_info = "分析数据正常"
                            else:
                                data_valid = False
                                key_info = "分析数据异常"
                        
                        if has_data and data_valid:
                            self.log_test(f"API端点-{endpoint['name']}", "PASS",
                                        f"{key_info}", response_time, "api")
                        else:
                            self.log_test(f"API端点-{endpoint['name']}", "FAIL",
                                        f"数据验证失败: {key_info}", response_time, "api")
                    except json.JSONDecodeError:
                        self.log_test(f"API端点-{endpoint['name']}", "FAIL",
                                    "JSON解析失败", response_time, "api")
                else:
                    self.log_test(f"API端点-{endpoint['name']}", "FAIL",
                                f"HTTP {response.status_code}", response_time, "api")
                    
            except Exception as e:
                self.log_test(f"API端点-{endpoint['name']}", "FAIL",
                            f"请求异常: {str(e)}", None, "api")

    def test_frontend_pages_comprehensive(self):
        """全面测试前端页面"""
        logging.info("=== 全面测试前端页面 ===")
        
        frontend_pages = [
            {
                'url': '/',
                'name': '主页挖矿计算器',
                'expected_elements': ['矿机型号', '计算', 'BTC', '算力', '功耗'],
                'required_functions': ['<form', '<select', '<input', '<button']
            },
            {
                'url': '/crm/dashboard',
                'name': 'CRM仪表盘',
                'expected_elements': ['客户管理', '仪表盘', '概览'],
                'required_functions': ['<a', '<div', 'dashboard']
            },
            {
                'url': '/crm/customers',
                'name': 'CRM客户列表',
                'expected_elements': ['客户', '列表', '新建'],
                'required_functions': ['<table', '<thead', '<tbody']
            },
            {
                'url': '/network_history',
                'name': '网络历史分析',
                'expected_elements': ['网络历史', '数据分析', '趋势'],
                'required_functions': ['<script', 'chart', 'canvas']
            },
            {
                'url': '/curtailment_calculator',
                'name': '电力削减计算器',
                'expected_elements': ['削减计算', '电力', '月度', '收益'],
                'required_functions': ['<form', '<input', 'calculate']
            },
            {
                'url': '/analytics_dashboard',
                'name': '数据分析仪表盘',
                'expected_elements': ['分析', '市场数据', '技术指标'],
                'required_functions': ['<div', 'analytics', 'dashboard']
            },
            {
                'url': '/algorithm_test',
                'name': '算法差异测试',
                'expected_elements': ['算法', '测试', '差异', '对比'],
                'required_functions': ['<form', '<input', 'test']
            },
            {
                'url': '/user_access',
                'name': '用户权限管理',
                'expected_elements': ['用户', '权限', '管理'],
                'required_functions': ['<table', '<form', 'access']
            }
        ]
        
        for page in frontend_pages:
            try:
                start_time = time.time()
                response = self.session.get(f"{self.base_url}{page['url']}")
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    page_content = response.text.lower()
                    
                    # 检查页面元素
                    elements_found = [elem for elem in page['expected_elements'] 
                                    if elem.lower() in page_content]
                    element_coverage = len(elements_found) / len(page['expected_elements'])
                    
                    # 检查功能元素
                    functions_found = [func for func in page['required_functions'] 
                                     if func.lower() in page_content]
                    function_coverage = len(functions_found) / len(page['required_functions'])
                    
                    # 页面加载时间验证
                    performance_ok = response_time < 2.0
                    
                    if element_coverage >= 0.6 and function_coverage >= 0.5 and performance_ok:
                        self.log_test(f"前端页面-{page['name']}", "PASS",
                                    f"元素: {element_coverage:.1%}, 功能: {function_coverage:.1%}",
                                    response_time, "frontend")
                    else:
                        self.log_test(f"前端页面-{page['name']}", "FAIL",
                                    f"覆盖不足 - 元素: {element_coverage:.1%}, 功能: {function_coverage:.1%}, "
                                    f"性能: {performance_ok}", response_time, "frontend")
                else:
                    self.log_test(f"前端页面-{page['name']}", "FAIL",
                                f"页面无法访问: HTTP {response.status_code}",
                                response_time, "frontend")
                    
            except Exception as e:
                self.log_test(f"前端页面-{page['name']}", "FAIL",
                            f"页面测试异常: {str(e)}", None, "frontend")

    def test_mining_calculations_comprehensive(self):
        """全面测试挖矿计算功能"""
        logging.info("=== 全面测试挖矿计算功能 ===")
        
        # 多种挖矿计算场景
        calculation_scenarios = [
            {
                'name': 'S19 Pro单台标准测试',
                'data': {
                    'miner_model': 'Antminer S19 Pro',
                    'miner_count': '1',
                    'electricity_cost': '0.06'
                },
                'validation': lambda r: (
                    r.get('inputs', {}).get('hashrate', 0) > 0 and
                    r.get('btc_mined', {}).get('daily', 0) > 0
                )
            },
            {
                'name': 'S21高效能测试',
                'data': {
                    'miner_model': 'Antminer S21',
                    'miner_count': '1',
                    'electricity_cost': '0.05'
                },
                'validation': lambda r: (
                    r.get('inputs', {}).get('hashrate', 0) > 0 and
                    r.get('btc_mined', {}).get('daily', 0) > 0
                )
            },
            {
                'name': '中等规模矿场测试',
                'data': {
                    'miner_model': 'Antminer S19 Pro',
                    'miner_count': '10',
                    'electricity_cost': '0.04',
                    'site_power': '1.0'
                },
                'validation': lambda r: (
                    r.get('inputs', {}).get('hashrate', 0) > 1000 and
                    r.get('btc_mined', {}).get('monthly', 0) > 0.1
                )
            },
            {
                'name': '大规模矿场测试',
                'data': {
                    'miner_model': 'Antminer S19 Pro',
                    'miner_count': '100',
                    'electricity_cost': '0.03',
                    'site_power': '10.0'
                },
                'validation': lambda r: (
                    r.get('inputs', {}).get('hashrate', 0) > 10000 and
                    r.get('btc_mined', {}).get('yearly', 0) > 1.0
                )
            },
            {
                'name': '电力削减场景测试',
                'data': {
                    'miner_model': 'Antminer S19 Pro',
                    'miner_count': '50',
                    'electricity_cost': '0.05',
                    'curtailment_rate': '15'
                },
                'validation': lambda r: (
                    r.get('success') == True and
                    r.get('inputs', {}).get('hashrate', 0) > 0
                )
            }
        ]
        
        for scenario in calculation_scenarios:
            try:
                start_time = time.time()
                response = self.session.post(f"{self.base_url}/calculate", data=scenario['data'])
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    result = response.json()
                    
                    if result.get('success') and scenario['validation'](result):
                        inputs = result.get('inputs', {})
                        btc_mined = result.get('btc_mined', {})
                        
                        hashrate = inputs.get('hashrate', 0)
                        daily_btc = btc_mined.get('daily', 0)
                        
                        self.log_test(f"挖矿计算-{scenario['name']}", "PASS",
                                    f"算力: {hashrate}TH/s, 日产: {daily_btc:.6f}BTC",
                                    response_time, "calculation")
                    else:
                        error_msg = result.get('error', 'Validation failed')
                        self.log_test(f"挖矿计算-{scenario['name']}", "FAIL",
                                    f"计算验证失败: {error_msg}", response_time, "calculation")
                else:
                    self.log_test(f"挖矿计算-{scenario['name']}", "FAIL",
                                f"HTTP错误: {response.status_code}", response_time, "calculation")
                    
            except Exception as e:
                self.log_test(f"挖矿计算-{scenario['name']}", "FAIL",
                            f"计算异常: {str(e)}", None, "calculation")

    def test_analytics_system_comprehensive(self):
        """全面测试分析系统"""
        logging.info("=== 全面测试分析系统 ===")
        
        # 分析系统组件测试
        analytics_tests = [
            {
                'url': '/api/analytics/market-data',
                'name': '市场数据收集',
                'validation': lambda d: d.get('success') and d.get('data', {}).get('btc_price', 0) > 50000
            },
            {
                'url': '/api/analytics/latest-report',
                'name': '分析报告生成',
                'validation': lambda d: d.get('summary') or d.get('recommendations')
            },
            {
                'url': '/api/analytics/technical-indicators',
                'name': '技术指标计算',
                'validation': lambda d: d.get('rsi_14') is not None or d.get('sma_20') is not None
            },
            {
                'url': '/api/analytics/price-history',
                'name': '价格历史数据',
                'validation': lambda d: isinstance(d, list) and len(d) > 0
            }
        ]
        
        for test in analytics_tests:
            try:
                start_time = time.time()
                response = self.session.get(f"{self.base_url}{test['url']}")
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        
                        if test['validation'](data):
                            # 提取关键信息
                            key_info = ""
                            if 'market-data' in test['url'] and data.get('data'):
                                price = data['data'].get('btc_price', 0)
                                key_info = f"BTC: ${price:,.0f}"
                            elif 'technical' in test['url']:
                                rsi = data.get('rsi_14')
                                key_info = f"RSI: {rsi}" if rsi else "技术指标正常"
                            elif 'history' in test['url']:
                                key_info = f"历史记录: {len(data)}条"
                            else:
                                key_info = "数据正常"
                                
                            self.log_test(f"分析系统-{test['name']}", "PASS",
                                        key_info, response_time, "analytics")
                        else:
                            self.log_test(f"分析系统-{test['name']}", "FAIL",
                                        "数据验证失败", response_time, "analytics")
                    except json.JSONDecodeError:
                        self.log_test(f"分析系统-{test['name']}", "FAIL",
                                    "JSON解析失败", response_time, "analytics")
                else:
                    self.log_test(f"分析系统-{test['name']}", "FAIL",
                                f"HTTP {response.status_code}", response_time, "analytics")
                    
            except Exception as e:
                self.log_test(f"分析系统-{test['name']}", "FAIL",
                            f"请求异常: {str(e)}", None, "analytics")

    def test_crm_system_comprehensive(self):
        """全面测试CRM系统"""
        logging.info("=== 全面测试CRM系统 ===")
        
        # CRM系统页面和功能测试
        crm_tests = [
            {'url': '/crm/dashboard', 'name': 'CRM仪表盘'},
            {'url': '/crm/customers', 'name': 'CRM客户列表'},
            {'url': '/crm/leads', 'name': 'CRM商机列表'},
            {'url': '/crm/deals', 'name': 'CRM交易列表'},
            {'url': '/crm/activities', 'name': 'CRM活动记录'},
        ]
        
        for test in crm_tests:
            try:
                start_time = time.time()
                response = self.session.get(f"{self.base_url}{test['url']}")
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    content = response.text.lower()
                    
                    # 检查CRM相关元素
                    crm_elements = ['客户', 'customer', 'crm', '管理', '列表']
                    elements_found = sum(1 for elem in crm_elements if elem in content)
                    
                    # 检查功能元素
                    function_elements = ['<table', '<form', '<button', '<a']
                    functions_found = sum(1 for func in function_elements if func in content)
                    
                    if elements_found >= 2 and functions_found >= 2:
                        self.log_test(f"CRM系统-{test['name']}", "PASS",
                                    f"元素: {elements_found}, 功能: {functions_found}",
                                    response_time, "crm")
                    else:
                        self.log_test(f"CRM系统-{test['name']}", "FAIL",
                                    f"元素不足: {elements_found}, 功能: {functions_found}",
                                    response_time, "crm")
                else:
                    self.log_test(f"CRM系统-{test['name']}", "FAIL",
                                f"HTTP {response.status_code}", response_time, "crm")
                    
            except Exception as e:
                self.log_test(f"CRM系统-{test['name']}", "FAIL",
                            f"请求异常: {str(e)}", None, "crm")

    def test_system_performance(self):
        """测试系统性能"""
        logging.info("=== 测试系统性能 ===")
        
        # 并发性能测试
        concurrent_requests = [
            '/get_btc_price',
            '/get_network_stats',
            '/get_miners',
            '/api/analytics/market-data'
        ]
        
        # 批量请求测试
        start_time = time.time()
        all_responses = []
        
        for endpoint in concurrent_requests:
            try:
                response = self.session.get(f"{self.base_url}{endpoint}")
                all_responses.append(response.status_code == 200)
            except:
                all_responses.append(False)
        
        batch_time = time.time() - start_time
        success_rate = sum(all_responses) / len(all_responses)
        
        if success_rate >= 0.75 and batch_time < 5.0:
            self.log_test("系统性能-并发请求", "PASS",
                        f"成功率: {success_rate:.1%}, 批次时间: {batch_time:.2f}s",
                        batch_time, "performance")
        else:
            self.log_test("系统性能-并发请求", "FAIL",
                        f"性能不达标: 成功率{success_rate:.1%}, 时间{batch_time:.2f}s",
                        batch_time, "performance")
        
        # 响应时间统计
        if self.response_times:
            avg_response = sum(self.response_times) / len(self.response_times)
            max_response = max(self.response_times)
            min_response = min(self.response_times)
            
            performance_acceptable = avg_response < 1.0 and max_response < 3.0
            
            if performance_acceptable:
                self.log_test("系统性能-响应时间", "PASS",
                            f"平均: {avg_response:.3f}s, 最大: {max_response:.3f}s, 最小: {min_response:.3f}s",
                            avg_response, "performance")
            else:
                self.log_test("系统性能-响应时间", "FAIL",
                            f"响应时间过长: 平均{avg_response:.3f}s, 最大{max_response:.3f}s",
                            avg_response, "performance")

    def test_data_consistency(self):
        """测试数据一致性"""
        logging.info("=== 测试数据一致性 ===")
        
        try:
            # 获取多个源的BTC价格进行一致性检查
            price_sources = []
            
            # 源1: 直接API
            try:
                response = self.session.get(f"{self.base_url}/get_btc_price")
                if response.status_code == 200:
                    data = response.json()
                    price_sources.append(('API价格', data.get('price', 0)))
            except:
                pass
            
            # 源2: 分析系统
            try:
                response = self.session.get(f"{self.base_url}/api/analytics/market-data")
                if response.status_code == 200:
                    data = response.json()
                    analytics_price = data.get('data', {}).get('btc_price', 0)
                    price_sources.append(('分析价格', analytics_price))
            except:
                pass
            
            # 检查价格一致性
            if len(price_sources) >= 2:
                prices = [price for _, price in price_sources]
                max_price = max(prices)
                min_price = min(prices)
                price_variance = (max_price - min_price) / max_price if max_price > 0 else 0
                
                if price_variance < 0.1:  # 10%以内的差异是可接受的
                    self.log_test("数据一致性-价格数据", "PASS",
                                f"价格差异: {price_variance:.1%}, 来源: {len(price_sources)}个",
                                None, "consistency")
                else:
                    self.log_test("数据一致性-价格数据", "FAIL",
                                f"价格差异过大: {price_variance:.1%}",
                                None, "consistency")
            else:
                self.log_test("数据一致性-价格数据", "FAIL",
                            "价格数据源不足", None, "consistency")
                
            # 测试计算结果一致性
            calculation_data = {
                'miner_model': 'Antminer S19 Pro',
                'miner_count': '1',
                'electricity_cost': '0.06'
            }
            
            # 进行两次相同计算
            results = []
            for i in range(2):
                try:
                    response = self.session.post(f"{self.base_url}/calculate", data=calculation_data)
                    if response.status_code == 200:
                        result = response.json()
                        if result.get('success'):
                            daily_btc = result.get('btc_mined', {}).get('daily', 0)
                            results.append(daily_btc)
                except:
                    pass
            
            if len(results) == 2:
                variance = abs(results[0] - results[1]) / results[0] if results[0] > 0 else 0
                if variance < 0.01:  # 1%以内的差异
                    self.log_test("数据一致性-计算结果", "PASS",
                                f"计算一致性: {variance:.3%}",
                                None, "consistency")
                else:
                    self.log_test("数据一致性-计算结果", "FAIL",
                                f"计算结果不一致: {variance:.3%}",
                                None, "consistency")
            else:
                self.log_test("数据一致性-计算结果", "FAIL",
                            "无法进行一致性检查", None, "consistency")
                
        except Exception as e:
            self.log_test("数据一致性-测试异常", "FAIL",
                        f"一致性测试异常: {str(e)}", None, "consistency")

    def generate_comprehensive_report(self):
        """生成完整测试报告"""
        test_duration = time.time() - self.test_start_time
        success_rate = (self.passed_tests / self.total_tests * 100) if self.total_tests > 0 else 0
        
        # 按类别统计
        categories = {}
        for result in self.test_results:
            category = result['test_category']
            if category not in categories:
                categories[category] = {'total': 0, 'passed': 0}
            categories[category]['total'] += 1
            if result['status'] == 'PASS':
                categories[category]['passed'] += 1
        
        # 性能统计
        avg_response_time = sum(self.response_times) / len(self.response_times) if self.response_times else 0
        
        report = {
            'test_summary': {
                'total_tests': self.total_tests,
                'passed_tests': self.passed_tests,
                'failed_tests': self.failed_tests,
                'success_rate': round(success_rate, 1),
                'test_duration': round(test_duration, 2),
                'avg_response_time': round(avg_response_time, 3),
                'test_timestamp': datetime.now().isoformat()
            },
            'category_breakdown': categories,
            'detailed_results': self.test_results,
            'performance_metrics': {
                'total_requests': len(self.response_times),
                'avg_response_time': avg_response_time,
                'max_response_time': max(self.response_times) if self.response_times else 0,
                'min_response_time': min(self.response_times) if self.response_times else 0
            }
        }
        
        # 保存报告
        with open('complete_system_regression_report.json', 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        # 生成摘要
        logging.info("=== 完整系统回归测试报告 ===")
        logging.info(f"📊 测试总数: {self.total_tests}")
        logging.info(f"✅ 通过测试: {self.passed_tests}")
        logging.info(f"❌ 失败测试: {self.failed_tests}")
        logging.info(f"📈 成功率: {success_rate:.1f}%")
        logging.info(f"⏱️ 测试耗时: {test_duration:.2f}秒")
        logging.info(f"🚀 平均响应时间: {avg_response_time:.3f}秒")
        logging.info("")
        logging.info("📋 分类统计:")
        for category, stats in categories.items():
            category_rate = (stats['passed'] / stats['total'] * 100) if stats['total'] > 0 else 0
            logging.info(f"  {category}: {stats['passed']}/{stats['total']} ({category_rate:.1f}%)")
        
        logging.info(f"📄 详细报告已保存: complete_system_regression_report.json")
        
        return report

    def run_complete_regression_test(self):
        """运行完整回归测试"""
        logging.info("🚀 开始完整系统回归测试")
        logging.info("🎯 全面验证系统所有组件和功能")
        
        # 用户认证
        if not self.authenticate():
            logging.error("用户认证失败，测试终止")
            return None
        
        # 执行所有测试模块
        self.test_database_infrastructure()
        self.test_api_endpoints_comprehensive()
        self.test_frontend_pages_comprehensive()
        self.test_mining_calculations_comprehensive()
        self.test_analytics_system_comprehensive()
        self.test_crm_system_comprehensive()
        self.test_system_performance()
        self.test_data_consistency()
        
        # 生成报告
        report = self.generate_comprehensive_report()
        return report

def main():
    """主函数"""
    tester = CompleteSystemRegressionTest()
    report = tester.run_complete_regression_test()
    
    if report:
        print("\n" + "="*60)
        print("完整系统回归测试总结")
        print("="*60)
        print(f"总测试数: {report['test_summary']['total_tests']}")
        print(f"通过测试: {report['test_summary']['passed_tests']}")
        print(f"失败测试: {report['test_summary']['failed_tests']}")
        print(f"成功率: {report['test_summary']['success_rate']}%")
        print(f"测试耗时: {report['test_summary']['test_duration']}秒")
        print(f"平均响应时间: {report['test_summary']['avg_response_time']}秒")
        print("="*60)

if __name__ == "__main__":
    main()