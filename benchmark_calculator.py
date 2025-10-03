#!/usr/bin/env python3
"""
性能基准测试脚本 - Mining Calculator Performance Benchmark
Benchmark Calculator Performance Testing

测试目标：
- 5000台矿机批量计算 ≤20秒
- 比较优化前后的性能提升
- 生成性能对比报告

Usage:
    python benchmark_calculator.py
"""

import time
import pandas as pd
import numpy as np
import logging
import json
from datetime import datetime
from mining_calculator import (
    batch_calculate_mining_profit_vectorized,
    batch_calculate_with_concurrency,
    calculate_mining_profitability,
    MINER_DATA
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def generate_test_data(num_miners=5000):
    """生成测试数据"""
    logging.info(f"生成 {num_miners} 条测试数据...")
    
    # 矿机型号列表
    miner_models = list(MINER_DATA.keys())
    
    # 随机生成测试数据
    np.random.seed(42)  # 固定随机种子以保证可重复性
    
    test_data = []
    for i in range(num_miners):
        test_data.append({
            'id': i + 1,
            'miner_model': np.random.choice(miner_models),
            'miner_count': np.random.randint(1, 100),
            'site_power_mw': np.random.uniform(1, 50)
        })
    
    df = pd.DataFrame(test_data)
    logging.info(f"测试数据生成完成：{len(df)} 条记录")
    return df


def benchmark_traditional_loop(test_data):
    """基准测试：传统循环方式（逐个计算）"""
    logging.info("=" * 60)
    logging.info("基准测试 1: 传统循环方式")
    logging.info("=" * 60)
    
    start_time = time.time()
    results = []
    
    # 只测试前100条，因为传统方式太慢
    sample_size = min(100, len(test_data))
    logging.info(f"测试样本：{sample_size} 条（传统方式太慢，仅测试部分）")
    
    for idx, row in test_data.head(sample_size).iterrows():
        try:
            result = calculate_mining_profitability(
                miner_model=row['miner_model'],
                miner_count=row['miner_count'],
                use_real_time_data=False  # 使用默认值以保证速度一致性
            )
            results.append(result)
        except Exception as e:
            logging.error(f"计算失败 (ID: {row['id']}): {e}")
    
    elapsed = time.time() - start_time
    
    # 推算全部5000条所需时间
    estimated_total = (elapsed / sample_size) * len(test_data)
    
    logging.info(f"✓ 完成 {len(results)} 条计算")
    logging.info(f"✓ 耗时: {elapsed:.2f} 秒")
    logging.info(f"✓ 平均: {elapsed/len(results)*1000:.1f} ms/条")
    logging.info(f"✗ 推算5000条需要: {estimated_total:.2f} 秒 ({estimated_total/60:.1f} 分钟)")
    
    return {
        'method': 'Traditional Loop',
        'sample_size': sample_size,
        'total_size': len(test_data),
        'elapsed_seconds': elapsed,
        'avg_ms_per_record': elapsed / len(results) * 1000,
        'estimated_total_seconds': estimated_total,
        'success_count': len(results)
    }


def benchmark_vectorized(test_data):
    """基准测试：NumPy向量化方式"""
    logging.info("=" * 60)
    logging.info("基准测试 2: NumPy向量化批量计算")
    logging.info("=" * 60)
    
    start_time = time.time()
    
    results_df = batch_calculate_mining_profit_vectorized(
        test_data, 
        use_real_time=False  # 使用默认值以保证速度一致性
    )
    
    elapsed = time.time() - start_time
    
    logging.info(f"✓ 完成 {len(results_df)} 条计算")
    logging.info(f"✓ 耗时: {elapsed:.2f} 秒")
    logging.info(f"✓ 平均: {elapsed/len(results_df)*1000:.1f} ms/条")
    
    # 检查是否满足目标
    target_seconds = 20
    if elapsed <= target_seconds:
        logging.info(f"✓ 性能目标达成！({elapsed:.2f}s ≤ {target_seconds}s)")
    else:
        logging.warning(f"✗ 未达到性能目标 ({elapsed:.2f}s > {target_seconds}s)")
    
    return {
        'method': 'Vectorized (NumPy)',
        'sample_size': len(results_df),
        'total_size': len(results_df),
        'elapsed_seconds': elapsed,
        'avg_ms_per_record': elapsed / len(results_df) * 1000,
        'estimated_total_seconds': elapsed,
        'success_count': len(results_df),
        'meets_target': elapsed <= target_seconds
    }


def benchmark_concurrent(test_data):
    """基准测试：并发方式"""
    logging.info("=" * 60)
    logging.info("基准测试 3: 并发批量计算")
    logging.info("=" * 60)
    
    # 转换为字典列表
    data_list = test_data.to_dict('records')
    
    start_time = time.time()
    
    results = batch_calculate_with_concurrency(
        data_list,
        use_real_time=False,
        max_workers=4,
        chunk_size=1000
    )
    
    elapsed = time.time() - start_time
    
    logging.info(f"✓ 完成 {len(results)} 条计算")
    logging.info(f"✓ 耗时: {elapsed:.2f} 秒")
    logging.info(f"✓ 平均: {elapsed/len(results)*1000:.1f} ms/条")
    
    # 检查是否满足目标
    target_seconds = 20
    if elapsed <= target_seconds:
        logging.info(f"✓ 性能目标达成！({elapsed:.2f}s ≤ {target_seconds}s)")
    else:
        logging.warning(f"✗ 未达到性能目标 ({elapsed:.2f}s > {target_seconds}s)")
    
    return {
        'method': 'Concurrent (ThreadPool)',
        'sample_size': len(results),
        'total_size': len(results),
        'elapsed_seconds': elapsed,
        'avg_ms_per_record': elapsed / len(results) * 1000,
        'estimated_total_seconds': elapsed,
        'success_count': len(results),
        'meets_target': elapsed <= target_seconds
    }


def calculate_speedup(benchmark_results):
    """计算性能提升倍数"""
    baseline = benchmark_results[0]['estimated_total_seconds']
    
    for result in benchmark_results:
        speedup = baseline / result['estimated_total_seconds']
        result['speedup_vs_baseline'] = f"{speedup:.1f}x"
        result['improvement_percent'] = f"{(speedup - 1) * 100:.1f}%"
    
    return benchmark_results


def generate_performance_report(benchmark_results, output_file='performance_report.json'):
    """生成性能对比报告"""
    logging.info("=" * 60)
    logging.info("性能对比报告")
    logging.info("=" * 60)
    
    # 添加性能提升计算
    benchmark_results = calculate_speedup(benchmark_results)
    
    # 打印表格
    print("\n性能对比表格：")
    print("-" * 120)
    print(f"{'方法':<25} {'样本数':<10} {'总数':<10} {'耗时(秒)':<12} {'平均(ms)':<12} {'推算总时间(秒)':<15} {'提速':<10} {'改善%':<10}")
    print("-" * 120)
    
    for result in benchmark_results:
        print(
            f"{result['method']:<25} "
            f"{result['sample_size']:<10} "
            f"{result['total_size']:<10} "
            f"{result['elapsed_seconds']:<12.2f} "
            f"{result['avg_ms_per_record']:<12.1f} "
            f"{result['estimated_total_seconds']:<15.2f} "
            f"{result.get('speedup_vs_baseline', 'N/A'):<10} "
            f"{result.get('improvement_percent', 'N/A'):<10}"
        )
    
    print("-" * 120)
    
    # 生成JSON报告
    report = {
        'generated_at': datetime.now().isoformat(),
        'test_configuration': {
            'total_records': benchmark_results[0]['total_size'],
            'target_time_seconds': 20,
            'test_environment': 'Development'
        },
        'benchmark_results': benchmark_results,
        'summary': {
            'best_method': min(benchmark_results, key=lambda x: x['estimated_total_seconds'])['method'],
            'best_time': min(x['estimated_total_seconds'] for x in benchmark_results),
            'target_achieved': any(x.get('meets_target', False) for x in benchmark_results)
        }
    }
    
    with open(output_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    logging.info(f"\n✓ 性能报告已保存到: {output_file}")
    
    return report


def main():
    """主测试函数"""
    logging.info("=" * 60)
    logging.info("Mining Calculator 性能基准测试")
    logging.info("目标：5000台矿机批量计算 ≤20秒")
    logging.info("=" * 60)
    
    # 1. 生成测试数据
    test_data = generate_test_data(num_miners=5000)
    
    # 2. 运行基准测试
    benchmark_results = []
    
    # 测试1: 传统循环方式（仅部分测试）
    result1 = benchmark_traditional_loop(test_data)
    benchmark_results.append(result1)
    
    # 测试2: NumPy向量化方式
    result2 = benchmark_vectorized(test_data)
    benchmark_results.append(result2)
    
    # 测试3: 并发方式
    result3 = benchmark_concurrent(test_data)
    benchmark_results.append(result3)
    
    # 3. 生成性能报告
    report = generate_performance_report(benchmark_results)
    
    # 4. 总结
    logging.info("\n" + "=" * 60)
    logging.info("测试总结")
    logging.info("=" * 60)
    
    if report['summary']['target_achieved']:
        logging.info("✓ 性能目标已达成！")
        logging.info(f"  最佳方法: {report['summary']['best_method']}")
        logging.info(f"  最佳时间: {report['summary']['best_time']:.2f} 秒")
    else:
        logging.warning("✗ 性能目标未达成，需要进一步优化")
    
    logging.info("\n测试完成！")
    
    return report


if __name__ == '__main__':
    main()
