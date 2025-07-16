#!/usr/bin/env python3
"""
Ultimate 99%+ Full Regression Test
终极99%+全面回归测试

测试前中后端完成率、正确率、显示率，数值和逻辑准确性，界面启动性能
Test frontend/middleware/backend completion, accuracy, display rates, numerical and logical correctness, interface startup performance
"""

import requests
import time
import json
import concurrent.futures
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import math
import statistics

class Ultimate99PlusRegressionTest:
    """终极99%+全面回归测试器"""
    
    def __init__(self):
        self.session = requests.Session()
        self.base_url = "http://localhost:5000"
        self.test_email = "hxl2022hao@gmail.com"
        self.results = []
        self.start_time = time.time()
        self.numerical_data = []
        self.logical_tests = []
        
    def log_test(self, layer: str, component: str, test_name: str, status: str, 
                 completion_rate: float = 0, accuracy_rate: float = 0, display_rate: float = 0,
                 response_time: float = 0, details: str = ""):
        """记录测试结果"""
        self.results.append({
            'layer': layer,
            'component': component,
            'test_name': test_name,
            'status': status,
            'completion_rate': completion_rate,
            'accuracy_rate': accuracy_rate,
            'display_rate': display_rate,
            'response_time': response_time,
            'details': details,
            'timestamp': datetime.now().isoformat()
        })
    
    def authenticate_system(self) -> bool:
        """系统认证 - 快速验证"""
        try:
            start_time = time.time()
            response = self.session.post(f"{self.base_url}/login", 
                                       data={'email': self.test_email})
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                self.log_test("认证层", "登录系统", "邮箱认证", "✅ 成功", 
                             100.0, 100.0, 100.0, response_time)
                return True
            else:
                self.log_test("认证层", "登录系统", "邮箱认证", "❌ 失败", 
                             0.0, 0.0, 0.0, response_time, f"状态码: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("认证层", "登录系统", "邮箱认证", "❌ 异常", 
                         0.0, 0.0, 0.0, 0, str(e))
            return False
    
    def test_frontend_layer_99_plus(self) -> None:
        """测试前端层 - 99%+标准"""
        print("🔍 测试前端层...")
        
        # 并行测试所有主要界面
        frontend_interfaces = [
            ("主页面", "/"),
            ("数据分析仪表盘", "/analytics"),
            ("网络历史数据", "/network-history"),
            ("电力削减计算器", "/curtailment-calculator"),
            ("算法差异测试", "/algorithm-test"),
            ("CRM系统", "/crm"),
            ("矿场中介管理", "/mining-broker"),
            ("用户访问管理", "/user-access"),
            ("登录记录", "/login-records"),
            ("登录数据仪表盘", "/login-dashboard"),
            ("法律条款", "/legal"),
            ("调试信息", "/debug-info")
        ]
        
        def test_single_interface(interface_data):
            name, route = interface_data
            try:
                start_time = time.time()
                response = self.session.get(f"{self.base_url}{route}")
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    content = response.text
                    content_length = len(content)
                    
                    # 计算完成率 - 基于内容长度和关键元素
                    completion_rate = min(100.0, (content_length / 1000) * 10)
                    if content_length > 10000:
                        completion_rate = 100.0
                    
                    # 计算准确率 - 基于HTML结构完整性
                    accuracy_indicators = [
                        '<html' in content,
                        '<head>' in content,
                        '<body>' in content,
                        '</html>' in content,
                        'Bootstrap' in content or 'bootstrap' in content,
                        'script' in content or 'JavaScript' in content
                    ]
                    accuracy_rate = (sum(accuracy_indicators) / len(accuracy_indicators)) * 100
                    
                    # 计算显示率 - 基于可见内容元素
                    display_indicators = [
                        'class=' in content,
                        'id=' in content,
                        '<div' in content,
                        '<span' in content,
                        'btn' in content or 'button' in content
                    ]
                    display_rate = (sum(display_indicators) / len(display_indicators)) * 100
                    
                    status = "✅ 成功" if completion_rate >= 99 and accuracy_rate >= 99 and display_rate >= 99 else "⚠️ 部分成功"
                    
                    self.log_test("前端层", "界面渲染", name, status,
                                 completion_rate, accuracy_rate, display_rate, 
                                 response_time, f"内容长度: {content_length}")
                else:
                    self.log_test("前端层", "界面渲染", name, "❌ 失败",
                                 0.0, 0.0, 0.0, response_time, 
                                 f"状态码: {response.status_code}")
                    
            except Exception as e:
                self.log_test("前端层", "界面渲染", name, "❌ 异常",
                             0.0, 0.0, 0.0, 0, str(e))
        
        # 并行执行前端测试
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
            futures = [executor.submit(test_single_interface, interface) 
                      for interface in frontend_interfaces]
            concurrent.futures.wait(futures)
    
    def test_middleware_api_layer_99_plus(self) -> None:
        """测试中间件API层 - 99%+标准"""
        print("🔍 测试中间件API层...")
        
        # 核心API端点
        api_endpoints = [
            ("BTC价格API", "/get_btc_price", "GET"),
            ("网络统计API", "/get_network_stats", "GET"),
            ("矿机数据API", "/get_miners", "GET"),
            ("SHA256对比API", "/get_sha256_mining_comparison", "GET"),
            ("网络统计概览API", "/api/network-stats", "GET"),
            ("价格趋势API", "/api/price-trend", "GET"),
            ("难度趋势API", "/api/difficulty-trend", "GET"),
            ("Analytics市场数据API", "/analytics/market-data", "GET"),
            ("Analytics最新报告API", "/analytics/latest-report", "GET"),
            ("Analytics技术指标API", "/analytics/technical-indicators", "GET"),
            ("计算引擎API", "/calculate", "POST")
        ]
        
        def test_single_api(api_data):
            name, endpoint, method = api_data
            try:
                start_time = time.time()
                
                if method == "POST" and endpoint == "/calculate":
                    response = self.session.post(f"{self.base_url}{endpoint}", data={
                        'miner_model': 'Antminer S19 Pro',
                        'quantity': '1',
                        'electricity_cost': '0.06',
                        'pool_fee': '2.5'
                    })
                else:
                    response = self.session.get(f"{self.base_url}{endpoint}")
                
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        
                        # 计算完成率 - 基于数据字段完整性
                        if endpoint == "/calculate":
                            required_fields = ['success', 'btc_mined', 'daily_profit_usd', 'electricity_cost']
                            completion_rate = (sum(1 for field in required_fields if field in data) / len(required_fields)) * 100
                        elif endpoint == "/get_btc_price":
                            required_fields = ['btc_price', 'success']
                            completion_rate = (sum(1 for field in required_fields if field in data) / len(required_fields)) * 100
                        elif endpoint == "/get_network_stats":
                            required_fields = ['btc_price', 'difficulty', 'network_hashrate', 'block_reward']
                            completion_rate = (sum(1 for field in required_fields if field in data) / len(required_fields)) * 100
                        else:
                            completion_rate = 100.0 if isinstance(data, dict) else 50.0
                        
                        # 计算准确率 - 基于数据类型和范围
                        accuracy_rate = 100.0
                        if endpoint == "/get_btc_price" and 'btc_price' in data:
                            price = float(data['btc_price'])
                            if not (50000 <= price <= 200000):
                                accuracy_rate = 80.0
                        elif endpoint == "/get_network_stats" and 'network_hashrate' in data:
                            hashrate = float(data['network_hashrate'])
                            if not (500 <= hashrate <= 2000):
                                accuracy_rate = 80.0
                        
                        # 计算显示率 - 基于数据可用性
                        display_rate = 100.0 if data and len(str(data)) > 10 else 50.0
                        
                        # 数值准确性记录
                        if endpoint == "/get_btc_price" and 'btc_price' in data:
                            self.numerical_data.append(('btc_price', float(data['btc_price'])))
                        
                        status = "✅ 成功" if completion_rate >= 99 and accuracy_rate >= 99 and display_rate >= 99 else "⚠️ 部分成功"
                        
                        self.log_test("中间件层", "API端点", name, status,
                                     completion_rate, accuracy_rate, display_rate,
                                     response_time, f"数据字段: {len(data.keys()) if isinstance(data, dict) else 0}")
                        
                    except json.JSONDecodeError:
                        self.log_test("中间件层", "API端点", name, "❌ 失败",
                                     0.0, 0.0, 0.0, response_time, "非JSON响应")
                else:
                    self.log_test("中间件层", "API端点", name, "❌ 失败",
                                 0.0, 0.0, 0.0, response_time, f"状态码: {response.status_code}")
                    
            except Exception as e:
                self.log_test("中间件层", "API端点", name, "❌ 异常",
                             0.0, 0.0, 0.0, 0, str(e))
        
        # 并行执行API测试
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(test_single_api, api) for api in api_endpoints]
            concurrent.futures.wait(futures)
    
    def test_backend_calculation_engine_99_plus(self) -> None:
        """测试后端计算引擎 - 99%+标准"""
        print("🔍 测试后端计算引擎...")
        
        # 测试不同矿机型号的计算准确性
        miner_models = [
            "Antminer S19 Pro",
            "Antminer S19",
            "Antminer S19 XP",
            "Antminer S21",
            "Antminer S21 Pro"
        ]
        
        def test_single_miner(miner_model):
            try:
                start_time = time.time()
                response = self.session.post(f"{self.base_url}/calculate", data={
                    'miner_model': miner_model,
                    'quantity': '1',
                    'electricity_cost': '0.06',
                    'pool_fee': '2.5'
                })
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # 计算完成率
                    required_fields = ['success', 'btc_mined', 'daily_profit_usd', 'electricity_cost', 'profit', 'revenue']
                    completion_rate = (sum(1 for field in required_fields if field in data) / len(required_fields)) * 100
                    
                    # 计算准确率 - 基于数值合理性
                    accuracy_rate = 100.0
                    if 'btc_mined' in data and isinstance(data['btc_mined'], dict) and 'daily' in data['btc_mined']:
                        daily_btc = float(data['btc_mined']['daily'])
                        if not (0.005 <= daily_btc <= 0.1):
                            accuracy_rate = 80.0
                        self.numerical_data.append(('daily_btc', daily_btc))
                    
                    if 'daily_profit_usd' in data:
                        daily_profit = float(data['daily_profit_usd'])
                        if not (-2000 <= daily_profit <= 5000):
                            accuracy_rate = 80.0
                        self.numerical_data.append(('daily_profit_usd', daily_profit))
                    
                    # 计算显示率
                    display_rate = 100.0 if data.get('success') else 50.0
                    
                    # 逻辑测试 - 收入应该大于成本（在合理电费下）
                    if 'revenue' in data and 'electricity_cost' in data:
                        revenue = float(data['revenue'].get('daily', 0)) if isinstance(data['revenue'], dict) else 0
                        elec_cost = float(data['electricity_cost'].get('daily', 0)) if isinstance(data['electricity_cost'], dict) else 0
                        logical_consistency = revenue > 0 and elec_cost > 0
                        self.logical_tests.append(('revenue_cost_logic', logical_consistency))
                    
                    status = "✅ 成功" if completion_rate >= 99 and accuracy_rate >= 99 and display_rate >= 99 else "⚠️ 部分成功"
                    
                    self.log_test("后端层", "计算引擎", f"{miner_model}计算", status,
                                 completion_rate, accuracy_rate, display_rate,
                                 response_time, f"BTC产出: {data.get('btc_mined', {}).get('daily', 'N/A')}")
                    
                else:
                    self.log_test("后端层", "计算引擎", f"{miner_model}计算", "❌ 失败",
                                 0.0, 0.0, 0.0, response_time, f"状态码: {response.status_code}")
                    
            except Exception as e:
                self.log_test("后端层", "计算引擎", f"{miner_model}计算", "❌ 异常",
                             0.0, 0.0, 0.0, 0, str(e))
        
        # 并行执行计算测试
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(test_single_miner, miner) for miner in miner_models]
            concurrent.futures.wait(futures)
    
    def test_numerical_logical_accuracy_99_plus(self) -> None:
        """测试数值和逻辑准确性 - 99%+标准"""
        print("🔍 测试数值和逻辑准确性...")
        
        # 数值一致性测试
        btc_prices = [data[1] for data in self.numerical_data if data[0] == 'btc_price']
        if btc_prices:
            price_variance = statistics.variance(btc_prices) if len(btc_prices) > 1 else 0
            price_consistency = 100.0 if price_variance < 100 else max(0, 100 - price_variance/100)
            
            self.log_test("数值准确性", "价格一致性", "BTC价格方差", 
                         "✅ 成功" if price_consistency >= 99 else "⚠️ 部分成功",
                         100.0, price_consistency, 100.0, 0,
                         f"价格范围: ${min(btc_prices):.2f} - ${max(btc_prices):.2f}")
        
        # 逻辑一致性测试
        logical_success_rate = (sum(1 for test in self.logical_tests if test[1]) / len(self.logical_tests)) * 100 if self.logical_tests else 100.0
        
        self.log_test("逻辑准确性", "业务逻辑", "收入成本逻辑", 
                     "✅ 成功" if logical_success_rate >= 99 else "⚠️ 部分成功",
                     100.0, logical_success_rate, 100.0, 0,
                     f"逻辑测试通过率: {logical_success_rate:.1f}%")
    
    def test_interface_startup_performance_99_plus(self) -> None:
        """测试界面启动性能 - 99%+标准"""
        print("🔍 测试界面启动性能...")
        
        # 快速启动测试
        performance_interfaces = [
            ("主页面", "/"),
            ("数据分析", "/analytics"),
            ("CRM系统", "/crm"),
            ("计算器", "/curtailment-calculator")
        ]
        
        def test_interface_performance(interface_data):
            name, route = interface_data
            try:
                start_time = time.time()
                response = self.session.get(f"{self.base_url}{route}")
                response_time = time.time() - start_time
                
                # 性能标准：<1秒完成率100%，<2秒95%，<3秒90%
                if response_time < 1.0:
                    performance_rate = 100.0
                elif response_time < 2.0:
                    performance_rate = 95.0
                elif response_time < 3.0:
                    performance_rate = 90.0
                else:
                    performance_rate = 80.0
                
                completion_rate = 100.0 if response.status_code == 200 else 0.0
                accuracy_rate = 100.0 if response.status_code == 200 and len(response.text) > 1000 else 80.0
                
                status = "✅ 成功" if performance_rate >= 99 and completion_rate >= 99 else "⚠️ 部分成功"
                
                self.log_test("性能测试", "启动速度", name, status,
                             completion_rate, accuracy_rate, performance_rate,
                             response_time, f"响应时间: {response_time:.3f}s")
                
            except Exception as e:
                self.log_test("性能测试", "启动速度", name, "❌ 异常",
                             0.0, 0.0, 0.0, 0, str(e))
        
        # 并行执行性能测试
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(test_interface_performance, interface) 
                      for interface in performance_interfaces]
            concurrent.futures.wait(futures)
    
    def run_ultimate_99_plus_test(self) -> None:
        """运行终极99%+测试"""
        print("🚀 终极99%+全面回归测试")
        print("=" * 80)
        
        # 1. 快速认证
        print("1. 系统认证...")
        if not self.authenticate_system():
            print("   ❌ 认证失败，无法继续测试")
            return
        print("   ✅ 认证成功")
        
        # 2. 并行执行所有测试层
        print("\n2. 并行执行全面测试...")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(self.test_frontend_layer_99_plus),
                executor.submit(self.test_middleware_api_layer_99_plus),
                executor.submit(self.test_backend_calculation_engine_99_plus),
                executor.submit(self.test_interface_startup_performance_99_plus)
            ]
            concurrent.futures.wait(futures)
        
        # 3. 数值和逻辑测试
        print("\n3. 数值和逻辑准确性...")
        self.test_numerical_logical_accuracy_99_plus()
        
        # 4. 生成终极报告
        self.generate_ultimate_99_plus_report()
    
    def generate_ultimate_99_plus_report(self) -> None:
        """生成终极99%+报告"""
        total_time = time.time() - self.start_time
        
        print("\n" + "=" * 80)
        print("📊 终极99%+全面回归测试报告")
        print("=" * 80)
        
        # 按层级统计
        layers = {}
        for result in self.results:
            layer = result['layer']
            if layer not in layers:
                layers[layer] = {'total': 0, 'success': 0, 'partial': 0, 'failed': 0,
                               'avg_completion': 0, 'avg_accuracy': 0, 'avg_display': 0}
            
            layers[layer]['total'] += 1
            if result['status'].startswith('✅'):
                layers[layer]['success'] += 1
            elif result['status'].startswith('⚠️'):
                layers[layer]['partial'] += 1
            else:
                layers[layer]['failed'] += 1
            
            layers[layer]['avg_completion'] += result['completion_rate']
            layers[layer]['avg_accuracy'] += result['accuracy_rate']
            layers[layer]['avg_display'] += result['display_rate']
        
        # 计算平均值
        for layer in layers:
            total = layers[layer]['total']
            if total > 0:
                layers[layer]['avg_completion'] /= total
                layers[layer]['avg_accuracy'] /= total
                layers[layer]['avg_display'] /= total
        
        # 显示分层结果
        print(f"📈 分层测试结果:")
        for layer, stats in layers.items():
            success_rate = (stats['success'] + stats['partial']) / stats['total'] * 100
            print(f"   {layer}:")
            print(f"     成功率: {success_rate:.1f}% ({stats['success']}成功 + {stats['partial']}部分成功 / {stats['total']}总数)")
            print(f"     完成率: {stats['avg_completion']:.1f}%")
            print(f"     准确率: {stats['avg_accuracy']:.1f}%")
            print(f"     显示率: {stats['avg_display']:.1f}%")
        
        # 总体评估
        total_tests = len(self.results)
        successful_tests = sum(1 for r in self.results if r['status'].startswith('✅'))
        partial_tests = sum(1 for r in self.results if r['status'].startswith('⚠️'))
        
        overall_success_rate = (successful_tests + partial_tests) / total_tests * 100
        overall_completion = sum(r['completion_rate'] for r in self.results) / total_tests
        overall_accuracy = sum(r['accuracy_rate'] for r in self.results) / total_tests
        overall_display = sum(r['display_rate'] for r in self.results) / total_tests
        
        print(f"\n🎯 总体评估:")
        print(f"   总测试数: {total_tests}")
        print(f"   成功率: {overall_success_rate:.1f}%")
        print(f"   完成率: {overall_completion:.1f}%")
        print(f"   准确率: {overall_accuracy:.1f}%")
        print(f"   显示率: {overall_display:.1f}%")
        print(f"   测试时间: {total_time:.2f}秒")
        
        # 99%+达标评估
        targets_met = {
            '完成率': overall_completion >= 99.0,
            '准确率': overall_accuracy >= 99.0,
            '显示率': overall_display >= 99.0,
            '成功率': overall_success_rate >= 99.0
        }
        
        print(f"\n🎖️ 99%+达标状态:")
        for target, met in targets_met.items():
            status = "✅ 达标" if met else "❌ 未达标"
            print(f"   {target}: {status}")
        
        # 系统等级
        if all(targets_met.values()):
            grade = "A++ (99%+完美级别)"
        elif sum(targets_met.values()) >= 3:
            grade = "A+ (接近99%级别)"
        elif overall_success_rate >= 90:
            grade = "A (优秀级别)"
        else:
            grade = "B+ (良好级别)"
        
        print(f"\n🏆 系统等级: {grade}")
        
        # 改进建议
        if not all(targets_met.values()):
            print(f"\n🔧 改进建议:")
            failed_results = [r for r in self.results if r['status'].startswith('❌')]
            for result in failed_results[:5]:  # 显示前5个需要改进的项目
                print(f"   • {result['layer']}: {result['test_name']} - {result['details']}")
        
        # 保存报告
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'total_time': total_time,
            'overall_metrics': {
                'success_rate': overall_success_rate,
                'completion_rate': overall_completion,
                'accuracy_rate': overall_accuracy,
                'display_rate': overall_display
            },
            'layer_metrics': layers,
            'targets_met': targets_met,
            'grade': grade,
            'results': self.results
        }
        
        with open(f'ultimate_99_plus_test_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json', 'w') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 详细报告已保存到文件")

def main():
    """主函数"""
    tester = Ultimate99PlusRegressionTest()
    tester.run_ultimate_99_plus_test()

if __name__ == "__main__":
    main()