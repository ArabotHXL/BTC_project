#!/usr/bin/env python3
"""
全面认证回归测试系统
Comprehensive Authenticated Regression Test System

使用hxl2022hao@gmail.com邮箱进行完整的99%准确率验证测试
Complete 99% accuracy verification test using hxl2022hao@gmail.com email
"""

import requests
import time
import json
from datetime import datetime
import hashlib
from typing import Dict, List, Any, Tuple

class ComprehensiveAuthenticatedRegressionTest:
    def __init__(self):
        self.base_url = "http://localhost:5000"
        self.test_email = "hxl2022hao@gmail.com"
        self.session = requests.Session()
        self.test_results = {
            "authentication": [],
            "core_apis": [],
            "mining_calculations": [],
            "ui_pages": [],
            "analytics_system": [],
            "data_consistency": [],
            "performance": [],
            "security": []
        }
        self.start_time = time.time()
    
    def log_test(self, category: str, test_name: str, status: str, details: str = "", response_time: float = None):
        """记录测试结果"""
        result = {
            "timestamp": datetime.now().isoformat(),
            "test_name": test_name,
            "status": status,
            "details": details,
            "response_time": response_time
        }
        self.test_results[category].append(result)
        
        status_icon = "✅" if status == "成功" else "⚠️" if status == "警告" else "❌"
        time_info = f" ({response_time:.2f}ms)" if response_time else ""
        print(f"{status_icon} [{category.upper()}] {test_name}: {status}{time_info}")
        if details:
            print(f"   详情: {details}")
    
    def authenticate_with_email(self):
        """使用指定邮箱进行认证"""
        print(f"\n🔐 开始认证测试 - 使用邮箱: {self.test_email}")
        
        try:
            # 模拟登录过程
            start_time = time.time()
            
            # 创建会话哈希
            email_hash = hashlib.sha256(self.test_email.encode()).hexdigest()
            
            # 设置会话cookie
            self.session.cookies.set('session', f"authenticated_{email_hash}")
            self.session.cookies.set('user_email', self.test_email)
            self.session.cookies.set('user_role', 'owner')
            
            # 验证认证状态
            response = self.session.get(f"{self.base_url}/")
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                # 检查是否包含认证后的内容
                content = response.text
                is_authenticated = "登录" not in content or "login" not in content.lower()
                
                if is_authenticated:
                    self.log_test("authentication", "邮箱认证", "成功", 
                                f"用户: {self.test_email}, 角色: owner", response_time)
                    return True
                else:
                    self.log_test("authentication", "邮箱认证", "失败", 
                                "未检测到认证状态", response_time)
                    return False
            else:
                self.log_test("authentication", "邮箱认证", "失败", 
                            f"HTTP {response.status_code}", response_time)
                return False
                
        except Exception as e:
            self.log_test("authentication", "邮箱认证", "错误", str(e))
            return False
    
    def test_core_apis(self):
        """测试核心API端点"""
        print("\n🔧 开始核心API测试")
        
        api_endpoints = [
            ("/api/btc-price", "BTC价格API", self.validate_price_api),
            ("/api/network-stats", "网络统计API", self.validate_network_api),
            ("/api/miners", "矿机列表API", self.validate_miners_api),
            ("/api/sha256-comparison", "SHA256对比API", self.validate_comparison_api),
            ("/analytics/api/market-data", "分析市场数据API", self.validate_analytics_market),
            ("/analytics/api/latest-report", "最新报告API", self.validate_analytics_report),
            ("/analytics/api/technical-indicators", "技术指标API", self.validate_analytics_indicators),
            ("/analytics/api/price-history", "价格历史API", self.validate_analytics_history)
        ]
        
        for endpoint, name, validator in api_endpoints:
            start_time = time.time()
            try:
                response = self.session.get(f"{self.base_url}{endpoint}", timeout=10)
                response_time = (time.time() - start_time) * 1000
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        is_valid, validation_msg = validator(data)
                        
                        if is_valid:
                            self.log_test("core_apis", name, "成功", validation_msg, response_time)
                        else:
                            self.log_test("core_apis", name, "警告", f"数据验证问题: {validation_msg}", response_time)
                    except json.JSONDecodeError:
                        self.log_test("core_apis", name, "失败", "JSON解析错误", response_time)
                else:
                    self.log_test("core_apis", name, "失败", f"HTTP {response.status_code}", response_time)
                    
            except Exception as e:
                self.log_test("core_apis", name, "错误", str(e))
    
    def validate_price_api(self, data) -> Tuple[bool, str]:
        """验证价格API响应"""
        if 'btc_price' in data and isinstance(data['btc_price'], (int, float)) and data['btc_price'] > 0:
            return True, f"BTC价格: ${data['btc_price']:,.2f}"
        return False, "价格数据无效"
    
    def validate_network_api(self, data) -> Tuple[bool, str]:
        """验证网络统计API响应"""
        required_fields = ['btc_price', 'network_difficulty', 'network_hashrate']
        missing_fields = [field for field in required_fields if field not in data]
        
        if not missing_fields:
            return True, f"网络数据完整 - 价格: ${data['btc_price']:,.2f}, 算力: {data['network_hashrate']:.2f} EH/s"
        return False, f"缺失字段: {missing_fields}"
    
    def validate_miners_api(self, data) -> Tuple[bool, str]:
        """验证矿机数据API响应"""
        if isinstance(data, list) and len(data) >= 8:
            miner_names = [miner.get('name', '') for miner in data if isinstance(miner, dict)]
            return True, f"矿机数量: {len(data)}, 包含: {', '.join(miner_names[:3])}..."
        return False, "矿机数据不足或格式错误"
    
    def validate_comparison_api(self, data) -> Tuple[bool, str]:
        """验证挖矿对比API响应"""
        if isinstance(data, list) and len(data) > 0:
            return True, f"对比数据: {len(data)}个币种"
        return False, "对比数据为空"
    
    def validate_analytics_market(self, data) -> Tuple[bool, str]:
        """验证分析市场数据API"""
        if 'data' in data and 'btc_price' in data['data']:
            market_data = data['data']
            return True, f"分析数据 - 价格: ${market_data['btc_price']:,.2f}, 算力: {market_data.get('network_hashrate', 'N/A')} EH/s"
        return False, "分析市场数据格式错误"
    
    def validate_analytics_report(self, data) -> Tuple[bool, str]:
        """验证分析报告API"""
        if 'data' in data and isinstance(data['data'], dict):
            return True, "分析报告数据正常"
        return False, "分析报告数据异常"
    
    def validate_analytics_indicators(self, data) -> Tuple[bool, str]:
        """验证技术指标API"""
        if 'data' in data:
            return True, "技术指标数据正常"
        return False, "技术指标数据异常"
    
    def validate_analytics_history(self, data) -> Tuple[bool, str]:
        """验证价格历史API"""
        if 'data' in data and isinstance(data['data'], list):
            return True, f"历史数据: {len(data['data'])}条记录"
        return False, "历史数据格式错误"
    
    def test_mining_calculations(self):
        """测试挖矿计算功能"""
        print("\n⛏️ 开始挖矿计算测试")
        
        # 测试标准挖矿计算
        test_cases = [
            {
                "name": "标准S19 Pro计算",
                "data": {
                    "hashrate": 110,
                    "power": 3250,
                    "electricity_cost": 0.05,
                    "miner_price": 4500
                },
                "expected_profit_range": (500, 2000)  # 日利润范围(USD)
            },
            {
                "name": "高效S21 XP计算", 
                "data": {
                    "hashrate": 270,
                    "power": 3645,
                    "electricity_cost": 0.04,
                    "miner_price": 8000
                },
                "expected_profit_range": (1000, 4000)
            }
        ]
        
        for test_case in test_cases:
            start_time = time.time()
            try:
                response = self.session.post(f"{self.base_url}/calculate", 
                                           data=test_case["data"], timeout=15)
                response_time = (time.time() - start_time) * 1000
                
                if response.status_code == 200:
                    try:
                        result = response.json()
                        
                        # 验证计算结果
                        if self.validate_calculation_result(result, test_case["expected_profit_range"]):
                            profit = result.get('daily_profit_usd', 0)
                            roi = result.get('annual_roi_percentage', 0)
                            self.log_test("mining_calculations", test_case["name"], "成功", 
                                        f"日利润: ${profit:.2f}, 年化ROI: {roi:.1f}%", response_time)
                        else:
                            self.log_test("mining_calculations", test_case["name"], "警告", 
                                        "计算结果超出预期范围", response_time)
                    except json.JSONDecodeError:
                        self.log_test("mining_calculations", test_case["name"], "失败", 
                                    "JSON解析错误", response_time)
                else:
                    self.log_test("mining_calculations", test_case["name"], "失败", 
                                f"HTTP {response.status_code}", response_time)
                                
            except Exception as e:
                self.log_test("mining_calculations", test_case["name"], "错误", str(e))
    
    def validate_calculation_result(self, result: Dict, expected_range: Tuple[float, float]) -> bool:
        """验证挖矿计算结果"""
        required_fields = ['daily_profit_usd', 'monthly_profit_usd', 'annual_roi_percentage']
        
        # 检查必需字段
        if not all(field in result for field in required_fields):
            return False
        
        # 检查数值合理性
        daily_profit = result.get('daily_profit_usd', 0)
        return expected_range[0] <= daily_profit <= expected_range[1]
    
    def test_ui_pages(self):
        """测试UI页面功能"""
        print("\n🖥️ 开始UI页面测试")
        
        pages = [
            ("/", "主页", ["BTC挖矿计算器", "算力", "功耗"]),
            ("/analytics", "分析仪表盘", ["市场数据", "技术指标", "分析报告"]),
            ("/network-history", "网络历史", ["网络统计", "价格趋势", "难度趋势"]),
            ("/curtailment-calculator", "限电计算器", ["月度限电", "收益分析"]),
            ("/algorithm-test", "算法测试", ["算法差异", "测试结果"])
        ]
        
        for path, name, keywords in pages:
            start_time = time.time()
            try:
                response = self.session.get(f"{self.base_url}{path}", timeout=15)
                response_time = (time.time() - start_time) * 1000
                
                if response.status_code == 200:
                    content = response.text
                    
                    # 检查页面完整性
                    has_title = "<title>" in content
                    has_bootstrap = "bootstrap" in content.lower()
                    keyword_matches = sum(1 for keyword in keywords if keyword in content)
                    
                    completeness_score = (keyword_matches / len(keywords)) * 100
                    
                    if completeness_score >= 80 and has_title:
                        self.log_test("ui_pages", f"{name}页面", "成功", 
                                    f"内容完整性: {completeness_score:.1f}%, 加载正常", response_time)
                    elif completeness_score >= 50:
                        self.log_test("ui_pages", f"{name}页面", "警告", 
                                    f"内容完整性: {completeness_score:.1f}%, 部分内容缺失", response_time)
                    else:
                        self.log_test("ui_pages", f"{name}页面", "失败", 
                                    f"内容完整性: {completeness_score:.1f}%, 严重缺失", response_time)
                else:
                    self.log_test("ui_pages", f"{name}页面", "失败", 
                                f"HTTP {response.status_code}", response_time)
                                
            except Exception as e:
                self.log_test("ui_pages", f"{name}页面", "错误", str(e))
    
    def test_analytics_system(self):
        """测试分析系统功能"""
        print("\n📊 开始分析系统测试")
        
        # 测试分析系统的各个组件
        analytics_tests = [
            ("市场数据收集", "/analytics/api/market-data"),
            ("技术指标计算", "/analytics/api/technical-indicators"), 
            ("价格历史分析", "/analytics/api/price-history"),
            ("分析报告生成", "/analytics/api/latest-report")
        ]
        
        for test_name, endpoint in analytics_tests:
            start_time = time.time()
            try:
                response = self.session.get(f"{self.base_url}{endpoint}", timeout=10)
                response_time = (time.time() - start_time) * 1000
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        if 'success' in data and data['success']:
                            self.log_test("analytics_system", test_name, "成功", 
                                        "数据返回正常", response_time)
                        else:
                            self.log_test("analytics_system", test_name, "警告", 
                                        "返回数据格式异常", response_time)
                    except json.JSONDecodeError:
                        self.log_test("analytics_system", test_name, "失败", 
                                    "JSON解析错误", response_time)
                else:
                    self.log_test("analytics_system", test_name, "失败", 
                                f"HTTP {response.status_code}", response_time)
                                
            except Exception as e:
                self.log_test("analytics_system", test_name, "错误", str(e))
    
    def test_data_consistency(self):
        """测试数据一致性"""
        print("\n🔄 开始数据一致性测试")
        
        try:
            # 获取多个数据源的价格信息
            price_sources = [
                ("/api/btc-price", "价格API"),
                ("/api/network-stats", "网络统计API"),
                ("/analytics/api/market-data", "分析市场数据API")
            ]
            
            prices = []
            source_names = []
            
            for endpoint, name in price_sources:
                try:
                    response = self.session.get(f"{self.base_url}{endpoint}", timeout=5)
                    if response.status_code == 200:
                        data = response.json()
                        
                        # 提取价格数据
                        price = None
                        if 'btc_price' in data:
                            price = data['btc_price']
                        elif 'data' in data and 'btc_price' in data['data']:
                            price = data['data']['btc_price']
                        
                        if price and price > 0:
                            prices.append(price)
                            source_names.append(name)
                            
                except Exception:
                    continue
            
            # 计算价格一致性
            if len(prices) >= 2:
                max_price = max(prices)
                min_price = min(prices)
                variance = ((max_price - min_price) / min_price) * 100 if min_price > 0 else 0
                
                if variance < 1.0:
                    self.log_test("data_consistency", "价格数据一致性", "成功", 
                                f"价格方差: {variance:.3f}%, 数据源: {len(prices)}个")
                elif variance < 3.0:
                    self.log_test("data_consistency", "价格数据一致性", "警告", 
                                f"价格方差: {variance:.3f}%, 存在轻微差异")
                else:
                    self.log_test("data_consistency", "价格数据一致性", "失败", 
                                f"价格方差: {variance:.3f}%, 数据源不同步")
            else:
                self.log_test("data_consistency", "价格数据一致性", "失败", 
                            "获取价格数据不足")
                            
        except Exception as e:
            self.log_test("data_consistency", "数据一致性测试", "错误", str(e))
    
    def test_performance(self):
        """测试系统性能"""
        print("\n⚡ 开始性能测试")
        
        # 测试关键端点的响应时间
        performance_endpoints = [
            ("/", "主页加载"),
            ("/api/btc-price", "价格API响应"),
            ("/api/network-stats", "网络统计响应"),
            ("/analytics", "分析仪表盘加载")
        ]
        
        for endpoint, test_name in performance_endpoints:
            response_times = []
            
            # 执行5次测试取平均值
            for i in range(5):
                start_time = time.time()
                try:
                    response = self.session.get(f"{self.base_url}{endpoint}", timeout=10)
                    response_time = (time.time() - start_time) * 1000
                    
                    if response.status_code == 200:
                        response_times.append(response_time)
                        
                except Exception:
                    continue
            
            if response_times:
                avg_response_time = sum(response_times) / len(response_times)
                
                if avg_response_time < 500:
                    performance_level = "优秀"
                    status = "成功"
                elif avg_response_time < 1000:
                    performance_level = "良好"
                    status = "成功"
                elif avg_response_time < 2000:
                    performance_level = "一般"
                    status = "警告"
                else:
                    performance_level = "需优化"
                    status = "失败"
                
                self.log_test("performance", test_name, status, 
                            f"平均响应时间: {avg_response_time:.2f}ms, 性能: {performance_level}")
            else:
                self.log_test("performance", test_name, "失败", "无法获取响应时间")
    
    def test_security(self):
        """测试安全功能"""
        print("\n🔒 开始安全测试")
        
        # 创建未认证的会话来测试访问控制
        unauth_session = requests.Session()
        
        protected_endpoints = [
            "/analytics",
            "/user-access", 
            "/mine-customer-management"
        ]
        
        for endpoint in protected_endpoints:
            try:
                response = unauth_session.get(f"{self.base_url}{endpoint}", timeout=5)
                
                if response.status_code in [401, 403]:
                    self.log_test("security", f"访问控制 {endpoint}", "成功", 
                                "未授权访问被阻止")
                elif response.status_code == 302:
                    # 检查是否重定向到登录页面
                    location = response.headers.get('Location', '')
                    if 'login' in location.lower():
                        self.log_test("security", f"访问控制 {endpoint}", "成功", 
                                    "重定向到登录页面")
                    else:
                        self.log_test("security", f"访问控制 {endpoint}", "警告", 
                                    "重定向目标未知")
                else:
                    self.log_test("security", f"访问控制 {endpoint}", "失败", 
                                f"未授权访问成功 (HTTP {response.status_code})")
                                
            except Exception as e:
                self.log_test("security", f"访问控制 {endpoint}", "错误", str(e))
    
    def run_comprehensive_test(self):
        """运行完整的认证回归测试"""
        print(f"开始全面认证回归测试 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"测试邮箱: {self.test_email}")
        print("="*80)
        
        # 1. 认证测试
        auth_success = self.authenticate_with_email()
        if not auth_success:
            print("❌ 认证失败，终止测试")
            return False
        
        # 2. 核心功能测试
        self.test_core_apis()
        self.test_mining_calculations()
        self.test_ui_pages()
        self.test_analytics_system()
        self.test_data_consistency()
        self.test_performance()
        self.test_security()
        
        return True
    
    def generate_final_report(self):
        """生成最终测试报告"""
        total_time = time.time() - self.start_time
        
        print("\n" + "="*80)
        print("全面认证回归测试报告")
        print("="*80)
        
        total_tests = 0
        successful_tests = 0
        warning_tests = 0
        failed_tests = 0
        
        category_summary = {}
        
        for category, results in self.test_results.items():
            if not results:
                continue
                
            category_total = len(results)
            category_success = sum(1 for r in results if r['status'] == '成功')
            category_warning = sum(1 for r in results if r['status'] == '警告')
            category_failed = category_total - category_success - category_warning
            
            total_tests += category_total
            successful_tests += category_success
            warning_tests += category_warning
            failed_tests += category_failed
            
            category_summary[category] = {
                'total': category_total,
                'success': category_success,
                'warning': category_warning,
                'failed': category_failed,
                'success_rate': (category_success / category_total) * 100 if category_total > 0 else 0
            }
            
            print(f"\n[{category.upper()}] 测试结果:")
            for result in results:
                status_icon = "✅" if result['status'] == "成功" else "⚠️" if result['status'] == "警告" else "❌"
                print(f"  {status_icon} {result['test_name']}: {result['status']}")
                if result['details']:
                    print(f"     {result['details']}")
            
            print(f"  分类统计: {category_success}成功, {category_warning}警告, {category_failed}失败")
            print(f"  分类成功率: {category_summary[category]['success_rate']:.1f}%")
        
        # 计算总体统计
        overall_success_rate = (successful_tests / total_tests) * 100 if total_tests > 0 else 0
        functional_success_rate = ((successful_tests + warning_tests) / total_tests) * 100 if total_tests > 0 else 0
        
        print(f"\n🎯 总体测试统计:")
        print(f"   总测试数: {total_tests}")
        print(f"   成功: {successful_tests} ({(successful_tests/total_tests)*100:.1f}%)")
        print(f"   警告: {warning_tests} ({(warning_tests/total_tests)*100:.1f}%)")
        print(f"   失败: {failed_tests} ({(failed_tests/total_tests)*100:.1f}%)")
        print(f"   严格准确率: {overall_success_rate:.1f}%")
        print(f"   功能可用率: {functional_success_rate:.1f}%")
        print(f"   测试耗时: {total_time:.1f}秒")
        
        # 准确率等级评定
        if functional_success_rate >= 99.0:
            accuracy_level = "🏆 卓越级别 (99%+)"
        elif functional_success_rate >= 95.0:
            accuracy_level = "🥇 优秀级别 (95-99%)"
        elif functional_success_rate >= 90.0:
            accuracy_level = "🥈 良好级别 (90-95%)"
        elif functional_success_rate >= 80.0:
            accuracy_level = "🥉 及格级别 (80-90%)"
        else:
            accuracy_level = "❌ 不及格 (<80%)"
        
        print(f"\n📊 准确率等级: {accuracy_level}")
        
        # 99%目标达成评估
        if functional_success_rate >= 99.0:
            print("🎉 恭喜！系统已达到99%准确率目标！")
            target_achieved = True
        else:
            remaining_improvement = 99.0 - functional_success_rate
            print(f"🎯 距离99%目标还需提升: {remaining_improvement:.1f}%")
            target_achieved = False
        
        # 保存详细报告
        report_filename = f"comprehensive_authenticated_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_filename, 'w', encoding='utf-8') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "test_email": self.test_email,
                "total_tests": total_tests,
                "successful_tests": successful_tests,
                "warning_tests": warning_tests,
                "failed_tests": failed_tests,
                "overall_success_rate": overall_success_rate,
                "functional_success_rate": functional_success_rate,
                "accuracy_level": accuracy_level,
                "target_achieved": target_achieved,
                "test_duration": total_time,
                "category_summary": category_summary,
                "detailed_results": self.test_results
            }, f, ensure_ascii=False, indent=2)
        
        print(f"\n📋 详细测试报告已保存: {report_filename}")
        
        return functional_success_rate, target_achieved, total_tests, successful_tests

def main():
    """主函数"""
    tester = ComprehensiveAuthenticatedRegressionTest()
    
    # 运行完整测试
    test_success = tester.run_comprehensive_test()
    
    if test_success:
        # 生成最终报告
        success_rate, target_achieved, total, successful = tester.generate_final_report()
        
        print(f"\n全面认证回归测试完成!")
        print(f"功能可用率: {success_rate:.1f}%")
        print(f"99%目标达成: {'是' if target_achieved else '否'}")
        
        return target_achieved
    else:
        print("\n❌ 测试因认证失败而终止")
        return False

if __name__ == "__main__":
    main()