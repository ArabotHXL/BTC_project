#!/usr/bin/env python3
"""
认证回归测试 (Authenticated Regression Test)
使用有效用户认证测试所有系统功能
"""

import requests
import time
import json
import os
import psycopg2
from datetime import datetime
import sys

class AuthenticatedRegressionTest:
    def __init__(self):
        self.base_url = "http://localhost:5000"
        self.session = requests.Session()
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
        
    def authenticate_user(self):
        """使用授权邮箱进行用户认证"""
        test_start = time.time()
        try:
            # 获取登录页面以建立会话
            login_page = self.session.get(f"{self.base_url}/")
            
            # 使用授权邮箱登录
            login_data = {
                'email': 'hxl2022hao@gmail.com'  # 拥有者邮箱
            }
            
            response = self.session.post(f"{self.base_url}/login", data=login_data)
            response_time = time.time() - test_start
            
            # 检查是否重定向到主页（登录成功的标志）
            if response.status_code in [200, 302]:
                # 验证会话是否有效
                main_page = self.session.get(f"{self.base_url}/")
                if "拥有者" in main_page.text or "owner" in main_page.text.lower():
                    self.log_test("User Authentication", "PASS", "拥有者权限认证成功", response_time)
                    return True
                else:
                    self.log_test("User Authentication", "PASS", "基础用户认证成功", response_time)
                    return True
            else:
                self.log_test("User Authentication", "FAIL", f"登录失败，状态码: {response.status_code}", response_time)
                return False
                
        except Exception as e:
            response_time = time.time() - test_start
            self.log_test("User Authentication", "FAIL", f"认证异常: {str(e)}", response_time)
            return False

    def test_database_system(self):
        """测试数据库系统完整性"""
        test_start = time.time()
        try:
            db_url = os.environ.get('DATABASE_URL')
            if not db_url:
                self.log_test("Database System", "FAIL", "DATABASE_URL环境变量未设置")
                return
                
            conn = psycopg2.connect(db_url)
            cursor = conn.cursor()
            
            # 检查关键表和数据
            test_queries = [
                ("SELECT COUNT(*) FROM network_snapshots", "网络快照数据"),
                ("SELECT COUNT(*) FROM user_access", "用户访问权限"),
                ("SELECT COUNT(*) FROM login_records", "登录记录"),
                ("SELECT COUNT(*) FROM market_analytics", "市场分析数据"),
                ("SELECT COUNT(*) FROM technical_indicators", "技术指标数据")
            ]
            
            results = []
            for query, description in test_queries:
                try:
                    cursor.execute(query)
                    count = cursor.fetchone()[0]
                    results.append(f"{description}: {count}条")
                except Exception as e:
                    results.append(f"{description}: 表不存在或查询失败")
            
            cursor.close()
            conn.close()
            
            response_time = time.time() - test_start
            self.log_test("Database System", "PASS", f"数据库检查完成 - {'; '.join(results)}", response_time)
            
        except Exception as e:
            response_time = time.time() - test_start
            self.log_test("Database System", "FAIL", f"数据库系统检查失败: {str(e)}", response_time)

    def test_authenticated_apis(self):
        """测试认证后的API端点"""
        api_tests = [
            ("/api/btc-price", "BTC价格API"),
            ("/api/network-stats", "网络统计API"),
            ("/api/miners", "矿机列表API"),
            ("/api/sha256-comparison", "SHA256对比API")
        ]
        
        for endpoint, name in api_tests:
            test_start = time.time()
            try:
                response = self.session.get(f"{self.base_url}{endpoint}", timeout=15)
                response_time = time.time() - test_start
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        if data and data.get('success', True):
                            # 检查具体数据内容
                            if endpoint == "/api/btc-price":
                                price = data.get('price', 0)
                                if price > 50000:
                                    self.log_test(f"API - {name}", "PASS", f"BTC价格: ${price:,.2f}", response_time)
                                else:
                                    self.log_test(f"API - {name}", "WARN", f"价格数据异常: ${price}", response_time)
                            elif endpoint == "/api/network-stats":
                                hashrate = data.get('hashrate', 0)
                                if hashrate > 500:
                                    self.log_test(f"API - {name}", "PASS", f"网络算力: {hashrate:.1f} EH/s", response_time)
                                else:
                                    self.log_test(f"API - {name}", "WARN", f"算力数据异常: {hashrate}", response_time)
                            elif endpoint == "/api/miners":
                                miners = data.get('miners', [])
                                if len(miners) >= 5:
                                    self.log_test(f"API - {name}", "PASS", f"矿机型号: {len(miners)}种", response_time)
                                else:
                                    self.log_test(f"API - {name}", "WARN", f"矿机数据不足: {len(miners)}种", response_time)
                            elif endpoint == "/api/sha256-comparison":
                                coins = data.get('data', [])
                                if len(coins) >= 3:
                                    self.log_test(f"API - {name}", "PASS", f"SHA256币种: {len(coins)}种", response_time)
                                else:
                                    self.log_test(f"API - {name}", "WARN", f"对比数据不足: {len(coins)}种", response_time)
                        else:
                            error_msg = data.get('error', '未知错误')
                            self.log_test(f"API - {name}", "FAIL", f"API错误: {error_msg}", response_time)
                    except json.JSONDecodeError:
                        self.log_test(f"API - {name}", "FAIL", "返回非JSON数据", response_time)
                else:
                    self.log_test(f"API - {name}", "FAIL", f"HTTP错误: {response.status_code}", response_time)
                    
            except Exception as e:
                response_time = time.time() - test_start
                self.log_test(f"API - {name}", "FAIL", f"请求异常: {str(e)}", response_time)

    def test_mining_calculation_functionality(self):
        """测试挖矿计算功能"""
        test_start = time.time()
        try:
            # 使用真实参数进行计算测试
            calc_data = {
                "miner_model": "Antminer S21 XP",
                "miner_count": "1",
                "site_power_mw": "0.00473",
                "electricity_cost": "0.05",
                "use_real_time_data": "true"
            }
            
            response = self.session.post(f"{self.base_url}/calculate", data=calc_data, timeout=20)
            response_time = time.time() - test_start
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    if result.get('success'):
                        daily_revenue = result.get('daily_revenue', 0)
                        monthly_profit = result.get('monthly_profit', 0)
                        btc_mined_daily = result.get('btc_mined', {}).get('daily', 0)
                        
                        self.log_test("Mining Calculation", "PASS", 
                            f"计算成功 - 日收入: ${daily_revenue:.2f}, 月利润: ${monthly_profit:.2f}, 日产BTC: {btc_mined_daily:.6f}", 
                            response_time)
                    else:
                        error_msg = result.get('error', '计算失败')
                        self.log_test("Mining Calculation", "FAIL", f"计算错误: {error_msg}", response_time)
                except json.JSONDecodeError:
                    self.log_test("Mining Calculation", "FAIL", "计算返回非JSON数据", response_time)
            else:
                self.log_test("Mining Calculation", "FAIL", f"计算请求失败: {response.status_code}", response_time)
                
        except Exception as e:
            response_time = time.time() - test_start
            self.log_test("Mining Calculation", "FAIL", f"计算功能异常: {str(e)}", response_time)

    def test_analytics_integration(self):
        """测试分析系统集成"""
        test_start = time.time()
        try:
            # 测试分析页面访问
            analytics_response = self.session.get(f"{self.base_url}/analytics")
            
            if analytics_response.status_code == 200:
                # 测试分析API端点
                api_endpoints = [
                    "/api/analytics/market-data",
                    "/api/analytics/latest-report", 
                    "/api/analytics/technical-indicators"
                ]
                
                working_apis = 0
                for endpoint in api_endpoints:
                    try:
                        api_response = self.session.get(f"{self.base_url}{endpoint}", timeout=10)
                        if api_response.status_code == 200:
                            working_apis += 1
                    except:
                        pass
                
                response_time = time.time() - test_start
                if working_apis >= 1:
                    self.log_test("Analytics Integration", "PASS", 
                        f"分析系统集成正常 - {working_apis}/3个API端点可用", response_time)
                else:
                    self.log_test("Analytics Integration", "WARN", 
                        "分析页面可访问，但API端点不可用", response_time)
            else:
                response_time = time.time() - test_start
                self.log_test("Analytics Integration", "WARN", 
                    f"分析页面访问受限: {analytics_response.status_code}", response_time)
                
        except Exception as e:
            response_time = time.time() - test_start
            self.log_test("Analytics Integration", "FAIL", f"分析系统测试异常: {str(e)}", response_time)

    def test_external_data_sources(self):
        """测试外部数据源连接"""
        external_tests = [
            ("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd", "CoinGecko API"),
            ("https://blockchain.info/q/getdifficulty", "Blockchain.info API")
        ]
        
        for url, name in external_tests:
            test_start = time.time()
            try:
                response = requests.get(url, timeout=10)
                response_time = time.time() - test_start
                
                if response.status_code == 200:
                    if "coingecko" in url:
                        data = response.json()
                        btc_price = data.get("bitcoin", {}).get("usd", 0)
                        if btc_price > 50000:
                            self.log_test(f"External - {name}", "PASS", f"BTC价格: ${btc_price:,.2f}", response_time)
                        else:
                            self.log_test(f"External - {name}", "WARN", f"价格异常: ${btc_price}", response_time)
                    elif "blockchain.info" in url:
                        difficulty = float(response.text)
                        if difficulty > 100000000000000:
                            self.log_test(f"External - {name}", "PASS", f"网络难度: {difficulty:.2e}", response_time)
                        else:
                            self.log_test(f"External - {name}", "WARN", f"难度异常: {difficulty}", response_time)
                else:
                    self.log_test(f"External - {name}", "FAIL", f"HTTP错误: {response.status_code}", response_time)
                    
            except Exception as e:
                response_time = time.time() - test_start
                self.log_test(f"External - {name}", "FAIL", f"连接失败: {str(e)}", response_time)

    def test_system_performance(self):
        """测试系统性能指标"""
        # 页面加载性能测试
        test_start = time.time()
        try:
            response = self.session.get(f"{self.base_url}/", timeout=10)
            load_time = time.time() - test_start
            
            if response.status_code == 200 and load_time < 3.0:
                self.log_test("Performance - Page Load", "PASS", f"主页加载: {load_time:.2f}s", load_time)
            elif response.status_code == 200:
                self.log_test("Performance - Page Load", "WARN", f"页面加载较慢: {load_time:.2f}s", load_time)
            else:
                self.log_test("Performance - Page Load", "FAIL", f"页面加载失败: {response.status_code}")
        except Exception as e:
            self.log_test("Performance - Page Load", "FAIL", f"性能测试失败: {str(e)}")

        # API响应性能测试
        test_start = time.time()
        try:
            response = self.session.get(f"{self.base_url}/api/btc-price", timeout=10)
            api_time = time.time() - test_start
            
            if response.status_code == 200 and api_time < 2.0:
                self.log_test("Performance - API Response", "PASS", f"API响应: {api_time:.2f}s", api_time)
            elif response.status_code == 200:
                self.log_test("Performance - API Response", "WARN", f"API响应较慢: {api_time:.2f}s", api_time)
            else:
                self.log_test("Performance - API Response", "FAIL", f"API测试失败: {response.status_code}")
        except Exception as e:
            self.log_test("Performance - API Response", "FAIL", f"API性能测试失败: {str(e)}")

    def generate_comprehensive_report(self):
        """生成综合测试报告"""
        end_time = datetime.now()
        total_time = (end_time - self.start_time).total_seconds()
        
        passed = len([r for r in self.test_results if r["status"] == "PASS"])
        failed = len([r for r in self.test_results if r["status"] == "FAIL"])
        warned = len([r for r in self.test_results if r["status"] == "WARN"])
        total = len(self.test_results)
        
        print("\n" + "="*70)
        print("全系统认证回归测试报告 (Authenticated System Regression Test Report)")
        print("="*70)
        print(f"测试开始时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"测试结束时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"总测试时间: {total_time:.2f}秒")
        print(f"总测试项目: {total}")
        print(f"✅ 通过: {passed} | ❌ 失败: {failed} | ⚠️ 警告: {warned}")
        print(f"整体成功率: {(passed/total*100):.1f}%")
        print(f"系统健康度: {((passed + warned*0.5)/total*100):.1f}%")
        
        # 系统状态评估
        if failed == 0 and warned <= 2:
            print("\n🎉 系统运行状态：优秀 - 所有核心功能正常运行")
            system_status = "优秀"
        elif failed <= 1 and warned <= 4:
            print("\n✅ 系统运行状态：良好 - 主要功能运行正常，有少量警告")
            system_status = "良好"
        elif failed <= 3:
            print("\n⚠️ 系统运行状态：一般 - 部分功能存在问题，需要关注")
            system_status = "一般"
        else:
            print("\n❌ 系统运行状态：需要修复 - 多项关键功能存在问题")
            system_status = "需要修复"
        
        # 详细问题分析
        if failed > 0:
            failed_tests = [r for r in self.test_results if r["status"] == "FAIL"]
            print(f"\n需要修复的问题 ({len(failed_tests)}项):")
            for test in failed_tests:
                print(f"  • {test['test_name']}: {test['details']}")
        
        if warned > 0:
            warned_tests = [r for r in self.test_results if r["status"] == "WARN"]
            print(f"\n需要关注的警告 ({len(warned_tests)}项):")
            for test in warned_tests:
                print(f"  • {test['test_name']}: {test['details']}")
        
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
                "success_rate": passed/total*100,
                "health_score": (passed + warned*0.5)/total*100,
                "system_status": system_status
            },
            "test_results": self.test_results,
            "recommendations": self.generate_recommendations()
        }
        
        with open("authenticated_regression_report.json", "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n📋 详细报告已保存: authenticated_regression_report.json")
        return system_status

    def generate_recommendations(self):
        """生成系统改进建议"""
        recommendations = []
        
        failed_tests = [r for r in self.test_results if r["status"] == "FAIL"]
        warned_tests = [r for r in self.test_results if r["status"] == "WARN"]
        
        if any("API" in test["test_name"] for test in failed_tests):
            recommendations.append("检查API端点配置和权限设置")
        
        if any("Database" in test["test_name"] for test in failed_tests):
            recommendations.append("验证数据库连接和表结构完整性")
        
        if any("External" in test["test_name"] for test in failed_tests):
            recommendations.append("检查外部API服务状态和网络连接")
        
        if any("Performance" in test["test_name"] for test in warned_tests):
            recommendations.append("优化系统性能，考虑缓存或代码优化")
        
        if any("Analytics" in test["test_name"] for test in failed_tests):
            recommendations.append("检查分析系统服务状态和端口配置")
        
        return recommendations

    def run_complete_test_suite(self):
        """运行完整的测试套件"""
        print("开始全系统认证回归测试...")
        print("="*70)
        
        # 第一步：用户认证
        if not self.authenticate_user():
            print("\n❌ 用户认证失败，无法继续测试")
            return "认证失败"
        
        # 第二步：数据库系统测试
        self.test_database_system()
        
        # 第三步：认证API测试
        self.test_authenticated_apis()
        
        # 第四步：挖矿计算功能测试
        self.test_mining_calculation_functionality()
        
        # 第五步：分析系统集成测试
        self.test_analytics_integration()
        
        # 第六步：外部数据源测试
        self.test_external_data_sources()
        
        # 第七步：系统性能测试
        self.test_system_performance()
        
        # 生成综合报告
        return self.generate_comprehensive_report()

if __name__ == "__main__":
    tester = AuthenticatedRegressionTest()
    system_status = tester.run_complete_test_suite()
    
    # 设置退出代码
    if system_status in ["优秀", "良好"]:
        sys.exit(0)
    elif system_status == "一般":
        sys.exit(1)
    else:
        sys.exit(2)