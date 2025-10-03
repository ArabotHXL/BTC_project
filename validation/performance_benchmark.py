"""
HashInsight Enterprise - Performance Benchmark
性能基准测试
"""

import time
import statistics
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


class PerformanceBenchmark:
    """性能基准测试"""
    
    # 性能目标
    TARGETS = {
        'api_latency_p95': 250,  # ms
        'batch_import_5000': 20,  # seconds
        'concurrent_users': 100,
        'database_query_p95': 100,  # ms
        'heatmap_generation': 2000  # ms
    }
    
    def __init__(self):
        """初始化基准测试"""
        self.results = {}
    
    def benchmark_api_latency(self, endpoint_func, iterations: int = 100) -> Dict:
        """API延迟基准测试"""
        latencies = []
        
        for _ in range(iterations):
            start = time.time()
            endpoint_func()
            latency = (time.time() - start) * 1000  # ms
            latencies.append(latency)
        
        p50 = statistics.median(latencies)
        p95 = sorted(latencies)[int(len(latencies) * 0.95)]
        p99 = sorted(latencies)[int(len(latencies) * 0.99)]
        
        passed = p95 <= self.TARGETS['api_latency_p95']
        
        return {
            'test': 'API Latency',
            'iterations': iterations,
            'p50': round(p50, 2),
            'p95': round(p95, 2),
            'p99': round(p99, 2),
            'avg': round(statistics.mean(latencies), 2),
            'target': self.TARGETS['api_latency_p95'],
            'passed': passed
        }
    
    def benchmark_batch_import(self, import_func, row_count: int = 5000) -> Dict:
        """批量导入基准测试"""
        start = time.time()
        result = import_func(row_count)
        elapsed = time.time() - start
        
        rows_per_second = row_count / elapsed
        passed = elapsed <= self.TARGETS['batch_import_5000']
        
        return {
            'test': 'Batch Import',
            'row_count': row_count,
            'elapsed_seconds': round(elapsed, 2),
            'rows_per_second': round(rows_per_second, 2),
            'target_seconds': self.TARGETS['batch_import_5000'],
            'passed': passed
        }
    
    def benchmark_concurrent_load(self, endpoint_func, concurrent: int = 100) -> Dict:
        """并发负载基准测试"""
        import concurrent.futures
        
        start = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent) as executor:
            futures = [executor.submit(endpoint_func) for _ in range(concurrent)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        elapsed = time.time() - start
        requests_per_second = concurrent / elapsed
        
        passed = len([r for r in results if r.get('success')]) == concurrent
        
        return {
            'test': 'Concurrent Load',
            'concurrent_users': concurrent,
            'total_requests': concurrent,
            'elapsed_seconds': round(elapsed, 2),
            'requests_per_second': round(requests_per_second, 2),
            'success_rate': (len([r for r in results if r.get('success')]) / concurrent) * 100,
            'passed': passed
        }
    
    def run_all_benchmarks(self) -> Dict:
        """运行所有基准测试"""
        # 这里应该调用实际的测试函数
        # 示例：
        # self.results['api_latency'] = self.benchmark_api_latency(some_api_func)
        # self.results['batch_import'] = self.benchmark_batch_import(import_func)
        
        return {
            'timestamp': time.time(),
            'results': self.results,
            'overall_passed': all(r.get('passed', False) for r in self.results.values())
        }
    
    def generate_html_report(self, output_file: str = 'benchmark_report.html'):
        """生成HTML报告"""
        summary = self.run_all_benchmarks()
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Performance Benchmark Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .passed {{ color: green; }}
        .failed {{ color: red; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #4CAF50; color: white; }}
    </style>
</head>
<body>
    <h1>HashInsight Performance Benchmark Report</h1>
    <p>Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}</p>
    
    <h2>Summary</h2>
    <p class="{'passed' if summary['overall_passed'] else 'failed'}">
        Overall Status: {'PASSED' if summary['overall_passed'] else 'FAILED'}
    </p>
    
    <h2>Benchmark Results</h2>
    <table>
        <tr>
            <th>Test</th>
            <th>Metric</th>
            <th>Result</th>
            <th>Target</th>
            <th>Status</th>
        </tr>
"""
        
        for test_name, result in self.results.items():
            status_class = 'passed' if result.get('passed') else 'failed'
            status_text = 'PASSED' if result.get('passed') else 'FAILED'
            
            html += f"""
        <tr>
            <td>{result.get('test', test_name)}</td>
            <td>P95 Latency / Duration</td>
            <td>{result.get('p95', result.get('elapsed_seconds', 'N/A'))}</td>
            <td>{result.get('target', 'N/A')}</td>
            <td class="{status_class}">{status_text}</td>
        </tr>
"""
        
        html += """
    </table>
</body>
</html>
"""
        
        with open(output_file, 'w') as f:
            f.write(html)
        
        return output_file
