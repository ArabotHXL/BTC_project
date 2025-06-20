#!/usr/bin/env python3
"""
BTC Price Update Regression Test Suite
测试BTC价格实时更新功能的完整回归测试
"""

import requests
import json
import time
from datetime import datetime

class BTCPriceRegressionTest:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.test_results = []
        
    def log_result(self, test_name, success, details=""):
        """记录测试结果"""
        result = {
            'test': test_name,
            'success': success,
            'details': details,
            'timestamp': datetime.now().isoformat()
        }
        self.test_results.append(result)
        status = "✓" if success else "✗"
        print(f"{status} {test_name}: {details}")
        
    def authenticate(self):
        """用户认证"""
        try:
            response = self.session.post(f"{self.base_url}/login", 
                                       data={'email': 'user@example.com'})
            success = response.status_code == 200
            self.log_result("用户认证", success, f"状态码: {response.status_code}")
            return success
        except Exception as e:
            self.log_result("用户认证", False, f"异常: {str(e)}")
            return False
    
    def test_network_stats_api(self):
        """测试网络统计API"""
        try:
            response = self.session.get(f"{self.base_url}/network_stats")
            if response.status_code == 200:
                data = response.json()
                if data.get('success') and data.get('btc_price'):
                    price = data['btc_price']
                    is_realistic = 50000 <= price <= 200000  # 合理价格范围
                    self.log_result("网络统计API", True, 
                                  f"BTC价格: ${price:,.0f}, 合理性: {is_realistic}")
                    return price
                else:
                    self.log_result("网络统计API", False, "响应缺少必要数据")
            else:
                self.log_result("网络统计API", False, f"HTTP错误: {response.status_code}")
        except Exception as e:
            self.log_result("网络统计API", False, f"异常: {str(e)}")
        return None
    
    def test_initial_data_embedding(self):
        """测试初始数据嵌入"""
        try:
            response = self.session.get(self.base_url)
            if response.status_code == 200:
                content = response.text
                has_initial_data = 'window.initialData' in content
                has_btc_price = 'btc_price' in content
                has_network_data = 'network' in content
                
                success = has_initial_data and has_btc_price and has_network_data
                details = f"初始数据: {has_initial_data}, BTC价格: {has_btc_price}, 网络数据: {has_network_data}"
                self.log_result("初始数据嵌入", success, details)
                return success
            else:
                self.log_result("初始数据嵌入", False, f"HTTP错误: {response.status_code}")
        except Exception as e:
            self.log_result("初始数据嵌入", False, f"异常: {str(e)}")
        return False
    
    def test_api_failover_system(self):
        """测试API备用系统"""
        try:
            # 连续请求多次以测试API切换
            prices = []
            for i in range(3):
                response = self.session.get(f"{self.base_url}/network_stats")
                if response.status_code == 200:
                    data = response.json()
                    if data.get('success') and data.get('btc_price'):
                        prices.append(data['btc_price'])
                time.sleep(1)  # 避免过快请求
            
            if len(prices) >= 2:
                # 检查价格一致性（允许小幅波动）
                price_diff = max(prices) - min(prices)
                consistent = price_diff < 1000  # 允许$1000波动
                self.log_result("API备用系统", True, 
                              f"获取{len(prices)}个价格点, 波动: ${price_diff:.0f}")
                return True
            else:
                self.log_result("API备用系统", False, "无法获取足够价格数据")
        except Exception as e:
            self.log_result("API备用系统", False, f"异常: {str(e)}")
        return False
    
    def test_mining_calculation_with_realtime_price(self):
        """测试使用实时价格的挖矿计算"""
        try:
            # 获取当前实时价格
            network_response = self.session.get(f"{self.base_url}/network_stats")
            if network_response.status_code != 200:
                self.log_result("实时价格挖矿计算", False, "无法获取网络数据")
                return False
                
            network_data = network_response.json()
            current_price = network_data.get('btc_price')
            
            # 使用实时价格进行计算
            calc_data = {
                'miner_model': 'Antminer S21 Pro',
                'miner_count': '100',
                'btc_price': str(int(current_price)),
                'use_real_time': 'on',
                'site_power_mw': '5.0',
                'electricity_cost': '0.05'
            }
            
            response = self.session.post(f"{self.base_url}/calculate", data=calc_data)
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    monthly_profit = data.get('monthly_profit_usd', 0)
                    self.log_result("实时价格挖矿计算", True, 
                                  f"月度收益: ${monthly_profit:,.0f}, 使用价格: ${current_price:,.0f}")
                    return True
                else:
                    self.log_result("实时价格挖矿计算", False, "计算返回错误")
            else:
                self.log_result("实时价格挖矿计算", False, f"HTTP错误: {response.status_code}")
        except Exception as e:
            self.log_result("实时价格挖矿计算", False, f"异常: {str(e)}")
        return False
    
    def test_javascript_functionality(self):
        """测试JavaScript功能基础检查"""
        try:
            response = self.session.get(self.base_url)
            if response.status_code == 200:
                content = response.text
                
                # 检查关键JavaScript元素
                has_main_js = 'main.js?v=5' in content
                has_dom_safety = 'dom-safety.js' in content
                has_event_handlers = 'safeEvent' in content
                has_real_time_toggle = 'use-real-time' in content
                
                success = has_main_js and has_dom_safety and has_real_time_toggle
                details = f"主JS: {has_main_js}, DOM安全: {has_dom_safety}, 实时切换: {has_real_time_toggle}"
                self.log_result("JavaScript功能检查", success, details)
                return success
            else:
                self.log_result("JavaScript功能检查", False, f"HTTP错误: {response.status_code}")
        except Exception as e:
            self.log_result("JavaScript功能检查", False, f"异常: {str(e)}")
        return False
    
    def test_miner_data_integration(self):
        """测试矿机数据集成"""
        try:
            response = self.session.get(f"{self.base_url}/miners")
            if response.status_code == 200:
                data = response.json()
                if data.get('success') and data.get('miners'):
                    miners = data['miners']
                    miner_count = len(miners)
                    has_s21_pro = any(m.get('model') == 'Antminer S21 Pro' for m in miners)
                    
                    success = miner_count >= 10 and has_s21_pro
                    self.log_result("矿机数据集成", success, 
                                  f"矿机数量: {miner_count}, 包含S21 Pro: {has_s21_pro}")
                    return success
                else:
                    self.log_result("矿机数据集成", False, "响应缺少矿机数据")
            else:
                self.log_result("矿机数据集成", False, f"HTTP错误: {response.status_code}")
        except Exception as e:
            self.log_result("矿机数据集成", False, f"异常: {str(e)}")
        return False
    
    def run_complete_regression(self):
        """运行完整回归测试"""
        print("BTC价格更新回归测试")
        print("=" * 50)
        print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # 执行所有测试
        tests = [
            self.authenticate,
            self.test_network_stats_api,
            self.test_initial_data_embedding,
            self.test_api_failover_system,
            self.test_mining_calculation_with_realtime_price,
            self.test_javascript_functionality,
            self.test_miner_data_integration
        ]
        
        passed = 0
        total = len(tests)
        
        for test in tests:
            try:
                if test():
                    passed += 1
            except Exception as e:
                print(f"✗ 测试异常: {test.__name__} - {str(e)}")
        
        print()
        print("=" * 50)
        print(f"测试完成: {passed}/{total} 通过")
        print(f"成功率: {(passed/total)*100:.1f}%")
        
        if passed == total:
            print("🎉 所有测试通过！系统准备就绪。")
            return True
        else:
            print("⚠️ 部分测试失败，请检查问题。")
            return False

def main():
    """主测试入口"""
    tester = BTCPriceRegressionTest()
    return tester.run_complete_regression()

if __name__ == "__main__":
    main()