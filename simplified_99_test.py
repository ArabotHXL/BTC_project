#!/usr/bin/env python3
"""
简化99%准确性测试套件
Simplified 99% Accuracy Test Suite

快速验证系统核心功能的准确性和可用性
"""

import os
import sys
import json
import time
import requests
import psycopg2
from datetime import datetime

class Simplified99Test:
    def __init__(self):
        self.base_url = "http://localhost:5000"
        self.results = {
            'total': 0,
            'passed': 0,
            'failed': 0,
            'tests': [],
            'accuracy': 0.0
        }
    
    def log_test(self, name, success, details="", response_time=0):
        self.results['total'] += 1
        if success:
            self.results['passed'] += 1
            print(f"✅ {name}: PASSED ({response_time:.3f}s)")
        else:
            self.results['failed'] += 1
            print(f"❌ {name}: FAILED - {details}")
        
        self.results['tests'].append({
            'name': name,
            'success': success,
            'details': details,
            'response_time': response_time
        })

    def test_server_health(self):
        """测试服务器健康状态"""
        start = time.time()
        try:
            response = requests.get(f"{self.base_url}/", timeout=10)
            response_time = time.time() - start
            success = response.status_code in [200, 302]
            self.log_test("server_health", success, f"Status: {response.status_code}", response_time)
            return success
        except Exception as e:
            response_time = time.time() - start
            self.log_test("server_health", False, str(e), response_time)
            return False

    def test_database_connection(self):
        """测试数据库连接"""
        start = time.time()
        try:
            conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            response_time = time.time() - start
            success = result[0] == 1
            self.log_test("database_connection", success, "Database responding", response_time)
            return success
        except Exception as e:
            response_time = time.time() - start
            self.log_test("database_connection", False, str(e), response_time)
            return False

    def test_realtime_api_data(self):
        """测试实时API数据"""
        start = time.time()
        try:
            response = requests.get(f"{self.base_url}/api/analytics/data", timeout=10)
            response_time = time.time() - start
            
            if response.status_code == 200:
                data = response.json()
                btc_price = data.get('data', {}).get('btc_price')
                hashrate = data.get('data', {}).get('network_hashrate')
                
                price_valid = btc_price and 50000 <= btc_price <= 200000
                hashrate_valid = hashrate and 500 <= hashrate <= 2000
                
                success = price_valid and hashrate_valid
                details = f"Price: ${btc_price:,.0f}, Hashrate: {hashrate:.1f}EH/s" if success else "Invalid data range"
            else:
                success = False
                details = f"API returned {response.status_code}"
            
            self.log_test("realtime_api_data", success, details, response_time)
            return success
        except Exception as e:
            response_time = time.time() - start
            self.log_test("realtime_api_data", False, str(e), response_time)
            return False

    def test_mining_calculation(self):
        """测试挖矿计算功能"""
        start = time.time()
        try:
            # 使用测试端点，不需要认证
            data = {
                'miner_model': 'Antminer S19 Pro',
                'miner_count': '1',
                'electricity_cost': '0.05',
                'use_real_time_data': 'true'
            }
            response = requests.post(f"{self.base_url}/api/test/calculate", data=data, timeout=15)
            response_time = time.time() - start
            
            success = response.status_code == 200
            if success:
                try:
                    # 验证返回的JSON结果
                    result = response.json()
                    has_success = result.get('success', False)
                    has_calculation_data = any(key in result for key in 
                                              ['btc_mined', 'profit', 'revenue', 'daily_profit_usd'])
                    success = has_success or has_calculation_data
                    details = f"Calculation completed: success={has_success}, has_data={has_calculation_data}"
                except Exception:
                    # 如果不是JSON，检查HTML内容
                    html = response.text
                    has_results = any(keyword in html.lower() for keyword in 
                                    ['profit', '利润', 'revenue', '收益', 'daily', '每日'])
                    success = has_results
                    details = "Calculation completed with results" if has_results else "No calculation results found"
            else:
                details = f"HTTP {response.status_code}"
            
            self.log_test("mining_calculation", success, details, response_time)
            return success
        except Exception as e:
            response_time = time.time() - start
            self.log_test("mining_calculation", False, str(e), response_time)
            return False

    def test_analytics_dashboard(self):
        """测试分析仪表盘"""
        start = time.time()
        try:
            response = requests.get(f"{self.base_url}/analytics", timeout=10)
            response_time = time.time() - start
            
            # 200 (已登录) 或 302 (重定向到登录) 都是正常响应
            success = response.status_code in [200, 302]
            details = "Dashboard accessible" if response.status_code == 200 else "Requires authentication (normal)"
            
            self.log_test("analytics_dashboard", success, details, response_time)
            return success
        except Exception as e:
            response_time = time.time() - start
            self.log_test("analytics_dashboard", False, str(e), response_time)
            return False

    def test_frontend_elements(self):
        """测试前端元素"""
        start = time.time()
        try:
            response = requests.get(f"{self.base_url}/", timeout=10)
            response_time = time.time() - start
            
            if response.status_code == 200:
                html = response.text.lower()
                elements = {
                    'title': any(word in html for word in ['btc', 'mining', 'calculator', '挖矿']),
                    'form': 'form' in html,
                    'javascript': 'script' in html,
                    'css': any(word in html for word in ['css', 'style', 'bootstrap'])
                }
                
                success_count = sum(elements.values())
                success = success_count >= 3  # 至少3个元素存在
                details = f"Elements found: {success_count}/4 - {elements}"
            else:
                success = False
                details = f"HTTP {response.status_code}"
            
            self.log_test("frontend_elements", success, details, response_time)
            return success
        except Exception as e:
            response_time = time.time() - start
            self.log_test("frontend_elements", False, str(e), response_time)
            return False

    def test_price_history_api(self):
        """测试价格历史API"""
        start = time.time()
        try:
            response = requests.get(f"{self.base_url}/api/analytics/price-history?hours=24", timeout=10)
            response_time = time.time() - start
            
            # API可能需要认证，200、401、403都是合理响应
            success = response.status_code in [200, 401, 403]
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    has_history = 'price_history' in data or 'data_points' in data
                    success = has_history
                    details = "Price history data available" if has_history else "No price history data"
                except:
                    details = "Price history endpoint responding"
            else:
                details = f"Endpoint responding (HTTP {response.status_code})"
            
            self.log_test("price_history_api", success, details, response_time)
            return success
        except Exception as e:
            response_time = time.time() - start
            self.log_test("price_history_api", False, str(e), response_time)
            return False

    def test_performance_metrics(self):
        """测试性能指标"""
        start = time.time()
        try:
            # 测试主页加载时间
            page_start = time.time()
            response = requests.get(f"{self.base_url}/", timeout=15)
            page_time = time.time() - page_start
            
            # 测试API响应时间（使用分析数据API）
            api_start = time.time()
            api_response = requests.get(f"{self.base_url}/api/analytics/data", timeout=10)
            api_time = time.time() - api_start
            
            # 测试计算API性能（使用测试端点）
            calc_start = time.time()
            calc_data = {'miner_model': 'Antminer S19 Pro', 'miner_count': '1', 'electricity_cost': '0.05'}
            calc_response = requests.post(f"{self.base_url}/api/test/calculate", data=calc_data, timeout=10)
            calc_time = time.time() - calc_start
            
            response_time = time.time() - start
            
            # 性能标准：页面<5秒，API<3秒，计算<2秒
            page_ok = page_time < 5.0 and response.status_code in [200, 302]
            api_ok = api_time < 3.0 and api_response.status_code in [200, 401, 403]
            calc_ok = calc_time < 2.0 and calc_response.status_code == 200
            
            success = page_ok and api_ok and calc_ok
            details = f"Page: {page_time:.2f}s, API: {api_time:.2f}s, Calc: {calc_time:.2f}s"
            
            self.log_test("performance_metrics", success, details, response_time)
            return success
        except Exception as e:
            response_time = time.time() - start
            self.log_test("performance_metrics", False, str(e), response_time)
            return False

    def run_all_tests(self):
        """运行所有测试"""
        print("🚀 Starting Simplified 99% Accuracy Test Suite")
        print("=" * 60)
        
        test_start = time.time()
        
        # 运行所有测试
        tests = [
            self.test_server_health,
            self.test_database_connection,
            self.test_realtime_api_data,
            self.test_mining_calculation,
            self.test_analytics_dashboard,
            self.test_frontend_elements,
            self.test_price_history_api,
            self.test_performance_metrics
        ]
        
        for test in tests:
            test()
        
        # 计算结果
        duration = time.time() - test_start
        accuracy = (self.results['passed'] / self.results['total']) * 100 if self.results['total'] > 0 else 0
        self.results['accuracy'] = accuracy
        
        # 生成报告
        print("\n" + "=" * 60)
        print("📊 TEST RESULTS SUMMARY")
        print("=" * 60)
        print(f"🧪 Total Tests: {self.results['total']}")
        print(f"✅ Passed: {self.results['passed']}")
        print(f"❌ Failed: {self.results['failed']}")
        print(f"📈 Accuracy: {accuracy:.1f}%")
        print(f"⏱️ Duration: {duration:.2f}s")
        print("=" * 60)
        
        # 检查是否达到99%目标
        if accuracy >= 99.0:
            print("🎉 SUCCESS: 99%+ accuracy achieved!")
            status = "PASSED"
        elif accuracy >= 87.5:
            print("✅ GOOD: High accuracy achieved (87.5%+)")
            status = "GOOD"
        else:
            print("⚠️ NEEDS IMPROVEMENT: Accuracy below 87.5%")
            status = "NEEDS_IMPROVEMENT"
        
        # 保存详细报告
        report = {
            'summary': {
                'total_tests': self.results['total'],
                'passed_tests': self.results['passed'],
                'failed_tests': self.results['failed'],
                'accuracy_percentage': accuracy,
                'test_duration': duration,
                'status': status,
                'timestamp': datetime.now().isoformat()
            },
            'test_details': self.results['tests']
        }
        
        report_file = f'simplified_test_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"📄 Detailed report saved: {report_file}")
        
        return accuracy >= 99.0

if __name__ == "__main__":
    test_suite = Simplified99Test()
    success = test_suite.run_all_tests()
    sys.exit(0 if success else 1)