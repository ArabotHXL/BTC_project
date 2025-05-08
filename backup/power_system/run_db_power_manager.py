"""
基于数据库的智能电力削减管理系统 - 启动脚本
"""
import os
import sys

# 强制使用SQLite数据库
os.environ["DATABASE_URL"] = "sqlite:///power_management.db"

from db_power_management_app import app, power_manager

if __name__ == "__main__":
    try:
        # 打印系统信息
        print("\n===== 基于数据库的智能电力削减管理系统 =====")
        print("数据库URL:", os.environ.get("DATABASE_URL"))
        
        # 初始化数据库
        with app.app_context():
            try:
                from power_management_models import db
                db.create_all()
                print("数据库表创建完成")
                
                from power_management_models import MinerStatus
                
                miners_count = MinerStatus.query.count()
                print(f"当前矿机数量: {miners_count}")
                
                if miners_count == 0:
                    print("初始化矿机数据...")
                    success_count = power_manager.initialize_test_data(100)  # 减少矿机数量以加快初始化速度
                    print(f"成功初始化 {success_count} 台矿机数据")
            except Exception as e:
                print(f"数据库初始化错误: {str(e)}")
                import traceback
                traceback.print_exc()
                print("继续启动应用...")
        
        # 启动Web服务
        print("\n启动智能电力削减管理系统...")
        print("访问: http://localhost:5002/")
        app.run(host='0.0.0.0', port=5002, debug=True, use_reloader=False)
    except Exception as e:
        print(f"启动错误: {str(e)}")
        import traceback
        traceback.print_exc()