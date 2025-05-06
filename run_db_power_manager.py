"""
基于数据库的智能电力削减管理系统 - 启动脚本
"""
import os
import sys
from db_power_management_app import app, power_manager

if __name__ == "__main__":
    # 确保数据库环境变量设置正确
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("警告: 数据库URL环境变量未设置，使用默认SQLite数据库")
        # 设置默认SQLite数据库
        os.environ["DATABASE_URL"] = "sqlite:///power_management.db"
    
    # 打印系统信息
    print("\n===== 基于数据库的智能电力削减管理系统 =====")
    print("数据库URL:", os.environ.get("DATABASE_URL"))
    
    # 确保有矿机数据
    with app.app_context():
        from power_management_models import MinerStatus
        
        miners_count = MinerStatus.query.count()
        print(f"当前矿机数量: {miners_count}")
        
        if miners_count == 0:
            print("初始化矿机数据...")
            success_count = power_manager.initialize_test_data(1000)
            print(f"成功初始化 {success_count} 台矿机数据")
    
    # 启动Web服务
    print("\n启动智能电力削减管理系统...")
    print("访问: http://localhost:5002/")
    app.run(host='0.0.0.0', port=5002, debug=True)