from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
import logging
import json
import numpy as np
import os
import secrets
import requests
from datetime import datetime
from auth import verify_email, login_required
from mining_calculator import (
    MINER_DATA,
    get_real_time_btc_price,
    get_real_time_difficulty,
    get_real_time_block_reward,
    get_real_time_btc_hashrate,
    calculate_mining_profitability,
    generate_profit_chart_data,
    calculate_mining_roi,
    generate_roi_comparison_data
)

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

# 导入数据库和用户模型
from db import db
from models import LoginRecord, UserAccess

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
            try:
                if request.remote_addr:
                    # 如果是本地或内部网络IP
                    if request.remote_addr.startswith('127.') or request.remote_addr == '::1':
                        location = "本地, 开发环境, localhost"
                    elif request.remote_addr.startswith('192.168.') or request.remote_addr.startswith('10.'):
                        location = "中国, 内部网络, 局域网"
                    else:
                        # 使用IP-API获取地理位置信息
                        import requests
                        # 免费版的ip-api.com，不需要API密钥
                        ip_api_url = f"http://ip-api.com/json/{request.remote_addr}?fields=status,message,country,regionName,city,query"
                        response = requests.get(ip_api_url, timeout=3)
                        if response.status_code == 200:
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
                                    location = f"Replit服务器, 数据中心"
                                else:
                                    location = f"外部网络 ({request.remote_addr})"
                        else:
                            logging.warning(f"IP-API请求失败，状态码: {response.status_code}")
                            location = f"外部网络 ({request.remote_addr})"
                    logging.info(f"用户IP地址 {request.remote_addr} 已被识别为 {location}")
            except Exception as e:
                logging.error(f"获取位置信息时出错: {str(e)}")
                
            login_record = LoginRecord(
                email=email,
                successful=login_successful,
                ip_address=request.remote_addr,
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
            
            # 获取并保存用户角色到会话
            user_role = get_user_role(email)
            session['role'] = user_role
            
            # 记录成功登录
            logging.info(f"用户成功登录: {email}")
            
            # 闪现成功消息
            flash('登录成功！欢迎使用BTC挖矿计算器', 'success')
            
            # 重定向到原始请求的URL或主页
            next_url = session.pop('next_url', url_for('index'))
            return redirect(next_url)
        else:
            # 登录失败
            logging.warning(f"用户登录失败: {email}")
            
            # 闪现错误消息
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
    """处理用户登出"""
    # 清除会话
    session.clear()
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

@app.route('/calculate', methods=['POST'])
@login_required
def calculate():
    """Handle the calculation request and return results as JSON"""
    try:
        # Log full form data for debugging
        logging.info(f"Received calculate request form data: {request.form}")
        
        # 初始化错误收集列表
        input_errors = []
        
        # Get values from the form submission with detailed error handling
        try:
            hashrate = float(request.form.get('hashrate', 0))
        except ValueError as e:
            error_msg = f"无效的算力值: {request.form.get('hashrate')}"
            logging.error(f"{error_msg} - {str(e)}")
            input_errors.append(error_msg)
            hashrate = 0
            
        hashrate_unit = request.form.get('hashrate_unit', 'TH/s')
        
        try:
            power_consumption = float(request.form.get('power_consumption', 0))
        except ValueError as e:
            error_msg = f"无效的功耗值: {request.form.get('power_consumption')}"
            logging.error(f"{error_msg} - {str(e)}")
            input_errors.append(error_msg)
            power_consumption = 0
            
        try:
            electricity_cost = float(request.form.get('electricity_cost', 0))
        except ValueError as e:
            error_msg = f"无效的电费值: {request.form.get('electricity_cost')}"
            logging.error(f"{error_msg} - {str(e)}")
            input_errors.append(error_msg)
            electricity_cost = 0.05  # Default value
            
        try:
            client_electricity_cost = float(request.form.get('client_electricity_cost', 0))
        except ValueError as e:
            error_msg = f"无效的客户电费值: {request.form.get('client_electricity_cost')}"
            logging.error(f"{error_msg} - {str(e)}")
            input_errors.append(error_msg)
            client_electricity_cost = 0
            
        try:
            btc_price = float(request.form.get('btc_price', 0))
        except ValueError as e:
            error_msg = f"无效的BTC价格值: {request.form.get('btc_price')}"
            logging.error(f"{error_msg} - {str(e)}")
            input_errors.append(error_msg)
            btc_price = 0
            
        use_real_time = request.form.get('use_real_time') == 'on'
        miner_model = request.form.get('miner_model')
        
        try:
            miner_count = int(request.form.get('miner_count', 1))
        except ValueError as e:
            error_msg = f"无效的矿机数量: {request.form.get('miner_count')}"
            logging.error(f"{error_msg} - {str(e)}")
            input_errors.append(error_msg)
            miner_count = 1
            
        try:
            site_power_mw = float(request.form.get('site_power_mw', 1.0))
        except ValueError as e:
            error_msg = f"无效的站点功率值: {request.form.get('site_power_mw')}"
            logging.error(f"{error_msg} - {str(e)}")
            input_errors.append(error_msg)
            site_power_mw = 1.0
            
        # 如果有输入错误，返回具体的错误信息
        if input_errors:
            error_message = "输入参数无效: " + ", ".join(input_errors)
            logging.error(error_message)
            return jsonify({
                'success': False,
                'error': error_message
            }), 400
            
        try:
            curtailment = float(request.form.get('curtailment', 0))
        except ValueError as e:
            logging.error(f"Invalid curtailment value: {request.form.get('curtailment')} - {str(e)}")
            curtailment = 0
            
        try:
            maintenance_fee = float(request.form.get('maintenance_fee', 0))
        except ValueError as e:
            logging.error(f"Invalid maintenance fee value: {request.form.get('maintenance_fee')} - {str(e)}")
            maintenance_fee = 0
        
        logging.info(f"Calculate request: model={miner_model}, count={miner_count}, real_time={use_real_time}, "
                     f"site_power={site_power_mw}MW, curtailment={curtailment}%")
        
        # Convert hashrate to TH/s for calculation
        if hashrate_unit == 'PH/s':
            hashrate = hashrate * 1000
        elif hashrate_unit == 'EH/s':
            hashrate = hashrate * 1000000
                
        # 添加错误处理来确保即使API调用失败计算仍能继续
        try:
            # 计算挖矿盈利能力
            result = calculate_mining_profitability(
                hashrate=hashrate,
                power_consumption=power_consumption,
                electricity_cost=electricity_cost,
                client_electricity_cost=client_electricity_cost,
                btc_price=btc_price if not use_real_time else None,
                use_real_time_data=use_real_time,
                miner_model=miner_model,
                miner_count=miner_count,
                site_power_mw=site_power_mw,
                curtailment=curtailment
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
                monthly_profit = monthly_revenue - monthly_cost
                
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
                    'btc_price': result.get('break_even', {}).get('btc_price', 0)
                }
            }
            
            # 如果结果中有估算注释，也添加到过滤结果中
            if 'estimation_note' in result:
                filtered_result['estimation_note'] = result['estimation_note']
            
            # 返回过滤后的结果
            return jsonify(filtered_result)
            
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

@app.route('/btc_price', methods=['GET'])
@login_required
def get_btc_price():
    """Get the current Bitcoin price from API"""
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

@app.route('/network_stats', methods=['GET'])
@login_required
def get_network_stats():
    """Get current Bitcoin network statistics"""
    try:
        # 使用定义的默认值
        
        # 获取实时数据，如果有任何错误使用默认值
        try:
            price = get_real_time_btc_price()
            logging.info(f"成功获取BTC价格: ${price}")
        except Exception as e:
            logging.error(f"获取BTC价格失败: {e}")
            price = 80000  # 默认价格
            
        try:
            difficulty = get_real_time_difficulty()
            logging.info(f"成功获取网络难度: {difficulty/10**12}T")
        except Exception as e:
            logging.error(f"获取网络难度失败: {e}")
            difficulty = 119116256505723  # 默认难度
            
        try:
            block_reward = get_real_time_block_reward()
            logging.info(f"成功获取区块奖励: {block_reward} BTC")
        except Exception as e:
            logging.error(f"获取区块奖励失败: {e}")
            block_reward = 3.125  # 默认区块奖励
            
        try:
            # 直接使用简单高效的API获取哈希率
            response = requests.get('https://blockchain.info/q/hashrate', timeout=5)
            if response.status_code == 200:
                # 该API直接返回TH/s单位的哈希率
                hashrate_th = float(response.text.strip())
                # 转换为EH/s (1 EH/s = 1,000,000,000 TH/s)
                hashrate = hashrate_th / 1e9
                logging.info(f"成功获取网络哈希率: {hashrate_th} TH/s → {hashrate} EH/s")
                
                # 如果哈希率不合理，使用默认值
                if hashrate < 10 or hashrate > 2000:
                    logging.warning(f"计算的哈希率值不合理: {hashrate} EH/s，使用默认值")
                    hashrate = DEFAULT_HASHRATE_EH
            else:
                logging.error(f"获取网络哈希率API返回错误状态码: {response.status_code}")
                hashrate = DEFAULT_HASHRATE_EH
        except Exception as e:
            logging.error(f"获取网络哈希率时出错: {e}")
            hashrate = DEFAULT_HASHRATE_EH
        
        # 提供额外日志以便调试
        logging.info(f"返回网络统计数据: 价格=${price}, 难度={difficulty/10**12}T, 哈希率={hashrate}EH/s, 奖励={block_reward}BTC")
        
        return jsonify({
            'success': True,
            'price': price,
            'difficulty': difficulty / 10**12,  # Convert to T for readability
            'hashrate': hashrate,  # EH/s
            'block_reward': block_reward
        })
    except Exception as e:
        logging.error(f"获取网络状态统计时发生错误: {str(e)}")
        # 返回默认值而不是错误，这样前端至少能显示一些内容
        return jsonify({
            'success': True,
            'price': DEFAULT_BTC_PRICE,  # 默认价格
            'difficulty': DEFAULT_DIFFICULTY,  # 默认难度，单位T
            'hashrate': DEFAULT_HASHRATE_EH,  # 默认哈希率，单位EH/s
            'block_reward': DEFAULT_BLOCK_REWARD  # 默认区块奖励
        })

@app.route('/miners', methods=['GET'])
@login_required
def get_miners():
    """Get the list of available miner models and their specifications"""
    try:
        miners_list = []
        for name, specs in MINER_DATA.items():
            miners_list.append({
                'name': name,
                'hashrate': specs['hashrate'],
                'power_watt': specs['power_watt'],
                'efficiency': round(specs['power_watt'] / specs['hashrate'], 2) # W/TH
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

@app.route('/profit_chart_data', methods=['POST'])
@login_required
def get_profit_chart_data():
    """Generate profit chart data for visualization"""
    try:
        # 添加详细日志以帮助调试
        import time
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
            import traceback
            logging.error(traceback.format_exc())
            return jsonify({
                'success': False,
                'error': f'Error generating chart data: {str(e)}'
            }), 500
    except Exception as e:
        logging.error(f"Unhandled exception in profit chart data generation: {str(e)}")
        import traceback
        logging.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)