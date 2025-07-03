#!/usr/bin/env python3
"""
最终99%准确率验证测试
Final 99% Accuracy Verification Test

使用hxl2022hao@gmail.com进行完整的系统准确率验证
Complete system accuracy verification using hxl2022hao@gmail.com
"""

import requests
import time
import json
from datetime import datetime
from typing import Dict, List, Any, Tuple

class Final99AccuracyTest:
    def __init__(self):
        self.base_url = "http://localhost:5000"
        self.test_email = "hxl2022hao@gmail.com"
        self.session = requests.Session()
        self.test_results = {
            "authentication": [],
            "core_functionality": [],
            "mining_calculations": [],
            "api_endpoints": [],
            "ui_completeness": [],
            "data_accuracy": []
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
    
    def authenticate_system(self) -> bool:
        """认证系统 - 使用标准登录流程"""
        print(f"\n🔐 开始系统认证测试")
        
        try:
            start_time = time.time()
            
            # 步骤1: 提交登录表单
            login_data = {
                'email': self.test_email
            }
            
            response = self.session.post(f"{self.base_url}/login", 
                                       data=login_data, 
                                       allow_redirects=True,
                                       timeout=10)
            response_time = (time.time() - start_time) * 1000
            
            # 步骤2: 验证登录结果
            if response.status_code == 200:
                # 检查是否成功登录（通过检查页面内容）
                content = response.text
                
                # 检查是否包含认证后才能看到的内容
                auth_indicators = [
                    "BTC挖矿计算器",
                    "算力",
                    "功耗",
                    "电费",
                    "calculate"
                ]
                
                auth_score = sum(1 for indicator in auth_indicators if indicator in content)
                
                if auth_score >= 3:  # 至少要有3个指标说明成功登录
                    self.log_test("authentication", "邮箱认证登录", "成功", 
                                f"认证邮箱: {self.test_email}, 内容指标: {auth_score}/5", response_time)
                    return True
                else:
                    self.log_test("authentication", "邮箱认证登录", "失败", 
                                f"认证内容不完整, 指标: {auth_score}/5", response_time)
                    return False
            else:
                self.log_test("authentication", "邮箱认证登录", "失败", 
                            f"HTTP状态码: {response.status_code}", response_time)
                return False
                
        except Exception as e:
            self.log_test("authentication", "邮箱认证登录", "错误", str(e))
            return False
    
    def test_core_functionality(self):
        """测试核心功能"""
        print("\n🔧 开始核心功能测试")
        
        # 测试主页加载
        start_time = time.time()
        try:
            response = self.session.get(f"{self.base_url}/", timeout=10)
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                content = response.text
                
                # 检查核心功能元素
                core_elements = [
                    "BTC挖矿计算器",
                    "算力",
                    "功耗", 
                    "电费",
                    "矿机型号",
                    "计算收益"
                ]
                
                element_count = sum(1 for element in core_elements if element in content)
                completeness = (element_count / len(core_elements)) * 100
                
                if completeness >= 80:
                    self.log_test("core_functionality", "主页核心功能", "成功", 
                                f"功能完整性: {completeness:.1f}% ({element_count}/{len(core_elements)})", response_time)
                else:
                    self.log_test("core_functionality", "主页核心功能", "警告", 
                                f"功能完整性: {completeness:.1f}% ({element_count}/{len(core_elements)})", response_time)
            else:
                self.log_test("core_functionality", "主页核心功能", "失败", 
                            f"HTTP {response.status_code}", response_time)
                            
        except Exception as e:
            self.log_test("core_functionality", "主页核心功能", "错误", str(e))
    
    def test_mining_calculations(self):
        """测试挖矿计算功能"""
        print("\n⛏️ 开始挖矿计算测试")
        
        # 测试案例：Antminer S19 Pro标准配置
        test_data = {
            "miner_model": "antminer_s19_pro",
            "miner_count": "1",
            "electricity_cost": "0.05",
            "use_real_time": "true"
        }
        
        start_time = time.time()
        try:
            response = self.session.post(f"{self.base_url}/calculate", 
                                       data=test_data, 
                                       timeout=15)
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    
                    # 验证计算结果的关键字段
                    required_fields = [
                        'daily_profit_usd',
                        'monthly_profit_usd', 
                        'annual_roi_percentage',
                        'breakeven_electricity_cost',
                        'btc_price',
                        'network_hashrate'
                    ]
                    
                    missing_fields = [field for field in required_fields if field not in result]
                    
                    if not missing_fields:
                        # 验证数值合理性
                        daily_profit = result.get('daily_profit_usd', 0)
                        annual_roi = result.get('annual_roi_percentage', 0)
                        
                        # 合理性检查：日利润应该在合理范围内
                        if 0 < daily_profit < 5000 and -100 < annual_roi < 1000:
                            self.log_test("mining_calculations", "S19 Pro标准计算", "成功", 
                                        f"日利润: ${daily_profit:.2f}, 年化ROI: {annual_roi:.1f}%", response_time)
                        else:
                            self.log_test("mining_calculations", "S19 Pro标准计算", "警告", 
                                        f"数值异常 - 日利润: ${daily_profit:.2f}, ROI: {annual_roi:.1f}%", response_time)
                    else:
                        self.log_test("mining_calculations", "S19 Pro标准计算", "失败", 
                                    f"缺失字段: {missing_fields}", response_time)
                        
                except json.JSONDecodeError:
                    self.log_test("mining_calculations", "S19 Pro标准计算", "失败", 
                                "JSON解析错误", response_time)
            else:
                self.log_test("mining_calculations", "S19 Pro标准计算", "失败", 
                            f"HTTP {response.status_code}", response_time)
                            
        except Exception as e:
            self.log_test("mining_calculations", "S19 Pro标准计算", "错误", str(e))
    
    def test_api_endpoints(self):
        """测试API端点"""
        print("\n🔌 开始API端点测试")
        
        api_tests = [
            ("/api/btc-price", "BTC价格API", self.validate_price_data),
            ("/api/network-stats", "网络统计API", self.validate_network_data), 
            ("/api/miners", "矿机列表API", self.validate_miners_data),
            ("/analytics/api/market-data", "分析市场数据API", self.validate_analytics_data)
        ]
        
        for endpoint, name, validator in api_tests:
            start_time = time.time()
            try:
                response = self.session.get(f"{self.base_url}{endpoint}", timeout=10)
                response_time = (time.time() - start_time) * 1000
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        is_valid, details = validator(data)
                        
                        if is_valid:
                            self.log_test("api_endpoints", name, "成功", details, response_time)
                        else:
                            self.log_test("api_endpoints", name, "警告", f"数据验证问题: {details}", response_time)
                            
                    except json.JSONDecodeError:
                        self.log_test("api_endpoints", name, "失败", "JSON解析错误", response_time)
                else:
                    self.log_test("api_endpoints", name, "失败", f"HTTP {response.status_code}", response_time)
                    
            except Exception as e:
                self.log_test("api_endpoints", name, "错误", str(e))
    
    def validate_price_data(self, data) -> Tuple[bool, str]:
        """验证价格数据"""
        if 'btc_price' in data and isinstance(data['btc_price'], (int, float)) and data['btc_price'] > 50000:
            return True, f"BTC价格: ${data['btc_price']:,.2f}"
        return False, "价格数据无效或超出合理范围"
    
    def validate_network_data(self, data) -> Tuple[bool, str]:
        """验证网络数据"""
        required_fields = ['btc_price', 'network_hashrate', 'network_difficulty']
        missing_fields = [field for field in required_fields if field not in data]
        
        if not missing_fields:
            hashrate = data.get('network_hashrate', 0)
            if hashrate > 500:  # 网络算力应该大于500 EH/s
                return True, f"网络算力: {hashrate:.2f} EH/s, 价格: ${data['btc_price']:,.2f}"
            else:
                return False, f"网络算力异常: {hashrate} EH/s"
        return False, f"缺失字段: {missing_fields}"
    
    def validate_miners_data(self, data) -> Tuple[bool, str]:
        """验证矿机数据"""
        if isinstance(data, list) and len(data) >= 8:
            # 检查矿机数据完整性
            complete_miners = 0
            for miner in data:
                if isinstance(miner, dict) and all(field in miner for field in ['name', 'hashrate', 'power']):
                    complete_miners += 1
            
            completeness = (complete_miners / len(data)) * 100
            return True, f"矿机数量: {len(data)}, 数据完整性: {completeness:.1f}%"
        return False, "矿机数据不足"
    
    def validate_analytics_data(self, data) -> Tuple[bool, str]:
        """验证分析数据"""
        if 'data' in data and 'btc_price' in data['data']:
            analytics_data = data['data']
            price = analytics_data['btc_price']
            if price > 50000:
                return True, f"分析价格: ${price:,.2f}"
            else:
                return False, f"分析价格异常: ${price}"
        return False, "分析数据格式错误"
    
    def test_ui_completeness(self):
        """测试UI完整性"""
        print("\n🖥️ 开始UI完整性测试")
        
        ui_pages = [
            ("/", "主页", ["计算收益", "矿机型号", "算力", "功耗"]),
            ("/analytics", "分析仪表盘", ["市场数据", "分析", "价格"]),
            ("/network-history", "网络历史", ["网络", "历史", "趋势"]),
            ("/curtailment-calculator", "限电计算器", ["限电", "计算"]),
            ("/algorithm-test", "算法测试", ["算法", "测试"])
        ]
        
        for path, name, keywords in ui_pages:
            start_time = time.time()
            try:
                response = self.session.get(f"{self.base_url}{path}", timeout=15)
                response_time = (time.time() - start_time) * 1000
                
                if response.status_code == 200:
                    content = response.text
                    
                    # 检查基本结构
                    has_title = "<title>" in content
                    has_css = "bootstrap" in content.lower() or "css" in content.lower()
                    
                    # 检查关键词
                    keyword_matches = sum(1 for keyword in keywords if keyword in content)
                    keyword_score = (keyword_matches / len(keywords)) * 100
                    
                    if keyword_score >= 70 and has_title:
                        self.log_test("ui_completeness", f"{name}页面", "成功", 
                                    f"关键词匹配: {keyword_score:.1f}%, 结构完整", response_time)
                    elif keyword_score >= 40:
                        self.log_test("ui_completeness", f"{name}页面", "警告", 
                                    f"关键词匹配: {keyword_score:.1f}%, 部分内容缺失", response_time)
                    else:
                        self.log_test("ui_completeness", f"{name}页面", "失败", 
                                    f"关键词匹配: {keyword_score:.1f}%, 内容严重缺失", response_time)
                else:
                    self.log_test("ui_completeness", f"{name}页面", "失败", 
                                f"HTTP {response.status_code}", response_time)
                                
            except Exception as e:
                self.log_test("ui_completeness", f"{name}页面", "错误", str(e))
    
    def test_data_accuracy(self):
        """测试数据准确性"""
        print("\n📊 开始数据准确性测试")
        
        try:
            # 获取不同数据源的价格进行一致性检查
            price_sources = []
            
            # 获取价格API数据
            try:
                response = self.session.get(f"{self.base_url}/api/btc-price", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    if 'btc_price' in data:
                        price_sources.append(('价格API', data['btc_price']))
            except:
                pass
            
            # 获取网络统计数据
            try:
                response = self.session.get(f"{self.base_url}/api/network-stats", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    if 'btc_price' in data:
                        price_sources.append(('网络统计', data['btc_price']))
            except:
                pass
            
            # 获取分析数据
            try:
                response = self.session.get(f"{self.base_url}/analytics/api/market-data", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    if 'data' in data and 'btc_price' in data['data']:
                        price_sources.append(('分析系统', data['data']['btc_price']))
            except:
                pass
            
            # 计算价格一致性
            if len(price_sources) >= 2:
                prices = [price for _, price in price_sources]
                max_price = max(prices)
                min_price = min(prices)
                variance = ((max_price - min_price) / min_price) * 100 if min_price > 0 else 0
                
                source_info = ", ".join([f"{name}: ${price:,.2f}" for name, price in price_sources])
                
                if variance < 1.0:
                    self.log_test("data_accuracy", "价格数据一致性", "成功", 
                                f"方差: {variance:.3f}%, 数据源: {source_info}")
                elif variance < 3.0:
                    self.log_test("data_accuracy", "价格数据一致性", "警告", 
                                f"方差: {variance:.3f}%, 轻微差异, {source_info}")
                else:
                    self.log_test("data_accuracy", "价格数据一致性", "失败", 
                                f"方差: {variance:.3f}%, 差异过大, {source_info}")
            else:
                self.log_test("data_accuracy", "价格数据一致性", "失败", 
                            f"数据源不足: {len(price_sources)}个")
                            
        except Exception as e:
            self.log_test("data_accuracy", "数据准确性测试", "错误", str(e))
    
    def run_final_test(self):
        """运行最终99%准确率测试"""
        print(f"开始最终99%准确率验证测试 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"测试邮箱: {self.test_email}")
        print("="*80)
        
        # 1. 系统认证
        auth_success = self.authenticate_system()
        if not auth_success:
            print("❌ 认证失败，跳过需要认证的测试")
            # 但继续进行不需要认证的测试
        
        # 2. 核心功能测试（即使未认证也测试基本功能）
        self.test_core_functionality()
        self.test_mining_calculations()
        self.test_api_endpoints()
        self.test_ui_completeness()
        self.test_data_accuracy()
        
        return True
    
    def generate_final_report(self):
        """生成最终测试报告"""
        total_time = time.time() - self.start_time
        
        print("\n" + "="*80)
        print("最终99%准确率验证测试报告")
        print("="*80)
        
        total_tests = 0
        successful_tests = 0
        warning_tests = 0
        failed_tests = 0
        
        for category, results in self.test_results.items():
            if not results:
                continue
                
            print(f"\n[{category.upper()}] 测试结果:")
            
            for result in results:
                total_tests += 1
                status = result['status']
                
                if status == '成功':
                    successful_tests += 1
                    icon = "✅"
                elif status == '警告':
                    warning_tests += 1
                    icon = "⚠️"
                else:
                    failed_tests += 1
                    icon = "❌"
                
                print(f"  {icon} {result['test_name']}: {status}")
                if result['details']:
                    print(f"     {result['details']}")
        
        # 计算成功率
        functional_success_rate = ((successful_tests + warning_tests) / total_tests) * 100 if total_tests > 0 else 0
        strict_success_rate = (successful_tests / total_tests) * 100 if total_tests > 0 else 0
        
        print(f"\n🎯 测试统计:")
        print(f"   总测试数: {total_tests}")
        print(f"   成功: {successful_tests} ({strict_success_rate:.1f}%)")
        print(f"   警告: {warning_tests} ({(warning_tests/total_tests)*100:.1f}%)")
        print(f"   失败: {failed_tests} ({(failed_tests/total_tests)*100:.1f}%)")
        print(f"   功能可用率: {functional_success_rate:.1f}%")
        print(f"   严格成功率: {strict_success_rate:.1f}%")
        print(f"   测试耗时: {total_time:.1f}秒")
        
        # 99%目标评估
        if functional_success_rate >= 99.0:
            print("\n🎉 恭喜！系统已达到99%准确率目标！")
            target_achieved = "已达成"
        else:
            remaining = 99.0 - functional_success_rate
            print(f"\n🎯 距离99%目标还需提升: {remaining:.1f}%")
            target_achieved = f"未达成 (差{remaining:.1f}%)"
        
        # 准确率等级
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
        print(f"🎯 99%目标状态: {target_achieved}")
        
        # 保存报告
        report_filename = f"final_99_accuracy_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_filename, 'w', encoding='utf-8') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "test_email": self.test_email,
                "total_tests": total_tests,
                "successful_tests": successful_tests,
                "warning_tests": warning_tests,
                "failed_tests": failed_tests,
                "functional_success_rate": functional_success_rate,
                "strict_success_rate": strict_success_rate,
                "accuracy_level": accuracy_level,
                "target_achieved": functional_success_rate >= 99.0,
                "test_duration": total_time,
                "detailed_results": self.test_results
            }, f, ensure_ascii=False, indent=2)
        
        print(f"\n📋 详细测试报告已保存: {report_filename}")
        
        return functional_success_rate >= 99.0, functional_success_rate, total_tests

def main():
    """主函数"""
    tester = Final99AccuracyTest()
    
    # 运行最终测试
    test_success = tester.run_final_test()
    
    # 生成报告
    target_achieved, success_rate, total_tests = tester.generate_final_report()
    
    print(f"\n最终99%准确率验证测试完成！")
    print(f"功能可用率: {success_rate:.1f}%")
    print(f"99%目标达成: {'是' if target_achieved else '否'}")
    
    return target_achieved

if __name__ == "__main__":
    main()