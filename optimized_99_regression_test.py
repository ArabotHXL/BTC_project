#!/usr/bin/env python3
"""
优化的99%准确率回归测试
Optimized 99% Accuracy Regression Test

专注于核心功能和数值准确性验证
Focus on core functionality and numerical accuracy validation
"""

import json
import time
import requests
import psycopg2
from datetime import datetime
from typing import Dict, List, Any, Tuple, Optional
import os
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Optimized99RegressionTest:
    """优化的99%准确率回归测试器"""
    
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
        """认证测试"""
        try:
            start_time = time.time()
            
            # 访问登录页面
            response = self.session.get(f"{self.base_url}/")
            
            # 提交登录
            login_data = {"email": self.test_email}
            response = self.session.post(f"{self.base_url}/login", data=login_data, allow_redirects=True)
            
            response_time = time.time() - start_time
            
            if response.status_code == 200 and "logout" in response.text.lower():
                self.log_test("Authentication", "login", "PASS", 
                            f"成功认证", response_time)
                return True
            else:
                self.log_test("Authentication", "login", "FAIL", 
                            f"认证失败: {response.status_code}", response_time)
                return False
                
        except Exception as e:
            self.log_test("Authentication", "login", "FAIL", 
                        f"认证异常: {str(e)}")
            return False
    
    def test_core_apis(self) -> None:
        """测试核心API的准确性"""
        logger.info("测试核心API准确性...")
        
        # BTC价格API测试
        try:
            start_time = time.time()
            response = self.session.get(f"{self.base_url}/api/btc-price")
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success') and isinstance(data.get('btc_price'), (int, float)):
                    price = data['btc_price']
                    if 50000 <= price <= 200000:
                        self.log_test("Core_APIs", "btc_price", "PASS",
                                    f"BTC价格${price:,.2f}合理", response_time, 100.0)
                    else:
                        self.log_test("Core_APIs", "btc_price", "WARNING",
                                    f"BTC价格${price:,.2f}超出预期范围", response_time, 80.0)
                else:
                    self.log_test("Core_APIs", "btc_price", "FAIL",
                                "价格数据格式错误", response_time, 0.0)
            else:
                self.log_test("Core_APIs", "btc_price", "FAIL",
                            f"API请求失败: {response.status_code}", response_time, 0.0)
        except Exception as e:
            self.log_test("Core_APIs", "btc_price", "FAIL", f"请求异常: {str(e)}", 0.0, 0.0)
        
        # 网络统计API测试
        try:
            start_time = time.time()
            response = self.session.get(f"{self.base_url}/api/network-stats")
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    hashrate = data.get('network_hashrate')
                    if isinstance(hashrate, (int, float)) and 400 <= hashrate <= 2000:
                        self.log_test("Core_APIs", "network_stats", "PASS",
                                    f"网络算力{hashrate}EH/s合理", response_time, 100.0)
                    else:
                        self.log_test("Core_APIs", "network_stats", "WARNING",
                                    f"网络算力{hashrate}EH/s异常", response_time, 70.0)
                else:
                    self.log_test("Core_APIs", "network_stats", "FAIL",
                                "网络统计数据无效", response_time, 0.0)
            else:
                self.log_test("Core_APIs", "network_stats", "FAIL",
                            f"API请求失败: {response.status_code}", response_time, 0.0)
        except Exception as e:
            self.log_test("Core_APIs", "network_stats", "FAIL", f"请求异常: {str(e)}", 0.0, 0.0)
        
        # 矿机数据API测试
        try:
            start_time = time.time()
            response = self.session.get(f"{self.base_url}/api/miners")
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    miners = data.get('miners', [])
                    if len(miners) >= 8:
                        self.log_test("Core_APIs", "miners", "PASS",
                                    f"矿机数据包含{len(miners)}个型号", response_time, 100.0)
                    else:
                        self.log_test("Core_APIs", "miners", "WARNING",
                                    f"矿机数量不足: {len(miners)}", response_time, 70.0)
                else:
                    self.log_test("Core_APIs", "miners", "FAIL",
                                "矿机数据无效", response_time, 0.0)
            else:
                self.log_test("Core_APIs", "miners", "FAIL",
                            f"API请求失败: {response.status_code}", response_time, 0.0)
        except Exception as e:
            self.log_test("Core_APIs", "miners", "FAIL", f"请求异常: {str(e)}", 0.0, 0.0)
    
    def test_mining_calculations(self) -> None:
        """测试挖矿计算准确性"""
        logger.info("测试挖矿计算准确性...")
        
        # 标准计算测试
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
                    logger.info(f"计算结果: {result}")
                    
                    # 检查关键计算字段 - 使用实际返回的字段名
                    required_fields = ['site_daily_btc_output', 'revenue', 'profit']
                    missing_fields = [f for f in required_fields if f not in result]
                    
                    # 验证数值合理性 - 直接从结果中获取数据
                    btc_output = result.get('site_daily_btc_output', 0)
                    revenue_data = result.get('revenue', {})
                    profit_data = result.get('profit', {})
                    
                    daily_revenue = revenue_data.get('daily', 0) if isinstance(revenue_data, dict) else 0
                    daily_profit = profit_data.get('daily', 0) if isinstance(profit_data, dict) else 0
                    
                    if btc_output and daily_revenue and daily_profit is not None:
                        
                        accuracy = 100.0
                        issues = []
                        
                        # BTC产出合理性 (单台S19 Pro每日约0.001-0.1 BTC)
                        if not (0.001 <= btc_output <= 0.1):
                            accuracy -= 20.0
                            issues.append(f"BTC产出{btc_output}异常")
                        
                        # 收益合理性 (日收益应为正数且合理)
                        if daily_revenue <= 0 or daily_revenue > 1000:
                            accuracy -= 20.0
                            issues.append(f"日收益${daily_revenue}异常")
                        
                        # 利润可为负数但不应过极端
                        if abs(daily_profit) > 1000:
                            accuracy -= 10.0
                            issues.append(f"日利润${daily_profit}过极端")
                        
                        status = "PASS" if accuracy >= 99 else ("WARNING" if accuracy >= 90 else "FAIL")
                        details = f"准确率{accuracy}%" + (f" (问题: {'; '.join(issues)})" if issues else "")
                        
                        self.log_test("Mining_Calculations", "s19_pro_standard", status,
                                    details, response_time, accuracy)
                    else:
                        self.log_test("Mining_Calculations", "s19_pro_standard", "FAIL",
                                    f"缺失字段: {missing_fields}", response_time, 0.0)
                        
                except json.JSONDecodeError as e:
                    self.log_test("Mining_Calculations", "s19_pro_standard", "FAIL",
                                f"JSON解析失败: {str(e)}", response_time, 0.0)
            else:
                self.log_test("Mining_Calculations", "s19_pro_standard", "FAIL",
                            f"计算请求失败: {response.status_code}", response_time, 0.0)
                
        except Exception as e:
            self.log_test("Mining_Calculations", "s19_pro_standard", "FAIL",
                        f"计算异常: {str(e)}", 0.0, 0.0)
    
    def test_analytics_system(self) -> None:
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
                    
                    accuracy = 100.0
                    if not (isinstance(btc_price, (int, float)) and 50000 <= btc_price <= 200000):
                        accuracy -= 30.0
                    if not (isinstance(hashrate, (int, float)) and 400 <= hashrate <= 2000):
                        accuracy -= 30.0
                    
                    status = "PASS" if accuracy >= 99 else ("WARNING" if accuracy >= 80 else "FAIL")
                    self.log_test("Analytics_System", "market_data", status,
                                f"价格${btc_price}, 算力{hashrate}EH/s", response_time, accuracy)
                else:
                    self.log_test("Analytics_System", "market_data", "FAIL",
                                "分析数据无效", response_time, 0.0)
            else:
                self.log_test("Analytics_System", "market_data", "FAIL",
                            f"API请求失败: {response.status_code}", response_time, 0.0)
                            
        except Exception as e:
            self.log_test("Analytics_System", "market_data", "FAIL",
                        f"请求异常: {str(e)}", 0.0, 0.0)
    
    def test_database_health(self) -> None:
        """测试数据库健康状态"""
        logger.info("测试数据库健康状态...")
        
        try:
            conn = psycopg2.connect(self.db_url)
            cursor = conn.cursor()
            
            # 检查关键数据表
            tables = [
                ("market_analytics", "市场分析"),
                ("network_snapshots", "网络快照"),
                ("user_access", "用户访问")
            ]
            
            healthy_tables = 0
            for table_name, description in tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    count = cursor.fetchone()[0]
                    
                    if count > 0:
                        healthy_tables += 1
                        self.log_test("Database_Health", f"table_{table_name}", "PASS",
                                    f"{description}表{count}条记录", 0.0, 100.0)
                    else:
                        self.log_test("Database_Health", f"table_{table_name}", "WARNING",
                                    f"{description}表为空", 0.0, 70.0)
                        
                except psycopg2.Error as e:
                    self.log_test("Database_Health", f"table_{table_name}", "FAIL",
                                f"{description}表错误: {str(e)}", 0.0, 0.0)
            
            overall_health = (healthy_tables / len(tables)) * 100
            if overall_health >= 80:
                self.log_test("Database_Health", "overall", "PASS",
                            f"数据库健康度{overall_health:.1f}%", 0.0, overall_health)
            else:
                self.log_test("Database_Health", "overall", "FAIL",
                            f"数据库健康度{overall_health:.1f}%过低", 0.0, overall_health)
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            self.log_test("Database_Health", "connection", "FAIL",
                        f"数据库连接失败: {str(e)}", 0.0, 0.0)
    
    def test_ui_pages(self) -> None:
        """测试UI页面加载"""
        logger.info("测试UI页面加载...")
        
        pages = [
            ("/", "主页"),
            ("/network-history", "网络历史"),
            ("/analytics", "数据分析")
        ]
        
        for path, name in pages:
            try:
                start_time = time.time()
                response = self.session.get(f"{self.base_url}{path}")
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    content_length = len(response.text)
                    if content_length > 1000:  # 页面应有足够内容
                        self.log_test("UI_Pages", f"page_{path.replace('/', '_')}", "PASS",
                                    f"{name}页面加载成功({content_length}字符)", response_time, 100.0)
                    else:
                        self.log_test("UI_Pages", f"page_{path.replace('/', '_')}", "WARNING",
                                    f"{name}页面内容过少({content_length}字符)", response_time, 70.0)
                else:
                    self.log_test("UI_Pages", f"page_{path.replace('/', '_')}", "FAIL",
                                f"{name}页面加载失败: {response.status_code}", response_time, 0.0)
                                
            except Exception as e:
                self.log_test("UI_Pages", f"page_{path.replace('/', '_')}", "FAIL",
                            f"{name}页面异常: {str(e)}", 0.0, 0.0)
    
    def run_optimized_99_test(self) -> None:
        """运行优化的99%准确率测试"""
        logger.info("开始运行优化的99%准确率回归测试")
        start_time = time.time()
        
        # 认证
        if not self.authenticate():
            logger.error("认证失败，测试终止")
            return
        
        # 运行各项测试
        self.test_core_apis()
        self.test_mining_calculations()
        self.test_analytics_system()
        self.test_database_health()
        self.test_ui_pages()
        
        # 生成报告
        total_time = time.time() - start_time
        self.generate_optimized_report(total_time)
    
    def generate_optimized_report(self, total_time: float) -> None:
        """生成优化测试报告"""
        success_rate = (self.passed_tests / self.total_tests * 100) if self.total_tests > 0 else 0
        
        # 计算加权准确率
        accuracy_scores = [r['accuracy'] for r in self.test_results if r.get('accuracy', 0) > 0]
        avg_accuracy = sum(accuracy_scores) / len(accuracy_scores) if accuracy_scores else 0
        
        # 确定系统等级
        if success_rate >= 99 and avg_accuracy >= 99:
            grade = "A+ (完美)"
        elif success_rate >= 95 and avg_accuracy >= 95:
            grade = "A (优秀)"
        elif success_rate >= 90 and avg_accuracy >= 90:
            grade = "B+ (良好)"
        elif success_rate >= 80 and avg_accuracy >= 80:
            grade = "B (合格)"
        else:
            grade = "C (需改进)"
        
        # 计算各类别通过率
        categories = {}
        for result in self.test_results:
            cat = result['category']
            if cat not in categories:
                categories[cat] = {'total': 0, 'passed': 0}
            categories[cat]['total'] += 1
            if result['status'] == 'PASS':
                categories[cat]['passed'] += 1
        
        report = {
            "test_summary": {
                "timestamp": datetime.now().isoformat(),
                "total_tests": self.total_tests,
                "passed_tests": self.passed_tests,
                "failed_tests": self.failed_tests,
                "warnings": self.warnings,
                "success_rate": round(success_rate, 1),
                "average_accuracy": round(avg_accuracy, 1),
                "system_grade": grade,
                "total_time_seconds": round(total_time, 1)
            },
            "category_performance": {
                cat: {
                    "passed": data['passed'],
                    "total": data['total'],
                    "pass_rate": round(data['passed'] / data['total'] * 100, 1)
                }
                for cat, data in categories.items()
            },
            "detailed_results": self.test_results,
            "recommendations": self.generate_recommendations(success_rate, avg_accuracy, categories)
        }
        
        # 保存报告
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"optimized_99_regression_test_report_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        # 输出摘要
        logger.info(f"\n{'='*80}")
        logger.info(f"优化的99%准确率回归测试完成")
        logger.info(f"{'='*80}")
        logger.info(f"总测试数: {self.total_tests}")
        logger.info(f"通过: {self.passed_tests} | 失败: {self.failed_tests} | 警告: {self.warnings}")
        logger.info(f"成功率: {success_rate:.1f}%")
        logger.info(f"平均准确率: {avg_accuracy:.1f}%")
        logger.info(f"系统等级: {grade}")
        logger.info(f"测试耗时: {total_time:.1f}秒")
        logger.info(f"详细报告: {filename}")
        
        # 输出各类别表现
        logger.info(f"\n类别表现:")
        for cat, data in categories.items():
            pass_rate = data['passed'] / data['total'] * 100
            logger.info(f"  {cat}: {data['passed']}/{data['total']} ({pass_rate:.1f}%)")
        
        logger.info(f"{'='*80}")
    
    def generate_recommendations(self, success_rate: float, avg_accuracy: float, categories: Dict) -> List[str]:
        """生成改进建议"""
        recommendations = []
        
        if success_rate < 99:
            recommendations.append(f"系统成功率{success_rate:.1f}%需提升至99%+")
        
        if avg_accuracy < 99:
            recommendations.append(f"平均准确率{avg_accuracy:.1f}%需提升至99%+")
        
        # 分析失败的类别
        for cat, data in categories.items():
            pass_rate = data['passed'] / data['total'] * 100
            if pass_rate < 80:
                recommendations.append(f"{cat}类别通过率{pass_rate:.1f}%过低，需要重点优化")
        
        if not recommendations:
            recommendations.append("系统表现优秀，已达到99%+准确率标准")
        
        return recommendations

def main():
    """主函数"""
    print("启动优化的99%准确率回归测试")
    print("专注于核心功能和数值准确性验证")
    print("="*80)
    
    tester = Optimized99RegressionTest()
    tester.run_optimized_99_test()

if __name__ == "__main__":
    main()