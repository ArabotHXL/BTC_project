#!/usr/bin/env python3
"""
Total and Full Regression Test - Focus on Numbers
全面回归测试 - 专注数值计算准确性

测试所有核心数值计算功能的准确性和一致性
Tests accuracy and consistency of all core numerical calculation functions
"""

import requests
import json
import time
from datetime import datetime
import sys
import os

class TotalFullRegressionTest:
    def __init__(self):
        self.base_url = "http://localhost:5000"
        self.session = requests.Session()
        self.test_results = []
        self.numerical_tolerance = 0.01  # 1% 数值容差
        
    def log_test(self, category: str, test_name: str, status: str, details: str = "", actual_value=None, expected_value=None):
        """记录测试结果"""
        result = {
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'category': category,
            'test_name': test_name,
            'status': status,
            'details': details,
            'actual_value': actual_value,
            'expected_value': expected_value
        }
        self.test_results.append(result)
        print(f"[{result['timestamp']}] {category} - {test_name}: {status}")
        if details:
            print(f"    Details: {details}")
        if actual_value is not None and expected_value is not None:
            print(f"    Expected: {expected_value}, Actual: {actual_value}")

    def authenticate_as_owner(self):
        """使用拥有者邮箱进行认证"""
        try:
            response = self.session.post(f"{self.base_url}/login", 
                                       data={'email': 'hxl2022hao@gmail.com'})
            if response.status_code == 200 or 'dashboard' in response.url:
                self.log_test("Authentication", "Owner Login", "PASS", "Successfully authenticated as owner")
                return True
            else:
                self.log_test("Authentication", "Owner Login", "FAIL", f"Status: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Authentication", "Owner Login", "ERROR", str(e))
            return False

    def test_core_api_numerical_accuracy(self):
        """测试核心API的数值准确性"""
        print("\n=== 测试核心API数值准确性 ===")
        
        # 1. BTC价格API数值验证
        try:
            response = self.session.get(f"{self.base_url}/api/btc-price")
            if response.status_code == 200:
                data = response.json()
                btc_price = float(data.get('btc_price', 0))
                
                if 50000 <= btc_price <= 200000:  # 合理价格范围
                    self.log_test("Core API", "BTC Price Range", "PASS", 
                                f"Price ${btc_price:,.2f} within reasonable range", 
                                btc_price, "50k-200k range")
                else:
                    self.log_test("Core API", "BTC Price Range", "FAIL", 
                                f"Price ${btc_price:,.2f} outside reasonable range", 
                                btc_price, "50k-200k range")
            else:
                self.log_test("Core API", "BTC Price API", "FAIL", f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("Core API", "BTC Price API", "ERROR", str(e))

        # 2. 网络统计API数值验证
        try:
            response = self.session.get(f"{self.base_url}/api/network-stats")
            if response.status_code == 200:
                data = response.json()
                hashrate = float(data.get('network_hashrate', 0))
                difficulty = float(data.get('difficulty', 0))
                
                # 验证算力范围 (300-2000 EH/s)
                if 300 <= hashrate <= 2000:
                    self.log_test("Core API", "Network Hashrate Range", "PASS", 
                                f"Hashrate {hashrate:.2f} EH/s within range", 
                                hashrate, "300-2000 EH/s")
                else:
                    self.log_test("Core API", "Network Hashrate Range", "FAIL", 
                                f"Hashrate {hashrate:.2f} EH/s outside range", 
                                hashrate, "300-2000 EH/s")
                
                # 验证难度范围 (30T-200T)
                difficulty_t = difficulty / 1e12  # 转换为T
                if 30 <= difficulty_t <= 200:
                    self.log_test("Core API", "Network Difficulty Range", "PASS", 
                                f"Difficulty {difficulty_t:.2f}T within range", 
                                difficulty_t, "30-200T")
                else:
                    self.log_test("Core API", "Network Difficulty Range", "FAIL", 
                                f"Difficulty {difficulty_t:.2f}T outside range", 
                                difficulty_t, "30-200T")
            else:
                self.log_test("Core API", "Network Stats API", "FAIL", f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("Core API", "Network Stats API", "ERROR", str(e))

    def test_mining_calculation_numerical_precision(self):
        """测试挖矿计算的数值精度"""
        print("\n=== 测试挖矿计算数值精度 ===")
        
        # 测试参数
        test_cases = [
            {
                'name': 'Antminer S19 Pro Standard',
                'miner_model': 'antminer_s19_pro',
                'electricity_cost': 0.05,
                'expected_daily_profit_range': (1, 50)  # $1-50 daily profit range
            },
            {
                'name': 'Antminer S19 High Cost',
                'miner_model': 'antminer_s19',
                'electricity_cost': 0.12,
                'expected_daily_profit_range': (-10, 30)  # May be negative with high cost
            },
            {
                'name': 'Antminer S21 XP Efficient',
                'miner_model': 'antminer_s21_xp',
                'electricity_cost': 0.03,
                'expected_daily_profit_range': (5, 80)  # Higher profit with low cost
            }
        ]
        
        for case in test_cases:
            try:
                calc_data = {
                    'miner_model': case['miner_model'],
                    'site_power_mw': 10,
                    'miner_count': 100,
                    'electricity_cost': case['electricity_cost'],
                    'use_real_time_data': True
                }
                
                response = self.session.post(f"{self.base_url}/calculate", json=calc_data)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # 验证关键数值
                    daily_profit = float(data.get('daily_profit_usd', 0))
                    btc_mined_daily = float(data.get('site_daily_btc_output', 0))
                    electricity_cost_daily = float(data.get('daily_electricity_cost', 0))
                    
                    # 验证每日利润范围
                    min_profit, max_profit = case['expected_daily_profit_range']
                    if min_profit <= daily_profit <= max_profit:
                        self.log_test("Mining Calc", f"{case['name']} - Daily Profit", "PASS", 
                                    f"Profit ${daily_profit:.2f} within expected range", 
                                    daily_profit, f"${min_profit}-${max_profit}")
                    else:
                        self.log_test("Mining Calc", f"{case['name']} - Daily Profit", "FAIL", 
                                    f"Profit ${daily_profit:.2f} outside expected range", 
                                    daily_profit, f"${min_profit}-${max_profit}")
                    
                    # 验证BTC挖矿产出 (应该大于0且小于1)
                    if 0 < btc_mined_daily < 1:
                        self.log_test("Mining Calc", f"{case['name']} - BTC Output", "PASS", 
                                    f"Daily BTC {btc_mined_daily:.6f} within range", 
                                    btc_mined_daily, "0-1 BTC")
                    else:
                        self.log_test("Mining Calc", f"{case['name']} - BTC Output", "FAIL", 
                                    f"Daily BTC {btc_mined_daily:.6f} outside range", 
                                    btc_mined_daily, "0-1 BTC")
                    
                    # 验证电费成本 (应该大于0)
                    if electricity_cost_daily > 0:
                        self.log_test("Mining Calc", f"{case['name']} - Electricity Cost", "PASS", 
                                    f"Daily cost ${electricity_cost_daily:.2f} > 0", 
                                    electricity_cost_daily, "> 0")
                    else:
                        self.log_test("Mining Calc", f"{case['name']} - Electricity Cost", "FAIL", 
                                    f"Daily cost ${electricity_cost_daily:.2f} <= 0", 
                                    electricity_cost_daily, "> 0")
                        
                else:
                    self.log_test("Mining Calc", f"{case['name']}", "FAIL", f"HTTP {response.status_code}")
                    
            except Exception as e:
                self.log_test("Mining Calc", f"{case['name']}", "ERROR", str(e))

    def test_breakeven_calculation_accuracy(self):
        """测试盈亏平衡计算准确性"""
        print("\n=== 测试盈亏平衡计算准确性 ===")
        
        # 获取矿机列表
        try:
            response = self.session.get(f"{self.base_url}/api/miners")
            if response.status_code == 200:
                miners_data = response.json()
                miners = miners_data.get('miners', [])
                
                breakeven_results = []
                
                for miner in miners[:5]:  # 测试前5个矿机
                    miner_key = miner.get('key')
                    miner_name = miner.get('name')
                    
                    # 测试盈亏平衡计算
                    electricity_costs = [0.03, 0.05, 0.08, 0.12]  # 不同电价
                    
                    for elec_cost in electricity_costs:
                        try:
                            calc_data = {
                                'miner_model': miner_key,
                                'site_power_mw': 5,
                                'miner_count': 50,
                                'electricity_cost': elec_cost,
                                'use_real_time_data': True
                            }
                            
                            response = self.session.post(f"{self.base_url}/calculate", json=calc_data)
                            if response.status_code == 200:
                                data = response.json()
                                daily_profit = float(data.get('daily_profit_usd', 0))
                                
                                # 记录盈亏平衡点
                                if abs(daily_profit) < 50:  # 接近盈亏平衡
                                    breakeven_results.append({
                                        'miner': miner_name,
                                        'electricity_cost': elec_cost,
                                        'daily_profit': daily_profit,
                                        'is_profitable': daily_profit > 0
                                    })
                                    
                                    self.log_test("Breakeven", f"{miner_name} @ ${elec_cost}/kWh", 
                                                "PASS" if abs(daily_profit) < 10 else "INFO", 
                                                f"Daily profit: ${daily_profit:.2f}", 
                                                daily_profit, "Near breakeven")
                        except Exception as e:
                            self.log_test("Breakeven", f"{miner_name}", "ERROR", str(e))
                
                # 验证盈亏平衡趋势
                if breakeven_results:
                    # 检查高电价是否导致更低利润
                    sorted_by_cost = sorted(breakeven_results, key=lambda x: x['electricity_cost'])
                    trend_correct = True
                    for i in range(1, len(sorted_by_cost)):
                        if sorted_by_cost[i]['daily_profit'] > sorted_by_cost[i-1]['daily_profit']:
                            trend_correct = False
                            break
                    
                    if trend_correct:
                        self.log_test("Breakeven", "Electricity Cost Trend", "PASS", 
                                    "Higher electricity cost results in lower profit")
                    else:
                        self.log_test("Breakeven", "Electricity Cost Trend", "FAIL", 
                                    "Trend inconsistency detected")
                        
            else:
                self.log_test("Breakeven", "Miners API", "FAIL", f"HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test("Breakeven", "Miners API", "ERROR", str(e))

    def test_analytics_numerical_consistency(self):
        """测试分析系统数值一致性"""
        print("\n=== 测试分析系统数值一致性 ===")
        
        # 1. 市场数据一致性
        try:
            response = self.session.get(f"{self.base_url}/api/analytics/market-data")
            if response.status_code == 200:
                data = response.json().get('data', {})
                
                btc_price = float(data.get('btc_price', 0))
                network_hashrate = float(data.get('network_hashrate', 0))
                fear_greed = data.get('fear_greed_index')
                
                # 验证数值范围
                if 50000 <= btc_price <= 200000:
                    self.log_test("Analytics", "Market Data - BTC Price", "PASS", 
                                f"${btc_price:,.2f} within range", btc_price, "50k-200k")
                else:
                    self.log_test("Analytics", "Market Data - BTC Price", "FAIL", 
                                f"${btc_price:,.2f} outside range", btc_price, "50k-200k")
                
                if 300 <= network_hashrate <= 2000:
                    self.log_test("Analytics", "Market Data - Hashrate", "PASS", 
                                f"{network_hashrate:.2f} EH/s within range", 
                                network_hashrate, "300-2000 EH/s")
                else:
                    self.log_test("Analytics", "Market Data - Hashrate", "FAIL", 
                                f"{network_hashrate:.2f} EH/s outside range", 
                                network_hashrate, "300-2000 EH/s")
                
                if fear_greed is not None and 0 <= fear_greed <= 100:
                    self.log_test("Analytics", "Market Data - Fear & Greed", "PASS", 
                                f"Index {fear_greed} within 0-100", fear_greed, "0-100")
                else:
                    self.log_test("Analytics", "Market Data - Fear & Greed", "FAIL", 
                                f"Index {fear_greed} outside 0-100", fear_greed, "0-100")
            else:
                self.log_test("Analytics", "Market Data API", "FAIL", f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("Analytics", "Market Data API", "ERROR", str(e))

        # 2. 技术指标数值验证
        try:
            response = self.session.get(f"{self.base_url}/api/analytics/technical-indicators")
            if response.status_code == 200:
                data = response.json().get('data', {})
                
                rsi = data.get('rsi_14')
                sma_20 = data.get('sma_20')
                sma_50 = data.get('sma_50')
                volatility = data.get('volatility_30d')
                
                # RSI应该在0-100之间
                if rsi is not None and 0 <= rsi <= 100:
                    self.log_test("Analytics", "Technical - RSI Range", "PASS", 
                                f"RSI {rsi:.2f} within 0-100", rsi, "0-100")
                else:
                    self.log_test("Analytics", "Technical - RSI Range", "FAIL", 
                                f"RSI {rsi} outside 0-100", rsi, "0-100")
                
                # SMA应该接近当前价格
                if sma_20 and sma_50 and 50000 <= sma_20 <= 200000 and 50000 <= sma_50 <= 200000:
                    self.log_test("Analytics", "Technical - SMA Range", "PASS", 
                                f"SMA20: ${sma_20:.2f}, SMA50: ${sma_50:.2f}", 
                                [sma_20, sma_50], "50k-200k range")
                else:
                    self.log_test("Analytics", "Technical - SMA Range", "FAIL", 
                                f"SMA20: ${sma_20}, SMA50: ${sma_50}", 
                                [sma_20, sma_50], "50k-200k range")
                
                # 波动率应该是正数且合理
                if volatility is not None and 0 <= volatility <= 5:
                    self.log_test("Analytics", "Technical - Volatility", "PASS", 
                                f"Volatility {volatility:.3f} within range", 
                                volatility, "0-5")
                else:
                    self.log_test("Analytics", "Technical - Volatility", "FAIL", 
                                f"Volatility {volatility} outside range", 
                                volatility, "0-5")
            else:
                self.log_test("Analytics", "Technical Indicators API", "FAIL", f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("Analytics", "Technical Indicators API", "ERROR", str(e))

    def test_cross_component_numerical_consistency(self):
        """测试跨组件数值一致性"""
        print("\n=== 测试跨组件数值一致性 ===")
        
        # 获取多个API的BTC价格，验证一致性
        prices = {}
        
        try:
            # 1. 核心API价格
            response = self.session.get(f"{self.base_url}/api/btc-price")
            if response.status_code == 200:
                prices['core_api'] = float(response.json().get('btc_price', 0))
        except:
            pass
            
        try:
            # 2. 分析API价格
            response = self.session.get(f"{self.base_url}/api/analytics/market-data")
            if response.status_code == 200:
                prices['analytics_api'] = float(response.json().get('data', {}).get('btc_price', 0))
        except:
            pass
            
        try:
            # 3. 网络统计API中的价格
            response = self.session.get(f"{self.base_url}/api/network-stats")
            if response.status_code == 200:
                data = response.json()
                if 'btc_price' in data:
                    prices['network_stats'] = float(data.get('btc_price', 0))
        except:
            pass
        
        # 验证价格一致性 (允许1%差异)
        if len(prices) >= 2:
            price_values = list(prices.values())
            max_price = max(price_values)
            min_price = min(price_values)
            
            if max_price > 0:
                price_diff_pct = ((max_price - min_price) / max_price) * 100
                
                if price_diff_pct <= 1.0:  # 1%容差
                    self.log_test("Consistency", "Cross-API BTC Price", "PASS", 
                                f"Price variance {price_diff_pct:.2f}% within 1%", 
                                price_diff_pct, "≤1%")
                else:
                    self.log_test("Consistency", "Cross-API BTC Price", "FAIL", 
                                f"Price variance {price_diff_pct:.2f}% exceeds 1%", 
                                price_diff_pct, "≤1%")
                    
                    # 详细报告价格差异
                    for api, price in prices.items():
                        print(f"      {api}: ${price:,.2f}")
        else:
            self.log_test("Consistency", "Cross-API BTC Price", "SKIP", "Insufficient data sources")

    def run_comprehensive_numerical_test(self):
        """运行全面的数值回归测试"""
        print("="*80)
        print("Total and Full Regression Test - Focus on Numbers")
        print("全面回归测试 - 专注数值计算准确性")
        print("="*80)
        
        start_time = time.time()
        
        # 1. 认证
        if not self.authenticate_as_owner():
            print("❌ 认证失败，无法继续测试")
            return
        
        # 2. 核心API数值准确性
        self.test_core_api_numerical_accuracy()
        
        # 3. 挖矿计算数值精度
        self.test_mining_calculation_numerical_precision()
        
        # 4. 盈亏平衡计算准确性
        self.test_breakeven_calculation_accuracy()
        
        # 5. 分析系统数值一致性
        self.test_analytics_numerical_consistency()
        
        # 6. 跨组件数值一致性
        self.test_cross_component_numerical_consistency()
        
        # 生成测试报告
        self.generate_numerical_report(time.time() - start_time)

    def generate_numerical_report(self, duration):
        """生成数值测试报告"""
        print("\n" + "="*80)
        print("NUMERICAL REGRESSION TEST REPORT")
        print("数值回归测试报告")
        print("="*80)
        
        # 统计结果
        total_tests = len(self.test_results)
        passed_tests = len([t for t in self.test_results if t['status'] == 'PASS'])
        failed_tests = len([t for t in self.test_results if t['status'] == 'FAIL'])
        error_tests = len([t for t in self.test_results if t['status'] == 'ERROR'])
        
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        print(f"\n📊 TEST SUMMARY:")
        print(f"   Total Tests: {total_tests}")
        print(f"   Passed: {passed_tests} ✅")
        print(f"   Failed: {failed_tests} ❌")
        print(f"   Errors: {error_tests} ⚠️")
        print(f"   Success Rate: {success_rate:.1f}%")
        print(f"   Duration: {duration:.1f}s")
        
        # 按类别分组显示结果
        categories = {}
        for result in self.test_results:
            cat = result['category']
            if cat not in categories:
                categories[cat] = {'PASS': 0, 'FAIL': 0, 'ERROR': 0, 'INFO': 0, 'SKIP': 0}
            categories[cat][result['status']] = categories[cat].get(result['status'], 0) + 1
        
        print(f"\n📋 DETAILED RESULTS BY CATEGORY:")
        for category, stats in categories.items():
            total_cat = sum(stats.values())
            passed_cat = stats.get('PASS', 0)
            cat_rate = (passed_cat / total_cat * 100) if total_cat > 0 else 0
            print(f"   {category}: {passed_cat}/{total_cat} ({cat_rate:.1f}%)")
        
        # 显示失败的测试
        failed_results = [t for t in self.test_results if t['status'] in ['FAIL', 'ERROR']]
        if failed_results:
            print(f"\n❌ FAILED/ERROR TESTS:")
            for result in failed_results:
                print(f"   [{result['category']}] {result['test_name']}: {result['status']}")
                if result['details']:
                    print(f"      → {result['details']}")
        
        # 数值一致性摘要
        numerical_tests = [t for t in self.test_results if 'Range' in t['test_name'] or 'Consistency' in t['test_name']]
        numerical_passed = len([t for t in numerical_tests if t['status'] == 'PASS'])
        
        print(f"\n🔢 NUMERICAL ACCURACY SUMMARY:")
        print(f"   Numerical Tests: {len(numerical_tests)}")
        print(f"   Numerical Passed: {numerical_passed}")
        print(f"   Numerical Accuracy: {(numerical_passed/len(numerical_tests)*100) if numerical_tests else 0:.1f}%")
        
        # 最终评估
        if success_rate >= 90:
            print(f"\n🎉 OVERALL ASSESSMENT: EXCELLENT ({success_rate:.1f}%)")
            print("   All core numerical functions are working accurately")
        elif success_rate >= 75:
            print(f"\n✅ OVERALL ASSESSMENT: GOOD ({success_rate:.1f}%)")
            print("   Most numerical functions are working with minor issues")
        elif success_rate >= 50:
            print(f"\n⚠️  OVERALL ASSESSMENT: NEEDS IMPROVEMENT ({success_rate:.1f}%)")
            print("   Several numerical issues need attention")
        else:
            print(f"\n❌ OVERALL ASSESSMENT: CRITICAL ({success_rate:.1f}%)")
            print("   Major numerical issues require immediate attention")
        
        print("="*80)
        return success_rate

def main():
    """主函数"""
    tester = TotalFullRegressionTest()
    success_rate = tester.run_comprehensive_numerical_test()
    
    # 返回退出码
    if success_rate >= 75:
        sys.exit(0)  # 成功
    else:
        sys.exit(1)  # 失败

if __name__ == "__main__":
    main()