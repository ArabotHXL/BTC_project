import os
import sys
from datetime import datetime
from flask import Flask
from models import LoginRecord, UserAccess
from db import db, init_db

def display_user_session_details():
    """显示用户登录会话的详细信息，包括地理位置分析"""
    # 创建一个临时的Flask应用程序上下文
    app = Flask(__name__)
    # 初始化数据库
    init_db(app)
    
    with app.app_context():
        print('\n' + '=' * 80)
        print('用户会话详细信息报告'.center(70))
        print('=' * 80 + '\n')
        
        try:
            # 获取所有用户
            users = UserAccess.query.all()
            print(f"系统中共有 {len(users)} 个用户账户\n")
            
            user_login_stats = {}
            location_stats = {}
            
            # 收集每个用户的登录统计
            for user in users:
                email = user.email
                login_records = LoginRecord.query.filter_by(email=email).all()
                
                successful_logins = [r for r in login_records if r.successful]
                failed_logins = [r for r in login_records if not r.successful]
                
                # 获取最近一次登录
                last_login = None
                last_location = "未登录"
                if successful_logins:
                    last_login = max(successful_logins, key=lambda x: x.login_time)
                    last_location = last_login.login_location or "未知位置"
                
                # 统计登录位置
                login_locations = {}
                for record in successful_logins:
                    loc = record.login_location or "未知位置"
                    login_locations[loc] = login_locations.get(loc, 0) + 1
                    
                    # 更新全局位置统计
                    location_stats[loc] = location_stats.get(loc, 0) + 1
                
                # 存储用户统计信息
                user_login_stats[email] = {
                    'name': user.name,
                    'role': user.role,
                    'total_logins': len(successful_logins),
                    'failed_logins': len(failed_logins),
                    'last_login': last_login.login_time if last_login else None,
                    'last_location': last_location,
                    'locations': login_locations
                }
            
            # 显示用户登录信息
            print('-' * 80)
            print('用户登录活动摘要:')
            print('-' * 80)
            for email, stats in sorted(user_login_stats.items(), key=lambda x: x[1]['total_logins'], reverse=True):
                print(f"用户: {stats['name']} ({email})")
                print(f"角色: {stats['role']}")
                print(f"成功登录次数: {stats['total_logins']}")
                print(f"失败登录尝试: {stats['failed_logins']}")
                
                if stats['last_login']:
                    print(f"最近登录时间: {stats['last_login'].strftime('%Y-%m-%d %H:%M:%S')}")
                    print(f"最近登录位置: {stats['last_location']}")
                
                if stats['locations']:
                    print("登录位置分布:")
                    for loc, count in sorted(stats['locations'].items(), key=lambda x: x[1], reverse=True):
                        print(f"  - {loc}: {count}次 ({count/stats['total_logins']*100:.1f}%)")
                
                print('-' * 80)
            
            # 显示全局位置统计
            total_logins = sum(location_stats.values())
            print("\n全局位置访问统计:")
            print('-' * 80)
            for loc, count in sorted(location_stats.items(), key=lambda x: x[1], reverse=True):
                print(f"{loc}: {count}次 ({count/total_logins*100:.1f}%)")
            
            # 查找可能的不寻常登录模式
            print("\n可能的特殊登录模式分析:")
            print('-' * 80)
            for email, stats in user_login_stats.items():
                # 检查多个不同位置登录
                if len(stats['locations']) > 2:
                    print(f"用户 {stats['name']} ({email}) 从 {len(stats['locations'])} 个不同位置登录过")
                
                # 检查失败登录尝试
                if stats['failed_logins'] > 0:
                    ratio = stats['failed_logins'] / (stats['total_logins'] + stats['failed_logins'])
                    if ratio > 0.3:  # 如果失败率超过30%
                        print(f"用户 {stats['name']} ({email}) 有较高的登录失败率: {ratio*100:.1f}%")
            
        except Exception as e:
            print(f"分析用户会话时出错: {str(e)}")
            
if __name__ == "__main__":
    display_user_session_details()