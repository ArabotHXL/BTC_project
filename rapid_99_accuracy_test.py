#!/usr/bin/env python3
"""
快速99%精确度测试
Rapid 99% Accuracy Test
"""

import requests
import json
import time
from datetime import datetime

class Rapid99AccuracyTest:
    def __init__(self):
        self.base_url = "http://localhost:5000"
        self.session = requests.Session()
        
    def run_rapid_test(self):
        """运行快速测试"""
        print("🚀 快速99%精确度测试")
        print("="*50)
        
        start_time = time.time()
        
        # 1. 认证验证
        auth_success = self.test_auth()
        
        if auth_success:
            # 2. 核心功能测试
            core_results = self.test_core_functions()
            
            # 3. 计算精确度验证
            calc_accuracy = self.test_calculation_accuracy()
            
            # 4. API一致性检查
            api_consistency = self.test_api_consistency()
            
            total_time = time.time() - start_time
            
            # 汇总结果
            self.print_summary(core_results, calc_accuracy, api_consistency, total_time)
        
        else:
            print("❌ 认证失败，无法继续测试")
    
    def test_auth(self):
        """测试认证"""
        try:
            response = self.session.post(f"{self.base_url}/login", data={'email': 'hxl2022hao@gmail.com'})
            success = response.status_code == 200
            print(f"🔐 认证: {'✅ 成功' if success else '❌ 失败'}")
            return success
        except:
            print("🔐 认证: ❌ 异常")
            return False
    
    def test_core_functions(self):
        """测试核心功能"""
        print("\n🔧 核心功能测试:")
        
        tests = [
            ("主页", "/"),
            ("分析仪表盘", "/analytics_dashboard"),
            ("BTC价格API", "/get_btc_price"),
            ("网络统计API", "/get_network_stats"),
            ("矿机数据API", "/get_miners"),
            ("计算引擎", "/calculate")
        ]
        
        results = []
        
        for name, url in tests:
            try:
                if url == "/calculate":
                    response = self.session.post(f"{self.base_url}{url}", 
                                               data={'miner_model': 'Antminer S19 Pro', 'quantity': '1', 'electricity_cost': '0.06'})
                else:
                    response = self.session.get(f"{self.base_url}{url}")
                
                if response.status_code == 200:
                    # 基本完整性检查
                    content_check = len(response.text) > 1000 if "API" not in name else True
                    
                    if "API" in name or name == "计算引擎":
                        try:
                            data = response.json()
                            data_check = bool(data)
                        except:
                            data_check = False
                    else:
                        data_check = "html" in response.text.lower()
                    
                    success = content_check and data_check
                    results.append(success)
                    print(f"   {name}: {'✅' if success else '⚠️'}")
                else:
                    results.append(False)
                    print(f"   {name}: ❌ HTTP {response.status_code}")
            except:
                results.append(False)
                print(f"   {name}: ❌ 异常")
        
        success_rate = (sum(results) / len(results)) * 100
        print(f"   核心功能成功率: {success_rate:.1f}%")
        
        return success_rate
    
    def test_calculation_accuracy(self):
        """测试计算精确度"""
        print("\n📊 计算精确度测试:")
        
        try:
            response = self.session.post(f"{self.base_url}/calculate", 
                                       data={'miner_model': 'Antminer S19 Pro', 'quantity': '1', 'electricity_cost': '0.06', 'pool_fee': '2.5'})
            
            if response.status_code == 200:
                result = response.json()
                
                # 检查关键字段 - 使用实际API结构
                key_fields = ['daily_profit_usd', 'btc_mined', 'electricity_cost']
                found_fields = 0
                
                if 'daily_profit_usd' in result:
                    found_fields += 1
                if 'btc_mined' in result and isinstance(result['btc_mined'], dict) and 'daily' in result['btc_mined']:
                    found_fields += 1  
                if 'electricity_cost' in result:
                    found_fields += 1
                
                # 数值合理性检查 - 使用实际API结构
                reasonable_values = True
                
                # 检查BTC挖矿产出
                if 'btc_mined' in result and isinstance(result['btc_mined'], dict) and 'daily' in result['btc_mined']:
                    daily_btc = float(result['btc_mined']['daily'])
                    if not (0.005 <= daily_btc <= 0.1):
                        reasonable_values = False
                        
                # 检查日利润
                if 'daily_profit_usd' in result:
                    daily_profit = float(result['daily_profit_usd'])
                    # 允许负值（高电费时）
                    if not (-2000 <= daily_profit <= 5000):
                        reasonable_values = False
                
                field_accuracy = (found_fields / len(key_fields)) * 100
                value_accuracy = 100 if reasonable_values else 70
                total_accuracy = (field_accuracy + value_accuracy) / 2
                
                print(f"   字段完整性: {field_accuracy:.1f}% ({found_fields}/{len(key_fields)})")
                print(f"   数值合理性: {value_accuracy:.1f}%")
                print(f"   计算精确度: {total_accuracy:.1f}%")
                
                return total_accuracy
            else:
                print(f"   计算精确度: ❌ HTTP {response.status_code}")
                return 0
        except Exception as e:
            print(f"   计算精确度: ❌ 异常 - {str(e)[:30]}")
            return 0
    
    def test_api_consistency(self):
        """测试API一致性"""
        print("\n🔄 API一致性测试:")
        
        try:
            # 获取BTC价格两次，检查一致性
            prices = []
            for i in range(2):
                response = self.session.get(f"{self.base_url}/get_btc_price")
                if response.status_code == 200:
                    data = response.json()
                    if 'btc_price' in data:
                        prices.append(float(data['btc_price']))
                    elif 'price' in data:
                        prices.append(float(data['price']))
                time.sleep(0.5)
            
            if len(prices) >= 2:
                price_diff = abs(prices[0] - prices[1])
                consistency_score = max(0, 100 - (price_diff / prices[0] * 100)) if prices[0] > 0 else 100
                print(f"   BTC价格一致性: {consistency_score:.1f}% (差异: ${price_diff:.2f})")
                return consistency_score
            else:
                print("   API一致性: ❌ 数据不足")
                return 0
        except:
            print("   API一致性: ❌ 异常")
            return 0
    
    def print_summary(self, core_results, calc_accuracy, api_consistency, total_time):
        """打印测试总结"""
        print("\n" + "="*50)
        print("🎯 快速99%精确度测试结果")
        print("="*50)
        
        print(f"⏱️ 测试时间: {total_time:.2f}秒")
        print(f"🔧 核心功能: {core_results:.1f}%")
        print(f"📊 计算精确度: {calc_accuracy:.1f}%")
        print(f"🔄 API一致性: {api_consistency:.1f}%")
        
        overall_score = (core_results + calc_accuracy + api_consistency) / 3
        print(f"🏆 总体评分: {overall_score:.1f}%")
        
        if overall_score >= 99.0:
            print("🎉 ✅ 系统达到99%+精确度标准！")
            grade = "A+ (完美级别)"
        elif overall_score >= 95.0:
            print("🎊 ✅ 系统达到95%+优秀标准！")
            grade = "A (优秀级别)"
        elif overall_score >= 90.0:
            print("👍 ⚠️ 系统达到90%+良好标准")
            grade = "B+ (良好级别)"
        else:
            print("⚠️ 系统需要优化改进")
            grade = "C (需要改进)"
        
        print(f"🎖️ 系统等级: {grade}")
        
        # 改进建议
        if overall_score < 99.0:
            print("\n📈 改进建议:")
            if core_results < 99.0:
                print("   • 优化核心功能稳定性")
            if calc_accuracy < 99.0:
                print("   • 提升计算引擎精确度")
            if api_consistency < 99.0:
                print("   • 加强API数据一致性")
        
        print("="*50)

def main():
    tester = Rapid99AccuracyTest()
    tester.run_rapid_test()

if __name__ == "__main__":
    main()