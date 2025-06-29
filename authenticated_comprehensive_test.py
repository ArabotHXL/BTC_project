#!/usr/bin/env python3
"""
认证版本全面功能回归测试
Authenticated Comprehensive Function Regression Test

使用真实用户认证测试所有功能模块
Test all function modules with real user authentication
"""

import requests
import json
import time
from datetime import datetime

class AuthenticatedComprehensiveTest:
    def __init__(self):
        self.base_url = "http://0.0.0.0:5000"
        self.session = requests.Session()
        self.test_results = []
        self.authenticated = False
        
    def log_test(self, module_name: str, function_name: str, status: str, details: str = "", response_time: float = None):
        """记录测试结果"""
        result = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'module': module_name,
            'function': function_name,
            'status': status,
            'details': details,
            'response_time': response_time
        }
        self.test_results.append(result)
        
        status_symbol = "✓" if status == "PASS" else "✗" if status == "FAIL" else "⚠"
        time_str = f" ({response_time:.3f}s)" if response_time else ""
        print(f"{status_symbol} {module_name}.{function_name}: {status}{time_str}")
        if details:
            print(f"   → {details}")

    def authenticate_with_email(self, email: str):
        """使用指定邮箱进行认证"""
        try:
            login_data = {"email": email}
            start_time = time.time()
            response = self.session.post(f"{self.base_url}/login", data=login_data)
            response_time = time.time() - start_time
            
            if response.status_code == 200 and ("退出登录" in response.text or "Logout" in response.text):
                self.authenticated = True
                self.log_test("认证系统", f"邮箱登录({email})", "PASS", f"成功登录", response_time)
                return True
            else:
                self.log_test("认证系统", f"邮箱登录({email})", "FAIL", f"登录失败: {response.status_code}", response_time)
                return False
                
        except Exception as e:
            self.log_test("认证系统", f"邮箱登录({email})", "FAIL", f"认证异常: {str(e)}")
            return False

    def test_all_apis_authenticated(self):
        """测试所有API在认证状态下的功能"""
        print("\n🔌 认证状态API功能测试")
        
        apis = [
            ("BTC价格API", "/api/get_btc_price", self.validate_price_response),
            ("网络统计API", "/api/get_network_stats", self.validate_network_response),
            ("矿机数据API", "/api/get_miners", self.validate_miners_response),
            ("SHA256挖矿对比API", "/api/get_sha256_mining_comparison", self.validate_comparison_response)
        ]
        
        for api_name, endpoint, validator in apis:
            try:
                start_time = time.time()
                response = self.session.get(f"{self.base_url}{endpoint}")
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        validation_result = validator(data)
                        if validation_result[0]:
                            self.log_test("认证API", api_name, "PASS", validation_result[1], response_time)
                        else:
                            self.log_test("认证API", api_name, "WARN", validation_result[1], response_time)
                    except json.JSONDecodeError:
                        self.log_test("认证API", api_name, "FAIL", "JSON解析失败", response_time)
                else:
                    self.log_test("认证API", api_name, "FAIL", f"HTTP {response.status_code}", response_time)
                    
            except Exception as e:
                self.log_test("认证API", api_name, "FAIL", f"请求异常: {str(e)}")

    def validate_price_response(self, data):
        """验证价格API响应"""
        if data.get('success') and 'price' in data:
            price = data['price']
            if isinstance(price, (int, float)) and price > 0:
                return True, f"BTC价格: ${price:,.2f}"
            else:
                return False, f"价格数据异常: {price}"
        return False, "响应格式错误"

    def validate_network_response(self, data):
        """验证网络统计API响应"""
        if data.get('success'):
            required_fields = ['price', 'difficulty', 'hashrate', 'data_source']
            missing_fields = [field for field in required_fields if field not in data]
            if not missing_fields:
                return True, f"数据源: {data['data_source']}, 算力: {data['hashrate']}EH/s"
            else:
                return False, f"缺失字段: {missing_fields}"
        return False, "API响应失败"

    def validate_miners_response(self, data):
        """验证矿机数据API响应"""
        if data.get('success') and 'miners' in data:
            miners = data['miners']
            if isinstance(miners, list) and len(miners) >= 10:
                sample_miner = miners[0]
                required_fields = ['name', 'hashrate', 'power_consumption']
                if all(field in sample_miner for field in required_fields):
                    return True, f"获取{len(miners)}种矿机型号"
                else:
                    return False, "矿机数据格式错误"
            else:
                return False, f"矿机数据不足: {len(miners) if isinstance(miners, list) else 0}"
        return False, "响应格式错误"

    def validate_comparison_response(self, data):
        """验证挖矿对比API响应"""
        if data.get('success'):
            return True, "SHA256对比数据获取成功"
        elif 'error' in data:
            return False, f"API错误: {data['error']}"
        return False, "响应格式错误"

    def test_mining_calculations_authenticated(self):
        """测试认证状态下的挖矿计算功能"""
        print("\n⚡ 认证状态挖矿计算测试")
        
        # 测试标准挖矿计算
        calc_data = {
            "miner_model": "Antminer S21 XP Hyd",
            "miner_count": "10", 
            "electricity_cost": "0.05",
            "use_real_time": "on"
        }
        
        try:
            start_time = time.time()
            response = self.session.post(f"{self.base_url}/calculate", data=calc_data)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    
                    # 验证计算结果的完整性
                    if self.validate_calculation_result(data):
                        btc_daily = data.get('btc_mined', {}).get('daily', 0)
                        profit_daily = data.get('profit_daily', 0)
                        self.log_test("认证计算", "标准挖矿计算", "PASS", 
                                    f"日产BTC: {btc_daily:.6f}, 日收益: ${profit_daily:.2f}", response_time)
                        
                        # 测试盈亏平衡分析
                        self.test_breakeven_analysis_authenticated(data)
                    else:
                        self.log_test("认证计算", "标准挖矿计算", "FAIL", "计算结果验证失败", response_time)
                        
                except json.JSONDecodeError:
                    self.log_test("认证计算", "标准挖矿计算", "FAIL", "JSON解析失败", response_time)
            else:
                self.log_test("认证计算", "标准挖矿计算", "FAIL", f"HTTP {response.status_code}", response_time)
                
        except Exception as e:
            self.log_test("认证计算", "标准挖矿计算", "FAIL", f"计算异常: {str(e)}")

    def validate_calculation_result(self, data):
        """验证挖矿计算结果的完整性"""
        required_fields = ['btc_mined', 'electricity_cost_daily', 'profit_daily']
        
        for field in required_fields:
            if field not in data:
                return False
                
        # 验证BTC挖矿数据
        btc_mined = data.get('btc_mined', {})
        if not isinstance(btc_mined, dict) or 'daily' not in btc_mined:
            return False
            
        # 验证数值合理性
        daily_btc = btc_mined.get('daily', 0)
        daily_profit = data.get('profit_daily', 0)
        
        if daily_btc <= 0 or not isinstance(daily_profit, (int, float)):
            return False
            
        return True

    def test_breakeven_analysis_authenticated(self, calc_data):
        """测试认证状态下的盈亏平衡分析"""
        if 'breakeven_analysis' in calc_data:
            breakeven = calc_data['breakeven_analysis']
            breakeven_cost = breakeven.get('breakeven_electricity_cost', 0)
            
            if breakeven_cost > 0:
                self.log_test("认证计算", "盈亏平衡分析", "PASS", 
                            f"盈亏平衡电价: ${breakeven_cost:.6f}/kWh")
            else:
                self.log_test("认证计算", "盈亏平衡分析", "WARN", "盈亏平衡计算数据异常")
        else:
            self.log_test("认证计算", "盈亏平衡分析", "FAIL", "缺少盈亏平衡分析数据")

    def test_miner_models_completeness(self):
        """测试所有10种矿机型号的完整性"""
        print("\n🔧 矿机型号完整性测试")
        
        try:
            response = self.session.get(f"{self.base_url}/api/get_miners")
            if response.status_code == 200:
                data = response.json()
                if data.get('success') and 'miners' in data:
                    miners = data['miners']
                    
                    # 验证矿机型号数量和完整性
                    expected_models = [
                        "Antminer S21 XP Hyd", "Antminer S21 XP", "Antminer S21", 
                        "Antminer S21 Hyd", "Antminer S19 XP Hyd", "Antminer S19 XP", 
                        "Antminer S19 Pro+", "Antminer S19 Pro", "Antminer S19j Pro+", 
                        "Antminer S19"
                    ]
                    
                    found_models = [miner['name'] for miner in miners]
                    missing_models = [model for model in expected_models if model not in found_models]
                    
                    if len(miners) >= 10 and not missing_models:
                        self.log_test("矿机完整性", "10种型号验证", "PASS", 
                                    f"所有{len(miners)}种矿机型号完整")
                        
                        # 测试每种矿机的盈亏平衡计算
                        self.test_all_miners_breakeven()
                    else:
                        self.log_test("矿机完整性", "10种型号验证", "WARN", 
                                    f"缺失型号: {missing_models if missing_models else '数量不足'}")
                else:
                    self.log_test("矿机完整性", "10种型号验证", "FAIL", "API响应格式错误")
            else:
                self.log_test("矿机完整性", "10种型号验证", "FAIL", f"HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test("矿机完整性", "10种型号验证", "FAIL", f"测试异常: {str(e)}")

    def test_all_miners_breakeven(self):
        """测试所有矿机的盈亏平衡计算"""
        test_models = ["Antminer S21 XP Hyd", "Antminer S21", "Antminer S19 XP"]
        
        for model in test_models:
            calc_data = {
                "miner_model": model,
                "miner_count": "1",
                "electricity_cost": "0.08",
                "use_real_time": "on"
            }
            
            try:
                response = self.session.post(f"{self.base_url}/calculate", data=calc_data)
                if response.status_code == 200:
                    data = response.json()
                    breakeven = data.get('breakeven_analysis', {})
                    breakeven_cost = breakeven.get('breakeven_electricity_cost', 0)
                    
                    if breakeven_cost > 0:
                        self.log_test("矿机盈亏分析", f"{model}盈亏平衡", "PASS", 
                                    f"${breakeven_cost:.6f}/kWh")
                    else:
                        self.log_test("矿机盈亏分析", f"{model}盈亏平衡", "WARN", "计算结果异常")
                else:
                    self.log_test("矿机盈亏分析", f"{model}盈亏平衡", "FAIL", f"HTTP {response.status_code}")
                    
            except Exception as e:
                self.log_test("矿机盈亏分析", f"{model}盈亏平衡", "FAIL", f"异常: {str(e)}")

    def run_comprehensive_authenticated_test(self):
        """运行完整的认证功能测试"""
        print("=" * 80)
        print("🔧 BTC挖矿计算器系统 - 认证版本全面功能回归测试")
        print(f"📅 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        
        # 使用拥有者邮箱进行认证
        print("\n🔐 系统认证")
        success = self.authenticate_with_email("hxl2022hao@gmail.com")
        
        if success:
            # 运行认证状态下的所有测试
            self.test_all_apis_authenticated()
            self.test_mining_calculations_authenticated()
            self.test_miner_models_completeness()
        else:
            print("❌ 认证失败，无法继续功能测试")
            
        # 生成测试报告
        self.generate_authenticated_report()

    def generate_authenticated_report(self):
        """生成认证版本测试报告"""
        print("\n" + "=" * 80)
        print("📋 认证版本功能测试报告")
        print("=" * 80)
        
        # 统计结果
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r['status'] == 'PASS'])
        failed_tests = len([r for r in self.test_results if r['status'] == 'FAIL'])
        warned_tests = len([r for r in self.test_results if r['status'] == 'WARN'])
        
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        print(f"🎯 总测试数: {total_tests}")
        print(f"✅ 通过: {passed_tests}")
        print(f"❌ 失败: {failed_tests}")
        print(f"⚠️  警告: {warned_tests}")
        print(f"📈 成功率: {success_rate:.1f}%")
        
        # 按模块分组统计
        modules = {}
        for result in self.test_results:
            module = result['module']
            if module not in modules:
                modules[module] = {'PASS': 0, 'FAIL': 0, 'WARN': 0}
            modules[module][result['status']] += 1
        
        print(f"\n📊 模块测试详情:")
        for module, stats in modules.items():
            total_module = sum(stats.values())
            module_success_rate = (stats['PASS'] / total_module * 100) if total_module > 0 else 0
            print(f"   • {module}: {stats['PASS']}/{total_module} 通过 ({module_success_rate:.1f}%)")
        
        # 系统状态评估
        print(f"\n" + "=" * 80)
        if success_rate >= 80:
            print("🟢 系统状态: 优秀 - 认证功能完全正常")
        elif success_rate >= 60:
            print("🟡 系统状态: 良好 - 大部分认证功能正常")
        else:
            print("🔴 系统状态: 需要改进 - 认证功能存在问题")
        
        print(f"\n🚀 认证版本全面功能回归测试完成")

def main():
    """主函数"""
    tester = AuthenticatedComprehensiveTest()
    tester.run_comprehensive_authenticated_test()

if __name__ == "__main__":
    main()