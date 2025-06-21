import os
import sys
from datetime import datetime
from flask import Flask
from models import LoginRecord
from db import db, init_db

def get_login_records(limit=20, language="both"):
    """
    获取最近的登录记录 
    Get recent login records
    
    language: "zh" (中文), "en" (English), "both" (双语/Bilingual)
    """
    # 创建一个临时的Flask应用程序上下文 / Create a temporary Flask application context
    app = Flask(__name__)
    # 初始化数据库 / Initialize database
    init_db(app)
    
    with app.app_context():
        # 打印标题 / Print header
        if language in ["zh", "both"]:
            print(f'获取最近 {limit} 条登录记录:')
        if language in ["en", "both"]:
            print(f'Retrieving {limit} recent login records:')
        print('-' * 80)
        
        try:
            records = LoginRecord.query.order_by(LoginRecord.login_time.desc()).limit(limit).all()
            
            if not records:
                if language in ["zh", "both"]:
                    print("没有找到登录记录。")
                if language in ["en", "both"]:
                    print("No login records found.")
                return
            
            for r in records:
                status_zh = "成功" if r.successful else "失败"
                status_en = "Success" if r.successful else "Failed"
                
                # 用户ID和邮箱 / User ID and email
                if language in ["zh", "both"]:
                    print(f'ID: {r.id}, 用户: {r.email}')
                if language in ["en", "both"]:
                    print(f'ID: {r.id}, User: {r.email}')
                
                # 登录时间和状态 / Login time and status
                if language in ["zh", "both"]:
                    print(f'时间: {r.login_time.strftime("%Y-%m-%d %H:%M:%S")}, 状态: {status_zh}')
                if language in ["en", "both"]:
                    print(f'Time: {r.login_time.strftime("%Y-%m-%d %H:%M:%S")}, Status: {status_en}')
                
                # IP地址 / IP address
                ip_display = r.ip_address or "N/A"
                if language in ["zh", "both"]:
                    print(f'IP地址: {ip_display}')
                if language in ["en", "both"]:
                    print(f'IP Address: {ip_display}')
                
                # 完整位置信息 / Complete location info
                location_display = r.login_location or "未知/Unknown"
                if language in ["zh", "both"]:
                    print(f'完整位置信息: {location_display}')
                if language in ["en", "both"]:
                    print(f'Complete Location: {location_display}')
                
                # 解析位置信息以更好地展示 / Parse location for better display
                if r.login_location and ',' in r.login_location:
                    parts = r.login_location.split(',')
                    country = parts[0].strip() if len(parts) > 0 else "未知国家/Unknown Country"
                    region = parts[1].strip() if len(parts) > 1 else "未知地区/Unknown Region"
                    city = parts[2].strip() if len(parts) > 2 else "未知城市/Unknown City"
                    
                    # 国家 / Country
                    if language in ["zh", "both"]:
                        print(f'国家: {country}')
                    if language in ["en", "both"]:
                        print(f'Country: {country}')
                    
                    # 地区 / Region
                    if language in ["zh", "both"]:
                        print(f'地区: {region}')
                    if language in ["en", "both"]:
                        print(f'Region: {region}')
                    
                    # 城市 / City
                    if language in ["zh", "both"]:
                        print(f'城市: {city}')
                    if language in ["en", "both"]:
                        print(f'City: {city}')
                    
                print('-' * 80)
        except Exception as e:
            if language in ["zh", "both"]:
                print(f"查询数据库时出错: {str(e)}")
            if language in ["en", "both"]:
                print(f"Error querying database: {str(e)}")
            
if __name__ == "__main__":
    # 默认获取最近20条记录，可以通过传递命令行参数修改
    # Default to get 20 recent records, can be modified via command line args
    limit = 20
    language = "both"  # 默认双语 / Default to bilingual
    
    if len(sys.argv) > 1:
        try:
            limit = int(sys.argv[1])
        except ValueError:
            if language in ["zh", "both"]:
                print(f"错误：无效的记录数量 '{sys.argv[1]}'，使用默认值 20")
            if language in ["en", "both"]:
                print(f"Error: Invalid record count '{sys.argv[1]}', using default value 20")
    
    # 如果提供了第二个参数，设置语言 / If a second argument is provided, set language
    if len(sys.argv) > 2:
        if sys.argv[2] in ["zh", "en", "both"]:
            language = sys.argv[2]
        else:
            print(f"Invalid language '{sys.argv[2]}'. Using 'both'. Options: zh, en, both")
    
    get_login_records(limit, language)