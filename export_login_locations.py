import os
import sys
import json
from datetime import datetime
from flask import Flask
from models import LoginRecord
from db import db, init_db

def export_login_locations(export_file='login_locations.json'):
    """导出登录位置信息"""
    # 创建一个临时的Flask应用程序上下文
    app = Flask(__name__)
    # 初始化数据库
    init_db(app)
    
    with app.app_context():
        try:
            # 获取所有登录记录
            records = LoginRecord.query.order_by(LoginRecord.login_time.desc()).all()
            
            if not records:
                print("没有找到登录记录。")
                return
            
            # 转换为可JSON序列化的格式
            export_data = []
            for r in records:
                location_data = {
                    'id': r.id,
                    'email': r.email,
                    'login_time': r.login_time.strftime("%Y-%m-%d %H:%M:%S"),
                    'successful': r.successful,
                    'ip_address': r.ip_address,
                    'login_location': r.login_location,
                }
                
                # 解析位置信息
                if r.login_location and ',' in r.login_location:
                    parts = r.login_location.split(',')
                    location_data['country'] = parts[0].strip() if len(parts) > 0 else "未知国家"
                    location_data['region'] = parts[1].strip() if len(parts) > 1 else "未知地区" 
                    location_data['city'] = parts[2].strip() if len(parts) > 2 else "未知城市"
                
                export_data.append(location_data)
            
            # 写入JSON文件
            with open(export_file, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=4)
            
            print(f"成功导出 {len(export_data)} 条登录记录到 {export_file}")
            
            # 生成位置统计
            location_stats = {}
            for record in export_data:
                loc = record.get('login_location', '未知')
                location_stats[loc] = location_stats.get(loc, 0) + 1
            
            print("\n位置统计:")
            for loc, count in sorted(location_stats.items(), key=lambda x: x[1], reverse=True):
                print(f"{loc}: {count}条记录")
                
        except Exception as e:
            print(f"导出登录位置信息时出错: {str(e)}")
            
if __name__ == "__main__":
    # 默认导出文件名
    export_file = 'login_locations.json'
    if len(sys.argv) > 1:
        export_file = sys.argv[1]
    
    export_login_locations(export_file)