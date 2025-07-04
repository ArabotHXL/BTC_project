#!/usr/bin/env python3
"""
最终99%+准确率回归测试
Final 99%+ Accuracy Regression Test

针对系统核心功能进行精确验证，确保达到99%+准确率标准
"""

import json
import time
import requests
import psycopg2
from datetime import datetime
from typing import Dict, List, Any, Tuple, Optional
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Final99PlusRegressionTest:
    """最终99%+准确率回归测试器"""
    
    def __init__(self):
        self.base_url = "http://0.0.0.0:5000"
        self.session = requests.Session()
        self.test_results = []
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        self.warnings = 0
        
        # 核心测试邮箱
        self.test_email = "hxl2022hao@gmail.com"
        
        # 数据库连接
        self.db_url = os.environ.get('DATABASE_URL')
        
    def log_test(self, category: str, test_name: str, status: str, details: str = "", 
                 response_time: Optional[float] = None, accuracy: Optional[float] = None):
        """记录测试结果"""
        result = {
            "timestamp": datetime.now().isoformat(),
            "category": category,
            "test_name": test_name,
            "status": status,
            "details": details,
            "response_time": response_time or 0.0,
            "accuracy": accuracy or 0.0
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
    
    def authenticate(self) -> bool:
        """系统认证测试"""
        try:
            start_time = time.time()
            
            # 访问主页触发认证
            response = self.session.get(f"{self.base_url}/")
            
            # 执行登录
            login_data = {"email": self.test_email}
            response = self.session.post(f"{self.base_url}/login", data=login_data, allow_redirects=True)
            
            response_time = time.time() - start_time
            
            if response.status_code == 200 and "logout" in response.text.lower():
                self.log_test("Core_System", "authentication", "PASS", 
                            f"用户认证成功", response_time, 100.0)
                return True
            else:
                self.log_test("Core_System", "authentication", "FAIL", 
                            f"认证失败: {response.status_code}", response_time, 0.0)
                return False
                
        except Exception as e:
            self.log_test("Core_System", "authentication", "FAIL", 
                        f"认证异常: {str(e)}", 0.0, 0.0)
            return False
    
    def test_critical_apis(self) -> None:
        """测试关键API端点"""
        logger.info("测试关键API端点...")
        
        # 1. BTC价格API - 最重要
        try:
            start_time = time.time()
            response = self.session.get(f"{self.base_url}/api/btc-price")
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success') and isinstance(data.get('btc_price'), (int, float)):
                    price = data['btc_price']
                    # 严格价格验证
                    if 80000 <= price <= 150000:  # 当前合理范围
                        self.log_test("Critical_APIs", "btc_price", "PASS",
                                    f"BTC价格${price:,.2f}在合理范围", response_time, 100.0)
                    else:
                        self.log_test("Critical_APIs", "btc_price", "WARNING",
                                    f"BTC价格${price:,.2f}超出预期范围", response_time, 85.0)
                else:
                    self.log_test("Critical_APIs", "btc_price", "FAIL",
                                "价格数据结构错误", response_time, 0.0)
            else:
                self.log_test("Critical_APIs", "btc_price", "FAIL",
                            f"API响应错误: {response.status_code}", response_time, 0.0)
        except Exception as e:
            self.log_test("Critical_APIs", "btc_price", "FAIL", f"价格API异常: {str(e)}", 0.0, 0.0)
        
        # 2. 网络统计API
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
                        pass  # 合理范围
                    else:
                        accuracy -= 30.0
                        issues.append(f"算力{hashrate}EH/s异常")
                    
                    # 难度验证  
                    if difficulty and isinstance(difficulty, (int, float)):
                        if 8e13 <= difficulty <= 2e14:
                            pass  # 原始难度值合理
                        else:
                            accuracy -= 20.0
                            issues.append("难度值异常")
                    
                    status = "PASS" if accuracy >= 99 else ("WARNING" if accuracy >= 80 else "FAIL")
                    details = f"算力{hashrate}EH/s, 难度{difficulty}"
                    if issues:
                        details += f" (问题: {'; '.join(issues)})"
                        
                    self.log_test("Critical_APIs", "network_stats", status, details, response_time, accuracy)
                else:
                    self.log_test("Critical_APIs", "network_stats", "FAIL",
                                "网络数据响应无效", response_time, 0.0)
            else:
                self.log_test("Critical_APIs", "network_stats", "FAIL",
                            f"网络API响应错误: {response.status_code}", response_time, 0.0)
        except Exception as e:
            self.log_test("Critical_APIs", "network_stats", "FAIL", f"网络API异常: {str(e)}", 0.0, 0.0)
        
        # 3. 矿机数据API
        try:
            start_time = time.time()
            response = self.session.get(f"{self.base_url}/api/miners")
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    miners = data.get('miners', [])
                    accuracy = 100.0
                    
                    # 矿机数量验证
                    if len(miners) >= 10:
                        pass  # 足够的矿机型号
                    elif len(miners) >= 8:
                        accuracy = 95.0  # 可接受
                    else:
                        accuracy = 70.0  # 不足
                    
                    # 检查关键矿机型号
                    key_miners = ['Antminer S19 Pro', 'Antminer S21', 'Antminer S19']
                    found_key_miners = sum(1 for miner in miners if miner.get('name') in key_miners)
                    
                    if found_key_miners >= 3:
                        pass  # 关键型号齐全
                    else:
                        accuracy -= 15.0
                    
                    status = "PASS" if accuracy >= 99 else ("WARNING" if accuracy >= 90 else "FAIL")
                    self.log_test("Critical_APIs", "miners", status,
                                f"矿机数据包含{len(miners)}个型号，{found_key_miners}个关键型号", 
                                response_time, accuracy)
                else:
                    self.log_test("Critical_APIs", "miners", "FAIL",
                                "矿机数据响应无效", response_time, 0.0)
            else:
                self.log_test("Critical_APIs", "miners", "FAIL",
                            f"矿机API响应错误: {response.status_code}", response_time, 0.0)
        except Exception as e:
            self.log_test("Critical_APIs", "miners", "FAIL", f"矿机API异常: {str(e)}", 0.0, 0.0)
    
    def test_mining_calculation_precision(self) -> None:
        """测试挖矿计算精确性"""
        logger.info("测试挖矿计算精确性...")
        
        # 测试单台S19 Pro计算
        test_params = {
            "miner_model": "Antminer S19 Pro",
            "miner_count": "1",
            "electricity_cost": "0.06",
            "use_real_time_data": "true"
        }
        
        try:
            start_time = time.time()
            response = self.session.post(f"{self.base_url}/calculate", data=test_params)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    
                    if result.get('success'):
                        # 获取关键计算结果
                        btc_output = result.get('site_daily_btc_output', 0)
                        revenue_data = result.get('revenue', {})
                        profit_data = result.get('profit', {})
                        
                        daily_revenue = revenue_data.get('daily', 0) if isinstance(revenue_data, dict) else 0
                        daily_profit = profit_data.get('daily', 0) if isinstance(profit_data, dict) else 0
                        
                        accuracy = 100.0
                        issues = []
                        
                        # BTC产出精确性验证 (单台S19 Pro约0.001-0.02 BTC/天)
                        if 0.001 <= btc_output <= 0.02:
                            pass  # 合理范围
                        else:
                            accuracy -= 25.0
                            issues.append(f"BTC产出{btc_output:.6f}超出合理范围")
                        
                        # 收益逻辑验证
                        if daily_revenue > 0 and 10 <= daily_revenue <= 5000:
                            pass  # 日收益合理
                        else:
                            accuracy -= 25.0
                            issues.append(f"日收益${daily_revenue}异常")
                        
                        # 利润合理性验证
                        if isinstance(daily_profit, (int, float)):
                            if -2000 <= daily_profit <= 3000:  # 可为负但不过极端
                                pass
                            else:
                                accuracy -= 15.0
                                issues.append(f"日利润${daily_profit}过极端")
                        else:
                            accuracy -= 20.0
                            issues.append("利润数据类型错误")
                        
                        # 逻辑一致性检查
                        if daily_profit > daily_revenue:
                            accuracy -= 30.0  # 严重逻辑错误
                            issues.append("利润超过收入")
                        
                        status = "PASS" if accuracy >= 99 else ("WARNING" if accuracy >= 85 else "FAIL")
                        details = f"BTC产出:{btc_output:.6f}, 收益:${daily_revenue:.2f}, 利润:${daily_profit:.2f}"
                        if issues:
                            details += f" (问题: {'; '.join(issues)})"
                        
                        self.log_test("Mining_Precision", "s19_pro_calculation", status,
                                    details, response_time, accuracy)
                    else:
                        self.log_test("Mining_Precision", "s19_pro_calculation", "FAIL",
                                    "计算返回success=false", response_time, 0.0)
                        
                except json.JSONDecodeError as e:
                    self.log_test("Mining_Precision", "s19_pro_calculation", "FAIL",
                                f"JSON解析失败: {str(e)}", response_time, 0.0)
            else:
                self.log_test("Mining_Precision", "s19_pro_calculation", "FAIL",
                            f"计算请求失败: {response.status_code}", response_time, 0.0)
                
        except Exception as e:
            self.log_test("Mining_Precision", "s19_pro_calculation", "FAIL",
                        f"计算异常: {str(e)}", 0.0, 0.0)
    
    def test_analytics_accuracy(self) -> None:
        """测试分析系统准确性"""
        logger.info("测试分析系统准确性...")
        
        # 分析市场数据测试
        try:
            start_time = time.time()
            response = self.session.get(f"{self.base_url}/analytics/api/market-data")
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    market_data = data.get('data', {})
                    btc_price = market_data.get('btc_price')
                    hashrate = market_data.get('network_hashrate')
                    fear_greed = market_data.get('fear_greed_index')
                    
                    accuracy = 100.0
                    issues = []
                    
                    # 价格数据验证
                    if isinstance(btc_price, (int, float)) and 80000 <= btc_price <= 150000:
                        pass
                    else:
                        accuracy -= 30.0
                        issues.append(f"分析价格{btc_price}异常")
                    
                    # 算力数据验证
                    if isinstance(hashrate, (int, float)) and 600 <= hashrate <= 1200:
                        pass
                    else:
                        accuracy -= 30.0
                        issues.append(f"分析算力{hashrate}异常")
                    
                    # 恐惧贪婪指数验证
                    if isinstance(fear_greed, (int, float)) and 0 <= fear_greed <= 100:
                        pass
                    else:
                        accuracy -= 10.0
                        issues.append("恐惧贪婪指数异常")
                    
                    status = "PASS" if accuracy >= 99 else ("WARNING" if accuracy >= 85 else "FAIL")
                    details = f"价格${btc_price}, 算力{hashrate}EH/s, FG指数{fear_greed}"
                    if issues:
                        details += f" (问题: {'; '.join(issues)})"
                    
                    self.log_test("Analytics_Accuracy", "market_data", status,
                                details, response_time, accuracy)
                else:
                    self.log_test("Analytics_Accuracy", "market_data", "FAIL",
                                "分析数据响应success=false", response_time, 0.0)
            else:
                self.log_test("Analytics_Accuracy", "market_data", "FAIL",
                            f"分析API响应错误: {response.status_code}", response_time, 0.0)
                            
        except Exception as e:
            self.log_test("Analytics_Accuracy", "market_data", "FAIL",
                        f"分析API异常: {str(e)}", 0.0, 0.0)
    
    def test_data_consistency(self) -> None:
        """测试数据一致性"""
        logger.info("测试数据一致性...")
        
        # 获取多个来源的BTC价格进行一致性检查
        prices = []
        
        # 1. 主API价格
        try:
            response = self.session.get(f"{self.base_url}/api/btc-price")
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    prices.append(('主API', data.get('btc_price')))
        except:
            pass
        
        # 2. 分析系统价格
        try:
            response = self.session.get(f"{self.base_url}/analytics/api/market-data")
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    market_data = data.get('data', {})
                    prices.append(('分析系统', market_data.get('btc_price')))
        except:
            pass
        
        # 计算价格一致性
        if len(prices) >= 2:
            price_values = [p[1] for p in prices if isinstance(p[1], (int, float))]
            
            if len(price_values) >= 2:
                max_price = max(price_values)
                min_price = min(price_values)
                price_variance = ((max_price - min_price) / max_price) * 100
                
                if price_variance <= 1.0:  # 1%以内差异
                    accuracy = 100.0
                    status = "PASS"
                elif price_variance <= 3.0:  # 3%以内差异
                    accuracy = 95.0
                    status = "WARNING"
                else:
                    accuracy = 70.0
                    status = "FAIL"
                
                self.log_test("Data_Consistency", "price_consistency", status,
                            f"价格差异{price_variance:.2f}% (范围${min_price:.0f}-${max_price:.0f})",
                            0.0, accuracy)
            else:
                self.log_test("Data_Consistency", "price_consistency", "FAIL",
                            "价格数据类型错误", 0.0, 0.0)
        else:
            self.log_test("Data_Consistency", "price_consistency", "WARNING",
                        "无法获取足够价格数据进行对比", 0.0, 80.0)
    
    def test_system_reliability(self) -> None:
        """测试系统可靠性"""
        logger.info("测试系统可靠性...")
        
        # 数据库连接测试
        try:
            conn = psycopg2.connect(self.db_url)
            cursor = conn.cursor()
            
            # 检查关键表的数据完整性
            tables_health = []
            
            # 市场分析数据表
            cursor.execute("SELECT COUNT(*) FROM market_analytics")
            market_count = cursor.fetchone()[0]
            if market_count > 600:  # 有足够历史数据
                tables_health.append(100.0)
            elif market_count > 100:
                tables_health.append(85.0)
            else:
                tables_health.append(60.0)
            
            # 网络快照表
            cursor.execute("SELECT COUNT(*) FROM network_snapshots")
            snapshot_count = cursor.fetchone()[0]
            if snapshot_count > 1000:
                tables_health.append(100.0)
            elif snapshot_count > 500:
                tables_health.append(90.0)
            else:
                tables_health.append(70.0)
            
            cursor.close()
            conn.close()
            
            # 计算总体数据库健康度
            db_health = sum(tables_health) / len(tables_health)
            
            status = "PASS" if db_health >= 95 else ("WARNING" if db_health >= 85 else "FAIL")
            self.log_test("System_Reliability", "database_health", status,
                        f"数据库健康度{db_health:.1f}% (市场数据{market_count}条, 快照{snapshot_count}条)",
                        0.0, db_health)
            
        except Exception as e:
            self.log_test("System_Reliability", "database_health", "FAIL",
                        f"数据库连接失败: {str(e)}", 0.0, 0.0)
        
        # 页面加载可靠性测试
        critical_pages = [
            ("/", "主页"),
            ("/analytics", "分析页面")
        ]
        
        page_scores = []
        for path, name in critical_pages:
            try:
                start_time = time.time()
                response = self.session.get(f"{self.base_url}{path}")
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    content_length = len(response.text)
                    if content_length > 50000:  # 足够丰富的内容
                        page_scores.append(100.0)
                    elif content_length > 10000:
                        page_scores.append(90.0)
                    else:
                        page_scores.append(70.0)
                else:
                    page_scores.append(0.0)
                    
            except Exception:
                page_scores.append(0.0)
        
        if page_scores:
            page_reliability = sum(page_scores) / len(page_scores)
            status = "PASS" if page_reliability >= 95 else ("WARNING" if page_reliability >= 85 else "FAIL")
            self.log_test("System_Reliability", "page_loading", status,
                        f"页面加载可靠性{page_reliability:.1f}%", 0.0, page_reliability)
    
    def run_final_99_plus_test(self) -> None:
        """运行最终99%+准确率测试"""
        logger.info("开始运行最终99%+准确率回归测试")
        start_time = time.time()
        
        # 执行认证
        if not self.authenticate():
            logger.error("系统认证失败，测试终止")
            return
        
        # 运行核心测试
        self.test_critical_apis()
        self.test_mining_calculation_precision()
        self.test_analytics_accuracy()
        self.test_data_consistency()
        self.test_system_reliability()
        
        # 生成最终报告
        total_time = time.time() - start_time
        self.generate_final_report(total_time)
    
    def generate_final_report(self, total_time: float) -> None:
        """生成最终测试报告"""
        success_rate = (self.passed_tests / self.total_tests * 100) if self.total_tests > 0 else 0
        
        # 计算加权准确率
        accuracy_scores = [r['accuracy'] for r in self.test_results if r.get('accuracy', 0) > 0]
        avg_accuracy = sum(accuracy_scores) / len(accuracy_scores) if accuracy_scores else 0
        
        # 确定最终等级
        if success_rate >= 99 and avg_accuracy >= 99:
            grade = "A+ (完美级别)"
            level = "EXCELLENT"
        elif success_rate >= 95 and avg_accuracy >= 95:
            grade = "A (优秀级别)"
            level = "VERY_GOOD"
        elif success_rate >= 90 and avg_accuracy >= 90:
            grade = "B+ (良好级别)"
            level = "GOOD"
        elif success_rate >= 80 and avg_accuracy >= 80:
            grade = "B (合格级别)"
            level = "ACCEPTABLE"
        else:
            grade = "C (需要改进)"
            level = "NEEDS_IMPROVEMENT"
        
        # 统计各类别表现
        categories = {}
        for result in self.test_results:
            cat = result['category']
            if cat not in categories:
                categories[cat] = {'total': 0, 'passed': 0, 'avg_accuracy': 0.0}
            categories[cat]['total'] += 1
            if result['status'] == 'PASS':
                categories[cat]['passed'] += 1
        
        # 计算各类别平均准确率
        for cat in categories:
            cat_accuracies = [r['accuracy'] for r in self.test_results 
                            if r['category'] == cat and r.get('accuracy', 0) > 0]
            categories[cat]['avg_accuracy'] = sum(cat_accuracies) / len(cat_accuracies) if cat_accuracies else 0
        
        # 生成详细报告
        report = {
            "test_metadata": {
                "test_name": "Final 99%+ Accuracy Regression Test",
                "timestamp": datetime.now().isoformat(),
                "test_duration_seconds": round(total_time, 2),
                "tester_version": "1.0.0"
            },
            "summary_results": {
                "total_tests": self.total_tests,
                "passed_tests": self.passed_tests,
                "failed_tests": self.failed_tests,
                "warnings": self.warnings,
                "success_rate_percent": round(success_rate, 1),
                "average_accuracy_percent": round(avg_accuracy, 1),
                "system_grade": grade,
                "performance_level": level
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
            "detailed_test_results": self.test_results,
            "final_assessment": {
                "meets_99_percent_target": success_rate >= 99 and avg_accuracy >= 99,
                "production_ready": success_rate >= 95 and avg_accuracy >= 95,
                "recommendations": self.generate_final_recommendations(success_rate, avg_accuracy, categories)
            }
        }
        
        # 保存报告
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"final_99_plus_regression_test_report_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        # 输出详细摘要
        logger.info(f"\n{'='*100}")
        logger.info(f"最终99%+准确率回归测试完成")
        logger.info(f"{'='*100}")
        logger.info(f"测试概况:")
        logger.info(f"  总测试数: {self.total_tests}")
        logger.info(f"  通过: {self.passed_tests} | 失败: {self.failed_tests} | 警告: {self.warnings}")
        logger.info(f"  成功率: {success_rate:.1f}%")
        logger.info(f"  平均准确率: {avg_accuracy:.1f}%")
        logger.info(f"  系统等级: {grade}")
        logger.info(f"  测试耗时: {total_time:.1f}秒")
        logger.info(f"")
        logger.info(f"分类表现详情:")
        for cat, data in categories.items():
            pass_rate = data['passed'] / data['total'] * 100
            logger.info(f"  {cat}: {data['passed']}/{data['total']} ({pass_rate:.1f}%) - 准确率{data['avg_accuracy']:.1f}%")
        logger.info(f"")
        logger.info(f"最终评估:")
        if success_rate >= 99 and avg_accuracy >= 99:
            logger.info(f"  ✅ 系统达到99%+准确率标准")
            logger.info(f"  ✅ 准备就绪用于生产环境")
        elif success_rate >= 95 and avg_accuracy >= 95:
            logger.info(f"  ⚠️  系统接近99%标准，表现优秀")
            logger.info(f"  ✅ 可用于生产环境")
        else:
            logger.info(f"  ❌ 系统未达到99%标准")
            logger.info(f"  ⚠️  需要进一步优化")
        logger.info(f"")
        logger.info(f"详细报告保存至: {filename}")
        logger.info(f"{'='*100}")
    
    def generate_final_recommendations(self, success_rate: float, avg_accuracy: float, categories: Dict) -> List[str]:
        """生成最终改进建议"""
        recommendations = []
        
        if success_rate >= 99 and avg_accuracy >= 99:
            recommendations.append("🎉 系统已达到99%+准确率标准，表现完美")
            recommendations.append("✅ 系统准备就绪，可部署到生产环境")
            recommendations.append("📊 建议定期监控以维持高准确率水平")
        elif success_rate >= 95 and avg_accuracy >= 95:
            recommendations.append("✅ 系统表现优秀，接近99%标准")
            recommendations.append("🔧 微调以下方面可达到完美水平:")
            
            # 分析具体需要改进的类别
            for cat, data in categories.items():
                pass_rate = data['passed'] / data['total'] * 100
                if pass_rate < 100:
                    recommendations.append(f"   - 优化{cat}类别测试 (当前{pass_rate:.1f}%)")
        else:
            recommendations.append("⚠️ 系统需要重点改进以达到99%标准")
            recommendations.append("🔧 建议优先处理以下问题:")
            
            # 识别问题最严重的类别
            problem_categories = []
            for cat, data in categories.items():
                pass_rate = data['passed'] / data['total'] * 100
                if pass_rate < 80:
                    problem_categories.append((cat, pass_rate))
            
            problem_categories.sort(key=lambda x: x[1])  # 按通过率排序
            
            for cat, pass_rate in problem_categories:
                recommendations.append(f"   - 修复{cat}类别问题 (通过率仅{pass_rate:.1f}%)")
        
        return recommendations

def main():
    """主函数"""
    print("启动最终99%+准确率回归测试")
    print("针对系统核心功能进行精确验证")
    print("目标: 确保系统达到99%+准确率标准")
    print("="*100)
    
    tester = Final99PlusRegressionTest()
    tester.run_final_99_plus_test()

if __name__ == "__main__":
    main()