#!/usr/bin/env python3
"""
分析系统深度测试 (Analytics System Comprehensive Test)
全面测试分析系统的所有组件和功能
"""

import os
import psycopg2
import requests
import json
import time
from datetime import datetime, timedelta
import pandas as pd
import threading
import sys

class AnalyticsSystemTester:
    def __init__(self):
        self.db_url = os.environ.get('DATABASE_URL')
        self.base_url = "http://localhost:5000"
        self.analytics_url = "http://localhost:5001"
        self.test_results = []
        self.start_time = datetime.now()
        
    def log_test(self, test_name, status, details="", response_time=None):
        """记录测试结果"""
        result = {
            "test_name": test_name,
            "status": status,
            "details": details,
            "response_time": response_time,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        status_symbol = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        time_info = f" ({response_time:.2f}s)" if response_time else ""
        print(f"{status_symbol} {test_name}{time_info}: {details}")

    def test_analytics_database_structure(self):
        """测试分析系统数据库结构"""
        test_start = time.time()
        try:
            conn = psycopg2.connect(self.db_url)
            cursor = conn.cursor()
            
            # 检查分析表是否存在
            analytics_tables = [
                'market_analytics',
                'technical_indicators', 
                'analysis_reports',
                'mining_metrics'
            ]
            
            table_status = {}
            for table in analytics_tables:
                cursor.execute(f"""
                    SELECT COUNT(*) FROM information_schema.tables 
                    WHERE table_name = '{table}'
                """)
                exists = cursor.fetchone()[0] > 0
                
                if exists:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    table_status[table] = f"存在({count}条记录)"
                else:
                    table_status[table] = "不存在"
            
            cursor.close()
            conn.close()
            
            response_time = time.time() - test_start
            all_exist = all("存在" in status for status in table_status.values())
            
            if all_exist:
                details = "; ".join([f"{table}: {status}" for table, status in table_status.items()])
                self.log_test("Analytics Database Structure", "PASS", 
                             f"分析表结构完整 - {details}", response_time)
            else:
                missing = [table for table, status in table_status.items() if "不存在" in status]
                self.log_test("Analytics Database Structure", "FAIL", 
                             f"缺少分析表: {missing}", response_time)
                             
        except Exception as e:
            response_time = time.time() - test_start
            self.log_test("Analytics Database Structure", "FAIL", 
                         f"数据库检查失败: {str(e)}", response_time)

    def test_analytics_data_collection(self):
        """测试分析数据收集功能"""
        test_start = time.time()
        try:
            # 导入并测试分析引擎
            import analytics_engine
            
            # 创建分析引擎实例
            engine = analytics_engine.AnalyticsEngine()
            
            # 测试数据收集
            print("  开始测试数据收集...")
            engine.collect_and_analyze()
            
            # 验证数据是否被收集
            conn = psycopg2.connect(self.db_url)
            cursor = conn.cursor()
            
            # 检查最新的市场数据
            cursor.execute("""
                SELECT recorded_at, btc_price, network_hashrate, network_difficulty 
                FROM market_analytics 
                ORDER BY recorded_at DESC LIMIT 1
            """)
            market_data = cursor.fetchone()
            
            # 检查技术指标
            cursor.execute("""
                SELECT recorded_at, rsi_14, sma_20, sma_50 
                FROM technical_indicators 
                ORDER BY recorded_at DESC LIMIT 1
            """)
            tech_data = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            response_time = time.time() - test_start
            
            if market_data and tech_data:
                price = market_data[1]
                hashrate = market_data[2]
                rsi = tech_data[1] if tech_data[1] else "N/A"
                self.log_test("Analytics Data Collection", "PASS", 
                             f"数据收集成功 - BTC: ${price:.2f}, 算力: {hashrate:.1f}EH/s, RSI: {rsi}", 
                             response_time)
            else:
                self.log_test("Analytics Data Collection", "FAIL", 
                             "数据收集失败，未找到最新数据", response_time)
                             
        except Exception as e:
            response_time = time.time() - test_start
            self.log_test("Analytics Data Collection", "FAIL", 
                         f"数据收集测试失败: {str(e)}", response_time)

    def test_technical_indicators_calculation(self):
        """测试技术指标计算"""
        test_start = time.time()
        try:
            import analytics_engine
            
            # 创建技术分析器
            db_manager = analytics_engine.DatabaseManager()
            db_manager.connect()
            
            analyzer = analytics_engine.TechnicalAnalyzer(db_manager)
            
            # 计算技术指标
            indicators = analyzer.calculate_technical_indicators()
            
            response_time = time.time() - test_start
            
            if indicators:
                # 验证关键指标
                key_indicators = ['rsi_14', 'sma_20', 'sma_50', 'ema_12', 'ema_26']
                available_indicators = [ind for ind in key_indicators if ind in indicators and indicators[ind] is not None]
                
                if len(available_indicators) >= 3:
                    rsi = indicators.get('rsi_14', 'N/A')
                    sma20 = indicators.get('sma_20', 'N/A')
                    self.log_test("Technical Indicators Calculation", "PASS", 
                                 f"技术指标计算成功 - RSI: {rsi}, SMA20: {sma20}, 可用指标: {len(available_indicators)}/5", 
                                 response_time)
                else:
                    self.log_test("Technical Indicators Calculation", "WARN", 
                                 f"技术指标部分可用: {available_indicators}", response_time)
            else:
                self.log_test("Technical Indicators Calculation", "FAIL", 
                             "技术指标计算失败", response_time)
                             
        except Exception as e:
            response_time = time.time() - test_start
            self.log_test("Technical Indicators Calculation", "FAIL", 
                         f"技术指标计算异常: {str(e)}", response_time)

    def test_report_generation(self):
        """测试报告生成功能"""
        test_start = time.time()
        try:
            import analytics_engine
            
            # 创建报告生成器
            db_manager = analytics_engine.DatabaseManager()
            db_manager.connect()
            
            generator = analytics_engine.ReportGenerator(db_manager)
            
            # 生成日报
            report = generator.generate_daily_report()
            
            response_time = time.time() - test_start
            
            if report and 'title' in report:
                summary_length = len(report.get('summary', ''))
                recommendations_count = len(report.get('recommendations', []))
                risk_level = report.get('risk_assessment', {}).get('risk_level', 'Unknown')
                
                self.log_test("Report Generation", "PASS", 
                             f"报告生成成功 - 摘要: {summary_length}字符, 建议: {recommendations_count}条, 风险: {risk_level}", 
                             response_time)
            else:
                self.log_test("Report Generation", "FAIL", 
                             "报告生成失败或格式异常", response_time)
                             
        except Exception as e:
            response_time = time.time() - test_start
            self.log_test("Report Generation", "FAIL", 
                         f"报告生成异常: {str(e)}", response_time)

    def test_analytics_api_integration(self):
        """测试分析系统API集成"""
        test_start = time.time()
        
        # 创建会话并登录
        session = requests.Session()
        try:
            # 登录获取权限
            login_data = {'email': 'hxl2022hao@gmail.com'}
            login_response = session.post(f"{self.base_url}/login", data=login_data)
            
            # 测试主应用中的分析API端点
            api_endpoints = [
                ("/api/analytics/market-data", "市场数据API"),
                ("/api/analytics/latest-report", "最新报告API"),
                ("/api/analytics/technical-indicators", "技术指标API"),
                ("/api/analytics/price-history", "价格历史API")
            ]
            
            working_apis = 0
            api_details = []
            
            for endpoint, name in api_endpoints:
                try:
                    response = session.get(f"{self.base_url}{endpoint}", timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        if data:
                            working_apis += 1
                            api_details.append(f"{name}: 正常")
                        else:
                            api_details.append(f"{name}: 空数据")
                    else:
                        api_details.append(f"{name}: HTTP{response.status_code}")
                except Exception as e:
                    api_details.append(f"{name}: 异常")
            
            response_time = time.time() - test_start
            
            if working_apis >= 2:
                self.log_test("Analytics API Integration", "PASS", 
                             f"API集成正常 - {working_apis}/4个端点可用: {'; '.join(api_details)}", 
                             response_time)
            elif working_apis >= 1:
                self.log_test("Analytics API Integration", "WARN", 
                             f"API部分可用 - {working_apis}/4个端点: {'; '.join(api_details)}", 
                             response_time)
            else:
                self.log_test("Analytics API Integration", "FAIL", 
                             f"API集成失败 - 无可用端点: {'; '.join(api_details)}", 
                             response_time)
                             
        except Exception as e:
            response_time = time.time() - test_start
            self.log_test("Analytics API Integration", "FAIL", 
                         f"API集成测试异常: {str(e)}", response_time)

    def test_analytics_widget_integration(self):
        """测试分析小组件集成"""
        test_start = time.time()
        
        session = requests.Session()
        try:
            # 登录
            login_data = {'email': 'hxl2022hao@gmail.com'}
            session.post(f"{self.base_url}/login", data=login_data)
            
            # 获取主页内容
            main_page = session.get(f"{self.base_url}/")
            page_content = main_page.text
            
            # 检查分析小组件元素
            widget_elements = [
                'widget-btc-price',
                'widget-hashrate', 
                'widget-fear-greed',
                'Analytics Dashboard',
                'Data Analytics Center'
            ]
            
            found_elements = []
            for element in widget_elements:
                if element in page_content:
                    found_elements.append(element)
            
            response_time = time.time() - test_start
            
            if len(found_elements) >= 4:
                self.log_test("Analytics Widget Integration", "PASS", 
                             f"小组件集成完整 - 找到元素: {len(found_elements)}/5", response_time)
            elif len(found_elements) >= 2:
                self.log_test("Analytics Widget Integration", "WARN", 
                             f"小组件部分集成 - 找到元素: {len(found_elements)}/5", response_time)
            else:
                self.log_test("Analytics Widget Integration", "FAIL", 
                             f"小组件集成失败 - 仅找到: {len(found_elements)}/5", response_time)
                             
        except Exception as e:
            response_time = time.time() - test_start
            self.log_test("Analytics Widget Integration", "FAIL", 
                         f"小组件测试异常: {str(e)}", response_time)

    def test_data_quality_and_accuracy(self):
        """测试数据质量和准确性"""
        test_start = time.time()
        try:
            conn = psycopg2.connect(self.db_url)
            cursor = conn.cursor()
            
            # 检查市场数据质量
            cursor.execute("""
                SELECT COUNT(*), AVG(btc_price), MIN(btc_price), MAX(btc_price),
                       AVG(network_hashrate), MIN(network_hashrate), MAX(network_hashrate)
                FROM market_analytics 
                WHERE recorded_at > NOW() - INTERVAL '24 hours'
            """)
            market_stats = cursor.fetchone()
            
            # 检查数据一致性
            cursor.execute("""
                SELECT COUNT(*) FROM market_analytics 
                WHERE btc_price IS NULL OR network_hashrate IS NULL 
                OR btc_price <= 0 OR network_hashrate <= 0
            """)
            invalid_records = cursor.fetchone()[0]
            
            # 检查技术指标合理性
            cursor.execute("""
                SELECT COUNT(*), AVG(rsi_14), MIN(rsi_14), MAX(rsi_14)
                FROM technical_indicators 
                WHERE recorded_at > NOW() - INTERVAL '24 hours'
                AND rsi_14 IS NOT NULL
            """)
            rsi_stats = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            response_time = time.time() - test_start
            
            # 评估数据质量
            data_quality_issues = []
            
            if market_stats[0] == 0:
                data_quality_issues.append("无24小时内市场数据")
            
            if invalid_records > 0:
                data_quality_issues.append(f"{invalid_records}条无效记录")
            
            # BTC价格合理性检查
            if market_stats[1] and (market_stats[1] < 50000 or market_stats[1] > 200000):
                data_quality_issues.append("BTC价格异常")
            
            # 网络算力合理性检查
            if market_stats[4] and (market_stats[4] < 400 or market_stats[4] > 1500):
                data_quality_issues.append("网络算力异常")
            
            # RSI合理性检查
            if rsi_stats[0] > 0 and rsi_stats[1] and (rsi_stats[1] < 0 or rsi_stats[1] > 100):
                data_quality_issues.append("RSI指标异常")
            
            if not data_quality_issues:
                avg_price = market_stats[1] if market_stats[1] else 0
                avg_hashrate = market_stats[4] if market_stats[4] else 0
                avg_rsi = rsi_stats[1] if rsi_stats[1] else 0
                self.log_test("Data Quality and Accuracy", "PASS", 
                             f"数据质量优秀 - 24h记录: {market_stats[0]}条, 平均BTC: ${avg_price:.2f}, 平均算力: {avg_hashrate:.1f}EH/s, 平均RSI: {avg_rsi:.1f}", 
                             response_time)
            else:
                self.log_test("Data Quality and Accuracy", "WARN", 
                             f"数据质量问题: {'; '.join(data_quality_issues)}", response_time)
                             
        except Exception as e:
            response_time = time.time() - test_start
            self.log_test("Data Quality and Accuracy", "FAIL", 
                         f"数据质量检查异常: {str(e)}", response_time)

    def test_analytics_performance(self):
        """测试分析系统性能"""
        test_start = time.time()
        try:
            import analytics_engine
            
            # 测试数据收集性能
            engine = analytics_engine.AnalyticsEngine()
            
            collection_start = time.time()
            engine.collect_and_analyze()
            collection_time = time.time() - collection_start
            
            # 测试技术指标计算性能
            db_manager = analytics_engine.DatabaseManager()
            db_manager.connect()
            analyzer = analytics_engine.TechnicalAnalyzer(db_manager)
            
            calc_start = time.time()
            indicators = analyzer.calculate_technical_indicators()
            calc_time = time.time() - calc_start
            
            # 测试报告生成性能
            generator = analytics_engine.ReportGenerator(db_manager)
            
            report_start = time.time()
            report = generator.generate_daily_report()
            report_time = time.time() - report_start
            
            response_time = time.time() - test_start
            
            # 性能评估
            performance_issues = []
            if collection_time > 10:
                performance_issues.append(f"数据收集慢({collection_time:.1f}s)")
            if calc_time > 5:
                performance_issues.append(f"指标计算慢({calc_time:.1f}s)")
            if report_time > 3:
                performance_issues.append(f"报告生成慢({report_time:.1f}s)")
            
            if not performance_issues:
                self.log_test("Analytics Performance", "PASS", 
                             f"性能优秀 - 收集: {collection_time:.1f}s, 计算: {calc_time:.1f}s, 报告: {report_time:.1f}s", 
                             response_time)
            else:
                self.log_test("Analytics Performance", "WARN", 
                             f"性能问题: {'; '.join(performance_issues)}", response_time)
                             
        except Exception as e:
            response_time = time.time() - test_start
            self.log_test("Analytics Performance", "FAIL", 
                         f"性能测试异常: {str(e)}", response_time)

    def test_analytics_automation(self):
        """测试分析系统自动化功能"""
        test_start = time.time()
        try:
            import analytics_engine
            
            # 测试调度器启动
            engine = analytics_engine.AnalyticsEngine()
            
            # 检查调度器是否正常运行
            scheduler_running = hasattr(engine, 'scheduler') and engine.scheduler
            
            if scheduler_running:
                # 检查是否有定时任务
                jobs = engine.scheduler.get_jobs() if hasattr(engine.scheduler, 'get_jobs') else []
                job_count = len(jobs)
                
                response_time = time.time() - test_start
                
                if job_count > 0:
                    self.log_test("Analytics Automation", "PASS", 
                                 f"自动化系统正常 - 调度器运行中，{job_count}个定时任务", response_time)
                else:
                    self.log_test("Analytics Automation", "WARN", 
                                 "调度器运行但无定时任务", response_time)
            else:
                response_time = time.time() - test_start
                self.log_test("Analytics Automation", "WARN", 
                             "调度器未运行或未初始化", response_time)
                             
        except Exception as e:
            response_time = time.time() - test_start
            self.log_test("Analytics Automation", "FAIL", 
                         f"自动化测试异常: {str(e)}", response_time)

    def generate_comprehensive_report(self):
        """生成分析系统测试综合报告"""
        end_time = datetime.now()
        total_time = (end_time - self.start_time).total_seconds()
        
        passed = len([r for r in self.test_results if r["status"] == "PASS"])
        failed = len([r for r in self.test_results if r["status"] == "FAIL"])
        warned = len([r for r in self.test_results if r["status"] == "WARN"])
        total = len(self.test_results)
        
        print("\n" + "="*80)
        print("分析系统深度测试报告 (Analytics System Comprehensive Test Report)")
        print("="*80)
        print(f"测试开始时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"测试结束时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"总测试时间: {total_time:.2f}秒")
        print(f"测试项目: {total}")
        print(f"✅ 通过: {passed} | ❌ 失败: {failed} | ⚠️ 警告: {warned}")
        print(f"分析系统健康度: {((passed + warned*0.5)/total*100):.1f}%")
        
        # 分析系统状态评估
        if failed == 0 and warned <= 2:
            print("\n🎉 分析系统状态：优秀 - 所有核心分析功能正常")
            system_status = "优秀"
        elif failed <= 1 and warned <= 3:
            print("\n✅ 分析系统状态：良好 - 主要分析功能正常")
            system_status = "良好"
        elif failed <= 2:
            print("\n⚠️ 分析系统状态：一般 - 部分分析功能需要改进")
            system_status = "一般"
        else:
            print("\n❌ 分析系统状态：需要修复 - 多项分析功能存在问题")
            system_status = "需要修复"
        
        # 功能模块分析
        print(f"\n分析系统功能模块状态:")
        modules = {
            "数据库结构": "Analytics Database Structure",
            "数据收集": "Analytics Data Collection", 
            "技术指标": "Technical Indicators Calculation",
            "报告生成": "Report Generation",
            "API集成": "Analytics API Integration",
            "界面集成": "Analytics Widget Integration",
            "数据质量": "Data Quality and Accuracy",
            "系统性能": "Analytics Performance",
            "自动化": "Analytics Automation"
        }
        
        for module_name, test_name in modules.items():
            module_results = [r for r in self.test_results if r["test_name"] == test_name]
            if module_results:
                result = module_results[0]
                status_symbol = "✅" if result["status"] == "PASS" else "❌" if result["status"] == "FAIL" else "⚠️"
                print(f"  {status_symbol} {module_name}: {result['details']}")
        
        # 保存详细报告
        report_data = {
            "test_summary": {
                "start_time": self.start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "total_time": total_time,
                "total_tests": total,
                "passed": passed,
                "failed": failed,
                "warned": warned,
                "analytics_health_score": (passed + warned*0.5)/total*100,
                "system_status": system_status
            },
            "test_results": self.test_results,
            "analytics_recommendations": self.generate_analytics_recommendations()
        }
        
        with open("analytics_comprehensive_test_report.json", "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n📋 详细报告已保存: analytics_comprehensive_test_report.json")
        return system_status

    def generate_analytics_recommendations(self):
        """生成分析系统改进建议"""
        recommendations = []
        
        failed_tests = [r for r in self.test_results if r["status"] == "FAIL"]
        warned_tests = [r for r in self.test_results if r["status"] == "WARN"]
        
        if any("Database" in test["test_name"] for test in failed_tests):
            recommendations.append("检查分析数据库表结构和数据完整性")
        
        if any("Data Collection" in test["test_name"] for test in failed_tests):
            recommendations.append("验证数据收集流程和外部API连接")
        
        if any("Technical Indicators" in test["test_name"] for test in failed_tests):
            recommendations.append("检查技术指标计算算法和历史数据")
        
        if any("API Integration" in test["test_name"] for test in warned_tests):
            recommendations.append("考虑启动独立分析服务器以提供完整API支持")
        
        if any("Performance" in test["test_name"] for test in warned_tests):
            recommendations.append("优化分析算法性能，考虑数据缓存策略")
        
        if any("Automation" in test["test_name"] for test in warned_tests):
            recommendations.append("检查定时任务配置和调度器状态")
        
        return recommendations

    def run_comprehensive_analytics_test(self):
        """运行分析系统全面测试"""
        print("开始分析系统深度测试...")
        print("="*80)
        
        # 数据库和结构测试
        self.test_analytics_database_structure()
        
        # 核心功能测试
        self.test_analytics_data_collection()
        self.test_technical_indicators_calculation()
        self.test_report_generation()
        
        # 集成测试
        self.test_analytics_api_integration()
        self.test_analytics_widget_integration()
        
        # 质量和性能测试
        self.test_data_quality_and_accuracy()
        self.test_analytics_performance()
        self.test_analytics_automation()
        
        # 生成综合报告
        return self.generate_comprehensive_report()

if __name__ == "__main__":
    tester = AnalyticsSystemTester()
    system_status = tester.run_comprehensive_analytics_test()
    
    # 设置退出代码
    if system_status in ["优秀", "良好"]:
        sys.exit(0)
    elif system_status == "一般":
        sys.exit(1)
    else:
        sys.exit(2)