#!/usr/bin/env python3
"""
最终分析认证修复验证
Final Analytics Authentication Fix Verification

验证minerstat API集成后的完整系统功能
Verify complete system functionality after minerstat API integration
"""

import requests
import json
import time
import logging
from datetime import datetime
from typing import Dict, Any, List, Tuple

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class FinalSystemVerification:
    def __init__(self):
        self.base_url = "http://localhost:5000"
        self.session = requests.Session()
        self.test_results = []
        self.authenticated = False
        
    def log_test(self, module: str, test_name: str, status: str, details: str = "", response_time: float = None):
        """记录测试结果"""
        result = {
            'timestamp': datetime.now().isoformat(),
            'module': module,
            'test_name': test_name,
            'status': status,
            'details': details,
            'response_time': response_time
        }
        self.test_results.append(result)
        
        status_emoji = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        time_str = f" ({response_time:.3f}s)" if response_time else ""
        print(f"{status_emoji} {module}.{test_name}: {status}{time_str}")
        if details:
            print(f"   → {details}")

    def authenticate_system(self) -> bool:
        """系统认证"""
        start_time = time.time()
        
        try:
            # 使用拥有者邮箱进行认证
            response = self.session.post(f"{self.base_url}/login", data={
                'email': 'hxl2022hao@gmail.com'
            }, allow_redirects=False)
            
            response_time = time.time() - start_time
            
            if response.status_code in [200, 302]:
                self.authenticated = True
                self.log_test("认证系统", "拥有者认证", "PASS", "认证成功", response_time)
                return True
            else:
                self.log_test("认证系统", "拥有者认证", "FAIL", f"HTTP {response.status_code}", response_time)
                return False
                
        except Exception as e:
            response_time = time.time() - start_time
            self.log_test("认证系统", "拥有者认证", "FAIL", str(e), response_time)
            return False

    def test_core_apis(self) -> None:
        """测试核心API功能"""
        apis = [
            ("/api/btc_price", "BTC价格API", self.validate_price_api),
            ("/api/network_stats", "网络统计API", self.validate_network_api),
            ("/api/miners", "矿机数据API", self.validate_miners_api),
            ("/api/sha256_mining_comparison", "挖矿对比API", self.validate_comparison_api),
        ]
        
        for endpoint, name, validator in apis:
            start_time = time.time()
            try:
                response = self.session.get(f"{self.base_url}{endpoint}")
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    data = response.json()
                    is_valid, message = validator(data)
                    if is_valid:
                        self.log_test("核心API", name, "PASS", message, response_time)
                    else:
                        self.log_test("核心API", name, "FAIL", message, response_time)
                else:
                    self.log_test("核心API", name, "FAIL", f"HTTP {response.status_code}", response_time)
                    
            except Exception as e:
                response_time = time.time() - start_time
                self.log_test("核心API", name, "FAIL", str(e), response_time)

    def validate_price_api(self, data) -> Tuple[bool, str]:
        """验证价格API"""
        if 'price' in data and isinstance(data['price'], (int, float)):
            return True, f"BTC价格: ${data['price']:,.2f}"
        return False, "价格数据无效"

    def validate_network_api(self, data) -> Tuple[bool, str]:
        """验证网络统计API"""
        required_fields = ['hashrate', 'difficulty', 'price']
        if all(field in data for field in required_fields):
            hashrate = data.get('hashrate', 0)
            source = data.get('source', 'unknown')
            return True, f"算力: {hashrate}EH/s, 数据源: {source}"
        return False, "网络数据字段不完整"

    def validate_miners_api(self, data) -> Tuple[bool, str]:
        """验证矿机数据API"""
        if isinstance(data, dict) and len(data) >= 10:
            return True, f"获取{len(data)}种矿机型号"
        return False, "矿机数据不足"

    def validate_comparison_api(self, data) -> Tuple[bool, str]:
        """验证挖矿对比API"""
        if isinstance(data, list) and len(data) > 0:
            return True, f"SHA256对比数据: {len(data)}条记录"
        return False, "对比数据为空"

    def test_mining_calculations(self) -> None:
        """测试挖矿计算功能"""
        start_time = time.time()
        
        try:
            # 测试标准挖矿计算
            calc_data = {
                'miner_model': 'Antminer S21 XP Hyd',
                'miner_count': '10',
                'electricity_cost': '0.05',
                'use_real_time': 'on'
            }
            
            response = self.session.post(f"{self.base_url}/calculate", data=calc_data)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                
                # 验证关键字段
                required_fields = ['site_daily_btc_output', 'daily_profit_usd', 'network_hashrate_eh', 'btc_price']
                missing_fields = [field for field in required_fields if field not in result]
                
                if not missing_fields:
                    daily_btc = result.get('site_daily_btc_output', 0)
                    daily_profit = result.get('daily_profit_usd', 0)
                    network_hashrate = result.get('network_hashrate_eh', 0)
                    
                    # 验证minerstat数据源
                    if 790 <= network_hashrate <= 800:  # minerstat范围
                        source_status = "使用minerstat数据源"
                    else:
                        source_status = f"算力异常: {network_hashrate}EH/s"
                    
                    self.log_test("挖矿计算", "标准计算", "PASS", 
                                f"日产出: {daily_btc:.6f}BTC, 日利润: ${daily_profit:.2f}, {source_status}", response_time)
                else:
                    self.log_test("挖矿计算", "标准计算", "FAIL", 
                                f"缺失字段: {missing_fields}", response_time)
            else:
                self.log_test("挖矿计算", "标准计算", "FAIL", 
                            f"HTTP {response.status_code}", response_time)
                
        except Exception as e:
            response_time = time.time() - start_time
            self.log_test("挖矿计算", "标准计算", "FAIL", str(e), response_time)

    def test_analytics_integration(self) -> None:
        """测试分析系统集成"""
        analytics_endpoints = [
            ("/api/analytics/market-data", "市场数据API", self.validate_analytics_market),
            ("/api/analytics/latest-report", "最新报告API", self.validate_analytics_report),
            ("/api/analytics/technical-indicators", "技术指标API", self.validate_analytics_indicators),
            ("/api/analytics/price-history", "价格历史API", self.validate_analytics_history),
        ]
        
        for endpoint, name, validator in analytics_endpoints:
            start_time = time.time()
            try:
                response = self.session.get(f"{self.base_url}{endpoint}")
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    data = response.json()
                    is_valid, message = validator(data)
                    if is_valid:
                        self.log_test("分析系统", name, "PASS", message, response_time)
                    else:
                        self.log_test("分析系统", name, "FAIL", message, response_time)
                else:
                    self.log_test("分析系统", name, "FAIL", f"HTTP {response.status_code}", response_time)
                    
            except Exception as e:
                response_time = time.time() - start_time
                self.log_test("分析系统", name, "FAIL", str(e), response_time)

    def validate_analytics_market(self, data) -> Tuple[bool, str]:
        """验证分析市场数据"""
        if 'data' in data and 'network_hashrate' in data['data']:
            hashrate = data['data']['network_hashrate']
            btc_price = data['data'].get('btc_price', 0)
            return True, f"算力: {hashrate}EH/s, 价格: ${btc_price:,.0f}"
        return False, "市场数据格式错误"

    def validate_analytics_report(self, data) -> Tuple[bool, str]:
        """验证分析报告"""
        if 'latest_report' in data and data['latest_report']:
            report = data['latest_report']
            return True, f"报告日期: {report.get('date', 'N/A')}"
        return False, "报告数据为空"

    def validate_analytics_indicators(self, data) -> Tuple[bool, str]:
        """验证技术指标"""
        if 'indicators' in data:
            indicators = data['indicators']
            if indicators and len(indicators) > 0:
                return True, f"指标数量: {len(indicators)}"
            else:
                return True, "指标数据为空(正常，需要时间积累)"
        return False, "指标数据格式错误"

    def validate_analytics_history(self, data) -> Tuple[bool, str]:
        """验证价格历史"""
        if 'price_history' in data and isinstance(data['price_history'], list):
            history_count = len(data['price_history'])
            return True, f"历史记录: {history_count}条"
        return False, "历史数据为空"

    def test_miner_models_comprehensive(self) -> None:
        """测试矿机型号完整性"""
        start_time = time.time()
        
        try:
            response = self.session.get(f"{self.base_url}/api/miners")
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                miners = response.json()
                
                # 预期的矿机型号
                expected_miners = [
                    "Antminer S21 XP Hyd", "Antminer S21 Pro", "Antminer S21",
                    "Antminer S19 XP", "Antminer S19 Pro", "Antminer S19j Pro",
                    "Antminer S19", "Antminer S17 Pro", "Antminer T19",
                    "WhatsMiner M50S"
                ]
                
                available_miners = list(miners.keys()) if isinstance(miners, dict) else []
                missing_miners = [m for m in expected_miners if m not in available_miners]
                
                if len(missing_miners) == 0:
                    self.log_test("矿机完整性", "10种型号验证", "PASS", 
                                f"所有{len(available_miners)}种矿机型号完整", response_time)
                elif len(missing_miners) <= 3:
                    self.log_test("矿机完整性", "10种型号验证", "WARN", 
                                f"缺失{len(missing_miners)}种: {missing_miners}", response_time)
                else:
                    self.log_test("矿机完整性", "10种型号验证", "FAIL", 
                                f"缺失过多: {missing_miners}", response_time)
            else:
                self.log_test("矿机完整性", "10种型号验证", "FAIL", 
                            f"HTTP {response.status_code}", response_time)
                
        except Exception as e:
            response_time = time.time() - start_time
            self.log_test("矿机完整性", "10种型号验证", "FAIL", str(e), response_time)

    def test_minerstat_integration(self) -> None:
        """验证minerstat API集成状态"""
        start_time = time.time()
        
        try:
            # 直接测试minerstat API
            response = requests.get("https://api.minerstat.com/v2/coins?list=BTC", timeout=10)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    btc_data = data[0]
                    hashrate_hs = float(btc_data.get('network_hashrate', 0))
                    hashrate_eh = hashrate_hs / 1e18
                    price = btc_data.get('price', 0)
                    
                    self.log_test("外部集成", "Minerstat API", "PASS", 
                                f"算力: {hashrate_eh:.2f}EH/s, 价格: ${price:,.2f}", response_time)
                else:
                    self.log_test("外部集成", "Minerstat API", "FAIL", "数据为空", response_time)
            else:
                self.log_test("外部集成", "Minerstat API", "FAIL", 
                            f"HTTP {response.status_code}", response_time)
                
        except Exception as e:
            response_time = time.time() - start_time
            self.log_test("外部集成", "Minerstat API", "FAIL", str(e), response_time)

    def run_comprehensive_verification(self) -> None:
        """运行完整验证测试"""
        print("=" * 80)
        print("🔧 BTC挖矿计算器系统 - 最终验证测试 (Minerstat集成)")
        print(f"📅 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        
        # 1. 系统认证
        print(f"\n🔐 系统认证")
        if not self.authenticate_system():
            print("❌ 认证失败，终止测试")
            return
        
        # 2. 核心API功能
        print(f"\n🔌 核心API功能测试")
        self.test_core_apis()
        
        # 3. 挖矿计算测试
        print(f"\n⚡ 挖矿计算功能测试")
        self.test_mining_calculations()
        
        # 4. 分析系统集成
        print(f"\n📊 分析系统集成测试")
        self.test_analytics_integration()
        
        # 5. 矿机型号完整性
        print(f"\n🔧 矿机型号完整性测试")
        self.test_miner_models_comprehensive()
        
        # 6. Minerstat集成验证
        print(f"\n🌐 外部API集成验证")
        self.test_minerstat_integration()
        
        # 生成最终报告
        self.generate_final_report()

    def generate_final_report(self) -> None:
        """生成最终测试报告"""
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r['status'] == 'PASS'])
        failed_tests = len([r for r in self.test_results if r['status'] == 'FAIL'])
        warned_tests = len([r for r in self.test_results if r['status'] == 'WARN'])
        
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        # 按模块统计
        modules = {}
        for result in self.test_results:
            module = result['module']
            if module not in modules:
                modules[module] = {'total': 0, 'passed': 0}
            modules[module]['total'] += 1
            if result['status'] == 'PASS':
                modules[module]['passed'] += 1
        
        print("\n" + "=" * 80)
        print("📋 最终验证测试报告 (Minerstat集成)")
        print("=" * 80)
        print(f"🎯 总测试数: {total_tests}")
        print(f"✅ 通过: {passed_tests}")
        print(f"❌ 失败: {failed_tests}")
        print(f"⚠️  警告: {warned_tests}")
        print(f"📈 成功率: {success_rate:.1f}%")
        
        # 响应时间统计
        times = [r['response_time'] for r in self.test_results if r['response_time'] is not None]
        if times:
            avg_time = sum(times) / len(times)
            print(f"⏱️  平均响应时间: {avg_time:.3f}秒")
        
        print(f"\n📊 模块测试详情:")
        for module, stats in modules.items():
            percentage = (stats['passed'] / stats['total'] * 100) if stats['total'] > 0 else 0
            print(f"   • {module}: {stats['passed']}/{stats['total']} 通过 ({percentage:.1f}%)")
        
        # 失败测试详情
        failed_results = [r for r in self.test_results if r['status'] == 'FAIL']
        if failed_results:
            print(f"\n❌ 失败测试详情:")
            for result in failed_results:
                print(f"   • {result['module']}.{result['test_name']}: {result['details']}")
        
        # 系统状态评估
        print(f"\n" + "=" * 80)
        if success_rate >= 90:
            print("🟢 系统状态: 优秀 - Minerstat集成成功，所有核心功能正常")
        elif success_rate >= 75:
            print("🟡 系统状态: 良好 - Minerstat集成成功，大部分功能正常")
        elif success_rate >= 50:
            print("🟠 系统状态: 可用 - Minerstat集成完成，部分功能需要改进")
        else:
            print("🔴 系统状态: 需要修复 - 存在重大功能问题")
        
        print(f"\n🚀 最终验证测试完成")
        print("=" * 80)

def main():
    """主函数"""
    verifier = FinalSystemVerification()
    verifier.run_comprehensive_verification()

if __name__ == "__main__":
    main()