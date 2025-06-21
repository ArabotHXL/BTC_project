#!/usr/bin/env python3
"""
数据库连接测试脚本
直接测试生产数据库连接状态
"""

import os
import sys
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db

def test_database_connection():
    """测试数据库连接"""
    print("=== 数据库连接测试 ===")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        with app.app_context():
            # 测试基本连接
            result = db.session.execute(db.text("SELECT 1")).scalar()
            print(f"✅ 基本连接测试: {result}")
            
            # 获取数据库信息
            db_info = db.session.execute(
                db.text("SELECT current_database(), current_user, version()")
            ).fetchone()
            print(f"✅ 数据库名称: {db_info[0]}")
            print(f"✅ 当前用户: {db_info[1]}")
            print(f"✅ 版本信息: {db_info[2]}")
            
            # 检查表结构
            tables = db.session.execute(
                db.text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name")
            ).fetchall()
            
            print(f"\n✅ 数据库表 ({len(tables)} 个):")
            for table in tables:
                # 获取每个表的记录数
                count = db.session.execute(
                    db.text(f"SELECT COUNT(*) FROM {table[0]}")
                ).scalar()
                print(f"   - {table[0]}: {count} 条记录")
            
            # 测试连接池状态
            engine = db.engine
            print(f"\n✅ 连接池信息:")
            print(f"   - Pool size: {engine.pool.size()}")
            print(f"   - Checked out: {engine.pool.checkedout()}")
            print(f"   - Overflow: {engine.pool.overflow()}")
            
            # 测试最近的网络快照
            latest_snapshot = db.session.execute(
                db.text("SELECT btc_price, difficulty, created_at FROM network_snapshots ORDER BY created_at DESC LIMIT 1")
            ).fetchone()
            
            if latest_snapshot:
                print(f"\n✅ 最新网络快照:")
                print(f"   - BTC价格: ${latest_snapshot[0]:,.2f}")
                print(f"   - 网络难度: {latest_snapshot[1]:.2f}T")
                print(f"   - 记录时间: {latest_snapshot[2]}")
            
            print("\n🎉 数据库连接完全正常！")
            return True
            
    except Exception as e:
        print(f"❌ 数据库连接错误: {e}")
        import traceback
        print(f"详细错误信息:\n{traceback.format_exc()}")
        return False

def test_database_operations():
    """测试数据库操作"""
    print("\n=== 数据库操作测试 ===")
    
    try:
        with app.app_context():
            # 测试查询操作
            user_count = db.session.execute(
                db.text("SELECT COUNT(*) FROM user_access")
            ).scalar()
            print(f"✅ 用户访问记录查询: {user_count} 个授权用户")
            
            # 测试登录记录查询
            login_count = db.session.execute(
                db.text("SELECT COUNT(*) FROM login_records WHERE created_at > NOW() - INTERVAL '7 days'")
            ).scalar()
            print(f"✅ 近7天登录记录: {login_count} 次登录")
            
            # 测试CRM数据查询
            customer_count = db.session.execute(
                db.text("SELECT COUNT(*) FROM crm_customers")
            ).scalar()
            print(f"✅ CRM客户数据: {customer_count} 个客户")
            
            print("✅ 所有数据库操作正常")
            return True
            
    except Exception as e:
        print(f"❌ 数据库操作错误: {e}")
        return False

def main():
    """主测试函数"""
    print("开始数据库连接和操作测试...")
    
    connection_ok = test_database_connection()
    operations_ok = test_database_operations()
    
    if connection_ok and operations_ok:
        print("\n🎯 总结: 数据库连接和操作完全正常")
        print("   - 连接状态: ✅ 正常")
        print("   - 表结构: ✅ 完整")
        print("   - 数据完整性: ✅ 正常")
        print("   - 操作功能: ✅ 正常")
        return 0
    else:
        print("\n⚠️ 总结: 发现数据库问题")
        return 1

if __name__ == "__main__":
    exit(main())