"""
性能基准测试模块 - Phase 2.1
Performance Benchmark Module for Mining Calculator

目标：验证5000台矿机批量计算 ≤20秒
Target: Verify 5000 miners calculation in ≤20 seconds
"""
import time
import logging
import pandas as pd
import numpy as np
from typing import Dict, List
from datetime import datetime
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PerformanceBenchmark:
    """性能基准测试类"""
    
    def __init__(self):
        self.results = []
        self.test_scenarios = []
        
    def generate_test_data(self, count: int, miner_models: List[str] = None) -> pd.DataFrame:
        """
        生成测试数据
        
        Parameters:
        -----------
        count : int
            矿机数量
        miner_models : List[str]
            矿机型号列表，如果为None则使用常见型号
            
        Returns:
        --------
        pd.DataFrame : 测试数据
        """
        if miner_models is None:
            miner_models = [
                "Antminer S19 Pro",
                "Antminer S21",
                "Antminer S21 Pro",
                "WhatsMiner M50S",
                "WhatsMiner M56S"
            ]
        
        # 生成随机数据
        np.random.seed(42)  # 确保可重复性
        
        data = {
            'miner_model': np.random.choice(miner_models, count),
            'miner_count': np.random.randint(1, 100, count),
            'site_power_mw': np.random.uniform(0.5, 10.0, count),
            'electricity_cost': np.random.uniform(0.03, 0.08, count)
        }
        
        df = pd.DataFrame(data)
        logger.info(f"生成测试数据：{count} 条记录")
        return df
    
    def benchmark_vectorized_calculation(self, miners_df: pd.DataFrame) -> Dict:
        """
        基准测试：向量化批量计算
        
        Parameters:
        -----------
        miners_df : pd.DataFrame
            矿机数据
            
        Returns:
        --------
        Dict : 性能指标
        """
        from mining_calculator import batch_calculate_mining_profit_vectorized
        
        logger.info(f"开始向量化计算基准测试：{len(miners_df)} 条记录")
        
        start_time = time.time()
        start_memory = self._get_memory_usage()
        
        try:
            results_df = batch_calculate_mining_profit_vectorized(
                miners_df,
                use_real_time=False  # 避免API调用影响性能测试
            )
            
            end_time = time.time()
            end_memory = self._get_memory_usage()
            
            elapsed = end_time - start_time
            memory_delta = end_memory - start_memory
            throughput = len(miners_df) / elapsed
            
            metrics = {
                'method': 'vectorized',
                'record_count': len(miners_df),
                'elapsed_seconds': round(elapsed, 3),
                'throughput_per_second': round(throughput, 2),
                'memory_mb': round(end_memory, 2),
                'memory_delta_mb': round(memory_delta, 2),
                'avg_time_per_record_ms': round(elapsed / len(miners_df) * 1000, 3),
                'success': True,
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(
                f"向量化计算完成：{elapsed:.2f}秒，"
                f"吞吐量 {throughput:.2f} 记录/秒"
            )
            
            return metrics
            
        except Exception as e:
            logger.error(f"向量化计算基准测试失败: {e}")
            return {
                'method': 'vectorized',
                'record_count': len(miners_df),
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def benchmark_concurrent_calculation(self, miners_data_list: List[Dict], 
                                        max_workers: int = 4) -> Dict:
        """
        基准测试：并发批量计算
        
        Parameters:
        -----------
        miners_data_list : List[Dict]
            矿机数据列表
        max_workers : int
            最大worker数
            
        Returns:
        --------
        Dict : 性能指标
        """
        from mining_calculator import batch_calculate_with_concurrency
        
        logger.info(
            f"开始并发计算基准测试：{len(miners_data_list)} 条记录，"
            f"{max_workers} workers"
        )
        
        start_time = time.time()
        start_memory = self._get_memory_usage()
        
        try:
            results = batch_calculate_with_concurrency(
                miners_data_list,
                use_real_time=False,
                max_workers=max_workers
            )
            
            end_time = time.time()
            end_memory = self._get_memory_usage()
            
            elapsed = end_time - start_time
            memory_delta = end_memory - start_memory
            throughput = len(miners_data_list) / elapsed
            
            metrics = {
                'method': 'concurrent',
                'record_count': len(miners_data_list),
                'max_workers': max_workers,
                'elapsed_seconds': round(elapsed, 3),
                'throughput_per_second': round(throughput, 2),
                'memory_mb': round(end_memory, 2),
                'memory_delta_mb': round(memory_delta, 2),
                'avg_time_per_record_ms': round(elapsed / len(miners_data_list) * 1000, 3),
                'success': True,
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(
                f"并发计算完成：{elapsed:.2f}秒，"
                f"吞吐量 {throughput:.2f} 记录/秒"
            )
            
            return metrics
            
        except Exception as e:
            logger.error(f"并发计算基准测试失败: {e}")
            return {
                'method': 'concurrent',
                'record_count': len(miners_data_list),
                'max_workers': max_workers,
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def run_comprehensive_benchmark(self, 
                                   test_sizes: List[int] = None,
                                   worker_configs: List[int] = None) -> Dict:
        """
        运行综合基准测试
        
        Parameters:
        -----------
        test_sizes : List[int]
            测试数据规模列表
        worker_configs : List[int]
            并发worker配置列表
            
        Returns:
        --------
        Dict : 综合测试结果
        """
        if test_sizes is None:
            test_sizes = [100, 500, 1000, 2500, 5000]
        
        if worker_configs is None:
            worker_configs = [2, 4, 8]
        
        logger.info("=" * 80)
        logger.info("开始综合性能基准测试")
        logger.info("=" * 80)
        
        all_results = {
            'vectorized': [],
            'concurrent': [],
            'summary': {}
        }
        
        # 测试向量化计算
        logger.info("\n【向量化计算测试】")
        for size in test_sizes:
            logger.info(f"\n测试规模：{size} 条记录")
            test_df = self.generate_test_data(size)
            metrics = self.benchmark_vectorized_calculation(test_df)
            all_results['vectorized'].append(metrics)
            
            # 检查是否达标
            if size == 5000:
                if metrics.get('success') and metrics['elapsed_seconds'] <= 20:
                    logger.info(f"✅ 5000台矿机测试通过：{metrics['elapsed_seconds']}秒 ≤ 20秒")
                    all_results['summary']['vectorized_5000_pass'] = True
                else:
                    logger.warning(f"⚠️ 5000台矿机测试未达标：{metrics.get('elapsed_seconds', 'N/A')}秒 > 20秒")
                    all_results['summary']['vectorized_5000_pass'] = False
        
        # 测试并发计算
        logger.info("\n【并发计算测试】")
        for size in test_sizes:
            test_df = self.generate_test_data(size)
            test_data_list = test_df.to_dict('records')
            
            for workers in worker_configs:
                logger.info(f"\n测试规模：{size} 条记录，{workers} workers")
                metrics = self.benchmark_concurrent_calculation(
                    test_data_list,
                    max_workers=workers
                )
                all_results['concurrent'].append(metrics)
                
                # 检查5000台矿机是否达标
                if size == 5000:
                    if metrics.get('success') and metrics['elapsed_seconds'] <= 20:
                        logger.info(f"✅ 5000台矿机({workers} workers)测试通过：{metrics['elapsed_seconds']}秒 ≤ 20秒")
                        all_results['summary'][f'concurrent_{workers}workers_5000_pass'] = True
                    else:
                        logger.warning(f"⚠️ 5000台矿机({workers} workers)测试未达标")
                        all_results['summary'][f'concurrent_{workers}workers_5000_pass'] = False
        
        # 生成汇总统计
        all_results['summary']['total_tests'] = len(all_results['vectorized']) + len(all_results['concurrent'])
        all_results['summary']['test_timestamp'] = datetime.now().isoformat()
        
        # 找出最佳性能配置
        best_vectorized = min(
            [r for r in all_results['vectorized'] if r.get('success') and r['record_count'] == 5000],
            key=lambda x: x['elapsed_seconds'],
            default=None
        )
        
        best_concurrent = min(
            [r for r in all_results['concurrent'] if r.get('success') and r['record_count'] == 5000],
            key=lambda x: x['elapsed_seconds'],
            default=None
        )
        
        all_results['summary']['best_vectorized_5000'] = best_vectorized
        all_results['summary']['best_concurrent_5000'] = best_concurrent
        
        logger.info("\n" + "=" * 80)
        logger.info("基准测试完成")
        logger.info("=" * 80)
        
        return all_results
    
    def export_results(self, results: Dict, output_file: str = 'benchmark_results.json'):
        """
        导出测试结果
        
        Parameters:
        -----------
        results : Dict
            测试结果
        output_file : str
            输出文件路径
        """
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            logger.info(f"测试结果已导出到：{output_file}")
        except Exception as e:
            logger.error(f"导出测试结果失败: {e}")
    
    def _get_memory_usage(self) -> float:
        """获取当前内存使用量(MB)"""
        try:
            import psutil
            process = psutil.Process()
            memory_info = process.memory_info()
            return memory_info.rss / 1024 / 1024  # 转换为MB
        except ImportError:
            logger.warning("psutil未安装，无法获取内存使用量")
            return 0.0
        except Exception as e:
            logger.warning(f"获取内存使用量失败: {e}")
            return 0.0


def run_quick_benchmark():
    """快速基准测试 - 用于开发验证"""
    benchmark = PerformanceBenchmark()
    
    logger.info("运行快速基准测试（5000台矿机）...")
    test_df = benchmark.generate_test_data(5000)
    
    # 向量化测试
    vectorized_metrics = benchmark.benchmark_vectorized_calculation(test_df)
    
    # 并发测试
    test_data_list = test_df.to_dict('records')
    concurrent_metrics = benchmark.benchmark_concurrent_calculation(
        test_data_list,
        max_workers=4
    )
    
    # 输出结果
    logger.info("\n" + "=" * 80)
    logger.info("快速基准测试结果")
    logger.info("=" * 80)
    logger.info(f"向量化方法：{vectorized_metrics.get('elapsed_seconds', 'N/A')}秒")
    logger.info(f"并发方法(4 workers)：{concurrent_metrics.get('elapsed_seconds', 'N/A')}秒")
    
    # 检查是否达标
    vectorized_pass = vectorized_metrics.get('success') and vectorized_metrics['elapsed_seconds'] <= 20
    concurrent_pass = concurrent_metrics.get('success') and concurrent_metrics['elapsed_seconds'] <= 20
    
    logger.info(f"\n向量化方法达标：{'✅ 是' if vectorized_pass else '❌ 否'}")
    logger.info(f"并发方法达标：{'✅ 是' if concurrent_pass else '❌ 否'}")
    
    return {
        'vectorized': vectorized_metrics,
        'concurrent': concurrent_metrics
    }


if __name__ == '__main__':
    # 运行综合基准测试
    benchmark = PerformanceBenchmark()
    results = benchmark.run_comprehensive_benchmark()
    benchmark.export_results(results)
