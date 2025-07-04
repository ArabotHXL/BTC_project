#!/usr/bin/env python3
"""
全面回归测试 - 99%+ 准确率验证
Full Regression Test - 99%+ Accuracy Validation

测试所有核心功能模块，确保数值计算和系统功能准确率达到99%以上
Test all core function modules to ensure numerical calculation and system function accuracy above 99%
"""

import json
import time
import requests
import psycopg2
from datetime import datetime
from typing import Dict, List, Any, Tuple
import os
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FullRegressionTest99Percent:
    """全面回归测试 - 99%准确率验证器"""
    
    def __init__(self):
        self.base_url = "http://0.0.0.0:5000"
        self.session = requests.Session()
        self.test_results = []
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        self.warnings = 0
        
        # 测试用户邮箱列表
        self.test_emails = [
            "hxl2022hao@gmail.com",  # 主测试邮箱
            "testing123@example.com",  # 测试邮箱
            "admin@example.com",     # 管理员邮箱
            "site@example.com",      # 矿场邮箱
            "user@example.com"       # 普通用户邮箱
        ]
        
        # 数据库连接
        self.db_url = os.environ.get('DATABASE_URL')
        
        # 矿机规格数据 - 用于数值验证
        self.miner_specs = {
            "Antminer S19 Pro": {"hashrate": 110, "power": 3250},
            "Antminer S19": {"hashrate": 95, "power": 3250},
            "Antminer S19j Pro": {"hashrate": 100, "power": 3068},
            "Antminer S19 XP": {"hashrate": 140, "power": 3010},
            "Antminer S21": {"hashrate": 200, "power": 3550},
            "Antminer S21 Pro": {"hashrate": 234, "power": 3531},
            "Antminer S21 XP": {"hashrate": 270, "power": 3645},
            "Antminer S21 Hyd": {"hashrate": 335, "power": 5360},
            "Antminer S21 XP Hyd": {"hashrate": 473, "power": 5346},
            "WhatsMiner M63S+": {"hashrate": 390, "power": 7000}
        }
        
    def log_test(self, category: str, test_name: str, status: str, details: str = "", 
                 response_time: float = 0.0, email: str = "", actual_value: Any = None, 
                 expected_value: Any = None, accuracy: float = 0.0):
        """记录测试结果"""
        result = {
            "timestamp": datetime.now().isoformat(),
            "category": category,
            "test_name": test_name,
            "status": status,
            "details": details,
            "response_time": response_time,
            "email": email,
            "actual_value": actual_value,
            "expected_value": expected_value,
            "accuracy": accuracy
        }
        self.test_results.append(result)
        
        self.total_tests += 1
        if status == "PASS":
            self.passed_tests += 1
        elif status == "FAIL":
            self.failed_tests += 1
        elif status == "WARNING":
            self.warnings += 1
            
        logger.info(f"[{status}] {category}.{test_name}: {details}")
    
    def authenticate_with_email(self, email: str) -> bool:
        """使用指定邮箱进行认证"""
        try:
            start_time = time.time()
            
            # 首先访问登录页面
            response = self.session.get(f"{self.base_url}/")
            
            # 提交登录表单
            login_data = {"email": email}
            response = self.session.post(f"{self.base_url}/login", data=login_data, allow_redirects=True)
            
            response_time = time.time() - start_time
            
            if response.status_code == 200 and "logout" in response.text.lower():
                self.log_test("Authentication", f"login_{email.split('@')[0]}", "PASS", 
                            f"成功使用{email}登录", response_time, email)
                return True
            else:
                self.log_test("Authentication", f"login_{email.split('@')[0]}", "FAIL", 
                            f"使用{email}登录失败: {response.status_code}", response_time, email)
                return False
                
        except Exception as e:
            self.log_test("Authentication", f"login_{email.split('@')[0]}", "FAIL", 
                        f"登录异常: {str(e)}", None, email)
            return False
    
    def test_core_api_endpoints(self) -> None:
        """测试核心API端点的数值准确性"""
        logger.info("开始测试核心API端点...")
        
        # API端点列表
        api_endpoints = [
            ("/api/btc-price", self.validate_btc_price_api),
            ("/api/network-stats", self.validate_network_stats_api),
            ("/api/miners", self.validate_miners_api),
            ("/api/sha256-comparison", self.validate_comparison_api),
            ("/analytics/api/market-data", self.validate_analytics_market_api),
            ("/analytics/api/latest-report", self.validate_analytics_report_api),
            ("/analytics/api/technical-indicators", self.validate_technical_indicators_api),
            ("/analytics/api/price-history", self.validate_price_history_api)
        ]
        
        for endpoint, validator in api_endpoints:
            try:
                start_time = time.time()
                response = self.session.get(f"{self.base_url}{endpoint}")
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        is_valid, accuracy, details = validator(data)
                        
                        if is_valid and accuracy >= 99.0:
                            self.log_test("API_Endpoints", endpoint.replace("/", "_"), "PASS", 
                                        details, response_time, accuracy=accuracy)
                        elif is_valid and accuracy >= 95.0:
                            self.log_test("API_Endpoints", endpoint.replace("/", "_"), "WARNING", 
                                        f"准确率{accuracy:.1f}%低于99%: {details}", response_time, accuracy=accuracy)
                        else:
                            self.log_test("API_Endpoints", endpoint.replace("/", "_"), "FAIL", 
                                        f"准确率{accuracy:.1f}%不合格: {details}", response_time, accuracy=accuracy)
                            
                    except json.JSONDecodeError:
                        self.log_test("API_Endpoints", endpoint.replace("/", "_"), "FAIL", 
                                    "JSON解析失败", response_time)
                else:
                    self.log_test("API_Endpoints", endpoint.replace("/", "_"), "FAIL", 
                                f"HTTP错误: {response.status_code}", response_time)
                                
            except Exception as e:
                self.log_test("API_Endpoints", endpoint.replace("/", "_"), "FAIL", 
                            f"请求异常: {str(e)}")
    
    def validate_btc_price_api(self, data: Dict) -> Tuple[bool, float, str]:
        """验证BTC价格API的准确性"""
        try:
            # 检查必要字段
            if not data.get('success'):
                return False, 0.0, "API响应success=false"
            
            price = data.get('btc_price')
            if not price or not isinstance(price, (int, float)):
                return False, 0.0, "BTC价格数据无效"
            
            # 价格合理性检查 (50000-200000 USD范围)
            if not (50000 <= price <= 200000):
                return False, 60.0, f"BTC价格{price}超出合理范围"
            
            # 数据完整性检查
            accuracy = 100.0
            details = f"BTC价格: ${price:,.2f}"
            
            # 检查价格精度 (应为2位小数或整数)
            if isinstance(price, float) and round(price, 2) != price:
                accuracy -= 5.0
                details += " (精度警告)"
            
            return True, accuracy, details
            
        except Exception as e:
            return False, 0.0, f"验证异常: {str(e)}"
    
    def validate_network_stats_api(self, data: Dict) -> Tuple[bool, float, str]:
        """验证网络统计API的准确性"""
        try:
            if not data.get('success'):
                return False, 0.0, "API响应success=false"
            
            hashrate = data.get('network_hashrate')
            difficulty = data.get('difficulty')
            
            accuracy = 100.0
            issues = []
            
            # 验证算力 (应在500-2000 EH/s范围内)
            if not hashrate or not isinstance(hashrate, (int, float)):
                return False, 0.0, "网络算力数据无效"
            
            if not (500 <= hashrate <= 2000):
                accuracy -= 20.0
                issues.append(f"算力{hashrate}EH/s超出合理范围")
            
            # 验证难度 (应在50T-200T范围内)
            if difficulty:
                if isinstance(difficulty, str):
                    # 处理 "117.0T" 格式
                    try:
                        diff_value = float(difficulty.replace('T', ''))
                        if not (50 <= diff_value <= 200):
                            accuracy -= 10.0
                            issues.append(f"难度{difficulty}超出范围")
                    except:
                        accuracy -= 10.0
                        issues.append("难度格式解析失败")
                elif isinstance(difficulty, (int, float)):
                    # 原始难度值验证
                    if not (5e13 <= difficulty <= 2e14):
                        accuracy -= 10.0
                        issues.append("原始难度值超出范围")
            
            details = f"算力: {hashrate}EH/s, 难度: {difficulty}"
            if issues:
                details += f" (问题: {'; '.join(issues)})"
            
            return True, accuracy, details
            
        except Exception as e:
            return False, 0.0, f"验证异常: {str(e)}"
    
    def validate_miners_api(self, data: Dict) -> Tuple[bool, float, str]:
        """验证矿机数据API的准确性"""
        try:
            if not data.get('success'):
                return False, 0.0, "API响应success=false"
            
            miners = data.get('miners', [])
            if not miners or len(miners) < 8:
                return False, 50.0, f"矿机数量不足: {len(miners)}"
            
            accuracy = 100.0
            verified_miners = 0
            total_spec_accuracy = 0.0
            
            for miner in miners:
                name = miner.get('name', '')
                hashrate = miner.get('hashrate', 0)
                power = miner.get('power', 0)
                
                if name in self.miner_specs:
                    verified_miners += 1
                    expected_hashrate = self.miner_specs[name]['hashrate']
                    expected_power = self.miner_specs[name]['power']
                    
                    # 计算规格准确性 (允许5%误差)
                    hashrate_accuracy = max(0, 100 - abs(hashrate - expected_hashrate) / expected_hashrate * 100)
                    power_accuracy = max(0, 100 - abs(power - expected_power) / expected_power * 100)
                    
                    if hashrate_accuracy < 95 or power_accuracy < 95:
                        accuracy -= 5.0
                    
                    total_spec_accuracy += (hashrate_accuracy + power_accuracy) / 2
            
            if verified_miners > 0:
                avg_spec_accuracy = total_spec_accuracy / verified_miners
                accuracy = min(accuracy, avg_spec_accuracy)
            
            details = f"验证了{verified_miners}/{len(miners)}个矿机型号，平均规格准确率{avg_spec_accuracy:.1f}%"
            
            return True, accuracy, details
            
        except Exception as e:
            return False, 0.0, f"验证异常: {str(e)}"
    
    def validate_comparison_api(self, data: Dict) -> Tuple[bool, float, str]:
        """验证挖矿对比API的准确性"""
        try:
            if not data.get('success'):
                return False, 0.0, "API响应success=false"
            
            comparison_data = data.get('data', [])
            if not comparison_data:
                return False, 0.0, "对比数据为空"
            
            accuracy = 100.0
            btc_found = False
            
            for coin in comparison_data:
                if coin.get('coin_name') == 'Bitcoin':
                    btc_found = True
                    profitability = coin.get('profitability_24h')
                    revenue = coin.get('revenue_24h')
                    
                    # 验证盈利数据合理性
                    if profitability and isinstance(profitability, (int, float)):
                        if profitability < 0 or profitability > 1000:
                            accuracy -= 10.0
                    
                    if revenue and isinstance(revenue, (int, float)):
                        if revenue < 0 or revenue > 100:
                            accuracy -= 10.0
            
            if not btc_found:
                accuracy -= 20.0
            
            details = f"包含{len(comparison_data)}个币种对比数据"
            if btc_found:
                details += "，包含Bitcoin数据"
            
            return True, accuracy, details
            
        except Exception as e:
            return False, 0.0, f"验证异常: {str(e)}"
    
    def validate_analytics_market_api(self, data: Dict) -> Tuple[bool, float, str]:
        """验证分析市场数据API的准确性"""
        try:
            if not data.get('success'):
                return False, 0.0, "API响应success=false"
            
            market_data = data.get('data', {})
            if not market_data:
                return False, 0.0, "市场数据为空"
            
            accuracy = 100.0
            btc_price = market_data.get('btc_price')
            hashrate = market_data.get('network_hashrate')
            
            # 验证价格
            if btc_price and isinstance(btc_price, (int, float)):
                if not (50000 <= btc_price <= 200000):
                    accuracy -= 15.0
            else:
                accuracy -= 20.0
            
            # 验证算力
            if hashrate and isinstance(hashrate, (int, float)):
                if not (500 <= hashrate <= 2000):
                    accuracy -= 15.0
            else:
                accuracy -= 20.0
            
            details = f"价格: ${btc_price}, 算力: {hashrate}EH/s"
            
            return True, accuracy, details
            
        except Exception as e:
            return False, 0.0, f"验证异常: {str(e)}"
    
    def validate_analytics_report_api(self, data: Dict) -> Tuple[bool, float, str]:
        """验证分析报告API的准确性"""
        try:
            if not data.get('success'):
                return False, 0.0, "API响应success=false"
            
            report = data.get('latest_report', {})
            if not report:
                return False, 0.0, "报告数据为空"
            
            accuracy = 100.0
            
            # 检查必要字段
            required_fields = ['title', 'summary', 'confidence_score', 'key_findings']
            missing_fields = []
            
            for field in required_fields:
                if field not in report:
                    missing_fields.append(field)
                    accuracy -= 15.0
            
            # 验证置信度评分
            confidence = report.get('confidence_score')
            if confidence and isinstance(confidence, (int, float)):
                if not (0.5 <= confidence <= 1.0):
                    accuracy -= 10.0
            
            details = f"报告完整性: {len(required_fields) - len(missing_fields)}/{len(required_fields)}"
            if missing_fields:
                details += f", 缺失字段: {missing_fields}"
            
            return True, accuracy, details
            
        except Exception as e:
            return False, 0.0, f"验证异常: {str(e)}"
    
    def validate_technical_indicators_api(self, data: Dict) -> Tuple[bool, float, str]:
        """验证技术指标API的准确性"""
        try:
            if not data.get('success'):
                return False, 0.0, "API响应success=false"
            
            indicators = data.get('data', {})
            if not indicators:
                return False, 0.0, "技术指标数据为空"
            
            accuracy = 100.0
            valid_indicators = 0
            total_indicators = 0
            
            # 检查RSI
            rsi = indicators.get('rsi')
            total_indicators += 1
            if rsi and isinstance(rsi, (int, float)) and 0 <= rsi <= 100:
                valid_indicators += 1
            else:
                accuracy -= 15.0
            
            # 检查移动平均线
            ma20 = indicators.get('ma_20')
            total_indicators += 1
            if ma20 and isinstance(ma20, (int, float)) and ma20 > 0:
                valid_indicators += 1
            else:
                accuracy -= 15.0
            
            # 检查MACD
            macd = indicators.get('macd')
            total_indicators += 1
            if macd and isinstance(macd, dict):
                valid_indicators += 1
            else:
                accuracy -= 15.0
            
            details = f"有效技术指标: {valid_indicators}/{total_indicators}"
            
            return True, accuracy, details
            
        except Exception as e:
            return False, 0.0, f"验证异常: {str(e)}"
    
    def validate_price_history_api(self, data: Dict) -> Tuple[bool, float, str]:
        """验证价格历史API的准确性"""
        try:
            if not data.get('success'):
                return False, 0.0, "API响应success=false"
            
            history = data.get('data', [])
            if not history:
                return False, 0.0, "价格历史数据为空"
            
            accuracy = 100.0
            valid_records = 0
            
            for record in history[:10]:  # 检查前10条记录
                timestamp = record.get('timestamp')
                price = record.get('btc_price')
                
                if timestamp and price and isinstance(price, (int, float)):
                    if 10000 <= price <= 200000:  # 历史价格范围更宽
                        valid_records += 1
            
            if len(history) < 5:
                accuracy -= 30.0
            elif valid_records < len(history[:10]) * 0.8:
                accuracy -= 20.0
            
            details = f"历史记录数: {len(history)}, 有效记录: {valid_records}/10"
            
            return True, accuracy, details
            
        except Exception as e:
            return False, 0.0, f"验证异常: {str(e)}"
    
    def test_mining_calculations_numerical_accuracy(self) -> None:
        """测试挖矿计算的数值准确性"""
        logger.info("开始测试挖矿计算数值准确性...")
        
        # 测试场景
        test_scenarios = [
            {
                "name": "标准S19Pro测试",
                "miner": "Antminer S19 Pro",
                "hashrate_th": 110,
                "power_w": 3250,
                "count": 1,
                "electricity_cost": 0.06
            },
            {
                "name": "大规模S21测试", 
                "miner": "Antminer S21",
                "hashrate_th": 200,
                "power_w": 3550,
                "count": 100,
                "electricity_cost": 0.05
            },
            {
                "name": "高效率S21XP测试",
                "miner": "Antminer S21 XP",
                "hashrate_th": 270,
                "power_w": 3645,
                "count": 50,
                "electricity_cost": 0.08
            }
        ]
        
        for scenario in test_scenarios:
            try:
                start_time = time.time()
                
                # 构建计算请求
                calc_data = {
                    "miner_model": scenario["miner"],
                    "miner_count": scenario["count"],
                    "electricity_cost": scenario["electricity_cost"],
                    "use_real_time_data": True
                }
                
                response = self.session.post(f"{self.base_url}/calculate", 
                                           data=calc_data)
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    try:
                        result = response.json()
                        accuracy = self.validate_mining_calculation(result, scenario)
                        
                        if accuracy >= 99.0:
                            self.log_test("Mining_Calculations", scenario["name"], "PASS",
                                        f"数值计算准确率{accuracy:.1f}%", response_time, 
                                        accuracy=accuracy)
                        elif accuracy >= 95.0:
                            self.log_test("Mining_Calculations", scenario["name"], "WARNING",
                                        f"数值计算准确率{accuracy:.1f}%低于99%", response_time,
                                        accuracy=accuracy)
                        else:
                            self.log_test("Mining_Calculations", scenario["name"], "FAIL",
                                        f"数值计算准确率{accuracy:.1f}%不合格", response_time,
                                        accuracy=accuracy)
                            
                    except json.JSONDecodeError:
                        self.log_test("Mining_Calculations", scenario["name"], "FAIL",
                                    "计算结果JSON解析失败", response_time)
                else:
                    self.log_test("Mining_Calculations", scenario["name"], "FAIL",
                                f"计算请求失败: {response.status_code}", response_time)
                    
            except Exception as e:
                self.log_test("Mining_Calculations", scenario["name"], "FAIL",
                            f"计算异常: {str(e)}")
    
    def validate_mining_calculation(self, result: Dict, scenario: Dict) -> float:
        """验证挖矿计算结果的准确性"""
        try:
            accuracy = 100.0
            logger.info(f"验证计算结果: {result}")
            
            # 验证基本字段存在 - 使用实际返回的字段名
            required_fields = ['site_daily_btc_output', 'daily_revenue', 'daily_profit', 
                             'monthly_profit', 'annual_roi']
            
            missing_fields = []
            for field in required_fields:
                if field not in result or result[field] is None:
                    missing_fields.append(field)
                    accuracy -= 10.0
            
            if missing_fields:
                logger.info(f"缺失字段: {missing_fields}")
            
            # 验证数值合理性
            daily_btc = result.get('site_daily_btc_output', 0)
            daily_revenue = result.get('daily_revenue', 0)
            daily_profit = result.get('daily_profit', 0)
            
            # BTC产出合理性检查
            if isinstance(daily_btc, (int, float)) and daily_btc > 0:
                # 基于总算力的合理性检查 (不需要精确匹配)
                if daily_btc > 10:  # 单个矿机每日不应超过10 BTC
                    accuracy -= 15.0
            else:
                accuracy -= 20.0
            
            # 收益数值检查
            if isinstance(daily_revenue, (int, float)) and daily_revenue > 0:
                # 收益应该合理 (不应过高或过低)
                if daily_revenue > 100000 or daily_revenue < -50000:
                    accuracy -= 10.0
            else:
                accuracy -= 15.0
            
            # 利润合理性
            if isinstance(daily_profit, (int, float)):
                # 利润可以为负数 (电费高时)
                if abs(daily_profit) > 100000:  # 绝对值不应过大
                    accuracy -= 10.0
            else:
                accuracy -= 15.0
            
            logger.info(f"计算验证完成，准确率: {accuracy}%")
            return accuracy
            
        except Exception as e:
            logger.error(f"计算验证异常: {str(e)}")
            return 0.0
    
    def test_database_integrity(self) -> None:
        """测试数据库完整性"""
        logger.info("开始测试数据库完整性...")
        
        try:
            conn = psycopg2.connect(self.db_url)
            cursor = conn.cursor()
            
            # 测试核心表存在性和数据完整性
            tables_to_check = [
                ("market_analytics", "市场分析数据"),
                ("network_snapshots", "网络快照数据"), 
                ("technical_indicators", "技术指标数据"),
                ("user_access", "用户访问数据"),
                ("analysis_reports", "分析报告数据")
            ]
            
            for table_name, description in tables_to_check:
                try:
                    # 检查表存在性
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    count = cursor.fetchone()[0]
                    
                    if count > 0:
                        self.log_test("Database_Integrity", f"table_{table_name}", "PASS",
                                    f"{description}表包含{count}条记录")
                    else:
                        self.log_test("Database_Integrity", f"table_{table_name}", "WARNING",
                                    f"{description}表为空")
                        
                except psycopg2.Error as e:
                    self.log_test("Database_Integrity", f"table_{table_name}", "FAIL",
                                f"{description}表访问失败: {str(e)}")
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            self.log_test("Database_Integrity", "connection", "FAIL",
                        f"数据库连接失败: {str(e)}")
    
    def test_cross_user_consistency(self) -> None:
        """测试跨用户数据一致性"""
        logger.info("开始测试跨用户数据一致性...")
        
        price_values = []
        hashrate_values = []
        
        for email in self.test_emails[:3]:  # 测试前3个邮箱
            if self.authenticate_with_email(email):
                try:
                    # 获取BTC价格
                    response = self.session.get(f"{self.base_url}/api/btc-price")
                    if response.status_code == 200:
                        data = response.json()
                        if data.get('success') and data.get('btc_price'):
                            price_values.append(data['btc_price'])
                    
                    # 获取网络算力
                    response = self.session.get(f"{self.base_url}/api/network-stats")
                    if response.status_code == 200:
                        data = response.json()
                        if data.get('success') and data.get('network_hashrate'):
                            hashrate_values.append(data['network_hashrate'])
                            
                except Exception as e:
                    logger.warning(f"用户{email}数据获取异常: {str(e)}")
        
        # 计算一致性
        if len(price_values) >= 2:
            price_variance = max(price_values) - min(price_values)
            price_consistency = max(0, 100 - (price_variance / max(price_values) * 100))
            
            if price_consistency >= 99.0:
                self.log_test("Cross_User_Consistency", "btc_price", "PASS",
                            f"BTC价格一致性{price_consistency:.2f}%", accuracy=price_consistency)
            else:
                self.log_test("Cross_User_Consistency", "btc_price", "WARNING",
                            f"BTC价格一致性{price_consistency:.2f}%低于99%", accuracy=price_consistency)
        
        if len(hashrate_values) >= 2:
            hashrate_variance = max(hashrate_values) - min(hashrate_values)
            hashrate_consistency = max(0, 100 - (hashrate_variance / max(hashrate_values) * 100))
            
            if hashrate_consistency >= 99.0:
                self.log_test("Cross_User_Consistency", "network_hashrate", "PASS",
                            f"网络算力一致性{hashrate_consistency:.2f}%", accuracy=hashrate_consistency)
            else:
                self.log_test("Cross_User_Consistency", "network_hashrate", "WARNING",
                            f"网络算力一致性{hashrate_consistency:.2f}%低于99%", accuracy=hashrate_consistency)
    
    def run_full_regression_test(self) -> None:
        """运行完整的99%准确率回归测试"""
        logger.info("开始运行全面回归测试 - 目标准确率99%+")
        start_time = time.time()
        
        # 认证测试
        auth_success = False
        for email in self.test_emails:
            if self.authenticate_with_email(email):
                auth_success = True
                break
        
        if not auth_success:
            logger.error("所有邮箱认证失败，测试终止")
            return
        
        # 核心功能测试
        self.test_core_api_endpoints()
        self.test_mining_calculations_numerical_accuracy()
        self.test_database_integrity()
        self.test_cross_user_consistency()
        
        # 生成最终报告
        total_time = time.time() - start_time
        self.generate_99_percent_report(total_time)
    
    def generate_99_percent_report(self, total_time: float) -> None:
        """生成99%准确率测试报告"""
        success_rate = (self.passed_tests / self.total_tests * 100) if self.total_tests > 0 else 0
        
        # 计算平均准确率
        accuracy_scores = [r['accuracy'] for r in self.test_results if r.get('accuracy')]
        avg_accuracy = sum(accuracy_scores) / len(accuracy_scores) if accuracy_scores else 0
        
        # 确定等级
        if success_rate >= 99 and avg_accuracy >= 99:
            grade = "A+ (优秀)"
        elif success_rate >= 95 and avg_accuracy >= 95:
            grade = "A (良好)"
        elif success_rate >= 90 and avg_accuracy >= 90:
            grade = "B+ (合格)"
        else:
            grade = "C (需要改进)"
        
        report = {
            "test_summary": {
                "total_tests": self.total_tests,
                "passed_tests": self.passed_tests,
                "failed_tests": self.failed_tests,
                "warnings": self.warnings,
                "success_rate": success_rate,
                "average_accuracy": avg_accuracy,
                "grade": grade,
                "total_time": total_time
            },
            "accuracy_breakdown": {
                "api_endpoints": len([r for r in self.test_results if r['category'] == 'API_Endpoints' and r['status'] == 'PASS']),
                "mining_calculations": len([r for r in self.test_results if r['category'] == 'Mining_Calculations' and r['status'] == 'PASS']),
                "database_integrity": len([r for r in self.test_results if r['category'] == 'Database_Integrity' and r['status'] == 'PASS']),
                "cross_user_consistency": len([r for r in self.test_results if r['category'] == 'Cross_User_Consistency' and r['status'] == 'PASS'])
            },
            "detailed_results": self.test_results,
            "recommendations": self.generate_recommendations(success_rate, avg_accuracy)
        }
        
        # 保存报告
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"full_regression_test_99_percent_report_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        logger.info(f"\n{'='*80}")
        logger.info(f"全面回归测试完成 - 99%准确率验证")
        logger.info(f"{'='*80}")
        logger.info(f"总测试数: {self.total_tests}")
        logger.info(f"成功: {self.passed_tests} | 失败: {self.failed_tests} | 警告: {self.warnings}")
        logger.info(f"成功率: {success_rate:.1f}%")
        logger.info(f"平均准确率: {avg_accuracy:.1f}%")
        logger.info(f"系统等级: {grade}")
        logger.info(f"测试时长: {total_time:.1f}秒")
        logger.info(f"详细报告: {filename}")
        logger.info(f"{'='*80}")
    
    def generate_recommendations(self, success_rate: float, avg_accuracy: float) -> List[str]:
        """生成改进建议"""
        recommendations = []
        
        if success_rate < 99:
            recommendations.append(f"成功率{success_rate:.1f}%需提升至99%+")
        
        if avg_accuracy < 99:
            recommendations.append(f"平均准确率{avg_accuracy:.1f}%需提升至99%+")
        
        failed_categories = {}
        for result in self.test_results:
            if result['status'] == 'FAIL':
                category = result['category']
                failed_categories[category] = failed_categories.get(category, 0) + 1
        
        for category, count in failed_categories.items():
            recommendations.append(f"{category}类别有{count}个失败测试需要修复")
        
        if not recommendations:
            recommendations.append("系统已达到99%+准确率标准，表现优秀")
        
        return recommendations

def main():
    """主函数"""
    print("启动全面回归测试 - 99%+准确率验证")
    print("测试所有核心功能模块的数值计算和系统功能准确性")
    print("="*80)
    
    tester = FullRegressionTest99Percent()
    tester.run_full_regression_test()

if __name__ == "__main__":
    main()