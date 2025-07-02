#!/usr/bin/env python3
"""
快速回归测试 - BTC挖矿计算器
Quick Regression Test - BTC Mining Calculator

检查所有核心功能和数值计算准确性
"""

import requests
import json
import time
from datetime import datetime

class QuickRegressionTest:
    def __init__(self):
        self.base_url = "http://0.0.0.0:5000"
        self.session = requests.Session()
        self.test_results = []
        
    def log_test(self, category: str, test_name: str, status: str, details: str = "", value: str = ""):
        """记录测试结果"""
        result = {
            'category': category,
            'test_name': test_name,
            'status': status,
            'details': details,
            'value': value,
            'timestamp': datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        # 实时显示结果
        if status == "PASS":
            icon = "✓"
        elif status == "FAIL":
            icon = "✗"
        elif status == "WARN":
            icon = "⚠"
        else:
            icon = "ℹ"
            
        print(f"{icon} {category}.{test_name}: {status}")
        if details:
            print(f"   → {details}")
        if value:
            print(f"   → 数值: {value}")

    def authenticate(self):
        """系统认证"""
        try:
            # 使用拥有者邮箱登录
            response = self.session.post(f"{self.base_url}/login", 
                                       data={'email': 'hxl2022hao@gmail.com'})
            if response.status_code == 200:
                self.log_test("认证", "拥有者登录", "PASS", "成功登录系统")
                return True
            else:
                self.log_test("认证", "拥有者登录", "FAIL", f"登录失败: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("认证", "拥有者登录", "FAIL", f"登录异常: {str(e)}")
            return False

    def test_core_apis(self):
        """测试核心API"""
        apis = [
            ("BTC价格API", "/api/btc-price", self.validate_price_api),
            ("网络统计API", "/api/network-stats", self.validate_network_api),
            ("矿机数据API", "/api/miners", self.validate_miners_api),
            ("SHA256对比API", "/api/sha256-comparison", self.validate_comparison_api)
        ]
        
        for name, endpoint, validator in apis:
            try:
                start_time = time.time()
                response = self.session.get(f"{self.base_url}{endpoint}")
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    data = response.json()
                    is_valid, details, value = validator(data)
                    if is_valid:
                        self.log_test("核心API", name, "PASS", 
                                    f"{details} ({response_time:.3f}s)", value)
                    else:
                        self.log_test("核心API", name, "FAIL", details)
                else:
                    self.log_test("核心API", name, "FAIL", 
                                f"HTTP {response.status_code}")
            except Exception as e:
                self.log_test("核心API", name, "FAIL", f"异常: {str(e)}")

    def validate_price_api(self, data):
        """验证价格API"""
        if 'btc_price' in data and data['btc_price'] > 0:
            price = f"${data['btc_price']:,.2f}"
            return True, "BTC价格获取成功", price
        return False, "价格数据无效", ""

    def validate_network_api(self, data):
        """验证网络统计API"""
        if ('hashrate' in data and 'difficulty' in data and 
            data['hashrate'] > 0 and data['difficulty'] > 0):
            hashrate = f"{data['hashrate']:.1f} EH/s"
            difficulty = f"{data['difficulty']/1e12:.2f}T"
            return True, "网络数据完整", f"算力{hashrate}, 难度{difficulty}"
        return False, "网络数据缺失", ""

    def validate_miners_api(self, data):
        """验证矿机数据API"""
        if 'miners' in data and len(data['miners']) >= 10:
            count = len(data['miners'])
            return True, f"矿机数据完整", f"{count}种型号"
        return False, "矿机数据不足", ""

    def validate_comparison_api(self, data):
        """验证SHA256对比API"""
        if 'coins' in data and len(data['coins']) > 0:
            count = len(data['coins'])
            return True, f"SHA256对比数据", f"{count}种币种"
        return False, "对比数据为空", ""

    def test_mining_calculations(self):
        """测试挖矿计算功能"""
        # 测试标准挖矿计算
        test_data = {
            'miner_model': 'Antminer S19 Pro',
            'miner_count': '1',
            'electricity_cost': '0.05',
            'use_real_time': 'on'
        }
        
        try:
            response = self.session.post(f"{self.base_url}/calculate", data=test_data)
            if response.status_code == 200:
                data = response.json()
                
                # 验证关键计算结果
                if 'daily_btc' in data and 'daily_profit_usd' in data:
                    daily_btc = data['daily_btc']
                    daily_profit = data['daily_profit_usd']
                    
                    # 检查数值合理性
                    if 0.00001 <= daily_btc <= 0.001 and -100 <= daily_profit <= 100:
                        self.log_test("挖矿计算", "S19Pro计算", "PASS", 
                                    "数值在合理范围", 
                                    f"日产{daily_btc:.6f}BTC, 利润${daily_profit:.2f}")
                    else:
                        self.log_test("挖矿计算", "S19Pro计算", "WARN", 
                                    "数值可能异常",
                                    f"日产{daily_btc:.6f}BTC, 利润${daily_profit:.2f}")
                else:
                    self.log_test("挖矿计算", "S19Pro计算", "FAIL", "缺少关键结果字段")
            else:
                self.log_test("挖矿计算", "S19Pro计算", "FAIL", f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("挖矿计算", "S19Pro计算", "FAIL", f"计算异常: {str(e)}")

    def test_analytics_system(self):
        """测试分析系统"""
        analytics_apis = [
            ("市场数据", "/analytics/api/market-data"),
            ("技术指标", "/analytics/api/technical-indicators"),
            ("价格历史", "/analytics/api/price-history")
        ]
        
        for name, endpoint in analytics_apis:
            try:
                response = self.session.get(f"{self.base_url}{endpoint}")
                if response.status_code == 200:
                    data = response.json()
                    if 'success' in data and data['success']:
                        self.log_test("分析系统", name, "PASS", "数据获取成功")
                    else:
                        self.log_test("分析系统", name, "WARN", "数据可能不完整")
                else:
                    self.log_test("分析系统", name, "FAIL", f"HTTP {response.status_code}")
            except Exception as e:
                self.log_test("分析系统", name, "FAIL", f"异常: {str(e)}")

    def test_investment_analysis(self):
        """测试投资分析功能"""
        # 测试不同矿机型号的盈亏平衡计算
        miners = ['Antminer S19 Pro', 'Antminer S21 XP', 'Antminer S21']
        
        for miner in miners:
            try:
                test_data = {
                    'miner_model': miner,
                    'miner_count': '1',
                    'electricity_cost': '0.05',
                    'use_real_time': 'on'
                }
                
                response = self.session.post(f"{self.base_url}/calculate", data=test_data)
                if response.status_code == 200:
                    data = response.json()
                    if 'breakeven_electricity' in data:
                        breakeven = data['breakeven_electricity']
                        if 0.01 <= breakeven <= 0.50:  # 合理的盈亏平衡电价范围
                            self.log_test("投资分析", f"{miner}盈亏平衡", "PASS", 
                                        "盈亏平衡计算正常", f"${breakeven:.4f}/kWh")
                        else:
                            self.log_test("投资分析", f"{miner}盈亏平衡", "WARN", 
                                        "盈亏平衡值异常", f"${breakeven:.4f}/kWh")
                    else:
                        self.log_test("投资分析", f"{miner}盈亏平衡", "FAIL", "缺少盈亏平衡数据")
                else:
                    self.log_test("投资分析", f"{miner}盈亏平衡", "FAIL", f"HTTP {response.status_code}")
            except Exception as e:
                self.log_test("投资分析", f"{miner}盈亏平衡", "FAIL", f"异常: {str(e)}")

    def run_quick_test(self):
        """运行快速回归测试"""
        print("=" * 80)
        print("🚀 BTC挖矿计算器 - 快速回归测试")
        print(f"📅 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        print()
        
        # 认证
        if not self.authenticate():
            print("❌ 认证失败，终止测试")
            return
        
        print("\n🔌 核心API测试")
        self.test_core_apis()
        
        print("\n⚡ 挖矿计算测试")
        self.test_mining_calculations()
        
        print("\n📊 分析系统测试")
        self.test_analytics_system()
        
        print("\n💰 投资分析测试")
        self.test_investment_analysis()
        
        self.generate_summary()

    def generate_summary(self):
        """生成测试摘要"""
        total = len(self.test_results)
        passed = len([r for r in self.test_results if r['status'] == 'PASS'])
        failed = len([r for r in self.test_results if r['status'] == 'FAIL'])
        warned = len([r for r in self.test_results if r['status'] == 'WARN'])
        
        print("\n" + "=" * 80)
        print("📋 测试摘要")
        print("=" * 80)
        print(f"总计测试: {total}")
        print(f"✓ 通过: {passed} ({passed/total*100:.1f}%)")
        print(f"✗ 失败: {failed} ({failed/total*100:.1f}%)")
        print(f"⚠ 警告: {warned} ({warned/total*100:.1f}%)")
        
        success_rate = passed / total * 100
        if success_rate >= 90:
            print(f"\n🎉 系统状态: 优秀 ({success_rate:.1f}%)")
        elif success_rate >= 75:
            print(f"\n✅ 系统状态: 良好 ({success_rate:.1f}%)")
        elif success_rate >= 60:
            print(f"\n⚠️ 系统状态: 需要优化 ({success_rate:.1f}%)")
        else:
            print(f"\n❌ 系统状态: 需要修复 ({success_rate:.1f}%)")
        
        # 显示失败的测试
        if failed > 0:
            print(f"\n🔧 需要修复的问题:")
            for result in self.test_results:
                if result['status'] == 'FAIL':
                    print(f"   • {result['category']}.{result['test_name']}: {result['details']}")

def main():
    """主函数"""
    test = QuickRegressionTest()
    test.run_quick_test()

if __name__ == "__main__":
    main()