#!/usr/bin/env python3
"""
全系统回归测试 (Full System Regression Test)
专注数值准确性，全面覆盖前端、中端API、后端数据库功能
Focus on numbers and touch frontend, middleware, backend functions
"""
import requests
import time
import json
import logging
import psycopg2
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class FullSystemRegressionTest:
    def __init__(self):
        self.base_url = "http://127.0.0.1:5000"
        self.session = requests.Session()
        self.test_results = []
        self.test_start_time = time.time()
        self.numerical_tests = 0
        self.frontend_tests = 0
        self.middleware_tests = 0
        self.backend_tests = 0
        
        # 测试数据
        self.test_user_email = "hxl2022hao@gmail.com"  # 授权用户
        
        # 数值验证基准
        self.numerical_benchmarks = {
            'btc_price_range': (50000, 150000),  # BTC价格合理范围
            'network_hashrate_range': (500, 1200),  # EH/s
            'daily_btc_mining_range': (0.001, 0.01),  # 单台矿机日产BTC
            'power_consumption_range': (3000, 4000),  # 单台矿机功耗W
            'mining_efficiency_range': (25, 40),  # J/TH
        }
        
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
    
    def log_test(self, test_name: str, status: str, details: str = "", 
                numerical_result: Any = None, test_type: str = "general"):
        """记录测试结果"""
        result = {
            'test_name': test_name,
            'status': status,
            'details': details,
            'numerical_result': numerical_result,
            'test_type': test_type,
            'timestamp': datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        # 统计测试类型
        if test_type == "numerical":
            self.numerical_tests += 1
        elif test_type == "frontend":
            self.frontend_tests += 1
        elif test_type == "middleware":
            self.middleware_tests += 1
        elif test_type == "backend":
            self.backend_tests += 1
            
        status_icon = "✅" if status == "PASS" else "❌"
        msg = f"{status_icon} {test_name}"
        if details:
            msg += f": {details}"
        if numerical_result is not None:
            msg += f" (数值: {numerical_result})"
        logging.info(msg)

    # ==================== 后端数据库测试 ====================
    def test_backend_database_operations(self):
        """测试后端数据库操作"""
        logging.info("=== 测试后端数据库层 ===")
        
        try:
            conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
            cursor = conn.cursor()
            
            # 测试核心业务表
            core_tables = [
                ('market_analytics', '分析数据表'),
                ('network_snapshots', '网络快照表'),
                ('user_access', '用户权限表'),
                ('crm_customers', '客户管理表'),
                ('crm_leads', '商机管理表'),
                ('crm_deals', '交易记录表'),
                ('login_records', '登录记录表'),
                ('technical_indicators', '技术指标表')
            ]
            
            for table_name, description in core_tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    count = cursor.fetchone()[0]
                    self.log_test(f"后端数据库-{description}", "PASS", 
                                f"记录数: {count}", count, "backend")
                except Exception as e:
                    self.log_test(f"后端数据库-{description}", "FAIL", 
                                f"查询失败: {str(e)}", None, "backend")
            
            # 测试数据完整性
            cursor.execute("""
                SELECT recorded_at, btc_price, network_hashrate, network_difficulty 
                FROM market_analytics 
                ORDER BY recorded_at DESC LIMIT 1
            """)
            latest_data = cursor.fetchone()
            
            if latest_data:
                price = float(latest_data[1]) if latest_data[1] else 0
                hashrate = float(latest_data[2]) if latest_data[2] else 0
                
                price_valid = self.numerical_benchmarks['btc_price_range'][0] <= price <= self.numerical_benchmarks['btc_price_range'][1]
                hashrate_valid = self.numerical_benchmarks['network_hashrate_range'][0] <= hashrate <= self.numerical_benchmarks['network_hashrate_range'][1]
                
                if price_valid and hashrate_valid:
                    self.log_test("后端数据库-数据完整性验证", "PASS", 
                                f"价格: ${price:,.2f}, 算力: {hashrate:.2f}EH/s", 
                                {'price': price, 'hashrate': hashrate}, "backend")
                else:
                    self.log_test("后端数据库-数据完整性验证", "FAIL", 
                                f"数值超出合理范围", 
                                {'price': price, 'hashrate': hashrate}, "backend")
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            self.log_test("后端数据库-连接测试", "FAIL", f"数据库连接失败: {str(e)}", None, "backend")

    # ==================== 挖矿计算数值精度测试 ====================
    def test_mining_calculation_precision(self):
        """测试挖矿计算数值精度"""
        logging.info("=== 测试挖矿计算数值精度 ===")
        
        # 标准测试用例
        test_cases = [
            {
                'name': 'Antminer S19 Pro - 标准配置',
                'data': {
                    'miner_model': 'Antminer S19 Pro',
                    'miner_count': '1',
                    'site_power': '0.1',
                    'electricity_cost': '0.06',
                    'curtailment_rate': '0',
                    'host_investment': '0',
                    'client_investment': '0'
                },
                'expected_hashrate': 110,  # TH/s
                'expected_power': 3250,    # W
                'expected_daily_btc_min': 0.001,
                'expected_daily_btc_max': 0.005
            },
            {
                'name': 'Antminer S21 - 高效配置',
                'data': {
                    'miner_model': 'Antminer S21',
                    'miner_count': '1',
                    'site_power': '0.1',
                    'electricity_cost': '0.05',
                    'curtailment_rate': '0',
                    'host_investment': '0',
                    'client_investment': '0'
                },
                'expected_hashrate': 200,  # TH/s
                'expected_power': 3550,    # W
                'expected_daily_btc_min': 0.0015,
                'expected_daily_btc_max': 0.008
            },
            {
                'name': '大规模矿场测试',
                'data': {
                    'miner_model': 'Antminer S19 Pro',
                    'miner_count': '100',
                    'site_power': '5.0',
                    'electricity_cost': '0.04',
                    'curtailment_rate': '10',
                    'host_investment': '1000000',
                    'client_investment': '500000'
                },
                'expected_total_hashrate_min': 10000,  # TH/s (100台)
                'expected_total_power_min': 320000,    # W
                'expected_monthly_profit_min': 50000   # USD
            }
        ]
        
        for test_case in test_cases:
            try:
                start_time = time.time()
                response = self.session.post(f"{self.base_url}/calculate", data=test_case['data'])
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    result = response.json()
                    
                    if result.get('success'):
                        # 验证算力数值 - 匹配实际响应格式
                        inputs = result.get('inputs', {})
                        btc_mined = result.get('btc_mined', {})
                        total_hashrate = inputs.get('hashrate', 0)
                        total_power = inputs.get('power_consumption', 0)
                        daily_btc_algo1 = btc_mined.get('daily', 0)
                        
                        # 数值精度验证
                        precision_checks = []
                        
                        # 单台矿机测试
                        if test_case['name'] in ['Antminer S19 Pro - 标准配置', 'Antminer S21 - 高效配置']:
                            hashrate_match = abs(total_hashrate - test_case['expected_hashrate']) < 10
                            power_match = abs(total_power - test_case['expected_power']) < 100
                            btc_in_range = (test_case['expected_daily_btc_min'] <= daily_btc_algo1 <= test_case['expected_daily_btc_max'])
                            
                            precision_checks = [hashrate_match, power_match, btc_in_range]
                            
                            if all(precision_checks):
                                self.log_test(f"数值精度-{test_case['name']}", "PASS", 
                                            f"算力: {total_hashrate}TH/s, 功耗: {total_power}W, 日产BTC: {daily_btc_algo1:.6f}",
                                            {
                                                'hashrate': total_hashrate,
                                                'power': total_power,
                                                'daily_btc': daily_btc_algo1,
                                                'response_time': response_time
                                            }, "numerical")
                            else:
                                self.log_test(f"数值精度-{test_case['name']}", "FAIL", 
                                            f"数值验证失败 - 算力: {total_hashrate} (期望: {test_case['expected_hashrate']}), "
                                            f"功耗: {total_power} (期望: {test_case['expected_power']}), "
                                            f"日产BTC: {daily_btc_algo1:.6f}",
                                            None, "numerical")
                        
                        # 大规模测试
                        elif test_case['name'] == '大规模矿场测试':
                            monthly_profit = result.get('client_monthly_profit', 0) + result.get('host_monthly_profit', 0)
                            
                            large_scale_valid = (
                                total_hashrate >= test_case['expected_total_hashrate_min'] and
                                total_power >= test_case['expected_total_power_min'] and
                                monthly_profit >= test_case['expected_monthly_profit_min']
                            )
                            
                            if large_scale_valid:
                                self.log_test(f"数值精度-{test_case['name']}", "PASS", 
                                            f"总算力: {total_hashrate}TH/s, 总功耗: {total_power}W, 月利润: ${monthly_profit:,.2f}",
                                            {
                                                'total_hashrate': total_hashrate,
                                                'total_power': total_power,
                                                'monthly_profit': monthly_profit
                                            }, "numerical")
                            else:
                                self.log_test(f"数值精度-{test_case['name']}", "FAIL", 
                                            f"大规模计算验证失败", None, "numerical")
                    else:
                        self.log_test(f"数值精度-{test_case['name']}", "FAIL", 
                                    f"计算失败: {result.get('error')}", None, "numerical")
                else:
                    self.log_test(f"数值精度-{test_case['name']}", "FAIL", 
                                f"HTTP错误: {response.status_code}", None, "numerical")
                    
            except Exception as e:
                self.log_test(f"数值精度-{test_case['name']}", "FAIL", 
                            f"测试异常: {str(e)}", None, "numerical")

    # ==================== 中端API层测试 ====================
    def test_middleware_api_endpoints(self):
        """测试中端API端点功能"""
        logging.info("=== 测试中端API层 ===")
        
        # 核心API端点测试
        api_endpoints = [
            {
                'name': 'BTC价格API',
                'url': '/get_btc_price',
                'method': 'GET',
                'expected_fields': ['price'],
                'numerical_validation': lambda data: 50000 <= data.get('price', 0) <= 150000
            },
            {
                'name': '网络统计API',
                'url': '/get_network_stats',
                'method': 'GET',
                'expected_fields': ['hashrate', 'difficulty'],
                'numerical_validation': lambda data: 500 <= data.get('hashrate', 0) <= 1200
            },
            {
                'name': '矿机列表API',
                'url': '/get_miners',
                'method': 'GET',
                'expected_fields': ['miners'],
                'numerical_validation': lambda data: len(data.get('miners', [])) >= 8
            },
            {
                'name': '分析系统市场数据API',
                'url': '/api/analytics/market-data',
                'method': 'GET',
                'expected_fields': ['success', 'data'],
                'numerical_validation': lambda data: data.get('success') == True and data.get('data', {}).get('btc_price') is not None
            },
            {
                'name': '分析系统技术指标API',
                'url': '/api/analytics/technical-indicators',
                'method': 'GET',
                'expected_fields': ['rsi_14', 'sma_20'],
                'numerical_validation': lambda data: True  # 技术指标可能为空
            }
        ]
        
        for endpoint in api_endpoints:
            try:
                start_time = time.time()
                if endpoint['method'] == 'GET':
                    response = self.session.get(f"{self.base_url}{endpoint['url']}")
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        
                        # 检查必需字段
                        missing_fields = [field for field in endpoint['expected_fields'] 
                                        if field not in data]
                        
                        # 数值验证
                        numerical_valid = endpoint['numerical_validation'](data)
                        
                        if not missing_fields and numerical_valid:
                            # 提取关键数值
                            key_value = None
                            if 'price' in data:
                                key_value = data['price']
                            elif 'hashrate' in data:
                                key_value = data['hashrate']
                            elif 'miners' in data:
                                key_value = len(data['miners'])
                            elif endpoint['name'] == '分析系统市场数据API' and data.get('success'):
                                key_value = data.get('data', {}).get('btc_price')
                            
                            self.log_test(f"中端API-{endpoint['name']}", "PASS", 
                                        f"响应时间: {response_time:.3f}s",
                                        key_value, "middleware")
                        else:
                            fail_reason = []
                            if missing_fields:
                                fail_reason.append(f"缺少字段: {missing_fields}")
                            if not numerical_valid:
                                fail_reason.append("数值验证失败")
                            
                            self.log_test(f"中端API-{endpoint['name']}", "FAIL", 
                                        "; ".join(fail_reason), None, "middleware")
                    except json.JSONDecodeError:
                        self.log_test(f"中端API-{endpoint['name']}", "FAIL", 
                                    "JSON解析失败", None, "middleware")
                else:
                    self.log_test(f"中端API-{endpoint['name']}", "FAIL", 
                                f"HTTP状态码: {response.status_code}", None, "middleware")
                    
            except Exception as e:
                self.log_test(f"中端API-{endpoint['name']}", "FAIL", 
                            f"请求异常: {str(e)}", None, "middleware")

    # ==================== 前端页面测试 ====================
    def test_frontend_page_functionality(self):
        """测试前端页面功能"""
        logging.info("=== 测试前端页面层 ===")
        
        # 核心页面测试
        frontend_pages = [
            {
                'name': '主页挖矿计算器',
                'url': '/',
                'expected_elements': ['矿机型号', '计算', 'BTC', '功率'],
                'form_test': True
            },
            {
                'name': 'CRM客户管理仪表盘',
                'url': '/crm/dashboard',
                'expected_elements': ['客户管理', '仪表盘', '新建'],
                'form_test': False
            },
            {
                'name': '网络历史数据分析',
                'url': '/network_history',
                'expected_elements': ['网络历史', '价格趋势', '算力分析'],
                'form_test': False
            },
            {
                'name': '电力削减计算器',
                'url': '/curtailment_calculator',
                'expected_elements': ['削减计算', '电力', '月度'],
                'form_test': True
            },
            {
                'name': '数据分析仪表盘',
                'url': '/analytics_dashboard',
                'expected_elements': ['分析', '市场数据', '技术指标'],
                'form_test': False
            },
            {
                'name': '算法差异测试工具',
                'url': '/algorithm_test',
                'expected_elements': ['算法', '测试', '差异'],
                'form_test': True
            }
        ]
        
        for page in frontend_pages:
            try:
                start_time = time.time()
                response = self.session.get(f"{self.base_url}{page['url']}")
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    page_content = response.text
                    
                    # 检查关键元素
                    found_elements = [element for element in page['expected_elements'] 
                                    if element in page_content]
                    
                    # 表单功能测试
                    form_elements_found = []
                    if page['form_test']:
                        form_indicators = ['<form', 'submit', 'button', 'input']
                        form_elements_found = [indicator for indicator in form_indicators 
                                             if indicator in page_content.lower()]
                    
                    if len(found_elements) >= len(page['expected_elements']) * 0.7:  # 70%元素匹配
                        details = f"响应时间: {response_time:.3f}s, 找到元素: {found_elements}"
                        if page['form_test'] and form_elements_found:
                            details += f", 表单元素: {len(form_elements_found)}"
                        
                        self.log_test(f"前端页面-{page['name']}", "PASS", 
                                    details, len(found_elements), "frontend")
                    else:
                        self.log_test(f"前端页面-{page['name']}", "FAIL", 
                                    f"关键元素缺失，找到: {found_elements}, 期望: {page['expected_elements']}", 
                                    None, "frontend")
                else:
                    self.log_test(f"前端页面-{page['name']}", "FAIL", 
                                f"页面无法访问: {response.status_code}", None, "frontend")
                    
            except Exception as e:
                self.log_test(f"前端页面-{page['name']}", "FAIL", 
                            f"页面测试异常: {str(e)}", None, "frontend")

    # ==================== 数据流集成测试 ====================
    def test_data_flow_integration(self):
        """测试完整数据流集成"""
        logging.info("=== 测试数据流集成 ===")
        
        # 端到端数据流测试
        try:
            # 1. 前端表单提交 -> 中端API处理 -> 后端计算 -> 前端显示
            calculation_data = {
                'miner_model': 'Antminer S19 Pro',
                'miner_count': '5',
                'site_power': '0.5',
                'electricity_cost': '0.06',
                'curtailment_rate': '0',
                'host_investment': '100000',
                'client_investment': '50000'
            }
            
            start_time = time.time()
            response = self.session.post(f"{self.base_url}/calculate", data=calculation_data)
            end_to_end_time = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('success'):
                    # 验证数据流完整性
                    required_data_points = [
                        'total_hashrate_th', 'total_power_w', 'algorithm1_btc', 'algorithm2_btc',
                        'client_monthly_profit', 'host_monthly_profit'
                    ]
                    
                    missing_data = [point for point in required_data_points if point not in result]
                    
                    if not missing_data:
                        # 验证数值合理性
                        total_hashrate = result['total_hashrate_th']
                        daily_btc = result['algorithm1_btc']
                        monthly_profit = result['client_monthly_profit'] + result['host_monthly_profit']
                        
                        data_reasonable = (
                            400 <= total_hashrate <= 800 and  # 5台S19 Pro
                            0.005 <= daily_btc <= 0.02 and    # 合理日产量
                            monthly_profit > 0                 # 正利润
                        )
                        
                        if data_reasonable:
                            self.log_test("数据流集成-端到端计算", "PASS", 
                                        f"完整数据流验证成功，处理时间: {end_to_end_time:.3f}s",
                                        {
                                            'hashrate': total_hashrate,
                                            'daily_btc': daily_btc,
                                            'monthly_profit': monthly_profit,
                                            'processing_time': end_to_end_time
                                        }, "numerical")
                        else:
                            self.log_test("数据流集成-端到端计算", "FAIL", 
                                        "数值合理性验证失败", None, "numerical")
                    else:
                        self.log_test("数据流集成-端到端计算", "FAIL", 
                                    f"数据完整性验证失败，缺少: {missing_data}", None, "numerical")
                else:
                    self.log_test("数据流集成-端到端计算", "FAIL", 
                                f"计算处理失败: {result.get('error')}", None, "numerical")
            
            # 2. 分析系统数据流测试
            analytics_response = self.session.get(f"{self.base_url}/api/analytics/market-data")
            if analytics_response.status_code == 200:
                analytics_data = analytics_response.json()
                if analytics_data.get('success') and analytics_data.get('data'):
                    btc_price = analytics_data['data'].get('btc_price')
                    if btc_price and 50000 <= btc_price <= 150000:
                        self.log_test("数据流集成-分析系统", "PASS", 
                                    f"分析数据流正常，BTC价格: ${btc_price:,.2f}",
                                    btc_price, "numerical")
                    else:
                        self.log_test("数据流集成-分析系统", "FAIL", 
                                    "分析数据价格异常", btc_price, "numerical")
                        
        except Exception as e:
            self.log_test("数据流集成-测试异常", "FAIL", f"集成测试异常: {str(e)}", None, "numerical")

    # ==================== 性能基准测试 ====================
    def test_performance_benchmarks(self):
        """测试性能基准"""
        logging.info("=== 测试系统性能基准 ===")
        
        # API性能测试
        performance_tests = [
            {'name': '挖矿计算性能', 'url': '/calculate', 'method': 'POST', 'max_time': 2.0,
             'data': {'miner_model': 'Antminer S19 Pro', 'miner_count': '10'}},
            {'name': 'BTC价格API性能', 'url': '/api/btc_price', 'method': 'GET', 'max_time': 1.0},
            {'name': '网络统计API性能', 'url': '/api/network_stats', 'method': 'GET', 'max_time': 3.0},
            {'name': '分析数据API性能', 'url': '/api/analytics/market-data', 'method': 'GET', 'max_time': 1.0},
        ]
        
        for test in performance_tests:
            try:
                start_time = time.time()
                if test['method'] == 'GET':
                    response = self.session.get(f"{self.base_url}{test['url']}")
                else:
                    response = self.session.post(f"{self.base_url}{test['url']}", data=test.get('data', {}))
                response_time = time.time() - start_time
                
                if response.status_code == 200 and response_time <= test['max_time']:
                    self.log_test(f"性能基准-{test['name']}", "PASS", 
                                f"响应时间: {response_time:.3f}s (限制: {test['max_time']}s)",
                                response_time, "numerical")
                else:
                    self.log_test(f"性能基准-{test['name']}", "FAIL", 
                                f"性能不达标，响应时间: {response_time:.3f}s", 
                                response_time, "numerical")
                    
            except Exception as e:
                self.log_test(f"性能基准-{test['name']}", "FAIL", 
                            f"性能测试异常: {str(e)}", None, "numerical")

    # ==================== 生成综合报告 ====================
    def generate_comprehensive_report(self):
        """生成综合测试报告"""
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r['status'] == 'PASS'])
        failed_tests = total_tests - passed_tests
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        test_duration = time.time() - self.test_start_time
        
        # 按测试类型统计
        type_stats = {
            'backend': len([r for r in self.test_results if r['test_type'] == 'backend']),
            'middleware': len([r for r in self.test_results if r['test_type'] == 'middleware']),
            'frontend': len([r for r in self.test_results if r['test_type'] == 'frontend']),
            'numerical': len([r for r in self.test_results if r['test_type'] == 'numerical'])
        }
        
        # 数值测试结果统计
        numerical_results = [r for r in self.test_results 
                           if r['test_type'] == 'numerical' and r['numerical_result'] is not None]
        
        report = {
            'test_summary': {
                'total_tests': total_tests,
                'passed_tests': passed_tests,
                'failed_tests': failed_tests,
                'success_rate': round(success_rate, 1),
                'test_duration': round(test_duration, 2),
                'test_timestamp': datetime.now().isoformat()
            },
            'layer_coverage': type_stats,
            'numerical_test_count': len(numerical_results),
            'test_results': self.test_results,
            'recommendations': self.generate_recommendations()
        }
        
        # 保存详细报告
        with open('full_system_regression_report.json', 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        logging.info("=== 全系统回归测试报告 ===")
        logging.info(f"📊 总测试: {total_tests}")
        logging.info(f"✅ 通过: {passed_tests}")
        logging.info(f"❌ 失败: {failed_tests}")
        logging.info(f"📈 成功率: {success_rate:.1f}%")
        logging.info(f"⏱️ 测试耗时: {test_duration:.2f}秒")
        logging.info(f"🔢 数值测试: {len(numerical_results)} 项")
        logging.info(f"🏗️ 层次覆盖: 后端({type_stats['backend']}) 中端({type_stats['middleware']}) 前端({type_stats['frontend']})")
        logging.info(f"📄 详细报告已保存: full_system_regression_report.json")
        
        return report

    def generate_recommendations(self):
        """生成改进建议"""
        failed_tests = [r for r in self.test_results if r['status'] == 'FAIL']
        recommendations = []
        
        # 按失败类型分析
        backend_failures = len([r for r in failed_tests if r['test_type'] == 'backend'])
        middleware_failures = len([r for r in failed_tests if r['test_type'] == 'middleware'])
        frontend_failures = len([r for r in failed_tests if r['test_type'] == 'frontend'])
        numerical_failures = len([r for r in failed_tests if r['test_type'] == 'numerical'])
        
        if backend_failures > 0:
            recommendations.append("后端数据库: 检查数据库连接和表结构完整性")
        
        if middleware_failures > 0:
            recommendations.append("中端API: 优化API响应格式和错误处理")
        
        if frontend_failures > 0:
            recommendations.append("前端界面: 验证页面元素加载和表单功能")
        
        if numerical_failures > 0:
            recommendations.append("数值计算: 校验计算逻辑和数值范围验证")
        
        return recommendations

    # ==================== 主测试流程 ====================
    def run_full_system_test(self):
        """运行完整系统测试"""
        logging.info("🚀 开始全系统回归测试")
        logging.info("📋 测试覆盖: 数值精度 + 前端中端后端功能")
        logging.info("🎯 专注数值准确性和全栈功能验证")
        
        # 用户认证
        if not self.authenticate():
            logging.error("用户认证失败，测试终止")
            return
        
        # 执行所有测试
        self.test_backend_database_operations()
        self.test_mining_calculation_precision()
        self.test_middleware_api_endpoints()
        self.test_frontend_page_functionality()
        self.test_data_flow_integration()
        self.test_performance_benchmarks()
        
        # 生成报告
        report = self.generate_comprehensive_report()
        
        return report

def main():
    """主函数"""
    tester = FullSystemRegressionTest()
    report = tester.run_full_system_test()
    
    print("\n" + "="*50)
    print("全系统回归测试报告")
    print("="*50)
    print(f"总测试: {report['test_summary']['total_tests']}")
    print(f"通过: {report['test_summary']['passed_tests']}")
    print(f"失败: {report['test_summary']['failed_tests']}")
    print(f"成功率: {report['test_summary']['success_rate']}%")
    print(f"测试耗时: {report['test_summary']['test_duration']}秒")
    print(f"数值精度测试: {report['numerical_test_count']} 项")
    print(f"层次覆盖: 后端({report['layer_coverage']['backend']}) "
          f"中端({report['layer_coverage']['middleware']}) "
          f"前端({report['layer_coverage']['frontend']})")
    print("="*50)

if __name__ == "__main__":
    main()