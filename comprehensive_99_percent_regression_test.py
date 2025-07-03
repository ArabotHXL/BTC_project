#!/usr/bin/env python3
"""
全面99%准确率回归测试
Comprehensive 99% Accuracy Regression Test

测试所有功能模块，使用多个用户邮箱，确保系统准确率达到99%
Test all function modules with multiple user emails to ensure 99% system accuracy
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, List, Tuple

class Comprehensive99PercentRegressionTest:
    def __init__(self):
        self.base_url = "http://0.0.0.0:5000"
        self.test_emails = [
            "testing123@example.com",
            "site@example.com", 
            "user@example.com",
            "hxl2022hao@gmail.com",
            "admin@example.com"
        ]
        self.test_results = []
        self.session = requests.Session()
        self.current_email = None
        self.start_time = datetime.now()
        
    def log_test(self, category: str, test_name: str, status: str, details: str = "", response_time: float = None, email: str = None):
        """记录测试结果"""
        result = {
            'timestamp': datetime.now().isoformat(),
            'category': category,
            'test_name': test_name,
            'status': status,
            'details': details,
            'response_time': round(response_time, 2) if response_time else None,
            'email': email or self.current_email
        }
        self.test_results.append(result)
        
        status_icon = "✅" if status == "成功" else "⚠️" if status == "警告" else "❌"
        email_info = f" [{email or self.current_email}]" if email or self.current_email else ""
        print(f"{status_icon} [{category}] {test_name}: {status}{email_info}")
        if details:
            print(f"   详情: {details}")
        if response_time:
            print(f"   响应时间: {response_time:.2f}ms")

    def authenticate_with_email(self, email: str) -> bool:
        """使用指定邮箱进行认证"""
        try:
            start_time = time.time()
            
            # 清除之前的会话
            self.session = requests.Session()
            
            login_data = {'email': email}
            response = self.session.post(f"{self.base_url}/login", data=login_data, timeout=10)
            
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code in [200, 302]:
                self.current_email = email
                
                # 验证登录状态
                main_response = self.session.get(f"{self.base_url}/", timeout=5)
                if main_response.status_code == 200 and "logout" in main_response.text.lower():
                    self.log_test("AUTHENTICATION", f"邮箱认证登录", "成功", 
                                f"认证邮箱: {email}, 状态码: {response.status_code}", response_time, email)
                    return True
                else:
                    self.log_test("AUTHENTICATION", f"邮箱认证登录", "失败", 
                                f"登录后验证失败: {email}", response_time, email)
                    return False
            else:
                self.log_test("AUTHENTICATION", f"邮箱认证登录", "失败", 
                            f"认证失败: {email}, 状态码: {response.status_code}", response_time, email)
                return False
                
        except Exception as e:
            self.log_test("AUTHENTICATION", f"邮箱认证登录", "失败", 
                        f"认证异常: {email}, 错误: {str(e)}", None, email)
            return False

    def test_api_endpoints_with_authentication(self) -> None:
        """测试所有API端点的认证访问"""
        api_tests = [
            ("/api/btc-price", "BTC价格API"),
            ("/api/network-stats", "网络统计API"),
            ("/api/miners", "矿机列表API"),
            ("/analytics/api/market-data", "分析市场数据API")
        ]
        
        for endpoint, name in api_tests:
            try:
                start_time = time.time()
                response = self.session.get(f"{self.base_url}{endpoint}", timeout=10)
                response_time = (time.time() - start_time) * 1000
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('success'):
                        self.log_test("API_ENDPOINTS", name, "成功", 
                                    f"数据完整性验证通过", response_time)
                    else:
                        self.log_test("API_ENDPOINTS", name, "警告", 
                                    f"API返回success=false: {data.get('error', '未知错误')}", response_time)
                elif response.status_code == 401:
                    self.log_test("API_ENDPOINTS", name, "失败", 
                                f"认证失败，需要重新登录", response_time)
                else:
                    self.log_test("API_ENDPOINTS", name, "失败", 
                                f"HTTP错误: {response.status_code}", response_time)
                    
            except Exception as e:
                self.log_test("API_ENDPOINTS", name, "失败", f"请求异常: {str(e)}")

    def test_mining_calculations_comprehensive(self) -> None:
        """全面测试挖矿计算功能"""
        # 测试所有矿机型号
        miner_models = [
            "Antminer S19", "Antminer S19 Pro", "Antminer S19 XP",
            "Antminer S21", "Antminer S21 Pro", "Antminer S21 XP",
            "Antminer S21 Hyd", "Antminer S21 Pro Hyd", "Antminer S21 XP Hyd",
            "WhatsMiner M50"
        ]
        
        successful_calculations = 0
        total_calculations = len(miner_models)
        
        for miner_model in miner_models:
            try:
                start_time = time.time()
                
                calc_data = {
                    'miner_model': miner_model,
                    'miner_count': '100',
                    'site_power_mw': '10',
                    'electricity_cost': '0.06',
                    'client_electricity_cost': '0.08',
                    'btc_price': '108000',
                    'use_real_time': 'true'
                }
                
                response = self.session.post(f"{self.base_url}/calculate", data=calc_data, timeout=15)
                response_time = (time.time() - start_time) * 1000
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # 验证计算结果完整性
                    required_fields = ['btc_mined', 'revenue', 'client_profit', 'network_data']
                    missing_fields = [field for field in required_fields if field not in data]
                    
                    if not missing_fields:
                        successful_calculations += 1
                        
                        # 提取关键数据进行验证
                        btc_mined = data.get('btc_mined', {})
                        daily_btc = btc_mined.get('daily', 0) if isinstance(btc_mined, dict) else 0
                        
                        revenue = data.get('revenue', {})
                        daily_revenue = revenue.get('daily', 0) if isinstance(revenue, dict) else 0
                        
                        self.log_test("MINING_CALCULATIONS", f"{miner_model}计算", "成功", 
                                    f"日产BTC: {daily_btc:.6f}, 日收入: ${daily_revenue:.2f}", response_time)
                    else:
                        self.log_test("MINING_CALCULATIONS", f"{miner_model}计算", "警告", 
                                    f"缺失字段: {missing_fields}", response_time)
                else:
                    self.log_test("MINING_CALCULATIONS", f"{miner_model}计算", "失败", 
                                f"HTTP错误: {response.status_code}", response_time)
                    
            except Exception as e:
                self.log_test("MINING_CALCULATIONS", f"{miner_model}计算", "失败", f"计算异常: {str(e)}")
        
        # 计算成功率
        success_rate = (successful_calculations / total_calculations) * 100
        self.log_test("MINING_CALCULATIONS", "总体计算成功率", 
                     "成功" if success_rate >= 90 else "警告" if success_rate >= 70 else "失败",
                     f"成功率: {success_rate:.1f}% ({successful_calculations}/{total_calculations})")

    def test_user_interface_pages(self) -> None:
        """测试用户界面页面完整性"""
        pages = [
            ("/", "主页"),
            ("/analytics", "分析仪表盘"),
            ("/network-history", "网络历史"),
            ("/curtailment-calculator", "限电计算器"),
            ("/algorithm-test", "算法测试")
        ]
        
        for path, name in pages:
            try:
                start_time = time.time()
                response = self.session.get(f"{self.base_url}{path}", timeout=10)
                response_time = (time.time() - start_time) * 1000
                
                if response.status_code == 200:
                    content = response.text
                    
                    # 检查页面完整性
                    essential_elements = ["<!DOCTYPE html>", "<title>", "<body>"]
                    missing_elements = [elem for elem in essential_elements if elem not in content]
                    
                    if not missing_elements and len(content) > 1000:
                        self.log_test("USER_INTERFACE", f"{name}页面", "成功", 
                                    f"页面大小: {len(content)} 字符", response_time)
                    else:
                        self.log_test("USER_INTERFACE", f"{name}页面", "警告", 
                                    f"页面可能不完整，大小: {len(content)} 字符", response_time)
                else:
                    self.log_test("USER_INTERFACE", f"{name}页面", "失败", 
                                f"HTTP错误: {response.status_code}", response_time)
                    
            except Exception as e:
                self.log_test("USER_INTERFACE", f"{name}页面", "失败", f"页面异常: {str(e)}")

    def test_data_consistency_validation(self) -> None:
        """测试数据一致性验证"""
        try:
            # 获取多个API的价格数据进行一致性检查
            apis = [
                ("/api/btc-price", "价格API"),
                ("/api/network-stats", "网络统计API"),
                ("/analytics/api/market-data", "分析系统API")
            ]
            
            prices = {}
            for endpoint, name in apis:
                try:
                    response = self.session.get(f"{self.base_url}{endpoint}", timeout=5)
                    if response.status_code == 200:
                        data = response.json()
                        if data.get('success'):
                            if 'btc_price' in data:
                                prices[name] = data['btc_price']
                            elif 'price' in data:
                                prices[name] = data['price']
                            elif 'data' in data and 'btc_price' in data['data']:
                                prices[name] = data['data']['btc_price']
                except:
                    continue
            
            if len(prices) >= 2:
                price_values = list(prices.values())
                max_price = max(price_values)
                min_price = min(price_values)
                variance = ((max_price - min_price) / max_price) * 100 if max_price > 0 else 0
                
                if variance <= 1.0:  # 允许1%的差异
                    price_details = ", ".join([f"{name}: ${price:,.2f}" for name, price in prices.items()])
                    self.log_test("DATA_CONSISTENCY", "价格数据一致性", "成功", 
                                f"方差: {variance:.3f}%, 数据源: {price_details}")
                else:
                    self.log_test("DATA_CONSISTENCY", "价格数据一致性", "警告", 
                                f"价格差异过大，方差: {variance:.3f}%")
            else:
                self.log_test("DATA_CONSISTENCY", "价格数据一致性", "失败", 
                            f"无法获取足够的价格数据进行对比")
                
        except Exception as e:
            self.log_test("DATA_CONSISTENCY", "价格数据一致性", "失败", f"一致性检查异常: {str(e)}")

    def test_advanced_features(self) -> None:
        """测试高级功能"""
        advanced_tests = [
            # 限电计算测试
            {
                'endpoint': '/api/curtailment',
                'name': '限电计算API',
                'data': {
                    'site_power_mw': '10',
                    'curtailment_percentage': '20',
                    'electricity_cost': '0.06',
                    'shutdown_strategy': 'efficiency'
                }
            },
            # 算法差异测试
            {
                'endpoint': '/api/algorithm-difference',
                'name': '算法差异测试API',
                'data': {
                    'miner_count': '100',
                    'electricity_cost': '0.06'
                }
            }
        ]
        
        for test in advanced_tests:
            try:
                start_time = time.time()
                response = self.session.post(f"{self.base_url}{test['endpoint']}", 
                                           data=test['data'], timeout=10)
                response_time = (time.time() - start_time) * 1000
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        if data.get('success'):
                            self.log_test("ADVANCED_FEATURES", test['name'], "成功", 
                                        "功能正常运行", response_time)
                        else:
                            self.log_test("ADVANCED_FEATURES", test['name'], "警告", 
                                        f"API返回错误: {data.get('error', '未知错误')}", response_time)
                    except:
                        self.log_test("ADVANCED_FEATURES", test['name'], "警告", 
                                    "响应不是有效JSON", response_time)
                else:
                    self.log_test("ADVANCED_FEATURES", test['name'], "失败", 
                                f"HTTP错误: {response.status_code}", response_time)
                    
            except Exception as e:
                self.log_test("ADVANCED_FEATURES", test['name'], "失败", f"功能异常: {str(e)}")

    def run_comprehensive_99_percent_test(self) -> None:
        """运行全面的99%准确率测试"""
        print("="*80)
        print("开始全面99%准确率回归测试")
        print(f"测试开始时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"测试邮箱: {', '.join(self.test_emails)}")
        print("="*80)
        
        # 为每个邮箱执行完整测试
        for email in self.test_emails:
            print(f"\n🔐 开始测试邮箱: {email}")
            
            # 认证测试
            if self.authenticate_with_email(email):
                print(f"\n📊 开始API端点测试")
                self.test_api_endpoints_with_authentication()
                
                print(f"\n⛏️ 开始挖矿计算测试") 
                self.test_mining_calculations_comprehensive()
                
                print(f"\n🖥️ 开始用户界面测试")
                self.test_user_interface_pages()
                
                print(f"\n🔧 开始高级功能测试")
                self.test_advanced_features()
            else:
                print(f"❌ 邮箱 {email} 认证失败，跳过后续测试")
        
        # 数据一致性测试（使用最后一个成功认证的会话）
        print(f"\n📊 开始数据一致性测试")
        self.test_data_consistency_validation()
        
        # 生成最终报告
        self.generate_99_percent_report()

    def generate_99_percent_report(self) -> None:
        """生成99%准确率测试报告"""
        end_time = datetime.now()
        total_time = (end_time - self.start_time).total_seconds()
        
        # 统计结果
        total_tests = len(self.test_results)
        successful_tests = len([r for r in self.test_results if r['status'] == '成功'])
        warning_tests = len([r for r in self.test_results if r['status'] == '警告'])
        failed_tests = len([r for r in self.test_results if r['status'] == '失败'])
        
        success_rate = (successful_tests / total_tests) * 100 if total_tests > 0 else 0
        functional_rate = ((successful_tests + warning_tests) / total_tests) * 100 if total_tests > 0 else 0
        
        print("\n" + "="*80)
        print("全面99%准确率回归测试报告")
        print("="*80)
        
        # 按类别统计
        categories = {}
        for result in self.test_results:
            category = result['category']
            if category not in categories:
                categories[category] = {'成功': 0, '警告': 0, '失败': 0}
            categories[category][result['status']] += 1
        
        for category, stats in categories.items():
            total_cat = sum(stats.values())
            success_cat = stats['成功']
            rate_cat = (success_cat / total_cat) * 100 if total_cat > 0 else 0
            
            print(f"\n[{category}] 测试结果:")
            for status, count in stats.items():
                icon = "✅" if status == "成功" else "⚠️" if status == "警告" else "❌"
                print(f"  {icon} {status}: {count}")
            print(f"     类别成功率: {rate_cat:.1f}%")
        
        # 按邮箱统计
        print(f"\n📧 各邮箱测试结果:")
        for email in self.test_emails:
            email_results = [r for r in self.test_results if r.get('email') == email]
            if email_results:
                email_success = len([r for r in email_results if r['status'] == '成功'])
                email_total = len(email_results)
                email_rate = (email_success / email_total) * 100 if email_total > 0 else 0
                print(f"  {email}: {email_rate:.1f}% ({email_success}/{email_total})")
        
        print(f"\n🎯 总体统计:")
        print(f"   总测试数: {total_tests}")
        print(f"   成功: {successful_tests} ({success_rate:.1f}%)")
        print(f"   警告: {warning_tests} ({warning_tests/total_tests*100:.1f}%)")
        print(f"   失败: {failed_tests} ({failed_tests/total_tests*100:.1f}%)")
        print(f"   功能可用率: {functional_rate:.1f}%")
        print(f"   严格成功率: {success_rate:.1f}%")
        print(f"   测试耗时: {total_time:.1f}秒")
        
        # 99%达成评估
        target_achieved = success_rate >= 99.0
        print(f"\n🎯 99%目标达成: {'是' if target_achieved else '否'}")
        if not target_achieved:
            gap = 99.0 - success_rate
            print(f"🎯 距离99%目标还需提升: {gap:.1f}%")
        
        # 准确率等级评定
        if success_rate >= 99:
            grade = "🥇 完美级别 (99%+)"
        elif success_rate >= 95:
            grade = "🥈 卓越级别 (95-99%)"
        elif success_rate >= 90:
            grade = "🥉 良好级别 (90-95%)"
        elif success_rate >= 80:
            grade = "⚠️ 可接受级别 (80-90%)"
        else:
            grade = "❌ 需要改进 (<80%)"
            
        print(f"📊 准确率等级: {grade}")
        
        # 保存详细报告
        report_data = {
            'test_summary': {
                'start_time': self.start_time.isoformat(),
                'end_time': end_time.isoformat(),
                'total_duration_seconds': total_time,
                'total_tests': total_tests,
                'successful_tests': successful_tests,
                'warning_tests': warning_tests,
                'failed_tests': failed_tests,
                'success_rate': success_rate,
                'functional_rate': functional_rate,
                'target_achieved': target_achieved,
                'accuracy_grade': grade
            },
            'category_results': categories,
            'detailed_results': self.test_results,
            'test_emails': self.test_emails
        }
        
        report_filename = f"comprehensive_99_regression_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_filename, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n📋 详细测试报告已保存: {report_filename}")
        print(f"\n全面99%准确率回归测试完成！")
        print(f"功能可用率: {functional_rate:.1f}%")
        print(f"99%目标达成: {'是' if target_achieved else '否'}")

def main():
    """主函数"""
    test = Comprehensive99PercentRegressionTest()
    test.run_comprehensive_99_percent_test()

if __name__ == "__main__":
    main()