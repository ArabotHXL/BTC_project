#!/usr/bin/env python3
"""
创建用户账户脚本 - 用于新数据库
"""
import os
import sys
from werkzeug.security import generate_password_hash
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import UserAccess

def create_user(email, username, password, role='owner'):
    """创建新用户账户"""
    with app.app_context():
        try:
            # 检查用户是否已存在
            existing_user = UserAccess.query.filter(
                (UserAccess.email == email) | (UserAccess.username == username)
            ).first()
            
            if existing_user:
                print(f"⚠️  用户已存在: {email} / {username}")
                return False
            
            # 创建新用户
            new_user = UserAccess(
                email=email,
                username=username,
                password_hash=generate_password_hash(password),
                role=role,
                access_start=datetime.utcnow(),
                created_at=datetime.utcnow()
            )
            
            db.session.add(new_user)
            db.session.commit()
            
            print(f"✅ 用户创建成功!")
            print(f"   邮箱: {email}")
            print(f"   用户名: {username}")
            print(f"   角色: {role}")
            print(f"   密码: [已加密存储]")
            
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ 创建用户失败: {e}")
            return False

if __name__ == "__main__":
    # 创建用户账户
    print("=" * 60)
    print("HashInsight Enterprise - 创建用户账户")
    print("=" * 60)
    
    # 用户信息
    email = "hxl2022hao@gmail.com"
    username = "hxl2022"
    password = "HashInsight2025!"  # 默认密码，用户可以后续修改
    role = "owner"
    
    print(f"\n正在创建用户账户...")
    print(f"邮箱: {email}")
    print(f"用户名: {username}")
    print(f"角色: {role}")
    print(f"默认密码: {password}")
    print(f"\n⚠️  首次登录后请修改密码！\n")
    
    success = create_user(email, username, password, role)
    
    if success:
        print("\n" + "=" * 60)
        print("✅ 账户创建完成！现在可以使用以下信息登录：")
        print("=" * 60)
        print(f"邮箱: {email}")
        print(f"密码: {password}")
        print("=" * 60)
        print("\n🔒 安全提示：首次登录后请立即修改密码！")
    else:
        print("\n" + "=" * 60)
        print("❌ 账户创建失败！请检查数据库连接。")
        print("=" * 60)
