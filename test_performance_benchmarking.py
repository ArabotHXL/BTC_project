#!/usr/bin/env python3
"""
性能基准测试系统
Performance Benchmarking System

专门测试系统性能和响应时间，确保缓存优化效果
Tests system performance and response times to verify cache optimization effectiveness
"""

import requests
import time
import json
import logging
import statistics
from datetime import datetime
from typing import Dict, List, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

logging.basicConfig(level=logging.INFO)

class PerformanceBenchmarker:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.session = requests.Session()
        
    def benchmark_api_endpoint(self, endpoint: str, iterations: int = 20) -> Dict[str, Any]:
        """对单个API端点进行性能基准测试"""
        logging.info(f"🚀 基准测试: {endpoint} ({iterations}次)")
        
        response_times = []
        success_count = 0
        errors = []
        
        for i in range(iterations):
            try:
                start_time = time.time()
                response = self.session.get(f"{self.base_url}{endpoint}", timeout=10)
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    response_times.append(response_time)
                    success_count += 1
                else:
                    errors.append(f"Iteration {i+1}: HTTP {response.status_code}")
                    
                # 短暂延迟避免过度请求
                time.sleep(0.1)
                
            except Exception as e:
                errors.append(f"Iteration {i+1}: {str(e)}")
        
        if not response_times:
            return {
                'success': False,
                'error': 'No successful responses',
                'errors': errors
            }
        
        # 计算性能统计
        stats = {
            'success': True,
            'endpoint': endpoint,
            'total_requests': iterations,
            'successful_requests': success_count,
            'success_rate': (success_count / iterations) * 100,
            'avg_response_time': statistics.mean(response_times),
            'min_response_time': min(response_times),
            'max_response_time': max(response_times),
            'median_response_time': statistics.median(response_times),
            'p95_response_time': self.percentile(response_times, 95),
            'p99_response_time': self.percentile(response_times, 99),
            'std_deviation': statistics.stdev(response_times) if len(response_times) > 1 else 0,
            'errors': errors
        }
        
        return stats
    
    def percentile(self, data: List[float], percentile: int) -> float:
        """计算百分位数"""
        sorted_data = sorted(data)
        index = (percentile / 100) * (len(sorted_data) - 1)
        
        if index.is_integer():
            return sorted_data[int(index)]
        else:
            lower = sorted_data[int(index)]
            upper = sorted_data[int(index) + 1]
            return lower + (upper - lower) * (index - int(index))
    
    def test_cache_effectiveness(self, endpoint: str) -> Dict[str, Any]:
        """测试缓存效果"""
        logging.info(f"🧪 测试缓存效果: {endpoint}")
        
        # 清除缓存的方法：等待缓存过期或重启
        # 第一次请求（缓存未命中）
        cache_miss_times = []
        for _ in range(3):
            start = time.time()
            response = self.session.get(f"{self.base_url}{endpoint}")
            cache_miss_times.append(time.time() - start)
            time.sleep(1)  # 确保缓存生效
        
        # 连续请求（缓存命中）
        cache_hit_times = []
        for _ in range(10):
            start = time.time()
            response = self.session.get(f"{self.base_url}{endpoint}")
            cache_hit_times.append(time.time() - start)
            time.sleep(0.1)
        
        avg_miss_time = statistics.mean(cache_miss_times)
        avg_hit_time = statistics.mean(cache_hit_times)
        improvement = ((avg_miss_time - avg_hit_time) / avg_miss_time) * 100 if avg_miss_time > 0 else 0
        
        return {
            'endpoint': endpoint,
            'avg_cache_miss_time': avg_miss_time,
            'avg_cache_hit_time': avg_hit_time,
            'performance_improvement': improvement,
            'cache_effective': improvement > 10  # 至少10%改善
        }
    
    def concurrent_load_test(self, endpoint: str, concurrent_users: int = 10, requests_per_user: int = 5) -> Dict[str, Any]:
        """并发负载测试"""
        logging.info(f"⚡ 并发负载测试: {endpoint} ({concurrent_users}用户, {requests_per_user}请求/用户)")
        
        def user_requests(user_id: int) -> List[float]:
            user_times = []
            for _ in range(requests_per_user):
                try:
                    start = time.time()
                    response = self.session.get(f"{self.base_url}{endpoint}", timeout=15)
                    user_times.append(time.time() - start)
                except:
                    pass
            return user_times
        
        all_response_times = []
        
        with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            futures = [executor.submit(user_requests, i) for i in range(concurrent_users)]
            
            for future in as_completed(futures):
                user_times = future.result()
                all_response_times.extend(user_times)
        
        if not all_response_times:
            return {'success': False, 'error': 'No successful responses under load'}
        
        return {
            'success': True,
            'endpoint': endpoint,
            'concurrent_users': concurrent_users,
            'total_requests': len(all_response_times),
            'avg_response_time': statistics.mean(all_response_times),
            'max_response_time': max(all_response_times),
            'min_response_time': min(all_response_times),
            'p95_response_time': self.percentile(all_response_times, 95),
            'requests_per_second': len(all_response_times) / max(all_response_times) if all_response_times else 0
        }
    
    def run_comprehensive_benchmark(self) -> Dict[str, Any]:
        """运行全面的性能基准测试"""
        logging.info("🎯 开始全面性能基准测试...")
        
        # 关键API端点
        api_endpoints = [
            '/api/network-data',
            '/api/get-btc-price', 
            '/api/get_miners_data',
            '/api/analytics/data'
        ]
        
        # 关键页面端点
        page_endpoints = [
            '/',
            '/dashboard',
            '/calculator',
            '/analytics'
        ]
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'test_type': 'Comprehensive Performance Benchmark',
            'api_benchmarks': {},
            'page_benchmarks': {},
            'cache_tests': {},
            'load_tests': {},
            'summary': {}
        }
        
        # API性能基准测试
        logging.info("\n📊 API端点性能基准测试")
        api_performance_scores = []
        
        for endpoint in api_endpoints:
            benchmark = self.benchmark_api_endpoint(endpoint, 15)
            results['api_benchmarks'][endpoint] = benchmark
            
            if benchmark['success']:
                # 评分：平均响应时间 < 1s = 100分，每增加0.1s减10分
                score = max(0, 100 - (benchmark['avg_response_time'] - 1.0) * 100)
                api_performance_scores.append(score)
                
                logging.info(f"  {endpoint}: {benchmark['avg_response_time']:.3f}s "
                           f"(成功率: {benchmark['success_rate']:.1f}%)")
        
        # 页面性能基准测试
        logging.info("\n🌐 页面端点性能基准测试")
        page_performance_scores = []
        
        for endpoint in page_endpoints:
            benchmark = self.benchmark_api_endpoint(endpoint, 10)
            results['page_benchmarks'][endpoint] = benchmark
            
            if benchmark['success']:
                # 页面响应时间要求稍宽松：< 2s = 100分
                score = max(0, 100 - (benchmark['avg_response_time'] - 2.0) * 50)
                page_performance_scores.append(score)
                
                logging.info(f"  {endpoint}: {benchmark['avg_response_time']:.3f}s "
                           f"(成功率: {benchmark['success_rate']:.1f}%)")
        
        # 缓存效果测试
        logging.info("\n💾 缓存效果测试")
        cache_scores = []
        
        for endpoint in api_endpoints:
            cache_test = self.test_cache_effectiveness(endpoint)
            results['cache_tests'][endpoint] = cache_test
            
            if cache_test['cache_effective']:
                cache_scores.append(100)
                logging.info(f"  {endpoint}: 缓存改善 {cache_test['performance_improvement']:.1f}%")
            else:
                cache_scores.append(50)
                logging.info(f"  {endpoint}: 缓存效果不明显")
        
        # 负载测试
        logging.info("\n⚡ 并发负载测试")
        load_scores = []
        
        for endpoint in ['/api/network-data', '/dashboard']:
            load_test = self.concurrent_load_test(endpoint, 5, 3)
            results['load_tests'][endpoint] = load_test
            
            if load_test['success']:
                # 负载下平均响应时间 < 3s = 100分
                score = max(0, 100 - (load_test['avg_response_time'] - 3.0) * 33)
                load_scores.append(score)
                
                logging.info(f"  {endpoint}: 负载下 {load_test['avg_response_time']:.3f}s "
                           f"({load_test['concurrent_users']}并发用户)")
        
        # 计算综合性能分数
        all_scores = api_performance_scores + page_performance_scores + cache_scores + load_scores
        overall_performance = statistics.mean(all_scores) if all_scores else 0
        
        results['summary'] = {
            'overall_performance_score': overall_performance,
            'api_performance_avg': statistics.mean(api_performance_scores) if api_performance_scores else 0,
            'page_performance_avg': statistics.mean(page_performance_scores) if page_performance_scores else 0,
            'cache_effectiveness_avg': statistics.mean(cache_scores) if cache_scores else 0,
            'load_performance_avg': statistics.mean(load_scores) if load_scores else 0,
            'meets_performance_target': overall_performance >= 85  # 85分以上认为性能良好
        }
        
        # 输出摘要
        logging.info(f"\n🏆 性能基准测试摘要:")
        logging.info(f"   整体性能分数: {overall_performance:.1f}/100")
        logging.info(f"   API性能平均: {results['summary']['api_performance_avg']:.1f}/100")
        logging.info(f"   页面性能平均: {results['summary']['page_performance_avg']:.1f}/100")
        logging.info(f"   缓存效果平均: {results['summary']['cache_effectiveness_avg']:.1f}/100")
        logging.info(f"   负载性能平均: {results['summary']['load_performance_avg']:.1f}/100")
        logging.info(f"   性能目标达成: {'✅ 是' if results['summary']['meets_performance_target'] else '❌ 否'}")
        
        return results

def main():
    """主函数"""
    benchmarker = PerformanceBenchmarker()
    
    try:
        results = benchmarker.run_comprehensive_benchmark()
        
        # 保存结果
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"performance_benchmark_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        logging.info(f"\n💾 性能基准测试结果已保存到: {filename}")
        
        if results['summary']['meets_performance_target']:
            logging.info("🎉 性能基准测试通过！")
            return 0
        else:
            logging.warning("⚠️ 性能基准测试未完全达标")
            return 1
            
    except Exception as e:
        logging.error(f"💥 基准测试过程中发生错误: {e}")
        return 2

if __name__ == "__main__":
    exit(main())