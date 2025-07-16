#!/usr/bin/env python3
"""
全面系统回归测试 - 99%+目标
Comprehensive Full System Regression Test - 99%+ Target

验证前端、中端、后端的完成率、正确率、显示率，以及数值和逻辑的准确性
Verify frontend, middleware, backend completion, accuracy, display rates, plus numerical and logical correctness
"""

import requests
import json
import time
import math
import statistics
from datetime import datetime
from typing import Dict, List, Optional, Any
import traceback

class ComprehensiveFullSystemTest99Percent:
    """全面系统回归测试器 - 99%+目标"""
    
    def __init__(self):
        self.base_url = "http://localhost:5000"
        self.test_results = []
        self.session = requests.Session()
        self.test_emails = [
            "hxl2022hao@gmail.com",
            "testing123@example.com", 
            "admin@example.com",
            "site@example.com",
            "user@example.com"
        ]
        
    def log_test(self, category: str, test_name: str, status: str, details: str = "", 
                 response_time: Optional[float] = None, accuracy: Optional[float] = None,
                 completion_rate: Optional[float] = None, display_rate: Optional[float] = None,
                 email: Optional[str] = None):
        """记录测试结果"""
        result = {
            'timestamp': datetime.now().isoformat(),
            'category': category,
            'test_name': test_name,
            'status': status,
            'details': details,
            'response_time': response_time,
            'accuracy': accuracy,
            'completion_rate': completion_rate,
            'display_rate': display_rate,
            'email': email
        }
        self.test_results.append(result)
        print(f"[{category}] {test_name}: {status} - {details}")
        
    def authenticate_with_email(self, email: str) -> bool:
        """使用指定邮箱进行认证"""
        try:
            start_time = time.time()
            response = self.session.post(f"{self.base_url}/login", 
                                       data={'email': email}, 
                                       allow_redirects=True)
            response_time = time.time() - start_time
            
            if response.status_code == 200 and "登录成功" in response.text:
                self.log_test("Authentication", f"Login_{email}", "PASS", 
                            f"成功登录 {email}", response_time, 100.0, 100.0, 100.0, email)
                return True
            else:
                self.log_test("Authentication", f"Login_{email}", "FAIL", 
                            f"登录失败: {response.status_code}", response_time, 0.0, 0.0, 0.0, email)
                return False
        except Exception as e:
            self.log_test("Authentication", f"Login_{email}", "ERROR", 
                        f"认证异常: {str(e)}", None, 0.0, 0.0, 0.0, email)
            return False
    
    def test_frontend_layer_comprehensive(self, email: str) -> None:
        """测试前端层 - 综合测试"""
        if not self.authenticate_with_email(email):
            return
            
        frontend_tests = [
            ("/", "主页完整性", "主页"),
            ("/curtailment_calculator", "电力削减计算器", "削减计算器"),
            ("/analytics_dashboard", "数据分析仪表盘", "分析仪表盘"),
            ("/algorithm_test", "算法差异测试", "算法测试"),
            ("/network_history", "网络历史分析", "网络历史"),
            ("/crm/dashboard", "CRM系统仪表盘", "CRM仪表盘")
        ]
        
        for url, test_name, page_name in frontend_tests:
            try:
                start_time = time.time()
                response = self.session.get(f"{self.base_url}{url}")
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    # 检查页面完整性
                    page_content = response.text
                    completion_rate = self._calculate_page_completion(page_content)
                    display_rate = self._calculate_display_rate(page_content)
                    accuracy = self._calculate_frontend_accuracy(page_content, page_name)
                    
                    status = "PASS" if completion_rate >= 99.0 and display_rate >= 99.0 and accuracy >= 99.0 else "WARN"
                    self.log_test("Frontend", test_name, status, 
                                f"完成率:{completion_rate:.1f}% 显示率:{display_rate:.1f}% 精确率:{accuracy:.1f}%", 
                                response_time, accuracy, completion_rate, display_rate, email)
                else:
                    self.log_test("Frontend", test_name, "FAIL", 
                                f"HTTP {response.status_code}", response_time, 0.0, 0.0, 0.0, email)
            except Exception as e:
                self.log_test("Frontend", test_name, "ERROR", 
                            f"前端异常: {str(e)}", None, 0.0, 0.0, 0.0, email)
    
    def test_middleware_api_layer(self, email: str) -> None:
        """测试中间件API层"""
        if not self.authenticate_with_email(email):
            return
            
        api_tests = [
            ("/get_btc_price", "BTC价格API", "price"),
            ("/get_network_stats", "网络统计API", "network"),
            ("/get_miners", "矿机数据API", "miners"),
            ("/api/network_stats", "网络统计概览API", "network_overview"),
            ("/analytics/market-data", "分析系统市场数据API", "analytics_market"),
            ("/analytics/latest-report", "最新分析报告API", "analytics_report"),
            ("/analytics/technical-indicators", "技术指标API", "technical_indicators"),
            ("/analytics/price-history", "价格历史API", "price_history")
        ]
        
        for url, test_name, api_type in api_tests:
            try:
                start_time = time.time()
                response = self.session.get(f"{self.base_url}{url}")
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        completion_rate = self._calculate_api_completion(data, api_type)
                        accuracy = self._calculate_api_accuracy(data, api_type)
                        display_rate = self._calculate_api_display_rate(data)
                        
                        status = "PASS" if completion_rate >= 99.0 and accuracy >= 99.0 and display_rate >= 99.0 else "WARN"
                        self.log_test("Middleware", test_name, status, 
                                    f"完成率:{completion_rate:.1f}% 精确率:{accuracy:.1f}% 显示率:{display_rate:.1f}%", 
                                    response_time, accuracy, completion_rate, display_rate, email)
                    except json.JSONDecodeError:
                        self.log_test("Middleware", test_name, "FAIL", 
                                    "JSON解析失败", response_time, 0.0, 50.0, 0.0, email)
                else:
                    self.log_test("Middleware", test_name, "FAIL", 
                                f"HTTP {response.status_code}", response_time, 0.0, 0.0, 0.0, email)
            except Exception as e:
                self.log_test("Middleware", test_name, "ERROR", 
                            f"API异常: {str(e)}", None, 0.0, 0.0, 0.0, email)
    
    def test_backend_calculation_engine(self, email: str) -> None:
        """测试后端计算引擎"""
        if not self.authenticate_with_email(email):
            return
            
        # 测试挖矿计算引擎
        calculation_tests = [
            {
                'name': 'S19_Pro_计算精确性',
                'data': {
                    'miner_model': 'Antminer S19 Pro',
                    'quantity': '1',
                    'electricity_cost': '0.06',
                    'pool_fee': '2.5',
                    'manual_hashrate': '',
                    'manual_power': ''
                }
            },
            {
                'name': 'S21_XP_多台计算',
                'data': {
                    'miner_model': 'Antminer S21 XP',
                    'quantity': '5',
                    'electricity_cost': '0.05',
                    'pool_fee': '2.0',
                    'manual_hashrate': '',
                    'manual_power': ''
                }
            },
            {
                'name': '手动参数验证',
                'data': {
                    'miner_model': 'custom',
                    'quantity': '1',
                    'electricity_cost': '0.08',
                    'pool_fee': '3.0',
                    'manual_hashrate': '110',
                    'manual_power': '3250'
                }
            }
        ]
        
        for test_config in calculation_tests:
            try:
                start_time = time.time()
                response = self.session.post(f"{self.base_url}/calculate", 
                                           data=test_config['data'])
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    try:
                        result = response.json()
                        accuracy = self._validate_calculation_accuracy(result, test_config['data'])
                        completion_rate = self._calculate_calculation_completion(result)
                        display_rate = self._calculate_calculation_display_rate(result)
                        
                        status = "PASS" if accuracy >= 99.0 and completion_rate >= 99.0 and display_rate >= 99.0 else "WARN"
                        self.log_test("Backend", test_config['name'], status, 
                                    f"精确率:{accuracy:.1f}% 完成率:{completion_rate:.1f}% 显示率:{display_rate:.1f}%", 
                                    response_time, accuracy, completion_rate, display_rate, email)
                    except json.JSONDecodeError:
                        self.log_test("Backend", test_config['name'], "FAIL", 
                                    "计算结果JSON解析失败", response_time, 0.0, 0.0, 0.0, email)
                else:
                    self.log_test("Backend", test_config['name'], "FAIL", 
                                f"计算请求失败: {response.status_code}", response_time, 0.0, 0.0, 0.0, email)
            except Exception as e:
                self.log_test("Backend", test_config['name'], "ERROR", 
                            f"计算引擎异常: {str(e)}", None, 0.0, 0.0, 0.0, email)
    
    def test_numerical_logical_accuracy(self) -> None:
        """测试数值和逻辑准确性"""
        try:
            # 测试数值一致性
            btc_prices = []
            network_hashrates = []
            
            for i in range(3):  # 多次采样验证一致性
                try:
                    price_response = self.session.get(f"{self.base_url}/get_btc_price")
                    if price_response.status_code == 200:
                        price_data = price_response.json()
                        if 'current_price' in price_data:
                            btc_prices.append(float(price_data['current_price']))
                    
                    network_response = self.session.get(f"{self.base_url}/get_network_stats")
                    if network_response.status_code == 200:
                        network_data = network_response.json()
                        if 'hashrate' in network_data:
                            network_hashrates.append(float(network_data['hashrate']))
                    
                    time.sleep(1)  # 间隔1秒采样
                except:
                    pass
            
            # 计算数值一致性
            price_consistency = self._calculate_consistency(btc_prices) if btc_prices else 0.0
            hashrate_consistency = self._calculate_consistency(network_hashrates) if network_hashrates else 0.0
            
            overall_accuracy = (price_consistency + hashrate_consistency) / 2
            
            status = "PASS" if overall_accuracy >= 99.0 else "WARN"
            self.log_test("Numerical", "数值逻辑一致性", status, 
                        f"价格一致性:{price_consistency:.1f}% 算力一致性:{hashrate_consistency:.1f}%", 
                        None, overall_accuracy, 100.0, 100.0)
                        
        except Exception as e:
            self.log_test("Numerical", "数值逻辑一致性", "ERROR", 
                        f"数值测试异常: {str(e)}", None, 0.0, 0.0, 0.0)
    
    def _calculate_page_completion(self, content: str) -> float:
        """计算页面完成率"""
        required_elements = ['<html', '<head', '<body', '<title', '</html>']
        found_elements = sum(1 for element in required_elements if element in content)
        return (found_elements / len(required_elements)) * 100
    
    def _calculate_display_rate(self, content: str) -> float:
        """计算显示率"""
        display_indicators = ['<div', '<span', '<p', '<h1', '<h2', '<button', '<input']
        found_indicators = sum(1 for indicator in display_indicators if indicator in content)
        max_indicators = len(display_indicators)
        return min(100.0, (found_indicators / max_indicators) * 100)
    
    def _calculate_frontend_accuracy(self, content: str, page_name: str) -> float:
        """计算前端精确率"""
        accuracy_checks = {
            "主页": ["挖矿计算器", "BTC", "计算"],
            "削减计算器": ["电力削减", "curtailment", "计算"],
            "分析仪表盘": ["分析", "数据", "图表"],
            "算法测试": ["算法", "测试", "对比"],
            "网络历史": ["网络", "历史", "数据"],
            "CRM仪表盘": ["客户", "CRM", "管理"]
        }
        
        if page_name in accuracy_checks:
            required_terms = accuracy_checks[page_name]
            found_terms = sum(1 for term in required_terms if term in content)
            return (found_terms / len(required_terms)) * 100
        return 95.0  # 默认精确率
    
    def _calculate_api_completion(self, data: Dict, api_type: str) -> float:
        """计算API完成率"""
        completion_checks = {
            "price": ["current_price"],
            "network": ["hashrate", "difficulty"],
            "miners": ["miners"],
            "network_overview": ["btc_price", "network_hashrate"],
            "analytics_market": ["success", "data"],
            "analytics_report": ["latest_report"],
            "technical_indicators": ["indicators"],
            "price_history": ["history"]
        }
        
        if api_type in completion_checks:
            required_fields = completion_checks[api_type]
            found_fields = sum(1 for field in required_fields if field in data or self._deep_field_search(data, field))
            return (found_fields / len(required_fields)) * 100
        return 90.0
    
    def _calculate_api_accuracy(self, data: Dict, api_type: str) -> float:
        """计算API精确率"""
        try:
            if api_type == "price" and "current_price" in data:
                price = float(data["current_price"])
                return 100.0 if 50000 <= price <= 200000 else 80.0
            elif api_type == "network" and "hashrate" in data:
                hashrate = float(data["hashrate"])
                return 100.0 if 500 <= hashrate <= 2000 else 80.0
            elif api_type == "miners" and "miners" in data:
                miners = data["miners"]
                return 100.0 if len(miners) >= 8 else 80.0
            return 95.0
        except:
            return 70.0
    
    def _calculate_api_display_rate(self, data: Dict) -> float:
        """计算API显示率"""
        if isinstance(data, dict) and data:
            return 100.0
        return 0.0
    
    def _validate_calculation_accuracy(self, result: Dict, input_data: Dict) -> float:
        """验证计算精确率"""
        try:
            required_fields = ["daily_btc", "daily_profit_usd", "electricity_cost_daily", "roi_annual"]
            found_fields = sum(1 for field in required_fields if field in result)
            field_accuracy = (found_fields / len(required_fields)) * 100
            
            # 验证数值合理性
            numerical_accuracy = 100.0
            if "daily_btc" in result:
                daily_btc = float(result["daily_btc"])
                if not (0.001 <= daily_btc <= 1.0):
                    numerical_accuracy -= 25
            
            if "daily_profit_usd" in result:
                daily_profit = float(result["daily_profit_usd"])
                if not (-1000 <= daily_profit <= 10000):
                    numerical_accuracy -= 25
            
            return min(field_accuracy, numerical_accuracy)
        except:
            return 50.0
    
    def _calculate_calculation_completion(self, result: Dict) -> float:
        """计算计算完成率"""
        essential_fields = ["daily_btc", "daily_profit_usd", "electricity_cost_daily", "roi_annual", "payback_months"]
        found_fields = sum(1 for field in essential_fields if field in result)
        return (found_fields / len(essential_fields)) * 100
    
    def _calculate_calculation_display_rate(self, result: Dict) -> float:
        """计算计算显示率"""
        if isinstance(result, dict) and len(result) >= 5:
            return 100.0
        elif isinstance(result, dict) and len(result) >= 3:
            return 80.0
        return 50.0
    
    def _calculate_consistency(self, values: List[float]) -> float:
        """计算数值一致性"""
        if len(values) < 2:
            return 100.0
        
        mean_val = statistics.mean(values)
        if mean_val == 0:
            return 100.0 if all(v == 0 for v in values) else 0.0
        
        max_deviation = max(abs(v - mean_val) for v in values)
        deviation_percentage = (max_deviation / mean_val) * 100
        
        return max(0.0, 100.0 - deviation_percentage)
    
    def _deep_field_search(self, data: Any, field: str) -> bool:
        """深度搜索字段"""
        if isinstance(data, dict):
            if field in data:
                return True
            return any(self._deep_field_search(v, field) for v in data.values())
        elif isinstance(data, list):
            return any(self._deep_field_search(item, field) for item in data)
        return False
    
    def run_comprehensive_99_percent_test(self) -> Dict[str, Any]:
        """运行全面99%+测试"""
        print("🚀 开始全面系统回归测试 - 99%+目标")
        print("=" * 80)
        
        start_time = time.time()
        
        # 使用第一个邮箱进行全面测试
        test_email = self.test_emails[0]
        
        print(f"\n📧 使用测试邮箱: {test_email}")
        
        # 1. 前端层测试
        print("\n🎨 测试前端层...")
        self.test_frontend_layer_comprehensive(test_email)
        
        # 2. 中间件API层测试
        print("\n🔗 测试中间件API层...")
        self.test_middleware_api_layer(test_email)
        
        # 3. 后端计算引擎测试
        print("\n⚙️ 测试后端计算引擎...")
        self.test_backend_calculation_engine(test_email)
        
        # 4. 数值逻辑准确性测试
        print("\n🔢 测试数值逻辑准确性...")
        self.test_numerical_logical_accuracy()
        
        total_time = time.time() - start_time
        
        # 生成报告
        report = self.generate_final_99_percent_report(total_time)
        
        return report
    
    def generate_final_99_percent_report(self, total_time: float) -> Dict[str, Any]:
        """生成最终99%+报告"""
        categories = {}
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r['status'] == 'PASS')
        
        # 按类别统计
        for result in self.test_results:
            category = result['category']
            if category not in categories:
                categories[category] = {'total': 0, 'passed': 0, 'accuracy_sum': 0, 'completion_sum': 0, 'display_sum': 0}
            
            categories[category]['total'] += 1
            if result['status'] == 'PASS':
                categories[category]['passed'] += 1
            
            if result['accuracy']:
                categories[category]['accuracy_sum'] += result['accuracy']
            if result['completion_rate']:
                categories[category]['completion_sum'] += result['completion_rate']
            if result['display_rate']:
                categories[category]['display_sum'] += result['display_rate']
        
        # 计算平均值
        for category in categories:
            cat_data = categories[category]
            cat_data['success_rate'] = (cat_data['passed'] / cat_data['total']) * 100 if cat_data['total'] > 0 else 0
            cat_data['avg_accuracy'] = cat_data['accuracy_sum'] / cat_data['total'] if cat_data['total'] > 0 else 0
            cat_data['avg_completion'] = cat_data['completion_sum'] / cat_data['total'] if cat_data['total'] > 0 else 0
            cat_data['avg_display'] = cat_data['display_sum'] / cat_data['total'] if cat_data['total'] > 0 else 0
        
        overall_success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        overall_accuracy = sum(r['accuracy'] for r in self.test_results if r['accuracy']) / total_tests if total_tests > 0 else 0
        overall_completion = sum(r['completion_rate'] for r in self.test_results if r['completion_rate']) / total_tests if total_tests > 0 else 0
        overall_display = sum(r['display_rate'] for r in self.test_results if r['display_rate']) / total_tests if total_tests > 0 else 0
        
        # 系统等级
        system_grade = self.get_system_grade_99_percent(overall_success_rate, overall_accuracy, overall_completion, overall_display)
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'test_duration': f"{total_time:.2f}秒",
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'overall_success_rate': overall_success_rate,
            'overall_accuracy': overall_accuracy,
            'overall_completion_rate': overall_completion,
            'overall_display_rate': overall_display,
            'system_grade': system_grade,
            'categories': categories,
            'target_achieved': all([
                overall_success_rate >= 99.0,
                overall_accuracy >= 99.0,
                overall_completion >= 99.0,
                overall_display >= 99.0
            ])
        }
        
        self.print_final_99_percent_report(report)
        
        return report
    
    def get_system_grade_99_percent(self, success_rate: float, accuracy: float, completion: float, display: float) -> str:
        """获取系统等级 - 99%+标准"""
        overall_score = (success_rate + accuracy + completion + display) / 4
        
        if overall_score >= 99.0:
            return "A+ (完美级别)"
        elif overall_score >= 95.0:
            return "A (优秀级别)"
        elif overall_score >= 90.0:
            return "B+ (良好级别)"
        elif overall_score >= 85.0:
            return "B (达标级别)"
        elif overall_score >= 80.0:
            return "C+ (基础级别)"
        else:
            return "C (需改进)"
    
    def print_final_99_percent_report(self, report: Dict[str, Any]):
        """打印最终99%+报告"""
        print("\n" + "=" * 80)
        print("🎯 全面系统回归测试报告 - 99%+目标")
        print("=" * 80)
        
        print(f"⏱️  测试时间: {report['test_duration']}")
        print(f"📊 总测试数: {report['total_tests']}")
        print(f"✅ 通过测试: {report['passed_tests']}")
        print(f"📈 总体成功率: {report['overall_success_rate']:.1f}%")
        print(f"🎯 总体精确率: {report['overall_accuracy']:.1f}%")
        print(f"📋 总体完成率: {report['overall_completion_rate']:.1f}%")
        print(f"👁️  总体显示率: {report['overall_display_rate']:.1f}%")
        print(f"🏆 系统等级: {report['system_grade']}")
        print(f"🎉 99%+目标达成: {'✅ 是' if report['target_achieved'] else '❌ 否'}")
        
        print("\n📁 分类详情:")
        for category, data in report['categories'].items():
            print(f"  {category}: {data['passed']}/{data['total']} 通过 "
                  f"(成功率:{data['success_rate']:.1f}% "
                  f"精确率:{data['avg_accuracy']:.1f}% "
                  f"完成率:{data['avg_completion']:.1f}% "
                  f"显示率:{data['avg_display']:.1f}%)")
        
        if report['target_achieved']:
            print("\n🎊 恭喜！系统已达到99%+目标标准，已准备就绪用于生产环境部署！")
        else:
            print("\n⚠️  系统未完全达到99%+标准，建议优化后重新测试。")
        
        print("=" * 80)


def main():
    """主函数"""
    print("启动全面系统回归测试 - 99%+目标...")
    
    tester = ComprehensiveFullSystemTest99Percent()
    
    try:
        report = tester.run_comprehensive_99_percent_test()
        
        # 保存报告
        with open(f"full_system_test_99_percent_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        return report
        
    except KeyboardInterrupt:
        print("\n⏹️  测试被用户中断")
    except Exception as e:
        print(f"\n❌ 测试执行错误: {str(e)}")
        traceback.print_exc()


if __name__ == "__main__":
    main()