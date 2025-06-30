# 标准库导入
import logging
import json
import os
import secrets
import requests
import time
import traceback
from datetime import datetime, timedelta
import pytz

# 第三方库导入
import numpy as np
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash, g

# 本地模块导入
from auth import verify_email, login_required
from db import db
from models import LoginRecord, UserAccess, Customer, Contact, Lead, Activity, LeadStatus, DealStatus, NetworkSnapshot
from translations import get_translation
from mining_calculator import (
    MINER_DATA,
    get_real_time_btc_price,
    get_real_time_difficulty,
    get_real_time_block_reward,
    get_real_time_btc_hashrate,
    calculate_mining_profitability,
    generate_profit_chart_data,
    calculate_monthly_curtailment_impact
)
from crm_routes import init_crm_routes
from services.network_data_service import network_collector, network_analyzer
from mining_broker_routes import init_broker_routes

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# 默认网络参数
DEFAULT_HASHRATE_EH = 900  # 默认哈希率，单位: EH/s
DEFAULT_BTC_PRICE = 80000  # 默认比特币价格，单位: USD
DEFAULT_DIFFICULTY = 119.12  # 默认难度，单位: T
DEFAULT_BLOCK_REWARD = 3.125  # 默认区块奖励，单位: BTC

# Initialize Flask app
app = Flask(__name__)

# 设置安全的会话密钥
app.secret_key = os.environ.get("SESSION_SECRET", secrets.token_hex(32))

# 添加自定义过滤器
@app.template_filter('nl2br')
def nl2br_filter(s):
    """将文本中的换行符转换为HTML的<br>标签"""
    if s is None:
        return ""
    return str(s).replace('\n', '<br>')

# 默认语言 'en' 英文, 'zh' 中文
DEFAULT_LANGUAGE = 'zh'

# 在请求前处理设置语言
@app.before_request
def before_request():
    # 优先从会话中获取语言设置，如果没有则从 URL 参数获取，如果都没有则使用默认值
    g.language = session.get('language', request.args.get('lang', DEFAULT_LANGUAGE))
    
    # 如果有语言切换请求，保存到会话
    if request.args.get('lang'):
        session['language'] = request.args.get('lang')
        g.language = session['language']

# 添加翻译函数到模板上下文
@app.context_processor
def inject_translator():
    def translate(text):
        return get_translation(text, to_lang=g.language)
    return dict(t=translate, current_lang=g.language)

def get_user_role(email):
    """根据用户邮箱获取角色"""
    user = UserAccess.query.filter_by(email=email).first()
    if user and user.has_access:
        return user.role
    return None
    
def has_role(required_roles):
    """检查当前用户是否拥有指定角色之一"""
    email = session.get('email')
    if not email:
        return False
    
    user_role = get_user_role(email)
    if not user_role:
        return False
        
    # 如果用户是 owner，那么拥有所有权限
    if user_role == 'owner':
        return True
        
    # 检查用户角色是否在所需角色列表中
    return user_role in required_roles

# 登录页面
@app.route('/login', methods=['GET', 'POST'])
def login():
    """处理用户登录"""
    # 如果用户已经登录，重定向到主页
    if session.get('authenticated'):
        return redirect(url_for('index'))
    
    # 处理表单提交
    if request.method == 'POST':
        email = request.form.get('email')
        
        # 验证邮箱
        login_successful = verify_email(email)
        
        # 记录登录尝试
        try:
            # 获取地理位置信息（基于IP地址）
            location = "未知位置"  # 默认设置
            # 初始化客户端IP以避免未定义
            client_ip = request.remote_addr
            
            try:
                # 获取真实的客户端IP地址
                # 在Replit环境中，通常通过X-Forwarded-For或X-Real-IP头部获取
                client_ip = request.headers.get('X-Forwarded-For') or \
                           request.headers.get('X-Real-IP') or \
                           request.remote_addr
                
                # 如果X-Forwarded-For包含多个IP，取第一个（最靠近客户端的IP）
                if client_ip and ',' in client_ip:
                    client_ip = client_ip.split(',')[0].strip()
                
                logging.info(f"识别到的客户端IP: {client_ip}, 原始IP: {request.remote_addr}")
                
                if client_ip:
                    # 如果是本地或内部网络IP
                    if client_ip.startswith('127.') or client_ip == '::1':
                        location = "本地, 开发环境, localhost"
                    elif client_ip.startswith('192.168.') or client_ip.startswith('10.'):
                        location = "中国, 内部网络, 局域网"
                    else:
                        # 使用IP-API获取地理位置信息
                        # 免费版的ip-api.com，不需要API密钥
                        # 验证IP地址格式，防止SSRF攻击
                        import re
                        ip_pattern = re.compile(r'^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$')
                        ip_match = ip_pattern.match(client_ip)
                        
                        if ip_match:
                            # 确保IP地址的每个部分都是有效的（0-255）
                            is_valid = True
                            for i in range(1, 5):
                                octet = int(ip_match.group(i))
                                if octet < 0 or octet > 255:
                                    is_valid = False
                                    break
                            
                            if is_valid:
                                ip_api_url = f"http://ip-api.com/json/{client_ip}?fields=status,message,country,regionName,city,query"
                                response = requests.get(ip_api_url, timeout=3)
                            else:
                                logging.warning(f"无效的IP地址格式: {client_ip}")
                                location = "未知位置 (无效IP格式)"
                                response = None
                        else:
                            logging.warning(f"无效的IP地址格式: {client_ip}")
                            location = "未知位置 (无效IP格式)"
                            response = None
                        if response and response.status_code == 200:
                            data = response.json()
                            if data.get('status') == 'success':
                                country = data.get('country', '未知国家')
                                region = data.get('regionName', '未知地区')
                                city = data.get('city', '未知城市')
                                # 格式化为：国家, 地区, 城市
                                location = f"{country}, {region}, {city}"
                                logging.info(f"成功获取地理位置信息: {location}")
                            else:
                                error_msg = data.get('message', '未知错误')
                                logging.warning(f"IP-API返回错误: {error_msg}")
                                # 对于私有IP范围，使用更友好的显示
                                if error_msg == 'private range':
                                    # 如果在Replit环境中且检测到私有IP
                                    if 'replit' in request.headers.get('Host', '').lower():
                                        location = f"Replit托管服务, {client_ip}"
                                    else:
                                        location = f"私有网络, {client_ip}"
                                else:
                                    location = f"外部网络 ({client_ip})"
                        else:
                            logging.warning(f"IP-API请求失败，状态码: {response.status_code}")
                            location = f"外部网络 ({client_ip})"
                    
                    # 记录请求头信息以便调试
                    headers_info = {key: value for key, value in request.headers.items() 
                                   if key.lower() in ['x-forwarded-for', 'x-real-ip', 'host', 'user-agent']}
                    logging.info(f"请求头信息: {headers_info}")
                    logging.info(f"用户IP地址 {client_ip} 已被识别为 {location}")
            except Exception as e:
                logging.error(f"获取位置信息时出错: {str(e)}")
                
            login_record = LoginRecord(
                email=email,
                successful=login_successful,
                ip_address=client_ip,  # 使用获取到的真实客户端IP
                login_location=location
            )
            logging.info(f"创建登录记录: {email}, 状态: {'成功' if login_successful else '失败'}")
            db.session.add(login_record)
            db.session.commit()
            logging.info("登录记录已保存到数据库")
        except Exception as e:
            logging.error(f"保存登录记录时发生错误: {str(e)}")
            db.session.rollback()
        
        if login_successful:
            # 登录成功，设置会话
            session['authenticated'] = True
            session['email'] = email
            
            # 获取用户信息并保存到会话
            user = UserAccess.query.filter_by(email=email).first()
            if user:
                session['user_id'] = user.id
                user.last_login = datetime.utcnow()
                db.session.commit()
            
            # 获取并保存用户角色到会话
            user_role = get_user_role(email)
            session['role'] = user_role
            
            # 记录成功登录
            logging.info(f"用户成功登录: {email}, ID: {session.get('user_id')}")
            
            # 设置闪现成功消息，基于当前语言
            if g.language == 'en':
                flash('Login successful! Welcome to BTC Mining Calculator', 'success')
            else:
                flash('登录成功！欢迎使用BTC挖矿计算器', 'success')
            
            # 重定向到原始请求的URL或主页
            next_url = session.pop('next_url', url_for('index'))
            return redirect(next_url)
        else:
            # 登录失败
            logging.warning(f"用户登录失败: {email}")
            
            # 设置闪现错误消息，基于当前语言
            if g.language == 'en':
                flash('Login failed! You do not have access permission', 'danger')
            else:
                flash('登录失败！您没有访问权限', 'danger')
            
            # 重定向到未授权页面
            return redirect(url_for('unauthorized'))
    
    # 显示登录表单
    return render_template('login.html')

@app.route('/unauthorized')
def unauthorized():
    """显示未授权页面"""
    return render_template('unauthorized.html')

@app.route('/logout')
def logout():
    """处理用户登出 / Handle user logout"""
    # 保存当前语言 / Save current language
    current_lang = g.language
    
    # 清除会话但保留语言偏好 / Clear session but keep language preference
    session.clear()
    session['language'] = current_lang
    
    # 闪现消息，基于语言 / Flash message based on language
    if current_lang == 'en':
        flash('You have successfully logged out', 'info')
    else:
        flash('您已成功退出登录', 'info')
        
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    """渲染BTC挖矿计算器主页"""
    return render_template('index.html')

@app.route('/admin/login_records')
@login_required
def login_records():
    """拥有者查看登录记录"""
    # 只允许拥有者角色访问
    if not has_role(['owner']):
        flash('您没有权限访问此页面，需要拥有者权限', 'danger')
        return redirect(url_for('index'))
    
    # 获取登录记录
    records = LoginRecord.query.order_by(LoginRecord.login_time.desc()).limit(100).all()
    return render_template('login_records.html', records=records)
    
@app.route('/admin/login_dashboard')
@login_required
def login_dashboard():
    """拥有者查看登录数据分析仪表盘"""
    # 只允许拥有者角色访问
    if not has_role(['owner']):
        if g.language == 'en':
            flash('Access denied. Owner privileges required.', 'danger')
        else:
            flash('您没有权限访问此页面，需要拥有者权限', 'danger')
        return redirect(url_for('index'))
    
    # 从数据库获取登录记录
    all_records = LoginRecord.query.order_by(LoginRecord.login_time.desc()).all()
    
    # 定义从UTC转换到EST的时区偏移（-5小时）
    utc_to_est_offset = timedelta(hours=-5)
    
    # 处理记录，将UTC时间转换为EST时间
    records_with_est = []
    for record in all_records:
        # 深拷贝记录对象的关键属性
        record_copy = {
            'id': record.id,
            'email': record.email,
            'login_time': record.login_time,
            'successful': record.successful,
            'ip_address': record.ip_address,
            'login_location': record.login_location,
            # 转换为EST时间
            'est_time': (record.login_time + utc_to_est_offset).strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # 处理位置显示
        display_location = "未知/Unknown"
        if record.login_location and ',' in record.login_location:
            parts = record.login_location.split(',')
            if len(parts) >= 3:
                country = parts[0].strip()
                region = parts[1].strip()
                city = parts[2].strip()
                display_location = f"{city}, {region}, {country}"
            elif len(parts) == 2:
                country = parts[0].strip()
                region = parts[1].strip()
                display_location = f"{region}, {country}"
            else:
                display_location = parts[0].strip()
        
        record_copy['display_location'] = display_location
        records_with_est.append(record_copy)
    
    # 只取最近100条记录用于表格显示
    recent_records = records_with_est[:100]
    
    # 计算统计数据
    unique_users = len(set(r['email'] for r in records_with_est))
    total_logins = len(records_with_est)
    failed_logins = sum(1 for r in records_with_est if not r['successful'])
    
    # 计算今日登录数（使用EST时间）
    today = datetime.utcnow() + utc_to_est_offset
    today_start = datetime(today.year, today.month, today.day, 0, 0, 0) - utc_to_est_offset  # 转回UTC
    today_logins = sum(1 for r in records_with_est if r['login_time'] >= today_start)
    
    # 准备统计数据
    stats = {
        'unique_users': unique_users,
        'total_logins': total_logins,
        'failed_logins': failed_logins,
        'today_logins': today_logins
    }
    
    # 准备最近30天的登录趋势数据
    trend_data = {'dates': [], 'counts': []}
    
    # 生成过去30天的日期列表（EST时区）
    end_date = today
    start_date = end_date - timedelta(days=29)
    current_date = start_date
    
    while current_date <= end_date:
        date_str = current_date.strftime('%Y-%m-%d')
        trend_data['dates'].append(date_str)
        
        # 计算当天的登录数量（EST时区）
        day_start = datetime(current_date.year, current_date.month, current_date.day, 0, 0, 0) - utc_to_est_offset
        day_end = day_start + timedelta(days=1)
        day_count = sum(1 for r in records_with_est 
                        if r['login_time'] >= day_start and r['login_time'] < day_end)
        
        trend_data['counts'].append(day_count)
        current_date += timedelta(days=1)
    
    # 准备按小时的登录分布数据
    time_data = {'hours': [], 'counts': []}
    hour_counts = [0] * 24
    
    for record in records_with_est:
        login_time = record['login_time'] + utc_to_est_offset
        hour = login_time.hour
        hour_counts[hour] += 1
    
    for hour in range(24):
        # 格式化小时显示，如 "00:00", "01:00", ...
        hour_str = f"{hour:02d}:00"
        time_data['hours'].append(hour_str)
        time_data['counts'].append(hour_counts[hour])
    
    # 准备地理位置分布数据
    geo_data = {'countries': [], 'counts': []}
    country_counts = {}
    
    for record in records_with_est:
        if record['login_location'] and ',' in record['login_location']:
            country = record['login_location'].split(',')[0].strip()
            if country in country_counts:
                country_counts[country] += 1
            else:
                country_counts[country] = 1
        else:
            country = "未知/Unknown"
            if country in country_counts:
                country_counts[country] += 1
            else:
                country_counts[country] = 1
    
    # 按登录次数排序国家，并限制为前10个
    sorted_countries = sorted(country_counts.items(), key=lambda x: x[1], reverse=True)
    top_countries = sorted_countries[:10]
    
    for country, count in top_countries:
        geo_data['countries'].append(country)
        geo_data['counts'].append(count)
    
    # 如果超过10个国家，将剩余的合并为"其他"
    if len(sorted_countries) > 10:
        others_count = sum(count for _, count in sorted_countries[10:])
        if g.language == 'en':
            geo_data['countries'].append("Others")
        else:
            geo_data['countries'].append("其他")
        geo_data['counts'].append(others_count)
    
    return render_template('login_dashboard.html', 
                          records=recent_records, 
                          stats=stats, 
                          trend_data=trend_data,
                          time_data=time_data,
                          geo_data=geo_data)

@app.route('/calculate', methods=['POST'])
def calculate():
    """Handle the calculation request and return results as JSON"""
    # Check authentication for API endpoints
    if not session.get('email'):
        return jsonify({
            'success': False,
            'error': 'Authentication required'
        }), 401
        
    try:
        # Handle both JSON and form data
        if request.is_json:
            data = request.get_json()
            logging.info(f"Received calculate request JSON data: {data}")
        else:
            data = request.form
            logging.info(f"Received calculate request form data: {data}")
        
        # 初始化错误收集列表
        input_errors = []
        
        # Get values from the request data with detailed error handling
        try:
            hashrate = float(data.get('hashrate', 0))
        except (ValueError, TypeError) as e:
            error_msg = f"无效的算力值: {data.get('hashrate')}"
            logging.error(f"{error_msg} - {str(e)}")
            input_errors.append(error_msg)
            hashrate = 0
            
        hashrate_unit = data.get('hashrate_unit', 'TH/s')
        
        try:
            power_consumption = float(data.get('power_consumption', 0))
        except (ValueError, TypeError) as e:
            error_msg = f"无效的功耗值: {data.get('power_consumption')}"
            logging.error(f"{error_msg} - {str(e)}")
            input_errors.append(error_msg)
            power_consumption = 0
            
        try:
            electricity_cost = float(data.get('electricity_cost', 0))
        except (ValueError, TypeError) as e:
            error_msg = f"无效的电费值: {data.get('electricity_cost')}"
            logging.error(f"{error_msg} - {str(e)}")
            input_errors.append(error_msg)
            electricity_cost = 0.05  # Default value
            
        try:
            client_electricity_cost = float(data.get('client_electricity_cost', 0))
        except (ValueError, TypeError) as e:
            error_msg = f"无效的客户电费值: {data.get('client_electricity_cost')}"
            logging.error(f"{error_msg} - {str(e)}")
            input_errors.append(error_msg)
            client_electricity_cost = 0
            
        try:
            btc_price = float(data.get('btc_price', 0))
        except (ValueError, TypeError) as e:
            error_msg = f"无效的BTC价格值: {data.get('btc_price')}"
            logging.error(f"{error_msg} - {str(e)}")
            input_errors.append(error_msg)
            btc_price = 0
            
        use_real_time = data.get('use_real_time_data', data.get('use_real_time')) in ['on', True, 'true', '1']
        miner_model = data.get('miner_model')
        
        try:
            miner_count = int(data.get('count', data.get('miner_count', 1)))
        except (ValueError, TypeError) as e:
            error_msg = f"无效的矿机数量: {data.get('count', data.get('miner_count'))}"
            logging.error(f"{error_msg} - {str(e)}")
            input_errors.append(error_msg)
            miner_count = 1
            
        try:
            site_power_mw = float(data.get('site_power_mw', 1.0))
        except (ValueError, TypeError) as e:
            error_msg = f"无效的站点功率值: {data.get('site_power_mw')}"
            logging.error(f"{error_msg} - {str(e)}")
            input_errors.append(error_msg)
            site_power_mw = 1.0
            
        # 从表单获取总算力和总功耗值
        try:
            total_hashrate = float(request.form.get('total_hashrate') or 0)
        except (ValueError, TypeError) as e:
            logging.info(f"表单中的总算力格式无效或未提供: {request.form.get('total_hashrate')} - {str(e)}")
            total_hashrate = 0
            
        try:
            total_power = float(request.form.get('total_power') or 0)
        except (ValueError, TypeError) as e:
            logging.info(f"表单中的总功耗格式无效或未提供: {request.form.get('total_power')} - {str(e)}")
            total_power = 0
            
        # 如果没有提供或无效，根据矿机型号和数量计算总算力和总功耗
        if (total_hashrate <= 0 or total_power <= 0) and miner_model:
            # 使用矿机数据
            if miner_model in MINER_DATA:
                miner_data = MINER_DATA[miner_model]
                if total_hashrate <= 0:
                    total_hashrate = miner_data['hashrate'] * miner_count
                    logging.info(f"已计算总算力: {total_hashrate} TH/s")
                
                if total_power <= 0:
                    total_power = miner_data['power_watt'] * miner_count
                    logging.info(f"已计算总功耗: {total_power} W")
            else:
                # 如果没有找到矿机模型，使用表单中的单位hashrate和power_consumption来计算
                if total_hashrate <= 0 and hashrate > 0:
                    total_hashrate = hashrate * miner_count
                    logging.info(f"已根据单位算力计算总算力: {total_hashrate} TH/s")
                
                if total_power <= 0 and power_consumption > 0:
                    total_power = power_consumption * miner_count
                    logging.info(f"已根据单位功耗计算总功耗: {total_power} W")
                    
        logging.info(f"计算使用的总算力: {total_hashrate} TH/s, 总功耗: {total_power} W")
            
        # 如果有输入错误，返回具体的错误信息
        if input_errors:
            error_message = "输入参数无效: " + ", ".join(input_errors)
            logging.error(error_message)
            return jsonify({
                'success': False,
                'error': error_message
            }), 400
            
        try:
            curtailment_str = request.form.get('curtailment', '0')
            curtailment = float(curtailment_str)
            logging.info(f"解析限电率: 原始值='{curtailment_str}'，转换后={curtailment}%")
        except ValueError as e:
            logging.error(f"Invalid curtailment value: {request.form.get('curtailment')} - {str(e)}")
            curtailment = 0
            
        # 获取关机策略（如果有限电）
        shutdown_strategy = "efficiency"  # 默认按效率关机
        if curtailment > 0:
            strategy = request.form.get('shutdown_strategy')
            if strategy in ['efficiency', 'proportional', 'random']:
                shutdown_strategy = strategy
            logging.info(f"电力削减关机策略: {shutdown_strategy}")
            
        try:
            maintenance_fee = float(request.form.get('maintenance_fee', 0))
        except ValueError as e:
            logging.error(f"Invalid maintenance fee value: {request.form.get('maintenance_fee')} - {str(e)}")
            maintenance_fee = 0
            
        # 获取投资金额参数
        try:
            host_investment = float(request.form.get('host_investment', 0))
        except ValueError as e:
            logging.error(f"Invalid host investment value: {request.form.get('host_investment')} - {str(e)}")
            host_investment = 0
            
        try:
            client_investment = float(request.form.get('client_investment', 0))
        except ValueError as e:
            logging.error(f"Invalid client investment value: {request.form.get('client_investment')} - {str(e)}")
            client_investment = 0
        
        logging.info(f"Calculate request: model={miner_model}, count={miner_count}, real_time={use_real_time}, "
                     f"site_power={site_power_mw}MW, curtailment={curtailment}%, "
                     f"host_investment=${host_investment}, client_investment=${client_investment}")
        
        # Convert hashrate to TH/s for calculation
        if hashrate_unit == 'PH/s':
            hashrate = hashrate * 1000
        elif hashrate_unit == 'EH/s':
            hashrate = hashrate * 1000000
                
        # 处理全网算力来源选择
        hashrate_source = request.form.get('hashrate_source', 'api')
        manual_hashrate = None
        
        if hashrate_source == 'manual':
            try:
                manual_hashrate = float(request.form.get('manual_hashrate', 800.0))
                logging.info(f"使用手动输入的全网算力: {manual_hashrate} EH/s")
            except ValueError:
                logging.warning("手动全网算力输入无效，回退到API获取")
                hashrate_source = 'api'
                manual_hashrate = None
        
        # 添加错误处理来确保即使API调用失败计算仍能继续
        try:
            # 计算挖矿盈利能力 - 使用计算得到的总算力和总功耗
            result = calculate_mining_profitability(
                hashrate=total_hashrate if total_hashrate > 0 else hashrate,  # 使用计算出的总算力而不是单位算力
                power_consumption=total_power if total_power > 0 else power_consumption,  # 使用计算出的总功耗而不是单位功耗
                electricity_cost=electricity_cost,
                client_electricity_cost=client_electricity_cost,
                btc_price=btc_price if not use_real_time else None,
                use_real_time_data=use_real_time,
                miner_model=miner_model,
                miner_count=1,  # 设为1因为我们已经使用总算力和总功耗
                site_power_mw=site_power_mw,
                curtailment=curtailment,
                shutdown_strategy=shutdown_strategy,  # 新增参数：关机策略
                host_investment=host_investment,
                client_investment=client_investment,
                maintenance_fee=maintenance_fee,
                manual_network_hashrate=manual_hashrate  # 新增参数：手动全网算力
            )
        except Exception as calc_error:
            # 如果计算过程中出错，使用基本估算
            logging.error(f"计算过程中出错，使用基本估算: {calc_error}")
            
            # 创建一个基本结果对象
            if miner_model and miner_model in MINER_DATA:
                # 获取基本参数
                miner_specs = MINER_DATA[miner_model]
                total_hashrate = miner_specs["hashrate"] * miner_count
                total_power = miner_specs["power_watt"] * miner_count
                
                # 使用简单估算
                daily_btc = total_hashrate * 0.00000200  # 估算每TH每天产出
                monthly_btc = daily_btc * 30.5
                monthly_power_kwh = total_power * 24 * 30.5 / 1000
                
                # 估算收入和成本
                price_to_use = btc_price if not use_real_time else 80000
                monthly_revenue = monthly_btc * price_to_use
                monthly_cost = monthly_power_kwh * electricity_cost
                
                # 确保维护费被考虑进利润计算
                monthly_profit = monthly_revenue - monthly_cost - maintenance_fee
                
                result = {
                    'success': True,
                    'estimation_note': '由于实时API数据获取失败，使用估算值',
                    'btc_mined': {
                        'daily': daily_btc,
                        'monthly': monthly_btc,
                        'yearly': monthly_btc * 12
                    },
                    'inputs': {
                        'hashrate': total_hashrate,
                        'power_consumption': total_power,
                        'electricity_cost': electricity_cost,
                        'miner_count': miner_count
                    },
                    'network_data': {
                        'btc_price': price_to_use,
                        'network_difficulty': 119.12,  # T
                        'network_hashrate': 700,  # EH/s
                        'block_reward': 3.125
                    },
                    'profit': {
                        'daily': monthly_profit / 30.5,
                        'monthly': monthly_profit,
                        'yearly': monthly_profit * 12
                    }
                }
            else:
                # 如果连矿机型号都无效，则返回错误
                return jsonify({
                    'success': False,
                    'error': '无法计算结果且矿机型号无效'
                }), 400
        
        # Add maintenance fee to the result
        if maintenance_fee > 0:
            result['maintenance_fee'] = {
                'monthly': maintenance_fee,
                'daily': maintenance_fee / 30.5,
                'yearly': maintenance_fee * 12
            }
        
        # 根据用户角色过滤返回数据
        user_role = session.get('role')
        logging.info(f"计算请求的用户角色: {user_role}")
        
        # 如果不是允许的角色（owner、admin或mining_site），则移除矿场主相关敏感数据
        if user_role not in ['owner', 'admin', 'mining_site']:
            logging.info("用户没有矿场主权限，过滤敏感数据")
            
            # 保留必要数据，移除敏感数据
            filtered_result = {
                'success': True,  # 确保添加成功标志
                'timestamp': result.get('timestamp', datetime.now().isoformat()),
                'btc_mined': result.get('btc_mined', {}),
                'client_electricity_cost': result.get('client_electricity_cost', {}),
                'client_profit': result.get('client_profit', {}),
                'inputs': result.get('inputs', {}),
                'network_data': result.get('network_data', {}),
                'revenue': result.get('revenue', {}),  # 添加收入信息
                'break_even': {
                    'btc_price': result.get('break_even', {}).get('btc_price', 0),
                    'electricity_cost': result.get('break_even', {}).get('electricity_cost', 0)  # 添加盈亏平衡电价给客户
                },
                'optimization': result.get('optimization', {})  # 添加矿机运行状态数据
            }
            
            # 保留客户ROI数据，这对客户用户是可见的
            if 'roi' in result and 'client' in result['roi']:
                filtered_result['roi'] = {
                    'client': result['roi']['client']
                }
            
            # 如果结果中有估算注释，也添加到过滤结果中
            if 'estimation_note' in result:
                filtered_result['estimation_note'] = result['estimation_note']
            
            # 返回过滤后的结果
            return jsonify(filtered_result)
            
        # 记录网络数据快照（在成功计算后）
        try:
            if use_real_time and result.get('success', True):
                # 使用计算结果中的网络数据记录快照
                network_data = result.get('network_data', {})
                if network_data:
                    # 转换为EST时间
                    utc_time = datetime.utcnow()
                    est_time = pytz.utc.localize(utc_time).astimezone(pytz.timezone('US/Eastern'))
                    
                    snapshot = NetworkSnapshot(
                        btc_price=network_data.get('btc_price', 0),
                        network_difficulty=network_data.get('network_difficulty', 0),
                        network_hashrate=network_data.get('network_hashrate', 0),
                        block_reward=network_data.get('block_reward', 3.125),
                        recorded_at=est_time.replace(tzinfo=None)
                    )
                    db.session.add(snapshot)
                    db.session.commit()
                    logging.info(f"网络快照已记录: BTC=${network_data.get('btc_price')}, 难度={network_data.get('network_difficulty')}T")
        except Exception as snapshot_error:
            logging.error(f"记录网络快照失败: {snapshot_error}")
            # 不影响主要计算流程
        
        # 对于有权限的用户，返回完整结果
        return jsonify(result)
        
    except ValueError as e:
        logging.error(f"Invalid input: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Please ensure all inputs are valid numbers.'
        }), 400
    except Exception as e:
        logging.error(f"Error calculating profitability: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'An error occurred during calculation. Please try again.'
        }), 500

# API routes with standardized URL patterns
@app.route('/api/get_btc_price', methods=['GET'])
@app.route('/api/btc-price', methods=['GET'])
@app.route('/api/btc_price', methods=['GET'])
@app.route('/get_btc_price', methods=['GET'])
@app.route('/btc_price', methods=['GET'])
def get_btc_price():
    """Get the current Bitcoin price from API"""
    # Check authentication for API endpoints
    if not session.get('email'):
        return jsonify({
            'success': False,
            'error': 'Authentication required'
        }), 401
        
    try:
        current_btc_price = get_real_time_btc_price()
        return jsonify({
            'success': True,
            'price': current_btc_price
        })
    except Exception as e:
        logging.error(f"Error fetching BTC price: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Could not fetch BTC price.'
        }), 500

@app.route('/api/get_network_stats', methods=['GET'])
@app.route('/api/network-stats', methods=['GET'])
@app.route('/api/network_stats', methods=['GET'])
@app.route('/get_network_stats', methods=['GET'])
@app.route('/network_stats', methods=['GET'])
def get_network_stats():
    """Get current Bitcoin network statistics using smart API switching"""
    # Check authentication for API endpoints
    if not session.get('email'):
        return jsonify({
            'success': False,
            'error': 'Authentication required'
        }), 401
        
    try:
        from coinwarz_api import get_enhanced_network_data
        
        # 获取增强网络数据（自动切换API）
        network_data = get_enhanced_network_data()
        
        if network_data and network_data.get('btc_price'):
            response_data = {
                'success': True,
                'price': network_data['btc_price'],
                'difficulty': network_data['difficulty'] / 10**12 if network_data['difficulty'] > 1000 else network_data['difficulty'],
                'hashrate': network_data['hashrate'],
                'block_reward': network_data['block_reward'],
                'data_source': network_data['data_source'],
                'profit_ratio': network_data.get('profit_ratio', 100),
                'health_status': network_data.get('health_status', 'Unknown'),
                'api_calls_remaining': network_data.get('api_calls_remaining', 0)
            }
            
            # 添加详细的API状态信息
            if 'hashrate_source' in network_data:
                response_data['hashrate_source'] = network_data['hashrate_source']
            if 'fallback_reason' in network_data:
                response_data['fallback_reason'] = network_data['fallback_reason']
            if 'coinwarz_hashrate' in network_data and 'blockchain_hashrate' in network_data:
                response_data['hashrate_comparison'] = {
                    'coinwarz': network_data['coinwarz_hashrate'],
                    'blockchain': network_data['blockchain_hashrate']
                }
            
            return jsonify(response_data)
        else:
            # 最后的备选方案 - 使用blockchain.info直接获取
            from mining_calculator import get_real_time_btc_price, get_real_time_difficulty, get_real_time_btc_hashrate, get_real_time_block_reward
            
            price = get_real_time_btc_price()
            difficulty = get_real_time_difficulty()
            hashrate = get_real_time_btc_hashrate()
            block_reward = get_real_time_block_reward()
            
            return jsonify({
                'success': True,
                'price': price,
                'difficulty': difficulty / 10**12 if difficulty and difficulty > 1000 else difficulty,
                'hashrate': hashrate,
                'block_reward': block_reward,
                'data_source': 'blockchain.info (direct)',
                'health_status': 'Backup Active',
                'api_calls_remaining': 0,
                'fallback_reason': 'All enhanced APIs unavailable'
            })
        
    except Exception as e:
        logging.error(f"获取网络统计数据时发生错误: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve network statistics',
            'data_source': 'error',
            'health_status': 'Error',
            'api_calls_remaining': 0
        }), 500

@app.route('/api/get_sha256_mining_comparison', methods=['GET'])
@app.route('/api/sha256_mining_comparison', methods=['GET'])
@app.route('/api/sha256-comparison', methods=['GET'])
@app.route('/get_sha256_mining_comparison', methods=['GET'])
@app.route('/mining/sha256_comparison', methods=['GET'])
def get_sha256_mining_comparison():
    """Get SHA-256 mining profitability comparison from CoinWarz"""
    # Check authentication for API endpoints
    if not session.get('email'):
        return jsonify({
            'success': False,
            'error': 'Authentication required'
        }), 401
        
    try:
        from coinwarz_api import get_sha256_coins_comparison, check_coinwarz_api_status
        
        # 检查API状态（移除严格检查，允许降级服务）
        api_status = check_coinwarz_api_status()
        if not api_status or not api_status.get('Approved'):
            # 返回空数据而不是503错误
            return jsonify({
                'success': True,
                'coins': [],
                'data': [],
                'error': 'CoinWarz API temporarily unavailable',
                'api_calls_remaining': 0,
                'daily_calls_remaining': 0
            })
        
        # 获取SHA-256币种对比数据
        comparison_data = get_sha256_coins_comparison()
        
        if comparison_data:
            return jsonify({
                'success': True,
                'coins': comparison_data,  # 修复：添加coins字段
                'data': comparison_data,   # 保持向后兼容
                'api_calls_remaining': api_status.get('ApiUsageAvailable', 0),
                'daily_calls_remaining': api_status.get('DailyUsageAvailable', 0)
            })
        else:
            return jsonify({
                'success': False,
                'coins': [],  # 修复：空数据时也返回coins字段
                'error': 'Unable to fetch mining comparison data'
            }), 500
            
    except Exception as e:
        logging.error(f"获取SHA-256挖矿对比数据时发生错误: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error while fetching comparison data'
        }), 500

@app.route('/api/get_miners', methods=['GET'])
@app.route('/api/miners', methods=['GET'])
@app.route('/get_miners', methods=['GET'])
@app.route('/miners', methods=['GET'])
def get_miners():
    """Get the list of available miner models and their specifications"""
    # Check authentication for API endpoints
    if not session.get('email'):
        return jsonify({
            'success': False,
            'error': 'Authentication required'
        }), 401
        
    try:
        # 确保使用的是从mining_calculator导入的MINER_DATA
        miners_list = []
        # 计算效率时使用正确的公式：W/TH（能效比）
        for name, specs in MINER_DATA.items():
            miners_list.append({
                'name': name,
                'hashrate': specs['hashrate'],  # TH/s
                'power_consumption': specs['power_watt'],  # W (renamed for consistency)
                'power_watt': specs['power_watt'],  # W (keep for backward compatibility)
                'efficiency': round(specs['power_watt'] / specs['hashrate'], 2)  # W/TH
            })
        
        return jsonify({
            'success': True,
            'miners': miners_list
        })
    except Exception as e:
        logging.error(f"Error fetching miners data: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Could not fetch miners data.'
        }), 500

# 用户访问管理系统路由
@app.route('/admin/user_access')
@login_required
def user_access():
    """管理员管理用户访问权限"""
    # 只允许owner或admin角色访问
    if not has_role(['owner', 'admin']):
        flash('您没有权限访问此页面，需要管理员或拥有者权限', 'danger')
        return redirect(url_for('index'))
    
    # 获取所有用户
    users = UserAccess.query.order_by(UserAccess.created_at.desc()).all()
    
    # 记录当前用户角色（用于调试）
    current_user_role = session.get('role', '未设置')
    logging.info(f"当前用户角色: {current_user_role}")
    logging.info(f"所有session数据: {session}")
    
    return render_template('user_access.html', users=users)

@app.route('/admin/user_access/add', methods=['POST'])
@login_required
def add_user_access():
    """添加新用户访问权限"""
    # 只允许owner或admin角色访问
    if not has_role(['owner', 'admin']):
        flash('您没有权限访问此页面，需要管理员或拥有者权限', 'danger')
        return redirect(url_for('index'))
    
    try:
        # 获取表单数据
        name = request.form['name']
        email = request.form['email']
        
        try:
            access_days = int(request.form['access_days'])
        except (ValueError, KeyError):
            access_days = 30  # 默认30天
            
        company = request.form.get('company')
        position = request.form.get('position')
        notes = request.form.get('notes')
        role = request.form.get('role', 'guest')  # 获取角色参数，默认为矿场客人
        
        # 检查角色是否有效
        valid_roles = ['owner', 'admin', 'mining_site', 'guest']
        if role not in valid_roles:
            role = 'guest'  # 如果不是有效角色，默认为矿场客人
            
        # 根据当前用户角色限制可以创建的角色
        current_user_role = get_user_role(session.get('email'))
        # 如果当前用户是管理员，不能创建owner角色
        if current_user_role == 'admin' and role == 'owner':
            flash('管理员不能创建拥有者角色用户', 'warning')
            role = 'admin'  # 将角色降级为管理员
            
        # 检查邮箱是否已存在
        existing_user = UserAccess.query.filter_by(email=email).first()
        if existing_user:
            flash(f'邮箱 {email} 已存在，请使用其他邮箱', 'warning')
            return redirect(url_for('user_access'))
        
        # 创建新用户
        new_user = UserAccess(
            name=name,
            email=email,
            access_days=access_days,
            company=company,
            position=position,
            notes=notes,
            role=role
        )
        
        # 保存到数据库
        db.session.add(new_user)
        db.session.commit()
        
        # 获取角色的中文名称
        if role == "owner":
            role_name = "拥有者"
        elif role == "admin":
            role_name = "管理员"
        elif role == "mining_site":
            role_name = "矿场管理"
        else:
            role_name = "矿场客人"
        flash(f'用户 {name} ({email}) 已成功添加，角色为"{role_name}"，访问权限 {access_days} 天', 'success')
    except Exception as e:
        db.session.rollback()
        logging.error(f"添加用户访问权限时出错: {str(e)}")
        flash(f'添加用户失败: {str(e)}', 'danger')
    
    return redirect(url_for('user_access'))

@app.route('/admin/user_access/extend/<int:user_id>/<int:days>', methods=['POST'])
@login_required
def extend_user_access(user_id, days):
    """延长用户访问权限"""
    # 只允许owner或admin角色访问
    if not has_role(['owner', 'admin']):
        flash('您没有权限访问此页面，需要管理员或拥有者权限', 'danger')
        return redirect(url_for('index'))
    
    try:
        # 查找用户
        user = UserAccess.query.get_or_404(user_id)
        
        # 延长权限
        user.extend_access(days)
        db.session.commit()
        
        flash(f'用户 {user.name} 的访问权限已延长 {days} 天', 'success')
    except Exception as e:
        db.session.rollback()
        logging.error(f"延长用户访问权限时出错: {str(e)}")
        flash(f'延长用户访问权限失败: {str(e)}', 'danger')
    
    return redirect(url_for('user_access'))

@app.route('/admin/user_access/revoke/<int:user_id>', methods=['POST'])
@login_required
def revoke_user_access(user_id):
    """撤销用户访问权限"""
    # 只允许owner或admin角色访问
    if not has_role(['owner', 'admin']):
        flash('您没有权限访问此页面，需要管理员或拥有者权限', 'danger')
        return redirect(url_for('index'))
    
    try:
        # 查找用户
        user = UserAccess.query.get_or_404(user_id)
        
        # 撤销权限
        user.revoke_access()
        db.session.commit()
        
        flash(f'用户 {user.name} 的访问权限已撤销', 'warning')
    except Exception as e:
        db.session.rollback()
        logging.error(f"撤销用户访问权限时出错: {str(e)}")
        flash(f'撤销用户访问权限失败: {str(e)}', 'danger')
    
    return redirect(url_for('user_access'))

@app.route('/admin/migrate_to_crm')
@login_required
def migrate_to_crm():
    """将用户访问权限数据迁移到CRM系统中"""
    # 只允许拥有者角色访问
    if not has_role(['owner']):
        flash('您没有权限访问此页面，需要拥有者权限', 'danger')
        return redirect(url_for('index'))
    
    try:
        # 获取所有用户记录
        users = UserAccess.query.all()
        logging.info(f"开始迁移 {len(users)} 个用户数据到CRM系统")
        
        # 迁移计数器
        migrated_count = 0
        already_exists_count = 0
        
        # 遍历每个用户并迁移
        for user in users:
            # 检查是否已经存在同名/同邮箱的客户
            existing_customer = Customer.query.filter(
                (Customer.email == user.email) | 
                ((Customer.name == user.name) & (Customer.company == user.company))
            ).first()
            
            if existing_customer:
                logging.info(f"客户已存在: {user.name} ({user.email})")
                already_exists_count += 1
                continue
            
            # 创建新客户记录
            customer = Customer(
                name=user.name,
                company=user.company,
                email=user.email,
                customer_type="企业" if user.company else "个人",
                tags="已迁移用户,授权用户",
                created_at=user.created_at
            )
            db.session.add(customer)
            db.session.flush()  # 获取ID而不提交事务
            
            # 创建主要联系人
            contact = Contact(
                customer_id=customer.id,
                name=user.name,
                email=user.email,
                position=user.position,
                primary=True,
                notes=f"从用户访问系统迁移 - 角色: {user.role}"
            )
            db.session.add(contact)
            
            # 创建一个初始商机记录用户访问权限
            lead = Lead(
                customer_id=customer.id,
                title=f"{user.name} 访问授权",
                status="QUALIFIED" if user.has_access else "LOST",  # 访问has_access属性
                source="系统迁移",
                estimated_value=0.0,  # 授权访问没有直接价值
                assigned_to="系统管理员",
                description=f"用户访问授权信息 - 创建于 {user.created_at.strftime('%Y-%m-%d')}, "
                          f"过期于 {user.expires_at.strftime('%Y-%m-%d')}。"
                          f"\n备注: {user.notes if user.notes else '无'}"
            )
            db.session.add(lead)
            
            # 记录一条活动
            activity = Activity(
                customer_id=customer.id,
                lead_id=lead.id,
                type="创建",
                summary="从用户访问系统迁移",
                details=f"用户数据已从访问管理系统迁移到CRM系统。\n原始角色: {user.role}\n"
                        f"访问期限: {user.access_days} 天\n"
                        f"到期日期: {user.expires_at.strftime('%Y-%m-%d')}\n"
                        f"最后登录: {user.last_login.strftime('%Y-%m-%d') if user.last_login else '从未登录'}",
                created_by="系统管理员"
            )
            db.session.add(activity)
            
            # 提交到数据库
            db.session.commit()
            
            logging.info(f"成功迁移用户: {user.name} ({user.email}) -> 客户ID: {customer.id}")
            migrated_count += 1
            
        # 设置成功消息
        flash(f'迁移完成！{migrated_count} 个用户已迁移，{already_exists_count} 个用户已跳过（已存在）。', 'success')
        return redirect(url_for('crm.dashboard'))
    
    except Exception as e:
        db.session.rollback()
        logging.error(f"用户数据迁移失败: {str(e)}")
        flash(f'迁移失败: {str(e)}', 'danger')
        return redirect(url_for('user_access'))

@app.route('/api/profit-chart-data', methods=['POST'])
@app.route('/profit_chart_data', methods=['POST'])
@login_required
def get_profit_chart_data():
    """Generate profit chart data for visualization"""
    try:
        # 添加详细日志以帮助调试
        start_time = time.time()
        
        # 记录完整的请求数据
        logging.info(f"Profit chart data request received with data: {request.form}")
        
        # Get parameters from request with detailed error handling
        miner_model = request.form.get('miner_model')
        logging.info(f"Miner model from request: {miner_model}")
        
        # Validate miner model
        if not miner_model:
            logging.error("No miner model provided in request")
            return jsonify({
                'success': False,
                'error': 'Please select a miner model.'
            }), 400
            
        if miner_model not in MINER_DATA:
            logging.error(f"Invalid miner model: {miner_model} not in available models: {list(MINER_DATA.keys())}")
            return jsonify({
                'success': False,
                'error': f"Selected miner model '{miner_model}' is not valid. Please select from available models."
            }), 400
        
        # Parse miner count with error handling
        try:
            miner_count = int(request.form.get('miner_count', 1))
            if miner_count <= 0:
                logging.warning(f"Invalid miner count: {miner_count}, using default of 1")
                miner_count = 1
        except (ValueError, TypeError) as e:
            logging.error(f"Error parsing miner count: {request.form.get('miner_count')} - {str(e)}")
            miner_count = 1
            
        # Parse client electricity cost with error handling
        try:
            client_electricity_cost = float(request.form.get('client_electricity_cost', 0))
        except (ValueError, TypeError) as e:
            logging.error(f"Error parsing client electricity cost: {request.form.get('client_electricity_cost')} - {str(e)}")
            client_electricity_cost = 0
        
        # 禁用缓存以避免使用旧的数据（此前的缓存可能包含错误数据）
        # 生成新的价格和电费成本范围
        try:
            current_btc_price = get_real_time_btc_price()
            logging.info(f"Current BTC price fetched: ${current_btc_price}")
        except Exception as e:
            logging.error(f"Error getting real-time BTC price: {str(e)}, using default")
            current_btc_price = 50000  # 使用默认值
            
        # 创建价格和电费点的网格(5x5)
        btc_price_factors = [0.5, 0.75, 1.0, 1.25, 1.5]
        btc_prices = [round(current_btc_price * factor) for factor in btc_price_factors]
        electricity_costs = [0.02, 0.04, 0.06, 0.08, 0.10]
        
        logging.info(f"Generating profit chart for {miner_model} with {miner_count} miners")
        logging.info(f"Using BTC prices: {btc_prices}")
        logging.info(f"Using electricity costs: {electricity_costs}")
        
        # 获取热力图数据
        try:
            # 尝试生成热力图数据
            chart_data = generate_profit_chart_data(
                miner_model=miner_model,
                electricity_costs=electricity_costs,
                btc_prices=btc_prices,
                miner_count=miner_count,
                client_electricity_cost=client_electricity_cost if client_electricity_cost > 0 else None
            )
            
            # 验证返回的数据结构
            if not chart_data.get('success', False):
                error_msg = chart_data.get('error', 'Unknown error in chart data generation')
                logging.error(f"Chart data generation failed: {error_msg}")
                return jsonify({
                    'success': False,
                    'error': error_msg
                }), 400
                
            # 验证profit_data是否为数组且非空
            profit_data = chart_data.get('profit_data', [])
            if not isinstance(profit_data, list) or len(profit_data) == 0:
                logging.error("Generated chart data has empty or invalid profit_data")
                return jsonify({
                    'success': False,
                    'error': 'Generated chart data is invalid (empty profit data)'
                }), 500
            
            # 验证和清理数据
            cleaned_data = []
            for point in profit_data:
                # 验证数据点结构完整性
                if not isinstance(point, dict):
                    logging.warning(f"Skipping invalid data point (not a dict): {point}")
                    continue
                
                # 验证所有字段存在且为数字
                try:
                    if (isinstance(point.get('btc_price'), (int, float)) and 
                        isinstance(point.get('electricity_cost'), (int, float)) and 
                        isinstance(point.get('monthly_profit'), (int, float))):
                        
                        # 添加有效数据点
                        cleaned_data.append({
                            'btc_price': float(point['btc_price']),
                            'electricity_cost': float(point['electricity_cost']),
                            'monthly_profit': float(point['monthly_profit'])
                        })
                    else:
                        logging.warning(f"Skipping data point with invalid field types: {point}")
                except Exception as e:
                    logging.error(f"Error processing data point {point}: {str(e)}")
            
            # 如果没有有效数据点
            if len(cleaned_data) == 0:
                logging.error("No valid data points after validation")
                return jsonify({
                    'success': False,
                    'error': 'No valid profit data points could be generated'
                }), 500
                
            # 替换清理后的数据
            chart_data['profit_data'] = cleaned_data
            
            # 验证利润值是否有变化
            unique_profits = set(round(item['monthly_profit'], 2) for item in cleaned_data)
            if len(unique_profits) <= 1:
                logging.warning(f"All profit values are identical ({list(unique_profits)[0] if unique_profits else 'N/A'}), data may be incorrect")
                
            # 记录最终有效数据点数量
            logging.info(f"Validated profit chart data: {len(cleaned_data)} valid points out of {len(profit_data)} original points")
                
            elapsed_time = time.time() - start_time
            logging.info(f"Chart data generated in {elapsed_time:.2f} seconds with {len(profit_data)} data points")
            
            return jsonify(chart_data)
            
        except Exception as e:
            logging.error(f"Error generating chart data: {str(e)}")
            logging.error(traceback.format_exc())
            return jsonify({
                'success': False,
                'error': f'Error generating chart data: {str(e)}'
            }), 500
    except Exception as e:
        logging.error(f"Unhandled exception in profit chart data generation: {str(e)}")
        logging.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500

# API测试工具已移除以简化代码

# 电力管理系统功能已移除以简化代码

# 矿场客户管理
@app.route('/mine/customers')
@login_required
def mine_customer_management():
    """矿场主管理自己的客户"""
    # 只允许mining_site角色访问
    if not has_role(['mining_site']):
        flash('您没有权限访问此页面，需要矿场主权限', 'danger')
        return redirect(url_for('index'))
    
    # 获取当前用户ID
    user_id = session.get('user_id')
    
    # 查询该矿场主创建的所有客户
    users = UserAccess.query.filter_by(
        created_by_id=user_id, 
        role='guest'
    ).order_by(UserAccess.created_at.desc()).all()
    
    return render_template('mine_customer_management.html', users=users)

@app.route('/mine/customers/add', methods=['GET', 'POST'])
@login_required
def add_mine_customer():
    """矿场主添加新客户"""
    # 只允许mining_site角色访问
    if not has_role(['mining_site']):
        flash('您没有权限访问此页面，需要矿场主权限', 'danger')
        return redirect(url_for('index'))
    
    # 获取当前矿场主信息
    user_id = session.get('user_id')
    user_email = session.get('email')
    
    # 调试日志
    logging.info(f"当前登录用户: {user_email}, ID: {user_id}, 角色: {session.get('role')}")
    if user_id is None:
        logging.warning(f"用户ID未设置! 这会导致客户关联失败，请重新登录。会话数据: {session}")
    
    if request.method == 'POST':
        # 获取表单数据
        name = request.form['name']
        email = request.form['email']
        
        # 检查邮箱是否已存在
        existing_user = UserAccess.query.filter_by(email=email).first()
        if existing_user:
            flash(f'邮箱 {email} 已存在', 'danger')
            return redirect(url_for('add_mine_customer'))
        
        # 检查是否授予计算器访问权限
        grant_calculator_access = request.form.get('grant_calculator_access') == 'yes'
        
        # 获取访问天数（如果不授予访问权限，将使用默认值，但不会实际创建用户）
        try:
            access_days = int(request.form['access_days']) if grant_calculator_access else 30
        except (ValueError, KeyError):
            access_days = 30  # 默认30天
            
        company = request.form.get('company')
        position = request.form.get('position')
        notes = request.form.get('notes')
        
        # 添加调试日志
        logging.info(f"添加客户: {name}, 邮箱: {email}, 创建者ID: {user_id}, 授予计算器访问: {grant_calculator_access}")
        
        # 只有当授予计算器访问权限时，才创建用户访问记录
        user_access = None
        if grant_calculator_access:
            # 创建用户访问记录
            user_access = UserAccess(
                name=name,
                email=email,
                access_days=access_days,
                company=company,
                position=position,
                notes=notes,
                role='guest'  # 客户角色设为guest
            )
            
            # 设置创建者ID（关联到当前矿场主）
            user_access.created_by_id = user_id
            
            # 保存到数据库
            try:
                db.session.add(user_access)
                db.session.commit()
                logging.info(f"成功保存客户 {name} 到数据库，新用户ID: {user_access.id}")
            except Exception as e:
                db.session.rollback()
                logging.error(f"保存客户记录时出错: {str(e)}")
                flash(f'添加客户时出错: {str(e)}', 'danger')
                return redirect(url_for('add_mine_customer'))
        
        # 创建CRM客户记录
        try:
            customer = Customer(
                name=name,
                company=company,
                email=email,
                created_by_id=user_id,  # 设置创建者ID
                customer_type='个人' if not company else '企业',
                mining_capacity=float(request.form.get('mining_capacity', 0)) if request.form.get('mining_capacity') else None
            )
            db.session.add(customer)
            db.session.commit()
            logging.info(f"成功创建CRM客户记录: {name}, ID: {customer.id}")
        except Exception as e:
            db.session.rollback()
            logging.error(f"创建CRM客户记录时出错: {str(e)}")
            flash(f'创建CRM客户记录时出错: {str(e)}', 'danger')
            return redirect(url_for('mine_customer_management'))
        
        # 创建默认的商机记录
        try:
            lead = Lead(
                customer_id=customer.id,
                title=f"{name} 访问授权",
                status=LeadStatus.NEW,
                source="矿场主添加",
                assigned_to=session.get('email'),
                assigned_to_id=user_id,
                created_by_id=user_id,
                description=f"由矿场主 {session.get('email')} 添加的客户。" + 
                          (f"授权使用挖矿计算器 {access_days} 天。" if grant_calculator_access else "未授权使用计算器。")
            )
            db.session.add(lead)
            db.session.commit()
            logging.info(f"成功创建商机记录: {name}, ID: {lead.id}")
            
            # 记录活动
            activity = Activity(
                customer_id=customer.id,
                lead_id=lead.id,
                type="创建",
                summary=f"矿场主添加新客户: {name}",
                details=notes,
                created_by=user_email,
                created_by_id=user_id
            )
            db.session.add(activity)
            db.session.commit()
            logging.info(f"成功记录活动: {name}")
        except Exception as e:
            db.session.rollback()
            logging.error(f"创建商机记录或活动时出错: {str(e)}")
            flash(f'创建商机记录时出错: {str(e)}', 'danger')
            return redirect(url_for('mine_customer_management'))
        
        success_message = f'已成功添加客户: {name}。'
        if grant_calculator_access:
            success_message += f'已授权访问计算器 {access_days} 天。'
        else:
            success_message += f'未授权使用计算器。'
        success_message += '同时已在CRM系统中创建客户记录。'
        flash(success_message, 'success')
        return redirect(url_for('mine_customer_management'))
    
    return render_template('add_mine_customer.html')

@app.route('/mine/customers/view_crm/<int:user_id>')
@login_required
def view_customer_crm(user_id):
    """在CRM中查看客户详情"""
    # 只允许mining_site角色访问
    if not has_role(['mining_site']):
        flash('您没有权限访问此页面，需要矿场主权限', 'danger')
        return redirect(url_for('index'))
    
    # 验证客户属于当前矿场主
    user_access = UserAccess.query.get_or_404(user_id)
    if user_access.created_by_id != session.get('user_id'):
        flash('您无权查看此客户', 'danger')
        return redirect(url_for('mine_customer_management'))
    
    # 查找对应的CRM客户记录
    customer = Customer.query.filter_by(email=user_access.email).first()
    if not customer:
        flash('未找到此客户的CRM记录', 'warning')
        return redirect(url_for('mine_customer_management'))
    
    # 重定向到CRM客户详情页
    return redirect(url_for('crm.customer_detail', customer_id=customer.id))

# ============== 网络数据分析路由 ==============

@app.route('/network/history')
@login_required
def network_history():
    """网络历史数据分析页面"""
    if not has_role(['owner', 'admin', 'mining_site']):
        flash('您没有权限访问此页面', 'danger')
        return redirect(url_for('index'))
    
    return render_template('network_history.html')

@app.route('/api/network/stats')
@login_required
def api_network_stats():
    """获取网络统计概览"""
    try:
        stats = network_analyzer.get_network_statistics()
        return jsonify(stats)
    except Exception as e:
        logging.error(f"获取网络统计失败: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/network/price-trend')
@login_required
def api_price_trend():
    """获取价格趋势数据"""
    try:
        days = request.args.get('days', 7, type=int)
        trend_data = network_analyzer.get_price_trend(days)
        return jsonify(trend_data)
    except Exception as e:
        logging.error(f"获取价格趋势失败: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/network/difficulty-trend')
@login_required
def api_difficulty_trend():
    """获取难度趋势数据"""
    try:
        days = request.args.get('days', 30, type=int)
        trend_data = network_analyzer.get_difficulty_trend(days)
        return jsonify(trend_data)
    except Exception as e:
        logging.error(f"获取难度趋势失败: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/network/hashrate-analysis')
@login_required
def api_hashrate_analysis():
    """获取算力分析数据"""
    try:
        days = request.args.get('days', 7, type=int)
        analysis_data = network_analyzer.get_hashrate_analysis(days)
        return jsonify(analysis_data)
    except Exception as e:
        logging.error(f"获取算力分析失败: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/network/profitability-forecast')
@login_required
def api_profitability_forecast():
    """基于历史数据的收益预测"""
    try:
        miner_model = request.args.get('miner_model', 'Antminer S21')
        electricity_cost = request.args.get('electricity_cost', 0.05, type=float)
        days_back = request.args.get('days_back', 30, type=int)
        
        forecast_data = network_analyzer.get_profitability_forecast(
            miner_model, electricity_cost, days_back
        )
        return jsonify(forecast_data)
    except Exception as e:
        logging.error(f"获取收益预测失败: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/network/record-snapshot', methods=['POST'])
@login_required
def api_record_snapshot():
    """手动记录网络快照"""
    if not has_role(['owner', 'admin']):
        return jsonify({'error': '权限不足'}), 403
    
    try:
        success = network_collector.record_network_snapshot()
        if success:
            return jsonify({'success': True, 'message': '网络快照记录成功'})
        else:
            return jsonify({'success': False, 'error': '记录失败'}), 500
    except Exception as e:
        logging.error(f"手动记录快照失败: {e}")
        return jsonify({'error': str(e)}), 500

# 初始化CRM系统
init_crm_routes(app)

# 初始化矿场中介业务路由
init_broker_routes(app)

# 添加调试信息页面
@app.route('/debug_info')
@login_required
def debug_info():
    """显示调试信息页面，用于排查会话问题"""
    debug_data = {
        'session_email': session.get('email'),
        'session_role': session.get('role'),
        'session_user_id': session.get('user_id'),
        'session_authenticated': session.get('authenticated'),
        'all_session_keys': list(session.keys())
    }
    
    # 从数据库获取用户信息
    if session.get('email'):
        user = UserAccess.query.filter_by(email=session.get('email')).first()
        if user:
            debug_data['db_user_role'] = user.role
            debug_data['db_user_has_access'] = user.has_access
            debug_data['db_user_email'] = user.email
    
    return jsonify(debug_data)

# 月度电力削减(Curtailment)计算器
@app.route('/curtailment_calculator')
@login_required
def curtailment_calculator():
    """月度电力削减(Curtailment)计算器页面"""
    # 检查是否有权限访问
    if not has_role(['owner', 'admin', 'mining_site']):
        flash('您没有权限访问此页面', 'danger')
        return redirect(url_for('index'))
        
    # 获取最新的BTC价格作为默认值
    try:
        current_btc_price = get_real_time_btc_price()
    except:
        current_btc_price = 80000  # 默认值
        
    # 获取最新的网络难度作为默认值
    try:
        current_difficulty = get_real_time_difficulty() / 1e12  # 转换为T
    except:
        current_difficulty = 120  # 默认值 (T)
    
    # 渲染计算器页面
    return render_template(
        'curtailment_calculator.html',
        btc_price=current_btc_price,
        network_difficulty=current_difficulty,
        block_reward=3.125  # 当前区块奖励
    )
    
@app.route('/calculate_curtailment', methods=['POST'])
@login_required
def calculate_curtailment():
    """计算月度电力削减的影响"""
    try:
        # 检查是否有权限
        if not has_role(['owner', 'admin', 'mining_site']):
            return jsonify({
                'success': False,
                'error': '您没有权限执行此操作'
            }), 403
            
        # 从表单获取基本数据
        try:
            curtailment_percentage = float(request.form.get('curtailment_percentage', 0))
            if curtailment_percentage < 0:
                curtailment_percentage = 0
            elif curtailment_percentage > 100:
                curtailment_percentage = 100
        except:
            curtailment_percentage = 0
            
        try:
            electricity_cost = float(request.form.get('electricity_cost', 0.05))
            if electricity_cost < 0:
                electricity_cost = 0
        except:
            electricity_cost = 0.05
            
        try:
            btc_price = float(request.form.get('btc_price', 80000))
            if btc_price < 0:
                btc_price = 80000
        except:
            btc_price = 80000
            
        try:
            network_difficulty = float(request.form.get('network_difficulty', 120))
            if network_difficulty <= 0:
                network_difficulty = 120
        except:
            network_difficulty = 120
            
        try:
            block_reward = float(request.form.get('block_reward', 3.125))
            if block_reward <= 0:
                block_reward = 3.125
        except:
            block_reward = 3.125
            
        # 获取关机策略
        shutdown_strategy = request.form.get('shutdown_strategy', 'efficiency')
        if shutdown_strategy not in ['efficiency', 'random', 'proportional']:
            shutdown_strategy = 'efficiency'
            
        # 解析矿机数据（支持多台矿机）
        miners_data = []
        
        # 检查是否使用单一矿机模式（向后兼容）
        single_miner_model = request.form.get('miner_model')
        if single_miner_model and single_miner_model in MINER_DATA:
            try:
                miner_count = int(request.form.get('miner_count', 1))
                if miner_count < 1:
                    miner_count = 1
                    
                miners_data.append({
                    "model": single_miner_model,
                    "count": miner_count
                })
            except:
                return jsonify({
                    'success': False,
                    'error': '矿机数量格式无效'
                }), 400
        else:
            # 多矿机模式：从POST数据中提取miners_data数组
            miners_json = request.form.get('miners_data')
            if miners_json:
                try:
                    miners_data = json.loads(miners_json)
                    
                    # 验证miners_data格式
                    if not isinstance(miners_data, list):
                        return jsonify({
                            'success': False,
                            'error': '矿机数据格式无效'
                        }), 400
                        
                    # 验证每个矿机条目
                    for miner in miners_data:
                        if not isinstance(miner, dict) or 'model' not in miner or 'count' not in miner:
                            return jsonify({
                                'success': False,
                                'error': '矿机数据格式无效，每个条目必须包含model和count'
                            }), 400
                            
                        if miner['model'] not in MINER_DATA:
                            return jsonify({
                                'success': False,
                                'error': f'无效的矿机型号: {miner["model"]}'
                            }), 400
                            
                        try:
                            miner['count'] = int(miner['count'])
                            if miner['count'] < 1:
                                return jsonify({
                                    'success': False,
                                    'error': f'矿机数量必须大于0: {miner["model"]}'
                                }), 400
                        except:
                            return jsonify({
                                'success': False,
                                'error': f'矿机数量格式无效: {miner["model"]}'
                            }), 400
                            
                except json.JSONDecodeError:
                    return jsonify({
                        'success': False,
                        'error': '矿机数据JSON格式无效'
                    }), 400
        
        # 如果没有有效的矿机数据，返回错误
        if not miners_data:
            return jsonify({
                'success': False,
                'error': '请提供至少一种有效的矿机型号'
            }), 400
        
        # 调用计算函数
        result = calculate_monthly_curtailment_impact(
            miners_data=miners_data,
            curtailment_percentage=curtailment_percentage,
            electricity_cost=electricity_cost,
            btc_price=btc_price,
            network_difficulty=network_difficulty,
            block_reward=block_reward,
            shutdown_strategy=shutdown_strategy
        )
        
        # 记录计算结果
        logging.info(f"月度Curtailment计算结果: 矿机数量={len(miners_data)}, 净影响=${result['impact']['net_impact']:.2f}")
        
        # 返回JSON结果
        return jsonify(result)
        
    except Exception as e:
        logging.error(f"计算月度Curtailment时出错: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'计算过程中发生错误: {str(e)}'
        }), 500

# 添加导航菜单项
@app.context_processor
def inject_nav_menu():
    """向模板注入导航菜单项"""
    def user_has_crm_access():
        """检查用户是否有访问CRM的权限"""
        if not session.get('authenticated'):
            return False
        role = session.get('role')
        return role in ['owner', 'admin', 'manager', 'mining_site']
    
    def user_has_network_analysis_access():
        """检查用户是否有访问网络分析的权限"""
        if not session.get('authenticated'):
            return False
        role = session.get('role')
        return role in ['owner', 'admin', 'mining_site']
    
    def user_has_analytics_access():
        """检查用户是否有访问数据分析的权限"""
        if not session.get('authenticated'):
            return False
        role = session.get('role')
        return role == 'owner'
        
    return {
        'user_has_crm_access': user_has_crm_access,
        'user_has_network_analysis_access': user_has_network_analysis_access,
        'user_has_analytics_access': user_has_analytics_access
    }

@app.route('/algorithm-test')
@app.route('/algorithm_test')
@login_required
def algorithm_test():
    """算法差异测试工具页面"""
    user_role = get_user_role(session.get('email'))
    return render_template('algorithm_test.html', user_role=user_role)

@app.route('/curtailment-calculator')
@login_required
def curtailment_calculator_alt():
    """月度电力削减(Curtailment)计算器页面 - 备用路由"""
    user_role = get_user_role(session.get('email'))
    return render_template('curtailment_calculator.html', user_role=user_role)

@app.route('/network-history')
@login_required
def network_history_main():
    """网络历史数据分析页面 - 主路由"""
    user_role = get_user_role(session.get('email'))
    if user_role not in ['owner', 'admin', 'mining_site']:
        return render_template('unauthorized.html', message='需要矿场主或管理员权限'), 403
    return render_template('network_history.html', user_role=user_role)

@app.route('/analytics')
@login_required
def analytics_dashboard():
    """数据分析仪表盘 - 仅限拥有者"""
    user_role = get_user_role(session.get('email'))
    if user_role != 'owner':
        return render_template('unauthorized.html', message='只有拥有者可以访问数据分析系统'), 403
    
    # 直接在服务器端获取技术指标和分析报告数据
    technical_indicators = None
    latest_report = None
    
    try:
        from analytics_engine import DatabaseManager
        db_manager = DatabaseManager()
        db_manager.connect()
        
        # 获取技术指标
        cursor = db_manager.connection.cursor()
        cursor.execute("""
            SELECT rsi_14, sma_20, sma_50, ema_12, ema_26, macd, 
                   volatility_30d, bollinger_upper, bollinger_lower, recorded_at
            FROM technical_indicators 
            ORDER BY recorded_at DESC LIMIT 1
        """)
        tech_data = cursor.fetchone()
        
        if tech_data:
            technical_indicators = {
                'rsi_14': tech_data[0],
                'sma_20': tech_data[1],
                'sma_50': tech_data[2],
                'ema_12': tech_data[3],
                'ema_26': tech_data[4],
                'macd': tech_data[5],
                'volatility_30d': tech_data[6],
                'bollinger_upper': tech_data[7],
                'bollinger_lower': tech_data[8],
                'recorded_at': tech_data[9].isoformat() if tech_data[9] else None
            }
        
        # 获取最新分析报告
        cursor.execute("""
            SELECT title, summary, generated_at, confidence_score, recommendations,
                   risk_assessment, content
            FROM analysis_reports 
            ORDER BY generated_at DESC LIMIT 1
        """)
        report_data = cursor.fetchone()
        
        if report_data:
            latest_report = {
                'title': report_data[0],
                'summary': report_data[1],
                'generated_at': report_data[2].isoformat() if report_data[2] else None,
                'confidence_score': report_data[3],
                'recommendations': report_data[4],
                'risk_assessment': report_data[5],
                'content': report_data[6]
            }
        
        cursor.close()
        db_manager.connection.close()
        
    except Exception as e:
        print(f"获取分析数据时出错: {e}")
    
    return render_template('analytics_main.html', 
                          user_role=user_role,
                          technical_indicators=technical_indicators,
                          latest_report=latest_report)

@app.route('/api/analytics/market-data')
@login_required
def analytics_market_data():
    """获取分析系统的市场数据"""
    user_role = get_user_role(session.get('email'))
    if user_role != 'owner':
        return jsonify({'error': '只有拥有者可以访问分析系统'}), 403
    
    try:
        import psycopg2
        
        # 直接连接数据库获取最新市场数据
        conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
        cursor = conn.cursor()
        cursor.execute("""
            SELECT recorded_at, btc_price, network_hashrate, network_difficulty, 
                   fear_greed_index, price_change_24h, btc_market_cap, btc_volume_24h,
                   price_change_1h, price_change_7d
            FROM market_analytics 
            ORDER BY recorded_at DESC LIMIT 1
        """)
        data = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if data:
            return jsonify({
                'success': True,
                'data': {
                    'timestamp': data[0].isoformat(),
                    'btc_price': float(data[1]) if data[1] else None,
                    'network_hashrate': float(data[2]) if data[2] else None,
                    'network_difficulty': float(data[3]) if data[3] else None,
                    'fear_greed_index': data[4],
                    'price_change_24h': float(data[5]) if data[5] else None,
                    'btc_market_cap': float(data[6]) if data[6] else None,
                    'btc_volume_24h': float(data[7]) if data[7] else None,
                    'price_change_1h': float(data[8]) if data[8] else None,
                    'price_change_7d': float(data[9]) if data[9] else None
                }
            })
        else:
            return jsonify({'success': False, 'error': '暂无市场数据'}), 404
    except Exception as e:
        app.logger.error(f"获取分析数据失败: {e}")
        return jsonify({'error': f'获取市场数据失败: {str(e)}'}), 500

@app.route('/api/analytics/latest-report')
@login_required
def analytics_latest_report():
    """获取最新分析报告"""
    user_role = get_user_role(session.get('email'))
    if user_role != 'owner':
        return jsonify({'error': '只有拥有者可以访问分析系统'}), 403
    
    try:
        import psycopg2
        import analytics_engine
        
        # 直接连接数据库获取最新分析报告
        conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
        cursor = conn.cursor()
        cursor.execute("""
            SELECT generated_at, title, summary, key_findings, recommendations, 
                   risk_assessment, confidence_score
            FROM analysis_reports 
            ORDER BY generated_at DESC LIMIT 1
        """)
        data = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if data:
            latest_report = {
                'date': data[0].isoformat(),
                'generated_at': data[0].isoformat(),
                'title': data[1],
                'summary': data[2],
                'key_findings': data[3],
                'recommendations': data[4],
                'risk_assessment': data[5],
                'confidence_score': float(data[6]) if data[6] else None
            }
            return jsonify({
                'latest_report': latest_report,
                'success': True
            })
        else:
            # Return empty but valid format when no data
            return jsonify({
                'latest_report': None,
                'success': True,
                'message': '暂无分析报告数据'
            })
    except Exception as e:
        app.logger.error(f"获取分析报告失败: {e}")
        return jsonify({'error': f'获取分析报告失败: {str(e)}'}), 500

@app.route('/api/analytics/technical-indicators')
@login_required
def analytics_technical_indicators():
    """获取技术指标"""
    user_role = get_user_role(session.get('email'))
    if user_role != 'owner':
        return jsonify({'error': '只有拥有者可以访问分析系统'}), 403
    
    try:
        import analytics_engine
        import psycopg2
        
        # 获取最新技术指标
        conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
        cursor = conn.cursor()
        cursor.execute("""
            SELECT recorded_at, rsi_14, sma_20, sma_50, ema_12, ema_26, 
                   macd, bollinger_upper, bollinger_lower, volatility_30d
            FROM technical_indicators 
            ORDER BY recorded_at DESC LIMIT 1
        """)
        data = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if data:
            indicators_data = {
                'timestamp': data[0].isoformat(),
                'rsi_14': float(data[1]) if data[1] else None,
                'sma_20': float(data[2]) if data[2] else None,
                'sma_50': float(data[3]) if data[3] else None,
                'ema_12': float(data[4]) if data[4] else None,
                'ema_26': float(data[5]) if data[5] else None,
                'macd': float(data[6]) if data[6] else None,
                'bollinger_upper': float(data[7]) if data[7] else None,
                'bollinger_lower': float(data[8]) if data[8] else None,
                'volatility_30d': float(data[9]) if data[9] else None
            }
            return jsonify({
                'indicators': [indicators_data],
                'latest_indicators': indicators_data
            })
        else:
            # Return empty but valid format when no data
            return jsonify({
                'indicators': [],
                'latest_indicators': None,
                'message': '指标数据为空(正常，需要时间积累)'
            })
    except Exception as e:
        app.logger.error(f"获取技术指标失败: {e}")
        return jsonify({'error': f'获取技术指标失败: {str(e)}'}), 500

@app.route('/api/analytics/price-history')
@login_required
def analytics_price_history():
    """获取价格历史数据"""
    user_role = get_user_role(session.get('email'))
    if user_role != 'owner':
        return jsonify({'error': '只有拥有者可以访问分析系统'}), 403
    
    try:
        import psycopg2
        
        hours = request.args.get('hours', 24, type=int)
        
        # 直接从数据库获取价格历史数据
        conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
        cursor = conn.cursor()
        cursor.execute("""
            SELECT recorded_at, btc_price, network_hashrate, network_difficulty
            FROM market_analytics 
            WHERE recorded_at > NOW() - INTERVAL '%s hours'
            ORDER BY recorded_at ASC
        """, (hours,))
        
        data = cursor.fetchall()
        cursor.close()
        conn.close()
        
        if data:
            price_history = []
            for row in data:
                price_history.append({
                    'timestamp': row[0].isoformat(),
                    'btc_price': float(row[1]) if row[1] else None,
                    'network_hashrate': float(row[2]) if row[2] else None,
                    'network_difficulty': float(row[3]) if row[3] else None
                })
            
            return jsonify({
                'hours': hours,
                'data_points': len(price_history),
                'price_history': price_history
            })
        else:
            return jsonify({'error': f'未找到过去{hours}小时的价格数据'}), 404
            
    except Exception as e:
        app.logger.error(f"获取价格历史失败: {e}")
        return jsonify({'error': f'获取价格历史失败: {str(e)}'}), 500

# Missing frontend routes that were causing 404 errors
@app.route('/crm/dashboard')
@login_required
def crm_dashboard_redirect():
    """CRM系统仪表盘重定向"""
    user_role = get_user_role(session.get('email'))
    if user_role not in ['owner', 'admin', 'mining_site']:
        flash('您没有权限访问CRM系统', 'danger')
        return redirect(url_for('index'))
    return redirect(url_for('crm.dashboard'))

@app.route('/curtailment/calculator')
@login_required
def curtailment_calculator_redirect():
    """电力削减计算器 - 重定向路由"""
    return redirect(url_for('curtailment_calculator'))

@app.route('/analytics/dashboard')
@login_required
def analytics_dashboard_alt():
    """数据分析仪表盘 - 替代路由"""
    if not has_role(['owner']):
        flash('您没有权限访问分析仪表盘', 'danger')
        return redirect(url_for('index'))
    return analytics_dashboard()

@app.route('/algorithm/test')
@login_required
def algorithm_test_alt():
    """算法差异测试 - 替代路由"""
    if not has_role(['owner', 'admin']):
        flash('您没有权限访问算法测试', 'danger')
        return redirect(url_for('index'))
    return algorithm_test()

@app.route('/network_history')
@login_required
def network_history_alt():
    """网络历史数据分析 - 备用路由"""
    if not has_role(['owner', 'admin']):
        flash('您没有权限访问网络分析', 'danger')
        return redirect(url_for('index'))
    return network_history()



# 添加缺失分析系统API路由修复404错误
@app.route('/analytics/api/latest-report')
@login_required
def analytics_latest_report_api():
    """获取最新分析报告API"""
    if not has_role(['owner']):
        return jsonify({'error': '需要拥有者权限'}), 403
    
    try:
        from analytics_engine import DatabaseManager
        db_manager = DatabaseManager()
        db_manager.connect()
        
        cursor = db_manager.connection.cursor()
        cursor.execute("""
            SELECT report_data, created_at
            FROM analysis_reports 
            ORDER BY created_at DESC 
            LIMIT 1
        """)
        result = cursor.fetchone()
        
        if result:
            return jsonify({'success': True, 'data': result[0]})
        else:
            return jsonify({'success': False, 'error': '暂无报告'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/analytics/api/technical-indicators')
@login_required
def analytics_technical_indicators_api():
    """获取技术指标API"""
    if not has_role(['owner']):
        return jsonify({'error': '需要拥有者权限'}), 403
    
    try:
        from analytics_engine import DatabaseManager
        db_manager = DatabaseManager()
        db_manager.connect()
        
        cursor = db_manager.connection.cursor()
        cursor.execute("""
            SELECT sma_20, sma_50, ema_12, ema_26, rsi_14, macd, 
                   bollinger_upper, bollinger_lower, volatility_30d, created_at
            FROM technical_indicators 
            ORDER BY created_at DESC 
            LIMIT 1
        """)
        result = cursor.fetchone()
        
        if result:
            indicators_data = {
                'sma_20': float(result[0]) if result[0] else None,
                'sma_50': float(result[1]) if result[1] else None,
                'ema_12': float(result[2]) if result[2] else None,
                'ema_26': float(result[3]) if result[3] else None,
                'rsi_14': float(result[4]) if result[4] else None,
                'macd': float(result[5]) if result[5] else None,
                'bollinger_upper': float(result[6]) if result[6] else None,
                'bollinger_lower': float(result[7]) if result[7] else None,
                'volatility_30d': float(result[8]) if result[8] else None,
                'timestamp': result[9].isoformat() if result[9] else None
            }
            return jsonify({'success': True, 'data': indicators_data})
        else:
            return jsonify({'success': False, 'error': '暂无技术指标数据'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/analytics/api/price-history')
@login_required
def analytics_price_history_api():
    """获取价格历史数据API"""
    if not has_role(['owner']):
        return jsonify({'error': '需要拥有者权限'}), 403
    
    try:
        from analytics_engine import DatabaseManager
        db_manager = DatabaseManager()
        db_manager.connect()
        
        cursor = db_manager.connection.cursor()
        cursor.execute("""
            SELECT btc_price, timestamp
            FROM market_analytics 
            ORDER BY timestamp DESC 
            LIMIT 100
        """)
        results = cursor.fetchall()
        
        if results:
            data = [{'price': row[0], 'timestamp': row[1].isoformat() if row[1] else None} for row in results]
            return jsonify({'success': True, 'data': data})
        else:
            return jsonify({'success': False, 'error': '暂无价格历史数据'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# 添加缺失的API路由修复404错误
@app.route('/api/price-trend')
@login_required
def api_price_trend_missing():
    """价格趋势API - 缺失路由修复"""
    return api_price_trend()

@app.route('/api/difficulty-trend')
@login_required
def api_difficulty_trend_missing():
    """难度趋势API - 缺失路由修复"""
    return api_difficulty_trend()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)