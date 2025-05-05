import os
import sys
from datetime import datetime
from app import app
from models import LoginRecord

def get_login_records(limit=20):
    """获取最近的登录记录"""
    with app.app_context():
        print(f'获取最近 {limit} 条登录记录:')
        print('-' * 80)
        
        records = LoginRecord.query.order_by(LoginRecord.login_time.desc()).limit(limit).all()
        
        if not records:
            print("没有找到登录记录。")
            return
        
        for r in records:
            status = "成功" if r.successful else "失败"
            print(f'ID: {r.id}, 用户: {r.email}')
            print(f'时间: {r.login_time.strftime("%Y-%m-%d %H:%M:%S")}, 状态: {status}')
            print(f'IP: {r.ip_address or "N/A"}')
            print(f'位置: {r.login_location or "未知"}')
            print('-' * 80)
            
if __name__ == "__main__":
    # 默认获取最近20条记录，可以通过传递命令行参数修改
    limit = 20
    if len(sys.argv) > 1:
        try:
            limit = int(sys.argv[1])
        except ValueError:
            print(f"错误：无效的记录数量 '{sys.argv[1]}'，使用默认值 20")
    
    get_login_records(limit)