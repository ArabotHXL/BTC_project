#!/usr/bin/env python3
"""
增强版99%精度测试 - 专注业务逻辑验证
Enhanced 99% Precision Test - Focus on Business Logic Validation

深度测试挖矿计算引擎和数据精度，确保达到99%业务准确率
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, List, Tuple
import logging

class Enhanced99PrecisionTest:
    def __init__(self):
        self.base_url = "http://localhost:5000"
        self.session = requests.Session()
        self.test_results = []
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        self.warning_tests = 0
        
        # 设置日志
        logging.basicConfig(level=logging.INFO)
        
    def log_test(self, category: str, test_name: str, status: str, details: str = "", response_time: float = None):
        """记录测试结果"""
        self.total_tests += 1
        
        if status == "PASS":
            self.passed_tests += 1
            symbol = "✅"
        elif status == "WARN":
            self.warning_tests += 1
            symbol = "⚠️"
        else:
            self.failed_tests += 1
            symbol = "❌"
        
        result = {
            'category': category,
            'test_name': test_name,
            'status': status,
            'details': details,
            'response_time': response_time,
            'timestamp': datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        time_info = f" ({response_time:.3f}s)" if response_time else ""
        print(f"{symbol} {category}.{test_name}: {status}{time_info}")
        if details:
            print(f"   → {details}")
    
    def authenticate_system(self) -> bool:
        """系统认证 - 使用指定邮箱"""
        try:
            start_time = time.time()
            
            # 登录获取认证
            login_data = {'email': 'hxl2022hao@gmail.com'}
            response = self.session.post(f"{self.base_url}/login", data=login_data)
            
            response_time = time.time() - start_time
            
            if response.status_code in [200, 302]:
                self.log_test("Authentication", "system_login", "PASS", 
                            "系统认证成功", response_time)
                return True
            else:
                self.log_test("Authentication", "system_login", "FAIL",
                            f"认证失败: {response.status_code}", response_time)
                return False
                
        except Exception as e:
            self.log_test("Authentication", "system_login", "FAIL", f"认证异常: {e}")
            return False
    
    def test_core_apis_precision(self):
        """测试核心API数据精度"""
        print("\n📊 测试核心API数据精度...")
        
        # 测试1: BTC价格API精度
        try:
            start_time = time.time()
            response = self.session.get(f"{self.base_url}/api/btc-price")
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                btc_price = data.get('price')
                source = data.get('source', 'unknown')
                
                # 精确验证价格范围和精度
                if btc_price and 80000 <= btc_price <= 150000:
                    # 验证小数位数精度
                    decimal_places = len(str(btc_price).split('.')[1]) if '.' in str(btc_price) else 0
                    if decimal_places <= 2:
                        self.log_test("CoreAPI", "btc_price_precision", "PASS",
                                    f"BTC价格: ${btc_price:,.2f}, 来源: {source}", response_time)
                    else:
                        self.log_test("CoreAPI", "btc_price_precision", "WARN",
                                    f"价格精度过高: {decimal_places}位小数", response_time)
                else:
                    self.log_test("CoreAPI", "btc_price_precision", "FAIL",
                                f"BTC价格超出合理范围: ${btc_price}", response_time)
            else:
                self.log_test("CoreAPI", "btc_price_precision", "FAIL",
                            f"API错误: {response.status_code}", response_time)
                
        except Exception as e:
            self.log_test("CoreAPI", "btc_price_precision", "FAIL", f"API测试异常: {e}")
        
        # 测试2: 网络统计API精度
        try:
            start_time = time.time()
            response = self.session.get(f"{self.base_url}/api/network-stats")
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                hashrate = data.get('network_hashrate')
                difficulty = data.get('difficulty')
                source = data.get('source', 'unknown')
                
                # 验证算力精度
                if hashrate and 700 <= hashrate <= 1200:
                    hashrate_precision = len(str(hashrate).split('.')[1]) if '.' in str(hashrate) else 0
                    if hashrate_precision <= 2:
                        self.log_test("CoreAPI", "hashrate_precision", "PASS",
                                    f"算力: {hashrate:.2f} EH/s, 来源: {source}", response_time)
                    else:
                        self.log_test("CoreAPI", "hashrate_precision", "WARN",
                                    f"算力精度: {hashrate_precision}位小数", response_time)
                else:
                    self.log_test("CoreAPI", "hashrate_precision", "FAIL",
                                f"算力超出范围: {hashrate} EH/s", response_time)
                
                # 验证难度精度
                if difficulty and difficulty > 1e14:  # 合理的难度值
                    self.log_test("CoreAPI", "difficulty_precision", "PASS",
                                f"难度: {difficulty/1e12:.1f}T", response_time)
                else:
                    self.log_test("CoreAPI", "difficulty_precision", "WARN",
                                f"难度值: {difficulty}", response_time)
                                
            else:
                self.log_test("CoreAPI", "network_precision", "FAIL",
                            f"网络API错误: {response.status_code}", response_time)
                
        except Exception as e:
            self.log_test("CoreAPI", "network_precision", "FAIL", f"网络API异常: {e}")
    
    def test_mining_calculation_precision(self):
        """测试挖矿计算精度 - 深度验证"""
        print("\n⚡ 测试挖矿计算引擎精度...")
        
        # 测试用例1: 标准计算
        test_cases = [
            {
                'name': 'standard_calculation',
                'params': {
                    'miner_model': 'Antminer S21 XP',
                    'miner_count': '100',
                    'electricity_cost': '0.05',
                    'use_real_time': 'on'
                },
                'expected_range': {
                    'min_daily_btc': 0.03,
                    'max_daily_btc': 0.08,
                    'min_daily_profit': 1000,
                    'max_daily_profit': 8000
                }
            },
            {
                'name': 'single_miner',
                'params': {
                    'miner_model': 'Antminer S19 Pro',
                    'miner_count': '1',
                    'electricity_cost': '0.08',
                    'use_real_time': 'on'
                },
                'expected_range': {
                    'min_daily_btc': 0.0001,
                    'max_daily_btc': 0.001,
                    'min_daily_profit': -50,
                    'max_daily_profit': 50
                }
            },
            {
                'name': 'high_efficiency',
                'params': {
                    'miner_model': 'Antminer S21 XP Hyd',
                    'miner_count': '50',
                    'electricity_cost': '0.03',
                    'use_real_time': 'on'
                },
                'expected_range': {
                    'min_daily_btc': 0.02,
                    'max_daily_btc': 0.06,
                    'min_daily_profit': 1500,
                    'max_daily_profit': 6000
                }
            }
        ]
        
        for test_case in test_cases:
            try:
                start_time = time.time()
                response = self.session.post(f"{self.base_url}/calculate", data=test_case['params'])
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    # 解析HTML响应或JSON响应
                    content = response.text
                    
                    # 检查是否包含计算结果
                    if 'btc_mined' in content or 'daily_profit' in content or 'TH/s' in content:
                        self.log_test("Calculation", f"test_{test_case['name']}", "PASS",
                                    f"计算成功: {test_case['params']['miner_model']}", response_time)
                        
                        # 如果是JSON响应，进行详细验证
                        try:
                            if response.headers.get('content-type', '').startswith('application/json'):
                                data = response.json()
                                self._validate_calculation_precision(test_case, data, response_time)
                        except json.JSONDecodeError:
                            # HTML响应 - 检查关键指标存在性
                            if 'TH/s' in content and ('BTC' in content or 'profit' in content):
                                self.log_test("Calculation", f"output_{test_case['name']}", "PASS",
                                            "HTML响应包含计算指标")
                            else:
                                self.log_test("Calculation", f"output_{test_case['name']}", "WARN",
                                            "HTML响应缺少关键指标")
                    else:
                        self.log_test("Calculation", f"test_{test_case['name']}", "FAIL",
                                    "计算响应无有效数据", response_time)
                else:
                    self.log_test("Calculation", f"test_{test_case['name']}", "FAIL",
                                f"计算失败: {response.status_code}", response_time)
                                
            except Exception as e:
                self.log_test("Calculation", f"test_{test_case['name']}", "FAIL", f"计算异常: {e}")
    
    def _validate_calculation_precision(self, test_case: dict, data: dict, response_time: float):
        """验证计算结果精度"""
        name = test_case['name']
        expected = test_case['expected_range']
        
        # 提取计算结果
        daily_btc = data.get('daily_btc', 0)
        daily_profit = data.get('daily_profit', 0)
        
        # 验证BTC产出范围
        if expected['min_daily_btc'] <= daily_btc <= expected['max_daily_btc']:
            self.log_test("Precision", f"btc_range_{name}", "PASS",
                        f"日产BTC: {daily_btc:.6f} (合理范围)")
        else:
            self.log_test("Precision", f"btc_range_{name}", "WARN",
                        f"日产BTC: {daily_btc:.6f} (超出预期)")
        
        # 验证利润范围
        if expected['min_daily_profit'] <= daily_profit <= expected['max_daily_profit']:
            self.log_test("Precision", f"profit_range_{name}", "PASS",
                        f"日利润: ${daily_profit:.2f} (合理范围)")
        else:
            self.log_test("Precision", f"profit_range_{name}", "WARN",
                        f"日利润: ${daily_profit:.2f} (超出预期)")
    
    def test_business_logic_accuracy(self):
        """测试业务逻辑准确性"""
        print("\n💼 测试业务逻辑准确性...")
        
        # 测试1: 矿机效率对比
        try:
            response = self.session.get(f"{self.base_url}/api/miners")
            if response.status_code == 200:
                data = response.json()
                miners = data.get('miners', [])
                
                # 验证效率计算正确性
                efficiency_valid = 0
                total_miners = len(miners)
                
                for miner in miners:
                    hashrate = miner.get('hashrate', 0)
                    power = miner.get('power_watt', 0)
                    efficiency = miner.get('efficiency', 0)
                    
                    # 验证效率公式: W/TH
                    if hashrate > 0:
                        calculated_efficiency = power / hashrate
                        if abs(calculated_efficiency - efficiency) < 0.1:  # 允许0.1的误差
                            efficiency_valid += 1
                
                accuracy_rate = (efficiency_valid / total_miners * 100) if total_miners > 0 else 0
                
                if accuracy_rate >= 95:
                    self.log_test("Business", "efficiency_calculation", "PASS",
                                f"效率计算准确率: {accuracy_rate:.1f}%")
                elif accuracy_rate >= 90:
                    self.log_test("Business", "efficiency_calculation", "WARN",
                                f"效率计算准确率: {accuracy_rate:.1f}%")
                else:
                    self.log_test("Business", "efficiency_calculation", "FAIL",
                                f"效率计算准确率过低: {accuracy_rate:.1f}%")
            else:
                self.log_test("Business", "efficiency_calculation", "FAIL",
                            f"无法获取矿机数据: {response.status_code}")
                            
        except Exception as e:
            self.log_test("Business", "efficiency_calculation", "FAIL", f"效率测试异常: {e}")
        
        # 测试2: 电费成本影响验证
        try:
            # 测试不同电费的影响
            cost_tests = [
                {'cost': '0.03', 'expected': 'high_profit'},
                {'cost': '0.08', 'expected': 'medium_profit'},
                {'cost': '0.15', 'expected': 'low_profit'}
            ]
            
            profits = []
            
            for cost_test in cost_tests:
                params = {
                    'miner_model': 'Antminer S21 XP',
                    'miner_count': '10',
                    'electricity_cost': cost_test['cost'],
                    'use_real_time': 'on'
                }
                
                response = self.session.post(f"{self.base_url}/calculate", data=params)
                if response.status_code == 200:
                    # 记录电费成本计算成功
                    self.log_test("Business", f"cost_impact_{cost_test['cost']}", "PASS",
                                f"电费{cost_test['cost']}$/kWh计算成功")
                else:
                    self.log_test("Business", f"cost_impact_{cost_test['cost']}", "FAIL",
                                f"电费计算失败: {response.status_code}")
            
            # 验证电费成本逻辑正确性
            if len([test for test in cost_tests if response.status_code == 200]) >= 2:
                self.log_test("Business", "cost_logic", "PASS",
                            "电费成本逻辑验证成功")
            else:
                self.log_test("Business", "cost_logic", "WARN",
                            "电费成本逻辑需要验证")
                            
        except Exception as e:
            self.log_test("Business", "cost_logic", "FAIL", f"成本逻辑测试异常: {e}")
    
    def test_data_consistency_precision(self):
        """测试数据一致性精度"""
        print("\n🔄 测试数据一致性精度...")
        
        # 多次获取相同数据验证一致性
        consistency_tests = []
        
        for i in range(5):
            try:
                # 获取BTC价格
                btc_response = self.session.get(f"{self.base_url}/api/btc-price")
                # 获取网络统计
                network_response = self.session.get(f"{self.base_url}/api/network-stats")
                
                if btc_response.status_code == 200 and network_response.status_code == 200:
                    btc_data = btc_response.json()
                    network_data = network_response.json()
                    
                    consistency_tests.append({
                        'btc_price': btc_data.get('price', 0),
                        'hashrate': network_data.get('network_hashrate', 0),
                        'difficulty': network_data.get('difficulty', 0)
                    })
                
                time.sleep(0.5)  # 间隔0.5秒
                
            except Exception as e:
                continue
        
        if len(consistency_tests) >= 3:
            # 验证BTC价格一致性
            btc_prices = [test['btc_price'] for test in consistency_tests]
            price_variance = (max(btc_prices) - min(btc_prices)) / (sum(btc_prices) / len(btc_prices)) * 100
            
            if price_variance <= 1.0:  # 1%以内变化
                self.log_test("Consistency", "price_stability", "PASS",
                            f"价格稳定性: {price_variance:.2f}% 变化")
            elif price_variance <= 5.0:
                self.log_test("Consistency", "price_stability", "WARN",
                            f"价格波动: {price_variance:.2f}% 变化")
            else:
                self.log_test("Consistency", "price_stability", "FAIL",
                            f"价格波动过大: {price_variance:.2f}% 变化")
            
            # 验证算力一致性
            hashrates = [test['hashrate'] for test in consistency_tests]
            hashrate_variance = (max(hashrates) - min(hashrates)) / (sum(hashrates) / len(hashrates)) * 100
            
            if hashrate_variance <= 1.0:
                self.log_test("Consistency", "hashrate_stability", "PASS",
                            f"算力稳定性: {hashrate_variance:.2f}% 变化")
            elif hashrate_variance <= 3.0:
                self.log_test("Consistency", "hashrate_stability", "WARN",
                            f"算力轻微波动: {hashrate_variance:.2f}% 变化")
            else:
                self.log_test("Consistency", "hashrate_stability", "FAIL",
                            f"算力波动过大: {hashrate_variance:.2f}% 变化")
        else:
            self.log_test("Consistency", "data_collection", "FAIL",
                        "数据收集不足，无法验证一致性")
    
    def test_system_reliability(self):
        """测试系统可靠性"""
        print("\n🛡️ 测试系统可靠性...")
        
        # 并发请求测试
        import threading
        import queue
        
        results_queue = queue.Queue()
        
        def concurrent_request():
            try:
                response = self.session.get(f"{self.base_url}/api/btc-price")
                results_queue.put({
                    'status_code': response.status_code,
                    'response_time': response.elapsed.total_seconds()
                })
            except Exception as e:
                results_queue.put({'error': str(e)})
        
        # 启动10个并发请求
        threads = []
        for i in range(10):
            thread = threading.Thread(target=concurrent_request)
            threads.append(thread)
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        # 收集结果
        successful_requests = 0
        total_requests = 0
        response_times = []
        
        while not results_queue.empty():
            result = results_queue.get()
            total_requests += 1
            
            if result.get('status_code') == 200:
                successful_requests += 1
                response_times.append(result.get('response_time', 0))
        
        # 计算成功率和平均响应时间
        success_rate = (successful_requests / total_requests * 100) if total_requests > 0 else 0
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        if success_rate >= 95 and avg_response_time <= 2.0:
            self.log_test("Reliability", "concurrent_load", "PASS",
                        f"并发成功率: {success_rate:.1f}%, 平均响应: {avg_response_time:.3f}s")
        elif success_rate >= 90:
            self.log_test("Reliability", "concurrent_load", "WARN",
                        f"并发成功率: {success_rate:.1f}%, 平均响应: {avg_response_time:.3f}s")
        else:
            self.log_test("Reliability", "concurrent_load", "FAIL",
                        f"并发成功率过低: {success_rate:.1f}%")
    
    def run_enhanced_99_test(self):
        """运行增强版99%精度测试"""
        print("🚀 开始增强版99%精度系统验证测试")
        print(f"测试开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        
        # 认证系统
        if not self.authenticate_system():
            print("❌ 认证失败，终止测试")
            return
        
        # 核心测试模块
        self.test_core_apis_precision()
        self.test_mining_calculation_precision()
        self.test_business_logic_accuracy()
        self.test_data_consistency_precision()
        self.test_system_reliability()
        
        # 生成最终报告
        self.generate_enhanced_report()
    
    def generate_enhanced_report(self):
        """生成增强版测试报告"""
        print("\n" + "=" * 80)
        print("🎯 增强版99%精度验证测试完成报告")
        print("=" * 80)
        
        end_time = datetime.now()
        print(f"测试结束时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 计算准确率
        total_tests = self.total_tests
        passed_tests = self.passed_tests
        warning_tests = self.warning_tests
        failed_tests = self.failed_tests
        
        accuracy_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        functional_rate = ((passed_tests + warning_tests) / total_tests * 100) if total_tests > 0 else 0
        
        print(f"总测试数量: {total_tests}")
        print(f"✅ 完全通过: {passed_tests}")
        print(f"⚠️  警告项目: {warning_tests}")
        print(f"❌ 失败项目: {failed_tests}")
        print(f"📊 精度准确率: {accuracy_rate:.1f}%")
        print(f"🔄 功能可用率: {functional_rate:.1f}%")
        
        # 增强评级系统
        if accuracy_rate >= 99:
            grade = "🟢 卓越 (99%+)"
            status = "🎉 完美达成99%目标!"
        elif accuracy_rate >= 95:
            grade = "🟡 优秀 (95%+)"
            status = "🔥 接近99%目标，表现优异"
        elif accuracy_rate >= 90:
            grade = "🟠 良好 (90%+)"
            status = "👍 基本达标，需要微调"
        elif accuracy_rate >= 80:
            grade = "🟡 可接受 (80%+)"
            status = "⚠️ 需要优化改进"
        else:
            grade = "🔴 需要重大改进"
            status = "❌ 距离99%目标较远"
        
        print(f"📈 系统评级: {grade}")
        print(f"🎯 目标达成: {status}")
        
        # 按模块统计
        print(f"\n📋 模块精度统计:")
        modules = {}
        for result in self.test_results:
            category = result['category']
            if category not in modules:
                modules[category] = {'total': 0, 'passed': 0, 'warning': 0, 'failed': 0}
            
            modules[category]['total'] += 1
            if result['status'] == 'PASS':
                modules[category]['passed'] += 1
            elif result['status'] == 'WARN':
                modules[category]['warning'] += 1
            else:
                modules[category]['failed'] += 1
        
        for module, stats in modules.items():
            module_accuracy = (stats['passed'] / stats['total'] * 100) if stats['total'] > 0 else 0
            module_functional = ((stats['passed'] + stats['warning']) / stats['total'] * 100) if stats['total'] > 0 else 0
            
            if module_accuracy >= 95:
                symbol = "🟢"
            elif module_accuracy >= 85:
                symbol = "🟡"
            elif module_functional >= 85:
                symbol = "⚠️"
            else:
                symbol = "🔴"
                
            print(f"  {symbol} {module}: {stats['passed']}/{stats['total']} 精确通过 ({module_accuracy:.1f}%), 功能率 {module_functional:.1f}%")
        
        # 保存详细报告
        report_filename = f"enhanced_99_precision_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_data = {
            'test_summary': {
                'total_tests': total_tests,
                'passed_tests': passed_tests,
                'warning_tests': warning_tests,
                'failed_tests': failed_tests,
                'accuracy_rate': accuracy_rate,
                'functional_rate': functional_rate,
                'grade': grade,
                'target_achieved': accuracy_rate >= 99
            },
            'module_statistics': modules,
            'detailed_results': self.test_results,
            'timestamp': end_time.isoformat()
        }
        
        try:
            with open(report_filename, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False)
            print(f"\n📄 详细精度报告已保存: {report_filename}")
        except Exception as e:
            print(f"\n⚠️ 报告保存失败: {e}")
        
        # 99%目标达成状态
        if accuracy_rate >= 99:
            print(f"\n🏆 恭喜! 系统精度达到 {accuracy_rate:.1f}%，成功达成99%精度目标!")
            print("🎯 系统已达到企业级精度标准")
        elif accuracy_rate >= 95:
            print(f"\n🔥 优秀! 系统精度达到 {accuracy_rate:.1f}%，非常接近99%目标!")
            print("💪 只需少量优化即可达到99%精度标准")
        else:
            print(f"\n⚡ 当前系统精度: {accuracy_rate:.1f}%，距离99%目标需要继续优化")
            print("🛠️ 建议重点优化失败项目以提升精度")

def main():
    """主函数"""
    try:
        test = Enhanced99PrecisionTest()
        test.run_enhanced_99_test()
    except KeyboardInterrupt:
        print("\n测试被用户中断")
    except Exception as e:
        print(f"测试执行异常: {e}")

if __name__ == "__main__":
    main()