"""
测试请求合并（Request Coalescing）功能
Test Request Coalescing - 验证并发请求正确合并和结果共享
"""
import unittest
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cache_manager import request_coalescer, RequestCoalescer


class TestRequestCoalescing(unittest.TestCase):
    """测试请求合并功能"""
    
    def setUp(self):
        """每个测试前重置合并器"""
        self.coalescer = RequestCoalescer()
    
    def test_single_request(self):
        """测试单个请求正常执行"""
        call_count = [0]
        
        def expensive_operation():
            call_count[0] += 1
            time.sleep(0.1)
            return "result"
        
        result = self.coalescer.coalesce("test_key", expensive_operation)
        
        self.assertEqual(result, "result")
        self.assertEqual(call_count[0], 1)
    
    def test_concurrent_requests_coalescing(self):
        """测试并发请求正确合并 - 只执行一次"""
        call_count = [0]
        results = []
        
        def expensive_operation():
            call_count[0] += 1
            time.sleep(0.2)  # 模拟耗时操作
            return f"result_{call_count[0]}"
        
        # 启动10个并发请求
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            for i in range(10):
                future = executor.submit(
                    self.coalescer.coalesce,
                    "test_concurrent",
                    expensive_operation
                )
                futures.append(future)
            
            # 收集所有结果
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
        
        # 验证：只执行了一次（请求合并成功）
        self.assertEqual(call_count[0], 1, "应该只执行一次expensive_operation")
        
        # 验证：所有请求都得到了相同的结果
        self.assertEqual(len(results), 10, "应该有10个结果")
        self.assertTrue(all(r == results[0] for r in results), 
                       f"所有结果应该相同，但得到: {set(results)}")
        self.assertEqual(results[0], "result_1")
    
    def test_different_keys_execute_separately(self):
        """测试不同key的请求独立执行"""
        call_count = [0]
        
        def expensive_operation(value):
            call_count[0] += 1
            return f"result_{value}"
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            # 5个不同的key
            futures = []
            for i in range(5):
                future = executor.submit(
                    self.coalescer.coalesce,
                    f"key_{i}",
                    expensive_operation,
                    i
                )
                futures.append(future)
            
            results = [f.result() for f in futures]
        
        # 每个key都应该执行一次
        self.assertEqual(call_count[0], 5)
        self.assertEqual(len(set(results)), 5)  # 5个不同的结果
    
    def test_no_none_results_for_waiters(self):
        """
        测试等待者不会收到None结果
        这是修复的核心测试 - 验证bug已修复
        """
        results = []
        call_count = [0]
        
        def slow_operation():
            call_count[0] += 1
            time.sleep(0.3)
            return {"status": "success", "value": 42}
        
        def worker():
            result = self.coalescer.coalesce("shared_key", slow_operation)
            results.append(result)
        
        # 启动20个并发线程
        threads = []
        for _ in range(20):
            t = threading.Thread(target=worker)
            threads.append(t)
        
        # 同时启动所有线程
        for t in threads:
            t.start()
        
        # 等待所有线程完成
        for t in threads:
            t.join()
        
        # 验证结果
        self.assertEqual(len(results), 20, "应该有20个结果")
        self.assertEqual(call_count[0], 1, "只应该执行一次")
        
        # 关键验证：没有None结果
        none_count = sum(1 for r in results if r is None)
        self.assertEqual(none_count, 0, 
                        f"不应该有None结果，但有{none_count}个None在{results}中")
        
        # 所有结果都应该相同且正确
        expected = {"status": "success", "value": 42}
        for i, result in enumerate(results):
            self.assertEqual(result, expected, 
                           f"结果{i}不正确: {result}")
    
    def test_sequential_requests_not_coalesced(self):
        """测试顺序请求不会被合并（每次都执行）"""
        call_count = [0]
        
        def operation():
            call_count[0] += 1
            return call_count[0]
        
        # 顺序执行3次
        result1 = self.coalescer.coalesce("seq_key", operation)
        time.sleep(0.05)  # 等待清理
        result2 = self.coalescer.coalesce("seq_key", operation)
        time.sleep(0.05)
        result3 = self.coalescer.coalesce("seq_key", operation)
        
        # 每次都应该执行
        self.assertEqual(call_count[0], 3)
        self.assertEqual(result1, 1)
        self.assertEqual(result2, 2)
        self.assertEqual(result3, 3)
    
    def test_exception_handling(self):
        """测试异常传播 - 所有等待者都应该收到相同的异常"""
        call_count = [0]
        started = threading.Event()
        
        def failing_operation():
            # 等待确保所有线程都已启动
            time.sleep(0.1)
            call_count[0] += 1
            raise ValueError("Test error from coalescer")
        
        def submit_request():
            started.wait()  # 等待信号
            return self.coalescer.coalesce("error_key", failing_operation)
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(submit_request) for _ in range(10)]
            
            # 给所有线程一点时间启动
            time.sleep(0.05)
            # 同时释放所有请求
            started.set()
            
            # 收集结果
            exception_count = 0
            exception_messages = []
            for future in futures:
                try:
                    result = future.result(timeout=5)
                    self.fail(f"应该抛出异常，但得到结果: {result}")
                except ValueError as e:
                    exception_count += 1
                    exception_messages.append(str(e))
            
            # 验证：只执行了一次，所有10个请求都收到异常
            self.assertEqual(call_count[0], 1, f"只应该执行一次，实际{call_count[0]}次")
            self.assertEqual(exception_count, 10, "所有10个请求都应该抛出异常")
            
            # 验证：所有异常消息相同
            self.assertTrue(all(msg == "Test error from coalescer" for msg in exception_messages),
                          f"所有异常消息应该相同: {set(exception_messages)}")
    
    def test_performance_improvement(self):
        """测试性能提升 - 合并应该比独立执行快"""
        def slow_operation():
            time.sleep(0.2)  # 200ms
            return "result"
        
        # 10个独立请求：应该需要~2000ms
        start = time.time()
        for _ in range(10):
            slow_operation()
        independent_time = time.time() - start
        
        # 10个合并请求：应该只需要~200ms + 50ms cleanup
        start = time.time()
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(self.coalescer.coalesce, "perf_key", slow_operation)
                for _ in range(10)
            ]
            for f in futures:
                f.result()
        coalesced_time = time.time() - start
        
        # 合并请求应该明显更快（考虑到50ms的cleanup延迟）
        self.assertLess(coalesced_time, independent_time / 3,
                       f"合并请求应该快3倍以上，但独立{independent_time:.2f}s vs 合并{coalesced_time:.2f}s")
        
        print(f"\n性能对比：独立执行{independent_time:.3f}s，合并执行{coalesced_time:.3f}s，"
              f"提升{independent_time/coalesced_time:.1f}倍")


class TestRequestCoalescerIntegration(unittest.TestCase):
    """集成测试 - 模拟实际使用场景"""
    
    def test_bitcoin_price_coalescing(self):
        """模拟BTC价格API并发查询场景"""
        api_call_count = [0]
        started = threading.Event()
        
        def fetch_btc_price():
            """模拟API调用"""
            api_call_count[0] += 1
            time.sleep(0.2)  # 模拟网络延迟
            return {"price": 45000, "timestamp": time.time()}
        
        def submit_request():
            started.wait()  # 等待同步信号
            return request_coalescer.coalesce("btc_price", fetch_btc_price)
        
        # 模拟20个用户同时查询BTC价格
        results = []
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(submit_request) for _ in range(20)]
            
            # 给线程时间启动
            time.sleep(0.05)
            # 同时释放所有请求
            started.set()
            
            for future in as_completed(futures):
                result = future.result(timeout=5)
                results.append(result)
        
        # 验证：API应该只调用一次（请求合并成功）
        self.assertEqual(api_call_count[0], 1, 
                        f"API应该只调用1次，实际{api_call_count[0]}次")
        self.assertEqual(len(results), 20)
        self.assertTrue(all(r is not None for r in results), 
                       "所有结果都应该非None")
        self.assertTrue(all(r['price'] == 45000 for r in results),
                       "所有结果价格应该相同")


def run_tests():
    """运行所有测试"""
    suite = unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
