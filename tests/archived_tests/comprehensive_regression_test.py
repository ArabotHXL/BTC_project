#!/usr/bin/env python3
"""
全系统回归测试 (Comprehensive System Regression Test)
测试所有主要功能模块的完整性和性能
"""

import requests
import time
import json
import os
import psycopg2
from datetime import datetime
import sys

class SystemRegressionTest:
    def __init__(self):
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
        
    def test_database_connection(self):
        """测试数据库连接"""
        test_start = time.time()
        try:
            db_url = os.environ.get('DATABASE_URL')
            if not db_url:
                self.log_test("Database Connection", "FAIL", "DATABASE_URL not found")
                return
                
            conn = psycopg2.connect(db_url)
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            
            response_time = time.time() - test_start
            if result[0] == 1:
                self.log_test("Database Connection", "PASS", "连接正常", response_time)
            else:
                self.log_test("Database Connection", "FAIL", "查询结果异常")
        except Exception as e:
            response_time = time.time() - test_start
            self.log_test("Database Connection", "FAIL", f"连接失败: {str(e)}", response_time)

    def test_database_tables(self):
        """测试数据库表结构"""
        test_start = time.time()
        try:
            db_url = os.environ.get('DATABASE_URL')
            conn = psycopg2.connect(db_url)
            cursor = conn.cursor()
            
            # 检查主要表是否存在
            expected_tables = [
                'users', 'user_access', 'login_records', 'network_snapshots',
                'customers', 'contacts', 'leads', 'deals', 'activities',
                'mining_broker_deals', 'commission_records',
                'market_analytics', 'technical_indicators', 'analysis_reports', 'mining_metrics'
            ]
            
            cursor.execute("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
            existing_tables = [row[0] for row in cursor.fetchall()]
            
            missing_tables = [t for t in expected_tables if t not in existing_tables]
            
            cursor.close()
            conn.close()
            
            response_time = time.time() - test_start
            if not missing_tables:
                self.log_test("Database Tables", "PASS", f"所有14个表存在: {len(existing_tables)}个表", response_time)
            else:
                self.log_test("Database Tables", "WARN", f"缺少表: {missing_tables}", response_time)
                
        except Exception as e:
            response_time = time.time() - test_start
            self.log_test("Database Tables", "FAIL", f"表检查失败: {str(e)}", response_time)

    def test_web_server_status(self):
        """测试Web服务器状态"""
        test_start = time.time()
        try:
            response = requests.get(f"{self.base_url}/", timeout=10)
            response_time = time.time() - test_start
            
            if response.status_code == 200:
                self.log_test("Web Server", "PASS", f"服务器响应正常 (状态码: {response.status_code})", response_time)
            else:
                self.log_test("Web Server", "FAIL", f"状态码异常: {response.status_code}", response_time)
        except Exception as e:
            response_time = time.time() - test_start
            self.log_test("Web Server", "FAIL", f"服务器无响应: {str(e)}", response_time)

    def test_api_endpoints(self):
        """测试API端点"""
        endpoints = [
            ("/api/btc-price", "BTC价格API"),
            ("/api/network-stats", "网络统计API"),
            ("/api/miners", "矿机列表API"),
            ("/api/sha256-comparison", "SHA256对比API")
        ]
        
        for endpoint, name in endpoints:
            test_start = time.time()
            try:
                response = requests.get(f"{self.base_url}{endpoint}", timeout=10)
                response_time = time.time() - test_start
                
                if response.status_code == 200:
                    data = response.json()
                    if data:
                        self.log_test(f"API - {name}", "PASS", "数据返回正常", response_time)
                    else:
                        self.log_test(f"API - {name}", "WARN", "返回数据为空", response_time)
                else:
                    self.log_test(f"API - {name}", "FAIL", f"状态码: {response.status_code}", response_time)
            except Exception as e:
                response_time = time.time() - test_start
                self.log_test(f"API - {name}", "FAIL", f"请求失败: {str(e)}", response_time)

    def test_mining_calculation(self):
        """测试挖矿计算功能"""
        test_start = time.time()
        try:
            # 使用标准测试参数
            test_data = {
                "miner_model": "Antminer S21 XP",
                "miner_count": 1,
                "electricity_cost": 0.05,
                "use_real_time_data": True
            }
            
            response = requests.post(
                f"{self.base_url}/calculate",
                data=test_data,
                timeout=15
            )
            response_time = time.time() - test_start
            
            if response.status_code == 200:
                result = response.json()
                if "daily_revenue" in result and "monthly_profit" in result:
                    daily_revenue = result.get("daily_revenue", 0)
                    self.log_test("Mining Calculation", "PASS", f"计算成功，日收入: ${daily_revenue:.2f}", response_time)
                else:
                    self.log_test("Mining Calculation", "FAIL", "返回数据格式异常", response_time)
            else:
                self.log_test("Mining Calculation", "FAIL", f"计算失败，状态码: {response.status_code}", response_time)
        except Exception as e:
            response_time = time.time() - test_start
            self.log_test("Mining Calculation", "FAIL", f"计算请求异常: {str(e)}", response_time)

    def test_external_apis(self):
        """测试外部API集成"""
        # 测试CoinGecko API
        test_start = time.time()
        try:
            response = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd", timeout=10)
            response_time = time.time() - test_start
            if response.status_code == 200:
                data = response.json()
                btc_price = data.get("bitcoin", {}).get("usd")
                if btc_price:
                    self.log_test("External API - CoinGecko", "PASS", f"BTC价格获取成功: ${btc_price:,.2f}", response_time)
                else:
                    self.log_test("External API - CoinGecko", "FAIL", "价格数据格式异常", response_time)
            else:
                self.log_test("External API - CoinGecko", "FAIL", f"状态码: {response.status_code}", response_time)
        except Exception as e:
            response_time = time.time() - test_start
            self.log_test("External API - CoinGecko", "FAIL", f"请求失败: {str(e)}", response_time)

        # 测试Blockchain.info API
        test_start = time.time()
        try:
            response = requests.get("https://blockchain.info/q/getdifficulty", timeout=10)
            response_time = time.time() - test_start
            if response.status_code == 200:
                difficulty = float(response.text)
                self.log_test("External API - Blockchain.info", "PASS", f"网络难度获取成功: {difficulty:.2f}T", response_time)
            else:
                self.log_test("External API - Blockchain.info", "FAIL", f"状态码: {response.status_code}", response_time)
        except Exception as e:
            response_time = time.time() - test_start
            self.log_test("External API - Blockchain.info", "FAIL", f"请求失败: {str(e)}", response_time)

    def test_analytics_system(self):
        """测试分析系统"""
        test_start = time.time()
        try:
            # 检查分析数据表
            db_url = os.environ.get('DATABASE_URL')
            conn = psycopg2.connect(db_url)
            cursor = conn.cursor()
            
            # 检查市场数据
            cursor.execute("SELECT COUNT(*) FROM market_analytics")
            market_count = cursor.fetchone()[0]
            
            # 检查技术指标
            cursor.execute("SELECT COUNT(*) FROM technical_indicators")
            tech_count = cursor.fetchone()[0]
            
            cursor.close()
            conn.close()
            
            response_time = time.time() - test_start
            if market_count > 0 and tech_count > 0:
                self.log_test("Analytics System", "PASS", f"数据正常: {market_count}条市场数据, {tech_count}条技术指标", response_time)
            elif market_count > 0:
                self.log_test("Analytics System", "WARN", f"部分数据: {market_count}条市场数据, 技术指标为空", response_time)
            else:
                self.log_test("Analytics System", "WARN", "分析数据为空，可能刚启动", response_time)
                
        except Exception as e:
            response_time = time.time() - test_start
            self.log_test("Analytics System", "FAIL", f"分析系统检查失败: {str(e)}", response_time)

    def test_data_quality(self):
        """测试数据质量"""
        test_start = time.time()
        try:
            db_url = os.environ.get('DATABASE_URL')
            conn = psycopg2.connect(db_url)
            cursor = conn.cursor()
            
            # 检查网络快照数据
            cursor.execute("""
                SELECT COUNT(*), AVG(btc_price), AVG(network_hashrate) 
                FROM network_snapshots 
                WHERE recorded_at > NOW() - INTERVAL '24 hours'
            """)
            result = cursor.fetchone()
            count, avg_price, avg_hashrate = result
            
            cursor.close()
            conn.close()
            
            response_time = time.time() - test_start
            if count > 0:
                self.log_test("Data Quality", "PASS", 
                    f"24小时内{count}条记录, 平均价格: ${avg_price:.2f}, 平均算力: {avg_hashrate:.1f}EH/s", 
                    response_time)
            else:
                self.log_test("Data Quality", "WARN", "24小时内无新数据记录", response_time)
                
        except Exception as e:
            response_time = time.time() - test_start
            self.log_test("Data Quality", "FAIL", f"数据质量检查失败: {str(e)}", response_time)

    def test_performance_metrics(self):
        """测试性能指标"""
        test_start = time.time()
        
        # 测试主页加载时间
        page_start = time.time()
        try:
            response = requests.get(f"{self.base_url}/", timeout=10)
            page_load_time = time.time() - page_start
            
            if page_load_time < 2.0:
                self.log_test("Performance - Page Load", "PASS", f"主页加载时间: {page_load_time:.2f}s", page_load_time)
            elif page_load_time < 5.0:
                self.log_test("Performance - Page Load", "WARN", f"主页加载较慢: {page_load_time:.2f}s", page_load_time)
            else:
                self.log_test("Performance - Page Load", "FAIL", f"主页加载过慢: {page_load_time:.2f}s", page_load_time)
        except Exception as e:
            page_load_time = time.time() - page_start
            self.log_test("Performance - Page Load", "FAIL", f"页面加载失败: {str(e)}", page_load_time)

        # 测试API响应时间
        api_start = time.time()
        try:
            response = requests.get(f"{self.base_url}/api/btc-price", timeout=10)
            api_response_time = time.time() - api_start
            
            if api_response_time < 1.0:
                self.log_test("Performance - API", "PASS", f"API响应时间: {api_response_time:.2f}s", api_response_time)
            elif api_response_time < 3.0:
                self.log_test("Performance - API", "WARN", f"API响应较慢: {api_response_time:.2f}s", api_response_time)
            else:
                self.log_test("Performance - API", "FAIL", f"API响应过慢: {api_response_time:.2f}s", api_response_time)
        except Exception as e:
            api_response_time = time.time() - api_start
            self.log_test("Performance - API", "FAIL", f"API请求失败: {str(e)}", api_response_time)

    def generate_report(self):
        """生成测试报告"""
        end_time = datetime.now()
        total_time = (end_time - self.start_time).total_seconds()
        
        passed = len([r for r in self.test_results if r["status"] == "PASS"])
        failed = len([r for r in self.test_results if r["status"] == "FAIL"])
        warned = len([r for r in self.test_results if r["status"] == "WARN"])
        total = len(self.test_results)
        
        print("\n" + "="*60)
        print("全系统回归测试报告 (System Regression Test Report)")
        print("="*60)
        print(f"测试开始时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"测试结束时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"总测试时间: {total_time:.2f}秒")
        print(f"总测试数量: {total}")
        print(f"通过: {passed} | 失败: {failed} | 警告: {warned}")
        print(f"成功率: {(passed/total*100):.1f}%")
        
        if failed == 0:
            print("\n🎉 所有核心功能测试通过！系统运行正常。")
        elif failed < 3:
            print(f"\n⚠️ 发现{failed}个问题，但核心功能正常。")
        else:
            print(f"\n❌ 发现{failed}个严重问题，需要修复。")
        
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
                "success_rate": passed/total*100
            },
            "test_results": self.test_results
        }
        
        with open("regression_test_report.json", "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n详细报告已保存到: regression_test_report.json")

    def run_all_tests(self):
        """运行所有测试"""
        print("开始全系统回归测试...")
        print("="*60)
        
        # 核心系统测试
        self.test_database_connection()
        self.test_database_tables()
        self.test_web_server_status()
        
        # API功能测试
        self.test_api_endpoints()
        self.test_mining_calculation()
        self.test_external_apis()
        
        # 高级功能测试
        self.test_analytics_system()
        self.test_data_quality()
        
        # 性能测试
        self.test_performance_metrics()
        
        # 生成报告
        self.generate_report()

if __name__ == "__main__":
    tester = SystemRegressionTest()
    tester.run_all_tests()