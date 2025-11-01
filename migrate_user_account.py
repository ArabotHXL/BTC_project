#!/usr/bin/env python3
"""
迁移用户账户脚本 - 从旧数据库恢复账户到新数据库
"""
import os
import sys
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import UserAccess

def migrate_user():
    """迁移用户账户（保留原始密码hash）"""
    with app.app_context():
        try:
            # 从旧数据库导出的用户数据
            user_data = {
                'name': 'Owner',
                'email': 'hxl2022hao@gmail.com',
                'username': None,  # 原始数据中username为空
                'password_hash': 'scrypt:32768:8:1$MPsG5GJrSleLCii9$7c703137309b5950aea82ca99b616402df9b3ae71730700b8bffa3e40ea88f958d7134db497e74c0caf5a9b0291c8108c62de27595597e59df1a93c4f2be7410',
                'is_email_verified': True,
                'role': 'owner',
                'subscription_plan': 'pro',
                'access_days': 365,
                'created_at': datetime(2025, 10, 7, 21, 4, 29, 521257),
                'expires_at': datetime(2026, 10, 7, 21, 4, 29, 521257),
                'last_login': datetime(2025, 10, 25, 21, 23, 36, 717662)
            }
            
            print("=" * 70)
            print("HashInsight Enterprise - 用户账户迁移")
            print("=" * 70)
            print(f"\n正在迁移用户: {user_data['email']}")
            
            # 检查用户是否已存在
            existing_user = UserAccess.query.filter_by(email=user_data['email']).first()
            
            if existing_user:
                print(f"\n⚠️  用户已存在，正在更新...")
                # 更新现有用户
                existing_user.name = user_data['name']
                existing_user.password_hash = user_data['password_hash']
                existing_user.is_email_verified = user_data['is_email_verified']
                existing_user.role = user_data['role']
                existing_user.subscription_plan = user_data['subscription_plan']
                existing_user.access_days = user_data['access_days']
                existing_user.expires_at = user_data['expires_at']
                action = "更新"
            else:
                print(f"\n✅ 创建新用户...")
                # 创建新用户
                new_user = UserAccess(
                    name=user_data['name'],
                    email=user_data['email'],
                    username=user_data['username'],
                    password_hash=user_data['password_hash'],
                    is_email_verified=user_data['is_email_verified'],
                    role=user_data['role'],
                    subscription_plan=user_data['subscription_plan'],
                    access_days=user_data['access_days'],
                    created_at=user_data['created_at'],
                    expires_at=user_data['expires_at'],
                    last_login=user_data['last_login']
                )
                db.session.add(new_user)
                action = "创建"
            
            db.session.commit()
            
            print(f"\n{'=' * 70}")
            print(f"✅ 用户账户{action}成功！")
            print(f"{'=' * 70}")
            print(f"邮箱: {user_data['email']}")
            print(f"角色: {user_data['role']}")
            print(f"订阅计划: {user_data['subscription_plan']}")
            print(f"访问权限: {user_data['access_days']}天")
            print(f"过期时间: {user_data['expires_at'].strftime('%Y-%m-%d')}")
            print(f"邮箱已验证: {'是' if user_data['is_email_verified'] else '否'}")
            print(f"{'=' * 70}")
            print(f"\n🔐 密码已从旧数据库迁移，你可以使用原来的密码登录！")
            print(f"\n{'=' * 70}")
            
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"\n{'=' * 70}")
            print(f"❌ 迁移失败: {e}")
            print(f"{'=' * 70}")
            print("\n请确保：")
            print("1. 新数据库已创建并正常连接")
            print("2. DATABASE_URL 环境变量已更新")
            print("3. 数据库表结构已初始化")
            return False

if __name__ == "__main__":
    success = migrate_user()
    
    if success:
        print("\n✨ 迁移完成！现在你可以：")
        print("   1. 访问 /login 页面")
        print("   2. 使用原来的密码登录")
        print("   3. 享受完整的HashInsight Enterprise功能！")
    else:
        print("\n⚠️  如果迁移失败，请先确保新数据库已创建。")
        print("   然后重新运行此脚本: python migrate_user_account.py")
