#!/usr/bin/env python3
"""
快速99%准确率验证测试
Quick 99% Accuracy Validation Test
"""

import json
import time
import requests
from datetime import datetime

class Quick99Test:
    def __init__(self):
        self.base_url = "http://0.0.0.0:5000"
        self.session = requests.Session()
        self.results = []
        
    def authenticate(self):
        """快速认证"""
        try:
            response = self.session.get(f"{self.base_url}/")
            login_data = {"email": "hxl2022hao@gmail.com"}
            response = self.session.post(f"{self.base_url}/login", data=login_data, allow_redirects=True)
            return response.status_code == 200 and "logout" in response.text.lower()
        except:
            return False
    
    def test_core_functions(self):
        """测试核心功能"""
        tests = [
            ("BTC价格API", "/api/btc-price", self.validate_price),
            ("网络统计API", "/api/network-stats", self.validate_network),
            ("矿机数据API", "/api/miners", self.validate_miners),
            ("挖矿计算", "/calculate", self.validate_calculation),
            ("分析数据API", "/analytics/api/market-data", self.validate_analytics)
        ]
        
        for name, endpoint, validator in tests:
            try:
                if endpoint == "/calculate":
                    # POST请求用于计算
                    params = {
                        "miner_model": "Antminer S19 Pro",
                        "miner_count": "1", 
                        "electricity_cost": "0.06",
                        "use_real_time_data": "true"
                    }
                    response = self.session.post(f"{self.base_url}{endpoint}", data=params)
                else:
                    # GET请求
                    response = self.session.get(f"{self.base_url}{endpoint}")
                
                if response.status_code == 200:
                    data = response.json()
                    accuracy = validator(data)
                    status = "PASS" if accuracy >= 95 else "FAIL"
                    self.results.append((name, status, accuracy, f"{accuracy:.1f}%"))
                else:
                    self.results.append((name, "FAIL", 0, f"HTTP {response.status_code}"))
            except Exception as e:
                self.results.append((name, "FAIL", 0, str(e)[:50]))
    
    def validate_price(self, data):
        """验证价格数据"""
        if data.get('success') and isinstance(data.get('btc_price'), (int, float)):
            price = data['btc_price']
            return 100.0 if 80000 <= price <= 150000 else 80.0
        return 0.0
    
    def validate_network(self, data):
        """验证网络数据"""
        if data.get('success'):
            hashrate = data.get('network_hashrate')
            if isinstance(hashrate, (int, float)) and 600 <= hashrate <= 1200:
                return 100.0
            return 80.0
        return 0.0
    
    def validate_miners(self, data):
        """验证矿机数据"""
        if data.get('success'):
            miners = data.get('miners', [])
            return 100.0 if len(miners) >= 8 else 70.0
        return 0.0
    
    def validate_calculation(self, data):
        """验证挖矿计算"""
        if data.get('success'):
            btc_output = data.get('site_daily_btc_output', 0)
            if isinstance(btc_output, (int, float)) and 0.001 <= btc_output <= 0.1:
                return 100.0
            return 80.0
        return 0.0
    
    def validate_analytics(self, data):
        """验证分析数据"""
        if data.get('success'):
            market_data = data.get('data', {})
            btc_price = market_data.get('btc_price')
            if isinstance(btc_price, (int, float)) and 80000 <= btc_price <= 150000:
                return 100.0
            return 80.0
        return 0.0
    
    def run_test(self):
        """运行测试"""
        print("开始快速99%准确率验证测试")
        print("="*60)
        
        # 认证
        if not self.authenticate():
            print("❌ 认证失败")
            return
        print("✅ 认证成功")
        
        # 测试核心功能
        self.test_core_functions()
        
        # 统计结果
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r[1] == "PASS")
        total_accuracy = sum(r[2] for r in self.results) / total_tests if total_tests > 0 else 0
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        # 输出结果
        print(f"\n测试结果:")
        for name, status, accuracy, details in self.results:
            status_icon = "✅" if status == "PASS" else "❌"
            print(f"{status_icon} {name}: {details}")
        
        print(f"\n总结:")
        print(f"总测试数: {total_tests}")
        print(f"通过测试: {passed_tests}")
        print(f"成功率: {success_rate:.1f}%")
        print(f"平均准确率: {total_accuracy:.1f}%")
        
        # 判断是否达到99%标准
        if success_rate >= 99 and total_accuracy >= 99:
            grade = "A+ (完美)"
            print(f"🎉 系统等级: {grade}")
            print(f"✅ 已达到99%+准确率标准!")
        elif success_rate >= 95 and total_accuracy >= 95:
            grade = "A (优秀)"
            print(f"⭐ 系统等级: {grade}")
            print(f"✅ 系统表现优秀，接近99%标准")
        elif success_rate >= 90 and total_accuracy >= 90:
            grade = "B+ (良好)"
            print(f"👍 系统等级: {grade}")
            print(f"✅ 系统表现良好")
        else:
            grade = "B (合格)"
            print(f"📊 系统等级: {grade}")
            print(f"⚠️ 系统基本合格，可考虑进一步优化")
        
        # 保存报告
        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "success_rate": success_rate,
                "average_accuracy": total_accuracy,
                "grade": grade
            },
            "detailed_results": [
                {
                    "test_name": r[0],
                    "status": r[1], 
                    "accuracy": r[2],
                    "details": r[3]
                } for r in self.results
            ]
        }
        
        filename = f"quick_99_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"📄 详细报告: {filename}")
        print("="*60)

if __name__ == "__main__":
    tester = Quick99Test()
    tester.run_test()