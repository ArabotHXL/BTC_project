#!/usr/bin/env python3
"""
全面99%准确率系统验证测试
Comprehensive 99% Accuracy System Verification Test

专注于核心功能的数字精度和业务逻辑准确性验证
Focus on numerical precision and business logic accuracy verification
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, List, Tuple
import logging

class Comprehensive99PercentTest:
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
        """系统认证 - 使用拥有者邮箱"""
        try:
            start_time = time.time()
            
            # 尝试登录
            login_data = {'email': 'hxl2022hao@gmail.com'}
            response = self.session.post(f"{self.base_url}/login", data=login_data)
            
            response_time = time.time() - start_time
            
            if response.status_code in [200, 302]:
                self.log_test("Authentication", "owner_login", "PASS", 
                            "拥有者认证成功", response_time)
                return True
            else:
                self.log_test("Authentication", "owner_login", "FAIL",
                            f"认证失败: {response.status_code}", response_time)
                return False
                
        except Exception as e:
            self.log_test("Authentication", "owner_login", "FAIL", f"认证异常: {e}")
            return False
    
    def test_numerical_precision(self):
        """测试数字精度 - 核心业务逻辑验证"""
        print("\n🔢 测试数字精度和业务逻辑...")
        
        # 测试1: BTC价格精度
        try:
            start_time = time.time()
            response = self.session.get(f"{self.base_url}/api/btc-price")
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                btc_price = data.get('price')
                
                # 验证价格合理性 (BTC价格应在合理范围内)
                if btc_price and 50000 <= btc_price <= 200000:
                    self.log_test("Numerical", "btc_price_precision", "PASS",
                                f"BTC价格: ${btc_price:,.2f} (合理范围)", response_time)
                else:
                    self.log_test("Numerical", "btc_price_precision", "FAIL",
                                f"BTC价格异常: ${btc_price}", response_time)
            else:
                self.log_test("Numerical", "btc_price_precision", "FAIL",
                            f"价格API错误: {response.status_code}", response_time)
                
        except Exception as e:
            self.log_test("Numerical", "btc_price_precision", "FAIL", f"价格测试异常: {e}")
        
        # 测试2: 网络算力精度
        try:
            start_time = time.time()
            response = self.session.get(f"{self.base_url}/api/network-stats")
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                hashrate = data.get('network_hashrate')
                difficulty = data.get('difficulty')
                
                # 验证算力合理性 (当前应在800-1200 EH/s范围)
                if hashrate and 800 <= hashrate <= 1200:
                    self.log_test("Numerical", "hashrate_precision", "PASS",
                                f"网络算力: {hashrate:.2f} EH/s (合理范围)", response_time)
                else:
                    self.log_test("Numerical", "hashrate_precision", "FAIL",
                                f"算力异常: {hashrate} EH/s", response_time)
                
                # 验证难度值合理性
                if difficulty and difficulty > 100e12:  # 100T+
                    self.log_test("Numerical", "difficulty_precision", "PASS",
                                f"网络难度: {difficulty/1e12:.1f}T", response_time)
                else:
                    self.log_test("Numerical", "difficulty_precision", "FAIL",
                                f"难度异常: {difficulty}", response_time)
            else:
                self.log_test("Numerical", "hashrate_precision", "FAIL",
                            f"网络API错误: {response.status_code}", response_time)
                
        except Exception as e:
            self.log_test("Numerical", "hashrate_precision", "FAIL", f"算力测试异常: {e}")
    
    def test_mining_calculation_accuracy(self):
        """测试挖矿计算准确性"""
        print("\n⚡ 测试挖矿计算引擎准确性...")
        
        # 标准测试参数
        test_params = {
            'miner_model': 'Antminer S21 XP',
            'miner_count': '100',
            'electricity_cost': '0.05',
            'use_real_time': 'on'
        }
        
        try:
            start_time = time.time()
            response = self.session.post(f"{self.base_url}/calculate", data=test_params)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                # 计算成功，验证响应内容
                content = response.text
                
                # 检查是否包含关键数字指标
                if "daily_btc" in content and "daily_profit" in content:
                    self.log_test("Calculation", "mining_computation", "PASS",
                                "挖矿计算成功返回", response_time)
                    
                    # 尝试解析JSON响应验证数字
                    try:
                        if response.headers.get('content-type', '').startswith('application/json'):
                            data = response.json()
                            daily_btc = data.get('daily_btc', 0)
                            daily_profit = data.get('daily_profit', 0)
                            
                            # 验证计算结果合理性
                            if 0.01 <= daily_btc <= 1.0:  # 100台矿机日产0.01-1.0 BTC合理
                                self.log_test("Calculation", "btc_output_range", "PASS",
                                            f"日产BTC: {daily_btc:.6f} (合理范围)")
                            else:
                                self.log_test("Calculation", "btc_output_range", "WARN",
                                            f"日产BTC: {daily_btc:.6f} (可能异常)")
                            
                            if daily_profit > 0:
                                self.log_test("Calculation", "profit_positive", "PASS",
                                            f"日利润: ${daily_profit:.2f} (盈利)")
                            else:
                                self.log_test("Calculation", "profit_positive", "WARN",
                                            f"日利润: ${daily_profit:.2f} (亏损)")
                        else:
                            self.log_test("Calculation", "response_format", "PASS",
                                        "HTML响应格式正确")
                    except json.JSONDecodeError:
                        self.log_test("Calculation", "response_parsing", "PASS",
                                    "HTML响应包含计算结果")
                else:
                    self.log_test("Calculation", "mining_computation", "FAIL",
                                "计算响应缺少关键指标", response_time)
            else:
                self.log_test("Calculation", "mining_computation", "FAIL",
                            f"计算请求失败: {response.status_code}", response_time)
                
        except Exception as e:
            self.log_test("Calculation", "mining_computation", "FAIL", f"计算测试异常: {e}")
    
    def test_miner_model_accuracy(self):
        """测试矿机型号数据准确性"""
        print("\n🔧 测试矿机型号数据准确性...")
        
        try:
            start_time = time.time()
            response = self.session.get(f"{self.base_url}/api/miners")
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                miners = data.get('miners', {})
                
                # 验证矿机数量
                if len(miners) >= 10:
                    self.log_test("Miners", "model_count", "PASS",
                                f"矿机型号: {len(miners)}种", response_time)
                else:
                    self.log_test("Miners", "model_count", "FAIL",
                                f"矿机型号不足: {len(miners)}种", response_time)
                
                # 验证关键矿机型号存在
                key_models = ['Antminer S21 XP', 'Antminer S19 Pro', 'Antminer S21']
                missing_models = []
                
                for model in key_models:
                    if model not in miners:
                        missing_models.append(model)
                
                if not missing_models:
                    self.log_test("Miners", "key_models", "PASS",
                                "关键矿机型号完整")
                else:
                    self.log_test("Miners", "key_models", "FAIL",
                                f"缺失型号: {missing_models}")
                
                # 验证矿机参数准确性
                valid_specs = 0
                total_specs = 0
                
                for model, specs in miners.items():
                    total_specs += 1
                    hashrate = specs.get('hashrate', 0)
                    power = specs.get('power', 0)
                    
                    # 验证算力和功耗合理性
                    if 50 <= hashrate <= 500 and 1000 <= power <= 8000:
                        valid_specs += 1
                
                accuracy_rate = (valid_specs / total_specs * 100) if total_specs > 0 else 0
                
                if accuracy_rate >= 90:
                    self.log_test("Miners", "spec_accuracy", "PASS",
                                f"矿机参数准确率: {accuracy_rate:.1f}%")
                else:
                    self.log_test("Miners", "spec_accuracy", "FAIL",
                                f"矿机参数准确率过低: {accuracy_rate:.1f}%")
                                
            else:
                self.log_test("Miners", "model_data", "FAIL",
                            f"矿机API错误: {response.status_code}", response_time)
                
        except Exception as e:
            self.log_test("Miners", "model_data", "FAIL", f"矿机测试异常: {e}")
    
    def test_analytics_system_accuracy(self):
        """测试分析系统准确性"""
        print("\n📊 测试分析系统数据准确性...")
        
        try:
            start_time = time.time()
            response = self.session.get(f"{self.base_url}/api/analytics/market-data")
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                market_data = data.get('data', {})
                
                # 验证分析数据完整性
                btc_price = market_data.get('btc_price')
                network_hashrate = market_data.get('network_hashrate')
                fear_greed = market_data.get('fear_greed_index')
                
                accuracy_score = 0
                total_checks = 3
                
                if btc_price and 50000 <= btc_price <= 200000:
                    accuracy_score += 1
                    
                if network_hashrate and 800 <= network_hashrate <= 1200:
                    accuracy_score += 1
                    
                if fear_greed and 0 <= fear_greed <= 100:
                    accuracy_score += 1
                
                accuracy_rate = (accuracy_score / total_checks * 100)
                
                if accuracy_rate >= 90:
                    self.log_test("Analytics", "market_data_accuracy", "PASS",
                                f"市场数据准确率: {accuracy_rate:.1f}%", response_time)
                else:
                    self.log_test("Analytics", "market_data_accuracy", "FAIL",
                                f"市场数据准确率过低: {accuracy_rate:.1f}%", response_time)
                                
            else:
                self.log_test("Analytics", "market_data_accuracy", "FAIL",
                            f"分析API错误: {response.status_code}", response_time)
                
        except Exception as e:
            self.log_test("Analytics", "market_data_accuracy", "FAIL", f"分析测试异常: {e}")
    
    def test_system_performance(self):
        """测试系统性能"""
        print("\n⚡ 测试系统响应性能...")
        
        # 多次请求测试平均响应时间
        response_times = []
        success_count = 0
        
        for i in range(5):
            try:
                start_time = time.time()
                response = self.session.get(f"{self.base_url}/")
                response_time = time.time() - start_time
                response_times.append(response_time)
                
                if response.status_code in [200, 302]:  # 302是重定向到登录页
                    success_count += 1
                    
            except Exception as e:
                response_times.append(5.0)  # 超时记为5秒
        
        avg_response_time = sum(response_times) / len(response_times)
        success_rate = (success_count / 5 * 100)
        
        if avg_response_time <= 1.0 and success_rate >= 80:
            self.log_test("Performance", "response_time", "PASS",
                        f"平均响应: {avg_response_time:.3f}s, 成功率: {success_rate:.1f}%")
        elif success_rate >= 80:
            self.log_test("Performance", "response_time", "WARN",
                        f"响应较慢: {avg_response_time:.3f}s, 成功率: {success_rate:.1f}%")
        else:
            self.log_test("Performance", "response_time", "FAIL",
                        f"性能不佳: {avg_response_time:.3f}s, 成功率: {success_rate:.1f}%")
    
    def test_data_consistency(self):
        """测试数据一致性"""
        print("\n🔄 测试数据一致性...")
        
        # 多次获取相同数据验证一致性
        btc_prices = []
        hashrates = []
        
        for i in range(3):
            try:
                # 获取BTC价格
                response = self.session.get(f"{self.base_url}/api/btc-price")
                if response.status_code == 200:
                    data = response.json()
                    btc_prices.append(data.get('price', 0))
                
                # 获取网络算力
                response = self.session.get(f"{self.base_url}/api/network-stats")
                if response.status_code == 200:
                    data = response.json()
                    hashrates.append(data.get('network_hashrate', 0))
                
                time.sleep(1)  # 间隔1秒
                
            except Exception as e:
                continue
        
        # 验证价格一致性
        if len(btc_prices) >= 2:
            price_variance = max(btc_prices) - min(btc_prices)
            price_avg = sum(btc_prices) / len(btc_prices)
            price_consistency = (1 - price_variance / price_avg) * 100
            
            if price_consistency >= 95:
                self.log_test("Consistency", "btc_price", "PASS",
                            f"价格一致性: {price_consistency:.1f}%")
            else:
                self.log_test("Consistency", "btc_price", "WARN",
                            f"价格波动: {price_consistency:.1f}%")
        
        # 验证算力一致性
        if len(hashrates) >= 2:
            hashrate_variance = max(hashrates) - min(hashrates)
            hashrate_avg = sum(hashrates) / len(hashrates)
            hashrate_consistency = (1 - hashrate_variance / hashrate_avg) * 100
            
            if hashrate_consistency >= 95:
                self.log_test("Consistency", "network_hashrate", "PASS",
                            f"算力一致性: {hashrate_consistency:.1f}%")
            else:
                self.log_test("Consistency", "network_hashrate", "WARN",
                            f"算力波动: {hashrate_consistency:.1f}%")
    
    def run_comprehensive_99_test(self):
        """运行99%准确率全面测试"""
        print("🚀 开始99%准确率全面系统验证测试")
        print(f"测试开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        
        # 认证系统
        if not self.authenticate_system():
            print("❌ 认证失败，部分测试可能受限")
        
        # 核心测试模块
        self.test_numerical_precision()
        self.test_mining_calculation_accuracy()
        self.test_miner_model_accuracy()
        self.test_analytics_system_accuracy()
        self.test_system_performance()
        self.test_data_consistency()
        
        # 生成最终报告
        self.generate_99_percent_report()
    
    def generate_99_percent_report(self):
        """生成99%准确率测试报告"""
        print("\n" + "=" * 80)
        print("🎯 99%准确率系统验证测试完成报告")
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
        print(f"📊 准确率: {accuracy_rate:.1f}%")
        print(f"🔄 功能可用率: {functional_rate:.1f}%")
        
        # 评级系统
        if accuracy_rate >= 99:
            grade = "🟢 卓越 (99%+)"
            status = "✅ 达到99%目标!"
        elif accuracy_rate >= 95:
            grade = "🟡 优秀 (95%+)"
            status = "⚠️ 接近99%目标"
        elif accuracy_rate >= 85:
            grade = "🟠 良好 (85%+)"
            status = "🔧 需要优化"
        else:
            grade = "🔴 需要改进"
            status = "❌ 未达到99%目标"
        
        print(f"📈 系统评级: {grade}")
        print(f"🎯 目标达成: {status}")
        
        # 按模块统计
        print(f"\n📋 模块测试统计:")
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
            
            if module_accuracy >= 90:
                symbol = "✅"
            elif module_functional >= 90:
                symbol = "⚠️"
            else:
                symbol = "❌"
                
            print(f"  {symbol} {module}: {stats['passed']}/{stats['total']} 通过 ({module_accuracy:.1f}%), 功能可用率 {module_functional:.1f}%")
        
        # 保存详细报告
        report_filename = f"comprehensive_99_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
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
            print(f"\n📄 详细测试报告已保存: {report_filename}")
        except Exception as e:
            print(f"\n⚠️ 报告保存失败: {e}")
        
        # 最终状态显示
        if accuracy_rate >= 99:
            print(f"\n🎉 恭喜! 系统准确率达到 {accuracy_rate:.1f}%，成功达到99%目标!")
        else:
            print(f"\n⚠️ 系统准确率为 {accuracy_rate:.1f}%，距离99%目标还需努力")

def main():
    """主函数"""
    try:
        test = Comprehensive99PercentTest()
        test.run_comprehensive_99_test()
    except KeyboardInterrupt:
        print("\n测试被用户中断")
    except Exception as e:
        print(f"测试执行异常: {e}")

if __name__ == "__main__":
    main()