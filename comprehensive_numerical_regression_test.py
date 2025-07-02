#!/usr/bin/env python3
"""
全面数值回归测试 - 目标99%成功率
Comprehensive Numerical Regression Test - Target 99% Success Rate

专注于数值准确性的深度测试，涵盖所有计算模块
Deep testing focused on numerical accuracy covering all calculation modules
"""

import requests
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Tuple
import time

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ComprehensiveNumericalRegressionTest:
    def __init__(self):
        self.base_url = "http://localhost:5000"
        self.session = requests.Session()
        self.test_results = []
        self.module_stats = {}
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        self.warning_tests = 0
        
        # 测试模块定义
        self.test_modules = {
            "核心API端点": {
                "description": "Core API Endpoints",
                "tests": ["btc_price", "network_stats", "miners_list", "sha256_comparison"]
            },
            "矿机数据验证": {
                "description": "Miner Data Validation", 
                "tests": ["miner_specifications", "hashrate_accuracy", "power_consumption", "efficiency_ratios"]
            },
            "挖矿计算引擎": {
                "description": "Mining Calculation Engine",
                "tests": ["basic_profitability", "electricity_costs", "roi_calculations", "breakeven_analysis"]
            },
            "网络数据处理": {
                "description": "Network Data Processing",
                "tests": ["difficulty_conversion", "hashrate_validation", "block_reward", "time_calculations"]
            },
            "投资分析模块": {
                "description": "Investment Analysis Module",
                "tests": ["investment_scenarios", "payback_periods", "risk_assessment", "portfolio_analysis"]
            },
            "限电管理系统": {
                "description": "Curtailment Management System",
                "tests": ["curtailment_calculations", "shutdown_strategies", "efficiency_optimization", "power_management"]
            },
            "技术指标分析": {
                "description": "Technical Analysis Module",
                "tests": ["price_analysis", "trend_indicators", "market_data", "historical_accuracy"]
            },
            "数据一致性验证": {
                "description": "Data Consistency Validation",
                "tests": ["cross_api_validation", "temporal_consistency", "calculation_precision", "error_margins"]
            }
        }
        
    def log_test_result(self, module: str, test_name: str, status: str, expected: str, actual: str, details: str = ""):
        """记录测试结果"""
        self.total_tests += 1
        
        if status == "PASS":
            self.passed_tests += 1
        elif status == "FAIL":
            self.failed_tests += 1
        elif status == "WARN":
            self.warning_tests += 1
            
        if module not in self.module_stats:
            self.module_stats[module] = {"passed": 0, "failed": 0, "warned": 0, "total": 0}
            
        self.module_stats[module]["total"] += 1
        if status == "PASS":
            self.module_stats[module]["passed"] += 1
        elif status == "FAIL":
            self.module_stats[module]["failed"] += 1
        elif status == "WARN":
            self.module_stats[module]["warned"] += 1
            
        result = {
            "timestamp": datetime.now().isoformat(),
            "module": module,
            "test_name": test_name,
            "status": status,
            "expected": expected,
            "actual": actual,
            "details": details
        }
        self.test_results.append(result)
        
        # 实时显示测试结果
        status_icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"{status_icon} [{module}] {test_name}")
        print(f"   期望: {expected}, 实际: {actual}")
        if details:
            print(f"   详情: {details}")
            
    def authenticate(self) -> bool:
        """系统认证"""
        try:
            auth_data = {"email": "hxl2022hao@gmail.com"}
            response = self.session.post(f"{self.base_url}/login", data=auth_data)
            success = response.status_code == 200
            print("🚀 启动全面数值回归测试...")
            print("✅ 认证成功" if success else "❌ 认证失败")
            return success
        except Exception as e:
            print(f"❌ 认证异常: {e}")
            return False
            
    def test_core_api_endpoints(self):
        """测试核心API端点"""
        module = "核心API端点"
        print(f"\n=== {module} ===")
        
        # 1. BTC价格API测试
        try:
            response = self.session.get(f"{self.base_url}/api/btc-price")
            if response.status_code == 200:
                data = response.json()
                if data.get('success') and 'price' in data:
                    price = data['price']
                    if 50000 <= price <= 200000:
                        self.log_test_result(module, "BTC价格API", "PASS", 
                                           "$50,000-$200,000", f"${price:,.0f}")
                    else:
                        self.log_test_result(module, "BTC价格API", "WARN",
                                           "$50,000-$200,000", f"${price:,.0f}")
                else:
                    self.log_test_result(module, "BTC价格API", "FAIL",
                                       "有效响应", "数据格式错误")
            else:
                self.log_test_result(module, "BTC价格API", "FAIL",
                                   "HTTP 200", f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test_result(module, "BTC价格API", "FAIL", "正常响应", f"异常: {e}")
            
        # 2. 网络统计API测试
        try:
            response = self.session.get(f"{self.base_url}/api/network-stats")
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    # 验证网络算力
                    hashrate = data.get('network_hashrate', 0)
                    if 300 <= hashrate <= 2000:
                        self.log_test_result(module, "网络算力范围", "PASS",
                                           "300-2000 EH/s", f"{hashrate} EH/s")
                    else:
                        self.log_test_result(module, "网络算力范围", "WARN",
                                           "300-2000 EH/s", f"{hashrate} EH/s")
                    
                    # 验证难度值并转换为T单位
                    difficulty = data.get('network_difficulty', 0)
                    difficulty_t = difficulty / 1e12  # 转换为T单位
                    if 50 <= difficulty_t <= 200:
                        self.log_test_result(module, "网络难度范围", "PASS",
                                           "50-200T", f"{difficulty_t:.1f}T")
                    else:
                        self.log_test_result(module, "网络难度范围", "WARN",
                                           "50-200T", f"{difficulty_t:.1f}T")
                else:
                    self.log_test_result(module, "网络统计API", "FAIL",
                                       "成功响应", "数据格式错误")
            else:
                self.log_test_result(module, "网络统计API", "FAIL",
                                   "HTTP 200", f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test_result(module, "网络统计API", "FAIL", "正常响应", f"异常: {e}")
            
        # 3. 矿机列表API测试
        try:
            response = self.session.get(f"{self.base_url}/api/miners")
            if response.status_code == 200:
                data = response.json()
                if data.get('success') and 'miners' in data:
                    miners = data['miners']
                    if len(miners) >= 10:
                        self.log_test_result(module, "矿机列表完整性", "PASS",
                                           "≥10个型号", f"{len(miners)}个型号")
                    else:
                        self.log_test_result(module, "矿机列表完整性", "WARN",
                                           "≥10个型号", f"{len(miners)}个型号")
                else:
                    self.log_test_result(module, "矿机列表API", "FAIL",
                                       "有效数据", "数据格式错误")
            else:
                self.log_test_result(module, "矿机列表API", "FAIL",
                                   "HTTP 200", f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test_result(module, "矿机列表API", "FAIL", "正常响应", f"异常: {e}")
            
        # 4. SHA256对比API测试
        try:
            response = self.session.get(f"{self.base_url}/api/sha256-comparison")
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    self.log_test_result(module, "SHA256对比API", "PASS",
                                       "成功响应", "数据获取正常")
                else:
                    self.log_test_result(module, "SHA256对比API", "WARN",
                                       "成功响应", "API响应但无数据")
            else:
                self.log_test_result(module, "SHA256对比API", "FAIL",
                                   "HTTP 200", f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test_result(module, "SHA256对比API", "FAIL", "正常响应", f"异常: {e}")
            
    def test_miner_data_validation(self):
        """测试矿机数据验证"""
        module = "矿机数据验证"
        print(f"\n=== {module} ===")
        
        try:
            response = self.session.get(f"{self.base_url}/api/miners")
            if response.status_code == 200:
                data = response.json()
                if data.get('success') and 'miners' in data:
                    miners = data['miners']
                    
                    # 测试关键矿机型号
                    test_miners = [
                        {"name": "Antminer S19 Pro", "expected_hashrate": 110, "expected_power": 3250},
                        {"name": "Antminer S19", "expected_hashrate": 95, "expected_power": 3250},
                        {"name": "Antminer S21 XP", "expected_hashrate": 473, "expected_power": 5676},
                        {"name": "Antminer S21", "expected_hashrate": 200, "expected_power": 3500}
                    ]
                    
                    for test_miner in test_miners:
                        found_miner = None
                        for miner in miners:
                            if test_miner["name"] in miner.get("name", ""):
                                found_miner = miner
                                break
                                
                        if found_miner:
                            # 验证算力
                            actual_hashrate = found_miner.get("hashrate", 0)
                            expected_hashrate = test_miner["expected_hashrate"]
                            hashrate_diff = abs(actual_hashrate - expected_hashrate) / expected_hashrate * 100
                            
                            if hashrate_diff <= 5:  # 5%容差
                                self.log_test_result(module, f"{test_miner['name']} 算力", "PASS",
                                                   f"{expected_hashrate} TH/s", f"{actual_hashrate} TH/s")
                            else:
                                self.log_test_result(module, f"{test_miner['name']} 算力", "FAIL",
                                                   f"{expected_hashrate} TH/s", f"{actual_hashrate} TH/s")
                            
                            # 验证功耗
                            actual_power = found_miner.get("power_consumption", 0)
                            expected_power = test_miner["expected_power"]
                            power_diff = abs(actual_power - expected_power) / expected_power * 100
                            
                            if power_diff <= 5:  # 5%容差
                                self.log_test_result(module, f"{test_miner['name']} 功耗", "PASS",
                                                   f"{expected_power} W", f"{actual_power} W")
                            else:
                                self.log_test_result(module, f"{test_miner['name']} 功耗", "FAIL",
                                                   f"{expected_power} W", f"{actual_power} W")
                            
                            # 验证效率比
                            if actual_power > 0:
                                efficiency = actual_hashrate / (actual_power / 1000)  # TH/s per kW
                                if 15 <= efficiency <= 200:  # 合理的效率范围
                                    self.log_test_result(module, f"{test_miner['name']} 效率", "PASS",
                                                       "15-200 TH/s/kW", f"{efficiency:.1f} TH/s/kW")
                                else:
                                    self.log_test_result(module, f"{test_miner['name']} 效率", "WARN",
                                                       "15-200 TH/s/kW", f"{efficiency:.1f} TH/s/kW")
                        else:
                            self.log_test_result(module, f"{test_miner['name']} 存在性", "FAIL",
                                               "找到矿机", "未找到")
                                               
        except Exception as e:
            self.log_test_result(module, "矿机数据获取", "FAIL", "正常响应", f"异常: {e}")
            
    def test_mining_calculation_engine(self):
        """测试挖矿计算引擎"""
        module = "挖矿计算引擎"
        print(f"\n=== {module} ===")
        
        # 测试不同电价下的计算准确性
        test_scenarios = [
            {"description": "低电价场景", "electricity_cost": 0.05, "miner_count": 1},
            {"description": "中等电价场景", "electricity_cost": 0.08, "miner_count": 1},
            {"description": "高电价场景", "electricity_cost": 0.12, "miner_count": 1},
            {"description": "大规模挖矿", "electricity_cost": 0.06, "miner_count": 100}
        ]
        
        for scenario in test_scenarios:
            try:
                calc_data = {
                    'hashrate': 110,  # S19 Pro
                    'power_consumption': 3250,
                    'electricity_cost': scenario['electricity_cost'],
                    'miner_count': scenario['miner_count'],
                    'site_power_mw': 10,
                    'use_real_time_data': True
                }
                
                response = self.session.post(f"{self.base_url}/calculate", 
                                           json=calc_data,
                                           headers={'Content-Type': 'application/json'})
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # 验证基本响应结构
                    if result.get('success'):
                        # 验证BTC产出
                        daily_btc = result.get('site_daily_btc_output', 0)
                        if daily_btc > 0:
                            self.log_test_result(module, f"BTC产出计算 - {scenario['description']}", "PASS",
                                               ">0 BTC", f"{daily_btc:.8f} BTC")
                        else:
                            self.log_test_result(module, f"BTC产出计算 - {scenario['description']}", "FAIL",
                                               ">0 BTC", f"{daily_btc:.8f} BTC")
                        
                        # 验证利润计算
                        daily_profit = result.get('daily_profit_usd', 0)
                        expected_range = (-1000, 1000)  # 合理利润范围
                        if expected_range[0] <= daily_profit <= expected_range[1]:
                            self.log_test_result(module, f"利润计算 - {scenario['description']}", "PASS",
                                               f"${expected_range[0]}到${expected_range[1]}", 
                                               f"${daily_profit:.2f}")
                        else:
                            self.log_test_result(module, f"利润计算 - {scenario['description']}", "WARN",
                                               f"${expected_range[0]}到${expected_range[1]}", 
                                               f"${daily_profit:.2f}")
                        
                        # 验证电费计算
                        electricity_cost_data = result.get('electricity_cost', {})
                        if isinstance(electricity_cost_data, dict):
                            daily_electricity_cost = electricity_cost_data.get('daily', 0)
                            if daily_electricity_cost > 0:
                                self.log_test_result(module, f"电费计算 - {scenario['description']}", "PASS",
                                                   ">$0", f"${daily_electricity_cost:.2f}")
                            else:
                                self.log_test_result(module, f"电费计算 - {scenario['description']}", "FAIL",
                                                   ">$0", f"${daily_electricity_cost:.2f}")
                        else:
                            self.log_test_result(module, f"电费计算 - {scenario['description']}", "FAIL",
                                               "有效数据结构", "数据格式错误")
                        
                        # 验证网络数据
                        network_data = result.get('network_data', {})
                        btc_price = network_data.get('btc_price', 0)
                        if 50000 <= btc_price <= 200000:
                            self.log_test_result(module, f"网络数据集成 - {scenario['description']}", "PASS",
                                               "$50,000-$200,000", f"${btc_price:,.0f}")
                        else:
                            self.log_test_result(module, f"网络数据集成 - {scenario['description']}", "WARN",
                                               "$50,000-$200,000", f"${btc_price:,.0f}")
                    else:
                        self.log_test_result(module, f"计算响应 - {scenario['description']}", "FAIL",
                                           "成功响应", "计算失败")
                else:
                    self.log_test_result(module, f"计算请求 - {scenario['description']}", "FAIL",
                                       "HTTP 200", f"HTTP {response.status_code}")
                    
            except Exception as e:
                self.log_test_result(module, f"计算异常 - {scenario['description']}", "FAIL",
                                   "正常执行", f"异常: {e}")
                                   
    def test_investment_analysis_module(self):
        """测试投资分析模块"""
        module = "投资分析模块"
        print(f"\n=== {module} ===")
        
        # 测试投资场景分析
        investment_scenarios = [
            {"investment": 25000, "description": "小型投资"},
            {"investment": 100000, "description": "中型投资"},
            {"investment": 500000, "description": "大型投资"}
        ]
        
        for scenario in investment_scenarios:
            try:
                calc_data = {
                    'hashrate': 110,
                    'power_consumption': 3250,
                    'electricity_cost': 0.07,
                    'miner_count': 1,
                    'host_investment': scenario['investment'],
                    'use_real_time_data': True
                }
                
                response = self.session.post(f"{self.base_url}/calculate", 
                                           json=calc_data,
                                           headers={'Content-Type': 'application/json'})
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get('success'):
                        # 验证ROI数据
                        roi_data = result.get('roi_analysis', {})
                        if roi_data:
                            host_roi = roi_data.get('host', {})
                            if host_roi:
                                payback_months = host_roi.get('payback_months', 0)
                                if 6 <= payback_months <= 60:  # 合理的回本期间
                                    self.log_test_result(module, f"投资回本期 - {scenario['description']}", "PASS",
                                                       "6-60个月", f"{payback_months:.1f}个月")
                                else:
                                    self.log_test_result(module, f"投资回本期 - {scenario['description']}", "WARN",
                                                       "6-60个月", f"{payback_months:.1f}个月")
                            else:
                                self.log_test_result(module, f"ROI数据 - {scenario['description']}", "FAIL",
                                                   "有效ROI数据", "ROI数据缺失")
                        else:
                            self.log_test_result(module, f"ROI分析 - {scenario['description']}", "FAIL",
                                               "ROI分析数据", "分析数据缺失")
                    else:
                        self.log_test_result(module, f"投资计算 - {scenario['description']}", "FAIL",
                                           "成功响应", "计算失败")
                else:
                    self.log_test_result(module, f"投资请求 - {scenario['description']}", "FAIL",
                                       "HTTP 200", f"HTTP {response.status_code}")
                    
            except Exception as e:
                self.log_test_result(module, f"投资分析异常 - {scenario['description']}", "FAIL",
                                   "正常执行", f"异常: {e}")
                                   
    def test_technical_analysis_module(self):
        """测试技术指标分析模块"""
        module = "技术指标分析"
        print(f"\n=== {module} ===")
        
        try:
            # 测试分析系统市场数据
            response = self.session.get(f"{self.base_url}/api/analytics/market-data")
            if response.status_code == 200:
                data = response.json()
                if data.get('success') and 'data' in data:
                    market_data = data['data']
                    
                    # 验证BTC价格
                    btc_price = market_data.get('btc_price')
                    if btc_price and 50000 <= btc_price <= 200000:
                        self.log_test_result(module, "市场数据BTC价格", "PASS",
                                           "$50,000-$200,000", f"${btc_price:,.0f}")
                    else:
                        self.log_test_result(module, "市场数据BTC价格", "WARN",
                                           "$50,000-$200,000", f"${btc_price}")
                    
                    # 验证网络算力
                    network_hashrate = market_data.get('network_hashrate')
                    if network_hashrate and 300 <= network_hashrate <= 2000:
                        self.log_test_result(module, "市场数据网络算力", "PASS",
                                           "300-2000 EH/s", f"{network_hashrate} EH/s")
                    else:
                        self.log_test_result(module, "市场数据网络算力", "WARN",
                                           "300-2000 EH/s", f"{network_hashrate}")
                        
                    # 验证恐惧贪婪指数
                    fear_greed = market_data.get('fear_greed_index')
                    if fear_greed and 0 <= fear_greed <= 100:
                        self.log_test_result(module, "恐惧贪婪指数", "PASS",
                                           "0-100", f"{fear_greed}")
                    else:
                        self.log_test_result(module, "恐惧贪婪指数", "WARN",
                                           "0-100", f"{fear_greed}")
                else:
                    self.log_test_result(module, "市场数据API", "FAIL",
                                       "有效数据", "数据格式错误")
            else:
                self.log_test_result(module, "市场数据API", "FAIL",
                                   "HTTP 200", f"HTTP {response.status_code}")
                                   
            # 测试价格历史数据
            response = self.session.get(f"{self.base_url}/api/analytics/price-history")
            if response.status_code == 200:
                data = response.json()
                if data.get('success') and 'data' in data:
                    price_history = data['data']
                    if len(price_history) >= 10:
                        self.log_test_result(module, "价格历史数据量", "PASS",
                                           "≥10条记录", f"{len(price_history)}条记录")
                        
                        # 验证数据质量
                        valid_records = sum(1 for record in price_history[:10] 
                                          if record.get('btc_price') and record.get('btc_price') > 0)
                        if valid_records >= 8:
                            self.log_test_result(module, "价格历史数据质量", "PASS",
                                               "≥80%有效", f"{valid_records}/10有效")
                        else:
                            self.log_test_result(module, "价格历史数据质量", "WARN",
                                               "≥80%有效", f"{valid_records}/10有效")
                    else:
                        self.log_test_result(module, "价格历史数据量", "WARN",
                                           "≥10条记录", f"{len(price_history)}条记录")
                else:
                    self.log_test_result(module, "价格历史API", "FAIL",
                                       "有效数据", "数据格式错误")
            else:
                self.log_test_result(module, "价格历史API", "FAIL",
                                   "HTTP 200", f"HTTP {response.status_code}")
                                   
        except Exception as e:
            self.log_test_result(module, "技术分析模块", "FAIL", "正常执行", f"异常: {e}")
            
    def test_data_consistency_validation(self):
        """测试数据一致性验证"""
        module = "数据一致性验证"
        print(f"\n=== {module} ===")
        
        try:
            # 获取多个API的BTC价格进行一致性验证
            price_sources = []
            
            # 源1: BTC价格API
            response1 = self.session.get(f"{self.base_url}/api/btc-price")
            if response1.status_code == 200:
                data1 = response1.json()
                if data1.get('success') and 'price' in data1:
                    price_sources.append(("BTC价格API", data1['price']))
                    
            # 源2: 网络统计API
            response2 = self.session.get(f"{self.base_url}/api/network-stats")
            if response2.status_code == 200:
                data2 = response2.json()
                if data2.get('success') and 'btc_price' in data2:
                    price_sources.append(("网络统计API", data2['btc_price']))
                    
            # 源3: 分析系统API
            response3 = self.session.get(f"{self.base_url}/api/analytics/market-data")
            if response3.status_code == 200:
                data3 = response3.json()
                if data3.get('success') and 'data' in data3:
                    market_data = data3['data']
                    if 'btc_price' in market_data:
                        price_sources.append(("分析系统API", market_data['btc_price']))
            
            # 验证价格一致性
            if len(price_sources) >= 2:
                max_diff = 0
                base_price = price_sources[0][1]
                for source_name, price in price_sources[1:]:
                    diff_pct = abs(price - base_price) / base_price * 100
                    max_diff = max(max_diff, diff_pct)
                
                if max_diff <= 2:  # 2%容差
                    self.log_test_result(module, "BTC价格一致性", "PASS",
                                       "≤2%差异", f"{max_diff:.2f}%差异")
                else:
                    self.log_test_result(module, "BTC价格一致性", "WARN",
                                       "≤2%差异", f"{max_diff:.2f}%差异")
            else:
                self.log_test_result(module, "BTC价格一致性", "FAIL",
                                   "≥2个数据源", f"{len(price_sources)}个数据源")
                                   
            # 验证计算精度
            calc_data = {
                'hashrate': 100,
                'power_consumption': 3000,
                'electricity_cost': 0.06,
                'miner_count': 1,
                'use_real_time_data': True
            }
            
            # 执行两次相同计算
            results = []
            for i in range(2):
                response = self.session.post(f"{self.base_url}/calculate", 
                                           json=calc_data,
                                           headers={'Content-Type': 'application/json'})
                if response.status_code == 200:
                    result = response.json()
                    if result.get('success'):
                        results.append(result.get('site_daily_btc_output', 0))
                        
            if len(results) == 2:
                if results[0] == results[1]:
                    self.log_test_result(module, "计算一致性", "PASS",
                                       "完全一致", "两次计算结果相同")
                else:
                    diff_pct = abs(results[0] - results[1]) / results[0] * 100 if results[0] > 0 else 100
                    if diff_pct <= 0.1:  # 0.1%容差
                        self.log_test_result(module, "计算一致性", "PASS",
                                           "≤0.1%差异", f"{diff_pct:.4f}%差异")
                    else:
                        self.log_test_result(module, "计算一致性", "WARN",
                                           "≤0.1%差异", f"{diff_pct:.4f}%差异")
            else:
                self.log_test_result(module, "计算一致性", "FAIL",
                                   "两次成功计算", f"{len(results)}次成功")
                                   
        except Exception as e:
            self.log_test_result(module, "数据一致性验证", "FAIL", "正常执行", f"异常: {e}")
            
    def run_comprehensive_test(self):
        """运行全面测试"""
        if not self.authenticate():
            return
            
        # 执行所有测试模块
        self.test_core_api_endpoints()
        self.test_miner_data_validation()
        self.test_mining_calculation_engine()
        self.test_investment_analysis_module()
        self.test_technical_analysis_module()
        self.test_data_consistency_validation()
        
        # 生成测试报告
        self.generate_comprehensive_report()
        
    def generate_comprehensive_report(self):
        """生成全面测试报告"""
        success_rate = (self.passed_tests / self.total_tests * 100) if self.total_tests > 0 else 0
        
        print("\n" + "="*80)
        print("🔍 COMPREHENSIVE NUMERICAL REGRESSION TEST REPORT")
        print("全面数值回归测试报告")
        print("="*80)
        
        print(f"\n📊 总体统计:")
        print(f"   总测试数: {self.total_tests}")
        print(f"   通过: {self.passed_tests} ✅")
        print(f"   失败: {self.failed_tests} ❌") 
        print(f"   警告: {self.warning_tests} ⚠️")
        print(f"   成功率: {success_rate:.1f}%")
        
        print(f"\n📋 模块统计:")
        for module, stats in self.module_stats.items():
            module_success_rate = (stats['passed'] / stats['total'] * 100) if stats['total'] > 0 else 0
            print(f"   {module}: {stats['passed']}/{stats['total']} ({module_success_rate:.1f}%)")
            
        # 成功率评级
        if success_rate >= 99:
            grade = "优秀 (A+)"
            color = "🟢"
        elif success_rate >= 95:
            grade = "良好 (A)"
            color = "🟢"
        elif success_rate >= 90:
            grade = "中等 (B)"
            color = "🟡"
        elif success_rate >= 80:
            grade = "较差 (C)"
            color = "🟡"
        else:
            grade = "失败 (D)"
            color = "🔴"
            
        print(f"\n🎯 最终评级: {color} {grade}")
        
        if self.failed_tests > 0:
            print(f"\n❌ 失败测试详情:")
            for result in self.test_results:
                if result['status'] == 'FAIL':
                    print(f"   [{result['module']}] {result['test_name']}: {result['details']}")
                    
        if success_rate >= 99:
            print(f"\n💡 状态: 系统已达到99%成功率目标，生产就绪！")
        else:
            needed_fixes = self.failed_tests + (self.warning_tests // 2)
            print(f"💡 建议: 需修复 {needed_fixes} 个问题以达到99%目标")
            
        print("="*80)

def main():
    """主函数"""
    test = ComprehensiveNumericalRegressionTest()
    test.run_comprehensive_test()

if __name__ == "__main__":
    main()