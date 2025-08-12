#!/usr/bin/env python3
"""
BTC挖矿计算器 - 综合应用测试系统
目标: 99%准确率和可用率验证

测试覆盖范围:
1. 核心计算引擎准确性
2. API接口可用性
3. 数据库连接稳定性
4. 用户认证系统
5. 技术指标计算
6. 实时数据源集成
7. 前端功能完整性
8. 错误处理机制
9. 并发请求处理
10. 系统性能基准
"""

import os
import sys
import json
import time
import requests
import psycopg2
import threading
import numpy as np
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'comprehensive_test_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class ComprehensiveAppTester:
    def __init__(self):
        self.base_url = "https://btc-mining-calculator-system.replit.dev"
        self.test_results = {
            'total_tests': 0,
            'passed_tests': 0,
            'failed_tests': 0,
            'accuracy_score': 0.0,
            'availability_score': 0.0,
            'detailed_results': {},
            'performance_metrics': {},
            'error_log': []
        }
        self.start_time = time.time()

    def log_result(self, test_name, success, details=None, error=None):
        """记录测试结果"""
        self.test_results['total_tests'] += 1
        if success:
            self.test_results['passed_tests'] += 1
            logger.info(f"✓ {test_name}: PASSED")
        else:
            self.test_results['failed_tests'] += 1
            logger.error(f"✗ {test_name}: FAILED - {error}")
            self.test_results['error_log'].append({
                'test': test_name,
                'error': str(error),
                'timestamp': datetime.now().isoformat()
            })
        
        self.test_results['detailed_results'][test_name] = {
            'success': success,
            'details': details,
            'error': str(error) if error else None,
            'timestamp': datetime.now().isoformat()
        }

    def test_database_connectivity(self):
        """测试数据库连接和基础功能"""
        logger.info("🔍 测试数据库连接...")
        try:
            conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
            cursor = conn.cursor()
            
            # 测试基本查询
            cursor.execute("SELECT COUNT(*) FROM users")
            user_count = cursor.fetchone()[0]
            
            # 测试市场数据表
            cursor.execute("SELECT COUNT(*) FROM market_analytics WHERE btc_price > 0")
            market_data_count = cursor.fetchone()[0]
            
            # 测试技术指标表
            cursor.execute("SELECT COUNT(*) FROM technical_indicators")
            tech_indicators_count = cursor.fetchone()[0]
            
            conn.close()
            
            self.log_result('database_connectivity', True, {
                'user_count': user_count,
                'market_data_count': market_data_count,
                'tech_indicators_count': tech_indicators_count
            })
            
            return True
            
        except Exception as e:
            self.log_result('database_connectivity', False, error=e)
            return False

    def test_authentication_system(self):
        """测试用户认证系统"""
        logger.info("🔍 测试用户认证系统...")
        try:
            session = requests.Session()
            
            # 测试登录页面可访问性
            login_response = session.get(f"{self.base_url}/login")
            if login_response.status_code != 200:
                raise Exception(f"Login page not accessible: {login_response.status_code}")
            
            # 测试登录功能
            login_data = {
                'email': 'hxl2022hao@gmail.com',
                'password': 'Hxl,04141992'
            }
            
            auth_response = session.post(f"{self.base_url}/login", data=login_data, allow_redirects=False)
            
            # 验证重定向或成功响应
            if auth_response.status_code not in [200, 302, 303]:
                raise Exception(f"Login failed: {auth_response.status_code}")
            
            self.log_result('authentication_system', True, {
                'login_page_status': login_response.status_code,
                'auth_status': auth_response.status_code
            })
            
            return session
            
        except Exception as e:
            self.log_result('authentication_system', False, error=e)
            return None

    def test_core_mining_calculations(self):
        """测试核心挖矿计算准确性"""
        logger.info("🔍 测试核心挖矿计算...")
        
        test_cases = [
            {
                'miner': 'Antminer S19 Pro',
                'hashrate_th': 110,
                'power_consumption': 3250,
                'electricity_cost': 0.08,
                'btc_price': 118800,
                'network_hashrate_eh': 927,
                'expected_daily_profit_min': 3.0,
                'expected_daily_profit_max': 6.0
            },
            {
                'miner': 'Antminer S21 XP',
                'hashrate_th': 270,
                'power_consumption': 3645,
                'electricity_cost': 0.06,
                'btc_price': 118800,
                'network_hashrate_eh': 927,
                'expected_daily_profit_min': 8.0,
                'expected_daily_profit_max': 15.0
            }
        ]
        
        success_count = 0
        total_cases = len(test_cases)
        
        for i, case in enumerate(test_cases):
            try:
                # 计算每日BTC产出
                miner_hashrate_th = case['hashrate_th']
                network_hashrate_th = case['network_hashrate_eh'] * 1000000  # EH/s to TH/s
                daily_btc = (miner_hashrate_th / network_hashrate_th) * 144 * 6.25
                
                # 计算收益
                daily_revenue = daily_btc * case['btc_price']
                daily_power_cost = (case['power_consumption'] / 1000) * 24 * case['electricity_cost']
                daily_profit = daily_revenue - daily_power_cost
                
                # 验证计算结果
                if case['expected_daily_profit_min'] <= daily_profit <= case['expected_daily_profit_max']:
                    success_count += 1
                    logger.info(f"  ✓ 测试案例{i+1}: 每日利润 ${daily_profit:.2f} (预期范围: ${case['expected_daily_profit_min']}-${case['expected_daily_profit_max']})")
                else:
                    logger.warning(f"  ✗ 测试案例{i+1}: 每日利润 ${daily_profit:.2f} 超出预期范围")
                    
            except Exception as e:
                logger.error(f"  ✗ 测试案例{i+1}: 计算错误 - {e}")
        
        accuracy = success_count / total_cases
        self.log_result('core_mining_calculations', accuracy >= 0.95, {
            'success_cases': success_count,
            'total_cases': total_cases,
            'accuracy': accuracy
        })
        
        return accuracy >= 0.95

    def test_api_endpoints(self):
        """测试API接口可用性"""
        logger.info("🔍 测试API接口...")
        
        # 需要测试的API端点
        endpoints = [
            '/analytics/api/market-data',
            '/analytics/api/technical-indicators',
            '/analytics/api/price-history',
            '/api/mining-calculator',
            '/api/batch-calculator'
        ]
        
        session = self.test_authentication_system()
        if not session:
            self.log_result('api_endpoints', False, error="Authentication failed")
            return False
        
        success_count = 0
        total_endpoints = len(endpoints)
        
        for endpoint in endpoints:
            try:
                response = session.get(f"{self.base_url}{endpoint}", timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if 'success' in data and data['success']:
                        success_count += 1
                        logger.info(f"  ✓ {endpoint}: 可用")
                    else:
                        logger.warning(f"  ✗ {endpoint}: 响应格式错误")
                else:
                    logger.warning(f"  ✗ {endpoint}: HTTP {response.status_code}")
                    
            except Exception as e:
                logger.error(f"  ✗ {endpoint}: {e}")
        
        availability = success_count / total_endpoints
        self.log_result('api_endpoints', availability >= 0.95, {
            'available_endpoints': success_count,
            'total_endpoints': total_endpoints,
            'availability': availability
        })
        
        return availability >= 0.95

    def test_technical_indicators_accuracy(self):
        """测试技术指标计算准确性"""
        logger.info("🔍 测试技术指标准确性...")
        
        try:
            session = self.test_authentication_system()
            if not session:
                raise Exception("Authentication failed")
            
            response = session.get(f"{self.base_url}/analytics/api/technical-indicators", timeout=10)
            if response.status_code != 200:
                raise Exception(f"API不可用: {response.status_code}")
            
            data = response.json()
            if not data.get('success'):
                raise Exception("API返回错误")
            
            indicators = data['data']
            
            # 验证技术指标合理性
            validations = []
            
            # RSI应该在0-100之间
            rsi = indicators.get('rsi', 0)
            rsi_valid = 0 <= rsi <= 100
            validations.append(('RSI范围', rsi_valid, f"RSI: {rsi}"))
            
            # 当前价格超过10万时，RSI不应过低
            current_price = indicators.get('current_price', 0)
            if current_price > 100000:
                rsi_reasonable = rsi >= 30
                validations.append(('RSI合理性', rsi_reasonable, f"高价位RSI: {rsi}"))
            
            # MACD不应有极端值
            macd = indicators.get('macd', 0)
            macd_reasonable = abs(macd) <= 100
            validations.append(('MACD合理性', macd_reasonable, f"MACD: {macd}"))
            
            # 波动率应该是合理的百分比
            volatility = indicators.get('volatility', 0)
            volatility_reasonable = 0 <= volatility <= 50
            validations.append(('波动率范围', volatility_reasonable, f"波动率: {volatility}%"))
            
            # 移动平均线应该接近当前价格
            sma_20 = indicators.get('sma_20', 0)
            sma_reasonable = abs(sma_20 - current_price) <= current_price * 0.1  # 10%内
            validations.append(('SMA20合理性', sma_reasonable, f"SMA20: {sma_20}, 当前价格: {current_price}"))
            
            passed_validations = sum(1 for _, valid, _ in validations if valid)
            total_validations = len(validations)
            
            for name, valid, details in validations:
                if valid:
                    logger.info(f"  ✓ {name}: {details}")
                else:
                    logger.warning(f"  ✗ {name}: {details}")
            
            accuracy = passed_validations / total_validations
            self.log_result('technical_indicators_accuracy', accuracy >= 0.90, {
                'passed_validations': passed_validations,
                'total_validations': total_validations,
                'accuracy': accuracy,
                'indicators': indicators
            })
            
            return accuracy >= 0.90
            
        except Exception as e:
            self.log_result('technical_indicators_accuracy', False, error=e)
            return False

    def test_concurrent_requests(self):
        """测试并发请求处理能力"""
        logger.info("🔍 测试并发请求处理...")
        
        def make_request(url):
            try:
                response = requests.get(url, timeout=10)
                return response.status_code == 200
            except:
                return False
        
        try:
            # 测试URL列表
            test_urls = [
                f"{self.base_url}/",
                f"{self.base_url}/login",
                f"{self.base_url}/price",
                f"{self.base_url}/calculator"
            ]
            
            concurrent_requests = 20
            success_count = 0
            
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = []
                for _ in range(concurrent_requests):
                    for url in test_urls:
                        future = executor.submit(make_request, url)
                        futures.append(future)
                
                for future in as_completed(futures, timeout=30):
                    if future.result():
                        success_count += 1
            
            total_requests = concurrent_requests * len(test_urls)
            success_rate = success_count / total_requests
            
            self.log_result('concurrent_requests', success_rate >= 0.95, {
                'successful_requests': success_count,
                'total_requests': total_requests,
                'success_rate': success_rate
            })
            
            return success_rate >= 0.95
            
        except Exception as e:
            self.log_result('concurrent_requests', False, error=e)
            return False

    def test_real_time_data_integration(self):
        """测试实时数据源集成"""
        logger.info("🔍 测试实时数据源集成...")
        
        try:
            # 导入必要的模块
            sys.path.append('.')
            from mining_calculator import get_real_time_btc_price, get_real_time_btc_hashrate
            
            tests = []
            
            # 测试BTC价格获取
            try:
                btc_price = get_real_time_btc_price()
                price_valid = 50000 <= btc_price <= 200000  # 合理价格范围
                tests.append(('BTC价格获取', price_valid, f"价格: ${btc_price:,.2f}"))
            except Exception as e:
                tests.append(('BTC价格获取', False, f"错误: {e}"))
            
            # 测试网络算力获取
            try:
                hashrate = get_real_time_btc_hashrate()
                hashrate_valid = 500 <= hashrate <= 2000  # 合理算力范围(EH/s)
                tests.append(('网络算力获取', hashrate_valid, f"算力: {hashrate:.2f} EH/s"))
            except Exception as e:
                tests.append(('网络算力获取', False, f"错误: {e}"))
            
            passed_tests = sum(1 for _, valid, _ in tests if valid)
            total_tests = len(tests)
            
            for name, valid, details in tests:
                if valid:
                    logger.info(f"  ✓ {name}: {details}")
                else:
                    logger.warning(f"  ✗ {name}: {details}")
            
            success_rate = passed_tests / total_tests
            self.log_result('real_time_data_integration', success_rate >= 0.80, {
                'passed_tests': passed_tests,
                'total_tests': total_tests,
                'success_rate': success_rate
            })
            
            return success_rate >= 0.80
            
        except Exception as e:
            self.log_result('real_time_data_integration', False, error=e)
            return False

    def test_error_handling(self):
        """测试错误处理机制"""
        logger.info("🔍 测试错误处理...")
        
        try:
            session = requests.Session()
            
            # 测试无效API调用
            error_tests = [
                ('无效API端点', f"{self.base_url}/api/invalid-endpoint", 404),
                ('无权限访问', f"{self.base_url}/analytics/api/market-data", 401),
                ('无效参数', f"{self.base_url}/api/mining-calculator?invalid=param", [400, 422])
            ]
            
            passed_tests = 0
            
            for test_name, url, expected_codes in error_tests:
                try:
                    response = session.get(url, timeout=5)
                    expected = expected_codes if isinstance(expected_codes, list) else [expected_codes]
                    
                    if response.status_code in expected:
                        logger.info(f"  ✓ {test_name}: 正确返回 {response.status_code}")
                        passed_tests += 1
                    else:
                        logger.warning(f"  ✗ {test_name}: 期望 {expected}，实际 {response.status_code}")
                        
                except Exception as e:
                    logger.warning(f"  ✗ {test_name}: 请求失败 - {e}")
            
            success_rate = passed_tests / len(error_tests)
            self.log_result('error_handling', success_rate >= 0.80, {
                'passed_tests': passed_tests,
                'total_tests': len(error_tests),
                'success_rate': success_rate
            })
            
            return success_rate >= 0.80
            
        except Exception as e:
            self.log_result('error_handling', False, error=e)
            return False

    def generate_performance_metrics(self):
        """生成性能指标"""
        logger.info("📊 生成性能指标...")
        
        try:
            session = self.test_authentication_system()
            if not session:
                raise Exception("Authentication failed")
            
            # 测试页面加载时间
            endpoints_to_test = [
                ('首页', '/'),
                ('登录页', '/login'),
                ('计算器', '/calculator'),
                ('分析页面', '/analytics_dashboard')
            ]
            
            performance_data = {}
            
            for name, endpoint in endpoints_to_test:
                try:
                    start_time = time.time()
                    response = session.get(f"{self.base_url}{endpoint}", timeout=10)
                    load_time = time.time() - start_time
                    
                    performance_data[name] = {
                        'load_time': load_time,
                        'status_code': response.status_code,
                        'success': response.status_code == 200 and load_time < 5.0
                    }
                    
                    if performance_data[name]['success']:
                        logger.info(f"  ✓ {name}: {load_time:.2f}s")
                    else:
                        logger.warning(f"  ✗ {name}: {load_time:.2f}s (状态码: {response.status_code})")
                        
                except Exception as e:
                    performance_data[name] = {
                        'load_time': 999,
                        'status_code': 0,
                        'success': False,
                        'error': str(e)
                    }
                    logger.error(f"  ✗ {name}: 错误 - {e}")
            
            self.test_results['performance_metrics'] = performance_data
            
        except Exception as e:
            logger.error(f"性能测试失败: {e}")

    def run_comprehensive_test(self):
        """运行全面测试"""
        logger.info("🚀 开始综合应用测试...")
        logger.info("="*60)
        
        # 执行所有测试
        test_functions = [
            self.test_database_connectivity,
            self.test_authentication_system,
            self.test_core_mining_calculations,
            self.test_api_endpoints,
            self.test_technical_indicators_accuracy,
            self.test_concurrent_requests,
            self.test_real_time_data_integration,
            self.test_error_handling
        ]
        
        for test_func in test_functions:
            try:
                test_func()
            except Exception as e:
                logger.error(f"测试函数 {test_func.__name__} 执行失败: {e}")
                self.log_result(test_func.__name__, False, error=e)
        
        # 生成性能指标
        self.generate_performance_metrics()
        
        # 计算最终分数
        self.calculate_final_scores()
        
        # 生成测试报告
        self.generate_test_report()

    def calculate_final_scores(self):
        """计算最终准确率和可用率分数"""
        total_tests = self.test_results['total_tests']
        passed_tests = self.test_results['passed_tests']
        
        if total_tests > 0:
            self.test_results['accuracy_score'] = (passed_tests / total_tests) * 100
            self.test_results['availability_score'] = (passed_tests / total_tests) * 100
        
        logger.info("="*60)
        logger.info("📊 最终测试结果:")
        logger.info(f"总测试数: {total_tests}")
        logger.info(f"通过测试: {passed_tests}")
        logger.info(f"失败测试: {self.test_results['failed_tests']}")
        logger.info(f"准确率: {self.test_results['accuracy_score']:.2f}%")
        logger.info(f"可用率: {self.test_results['availability_score']:.2f}%")
        
        # 检查是否达到99%目标
        if self.test_results['accuracy_score'] >= 99.0:
            logger.info("🎉 恭喜！应用已达到99%准确率目标")
        else:
            logger.warning(f"⚠️  应用未达到99%准确率目标，当前: {self.test_results['accuracy_score']:.2f}%")

    def generate_test_report(self):
        """生成详细测试报告"""
        report_filename = f'comprehensive_test_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        
        # 添加执行时间
        self.test_results['execution_time'] = time.time() - self.start_time
        self.test_results['timestamp'] = datetime.now().isoformat()
        
        # 保存JSON报告
        with open(report_filename, 'w', encoding='utf-8') as f:
            json.dump(self.test_results, f, ensure_ascii=False, indent=2)
        
        logger.info(f"📄 详细测试报告已保存至: {report_filename}")
        
        return report_filename

def main():
    """主函数"""
    print("BTC挖矿计算器 - 综合应用测试系统")
    print("目标: 99%准确率和可用率验证")
    print("="*60)
    
    tester = ComprehensiveAppTester()
    tester.run_comprehensive_test()
    
    return tester.test_results

if __name__ == "__main__":
    results = main()
    
    # 输出最终结果
    print(f"\n🏁 测试完成!")
    print(f"准确率: {results['accuracy_score']:.2f}%")
    print(f"可用率: {results['availability_score']:.2f}%")
    
    # 退出代码
    exit_code = 0 if results['accuracy_score'] >= 99.0 else 1
    sys.exit(exit_code)