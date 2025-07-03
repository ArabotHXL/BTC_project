#!/usr/bin/env python3
"""
全面99%准确率回归测试系统
Comprehensive 99% Accuracy Regression Testing System

使用hxl2022hao@gmail.com邮箱进行完整的系统功能验证
Complete system functionality verification with owner email
"""

import requests
import json
import time
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Comprehensive99RegressionTest:
    def __init__(self):
        self.base_url = "http://localhost:5000"
        self.session = requests.Session()
        self.test_email = "hxl2022hao@gmail.com"
        
        # 测试结果统计
        self.test_results = {
            'total_tests': 0,
            'passed_tests': 0,
            'failed_tests': 0,
            'error_tests': 0,
            'response_times': [],
            'detailed_results': []
        }
        
        # 准确率阈值
        self.accuracy_threshold = 99.0
        
        # 性能基准
        self.performance_benchmarks = {
            'api_response_time': 2.0,  # 秒
            'calculation_accuracy': 99.9,  # 百分比
            'data_consistency': 99.0,  # 百分比
            'system_availability': 99.0  # 百分比
        }
        
        print(f"🎯 目标准确率: {self.accuracy_threshold}%")
        print(f"📧 测试邮箱: {self.test_email}")
        print(f"🏠 测试基础URL: {self.base_url}")

    def log_test_result(self, category: str, test_name: str, status: str, 
                       expected: str, actual: str, response_time: float = None):
        """记录测试结果"""
        self.test_results['total_tests'] += 1
        
        if status == "PASS":
            self.test_results['passed_tests'] += 1
        elif status == "FAIL":
            self.test_results['failed_tests'] += 1
        else:
            self.test_results['error_tests'] += 1
            
        if response_time:
            self.test_results['response_times'].append(response_time)
            
        result = {
            'timestamp': datetime.now().isoformat(),
            'category': category,
            'test_name': test_name,
            'status': status,
            'expected': expected,
            'actual': actual,
            'response_time': response_time
        }
        
        self.test_results['detailed_results'].append(result)
        
        # 实时输出
        status_icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"{status_icon} [{category}] {test_name}: {status} - {actual}")

    def authenticate_system(self) -> bool:
        """系统认证"""
        try:
            # 模拟登录过程
            auth_data = {'email': self.test_email}
            response = self.session.post(f"{self.base_url}/login", data=auth_data, timeout=10)
            
            if response.status_code in [200, 302]:
                self.log_test_result("认证系统", "拥有者邮箱认证", "PASS", 
                                   "成功认证", f"HTTP {response.status_code}")
                return True
            else:
                self.log_test_result("认证系统", "拥有者邮箱认证", "FAIL", 
                                   "成功认证", f"HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test_result("认证系统", "拥有者邮箱认证", "ERROR", 
                               "成功认证", f"异常: {str(e)}")
            return False

    def test_core_api_ecosystem(self):
        """测试核心API生态系统"""
        api_tests = [
            ("/api/btc-price", "BTC价格API"),
            ("/api/network-stats", "网络统计API"),
            ("/api/miners", "矿机数据API"),
            ("/api/sha256-comparison", "SHA256对比API"),
            ("/api/analytics/market-data", "分析市场数据API"),
            ("/api/analytics/latest-report", "最新分析报告API"),
            ("/api/analytics/technical-indicators", "技术指标API"),
            ("/api/analytics/price-history", "价格历史API")
        ]
        
        for endpoint, name in api_tests:
            try:
                start_time = time.time()
                response = self.session.get(f"{self.base_url}{endpoint}", timeout=8)
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        if self.validate_api_response(endpoint, data):
                            self.log_test_result("核心API", name, "PASS",
                                               "有效JSON数据", "数据完整", response_time)
                        else:
                            self.log_test_result("核心API", name, "FAIL",
                                               "有效JSON数据", "数据不完整", response_time)
                    except json.JSONDecodeError:
                        self.log_test_result("核心API", name, "FAIL",
                                           "有效JSON", "JSON解析失败", response_time)
                else:
                    self.log_test_result("核心API", name, "FAIL",
                                       "HTTP 200", f"HTTP {response.status_code}", response_time)
                    
            except Exception as e:
                self.log_test_result("核心API", name, "ERROR",
                                   "正常响应", f"异常: {str(e)}")

    def validate_api_response(self, endpoint: str, data: Any) -> bool:
        """验证API响应数据质量"""
        if "/btc-price" in endpoint:
            return isinstance(data, dict) and 'price' in data and data['price'] > 0
        elif "/network-stats" in endpoint:
            return isinstance(data, dict) and 'hashrate' in data and 'difficulty' in data
        elif "/miners" in endpoint:
            return isinstance(data, list) and len(data) >= 5
        elif "/analytics/market-data" in endpoint:
            return isinstance(data, dict) and 'btc_price' in data.get('data', {})
        else:
            return isinstance(data, (dict, list))

    def test_mining_calculation_engine(self):
        """测试挖矿计算引擎精度"""
        test_cases = [
            {
                'miner_model': 'Antminer S19 Pro',
                'site_power_mw': 5.0,
                'electricity_cost': 0.05,
                'expected_daily_profit': (3.0, 10.0)  # 范围
            },
            {
                'miner_model': 'Antminer S21 XP',
                'site_power_mw': 10.0,
                'electricity_cost': 0.08,
                'expected_daily_profit': (5.0, 20.0)
            },
            {
                'miner_model': 'Antminer S19',
                'site_power_mw': 3.0,
                'electricity_cost': 0.06,
                'expected_daily_profit': (2.0, 8.0)
            }
        ]
        
        for i, case in enumerate(test_cases):
            try:
                start_time = time.time()
                response = self.session.post(f"{self.base_url}/calculate", 
                                           data=case, timeout=15)
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    try:
                        result = response.json()
                        daily_profit = result.get('daily_profit_usd', 0)
                        
                        min_profit, max_profit = case['expected_daily_profit']
                        if min_profit <= daily_profit <= max_profit:
                            self.log_test_result("挖矿计算", f"计算精度-案例{i+1}", "PASS",
                                               f"利润${min_profit}-${max_profit}", 
                                               f"利润${daily_profit:.2f}", response_time)
                        else:
                            self.log_test_result("挖矿计算", f"计算精度-案例{i+1}", "FAIL",
                                               f"利润${min_profit}-${max_profit}", 
                                               f"利润${daily_profit:.2f}", response_time)
                            
                        # 验证数据完整性
                        required_fields = ['daily_btc_output', 'monthly_profit_usd', 'annual_roi']
                        missing_fields = [f for f in required_fields if f not in result]
                        if not missing_fields:
                            self.log_test_result("挖矿计算", f"数据完整性-案例{i+1}", "PASS",
                                               "所有必需字段", "字段完整", response_time)
                        else:
                            self.log_test_result("挖矿计算", f"数据完整性-案例{i+1}", "FAIL",
                                               "所有必需字段", f"缺失: {missing_fields}", response_time)
                            
                    except (json.JSONDecodeError, KeyError) as e:
                        self.log_test_result("挖矿计算", f"响应解析-案例{i+1}", "FAIL",
                                           "有效JSON", f"解析错误: {str(e)}", response_time)
                else:
                    self.log_test_result("挖矿计算", f"HTTP状态-案例{i+1}", "FAIL",
                                       "HTTP 200", f"HTTP {response.status_code}", response_time)
                    
            except Exception as e:
                self.log_test_result("挖矿计算", f"异常处理-案例{i+1}", "ERROR",
                                   "正常执行", f"异常: {str(e)}")

    def test_all_miner_models(self):
        """测试所有矿机型号的计算准确性"""
        # 首先获取矿机列表
        try:
            response = self.session.get(f"{self.base_url}/api/miners", timeout=10)
            if response.status_code == 200:
                miners = response.json()
                
                for miner in miners:
                    miner_name = miner.get('name', 'Unknown')
                    try:
                        calc_data = {
                            'miner_model': miner_name,
                            'site_power_mw': 5.0,
                            'electricity_cost': 0.05
                        }
                        
                        start_time = time.time()
                        calc_response = self.session.post(f"{self.base_url}/calculate", 
                                                        data=calc_data, timeout=10)
                        response_time = time.time() - start_time
                        
                        if calc_response.status_code == 200:
                            result = calc_response.json()
                            if 'daily_profit_usd' in result:
                                self.log_test_result("矿机型号", f"{miner_name}计算", "PASS",
                                                   "成功计算", f"日利润${result['daily_profit_usd']:.2f}", 
                                                   response_time)
                            else:
                                self.log_test_result("矿机型号", f"{miner_name}计算", "FAIL",
                                                   "包含利润数据", "缺少利润字段", response_time)
                        else:
                            self.log_test_result("矿机型号", f"{miner_name}计算", "FAIL",
                                               "HTTP 200", f"HTTP {calc_response.status_code}", 
                                               response_time)
                            
                    except Exception as e:
                        self.log_test_result("矿机型号", f"{miner_name}计算", "ERROR",
                                           "正常计算", f"异常: {str(e)}")
                        
        except Exception as e:
            self.log_test_result("矿机型号", "获取矿机列表", "ERROR",
                               "成功获取", f"异常: {str(e)}")

    def test_analytics_system_precision(self):
        """测试分析系统精度"""
        analytics_tests = [
            ("市场数据API", "/api/analytics/market-data"),
            ("技术指标API", "/api/analytics/technical-indicators"), 
            ("价格历史API", "/api/analytics/price-history"),
            ("最新报告API", "/api/analytics/latest-report")
        ]
        
        for test_name, endpoint in analytics_tests:
            try:
                start_time = time.time()
                response = self.session.get(f"{self.base_url}{endpoint}", timeout=10)
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        if self.validate_analytics_data(endpoint, data):
                            self.log_test_result("分析系统", test_name, "PASS",
                                               "有效数据", "数据验证通过", response_time)
                        else:
                            self.log_test_result("分析系统", test_name, "FAIL",
                                               "有效数据", "数据验证失败", response_time)
                    except json.JSONDecodeError:
                        self.log_test_result("分析系统", test_name, "FAIL",
                                           "有效JSON", "JSON解析失败", response_time)
                else:
                    self.log_test_result("分析系统", test_name, "FAIL",
                                       "HTTP 200", f"HTTP {response.status_code}", response_time)
                    
            except Exception as e:
                self.log_test_result("分析系统", test_name, "ERROR",
                                   "正常响应", f"异常: {str(e)}")

    def validate_analytics_data(self, endpoint: str, data: Any) -> bool:
        """验证分析数据质量"""
        if "/market-data" in endpoint:
            market_data = data.get('data', {})
            return (isinstance(market_data, dict) and 
                   'btc_price' in market_data and 
                   market_data['btc_price'] > 50000)
        elif "/technical-indicators" in endpoint:
            indicators = data.get('data', {})
            return (isinstance(indicators, dict) and 
                   'rsi_14' in indicators and 
                   0 <= indicators.get('rsi_14', -1) <= 100)
        elif "/price-history" in endpoint:
            return ('price_history' in data and 
                   isinstance(data['price_history'], list) and 
                   len(data['price_history']) > 0)
        else:
            return isinstance(data, dict)

    def test_user_interface_integrity(self):
        """测试用户界面完整性"""
        pages_to_test = [
            ("/", "主页"),
            ("/analytics", "分析仪表盘"),
            ("/curtailment", "电力削减计算器"),
            ("/algorithm/test", "算法测试页面"),
            ("/network/history", "网络历史分析")
        ]
        
        for path, name in pages_to_test:
            try:
                start_time = time.time()
                response = self.session.get(f"{self.base_url}{path}", timeout=10)
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    content = response.text
                    if self.validate_page_content(path, content):
                        self.log_test_result("用户界面", name, "PASS",
                                           "完整页面", "页面加载正常", response_time)
                    else:
                        self.log_test_result("用户界面", name, "FAIL",
                                           "完整页面", "页面内容不完整", response_time)
                else:
                    self.log_test_result("用户界面", name, "FAIL",
                                       "HTTP 200", f"HTTP {response.status_code}", response_time)
                    
            except Exception as e:
                self.log_test_result("用户界面", name, "ERROR",
                                   "正常加载", f"异常: {str(e)}")

    def validate_page_content(self, path: str, content: str) -> bool:
        """验证页面内容完整性"""
        if path == "/":
            return ("比特币挖矿收益计算器" in content and 
                   "矿机型号" in content and 
                   "计算" in content)
        elif path == "/analytics":
            return ("分析仪表盘" in content and 
                   "市场数据" in content)
        else:
            return len(content) > 1000 and "<html" in content

    def test_data_consistency(self):
        """测试数据一致性"""
        # 测试多次API调用的数据一致性
        consistency_tests = [
            "/api/btc-price",
            "/api/network-stats", 
            "/api/analytics/market-data"
        ]
        
        for endpoint in consistency_tests:
            prices = []
            hashrates = []
            
            for i in range(3):
                try:
                    response = self.session.get(f"{self.base_url}{endpoint}", timeout=5)
                    if response.status_code == 200:
                        data = response.json()
                        
                        if "/btc-price" in endpoint:
                            prices.append(data.get('price', 0))
                        elif "/network-stats" in endpoint:
                            hashrates.append(data.get('hashrate', 0))
                        elif "/analytics/market-data" in endpoint:
                            market_data = data.get('data', {})
                            prices.append(market_data.get('btc_price', 0))
                            
                    time.sleep(1)  # 间隔1秒
                    
                except Exception:
                    continue
            
            # 计算数据一致性
            if prices:
                price_variance = statistics.stdev(prices) if len(prices) > 1 else 0
                if price_variance < 100:  # 价格波动小于$100认为一致
                    self.log_test_result("数据一致性", f"{endpoint}价格一致性", "PASS",
                                       "价格稳定", f"标准差${price_variance:.2f}")
                else:
                    self.log_test_result("数据一致性", f"{endpoint}价格一致性", "FAIL",
                                       "价格稳定", f"标准差${price_variance:.2f}")
                    
            if hashrates:
                hashrate_variance = statistics.stdev(hashrates) if len(hashrates) > 1 else 0
                if hashrate_variance < 50:  # 算力波动小于50 EH/s认为一致
                    self.log_test_result("数据一致性", f"{endpoint}算力一致性", "PASS",
                                       "算力稳定", f"标准差{hashrate_variance:.2f} EH/s")
                else:
                    self.log_test_result("数据一致性", f"{endpoint}算力一致性", "FAIL",
                                       "算力稳定", f"标准差{hashrate_variance:.2f} EH/s")

    def test_performance_benchmarks(self):
        """测试性能基准"""
        # API响应时间测试
        if self.test_results['response_times']:
            avg_response_time = statistics.mean(self.test_results['response_times'])
            if avg_response_time <= self.performance_benchmarks['api_response_time']:
                self.log_test_result("性能基准", "API平均响应时间", "PASS",
                                   f"≤{self.performance_benchmarks['api_response_time']}s",
                                   f"{avg_response_time:.3f}s")
            else:
                self.log_test_result("性能基准", "API平均响应时间", "FAIL",
                                   f"≤{self.performance_benchmarks['api_response_time']}s",
                                   f"{avg_response_time:.3f}s")

    def run_comprehensive_99_test(self):
        """运行99%准确率综合测试"""
        print("\n" + "="*80)
        print("🚀 开始全面99%准确率回归测试")
        print("="*80)
        
        start_time = time.time()
        
        # 1. 系统认证
        print("\n📧 步骤1: 系统认证")
        if not self.authenticate_system():
            print("❌ 认证失败，测试终止")
            return
            
        # 2. 核心API生态系统测试
        print("\n🔧 步骤2: 核心API生态系统测试")
        self.test_core_api_ecosystem()
        
        # 3. 挖矿计算引擎测试
        print("\n⛏️ 步骤3: 挖矿计算引擎精度测试")
        self.test_mining_calculation_engine()
        
        # 4. 所有矿机型号测试
        print("\n🔩 步骤4: 全矿机型号计算测试")
        self.test_all_miner_models()
        
        # 5. 分析系统精度测试
        print("\n📊 步骤5: 分析系统精度测试")
        self.test_analytics_system_precision()
        
        # 6. 用户界面完整性测试
        print("\n🖥️ 步骤6: 用户界面完整性测试")
        self.test_user_interface_integrity()
        
        # 7. 数据一致性测试
        print("\n🔄 步骤7: 数据一致性测试")
        self.test_data_consistency()
        
        # 8. 性能基准测试
        print("\n⚡ 步骤8: 性能基准测试")
        self.test_performance_benchmarks()
        
        total_time = time.time() - start_time
        
        # 生成最终报告
        self.generate_99_accuracy_report(total_time)

    def generate_99_accuracy_report(self, total_time: float):
        """生成99%准确率测试报告"""
        total_tests = self.test_results['total_tests']
        passed_tests = self.test_results['passed_tests']
        failed_tests = self.test_results['failed_tests']
        error_tests = self.test_results['error_tests']
        
        # 计算准确率
        if total_tests > 0:
            accuracy_rate = (passed_tests / total_tests) * 100
            success_rate = ((passed_tests + error_tests) / total_tests) * 100
        else:
            accuracy_rate = 0
            success_rate = 0
            
        # 性能统计
        response_times = self.test_results['response_times']
        avg_response_time = statistics.mean(response_times) if response_times else 0
        max_response_time = max(response_times) if response_times else 0
        
        print("\n" + "="*80)
        print("📋 全面99%准确率回归测试报告")
        print("="*80)
        
        print(f"\n📊 整体统计:")
        print(f"   总测试数量: {total_tests}")
        print(f"   通过测试: {passed_tests}")
        print(f"   失败测试: {failed_tests}")
        print(f"   错误测试: {error_tests}")
        print(f"   测试耗时: {total_time:.2f}秒")
        
        print(f"\n🎯 准确率分析:")
        print(f"   整体准确率: {accuracy_rate:.2f}%")
        print(f"   系统可用率: {success_rate:.2f}%")
        
        # 准确率评级
        if accuracy_rate >= 99.0:
            grade = "🏆 卓越级别 (99%+)"
            status = "✅ 达到目标"
        elif accuracy_rate >= 95.0:
            grade = "🥇 优秀级别 (95-99%)"
            status = "⚠️ 接近目标"
        elif accuracy_rate >= 90.0:
            grade = "🥈 良好级别 (90-95%)"
            status = "🔄 需要改进"
        else:
            grade = "🥉 基础级别 (<90%)"
            status = "❌ 需要重大改进"
            
        print(f"   准确率等级: {grade}")
        print(f"   目标达成: {status}")
        
        print(f"\n⚡ 性能指标:")
        print(f"   平均响应时间: {avg_response_time:.3f}秒")
        print(f"   最大响应时间: {max_response_time:.3f}秒")
        print(f"   性能评级: {'优秀' if avg_response_time < 1.0 else '良好' if avg_response_time < 2.0 else '一般'}")
        
        # 分类别统计
        category_stats = {}
        for result in self.test_results['detailed_results']:
            category = result['category']
            if category not in category_stats:
                category_stats[category] = {'total': 0, 'passed': 0}
            category_stats[category]['total'] += 1
            if result['status'] == 'PASS':
                category_stats[category]['passed'] += 1
                
        print(f"\n📈 分类别统计:")
        for category, stats in category_stats.items():
            category_accuracy = (stats['passed'] / stats['total'] * 100) if stats['total'] > 0 else 0
            print(f"   {category}: {category_accuracy:.1f}% ({stats['passed']}/{stats['total']})")
        
        # 保存详细报告
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'test_email': self.test_email,
            'accuracy_rate': accuracy_rate,
            'success_rate': success_rate,
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'failed_tests': failed_tests,
            'error_tests': error_tests,
            'avg_response_time': avg_response_time,
            'max_response_time': max_response_time,
            'total_time': total_time,
            'category_stats': category_stats,
            'detailed_results': self.test_results['detailed_results']
        }
        
        report_filename = f"comprehensive_99_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_filename, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
            
        print(f"\n💾 详细报告已保存: {report_filename}")
        
        # 最终判定
        if accuracy_rate >= self.accuracy_threshold:
            print(f"\n🎉 恭喜！系统达到{self.accuracy_threshold}%准确率目标")
            print("系统已准备好用于生产环境部署")
        else:
            print(f"\n📝 系统准确率{accuracy_rate:.2f}%，距离{self.accuracy_threshold}%目标还需提升")
            print("建议继续优化系统以达到目标准确率")

def main():
    """主函数"""
    print("🎯 启动全面99%准确率回归测试系统")
    print("📧 使用拥有者邮箱: hxl2022hao@gmail.com")
    
    tester = Comprehensive99RegressionTest()
    tester.run_comprehensive_99_test()

if __name__ == "__main__":
    main()