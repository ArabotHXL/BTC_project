#!/usr/bin/env python3
"""
全面回归测试 - BTC挖矿计算器系统
Comprehensive Regression Test - BTC Mining Calculator System
"""

import requests
import time
import json
from datetime import datetime
import sys
import os

class ComprehensiveRegressionTest:
    def __init__(self):
        self.base_url = "http://0.0.0.0:5000"
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
        
        status_icon = "✓" if status == "PASS" else "✗" if status == "FAIL" else "⚠"
        time_str = f" ({response_time:.3f}s)" if response_time else ""
        print(f"{status_icon} {test_name}: {status}{time_str}")
        if details:
            print(f"   → {details}")

    def test_server_health(self):
        """测试服务器健康状态"""
        try:
            start = time.time()
            response = self.session.get(f"{self.base_url}/")
            response_time = time.time() - start
            
            if response.status_code in [200, 302]:  # 200 for success, 302 for redirect to login
                self.log_test("服务器健康检查", "PASS", f"状态码: {response.status_code}", response_time)
                return True
            else:
                self.log_test("服务器健康检查", "FAIL", f"状态码: {response.status_code}", response_time)
                return False
        except Exception as e:
            self.log_test("服务器健康检查", "FAIL", f"连接错误: {str(e)}")
            return False

    def test_api_endpoints(self):
        """测试关键API端点"""
        api_tests = [
            ("/api/get_btc_price", "BTC价格API"),
            ("/api/get_network_stats", "网络统计API"),
            ("/api/get_miners", "矿机数据API"),
            ("/api/get_sha256_mining_comparison", "SHA256挖矿对比API")
        ]
        
        for endpoint, name in api_tests:
            try:
                start = time.time()
                response = self.session.get(f"{self.base_url}{endpoint}")
                response_time = time.time() - start
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        if data and 'price' in str(data).lower() or 'data' in data or 'miners' in str(data).lower():
                            self.log_test(name, "PASS", f"返回有效数据", response_time)
                        else:
                            self.log_test(name, "WARN", f"数据格式异常", response_time)
                    except:
                        self.log_test(name, "WARN", f"JSON解析失败", response_time)
                else:
                    self.log_test(name, "FAIL", f"状态码: {response.status_code}", response_time)
            except Exception as e:
                self.log_test(name, "FAIL", f"请求失败: {str(e)}")

    def test_analytics_apis(self):
        """测试分析系统API"""
        analytics_tests = [
            ("/analytics/api/market-data", "分析系统市场数据API"),
            ("/analytics/api/latest-report", "最新分析报告API"),
            ("/analytics/api/technical-indicators", "技术指标API"),
            ("/analytics/api/price-history", "价格历史API")
        ]
        
        for endpoint, name in analytics_tests:
            try:
                start = time.time()
                response = self.session.get(f"{self.base_url}{endpoint}")
                response_time = time.time() - start
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        if data and 'data' in data:
                            self.log_test(name, "PASS", f"数据完整", response_time)
                        else:
                            self.log_test(name, "WARN", f"数据结构异常", response_time)
                    except:
                        self.log_test(name, "FAIL", f"JSON解析失败", response_time)
                else:
                    self.log_test(name, "FAIL", f"状态码: {response.status_code}", response_time)
            except Exception as e:
                self.log_test(name, "FAIL", f"请求失败: {str(e)}")

    def test_mining_calculation(self):
        """测试挖矿计算功能"""
        calculation_data = {
            "miner_model": "Antminer S21",
            "miner_count": "1",
            "electricity_cost": "0.05",
            "use_real_time_data": "true"
        }
        
        try:
            start = time.time()
            response = self.session.post(f"{self.base_url}/calculate", data=calculation_data)
            response_time = time.time() - start
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    if 'btc_per_day' in data and 'daily_profit_usd' in data:
                        btc_per_day = data.get('btc_per_day', 0)
                        daily_profit = data.get('daily_profit_usd', 0)
                        
                        if btc_per_day > 0 and daily_profit > 0:
                            self.log_test("挖矿计算功能", "PASS", 
                                        f"BTC/日: {btc_per_day:.4f}, 利润: ${daily_profit:.2f}", response_time)
                        else:
                            self.log_test("挖矿计算功能", "WARN", "计算结果为零", response_time)
                    else:
                        self.log_test("挖矿计算功能", "FAIL", "缺少关键数据字段", response_time)
                except:
                    self.log_test("挖矿计算功能", "FAIL", "JSON解析失败", response_time)
            else:
                self.log_test("挖矿计算功能", "FAIL", f"状态码: {response.status_code}", response_time)
        except Exception as e:
            self.log_test("挖矿计算功能", "FAIL", f"请求失败: {str(e)}")

    def test_page_loads(self):
        """测试主要页面加载"""
        # Note: These will redirect to login, but we test if they respond
        pages = [
            ("/", "主页"),
            ("/login", "登录页"),
            ("/analytics", "分析仪表盘"),
            ("/curtailment-calculator", "电力削减计算器"),
            ("/algorithm-test", "算法测试工具"),
            ("/network-history", "网络历史分析")
        ]
        
        for path, name in pages:
            try:
                start = time.time()
                response = self.session.get(f"{self.base_url}{path}")
                response_time = time.time() - start
                
                if response.status_code in [200, 302]:
                    self.log_test(f"页面加载: {name}", "PASS", 
                                f"状态码: {response.status_code}", response_time)
                else:
                    self.log_test(f"页面加载: {name}", "FAIL", 
                                f"状态码: {response.status_code}", response_time)
            except Exception as e:
                self.log_test(f"页面加载: {name}", "FAIL", f"请求失败: {str(e)}")

    def test_database_connectivity(self):
        """测试数据库连接"""
        # Test through an API that requires DB access
        try:
            start = time.time()
            response = self.session.get(f"{self.base_url}/analytics/api/market-data")
            response_time = time.time() - start
            
            if response.status_code == 200:
                data = response.json()
                if data and 'data' in data:
                    self.log_test("数据库连接", "PASS", "通过API验证数据库访问", response_time)
                else:
                    self.log_test("数据库连接", "WARN", "API响应但数据异常", response_time)
            else:
                self.log_test("数据库连接", "FAIL", f"API失败: {response.status_code}", response_time)
        except Exception as e:
            self.log_test("数据库连接", "FAIL", f"数据库访问失败: {str(e)}")

    def test_external_api_integration(self):
        """测试外部API集成"""
        try:
            start = time.time()
            response = self.session.get(f"{self.base_url}/api/get_network_stats")
            response_time = time.time() - start
            
            if response.status_code == 200:
                data = response.json()
                if 'hashrate' in data and 'difficulty' in data:
                    hashrate = data.get('hashrate', 0)
                    if hashrate > 0:
                        self.log_test("外部API集成", "PASS", 
                                    f"算力: {hashrate} EH/s", response_time)
                    else:
                        self.log_test("外部API集成", "WARN", "外部数据为空", response_time)
                else:
                    self.log_test("外部API集成", "FAIL", "数据格式错误", response_time)
            else:
                self.log_test("外部API集成", "FAIL", f"状态码: {response.status_code}", response_time)
        except Exception as e:
            self.log_test("外部API集成", "FAIL", f"外部API失败: {str(e)}")

    def test_miner_breakeven_analysis(self):
        """测试矿机盈亏平衡分析"""
        try:
            start = time.time()
            # Get current market data first
            market_response = self.session.get(f"{self.base_url}/analytics/api/market-data")
            response_time = time.time() - start
            
            if market_response.status_code == 200:
                market_data = market_response.json()
                if 'data' in market_data and 'btc_price' in market_data['data']:
                    btc_price = market_data['data']['btc_price']
                    network_hashrate = market_data['data'].get('network_hashrate', 900)
                    
                    # Calculate hash price
                    block_reward = 3.125
                    blocks_per_day = 144
                    daily_btc_rewards = block_reward * blocks_per_day
                    total_network_hashrate_th = network_hashrate * 1000  # Convert EH to TH
                    hash_price = (daily_btc_rewards * btc_price) / total_network_hashrate_th
                    
                    self.log_test("矿机盈亏平衡分析", "PASS", 
                                f"Hash Price: ${hash_price:.4f}/TH/天", response_time)
                else:
                    self.log_test("矿机盈亏平衡分析", "FAIL", "缺少市场数据", response_time)
            else:
                self.log_test("矿机盈亏平衡分析", "FAIL", f"API失败: {market_response.status_code}", response_time)
        except Exception as e:
            self.log_test("矿机盈亏平衡分析", "FAIL", f"计算失败: {str(e)}")

    def run_all_tests(self):
        """运行所有测试"""
        print("=" * 60)
        print("🔧 BTC挖矿计算器系统 - 全面回归测试")
        print(f"📅 测试时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        # 核心系统测试
        print("\n🏥 核心系统健康检查")
        self.test_server_health()
        self.test_database_connectivity()
        
        # API功能测试
        print("\n🔌 API端点功能测试")
        self.test_api_endpoints()
        
        # 分析系统测试
        print("\n📊 分析系统功能测试")
        self.test_analytics_apis()
        
        # 计算功能测试
        print("\n⚡ 挖矿计算功能测试")
        self.test_mining_calculation()
        self.test_miner_breakeven_analysis()
        
        # 页面加载测试
        print("\n🌐 页面加载功能测试")
        self.test_page_loads()
        
        # 外部集成测试
        print("\n🌍 外部API集成测试")
        self.test_external_api_integration()
        
        # 生成测试报告
        self.generate_report()

    def generate_report(self):
        """生成测试报告"""
        end_time = datetime.now()
        total_time = (end_time - self.start_time).total_seconds()
        
        passed = len([r for r in self.test_results if r['status'] == 'PASS'])
        failed = len([r for r in self.test_results if r['status'] == 'FAIL'])
        warnings = len([r for r in self.test_results if r['status'] == 'WARN'])
        total = len(self.test_results)
        
        success_rate = (passed / total * 100) if total > 0 else 0
        
        print("\n" + "=" * 60)
        print("📋 测试报告摘要")
        print("=" * 60)
        print(f"🎯 总测试数: {total}")
        print(f"✅ 通过: {passed}")
        print(f"❌ 失败: {failed}")
        print(f"⚠️  警告: {warnings}")
        print(f"📈 成功率: {success_rate:.1f}%")
        print(f"⏱️  总耗时: {total_time:.2f}秒")
        
        # 性能统计
        response_times = [r['response_time'] for r in self.test_results if r['response_time']]
        if response_times:
            avg_response = sum(response_times) / len(response_times)
            print(f"📊 平均响应时间: {avg_response:.3f}秒")
        
        # 失败详情
        if failed > 0:
            print(f"\n❌ 失败测试详情:")
            for result in self.test_results:
                if result['status'] == 'FAIL':
                    print(f"   • {result['test_name']}: {result['details']}")
        
        # 警告详情
        if warnings > 0:
            print(f"\n⚠️  警告测试详情:")
            for result in self.test_results:
                if result['status'] == 'WARN':
                    print(f"   • {result['test_name']}: {result['details']}")
        
        print("\n" + "=" * 60)
        
        # 系统状态评估
        if success_rate >= 90:
            print("🟢 系统状态: 优秀 - 所有核心功能正常运行")
        elif success_rate >= 75:
            print("🟡 系统状态: 良好 - 大部分功能正常，部分需要关注")
        elif success_rate >= 50:
            print("🟠 系统状态: 一般 - 存在多个问题需要修复")
        else:
            print("🔴 系统状态: 严重 - 系统存在重大问题")
        
        return success_rate >= 75

def main():
    """主函数"""
    test_runner = ComprehensiveRegressionTest()
    success = test_runner.run_all_tests()
    
    if success:
        print("\n🎉 回归测试完成 - 系统运行状态良好")
        return 0
    else:
        print("\n🚨 回归测试完成 - 发现严重问题需要修复")
        return 1

if __name__ == "__main__":
    sys.exit(main())