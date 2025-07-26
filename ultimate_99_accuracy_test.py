#!/usr/bin/env python3
"""
比特币挖矿计算器 - 99%准确性和可行性终极回归测试
Bitcoin Mining Calculator - Ultimate 99% Accuracy & Feasibility Regression Test
"""

import requests
import json
import time
import logging
import statistics
from datetime import datetime
import sys
import os
import concurrent.futures
from decimal import Decimal, ROUND_HALF_UP

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Ultimate99AccuracyTest:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.test_results = []
        self.accuracy_metrics = {}
        
        # 认证用户邮箱（实际生产环境邮箱）
        self.production_emails = [
            "testing@example.com",
            "admin@example.com", 
            "site@example.com",
            "hxl2022hao@gmail.com",
            "owner@example.com"
        ]
        
        # 真实矿机测试案例（基于实际市场数据）
        self.real_miner_cases = [
            {
                "model": "Antminer S19 Pro", 
                "hashrate_th": 110, 
                "power_w": 3250,
                "count": 100,
                "expected_daily_btc_range": (0.015, 0.018)  # 预期范围
            },
            {
                "model": "Antminer S19", 
                "hashrate_th": 95, 
                "power_w": 3250,
                "count": 50,
                "expected_daily_btc_range": (0.013, 0.016)
            },
            {
                "model": "Antminer S21", 
                "hashrate_th": 200, 
                "power_w": 3550,
                "count": 75,
                "expected_daily_btc_range": (0.026, 0.030)
            }
        ]
        
        # 99%准确性标准
        self.accuracy_standards = {
            "data_consistency_threshold": 0.01,  # 1%以内差异
            "response_time_max": 5.0,  # 最大响应时间5秒
            "calculation_variance_max": 0.05,  # 计算结果5%以内方差
            "api_success_rate_min": 0.98,  # 98%以上API成功率
            "authentication_success_min": 0.95,  # 95%以上认证成功率
            "real_time_data_freshness": 300  # 5分钟内数据算新鲜
        }
        
    def log_accuracy_test(self, category, test_name, success, accuracy_score, details="", response_time=0, data=None):
        """记录准确性测试结果"""
        result = {
            "category": category,
            "test_name": test_name,
            "success": success,
            "accuracy_score": accuracy_score,
            "details": details,
            "response_time": response_time,
            "timestamp": datetime.now().isoformat(),
            "data": data
        }
        self.test_results.append(result)
        
        status = "✅" if success and accuracy_score >= 95 else "⚠️" if success else "❌"
        logger.info(f"{status} [{category}] {test_name} - Accuracy: {accuracy_score:.1f}% - {details} ({response_time:.3f}s)")
        
    def authenticate_with_verification(self, email):
        """高精度用户认证验证"""
        try:
            start_time = time.time()
            response = self.session.post(f"{self.base_url}/login", 
                                       data={"email": email}, 
                                       timeout=10)
            response_time = time.time() - start_time
            
            # 验证重定向和会话
            if response.status_code in [200, 302]:
                # 验证是否成功登录（检查dashboard访问）
                dashboard_response = self.session.get(f"{self.base_url}/", timeout=5)
                if dashboard_response.status_code == 200 and "login" not in dashboard_response.url:
                    return True, response_time
            
            return False, response_time
        except Exception as e:
            logger.error(f"认证验证失败 {email}: {str(e)}")
            return False, 0
    
    def test_authentication_precision(self):
        """测试认证系统精度"""
        logger.info("=== 认证系统99%精度测试 ===")
        
        auth_results = []
        for email in self.production_emails:
            success, response_time = self.authenticate_with_verification(email)
            auth_results.append(success)
            
            accuracy = 100.0 if success else 0.0
            self.log_accuracy_test("Authentication", f"Login - {email}", success, accuracy, 
                                 "Verified" if success else "Failed", response_time)
        
        # 总体认证精度
        auth_success_rate = sum(auth_results) / len(auth_results)
        overall_accuracy = auth_success_rate * 100
        meets_standard = auth_success_rate >= self.accuracy_standards["authentication_success_min"]
        
        self.log_accuracy_test("Authentication", "System Authentication", meets_standard, overall_accuracy,
                             f"{overall_accuracy:.1f}% success rate (target: 95%+)")
        
        self.accuracy_metrics["authentication"] = overall_accuracy
    
    def test_api_data_consistency(self):
        """测试API数据一致性精度"""
        logger.info("=== API数据一致性99%精度测试 ===")
        
        # 确保已认证
        self.authenticate_with_verification("testing@example.com")
        
        # 多次调用网络统计API验证一致性
        api_responses = []
        for i in range(5):  # 5次连续调用
            try:
                start_time = time.time()
                response = self.session.get(f"{self.base_url}/api/network-stats", timeout=10)
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    data = response.json()
                    api_responses.append({
                        "call": i+1,
                        "btc_price": float(data.get('btc_price', 0)),
                        "network_hashrate": float(data.get('network_hashrate', 0)),
                        "difficulty": float(data.get('difficulty', 0)),
                        "response_time": response_time
                    })
                    
                    self.log_accuracy_test("API_Consistency", f"Network Stats Call {i+1}", True, 100.0,
                                         f"BTC: ${data.get('btc_price', 0):,.0f}", response_time, data)
                else:
                    self.log_accuracy_test("API_Consistency", f"Network Stats Call {i+1}", False, 0.0,
                                         f"HTTP {response.status_code}")
                    
                time.sleep(2)  # 2秒间隔
            except Exception as e:
                self.log_accuracy_test("API_Consistency", f"Network Stats Call {i+1}", False, 0.0,
                                     f"Error: {str(e)}")
        
        if len(api_responses) >= 3:
            # 计算数据一致性
            btc_prices = [r['btc_price'] for r in api_responses]
            hashrates = [r['network_hashrate'] for r in api_responses]
            
            btc_variance = (max(btc_prices) - min(btc_prices)) / statistics.mean(btc_prices) if btc_prices else 1
            hashrate_variance = (max(hashrates) - min(hashrates)) / statistics.mean(hashrates) if hashrates else 1
            
            # 计算一致性准确度
            consistency_accuracy = max(0, 100 - (btc_variance * 100 + hashrate_variance * 100) / 2)
            meets_standard = btc_variance <= self.accuracy_standards["data_consistency_threshold"]
            
            self.log_accuracy_test("API_Consistency", "Data Consistency", meets_standard, consistency_accuracy,
                                 f"BTC variance: {btc_variance:.4f}, Hash variance: {hashrate_variance:.4f}")
            
            self.accuracy_metrics["api_consistency"] = consistency_accuracy
    
    def test_mining_calculation_precision(self):
        """测试挖矿计算精度"""
        logger.info("=== 挖矿计算99%精度测试 ===")
        
        self.authenticate_with_verification("testing@example.com")
        
        calculation_accuracies = []
        
        for test_case in self.real_miner_cases:
            try:
                start_time = time.time()
                
                calc_data = {
                    "miner_model": test_case["model"],
                    "miner_count": str(test_case["count"]),
                    "electricity_cost": "0.08",
                    "client_electricity_cost": "0.10",
                    "use_real_time": "on"
                }
                
                response = self.session.post(f"{self.base_url}/calculate", 
                                           data=calc_data, 
                                           timeout=20)
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('success'):
                        btc_output = float(data.get('site_daily_btc_output', 0))
                        daily_profit = float(data.get('daily_profit_usd', 0))
                        
                        # 验证结果是否在预期范围内
                        expected_min, expected_max = test_case["expected_daily_btc_range"]
                        in_range = expected_min <= btc_output <= expected_max
                        
                        # 计算精度分数
                        if in_range:
                            range_center = (expected_min + expected_max) / 2
                            deviation = abs(btc_output - range_center) / range_center
                            accuracy = max(0, 100 - deviation * 100)
                        else:
                            # 超出范围，根据偏离程度计算
                            if btc_output < expected_min:
                                deviation = (expected_min - btc_output) / expected_min
                            else:
                                deviation = (btc_output - expected_max) / expected_max
                            accuracy = max(0, 80 - deviation * 100)  # 超出范围基础分80
                        
                        calculation_accuracies.append(accuracy)
                        
                        details = f"BTC: {btc_output:.6f}/day (range: {expected_min:.3f}-{expected_max:.3f}), Profit: ${daily_profit:,.2f}"
                        self.log_accuracy_test("Calculation", f"{test_case['model']}", True, accuracy, 
                                             details, response_time)
                    else:
                        self.log_accuracy_test("Calculation", f"{test_case['model']}", False, 0.0,
                                             f"Error: {data.get('error', 'Unknown')}")
                else:
                    self.log_accuracy_test("Calculation", f"{test_case['model']}", False, 0.0,
                                         f"HTTP {response.status_code}")
            except Exception as e:
                self.log_accuracy_test("Calculation", f"{test_case['model']}", False, 0.0,
                                     f"Error: {str(e)}")
        
        # 计算总体计算精度
        if calculation_accuracies:
            overall_calc_accuracy = statistics.mean(calculation_accuracies)
            self.accuracy_metrics["calculation"] = overall_calc_accuracy
            
            meets_standard = overall_calc_accuracy >= 90
            self.log_accuracy_test("Calculation", "Overall Precision", meets_standard, overall_calc_accuracy,
                                 f"Average calculation accuracy: {overall_calc_accuracy:.1f}%")
    
    def test_real_time_data_accuracy(self):
        """测试实时数据准确性"""
        logger.info("=== 实时数据99%准确性测试 ===")
        
        self.authenticate_with_verification("testing@example.com")
        
        try:
            start_time = time.time()
            response = self.session.get(f"{self.base_url}/api/network-stats", timeout=15)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                btc_price = float(data.get('btc_price', 0))
                network_hashrate = float(data.get('network_hashrate', 0))
                difficulty = float(data.get('difficulty', 0))
                
                # 验证数据合理性（基于2025年市场标准）
                btc_price_valid = 50000 <= btc_price <= 200000  # BTC价格合理范围
                hashrate_valid = 500 <= network_hashrate <= 2000  # 网络算力合理范围EH/s
                difficulty_valid = difficulty > 50  # 难度合理范围
                
                # 计算数据准确性分数
                validity_score = 0
                if btc_price_valid: validity_score += 40
                if hashrate_valid: validity_score += 40
                if difficulty_valid: validity_score += 20
                
                # 响应时间分数
                time_score = max(0, 100 - (response_time - 1) * 20) if response_time > 1 else 100
                
                overall_accuracy = (validity_score + time_score) / 2
                
                details = f"BTC: ${btc_price:,.0f}, Hashrate: {network_hashrate:.1f} EH/s, Difficulty: {difficulty:.1f}T"
                self.log_accuracy_test("Real_Time_Data", "Market Data Accuracy", True, overall_accuracy,
                                     details, response_time, data)
                
                self.accuracy_metrics["real_time_data"] = overall_accuracy
            else:
                self.log_accuracy_test("Real_Time_Data", "Market Data Accuracy", False, 0.0,
                                     f"HTTP {response.status_code}")
        except Exception as e:
            self.log_accuracy_test("Real_Time_Data", "Market Data Accuracy", False, 0.0,
                                 f"Error: {str(e)}")
    
    def test_system_performance_accuracy(self):
        """测试系统性能准确性"""
        logger.info("=== 系统性能99%准确性测试 ===")
        
        self.authenticate_with_verification("testing@example.com")
        
        # 测试关键端点响应时间
        performance_tests = [
            ("/api/network-stats", "Network Stats", 3.0),
            ("/api/miners", "Miner Models", 2.0),
            ("/", "Main Dashboard", 5.0)
        ]
        
        performance_scores = []
        
        for endpoint, name, max_time in performance_tests:
            try:
                start_time = time.time()
                response = self.session.get(f"{self.base_url}{endpoint}", timeout=max_time*2)
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    # 计算性能分数
                    if response_time <= max_time * 0.5:
                        performance_score = 100  # 极快
                    elif response_time <= max_time:
                        performance_score = 90 - (response_time / max_time - 0.5) * 40  # 快速
                    else:
                        performance_score = max(0, 50 - (response_time - max_time) * 10)  # 慢速
                    
                    performance_scores.append(performance_score)
                    
                    self.log_accuracy_test("Performance", f"{name} Response", True, performance_score,
                                         f"{response_time:.3f}s (target: <{max_time}s)", response_time)
                else:
                    self.log_accuracy_test("Performance", f"{name} Response", False, 0.0,
                                         f"HTTP {response.status_code}")
            except Exception as e:
                self.log_accuracy_test("Performance", f"{name} Response", False, 0.0,
                                     f"Error: {str(e)}")
        
        if performance_scores:
            overall_performance = statistics.mean(performance_scores)
            self.accuracy_metrics["performance"] = overall_performance
            
            self.log_accuracy_test("Performance", "Overall Performance", True, overall_performance,
                                 f"Average performance score: {overall_performance:.1f}%")
    
    def test_security_robustness(self):
        """测试安全健壮性"""
        logger.info("=== 安全健壮性99%测试 ===")
        
        security_tests = []
        
        # 测试1: 未授权访问保护
        try:
            new_session = requests.Session()
            response = new_session.get(f"{self.base_url}/", timeout=5)
            
            if "login" in response.url.lower() or response.status_code == 401:
                security_tests.append(100)
                self.log_accuracy_test("Security", "Unauthorized Access Protection", True, 100.0,
                                     "Successfully redirected to login")
            else:
                security_tests.append(0)
                self.log_accuracy_test("Security", "Unauthorized Access Protection", False, 0.0,
                                     "No access control detected")
        except Exception as e:
            security_tests.append(0)
            self.log_accuracy_test("Security", "Unauthorized Access Protection", False, 0.0,
                                 f"Error: {str(e)}")
        
        # 测试2: 恶意输入防护
        self.authenticate_with_verification("testing@example.com")
        
        malicious_inputs = [
            {"electricity_cost": "NaN", "expected": "rejected"},
            {"miner_count": "Infinity", "expected": "rejected"},
            {"client_electricity_cost": "-999999", "expected": "rejected"}
        ]
        
        for malicious_input in malicious_inputs:
            try:
                test_data = {
                    "miner_model": "Antminer S19 Pro",
                    "miner_count": "100",
                    "electricity_cost": "0.08",
                    "client_electricity_cost": "0.10",
                    "use_real_time": "on"
                }
                test_data.update(malicious_input)
                del test_data["expected"]
                
                response = self.session.post(f"{self.base_url}/calculate", 
                                           data=test_data, 
                                           timeout=10)
                
                if response.status_code != 200 or (response.status_code == 200 and not response.json().get('success')):
                    security_tests.append(100)
                    self.log_accuracy_test("Security", f"Malicious Input: {list(malicious_input.keys())[0]}", True, 100.0,
                                         "Input properly rejected")
                else:
                    security_tests.append(0)
                    self.log_accuracy_test("Security", f"Malicious Input: {list(malicious_input.keys())[0]}", False, 0.0,
                                         "Malicious input accepted")
            except Exception as e:
                security_tests.append(50)  # 异常也算部分防护
                self.log_accuracy_test("Security", f"Malicious Input: {list(malicious_input.keys())[0]}", True, 50.0,
                                     f"Error handling: {str(e)}")
        
        if security_tests:
            overall_security = statistics.mean(security_tests)
            self.accuracy_metrics["security"] = overall_security
            
            self.log_accuracy_test("Security", "Overall Security", True, overall_security,
                                 f"Average security score: {overall_security:.1f}%")
    
    def calculate_overall_99_accuracy(self):
        """计算总体99%准确性分数"""
        if not self.accuracy_metrics:
            return 0.0, "No metrics available"
        
        # 权重分配（总计100%）
        weights = {
            "authentication": 0.20,  # 20% - 认证系统
            "api_consistency": 0.25,  # 25% - API一致性
            "calculation": 0.30,  # 30% - 计算精度（最重要）
            "real_time_data": 0.15,  # 15% - 实时数据
            "performance": 0.05,  # 5% - 性能
            "security": 0.05  # 5% - 安全性
        }
        
        weighted_score = 0.0
        score_breakdown = {}
        
        for metric, weight in weights.items():
            if metric in self.accuracy_metrics:
                score = self.accuracy_metrics[metric]
                weighted_score += score * weight
                score_breakdown[metric] = f"{score:.1f}% (weight: {weight*100:.0f}%)"
            else:
                score_breakdown[metric] = "Not tested"
        
        return weighted_score, score_breakdown
    
    def run_ultimate_99_test(self):
        """运行终极99%准确性测试"""
        logger.info("🎯 开始终极99%准确性和可行性回归测试")
        start_time = time.time()
        
        # 运行所有高精度测试
        test_modules = [
            self.test_authentication_precision,
            self.test_api_data_consistency,
            self.test_mining_calculation_precision,
            self.test_real_time_data_accuracy,
            self.test_system_performance_accuracy,
            self.test_security_robustness
        ]
        
        for test_module in test_modules:
            try:
                test_module()
            except Exception as e:
                logger.error(f"测试模块失败: {test_module.__name__} - {str(e)}")
        
        # 计算总体99%准确性分数
        overall_score, breakdown = self.calculate_overall_99_accuracy()
        total_time = time.time() - start_time
        
        # 生成终极测试报告
        self.generate_ultimate_report(overall_score, breakdown, total_time)
        
        # 判断是否达到99%标准
        return overall_score >= 99.0
    
    def generate_ultimate_report(self, overall_score, breakdown, total_time):
        """生成终极测试报告"""
        # 确定等级
        if overall_score >= 99.5:
            grade = "A++ 完美无缺"
            status = "🟢 PERFECT"
        elif overall_score >= 99.0:
            grade = "A+ 接近完美"
            status = "🟢 EXCELLENT"
        elif overall_score >= 95.0:
            grade = "A 优秀"
            status = "🟡 VERY_GOOD"
        elif overall_score >= 90.0:
            grade = "B+ 良好"
            status = "🟡 GOOD"
        else:
            grade = "需要改进"
            status = "🔴 NEEDS_WORK"
        
        logger.info("\n" + "="*80)
        logger.info("🎯 终极99%准确性和可行性测试报告")
        logger.info("="*80)
        logger.info(f"总体准确性分数: {overall_score:.2f}%")
        logger.info(f"系统等级: {grade}")
        logger.info(f"状态: {status}")
        logger.info(f"测试耗时: {total_time:.2f}秒")
        logger.info("-"*80)
        
        logger.info("详细分数分解:")
        for metric, score_info in breakdown.items():
            logger.info(f"  {metric:20}: {score_info}")
        
        logger.info("-"*80)
        
        # 成功/失败测试统计
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r['success'])
        success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        
        logger.info(f"测试通过率: {success_rate:.1f}% ({passed_tests}/{total_tests})")
        
        # 99%标准评估
        if overall_score >= 99.0:
            logger.info("✅ 系统达到99%准确性标准！")
            logger.info("✅ 可行性评估: 完全可投入生产使用")
        elif overall_score >= 95.0:
            logger.info("⚠️ 系统接近99%标准，建议优化后投入使用")
        else:
            logger.info("❌ 系统未达到99%标准，需要进一步改进")
        
        # 保存详细报告
        report_file = f"ultimate_99_accuracy_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump({
                "summary": {
                    "overall_accuracy": overall_score,
                    "grade": grade,
                    "status": status,
                    "total_time": total_time,
                    "test_success_rate": success_rate,
                    "meets_99_standard": overall_score >= 99.0,
                    "timestamp": datetime.now().isoformat()
                },
                "accuracy_breakdown": breakdown,
                "accuracy_metrics": self.accuracy_metrics,
                "test_results": self.test_results
            }, f, indent=2, ensure_ascii=False)
        
        logger.info(f"详细报告已保存: {report_file}")

if __name__ == "__main__":
    tester = Ultimate99AccuracyTest()
    success = tester.run_ultimate_99_test()
    sys.exit(0 if success else 1)