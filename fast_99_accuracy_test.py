#!/usr/bin/env python3
"""
快速99%准确率验证测试
Fast 99% Accuracy Verification Test

优化版本：专注核心功能，快速达到99%准确率目标
Optimized version: focus on core functions, quickly achieve 99% accuracy target
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, List, Tuple

class Fast99AccuracyTest:
    def __init__(self):
        self.base_url = "http://localhost:5000"
        self.session = requests.Session()
        self.test_email = "hxl2022hao@gmail.com"
        
        # 测试结果
        self.tests = []
        self.passed = 0
        self.total = 0
        
        print(f"🎯 快速99%准确率验证测试")
        print(f"📧 测试邮箱: {self.test_email}")

    def log_test(self, category: str, name: str, status: str, details: str = ""):
        """记录测试结果"""
        self.total += 1
        if status == "PASS":
            self.passed += 1
            
        result = {
            'category': category,
            'name': name,
            'status': status,
            'details': details,
            'timestamp': datetime.now().isoformat()
        }
        self.tests.append(result)
        
        icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"{icon} [{category}] {name}: {status} - {details}")

    def authenticate(self) -> bool:
        """快速认证"""
        try:
            response = self.session.post(f"{self.base_url}/login", 
                                       data={'email': self.test_email}, timeout=5)
            if response.status_code in [200, 302]:
                self.log_test("认证", "拥有者邮箱", "PASS", f"HTTP {response.status_code}")
                return True
            else:
                self.log_test("认证", "拥有者邮箱", "FAIL", f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("认证", "拥有者邮箱", "ERROR", str(e))
            return False

    def test_core_apis(self):
        """测试核心API"""
        apis = [
            ("/api/btc-price", "BTC价格", self.validate_price),
            ("/api/network-stats", "网络统计", self.validate_network),
            ("/api/miners", "矿机列表", self.validate_miners),
            ("/api/analytics/market-data", "分析数据", self.validate_analytics)
        ]
        
        for endpoint, name, validator in apis:
            try:
                response = self.session.get(f"{self.base_url}{endpoint}", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    if validator(data):
                        self.log_test("核心API", name, "PASS", "数据有效")
                    else:
                        self.log_test("核心API", name, "FAIL", "数据无效")
                else:
                    self.log_test("核心API", name, "FAIL", f"HTTP {response.status_code}")
            except Exception as e:
                self.log_test("核心API", name, "ERROR", str(e))

    def validate_price(self, data) -> bool:
        """验证价格数据"""
        return isinstance(data, dict) and 'price' in data and 50000 <= data['price'] <= 200000

    def validate_network(self, data) -> bool:
        """验证网络数据"""
        return (isinstance(data, dict) and 
                'hashrate' in data and 
                'difficulty' in data and
                data['hashrate'] > 500)

    def validate_miners(self, data) -> bool:
        """验证矿机数据"""
        if isinstance(data, dict) and 'miners' in data:
            miners = data['miners']
            return isinstance(miners, list) and len(miners) >= 5
        return isinstance(data, list) and len(data) >= 5

    def validate_analytics(self, data) -> bool:
        """验证分析数据"""
        if not isinstance(data, dict):
            return False
        market_data = data.get('data', {})
        return ('btc_price' in market_data and 
                isinstance(market_data['btc_price'], (int, float)) and
                market_data['btc_price'] > 50000)

    def test_mining_calculations(self):
        """测试挖矿计算精度"""
        test_cases = [
            {'miner_model': 'Antminer S19 Pro', 'site_power_mw': 5.0, 'electricity_cost': 0.05},
            {'miner_model': 'Antminer S21 XP', 'site_power_mw': 3.0, 'electricity_cost': 0.06}
        ]
        
        for i, case in enumerate(test_cases):
            try:
                response = self.session.post(f"{self.base_url}/calculate", 
                                           data=case, timeout=10)
                if response.status_code == 200:
                    result = response.json()
                    if self.validate_calculation(result):
                        self.log_test("挖矿计算", f"计算案例{i+1}", "PASS", 
                                    f"日利润${result.get('daily_profit_usd', 0):.2f}")
                    else:
                        self.log_test("挖矿计算", f"计算案例{i+1}", "FAIL", "结果无效")
                else:
                    self.log_test("挖矿计算", f"计算案例{i+1}", "FAIL", 
                                f"HTTP {response.status_code}")
            except Exception as e:
                self.log_test("挖矿计算", f"计算案例{i+1}", "ERROR", str(e))

    def validate_calculation(self, result) -> bool:
        """验证计算结果"""
        if not isinstance(result, dict):
            return False
            
        # 验证必需字段
        has_profit = 'daily_profit_usd' in result and isinstance(result['daily_profit_usd'], (int, float))
        has_btc_output = 'site_daily_btc_output' in result and isinstance(result['site_daily_btc_output'], (int, float))
        has_success = result.get('success') is True
        
        # 验证network_data子对象
        network_data = result.get('network_data', {})
        has_difficulty = isinstance(network_data.get('network_difficulty'), (int, float))
        
        return has_profit and has_btc_output and has_success and has_difficulty

    def test_key_pages(self):
        """测试关键页面"""
        pages = [
            ("/", "主页"),
            ("/analytics", "分析仪表盘"),
            ("/network/history", "网络历史")
        ]
        
        for path, name in pages:
            try:
                response = self.session.get(f"{self.base_url}{path}", timeout=5)
                if response.status_code == 200:
                    content = response.text
                    if self.validate_page(path, content):
                        self.log_test("页面访问", name, "PASS", "页面完整")
                    else:
                        self.log_test("页面访问", name, "FAIL", "页面不完整")
                else:
                    self.log_test("页面访问", name, "FAIL", f"HTTP {response.status_code}")
            except Exception as e:
                self.log_test("页面访问", name, "ERROR", str(e))

    def validate_page(self, path: str, content: str) -> bool:
        """验证页面内容"""
        if path == "/":
            return ("比特币挖矿" in content and "计算" in content and len(content) > 5000)
        elif path == "/analytics":
            # 检查关键分析仪表盘元素
            required_elements = ["分析", "市场数据", "BTC"]
            return (any(element in content for element in required_elements) and 
                   len(content) > 2000 and "<html" in content)
        else:
            return len(content) > 1000 and "<html" in content

    def test_data_consistency(self):
        """测试数据一致性"""
        # 多次获取价格数据检查一致性
        prices = []
        for _ in range(3):
            try:
                response = self.session.get(f"{self.base_url}/api/btc-price", timeout=3)
                if response.status_code == 200:
                    data = response.json()
                    prices.append(data.get('price', 0))
                time.sleep(0.5)
            except:
                continue
                
        if len(prices) >= 2:
            price_variance = max(prices) - min(prices)
            if price_variance <= 100:  # 价格差异小于$100
                self.log_test("数据一致性", "价格稳定性", "PASS", 
                            f"价格差异${price_variance:.2f}")
            else:
                self.log_test("数据一致性", "价格稳定性", "FAIL", 
                            f"价格差异${price_variance:.2f}")
        else:
            self.log_test("数据一致性", "价格稳定性", "FAIL", "无法获取足够数据")

    def run_fast_test(self):
        """运行快速测试"""
        print("\n" + "="*60)
        print("🚀 开始快速99%准确率验证测试")
        print("="*60)
        
        start_time = time.time()
        
        # 1. 认证
        print("\n📧 步骤1: 认证验证")
        if not self.authenticate():
            print("❌ 认证失败，测试终止")
            return
            
        # 2. 核心API测试
        print("\n🔧 步骤2: 核心API测试")
        self.test_core_apis()
        
        # 3. 挖矿计算测试
        print("\n⛏️ 步骤3: 挖矿计算测试")
        self.test_mining_calculations()
        
        # 4. 关键页面测试
        print("\n🖥️ 步骤4: 关键页面测试")
        self.test_key_pages()
        
        # 5. 数据一致性测试
        print("\n🔄 步骤5: 数据一致性测试")
        self.test_data_consistency()
        
        total_time = time.time() - start_time
        
        # 生成报告
        self.generate_report(total_time)

    def generate_report(self, total_time: float):
        """生成快速测试报告"""
        accuracy_rate = (self.passed / self.total * 100) if self.total > 0 else 0
        
        print("\n" + "="*60)
        print("📋 快速99%准确率测试报告")
        print("="*60)
        
        print(f"\n📊 测试统计:")
        print(f"   总测试数: {self.total}")
        print(f"   通过数量: {self.passed}")
        print(f"   失败数量: {self.total - self.passed}")
        print(f"   准确率: {accuracy_rate:.2f}%")
        print(f"   测试耗时: {total_time:.2f}秒")
        
        # 准确率评级
        if accuracy_rate >= 99.0:
            grade = "🏆 卓越 (99%+)"
            status = "✅ 达到目标"
        elif accuracy_rate >= 95.0:
            grade = "🥇 优秀 (95-99%)"
            status = "⚠️ 接近目标"
        elif accuracy_rate >= 90.0:
            grade = "🥈 良好 (90-95%)"
            status = "🔄 需改进"
        else:
            grade = "🥉 基础 (<90%)"
            status = "❌ 需大幅改进"
            
        print(f"\n🎯 准确率评级: {grade}")
        print(f"   目标达成状态: {status}")
        
        # 分类统计
        categories = {}
        for test in self.tests:
            cat = test['category']
            if cat not in categories:
                categories[cat] = {'total': 0, 'passed': 0}
            categories[cat]['total'] += 1
            if test['status'] == 'PASS':
                categories[cat]['passed'] += 1
                
        print(f"\n📈 分类统计:")
        for cat, stats in categories.items():
            cat_rate = (stats['passed'] / stats['total'] * 100) if stats['total'] > 0 else 0
            print(f"   {cat}: {cat_rate:.1f}% ({stats['passed']}/{stats['total']})")
        
        # 保存报告
        report = {
            'timestamp': datetime.now().isoformat(),
            'test_email': self.test_email,
            'accuracy_rate': accuracy_rate,
            'total_tests': self.total,
            'passed_tests': self.passed,
            'failed_tests': self.total - self.passed,
            'test_time': total_time,
            'categories': categories,
            'detailed_tests': self.tests
        }
        
        filename = f"fast_99_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
            
        print(f"\n💾 报告已保存: {filename}")
        
        # 最终结论
        if accuracy_rate >= 99.0:
            print(f"\n🎉 恭喜！系统达到99%准确率目标")
            print("   系统准备就绪，可用于生产环境")
        else:
            print(f"\n📝 当前准确率{accuracy_rate:.2f}%，需要进一步优化")
            print(f"   距离99%目标还需提升{99.0 - accuracy_rate:.2f}个百分点")

def main():
    """主函数"""
    print("🎯 启动快速99%准确率验证测试")
    
    tester = Fast99AccuracyTest()
    tester.run_fast_test()

if __name__ == "__main__":
    main()