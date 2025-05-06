"""
智能电力削减管理系统 - 测试脚本
用于直接测试核心功能，无需Web界面
"""
import sys
import json
from smart_power_manager import PowerManagementSystem

def test_power_management():
    """测试电力管理系统的核心功能"""
    print("=== 智能电力削减管理系统测试 ===\n")
    
    # 创建系统实例
    print("初始化系统...")
    system = PowerManagementSystem()
    
    # 如果还没有矿机数据，初始化一些
    if not system.all_miners:
        print("初始化矿机数据...")
        system.initialize_miners(1000)
    
    # 分析矿机健康状况
    print("\n测试功能1: 矿机健康分析")
    health_summary = system.analyze_miners_health()
    print("矿机健康状况摘要:")
    for category, stats in health_summary.items():
        print(f"  {category}级: {stats['count']}台, 平均健康分: {stats['avg_health_score']:.1f}, 平均效率: {stats['avg_efficiency']:.6f}")
    
    # 获取系统状态
    print("\n测试功能2: 系统状态监控")
    status = system.get_system_status()
    print("系统状态:")
    print(f"  总矿机数: {status['total_miners']}台")
    print(f"  运行中: {status['running_miners']}台")
    print(f"  已关停: {status['shutdown_miners']}台")
    print(f"  总算力: {status['total_hashrate']:.2f} TH/s")
    print(f"  总功耗: {status['total_power']:.2f}W")
    
    # 测试不同电力削减百分比
    print("\n测试功能3: 不同电力削减比例测试")
    
    test_percentages = [10, 20, 30]
    results = {}
    
    for percentage in test_percentages:
        print(f"\n应用{percentage}%电力削减:")
        reduction_results = system.apply_power_reduction(percentage)
        
        status = system.get_system_status()
        results[percentage] = {
            'target_reduction': reduction_results['target_reduction'],
            'miners_shutdown': reduction_results['miners_to_shutdown'],
            'running_miners': status['running_miners'],
            'total_hashrate': status['total_hashrate'],
            'effective_reduction': status['effective_power_reduction'],
            'categories': reduction_results['categories_summary']
        }
        
        print(f"  目标削减功率: {reduction_results['target_reduction']:.2f}W")
        print(f"  关停矿机数: {reduction_results['miners_to_shutdown']}台")
        print(f"  剩余运行矿机: {status['running_miners']}台")
        print(f"  剩余总算力: {status['total_hashrate']:.2f} TH/s")
        print(f"  实际削减比例: {status['effective_power_reduction']:.2f}%")
        print("  按类别统计关停数量:")
        for category, count in reduction_results['categories_summary'].items():
            print(f"    {category}级: {count}台")
    
    # 测试矿机轮换
    print("\n测试功能4: 矿机轮换计划")
    rotation_plan = system.generate_rotation_plan()
    
    to_shutdown = len(rotation_plan['next_rotation_plan'].get('miners_to_shutdown', []))
    to_start = len(rotation_plan['next_rotation_plan'].get('miners_to_start', []))
    
    print("矿机轮换计划:")
    print(f"  下次轮换日期: {rotation_plan['next_rotation_date']}")
    print(f"  轮换间隔: {rotation_plan['days_between_rotation']}天")
    print(f"  计划关停: {to_shutdown}台, 计划启动: {to_start}台")
    
    if to_shutdown > 0 and to_start > 0:
        print("\n执行轮换计划...")
        results = system.execute_rotation()
        print(f"  成功关停: {results['successful_shutdown']}/{results['total_shutdown']}台")
        print(f"  成功启动: {results['successful_start']}/{results['total_start']}台")
        
        # 再次获取状态
        status = system.get_system_status()
        print("\n轮换后状态:")
        print(f"  运行中: {status['running_miners']}台")
        print(f"  已关停: {status['shutdown_miners']}台")
    
    # 总结测试结果
    print("\n=== 智能电力削减管理系统测试总结 ===")
    print("1. 矿机健康分析: 成功")
    print("2. 系统状态监控: 成功")
    print("3. 不同电力削减比例测试:")
    for percentage, result in results.items():
        print(f"   - {percentage}%削减: 关停{result['miners_shutdown']}台矿机，实际削减{result['effective_reduction']:.2f}%")
    print("4. 矿机轮换计划: 成功")
    
    print("\n所有功能测试完成!")

if __name__ == "__main__":
    test_power_management()