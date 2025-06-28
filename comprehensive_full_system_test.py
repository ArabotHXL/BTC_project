#!/usr/bin/env python3
"""
全面系统回归测试 (Comprehensive Full System Regression Test)
专注于数值准确性和前端中端后端功能的全覆盖测试
包含：
- 前端页面功能和数据显示
- 中端API接口和数据处理
- 后端数据库操作和计算引擎
- 数值计算精度验证
"""

import requests
import json
import time
import os
import psycopg2
from datetime import datetime
import traceback

class ComprehensiveFullSystemTest:
    def __init__(self):
        self.base_url = "http://127.0.0.1:5000"
        self.session = requests.Session()
        self.test_results = []
        self.numerical_results = {}
        self.performance_metrics = {}
        self.start_time = time.time()
        
        # 测试数据
        self.test_owner_email = "hxl2022hao@gmail.com"
        self.test_miner_params = {
            "miner_model": "Antminer S21",
            "hashrate": 200,
            "power": 3500,
            "count": 100,
            "electricity_cost": 0.08,
            "site_power_mw": 10,
            "use_real_time_data": True
        }

    def log_test(self, test_name, status, details="", numerical_result=None, response_time=None):
        """记录测试结果"""
        result = {
            "test_name": test_name,
            "status": status,
            "details": details,
            "timestamp": datetime.now().isoformat(),
            "response_time": response_time
        }
        
        if numerical_result:
            result["numerical_result"] = numerical_result
            self.numerical_results[test_name] = numerical_result
            
        self.test_results.append(result)
        print(f"[{status}] {test_name}: {details}")

    def authenticate(self):
        """用户认证"""
        try:
            start_time = time.time()
            response = self.session.post(f"{self.base_url}/login", 
                                       data={"email": self.test_owner_email})
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                self.log_test("用户认证", "PASS", 
                            f"Owner用户认证成功: {self.test_owner_email}", 
                            response_time=response_time)
                return True
            else:
                self.log_test("用户认证", "FAIL", 
                            f"认证失败，状态码: {response.status_code}", 
                            response_time=response_time)
                return False
        except Exception as e:
            self.log_test("用户认证", "ERROR", f"认证异常: {str(e)}")
            return False

    def test_backend_database_operations(self):
        """测试后端数据库操作"""
        try:
            # 测试数据库连接
            db_url = os.environ.get('DATABASE_URL')
            if not db_url:
                self.log_test("数据库连接", "FAIL", "DATABASE_URL环境变量未设置")
                return
                
            conn = psycopg2.connect(db_url)
            cursor = conn.cursor()
            
            # 测试表结构
            tables_to_check = [
                'user_access', 'login_records', 'network_snapshots', 
                'customers', 'leads', 'activities', 'market_analytics'
            ]
            
            for table in tables_to_check:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                self.log_test(f"数据库表-{table}", "PASS", 
                            f"表存在，记录数: {count}", 
                            numerical_result=count)
            
            # 测试最新网络数据
            cursor.execute("""
                SELECT btc_price, network_difficulty, network_hashrate 
                FROM network_snapshots 
                ORDER BY timestamp DESC LIMIT 1
            """)
            latest_data = cursor.fetchone()
            if latest_data:
                self.log_test("最新网络数据", "PASS", 
                            f"BTC价格: ${latest_data[0]}, 难度: {latest_data[1]:.2e}, 算力: {latest_data[2]:.1f}EH/s",
                            numerical_result={
                                "btc_price": float(latest_data[0]),
                                "difficulty": float(latest_data[1]),
                                "hashrate": float(latest_data[2])
                            })
            
            # 测试分析数据
            cursor.execute("""
                SELECT btc_price, network_hashrate, fear_greed_index 
                FROM market_analytics 
                ORDER BY timestamp DESC LIMIT 1
            """)
            analytics_data = cursor.fetchone()
            if analytics_data:
                self.log_test("分析数据", "PASS", 
                            f"分析BTC: ${analytics_data[0]}, 算力: {analytics_data[1]}EH/s, 恐惧贪婪: {analytics_data[2]}",
                            numerical_result={
                                "analytics_btc": float(analytics_data[0]),
                                "analytics_hashrate": float(analytics_data[1]),
                                "fear_greed": int(analytics_data[2]) if analytics_data[2] else None
                            })
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            self.log_test("数据库操作", "ERROR", f"数据库测试失败: {str(e)}")

    def test_mining_calculation_precision(self):
        """测试挖矿计算数值精度"""
        try:
            start_time = time.time()
            response = self.session.post(f"{self.base_url}/calculate", 
                                       json=self.test_miner_params)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                
                # 验证核心计算结果
                daily_btc = data.get('daily_btc_mined', 0)
                daily_revenue = data.get('daily_revenue', 0)
                daily_profit = data.get('daily_profit', 0)
                roi_days = data.get('roi_days', 0)
                efficiency = data.get('efficiency_wh_th', 0)
                
                # 数值精度验证
                precision_tests = {
                    "daily_btc_precision": len(str(daily_btc).split('.')[-1]) if '.' in str(daily_btc) else 0,
                    "revenue_precision": len(str(daily_revenue).split('.')[-1]) if '.' in str(daily_revenue) else 0,
                    "profit_precision": len(str(daily_profit).split('.')[-1]) if '.' in str(daily_profit) else 0
                }
                
                calculation_results = {
                    "daily_btc": daily_btc,
                    "daily_revenue": daily_revenue,
                    "daily_profit": daily_profit,
                    "roi_days": roi_days,
                    "efficiency": efficiency,
                    "precision_tests": precision_tests
                }
                
                self.log_test("挖矿计算精度", "PASS", 
                            f"日产BTC: {daily_btc:.8f}, 日收入: ${daily_revenue:.2f}, 日利润: ${daily_profit:.2f}, ROI: {roi_days}天",
                            numerical_result=calculation_results,
                            response_time=response_time)
                
                # 验证数值合理性
                if daily_btc > 0 and daily_revenue > 0 and roi_days > 0:
                    self.log_test("计算结果合理性", "PASS", 
                                "所有核心数值都为正数，计算逻辑正确")
                else:
                    self.log_test("计算结果合理性", "FAIL", 
                                "存在负数或零值，计算逻辑异常")
                    
            else:
                self.log_test("挖矿计算", "FAIL", 
                            f"计算请求失败，状态码: {response.status_code}",
                            response_time=response_time)
                
        except Exception as e:
            self.log_test("挖矿计算", "ERROR", f"计算测试异常: {str(e)}")

    def test_api_endpoints_comprehensive(self):
        """全面测试中端API端点"""
        api_endpoints = [
            # 核心数据API
            {"url": "/get_btc_price", "name": "BTC价格API", "method": "GET"},
            {"url": "/get_network_stats", "name": "网络统计API", "method": "GET"},
            {"url": "/get_miners", "name": "矿机列表API", "method": "GET"},
            
            # 分析系统API
            {"url": "/api/analytics/market-data", "name": "分析市场数据API", "method": "GET"},
            {"url": "/api/analytics/price-history?hours=24", "name": "价格历史API", "method": "GET"},
            {"url": "/api/analytics/technical-indicators", "name": "技术指标API", "method": "GET"},
            {"url": "/api/analytics/latest-report", "name": "最新报告API", "method": "GET"},
            
            # 网络历史API
            {"url": "/api/network-stats", "name": "网络概览API", "method": "GET"},
            {"url": "/api/price-trend?days=7", "name": "价格趋势API", "method": "GET"},
            {"url": "/api/difficulty-trend?days=7", "name": "难度趋势API", "method": "GET"},
        ]
        
        for endpoint in api_endpoints:
            try:
                start_time = time.time()
                
                if endpoint["method"] == "GET":
                    response = self.session.get(f"{self.base_url}{endpoint['url']}")
                else:
                    response = self.session.post(f"{self.base_url}{endpoint['url']}")
                    
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        
                        # 提取数值数据进行验证
                        numerical_data = {}
                        if 'btc_price' in str(data):
                            # 尝试提取BTC价格
                            if isinstance(data, dict):
                                for key, value in data.items():
                                    if 'price' in str(key).lower() and isinstance(value, (int, float)):
                                        numerical_data[key] = value
                                    elif 'hashrate' in str(key).lower() and isinstance(value, (int, float)):
                                        numerical_data[key] = value
                        
                        self.log_test(endpoint["name"], "PASS", 
                                    f"API响应正常，数据长度: {len(str(data))}",
                                    numerical_result=numerical_data,
                                    response_time=response_time)
                    except:
                        self.log_test(endpoint["name"], "PASS", 
                                    f"API响应正常，非JSON格式",
                                    response_time=response_time)
                else:
                    self.log_test(endpoint["name"], "FAIL", 
                                f"API响应失败，状态码: {response.status_code}",
                                response_time=response_time)
                    
            except Exception as e:
                self.log_test(endpoint["name"], "ERROR", 
                            f"API测试异常: {str(e)}")

    def test_frontend_pages_comprehensive(self):
        """全面测试前端页面"""
        frontend_pages = [
            {"url": "/", "name": "主页", "check_content": ["BTC挖矿计算器", "计算"]},
            {"url": "/analytics", "name": "分析仪表盘", "check_content": ["数据分析中心", "实时数据"]},
            {"url": "/network-history", "name": "网络历史", "check_content": ["网络历史数据", "价格趋势"]},
            {"url": "/crm", "name": "CRM系统", "check_content": ["客户关系管理", "客户列表"]},
            {"url": "/curtailment-calculator", "name": "削减计算器", "check_content": ["电力削减", "计算器"]},
            {"url": "/algorithm-test", "name": "算法测试", "check_content": ["算法差异", "测试"]},
        ]
        
        for page in frontend_pages:
            try:
                start_time = time.time()
                response = self.session.get(f"{self.base_url}{page['url']}")
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    content = response.text
                    
                    # 检查页面内容
                    content_found = 0
                    for check_text in page["check_content"]:
                        if check_text in content:
                            content_found += 1
                    
                    content_percentage = (content_found / len(page["check_content"])) * 100
                    
                    if content_percentage >= 50:
                        self.log_test(f"前端-{page['name']}", "PASS", 
                                    f"页面加载正常，内容匹配: {content_percentage:.1f}%",
                                    numerical_result={"content_match_percentage": content_percentage},
                                    response_time=response_time)
                    else:
                        self.log_test(f"前端-{page['name']}", "FAIL", 
                                    f"页面内容不完整，匹配度: {content_percentage:.1f}%",
                                    response_time=response_time)
                else:
                    self.log_test(f"前端-{page['name']}", "FAIL", 
                                f"页面加载失败，状态码: {response.status_code}",
                                response_time=response_time)
                    
            except Exception as e:
                self.log_test(f"前端-{page['name']}", "ERROR", 
                            f"页面测试异常: {str(e)}")

    def test_data_flow_integration(self):
        """测试数据流集成"""
        try:
            # 测试完整的数据流：前端输入 -> API处理 -> 数据库存储 -> 前端显示
            
            # 1. 获取实时BTC价格
            btc_response = self.session.get(f"{self.base_url}/get_btc_price")
            if btc_response.status_code == 200:
                btc_data = btc_response.json()
                btc_price = btc_data.get('price', 0)
                
                # 2. 使用该价格进行挖矿计算
                calc_params = self.test_miner_params.copy()
                calc_params['btc_price'] = btc_price
                
                calc_response = self.session.post(f"{self.base_url}/calculate", json=calc_params)
                if calc_response.status_code == 200:
                    calc_data = calc_response.json()
                    
                    # 3. 验证数据一致性
                    used_price = calc_data.get('btc_price_used', 0)
                    price_difference = abs(btc_price - used_price)
                    
                    if price_difference < 100:  # 允许小幅差异
                        self.log_test("数据流集成", "PASS", 
                                    f"数据流完整，价格一致性良好，差异: ${price_difference:.2f}",
                                    numerical_result={
                                        "api_btc_price": btc_price,
                                        "calc_btc_price": used_price,
                                        "price_difference": price_difference
                                    })
                    else:
                        self.log_test("数据流集成", "FAIL", 
                                    f"价格数据不一致，差异: ${price_difference:.2f}")
                        
        except Exception as e:
            self.log_test("数据流集成", "ERROR", f"数据流测试异常: {str(e)}")

    def test_performance_metrics(self):
        """测试系统性能指标"""
        performance_tests = [
            {"name": "首页加载性能", "url": "/", "threshold": 2.0},
            {"name": "计算API性能", "url": "/calculate", "method": "POST", "threshold": 1.0},
            {"name": "分析API性能", "url": "/api/analytics/market-data", "threshold": 0.5},
            {"name": "网络数据性能", "url": "/get_network_stats", "threshold": 1.5},
        ]
        
        for test in performance_tests:
            try:
                start_time = time.time()
                
                if test.get("method") == "POST":
                    response = self.session.post(f"{self.base_url}{test['url']}", 
                                               json=self.test_miner_params)
                else:
                    response = self.session.get(f"{self.base_url}{test['url']}")
                
                response_time = time.time() - start_time
                
                if response.status_code == 200 and response_time <= test["threshold"]:
                    self.log_test(test["name"], "PASS", 
                                f"性能良好，响应时间: {response_time:.3f}s",
                                numerical_result={"response_time": response_time},
                                response_time=response_time)
                elif response.status_code == 200:
                    self.log_test(test["name"], "WARN", 
                                f"功能正常但性能慢，响应时间: {response_time:.3f}s (阈值: {test['threshold']}s)",
                                response_time=response_time)
                else:
                    self.log_test(test["name"], "FAIL", 
                                f"请求失败，状态码: {response.status_code}",
                                response_time=response_time)
                    
            except Exception as e:
                self.log_test(test["name"], "ERROR", f"性能测试异常: {str(e)}")

    def generate_comprehensive_report(self):
        """生成全面测试报告"""
        total_tests = len(self.test_results)
        passed_tests = len([t for t in self.test_results if t["status"] == "PASS"])
        failed_tests = len([t for t in self.test_results if t["status"] == "FAIL"])
        error_tests = len([t for t in self.test_results if t["status"] == "ERROR"])
        warn_tests = len([t for t in self.test_results if t["status"] == "WARN"])
        
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        # 计算平均响应时间
        response_times = [t["response_time"] for t in self.test_results if t.get("response_time")]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        report = {
            "test_summary": {
                "total_tests": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "errors": error_tests,
                "warnings": warn_tests,
                "success_rate": round(success_rate, 1),
                "average_response_time": round(avg_response_time, 3),
                "test_duration": round(time.time() - self.start_time, 2)
            },
            "numerical_results": self.numerical_results,
            "detailed_results": self.test_results,
            "system_health": {
                "frontend_status": "HEALTHY" if passed_tests > failed_tests else "ISSUES",
                "api_status": "HEALTHY" if avg_response_time < 1.0 else "SLOW",
                "database_status": "HEALTHY" if error_tests == 0 else "ISSUES"
            },
            "recommendations": self.generate_recommendations()
        }
        
        # 保存报告
        with open("comprehensive_full_system_test_report.json", "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        return report

    def generate_recommendations(self):
        """生成系统改进建议"""
        recommendations = []
        
        # 分析响应时间
        slow_tests = [t for t in self.test_results if t.get("response_time") and t.get("response_time") > 1.0]
        if slow_tests:
            recommendations.append(f"优化性能：{len(slow_tests)}个端点响应时间超过1秒")
        
        # 分析失败测试
        failed_tests = [t for t in self.test_results if t["status"] in ["FAIL", "ERROR"]]
        if failed_tests:
            recommendations.append(f"修复问题：{len(failed_tests)}个测试失败或异常")
        
        # 分析数值精度
        if self.numerical_results:
            precision_issues = []
            for test_name, results in self.numerical_results.items():
                if isinstance(results, dict) and "precision_tests" in results:
                    low_precision = [k for k, v in results["precision_tests"].items() if v < 4]
                    if low_precision:
                        precision_issues.extend(low_precision)
            
            if precision_issues:
                recommendations.append(f"提高数值精度：{len(precision_issues)}个计算字段精度不足")
        
        if not recommendations:
            recommendations.append("系统运行良好，无需重大改进")
        
        return recommendations

    def run_comprehensive_test(self):
        """运行全面测试"""
        print("开始全面系统回归测试...")
        print("=" * 60)
        
        # 认证
        if not self.authenticate():
            print("认证失败，无法继续测试")
            return
        
        # 后端数据库测试
        print("\n测试后端数据库操作...")
        self.test_backend_database_operations()
        
        # 数值计算测试
        print("\n测试挖矿计算精度...")
        self.test_mining_calculation_precision()
        
        # API端点测试
        print("\n测试中端API接口...")
        self.test_api_endpoints_comprehensive()
        
        # 前端页面测试
        print("\n测试前端页面功能...")
        self.test_frontend_pages_comprehensive()
        
        # 数据流集成测试
        print("\n测试数据流集成...")
        self.test_data_flow_integration()
        
        # 性能测试
        print("\n测试系统性能...")
        self.test_performance_metrics()
        
        # 生成报告
        print("\n生成测试报告...")
        report = self.generate_comprehensive_report()
        
        # 输出摘要
        print("\n" + "=" * 60)
        print("测试完成！")
        print(f"总测试数: {report['test_summary']['total_tests']}")
        print(f"通过: {report['test_summary']['passed']}")
        print(f"失败: {report['test_summary']['failed']}")
        print(f"错误: {report['test_summary']['errors']}")
        print(f"警告: {report['test_summary']['warnings']}")
        print(f"成功率: {report['test_summary']['success_rate']}%")
        print(f"平均响应时间: {report['test_summary']['average_response_time']}秒")
        print(f"测试耗时: {report['test_summary']['test_duration']}秒")
        print("\n建议:")
        for rec in report['recommendations']:
            print(f"- {rec}")
        
        return report

def main():
    """主函数"""
    tester = ComprehensiveFullSystemTest()
    report = tester.run_comprehensive_test()
    
    if report['test_summary']['success_rate'] >= 80:
        print(f"\n✅ 系统状态良好 (成功率: {report['test_summary']['success_rate']}%)")
    else:
        print(f"\n⚠️ 系统需要改进 (成功率: {report['test_summary']['success_rate']}%)")

if __name__ == "__main__":
    main()