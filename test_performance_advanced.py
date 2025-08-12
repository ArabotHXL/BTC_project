"""
高级性能测试 - Advanced Performance Testing
确保后端API和数据库查询的99%准确性
"""
import asyncio
import aiohttp
import time
import statistics
import logging
from concurrent.futures import ThreadPoolExecutor
import json
import requests
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AdvancedPerformanceTest:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.results = []
        
    def test_concurrent_calculations(self, num_requests=50):
        """并发计算测试"""
        logger.info(f"测试并发计算 - {num_requests} 个并发请求")
        
        calc_data = {
            'miner_model': 'Antminer S21',
            'miner_count': '1',
            'host_electricity_cost': '0.05',
            'client_electricity_cost': '0.08'
        }
        
        def single_request():
            start_time = time.time()
            try:
                response = self.session.post(f"{self.base_url}/calculate", data=calc_data)
                end_time = time.time()
                
                if response.status_code == 200:
                    data = response.json()
                    if 'host_profit' in data and 'client_profit' in data:
                        return {
                            'success': True,
                            'response_time': end_time - start_time,
                            'data_valid': True
                        }
                return {'success': False, 'response_time': end_time - start_time, 'data_valid': False}
            except Exception as e:
                end_time = time.time()
                return {'success': False, 'response_time': end_time - start_time, 'error': str(e)}
        
        # 执行并发测试
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(single_request) for _ in range(num_requests)]
            results = [future.result() for future in futures]
        
        # 分析结果
        success_count = sum(1 for r in results if r.get('success'))
        response_times = [r['response_time'] for r in results]
        
        accuracy = (success_count / num_requests) * 100
        avg_response_time = statistics.mean(response_times)
        max_response_time = max(response_times)
        
        logger.info(f"并发测试结果:")
        logger.info(f"  准确率: {accuracy:.1f}%")
        logger.info(f"  平均响应时间: {avg_response_time:.3f}s")
        logger.info(f"  最大响应时间: {max_response_time:.3f}s")
        
        return {
            'test': 'Concurrent Calculations',
            'accuracy': accuracy,
            'avg_response_time': avg_response_time,
            'max_response_time': max_response_time,
            'success_count': success_count,
            'total_requests': num_requests
        }
    
    def test_data_consistency(self):
        """数据一致性测试"""
        logger.info("测试数据一致性")
        
        # 多次请求相同数据，检查一致性
        calc_data = {
            'miner_model': 'Antminer S21',
            'miner_count': '1',
            'host_electricity_cost': '0.05',
            'client_electricity_cost': '0.08'
        }
        
        results = []
        for i in range(10):
            response = self.session.post(f"{self.base_url}/calculate", data=calc_data)
            if response.status_code == 200:
                data = response.json()
                results.append(data)
        
        # 检查结果一致性
        if len(results) > 0:
            first_result = results[0]
            consistent = all(
                r.get('host_profit') == first_result.get('host_profit') and
                r.get('client_profit') == first_result.get('client_profit')
                for r in results
            )
            
            accuracy = 100.0 if consistent else 0.0
            logger.info(f"数据一致性: {accuracy}%")
            
            return {
                'test': 'Data Consistency',
                'accuracy': accuracy,
                'consistent': consistent,
                'sample_count': len(results)
            }
        
        return {'test': 'Data Consistency', 'accuracy': 0.0, 'error': 'No valid responses'}
    
    def test_subscription_accuracy(self):
        """订阅系统准确性测试"""
        logger.info("测试订阅系统准确性")
        
        test_cases = [
            {'feature': 'batch-calculator', 'expected_restriction': True},
            {'feature': 'crm/dashboard', 'expected_restriction': True},
            {'feature': 'admin/user_access', 'expected_restriction': True}
        ]
        
        correct_restrictions = 0
        total_tests = len(test_cases)
        
        for test_case in test_cases:
            try:
                response = self.session.get(f"{self.base_url}/{test_case['feature']}")
                
                # 检查是否正确限制访问
                is_restricted = (
                    response.status_code == 402 or
                    'upgrade' in response.text.lower() or
                    'subscription' in response.text.lower()
                )
                
                if is_restricted == test_case['expected_restriction']:
                    correct_restrictions += 1
                    logger.info(f"✅ {test_case['feature']}: 正确限制")
                else:
                    logger.info(f"❌ {test_case['feature']}: 限制不正确")
                    
            except Exception as e:
                logger.error(f"测试 {test_case['feature']} 时出错: {e}")
        
        accuracy = (correct_restrictions / total_tests) * 100
        
        return {
            'test': 'Subscription System Accuracy',
            'accuracy': accuracy,
            'correct_restrictions': correct_restrictions,
            'total_tests': total_tests
        }
    
    def test_api_endpoint_accuracy(self):
        """API端点准确性测试"""
        logger.info("测试API端点准确性")
        
        endpoints = [
            {'url': '/health', 'expected_keys': ['status']},
            {'url': '/api/get_miners_data', 'expected_keys': ['success', 'miners']},
            {'url': '/api/network-stats', 'expected_keys': ['btc_price']}
        ]
        
        accurate_responses = 0
        total_endpoints = len(endpoints)
        
        for endpoint in endpoints:
            try:
                response = self.session.get(f"{self.base_url}{endpoint['url']}")
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # 检查响应是否包含预期的键
                    has_expected_keys = any(key in data for key in endpoint['expected_keys'])
                    
                    if has_expected_keys:
                        accurate_responses += 1
                        logger.info(f"✅ {endpoint['url']}: API响应准确")
                    else:
                        logger.info(f"❌ {endpoint['url']}: API响应缺少预期字段")
                else:
                    logger.info(f"❌ {endpoint['url']}: HTTP {response.status_code}")
                    
            except Exception as e:
                logger.error(f"测试 {endpoint['url']} 时出错: {e}")
        
        accuracy = (accurate_responses / total_endpoints) * 100
        
        return {
            'test': 'API Endpoint Accuracy',
            'accuracy': accuracy,
            'accurate_responses': accurate_responses,
            'total_endpoints': total_endpoints
        }
    
    def test_database_query_performance(self):
        """数据库查询性能测试"""
        logger.info("测试数据库查询性能")
        
        # 测试多个需要数据库查询的端点
        db_endpoints = [
            '/api/network-stats',
            '/health'
        ]
        
        performance_results = []
        
        for endpoint in db_endpoints:
            response_times = []
            success_count = 0
            
            for i in range(10):
                start_time = time.time()
                try:
                    response = self.session.get(f"{self.base_url}{endpoint}")
                    end_time = time.time()
                    
                    response_time = end_time - start_time
                    response_times.append(response_time)
                    
                    if response.status_code == 200:
                        success_count += 1
                        
                except Exception as e:
                    logger.error(f"查询 {endpoint} 时出错: {e}")
            
            if response_times:
                avg_time = statistics.mean(response_times)
                max_time = max(response_times)
                accuracy = (success_count / 10) * 100
                
                performance_results.append({
                    'endpoint': endpoint,
                    'avg_response_time': avg_time,
                    'max_response_time': max_time,
                    'accuracy': accuracy
                })
                
                logger.info(f"{endpoint}: 平均 {avg_time:.3f}s, 准确率 {accuracy}%")
        
        return {
            'test': 'Database Query Performance',
            'results': performance_results
        }
    
    def run_advanced_tests(self):
        """运行高级性能测试"""
        logger.info("开始高级性能测试...")
        
        all_results = []
        
        # 并发计算测试
        concurrent_result = self.test_concurrent_calculations()
        all_results.append(concurrent_result)
        
        # 数据一致性测试
        consistency_result = self.test_data_consistency()
        all_results.append(consistency_result)
        
        # 订阅系统准确性测试
        subscription_result = self.test_subscription_accuracy()
        all_results.append(subscription_result)
        
        # API端点准确性测试
        api_result = self.test_api_endpoint_accuracy()
        all_results.append(api_result)
        
        # 数据库查询性能测试
        db_result = self.test_database_query_performance()
        all_results.append(db_result)
        
        # 计算总体准确率
        accuracy_scores = [r.get('accuracy', 0) for r in all_results if 'accuracy' in r]
        overall_accuracy = statistics.mean(accuracy_scores) if accuracy_scores else 0
        
        # 生成报告
        report = {
            'timestamp': datetime.now().isoformat(),
            'overall_accuracy': overall_accuracy,
            'test_results': all_results
        }
        
        # 保存报告
        with open(f'performance_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json', 'w') as f:
            json.dump(report, f, indent=2)
        
        # 打印摘要
        print(f"\n{'='*60}")
        print(f"高级性能测试完成 - Advanced Performance Test Complete")
        print(f"{'='*60}")
        print(f"总体准确率 Overall Accuracy: {overall_accuracy:.1f}%")
        
        for result in all_results:
            if 'accuracy' in result:
                print(f"{result['test']}: {result['accuracy']:.1f}%")
        
        if overall_accuracy >= 99.0:
            print(f"✅ 性能测试通过！准确率达到99%以上")
        else:
            print(f"❌ 性能测试需要改进，准确率低于99%")
        
        print(f"{'='*60}")
        
        return overall_accuracy >= 99.0

def main():
    """主函数"""
    print("等待服务器启动...")
    time.sleep(5)
    
    test_suite = AdvancedPerformanceTest()
    success = test_suite.run_advanced_tests()
    
    return success

if __name__ == "__main__":
    main()