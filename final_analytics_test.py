#!/usr/bin/env python3
"""
最终分析系统测试 (Final Analytics System Test)
验证分析系统所有功能模块的综合运行状态
"""

import os
import psycopg2
import requests
import json
import time
from datetime import datetime

class FinalAnalyticsTest:
    def __init__(self):
        self.db_url = os.environ.get('DATABASE_URL')
        self.base_url = "http://localhost:5000"
        self.results = []
        
    def log_result(self, test, status, details, time_taken=None):
        """记录测试结果"""
        result = {
            "test": test,
            "status": status,
            "details": details,
            "time": time_taken,
            "timestamp": datetime.now().isoformat()
        }
        self.results.append(result)
        symbol = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        time_info = f" ({time_taken:.2f}s)" if time_taken else ""
        print(f"{symbol} {test}{time_info}: {details}")

    def test_database_structure(self):
        """测试数据库结构完整性"""
        start_time = time.time()
        try:
            conn = psycopg2.connect(self.db_url)
            cursor = conn.cursor()
            
            # 检查分析相关表
            cursor.execute("""
                SELECT table_name, column_count 
                FROM (
                    SELECT table_name, COUNT(*) as column_count
                    FROM information_schema.columns 
                    WHERE table_name IN ('market_analytics', 'technical_indicators', 'analysis_reports', 'mining_metrics')
                    GROUP BY table_name
                ) t
                ORDER BY table_name
            """)
            tables = cursor.fetchall()
            
            # 检查记录数量
            record_counts = {}
            for table_name, _ in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                record_counts[table_name] = cursor.fetchone()[0]
            
            cursor.close()
            conn.close()
            
            execution_time = time.time() - start_time
            
            if len(tables) >= 4:
                total_records = sum(record_counts.values())
                details = f"数据库结构完整 - {len(tables)}个表，共{total_records}条记录"
                self.log_result("Database Structure", "PASS", details, execution_time)
                return True
            else:
                self.log_result("Database Structure", "FAIL", f"数据库表不完整，仅找到{len(tables)}个表", execution_time)
                return False
                
        except Exception as e:
            execution_time = time.time() - start_time
            self.log_result("Database Structure", "FAIL", f"数据库检查异常: {str(e)}", execution_time)
            return False

    def test_data_collection(self):
        """测试数据收集功能"""
        start_time = time.time()
        try:
            import analytics_engine
            
            # 执行数据收集
            engine = analytics_engine.AnalyticsEngine()
            engine.collect_and_analyze()
            
            # 验证收集结果
            conn = psycopg2.connect(self.db_url)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT btc_price, network_hashrate, recorded_at 
                FROM market_analytics 
                ORDER BY recorded_at DESC LIMIT 1
            """)
            market_data = cursor.fetchone()
            
            cursor.execute("""
                SELECT rsi_14, sma_20, recorded_at 
                FROM technical_indicators 
                ORDER BY recorded_at DESC LIMIT 1
            """)
            tech_data = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            execution_time = time.time() - start_time
            
            if market_data and tech_data:
                price = market_data[0]
                hashrate = market_data[1]
                details = f"数据收集成功 - BTC: ${price:,.0f}, 算力: {hashrate:.1f}EH/s"
                
                # 检查数据时效性
                time_diff = datetime.now() - market_data[2]
                if time_diff.total_seconds() < 300:  # 5分钟内
                    self.log_result("Data Collection", "PASS", details, execution_time)
                    return True
                else:
                    self.log_result("Data Collection", "WARN", f"{details} (数据时效性: {time_diff.total_seconds():.0f}秒)", execution_time)
                    return True
            else:
                self.log_result("Data Collection", "FAIL", "数据收集失败，未找到有效数据", execution_time)
                return False
                
        except Exception as e:
            execution_time = time.time() - start_time
            self.log_result("Data Collection", "FAIL", f"数据收集异常: {str(e)}", execution_time)
            return False

    def test_api_integration(self):
        """测试API集成功能"""
        start_time = time.time()
        
        # 创建会话并登录
        session = requests.Session()
        try:
            # 登录
            login_data = {'email': 'hxl2022hao@gmail.com'}
            session.post(f"{self.base_url}/login", data=login_data)
            
            # 测试分析API端点
            api_tests = [
                ("/api/analytics/market-data", "市场数据"),
                ("/api/analytics/latest-report", "分析报告"),
                ("/api/analytics/technical-indicators", "技术指标")
            ]
            
            working_apis = 0
            api_details = []
            
            for endpoint, name in api_tests:
                try:
                    response = session.get(f"{self.base_url}{endpoint}", timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        if data and not data.get('error'):
                            working_apis += 1
                            api_details.append(f"{name}: 正常")
                        else:
                            api_details.append(f"{name}: 无数据")
                    else:
                        api_details.append(f"{name}: HTTP{response.status_code}")
                except Exception as e:
                    api_details.append(f"{name}: 异常")
            
            execution_time = time.time() - start_time
            
            if working_apis >= 2:
                details = f"API集成良好 - {working_apis}/3个端点正常: {'; '.join(api_details)}"
                self.log_result("API Integration", "PASS", details, execution_time)
                return True
            elif working_apis >= 1:
                details = f"API部分可用 - {working_apis}/3个端点: {'; '.join(api_details)}"
                self.log_result("API Integration", "WARN", details, execution_time)
                return True
            else:
                details = f"API集成失败 - 无可用端点: {'; '.join(api_details)}"
                self.log_result("API Integration", "FAIL", details, execution_time)
                return False
                
        except Exception as e:
            execution_time = time.time() - start_time
            self.log_result("API Integration", "FAIL", f"API测试异常: {str(e)}", execution_time)
            return False

    def test_technical_analysis(self):
        """测试技术分析功能"""
        start_time = time.time()
        try:
            import analytics_engine
            
            # 创建技术分析器
            db_manager = analytics_engine.DatabaseManager()
            db_manager.connect()
            analyzer = analytics_engine.TechnicalAnalyzer(db_manager)
            
            # 计算技术指标
            indicators = analyzer.calculate_technical_indicators()
            
            execution_time = time.time() - start_time
            
            if indicators:
                valid_indicators = [k for k, v in indicators.items() if v is not None]
                if len(valid_indicators) >= 3:
                    rsi = indicators.get('rsi_14', 'N/A')
                    sma20 = indicators.get('sma_20', 'N/A')
                    details = f"技术分析正常 - RSI: {rsi}, SMA20: {sma20}, 有效指标: {len(valid_indicators)}"
                    self.log_result("Technical Analysis", "PASS", details, execution_time)
                    return True
                else:
                    details = f"技术分析部分有效 - 有效指标: {len(valid_indicators)}/9"
                    self.log_result("Technical Analysis", "WARN", details, execution_time)
                    return True
            else:
                self.log_result("Technical Analysis", "FAIL", "技术分析失败，无有效指标", execution_time)
                return False
                
        except Exception as e:
            execution_time = time.time() - start_time
            self.log_result("Technical Analysis", "FAIL", f"技术分析异常: {str(e)}", execution_time)
            return False

    def test_report_generation(self):
        """测试报告生成功能"""
        start_time = time.time()
        try:
            import analytics_engine
            
            # 创建报告生成器
            db_manager = analytics_engine.DatabaseManager()
            db_manager.connect()
            generator = analytics_engine.ReportGenerator(db_manager)
            
            # 生成报告
            report = generator.generate_daily_report()
            
            execution_time = time.time() - start_time
            
            if report and isinstance(report, dict):
                title = report.get('title', '')
                summary = report.get('summary', '')
                recommendations = report.get('recommendations', [])
                
                if title and summary and recommendations:
                    details = f"报告生成成功 - 标题: '{title}', 摘要: {len(summary)}字符, 建议: {len(recommendations)}条"
                    self.log_result("Report Generation", "PASS", details, execution_time)
                    return True
                else:
                    details = "报告生成但内容不完整"
                    self.log_result("Report Generation", "WARN", details, execution_time)
                    return True
            else:
                self.log_result("Report Generation", "FAIL", "报告生成失败", execution_time)
                return False
                
        except Exception as e:
            execution_time = time.time() - start_time
            self.log_result("Report Generation", "FAIL", f"报告生成异常: {str(e)}", execution_time)
            return False

    def test_performance(self):
        """测试系统性能"""
        start_time = time.time()
        try:
            import analytics_engine
            
            # 性能测试：数据收集
            collection_start = time.time()
            engine = analytics_engine.AnalyticsEngine()
            engine.collect_and_analyze()
            collection_time = time.time() - collection_start
            
            # 性能测试：技术分析
            analysis_start = time.time()
            db_manager = analytics_engine.DatabaseManager()
            db_manager.connect()
            analyzer = analytics_engine.TechnicalAnalyzer(db_manager)
            analyzer.calculate_technical_indicators()
            analysis_time = time.time() - analysis_start
            
            execution_time = time.time() - start_time
            
            # 性能评估
            performance_score = 0
            issues = []
            
            if collection_time < 5:
                performance_score += 50
            elif collection_time < 10:
                performance_score += 30
            else:
                issues.append(f"数据收集慢({collection_time:.1f}s)")
            
            if analysis_time < 3:
                performance_score += 50
            elif analysis_time < 6:
                performance_score += 30
            else:
                issues.append(f"技术分析慢({analysis_time:.1f}s)")
            
            if performance_score >= 80:
                details = f"性能优秀 - 收集: {collection_time:.1f}s, 分析: {analysis_time:.1f}s"
                self.log_result("Performance", "PASS", details, execution_time)
                return True
            elif performance_score >= 60:
                details = f"性能良好 - 收集: {collection_time:.1f}s, 分析: {analysis_time:.1f}s"
                self.log_result("Performance", "WARN", details, execution_time)
                return True
            else:
                details = f"性能需改进 - 问题: {'; '.join(issues)}"
                self.log_result("Performance", "FAIL", details, execution_time)
                return False
                
        except Exception as e:
            execution_time = time.time() - start_time
            self.log_result("Performance", "FAIL", f"性能测试异常: {str(e)}", execution_time)
            return False

    def generate_final_report(self):
        """生成最终测试报告"""
        print("\n" + "="*70)
        print("分析系统最终测试报告 (Final Analytics System Test Report)")
        print("="*70)
        
        passed = len([r for r in self.results if r["status"] == "PASS"])
        warned = len([r for r in self.results if r["status"] == "WARN"])
        failed = len([r for r in self.results if r["status"] == "FAIL"])
        total = len(self.results)
        
        print(f"测试完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"测试项目: {total}")
        print(f"✅ 通过: {passed} | ⚠️ 警告: {warned} | ❌ 失败: {failed}")
        
        # 计算健康度
        health_score = ((passed + warned * 0.5) / total * 100) if total > 0 else 0
        print(f"分析系统健康度: {health_score:.1f}%")
        
        # 系统状态评定
        if failed == 0 and warned <= 1:
            status = "优秀"
            print(f"\n🎉 分析系统状态: {status}")
            print("所有核心分析功能运行正常，系统可投入生产使用")
        elif failed <= 1 and warned <= 2:
            status = "良好"
            print(f"\n✅ 分析系统状态: {status}")
            print("主要分析功能正常，可正常使用")
        elif failed <= 2:
            status = "一般"
            print(f"\n⚠️ 分析系统状态: {status}")
            print("部分功能需要改进，建议修复后使用")
        else:
            status = "需要修复"
            print(f"\n❌ 分析系统状态: {status}")
            print("多项功能存在问题，需要修复")
        
        print(f"\n详细测试结果:")
        for result in self.results:
            symbol = "✅" if result["status"] == "PASS" else "⚠️" if result["status"] == "WARN" else "❌"
            time_info = f" ({result['time']:.2f}s)" if result['time'] else ""
            print(f"  {symbol} {result['test']}{time_info}: {result['details']}")
        
        # 保存报告
        report_data = {
            "test_time": datetime.now().isoformat(),
            "summary": {
                "total_tests": total,
                "passed": passed,
                "warned": warned,
                "failed": failed,
                "health_score": health_score,
                "system_status": status
            },
            "detailed_results": self.results
        }
        
        with open("final_analytics_test_report.json", "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n📋 完整报告已保存: final_analytics_test_report.json")
        return status, health_score

    def run_comprehensive_test(self):
        """运行全面测试"""
        print("开始分析系统最终测试...")
        print("="*70)
        
        # 执行所有测试
        tests = [
            self.test_database_structure,
            self.test_data_collection,
            self.test_api_integration,
            self.test_technical_analysis,
            self.test_report_generation,
            self.test_performance
        ]
        
        success_count = 0
        for test in tests:
            if test():
                success_count += 1
        
        # 生成最终报告
        status, health_score = self.generate_final_report()
        
        return status, health_score, success_count, len(tests)

if __name__ == "__main__":
    tester = FinalAnalyticsTest()
    status, health_score, passed, total = tester.run_comprehensive_test()
    
    # 设置退出代码
    if status in ["优秀", "良好"]:
        exit(0)
    elif status == "一般":
        exit(1)
    else:
        exit(2)