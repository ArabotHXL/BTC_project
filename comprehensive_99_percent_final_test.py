#!/usr/bin/env python3
"""
全面99%准确率最终回归测试
Comprehensive 99% Accuracy Final Regression Test

使用多个测试邮箱验证所有功能和数值计算的准确性
Tests all functions and numerical calculations with multiple test emails
"""

import json
import time
import requests
import psycopg2
from datetime import datetime
from typing import Dict, List, Any, Tuple, Optional
import os
import logging
import statistics

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Comprehensive99PercentFinalTest:
    """全面99%准确率最终回归测试器"""
    
    def __init__(self):
        self.base_url = "http://0.0.0.0:5000"
        self.session = requests.Session()
        self.test_results = []
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        self.warnings = 0
        
        # 测试邮箱列表
        self.test_emails = [
            "testing123@example.com",
            "site@example.com", 
            "user@example.com",
            "hxl2022hao@gmail.com",
            "admin@example.com"
        ]
        
        # 数据库连接
        self.db_url = os.environ.get('DATABASE_URL')
        
        # 用于收集数值数据进行准确性验证
        self.price_data = []
        self.hashrate_data = []
        self.calculation_results = []
        
    def log_test(self, category: str, test_name: str, status: str, details: str = "", 
                 response_time: Optional[float] = None, accuracy: Optional[float] = None,
                 email: Optional[str] = None):
        """记录测试结果"""
        result = {
            "timestamp": datetime.now().isoformat(),
            "category": category,
            "test_name": test_name,
            "status": status,
            "details": details,
            "response_time": response_time or 0.0,
            "accuracy": accuracy or 0.0,
            "email": email or "system"
        }
        self.test_results.append(result)
        
        self.total_tests += 1
        if status == "PASS":
            self.passed_tests += 1
        elif status == "FAIL":
            self.failed_tests += 1
        elif status == "WARNING":
            self.warnings += 1
            
        status_icon = "✅" if status == "PASS" else ("⚠️" if status == "WARNING" else "❌")
        logger.info(f"{status_icon} [{category}] {test_name}: {details}")
    
    def authenticate_with_email(self, email: str) -> bool:
        """使用指定邮箱进行认证"""
        try:
            start_time = time.time()
            
            # 首先访问主页
            response = self.session.get(f"{self.base_url}/")
            
            # 执行登录
            login_data = {"email": email}
            response = self.session.post(f"{self.base_url}/login", data=login_data, allow_redirects=True)
            
            response_time = time.time() - start_time
            
            if response.status_code == 200 and "logout" in response.text.lower():
                self.log_test("Authentication", "login", "PASS", 
                            f"邮箱{email}认证成功", response_time, 100.0, email)
                return True
            else:
                self.log_test("Authentication", "login", "FAIL", 
                            f"邮箱{email}认证失败: {response.status_code}", response_time, 0.0, email)
                return False
                
        except Exception as e:
            self.log_test("Authentication", "login", "FAIL", 
                        f"邮箱{email}认证异常: {str(e)}", 0.0, 0.0, email)
            return False
    
    def test_core_api_functions(self, email: str) -> None:
        """测试核心API功能"""
        logger.info(f"使用邮箱{email}测试核心API功能...")
        
        # 1. BTC价格API测试
        try:
            start_time = time.time()
            response = self.session.get(f"{self.base_url}/api/btc-price")
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success') and isinstance(data.get('btc_price'), (int, float)):
                    price = data['btc_price']
                    self.price_data.append(price)
                    
                    # 严格价格验证
                    accuracy = 100.0
                    issues = []
                    
                    if not (80000 <= price <= 150000):
                        accuracy = 70.0
                        issues.append(f"价格${price}超出预期范围")
                    
                    if not isinstance(price, (int, float)):
                        accuracy = 50.0
                        issues.append("价格数据类型错误")
                    
                    # 检查价格精度
                    if abs(price - round(price, 2)) > 0.001:
                        accuracy -= 10.0
                        issues.append("价格精度问题")
                    
                    status = "PASS" if accuracy >= 99 else ("WARNING" if accuracy >= 90 else "FAIL")
                    details = f"BTC价格${price:,.2f}"
                    if issues:
                        details += f" (问题: {'; '.join(issues)})"
                        
                    self.log_test("Core_API", "btc_price", status, details, response_time, accuracy, email)
                else:
                    self.log_test("Core_API", "btc_price", "FAIL",
                                "价格API响应数据无效", response_time, 0.0, email)
            else:
                self.log_test("Core_API", "btc_price", "FAIL",
                            f"价格API响应错误: {response.status_code}", response_time, 0.0, email)
        except Exception as e:
            self.log_test("Core_API", "btc_price", "FAIL", f"价格API异常: {str(e)}", 0.0, 0.0, email)
        
        # 2. 网络统计API测试
        try:
            start_time = time.time()
            response = self.session.get(f"{self.base_url}/api/network-stats")
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    hashrate = data.get('network_hashrate')
                    difficulty = data.get('difficulty')
                    
                    accuracy = 100.0
                    issues = []
                    
                    # 算力验证
                    if isinstance(hashrate, (int, float)) and 600 <= hashrate <= 1200:
                        self.hashrate_data.append(hashrate)
                    else:
                        accuracy -= 40.0
                        issues.append(f"算力{hashrate}EH/s异常")
                    
                    # 难度验证
                    if difficulty and isinstance(difficulty, (int, float)):
                        if 8e13 <= difficulty <= 2e14:
                            pass  # 合理范围
                        else:
                            accuracy -= 30.0
                            issues.append("难度值超出预期范围")
                    else:
                        accuracy -= 30.0
                        issues.append("难度数据无效")
                    
                    status = "PASS" if accuracy >= 99 else ("WARNING" if accuracy >= 85 else "FAIL")
                    details = f"算力{hashrate}EH/s, 难度{difficulty}"
                    if issues:
                        details += f" (问题: {'; '.join(issues)})"
                        
                    self.log_test("Core_API", "network_stats", status, details, response_time, accuracy, email)
                else:
                    self.log_test("Core_API", "network_stats", "FAIL",
                                "网络统计API响应数据无效", response_time, 0.0, email)
            else:
                self.log_test("Core_API", "network_stats", "FAIL",
                            f"网络统计API响应错误: {response.status_code}", response_time, 0.0, email)
        except Exception as e:
            self.log_test("Core_API", "network_stats", "FAIL", f"网络统计API异常: {str(e)}", 0.0, 0.0, email)
        
        # 3. 矿机数据API测试
        try:
            start_time = time.time()
            response = self.session.get(f"{self.base_url}/api/miners")
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    miners = data.get('miners', [])
                    accuracy = 100.0
                    issues = []
                    
                    # 矿机数量验证
                    if len(miners) >= 10:
                        pass  # 优秀
                    elif len(miners) >= 8:
                        accuracy = 95.0
                        issues.append("矿机型号数量略少")
                    else:
                        accuracy = 70.0
                        issues.append("矿机型号严重不足")
                    
                    # 检查关键矿机型号
                    key_miners = ['Antminer S19 Pro', 'Antminer S21', 'Antminer S19']
                    found_key_miners = sum(1 for miner in miners if miner.get('name') in key_miners)
                    
                    if found_key_miners >= 3:
                        pass  # 关键型号齐全
                    else:
                        accuracy -= 15.0
                        issues.append(f"关键矿机型号不足({found_key_miners}/3)")
                    
                    # 检查矿机数据完整性
                    complete_miners = 0
                    for miner in miners:
                        if all(key in miner for key in ['name', 'hashrate', 'power']):
                            complete_miners += 1
                    
                    completeness_rate = (complete_miners / len(miners)) * 100 if miners else 0
                    if completeness_rate < 90:
                        accuracy -= 20.0
                        issues.append(f"矿机数据完整性{completeness_rate:.1f}%偏低")
                    
                    status = "PASS" if accuracy >= 99 else ("WARNING" if accuracy >= 90 else "FAIL")
                    details = f"矿机数据{len(miners)}个型号，{found_key_miners}个关键型号，{completeness_rate:.1f}%完整"
                    if issues:
                        details += f" (问题: {'; '.join(issues)})"
                    
                    self.log_test("Core_API", "miners", status, details, response_time, accuracy, email)
                else:
                    self.log_test("Core_API", "miners", "FAIL",
                                "矿机API响应数据无效", response_time, 0.0, email)
            else:
                self.log_test("Core_API", "miners", "FAIL",
                            f"矿机API响应错误: {response.status_code}", response_time, 0.0, email)
        except Exception as e:
            self.log_test("Core_API", "miners", "FAIL", f"矿机API异常: {str(e)}", 0.0, 0.0, email)
    
    def test_numerical_calculations(self, email: str) -> None:
        """测试数值计算精确性"""
        logger.info(f"使用邮箱{email}测试数值计算精确性...")
        
        # 定义多种测试场景
        test_scenarios = [
            {
                "name": "standard_s19_pro",
                "params": {
                    "miner_model": "Antminer S19 Pro",
                    "miner_count": "1",
                    "electricity_cost": "0.06",
                    "use_real_time_data": "true"
                }
            },
            {
                "name": "bulk_s21_operation", 
                "params": {
                    "miner_model": "Antminer S21",
                    "miner_count": "10",
                    "electricity_cost": "0.05",
                    "use_real_time_data": "true"
                }
            },
            {
                "name": "high_cost_scenario",
                "params": {
                    "miner_model": "Antminer S19",
                    "miner_count": "5",
                    "electricity_cost": "0.10",
                    "use_real_time_data": "true"
                }
            }
        ]
        
        for scenario in test_scenarios:
            try:
                start_time = time.time()
                response = self.session.post(f"{self.base_url}/calculate", data=scenario["params"])
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    try:
                        result = response.json()
                        
                        if result.get('success'):
                            accuracy = 100.0
                            issues = []
                            
                            # 收集计算结果用于一致性检查
                            calc_data = {
                                "scenario": scenario["name"],
                                "btc_output": result.get('site_daily_btc_output', 0),
                                "revenue": result.get('revenue', {}),
                                "profit": result.get('profit', {}),
                                "electricity_cost": result.get('electricity_cost', {}),
                                "email": email
                            }
                            self.calculation_results.append(calc_data)
                            
                            # 获取关键数值
                            btc_output = result.get('site_daily_btc_output', 0)
                            revenue_data = result.get('revenue', {})
                            profit_data = result.get('profit', {})
                            
                            daily_revenue = revenue_data.get('daily', 0) if isinstance(revenue_data, dict) else 0
                            daily_profit = profit_data.get('daily', 0) if isinstance(profit_data, dict) else 0
                            
                            # BTC产出精确性验证
                            if isinstance(btc_output, (int, float)) and btc_output > 0:
                                # 根据矿机数量调整合理范围
                                miner_count = int(scenario["params"]["miner_count"])
                                expected_min = 0.001 * miner_count
                                expected_max = 0.02 * miner_count
                                
                                if expected_min <= btc_output <= expected_max:
                                    pass  # 合理范围
                                else:
                                    accuracy -= 25.0
                                    issues.append(f"BTC产出{btc_output:.6f}超出预期范围({expected_min:.6f}-{expected_max:.6f})")
                            else:
                                accuracy -= 30.0
                                issues.append("BTC产出数据无效")
                            
                            # 收益合理性验证
                            if isinstance(daily_revenue, (int, float)) and daily_revenue > 0:
                                # 收益应该基于BTC产出和当前价格
                                if self.price_data:
                                    avg_price = statistics.mean(self.price_data)
                                    expected_revenue = btc_output * avg_price
                                    revenue_diff = abs(daily_revenue - expected_revenue) / expected_revenue * 100
                                    
                                    if revenue_diff <= 5.0:  # 5%以内误差可接受
                                        pass
                                    else:
                                        accuracy -= 20.0
                                        issues.append(f"收益计算偏差{revenue_diff:.2f}%")
                            else:
                                accuracy -= 25.0
                                issues.append("收益数据无效")
                            
                            # 利润逻辑验证
                            if isinstance(daily_profit, (int, float)):
                                if daily_profit <= daily_revenue:  # 利润不应超过收益
                                    pass
                                else:
                                    accuracy -= 30.0  # 严重逻辑错误
                                    issues.append("利润超过收入")
                            else:
                                accuracy -= 20.0
                                issues.append("利润数据类型错误")
                            
                            # 数值精度验证
                            precision_score = 100.0
                            for key, value in [("BTC产出", btc_output), ("日收益", daily_revenue), ("日利润", daily_profit)]:
                                if isinstance(value, float):
                                    # 检查是否有合理的精度（不要过多或过少小数位）
                                    decimal_places = len(str(value).split('.')[-1]) if '.' in str(value) else 0
                                    if decimal_places > 10:  # 过高精度可能表示计算问题
                                        precision_score -= 10.0
                                        issues.append(f"{key}精度过高")
                            
                            accuracy = min(accuracy, precision_score)
                            
                            status = "PASS" if accuracy >= 99 else ("WARNING" if accuracy >= 85 else "FAIL")
                            details = f"{scenario['name']}: BTC产出{btc_output:.6f}, 收益${daily_revenue:.2f}, 利润${daily_profit:.2f}"
                            if issues:
                                details += f" (问题: {'; '.join(issues)})"
                            
                            self.log_test("Numerical_Calc", scenario["name"], status,
                                        details, response_time, accuracy, email)
                        else:
                            self.log_test("Numerical_Calc", scenario["name"], "FAIL",
                                        "计算返回success=false", response_time, 0.0, email)
                            
                    except json.JSONDecodeError as e:
                        self.log_test("Numerical_Calc", scenario["name"], "FAIL",
                                    f"JSON解析失败: {str(e)}", response_time, 0.0, email)
                else:
                    self.log_test("Numerical_Calc", scenario["name"], "FAIL",
                                f"计算请求失败: {response.status_code}", response_time, 0.0, email)
                    
            except Exception as e:
                self.log_test("Numerical_Calc", scenario["name"], "FAIL",
                            f"计算异常: {str(e)}", 0.0, 0.0, email)
    
    def test_data_consistency(self) -> None:
        """测试数据一致性"""
        logger.info("测试跨用户数据一致性...")
        
        # 价格数据一致性
        if len(self.price_data) >= 2:
            price_variance = (max(self.price_data) - min(self.price_data)) / max(self.price_data) * 100
            avg_price = statistics.mean(self.price_data)
            
            if price_variance <= 1.0:
                accuracy = 100.0
                status = "PASS"
            elif price_variance <= 3.0:
                accuracy = 95.0
                status = "WARNING"
            else:
                accuracy = 70.0
                status = "FAIL"
            
            self.log_test("Data_Consistency", "price_variance", status,
                        f"价格差异{price_variance:.2f}% (平均${avg_price:.2f}, 范围${min(self.price_data):.0f}-${max(self.price_data):.0f})",
                        0.0, accuracy)
        
        # 算力数据一致性
        if len(self.hashrate_data) >= 2:
            hashrate_variance = (max(self.hashrate_data) - min(self.hashrate_data)) / max(self.hashrate_data) * 100
            avg_hashrate = statistics.mean(self.hashrate_data)
            
            if hashrate_variance <= 2.0:
                accuracy = 100.0
                status = "PASS"
            elif hashrate_variance <= 5.0:
                accuracy = 90.0
                status = "WARNING"
            else:
                accuracy = 75.0
                status = "FAIL"
            
            self.log_test("Data_Consistency", "hashrate_variance", status,
                        f"算力差异{hashrate_variance:.2f}% (平均{avg_hashrate:.2f}EH/s, 范围{min(self.hashrate_data):.2f}-{max(self.hashrate_data):.2f})",
                        0.0, accuracy)
        
        # 计算结果一致性 (相同场景下不同用户的结果应该一致)
        scenario_results = {}
        for calc in self.calculation_results:
            scenario = calc["scenario"]
            if scenario not in scenario_results:
                scenario_results[scenario] = []
            scenario_results[scenario].append(calc)
        
        for scenario, results in scenario_results.items():
            if len(results) >= 2:
                btc_outputs = [r["btc_output"] for r in results if r["btc_output"]]
                if btc_outputs:
                    output_variance = (max(btc_outputs) - min(btc_outputs)) / max(btc_outputs) * 100 if max(btc_outputs) > 0 else 0
                    
                    if output_variance <= 0.1:  # 极小差异
                        accuracy = 100.0
                        status = "PASS"
                    elif output_variance <= 1.0:
                        accuracy = 95.0
                        status = "WARNING"
                    else:
                        accuracy = 80.0
                        status = "FAIL"
                    
                    self.log_test("Data_Consistency", f"calc_{scenario}", status,
                                f"场景{scenario}计算差异{output_variance:.3f}% (样本{len(btc_outputs)}个)",
                                0.0, accuracy)
    
    def test_system_reliability(self) -> None:
        """测试系统可靠性"""
        logger.info("测试系统可靠性...")
        
        # 数据库健康检查
        try:
            conn = psycopg2.connect(self.db_url)
            cursor = conn.cursor()
            
            # 检查关键表
            tables_status = []
            
            # 市场分析数据表
            cursor.execute("SELECT COUNT(*) FROM market_analytics")
            market_count = cursor.fetchone()[0]
            market_health = 100.0 if market_count > 700 else (90.0 if market_count > 500 else 70.0)
            tables_status.append(market_health)
            
            # 网络快照表
            cursor.execute("SELECT COUNT(*) FROM network_snapshots")
            snapshot_count = cursor.fetchone()[0]
            snapshot_health = 100.0 if snapshot_count > 1000 else (90.0 if snapshot_count > 700 else 70.0)
            tables_status.append(snapshot_health)
            
            cursor.close()
            conn.close()
            
            overall_db_health = statistics.mean(tables_status)
            
            status = "PASS" if overall_db_health >= 95 else ("WARNING" if overall_db_health >= 85 else "FAIL")
            self.log_test("System_Reliability", "database_health", status,
                        f"数据库健康度{overall_db_health:.1f}% (市场数据{market_count}条, 快照{snapshot_count}条)",
                        0.0, overall_db_health)
            
        except Exception as e:
            self.log_test("System_Reliability", "database_health", "FAIL",
                        f"数据库检查失败: {str(e)}", 0.0, 0.0)
        
        # 页面加载可靠性
        critical_pages = [
            ("/", "主页"),
            ("/legal", "法律页面")
        ]
        
        page_scores = []
        for path, name in critical_pages:
            try:
                start_time = time.time()
                # 使用新session避免认证影响
                temp_session = requests.Session()
                response = temp_session.get(f"{self.base_url}{path}")
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    content_length = len(response.text)
                    if content_length > 30000:  # 丰富内容
                        page_scores.append(100.0)
                    elif content_length > 10000:
                        page_scores.append(90.0)
                    else:
                        page_scores.append(70.0)
                    
                    self.log_test("System_Reliability", f"page_{path.replace('/', 'root')}", "PASS",
                                f"{name}加载成功({content_length}字符)", response_time, 100.0)
                else:
                    page_scores.append(0.0)
                    self.log_test("System_Reliability", f"page_{path.replace('/', 'root')}", "FAIL",
                                f"{name}加载失败: {response.status_code}", response_time, 0.0)
                    
            except Exception as e:
                page_scores.append(0.0)
                self.log_test("System_Reliability", f"page_{path.replace('/', 'root')}", "FAIL",
                            f"{name}加载异常: {str(e)}", 0.0, 0.0)
        
        if page_scores:
            page_reliability = statistics.mean(page_scores)
            status = "PASS" if page_reliability >= 95 else ("WARNING" if page_reliability >= 85 else "FAIL")
            self.log_test("System_Reliability", "page_loading", status,
                        f"页面加载可靠性{page_reliability:.1f}%", 0.0, page_reliability)
    
    def run_comprehensive_99_percent_test(self) -> None:
        """运行全面99%准确率测试"""
        logger.info("="*80)
        logger.info("开始运行全面99%准确率最终回归测试")
        logger.info(f"使用{len(self.test_emails)}个测试邮箱进行全面验证")
        logger.info("="*80)
        
        start_time = time.time()
        
        # 对每个邮箱执行完整测试
        for email in self.test_emails:
            logger.info(f"\n🔍 使用邮箱 {email} 进行测试...")
            
            # 认证
            if not self.authenticate_with_email(email):
                logger.warning(f"邮箱 {email} 认证失败，跳过后续测试")
                continue
            
            # 核心API功能测试
            self.test_core_api_functions(email)
            
            # 数值计算测试
            self.test_numerical_calculations(email)
            
            # 短暂延迟避免过快请求
            time.sleep(0.5)
        
        # 跨用户数据一致性测试
        self.test_data_consistency()
        
        # 系统可靠性测试
        self.test_system_reliability()
        
        # 生成最终报告
        total_time = time.time() - start_time
        self.generate_comprehensive_report(total_time)
    
    def generate_comprehensive_report(self, total_time: float) -> None:
        """生成全面测试报告"""
        success_rate = (self.passed_tests / self.total_tests * 100) if self.total_tests > 0 else 0
        
        # 计算加权准确率
        accuracy_scores = [r['accuracy'] for r in self.test_results if r.get('accuracy', 0) > 0]
        avg_accuracy = statistics.mean(accuracy_scores) if accuracy_scores else 0
        
        # 按类别统计
        categories = {}
        for result in self.test_results:
            cat = result['category']
            if cat not in categories:
                categories[cat] = {'total': 0, 'passed': 0, 'accuracy_sum': 0, 'accuracy_count': 0}
            categories[cat]['total'] += 1
            if result['status'] == 'PASS':
                categories[cat]['passed'] += 1
            if result.get('accuracy', 0) > 0:
                categories[cat]['accuracy_sum'] += result['accuracy']
                categories[cat]['accuracy_count'] += 1
        
        # 计算各类别平均准确率
        for cat in categories:
            if categories[cat]['accuracy_count'] > 0:
                categories[cat]['avg_accuracy'] = categories[cat]['accuracy_sum'] / categories[cat]['accuracy_count']
            else:
                categories[cat]['avg_accuracy'] = 0
        
        # 确定最终等级
        if success_rate >= 99 and avg_accuracy >= 99:
            grade = "A+ (完美级别)"
            level = "PERFECT"
        elif success_rate >= 95 and avg_accuracy >= 95:
            grade = "A (优秀级别)"
            level = "EXCELLENT"
        elif success_rate >= 90 and avg_accuracy >= 90:
            grade = "B+ (良好级别)"
            level = "GOOD"
        elif success_rate >= 80 and avg_accuracy >= 80:
            grade = "B (合格级别)"
            level = "ACCEPTABLE"
        else:
            grade = "C (需要改进)"
            level = "NEEDS_IMPROVEMENT"
        
        # 生成详细报告
        report = {
            "test_metadata": {
                "test_name": "Comprehensive 99% Accuracy Final Regression Test",
                "timestamp": datetime.now().isoformat(),
                "test_duration_seconds": round(total_time, 2),
                "test_emails": self.test_emails,
                "tester_version": "2.0.0"
            },
            "summary_results": {
                "total_tests": self.total_tests,
                "passed_tests": self.passed_tests,
                "failed_tests": self.failed_tests,
                "warnings": self.warnings,
                "success_rate_percent": round(success_rate, 1),
                "average_accuracy_percent": round(avg_accuracy, 1),
                "system_grade": grade,
                "performance_level": level,
                "meets_99_percent_target": success_rate >= 99 and avg_accuracy >= 99
            },
            "category_breakdown": {
                cat: {
                    "tests_passed": data['passed'],
                    "tests_total": data['total'],
                    "pass_rate_percent": round(data['passed'] / data['total'] * 100, 1),
                    "average_accuracy_percent": round(data['avg_accuracy'], 1)
                }
                for cat, data in categories.items()
            },
            "data_analysis": {
                "price_data_points": len(self.price_data),
                "price_range": f"${min(self.price_data):.0f} - ${max(self.price_data):.0f}" if self.price_data else "N/A",
                "hashrate_data_points": len(self.hashrate_data),
                "hashrate_range": f"{min(self.hashrate_data):.2f} - {max(self.hashrate_data):.2f} EH/s" if self.hashrate_data else "N/A",
                "calculation_scenarios_tested": len(self.calculation_results)
            },
            "detailed_test_results": self.test_results,
            "recommendations": self.generate_final_recommendations(success_rate, avg_accuracy, categories)
        }
        
        # 保存报告
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"comprehensive_99_percent_final_test_report_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        # 输出详细摘要
        logger.info(f"\n{'='*100}")
        logger.info(f"全面99%准确率最终回归测试完成")
        logger.info(f"{'='*100}")
        logger.info(f"📊 测试概况:")
        logger.info(f"   总测试数: {self.total_tests}")
        logger.info(f"   通过: {self.passed_tests} | 失败: {self.failed_tests} | 警告: {self.warnings}")
        logger.info(f"   成功率: {success_rate:.1f}%")
        logger.info(f"   平均准确率: {avg_accuracy:.1f}%")
        logger.info(f"   系统等级: {grade}")
        logger.info(f"   测试耗时: {total_time:.1f}秒")
        logger.info(f"")
        logger.info(f"📧 邮箱测试:")
        logger.info(f"   测试邮箱: {len(self.test_emails)}个")
        for email in self.test_emails:
            email_tests = [r for r in self.test_results if r.get('email') == email]
            email_passed = sum(1 for r in email_tests if r['status'] == 'PASS')
            if email_tests:
                logger.info(f"   {email}: {email_passed}/{len(email_tests)} 通过")
        logger.info(f"")
        logger.info(f"📈 数据分析:")
        logger.info(f"   价格数据点: {len(self.price_data)}个")
        if self.price_data:
            logger.info(f"   价格范围: ${min(self.price_data):.0f} - ${max(self.price_data):.0f}")
        logger.info(f"   算力数据点: {len(self.hashrate_data)}个")
        if self.hashrate_data:
            logger.info(f"   算力范围: {min(self.hashrate_data):.2f} - {max(self.hashrate_data):.2f} EH/s")
        logger.info(f"   计算场景: {len(self.calculation_results)}个")
        logger.info(f"")
        logger.info(f"🎯 分类表现:")
        for cat, data in categories.items():
            pass_rate = data['passed'] / data['total'] * 100
            logger.info(f"   {cat}: {data['passed']}/{data['total']} ({pass_rate:.1f}%) - 准确率{data['avg_accuracy']:.1f}%")
        logger.info(f"")
        logger.info(f"🏆 最终评估:")
        if success_rate >= 99 and avg_accuracy >= 99:
            logger.info(f"   ✅ 系统达到99%+准确率标准")
            logger.info(f"   🎉 完美级别 - 准备就绪用于生产环境")
        elif success_rate >= 95 and avg_accuracy >= 95:
            logger.info(f"   ⭐ 系统接近99%标准，表现优秀")
            logger.info(f"   ✅ 可用于生产环境")
        else:
            logger.info(f"   ⚠️  系统未达到99%标准")
            logger.info(f"   🔧 需要进一步优化")
        logger.info(f"")
        logger.info(f"📄 详细报告保存至: {filename}")
        logger.info(f"{'='*100}")
    
    def generate_final_recommendations(self, success_rate: float, avg_accuracy: float, categories: Dict) -> List[str]:
        """生成最终改进建议"""
        recommendations = []
        
        if success_rate >= 99 and avg_accuracy >= 99:
            recommendations.append("🎉 系统已达到99%+准确率标准，表现完美")
            recommendations.append("✅ 多邮箱测试验证系统稳定性和一致性")
            recommendations.append("🚀 系统准备就绪，可部署到生产环境")
            recommendations.append("📊 建议定期进行回归测试以维持高准确率")
        elif success_rate >= 95 and avg_accuracy >= 95:
            recommendations.append("⭐ 系统表现优秀，接近99%标准")
            recommendations.append("🔧 微调以下方面可达到完美水平:")
            
            # 分析具体需要改进的类别
            for cat, data in categories.items():
                pass_rate = data['passed'] / data['total'] * 100
                if pass_rate < 100 or data['avg_accuracy'] < 99:
                    recommendations.append(f"   - 优化{cat}类别 (通过率{pass_rate:.1f}%, 准确率{data['avg_accuracy']:.1f}%)")
        else:
            recommendations.append("⚠️ 系统需要重点改进以达到99%标准")
            recommendations.append("🔧 建议优先处理以下问题:")
            
            # 识别问题最严重的类别
            problem_categories = []
            for cat, data in categories.items():
                pass_rate = data['passed'] / data['total'] * 100
                if pass_rate < 90 or data['avg_accuracy'] < 90:
                    problem_categories.append((cat, pass_rate, data['avg_accuracy']))
            
            problem_categories.sort(key=lambda x: (x[1] + x[2]) / 2)  # 按平均分排序
            
            for cat, pass_rate, accuracy in problem_categories[:3]:  # 显示最需要改进的3个类别
                recommendations.append(f"   - 修复{cat}类别 (通过率{pass_rate:.1f}%, 准确率{accuracy:.1f}%)")
        
        return recommendations

def main():
    """主函数"""
    print("启动全面99%准确率最终回归测试")
    print("使用多个测试邮箱验证所有功能和数值计算")
    print("目标: 确保系统达到99%+准确率标准")
    print("="*80)
    
    tester = Comprehensive99PercentFinalTest()
    tester.run_comprehensive_99_percent_test()

if __name__ == "__main__":
    main()