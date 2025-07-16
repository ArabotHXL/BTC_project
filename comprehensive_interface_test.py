#!/usr/bin/env python3
"""
系统界面全面启动测试
Comprehensive Interface Startup Test

验证所有系统界面和组件的启动状态
Verify startup status of all system interfaces and components
"""

import requests
import time
from typing import Dict, List, Tuple
import json

class InterfaceStartupTest:
    """系统界面启动测试器"""
    
    def __init__(self):
        self.session = requests.Session()
        self.base_url = "http://localhost:5000"
        self.test_email = "hxl2022hao@gmail.com"
        self.results = []
        
    def log_test(self, interface_name: str, route: str, status: str, 
                 response_time: float = 0, details: str = ""):
        """记录测试结果"""
        self.results.append({
            'interface': interface_name,
            'route': route,
            'status': status,
            'response_time': response_time,
            'details': details
        })
        
    def authenticate(self) -> bool:
        """系统认证"""
        try:
            start_time = time.time()
            response = self.session.post(f"{self.base_url}/login", 
                                       data={'email': self.test_email})
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                self.log_test("认证系统", "/login", "✅ 成功", response_time)
                return True
            else:
                self.log_test("认证系统", "/login", "❌ 失败", response_time, 
                             f"状态码: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("认证系统", "/login", "❌ 异常", 0, str(e))
            return False
    
    def test_main_interfaces(self) -> None:
        """测试主要界面"""
        interfaces = [
            ("主页面", "/"),
            ("数据分析仪表盘", "/analytics"),
            ("网络历史数据分析", "/network-history"),
            ("电力削减计算器", "/curtailment-calculator"),
            ("算法差异测试工具", "/algorithm-test"),
            ("CRM系统", "/crm"),
            ("矿场中介管理", "/mining-broker"),
            ("用户访问管理", "/user-access"),
            ("登录记录", "/login-records"),
            ("登录数据仪表盘", "/login-dashboard"),
            ("法律条款", "/legal"),
            ("调试信息", "/debug-info")
        ]
        
        for name, route in interfaces:
            try:
                start_time = time.time()
                response = self.session.get(f"{self.base_url}{route}")
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    # 检查页面内容完整性
                    content_length = len(response.text)
                    if content_length > 1000:  # 完整页面应该有足够内容
                        self.log_test(name, route, "✅ 成功", response_time, 
                                     f"内容长度: {content_length}")
                    else:
                        self.log_test(name, route, "⚠️ 部分成功", response_time,
                                     f"内容较少: {content_length}")
                elif response.status_code == 403:
                    self.log_test(name, route, "🔒 权限限制", response_time,
                                 "需要特定权限")
                else:
                    self.log_test(name, route, "❌ 失败", response_time,
                                 f"状态码: {response.status_code}")
                    
            except Exception as e:
                self.log_test(name, route, "❌ 异常", 0, str(e))
    
    def test_api_endpoints(self) -> None:
        """测试API端点"""
        api_endpoints = [
            ("BTC价格API", "/get_btc_price"),
            ("网络统计API", "/get_network_stats"),
            ("矿机数据API", "/get_miners"),
            ("SHA256对比API", "/get_sha256_mining_comparison"),
            ("利润图表API", "/get_profit_chart_data"),
            ("网络统计概览API", "/api/network-stats"),
            ("价格趋势API", "/api/price-trend"),
            ("难度趋势API", "/api/difficulty-trend"),
            ("算力分析API", "/api/hashrate-analysis"),
            ("收益预测API", "/api/profitability-forecast"),
            ("Analytics市场数据API", "/analytics/market-data"),
            ("Analytics最新报告API", "/analytics/latest-report"),
            ("Analytics技术指标API", "/analytics/technical-indicators"),
            ("Analytics价格历史API", "/analytics/price-history")
        ]
        
        for name, endpoint in api_endpoints:
            try:
                start_time = time.time()
                response = self.session.get(f"{self.base_url}{endpoint}")
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        if isinstance(data, dict) and 'success' in data:
                            self.log_test(name, endpoint, "✅ 成功", response_time,
                                         f"数据字段: {len(data.keys())}")
                        else:
                            self.log_test(name, endpoint, "✅ 成功", response_time,
                                         "返回数据格式正确")
                    except json.JSONDecodeError:
                        self.log_test(name, endpoint, "⚠️ 部分成功", response_time,
                                     "非JSON响应")
                elif response.status_code == 403:
                    self.log_test(name, endpoint, "🔒 权限限制", response_time,
                                 "需要特定权限")
                else:
                    self.log_test(name, endpoint, "❌ 失败", response_time,
                                 f"状态码: {response.status_code}")
                    
            except Exception as e:
                self.log_test(name, endpoint, "❌ 异常", 0, str(e))
    
    def test_calculation_engine(self) -> None:
        """测试计算引擎"""
        try:
            start_time = time.time()
            response = self.session.post(f"{self.base_url}/calculate", data={
                'miner_model': 'Antminer S19 Pro',
                'quantity': '1',
                'electricity_cost': '0.06',
                'pool_fee': '2.5'
            })
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    if 'success' in data and data['success']:
                        required_fields = ['btc_mined', 'daily_profit_usd', 'electricity_cost']
                        found_fields = sum(1 for field in required_fields if field in data)
                        
                        if found_fields == len(required_fields):
                            self.log_test("计算引擎", "/calculate", "✅ 成功", response_time,
                                         f"所有关键字段存在: {found_fields}/{len(required_fields)}")
                        else:
                            self.log_test("计算引擎", "/calculate", "⚠️ 部分成功", response_time,
                                         f"字段不完整: {found_fields}/{len(required_fields)}")
                    else:
                        self.log_test("计算引擎", "/calculate", "❌ 失败", response_time,
                                     "计算失败")
                except json.JSONDecodeError:
                    self.log_test("计算引擎", "/calculate", "❌ 失败", response_time,
                                 "响应格式错误")
            else:
                self.log_test("计算引擎", "/calculate", "❌ 失败", response_time,
                             f"状态码: {response.status_code}")
                
        except Exception as e:
            self.log_test("计算引擎", "/calculate", "❌ 异常", 0, str(e))
    
    def run_comprehensive_test(self) -> None:
        """运行全面测试"""
        print("🚀 系统界面全面启动测试")
        print("=" * 60)
        
        # 1. 认证测试
        print("1. 系统认证...")
        if not self.authenticate():
            print("   ❌ 认证失败，无法继续测试")
            return
        print("   ✅ 认证成功")
        
        # 2. 主要界面测试
        print("\n2. 主要界面测试...")
        self.test_main_interfaces()
        
        # 3. API端点测试
        print("\n3. API端点测试...")
        self.test_api_endpoints()
        
        # 4. 计算引擎测试
        print("\n4. 计算引擎测试...")
        self.test_calculation_engine()
        
        # 5. 生成报告
        self.generate_report()
    
    def generate_report(self) -> None:
        """生成测试报告"""
        print("\n" + "=" * 60)
        print("📊 系统界面启动测试报告")
        print("=" * 60)
        
        # 统计结果
        total_tests = len(self.results)
        successful_tests = sum(1 for r in self.results if r['status'].startswith('✅'))
        partial_tests = sum(1 for r in self.results if r['status'].startswith('⚠️'))
        failed_tests = sum(1 for r in self.results if r['status'].startswith('❌'))
        restricted_tests = sum(1 for r in self.results if r['status'].startswith('🔒'))
        
        print(f"📈 测试统计:")
        print(f"   总测试数: {total_tests}")
        print(f"   ✅ 成功: {successful_tests}")
        print(f"   ⚠️ 部分成功: {partial_tests}")
        print(f"   🔒 权限限制: {restricted_tests}")
        print(f"   ❌ 失败: {failed_tests}")
        
        success_rate = (successful_tests + partial_tests) / total_tests * 100
        print(f"   🎯 成功率: {success_rate:.1f}%")
        
        # 详细结果
        print(f"\n📋 详细测试结果:")
        for result in self.results:
            response_time_str = f" ({result['response_time']:.3f}s)" if result['response_time'] > 0 else ""
            details_str = f" - {result['details']}" if result['details'] else ""
            print(f"   {result['status']} {result['interface']}: {result['route']}{response_time_str}{details_str}")
        
        # 系统等级评估
        if success_rate >= 95:
            grade = "A+ (完美级别)"
        elif success_rate >= 85:
            grade = "A (优秀级别)"
        elif success_rate >= 75:
            grade = "B+ (良好级别)"
        elif success_rate >= 65:
            grade = "B (及格级别)"
        else:
            grade = "C (需要改进)"
        
        print(f"\n🎖️ 系统等级: {grade}")
        print(f"⏱️ 测试完成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 改进建议
        if failed_tests > 0:
            print(f"\n🔧 改进建议:")
            failed_results = [r for r in self.results if r['status'].startswith('❌')]
            for result in failed_results:
                print(f"   • 修复 {result['interface']}: {result['details']}")

def main():
    """主函数"""
    tester = InterfaceStartupTest()
    tester.run_comprehensive_test()

if __name__ == "__main__":
    main()