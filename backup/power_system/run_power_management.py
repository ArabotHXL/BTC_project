"""
智能电力削减管理系统 - 启动脚本
"""
import os
import sys
from power_management_app import app, power_system

if __name__ == "__main__":
    # 确保有矿机数据
    if not power_system.all_miners:
        print("初始化矿机数据...")
        power_system.initialize_miners(1000)
    
    # 分析矿机健康状况
    print("分析矿机健康状况...")
    health_summary = power_system.analyze_miners_health()
    
    # 显示初始状态
    print("系统初始状态:")
    status = power_system.get_system_status()
    print(f"  总矿机数: {status['total_miners']}台")
    print(f"  运行中: {status['running_miners']}台")
    print(f"  已关停: {status['shutdown_miners']}台")
    
    # 启动Web服务
    print("启动智能电力削减管理系统...")
    print("访问: http://localhost:5001/")
    app.run(host='0.0.0.0', port=5001, debug=True)