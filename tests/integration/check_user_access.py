import os
import sys
from datetime import datetime
from flask import Flask
from models import UserAccess
from db import db, init_db

def get_users_access():
    """获取所有用户的访问权限信息"""
    # 创建一个临时的Flask应用程序上下文
    app = Flask(__name__)
    # 初始化数据库
    init_db(app)
    
    with app.app_context():
        print('用户访问权限信息:')
        print('-' * 100)
        print(f"{'ID':<4} {'姓名':<15} {'邮箱':<25} {'角色':<10} {'状态':<10} {'剩余天数':<10} {'公司':<20}")
        print('-' * 100)
        
        try:
            users = UserAccess.query.order_by(UserAccess.expires_at.desc()).all()
            
            if not users:
                print("没有找到用户访问权限记录。")
                return
            
            for u in users:
                print(f"{u.id:<4} {u.name:<15} {u.email:<25} {u.role:<10} {u.access_status:<10} {u.days_remaining:<10} {u.company or 'N/A':<20}")
            
            print('-' * 100)
            print(f"总用户数: {len(users)}")
            
            # 统计角色分布
            roles = {}
            for u in users:
                roles[u.role] = roles.get(u.role, 0) + 1
            
            print("\n角色分布:")
            for role, count in roles.items():
                print(f"- {role}: {count}人")
                
            # 统计有效/过期访问权限
            active = sum(1 for u in users if u.has_access)
            expired = len(users) - active
            print(f"\n有效访问权限: {active}人")
            print(f"过期访问权限: {expired}人")
            
        except Exception as e:
            print(f"查询数据库时出错: {str(e)}")
            
if __name__ == "__main__":
    get_users_access()