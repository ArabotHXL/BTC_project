#!/usr/bin/env python3
"""
分析系统聚焦测试 (Analytics System Focused Test)
专注测试分析系统核心功能和数据完整性
"""

import os
import psycopg2
import requests
import json
import time
from datetime import datetime, timedelta

class AnalyticsFocusedTester:
    def __init__(self):
        self.db_url = os.environ.get('DATABASE_URL')
        self.base_url = "http://localhost:5000"
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

    def test_analytics_database_integrity(self):
        """测试分析数据库完整性"""
        test_start = time.time()
        try:
            conn = psycopg2.connect(self.db_url)
            cursor = conn.cursor()
            
            # 检查表结构和数据
            tables_info = {}
            analytics_tables = ['market_analytics', 'technical_indicators', 'analysis_reports', 'mining_metrics']
            
            for table in analytics_tables:
                # 检查表是否存在
                cursor.execute(f"""
                    SELECT COUNT(*) FROM information_schema.tables 
                    WHERE table_name = '{table}'
                """)
                exists = cursor.fetchone()[0] > 0
                
                if exists:
                    # 获取记录数
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    
                    # 获取最新记录时间
                    cursor.execute(f"""
                        SELECT MAX(recorded_at) FROM {table} 
                        WHERE recorded_at IS NOT NULL
                    """)
                    latest = cursor.fetchone()[0]
                    
                    tables_info[table] = {
                        'exists': True,
                        'count': count,
                        'latest': latest.strftime('%Y-%m-%d %H:%M') if latest else None
                    }
                else:
                    tables_info[table] = {'exists': False}
            
            cursor.close()
            conn.close()
            
            response_time = time.time() - test_start
            
            # 评估结果
            existing_tables = [t for t, info in tables_info.items() if info['exists']]
            total_records = sum(info.get('count', 0) for info in tables_info.values() if info['exists'])
            
            if len(existing_tables) >= 3 and total_records > 0:
                details = f"分析表完整性良好 - {len(existing_tables)}/4个表存在，共{total_records}条记录"
                for table, info in tables_info.items():
                    if info['exists']:
                        details += f"; {table}: {info['count']}条"
                self.log_test("Analytics Database Integrity", "PASS", details, response_time)
            else:
                self.log_test("Analytics Database Integrity", "FAIL", 
                             f"数据库不完整 - 仅{len(existing_tables)}个表存在", response_time)
                             
        except Exception as e:
            response_time = time.time() - test_start
            self.log_test("Analytics Database Integrity", "FAIL", 
                         f"数据库测试异常: {str(e)}", response_time)

    def test_data_collection_functionality(self):
        """测试数据收集功能"""
        test_start = time.time()
        try:
            # 直接导入并测试分析引擎
            import analytics_engine
            
            # 创建引擎实例并收集数据
            engine = analytics_engine.AnalyticsEngine()
            engine.collect_and_analyze()
            
            # 验证数据是否成功收集
            conn = psycopg2.connect(self.db_url)
            cursor = conn.cursor()
            
            # 检查最新数据
            cursor.execute("""
                SELECT recorded_at, btc_price, network_hashrate 
                FROM market_analytics 
                ORDER BY recorded_at DESC LIMIT 1
            """)
            latest_market = cursor.fetchone()
            
            cursor.execute("""
                SELECT recorded_at, rsi_14, sma_20 
                FROM technical_indicators 
                ORDER BY recorded_at DESC LIMIT 1
            """)
            latest_tech = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            response_time = time.time() - test_start
            
            if latest_market and latest_tech:
                # 检查数据时效性（5分钟内）
                time_diff = datetime.now() - latest_market[0]
                if time_diff.total_seconds() < 300:
                    price = latest_market[1]
                    hashrate = latest_market[2]
                    rsi = latest_tech[1] if latest_tech[1] else "N/A"
                    self.log_test("Data Collection Functionality", "PASS", 
                                 f"数据收集正常 - BTC: ${price:,.0f}, 算力: {hashrate:.1f}EH/s, RSI: {rsi}", 
                                 response_time)
                else:
                    self.log_test("Data Collection Functionality", "WARN", 
                                 f"数据收集成功但时效性差 - 最新数据: {time_diff.total_seconds():.0f}秒前", 
                                 response_time)
            else:
                self.log_test("Data Collection Functionality", "FAIL", 
                             "数据收集失败 - 未找到有效数据", response_time)
                             
        except Exception as e:
            response_time = time.time() - test_start
            self.log_test("Data Collection Functionality", "FAIL", 
                         f"数据收集测试失败: {str(e)}", response_time)

    def test_technical_analysis_accuracy(self):
        """测试技术分析准确性"""
        test_start = time.time()
        try:
            conn = psycopg2.connect(self.db_url)
            cursor = conn.cursor()
            
            # 获取最新技术指标
            cursor.execute("""
                SELECT rsi_14, sma_20, sma_50, ema_12, ema_26, macd,
                       bollinger_upper, bollinger_lower, volatility_30d
                FROM technical_indicators 
                ORDER BY recorded_at DESC LIMIT 1
            """)
            indicators = cursor.fetchone()
            
            # 获取最新价格用于验证
            cursor.execute("""
                SELECT btc_price FROM market_analytics 
                ORDER BY recorded_at DESC LIMIT 1
            """)
            current_price = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            response_time = time.time() - test_start
            
            if indicators and current_price:
                # 验证指标合理性
                rsi, sma20, sma50, ema12, ema26, macd, bb_upper, bb_lower, volatility = indicators
                price = current_price[0]
                
                issues = []
                valid_indicators = 0
                
                # RSI范围检查
                if rsi is not None:
                    if 0 <= rsi <= 100:
                        valid_indicators += 1
                    else:
                        issues.append(f"RSI异常({rsi:.1f})")
                
                # 移动平均线逻辑检查
                if sma20 and sma50:
                    if abs(sma20 - price) / price < 0.3:  # 20日均线不应偏离价格过远
                        valid_indicators += 1
                    else:
                        issues.append("SMA20偏离过大")
                
                # 布林带检查
                if bb_upper and bb_lower and bb_upper > bb_lower:
                    if bb_lower < price < bb_upper * 1.1:  # 价格应在合理范围内
                        valid_indicators += 1
                    else:
                        issues.append("价格超出布林带合理范围")
                
                if valid_indicators >= 2 and not issues:
                    self.log_test("Technical Analysis Accuracy", "PASS", 
                                 f"技术分析准确 - RSI: {rsi:.1f}, SMA20: ${sma20:,.0f}, 有效指标: {valid_indicators}", 
                                 response_time)
                elif valid_indicators >= 1:
                    self.log_test("Technical Analysis Accuracy", "WARN", 
                                 f"技术分析部分准确 - 有效指标: {valid_indicators}, 问题: {'; '.join(issues)}", 
                                 response_time)
                else:
                    self.log_test("Technical Analysis Accuracy", "FAIL", 
                                 f"技术分析不准确 - 问题: {'; '.join(issues)}", response_time)
            else:
                self.log_test("Technical Analysis Accuracy", "FAIL", 
                             "无技术指标数据可验证", response_time)
                             
        except Exception as e:
            response_time = time.time() - test_start
            self.log_test("Technical Analysis Accuracy", "FAIL", 
                         f"技术分析测试异常: {str(e)}", response_time)

    def test_analytics_integration_status(self):
        """测试分析系统集成状态"""
        test_start = time.time()
        
        # 使用会话登录
        session = requests.Session()
        try:
            # 登录获取权限
            login_data = {'email': 'hxl2022hao@gmail.com'}
            session.post(f"{self.base_url}/login", data=login_data)
            
            # 检查主应用中的分析功能
            main_page = session.get(f"{self.base_url}/")
            
            # 检查分析页面是否可访问
            analytics_page = session.get(f"{self.base_url}/analytics")
            
            # 测试分析API端点
            api_results = {}
            api_endpoints = [
                "/api/analytics/market-data",
                "/api/analytics/latest-report",
                "/api/analytics/technical-indicators"
            ]
            
            for endpoint in api_endpoints:
                try:
                    response = session.get(f"{self.base_url}{endpoint}", timeout=5)
                    api_results[endpoint] = response.status_code
                except:
                    api_results[endpoint] = "timeout"
            
            response_time = time.time() - test_start
            
            # 评估集成状态
            main_ok = main_page.status_code == 200
            analytics_ok = analytics_page.status_code == 200
            working_apis = len([k for k, v in api_results.items() if v == 200])
            
            if main_ok and analytics_ok and working_apis >= 1:
                self.log_test("Analytics Integration Status", "PASS", 
                             f"分析系统集成正常 - 主页: 正常, 分析页: 正常, API: {working_apis}/3可用", 
                             response_time)
            elif main_ok and working_apis >= 1:
                self.log_test("Analytics Integration Status", "WARN", 
                             f"分析系统部分集成 - API: {working_apis}/3可用", response_time)
            else:
                self.log_test("Analytics Integration Status", "FAIL", 
                             f"分析系统集成问题 - API状态: {api_results}", response_time)
                             
        except Exception as e:
            response_time = time.time() - test_start
            self.log_test("Analytics Integration Status", "FAIL", 
                         f"集成测试异常: {str(e)}", response_time)

    def test_data_quality_validation(self):
        """测试数据质量验证"""
        test_start = time.time()
        try:
            conn = psycopg2.connect(self.db_url)
            cursor = conn.cursor()
            
            # 数据质量检查
            quality_checks = {}
            
            # 1. 检查价格数据合理性
            cursor.execute("""
                SELECT COUNT(*), AVG(btc_price), MIN(btc_price), MAX(btc_price)
                FROM market_analytics 
                WHERE recorded_at > NOW() - INTERVAL '24 hours'
                AND btc_price BETWEEN 50000 AND 200000
            """)
            price_stats = cursor.fetchone()
            quality_checks['price_valid'] = price_stats[0] if price_stats else 0
            
            # 2. 检查算力数据合理性
            cursor.execute("""
                SELECT COUNT(*), AVG(network_hashrate)
                FROM market_analytics 
                WHERE recorded_at > NOW() - INTERVAL '24 hours'
                AND network_hashrate BETWEEN 400 AND 1500
            """)
            hashrate_stats = cursor.fetchone()
            quality_checks['hashrate_valid'] = hashrate_stats[0] if hashrate_stats else 0
            
            # 3. 检查数据完整性
            cursor.execute("""
                SELECT COUNT(*) FROM market_analytics 
                WHERE recorded_at > NOW() - INTERVAL '24 hours'
                AND (btc_price IS NULL OR network_hashrate IS NULL)
            """)
            incomplete_records = cursor.fetchone()[0]
            quality_checks['incomplete'] = incomplete_records
            
            # 4. 检查数据更新频率
            cursor.execute("""
                SELECT COUNT(DISTINCT DATE_TRUNC('hour', recorded_at))
                FROM market_analytics 
                WHERE recorded_at > NOW() - INTERVAL '24 hours'
            """)
            update_frequency = cursor.fetchone()[0]
            quality_checks['update_hours'] = update_frequency
            
            cursor.close()
            conn.close()
            
            response_time = time.time() - test_start
            
            # 评估数据质量
            issues = []
            if quality_checks['price_valid'] == 0:
                issues.append("无有效价格数据")
            if quality_checks['hashrate_valid'] == 0:
                issues.append("无有效算力数据")
            if quality_checks['incomplete'] > 0:
                issues.append(f"{quality_checks['incomplete']}条不完整记录")
            if quality_checks['update_hours'] < 12:
                issues.append("更新频率低")
            
            if not issues:
                avg_price = price_stats[1] if price_stats[1] else 0
                avg_hashrate = hashrate_stats[1] if hashrate_stats[1] else 0
                self.log_test("Data Quality Validation", "PASS", 
                             f"数据质量优秀 - 24h有效记录: {quality_checks['price_valid']}条, 平均价格: ${avg_price:,.0f}, 平均算力: {avg_hashrate:.1f}EH/s", 
                             response_time)
            elif len(issues) <= 1:
                self.log_test("Data Quality Validation", "WARN", 
                             f"数据质量良好但有小问题: {'; '.join(issues)}", response_time)
            else:
                self.log_test("Data Quality Validation", "FAIL", 
                             f"数据质量问题: {'; '.join(issues)}", response_time)
                             
        except Exception as e:
            response_time = time.time() - test_start
            self.log_test("Data Quality Validation", "FAIL", 
                         f"数据质量验证异常: {str(e)}", response_time)

    def test_analytics_performance_metrics(self):
        """测试分析系统性能指标"""
        test_start = time.time()
        try:
            import analytics_engine
            
            # 测试数据收集性能
            collection_start = time.time()
            engine = analytics_engine.AnalyticsEngine()
            engine.collect_and_analyze()
            collection_time = time.time() - collection_start
            
            # 测试技术分析性能
            db_manager = analytics_engine.DatabaseManager()
            db_manager.connect()
            analyzer = analytics_engine.TechnicalAnalyzer(db_manager)
            
            analysis_start = time.time()
            indicators = analyzer.calculate_technical_indicators()
            analysis_time = time.time() - analysis_start
            
            response_time = time.time() - test_start
            
            # 性能评估
            performance_score = 0
            performance_details = []
            
            if collection_time < 5:
                performance_score += 40
                performance_details.append(f"数据收集快速({collection_time:.1f}s)")
            elif collection_time < 10:
                performance_score += 20
                performance_details.append(f"数据收集正常({collection_time:.1f}s)")
            else:
                performance_details.append(f"数据收集较慢({collection_time:.1f}s)")
            
            if analysis_time < 2:
                performance_score += 40
                performance_details.append(f"技术分析快速({analysis_time:.1f}s)")
            elif analysis_time < 5:
                performance_score += 20
                performance_details.append(f"技术分析正常({analysis_time:.1f}s)")
            else:
                performance_details.append(f"技术分析较慢({analysis_time:.1f}s)")
            
            if indicators and len([k for k, v in indicators.items() if v is not None]) >= 3:
                performance_score += 20
                performance_details.append("指标计算完整")
            
            if performance_score >= 80:
                self.log_test("Analytics Performance Metrics", "PASS", 
                             f"性能优秀(评分: {performance_score}/100) - {'; '.join(performance_details)}", 
                             response_time)
            elif performance_score >= 60:
                self.log_test("Analytics Performance Metrics", "WARN", 
                             f"性能良好(评分: {performance_score}/100) - {'; '.join(performance_details)}", 
                             response_time)
            else:
                self.log_test("Analytics Performance Metrics", "FAIL", 
                             f"性能需要改进(评分: {performance_score}/100) - {'; '.join(performance_details)}", 
                             response_time)
                             
        except Exception as e:
            response_time = time.time() - test_start
            self.log_test("Analytics Performance Metrics", "FAIL", 
                         f"性能测试异常: {str(e)}", response_time)

    def generate_analytics_summary(self):
        """生成分析系统测试总结"""
        end_time = datetime.now()
        total_time = (end_time - self.start_time).total_seconds()
        
        passed = len([r for r in self.test_results if r["status"] == "PASS"])
        failed = len([r for r in self.test_results if r["status"] == "FAIL"])
        warned = len([r for r in self.test_results if r["status"] == "WARN"])
        total = len(self.test_results)
        
        print("\n" + "="*70)
        print("分析系统聚焦测试总结 (Analytics System Focused Test Summary)")
        print("="*70)
        print(f"测试执行时间: {self.start_time.strftime('%H:%M:%S')} - {end_time.strftime('%H:%M:%S')} ({total_time:.1f}s)")
        print(f"测试项目: {total}")
        print(f"✅ 通过: {passed} | ❌ 失败: {failed} | ⚠️ 警告: {warned}")
        
        analytics_health = ((passed + warned * 0.5) / total * 100) if total > 0 else 0
        print(f"分析系统健康度: {analytics_health:.1f}%")
        
        # 系统状态评定
        if failed == 0 and warned <= 1:
            status = "优秀"
            print(f"\n🎉 分析系统状态: {status} - 所有核心分析功能运行正常")
        elif failed <= 1 and warned <= 2:
            status = "良好"
            print(f"\n✅ 分析系统状态: {status} - 主要分析功能正常运行")
        elif failed <= 2:
            status = "一般"
            print(f"\n⚠️ 分析系统状态: {status} - 部分功能需要改进")
        else:
            status = "需要修复"
            print(f"\n❌ 分析系统状态: {status} - 多项功能存在问题")
        
        # 关键发现
        print(f"\n关键测试结果:")
        for result in self.test_results:
            status_symbol = "✅" if result["status"] == "PASS" else "❌" if result["status"] == "FAIL" else "⚠️"
            print(f"  {status_symbol} {result['test_name']}: {result['details']}")
        
        # 保存结果
        summary_data = {
            "test_summary": {
                "start_time": self.start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "total_time": total_time,
                "total_tests": total,
                "passed": passed,
                "failed": failed,
                "warned": warned,
                "analytics_health": analytics_health,
                "system_status": status
            },
            "test_results": self.test_results
        }
        
        with open("analytics_focused_test_results.json", "w", encoding="utf-8") as f:
            json.dump(summary_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n📋 详细结果已保存: analytics_focused_test_results.json")
        return status

    def run_focused_test_suite(self):
        """运行聚焦测试套件"""
        print("开始分析系统聚焦测试...")
        print("="*70)
        
        # 核心功能测试
        self.test_analytics_database_integrity()
        self.test_data_collection_functionality()
        self.test_technical_analysis_accuracy()
        self.test_analytics_integration_status()
        self.test_data_quality_validation()
        self.test_analytics_performance_metrics()
        
        # 生成总结
        return self.generate_analytics_summary()

if __name__ == "__main__":
    tester = AnalyticsFocusedTester()
    system_status = tester.run_focused_test_suite()