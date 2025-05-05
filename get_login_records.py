import os
import sys
from datetime import datetime
from flask import Flask
from models import LoginRecord
from db import db, init_db

def get_login_records(limit=20):
    """获取最近的登录记录"""
    # 创建一个临时的Flask应用程序上下文
    app = Flask(__name__)
    # 初始化数据库
    init_db(app)
    
    with app.app_context():
        print(f'获取最近 {limit} 条登录记录:')
        print('-' * 80)
        
        try:
            records = LoginRecord.query.order_by(LoginRecord.login_time.desc()).limit(limit).all()
            
            if not records:
                print("没有找到登录记录。")
                return
            
            for r in records:
                status = "成功" if r.successful else "失败"
                print(f'ID: {r.id}, 用户: {r.email}')
                print(f'时间: {r.login_time.strftime("%Y-%m-%d %H:%M:%S")}, 状态: {status}')
                print(f'IP: {r.ip_address or "N/A"}')
                print(f'完整位置信息: {r.login_location or "未知"}')
                
                # 解析位置信息以更好地展示
                if r.login_location and ',' in r.login_location:
                    parts = r.login_location.split(',')
                    country = parts[0].strip() if len(parts) > 0 else "未知国家"
                    region = parts[1].strip() if len(parts) > 1 else "未知地区"
                    city = parts[2].strip() if len(parts) > 2 else "未知城市"
                    print(f'国家: {country}')
                    print(f'地区: {region}')
                    print(f'城市: {city}')
                    
                print('-' * 80)
        except Exception as e:
            print(f"查询数据库时出错: {str(e)}")
            
if __name__ == "__main__":
    # 默认获取最近20条记录，可以通过传递命令行参数修改
    limit = 20
    if len(sys.argv) > 1:
        try:
            limit = int(sys.argv[1])
        except ValueError:
            print(f"错误：无效的记录数量 '{sys.argv[1]}'，使用默认值 20")
    
    get_login_records(limit)