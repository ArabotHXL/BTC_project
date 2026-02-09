"""
HashInsight Enterprise - Authentication Routes
用户认证路由

提供以下端点:
- /login - 用户登录 (邮箱/密码)
- /logout - 用户登出
- /register - 用户注册
- /forgot-password - 忘记密码
- /reset-password/<token> - 密码重置
- /verify-email/<token> - 邮箱验证
- /unauthorized - 未授权页面
- /api/wallet/nonce - Web3钱包认证nonce生成
- /api/wallet/login - Web3钱包登录
"""

import os
import re
import secrets
import logging
import time
import requests
import ipaddress
from datetime import datetime, timedelta
from urllib.parse import quote

from flask import Blueprint, request, session, g, redirect, url_for, flash, render_template, jsonify

from db import db
from models import UserAccess, LoginRecord, User, PasswordResetToken
from auth import verify_email, verify_password_login, generate_wallet_login_message, verify_wallet_login
from security_enhancements import SecurityManager
from rate_limiting import rate_limit
from security_soc2 import (
    login_security_manager,
    password_policy_manager,
    data_access_logger,
    SensitiveResourceType
)

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)


def send_verification_email(email, token, language='zh'):
    """发送邮箱验证邮件
    
    Args:
        email: 接收邮箱
        token: 验证令牌
        language: 语言 ('zh' 中文, 'en' 英文)
    """
    try:
        domain = os.environ.get('VERIFICATION_DOMAIN', 'calc.hashinsight.net')
        verification_url = f"https://{domain}/verify-email/{token}"
        
        logger.info(f"邮箱验证链接已生成: {verification_url}")
        logger.info(f"发送验证邮件到: {email} (语言: {language})")
        
        try:
            from gmail_oauth_service import send_verification_email_smtp
            if send_verification_email_smtp(email, verification_url, language):
                logger.info(f"Gmail SMTP验证邮件已成功发送到: {email}")
                return True
        except Exception as e:
            logger.warning(f"Gmail SMTP服务出错: {e}")
        
        print("=" * 60)
        if language == 'en':
            print("📧 Email Verification Link:")
            print(f"User: {email}")
            print(f"Verification Link: {verification_url}")
            print("Please copy the above link to your browser to complete email verification")
        else:
            print("📧 邮箱验证链接:")
            print(f"用户: {email}")
            print(f"验证链接: {verification_url}")
            print("请复制上述链接到浏览器完成邮箱验证")
        print("=" * 60)
        logger.info(f"验证链接已生成并显示在控制台: {email}")
        return True
        
    except Exception as e:
        logger.error(f"发送验证邮件失败: {e}")
        return False


def get_user_role(email):
    """根据用户邮箱获取角色"""
    user = UserAccess.query.filter_by(email=email).first()
    if user and user.has_access:
        return user.role
    return None


def get_client_location(client_ip):
    """获取客户端地理位置信息"""
    location = "未知位置"
    
    if not client_ip:
        return location
    
    if client_ip.startswith('127.') or client_ip == '::1':
        return "本地, 开发环境, localhost"
    elif client_ip.startswith('192.168.') or client_ip.startswith('10.'):
        return "中国, 内部网络, 局域网"
    
    try:
        ip_obj = ipaddress.ip_address(client_ip)
        
        if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local or ip_obj.is_multicast or ip_obj.is_reserved:
            if ip_obj.is_private:
                if str(ip_obj).startswith('10.'):
                    return "内部网络 (10.x.x.x)"
                elif str(ip_obj).startswith('192.168.'):
                    return "局域网 (192.168.x.x)"
                elif str(ip_obj).startswith('172.'):
                    return "企业网络 (172.x.x.x)"
                else:
                    return "私有网络"
            elif ip_obj.is_loopback:
                return "本地环回地址"
            else:
                return "特殊用途IP地址"
        else:
            safe_ip = quote(str(ip_obj), safe='.')
            allowed_host = "ip-api.com"
            ip_api_url = f"http://{allowed_host}/json/{safe_ip}?fields=status,message,country,regionName,city,query"
            
            response = requests.get(ip_api_url, timeout=3)
            
            if response and response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    country = data.get('country', '未知国家')
                    region = data.get('regionName', '未知地区')
                    city = data.get('city', '未知城市')
                    location = f"{country}, {region}, {city}"
                else:
                    error_msg = data.get('message', '未知错误')
                    if error_msg == 'private range':
                        if 'replit' in request.headers.get('Host', '').lower():
                            location = f"Replit托管服务, {client_ip}"
                        else:
                            location = f"私有网络, {client_ip}"
                    else:
                        location = f"外部网络 ({client_ip})"
            else:
                location = f"外部网络 ({client_ip})"
                
    except (ipaddress.AddressValueError, ValueError) as e:
        logger.warning(f"无效的IP地址格式: {client_ip}, 错误: {str(e)}")
        location = "未知位置 (无效IP格式)"
    except Exception as e:
        logger.error(f"获取位置信息时出错: {str(e)}")
    
    return location


def get_client_ip():
    """获取客户端真实IP地址"""
    client_ip = request.headers.get('X-Forwarded-For') or \
               request.headers.get('X-Real-IP') or \
               request.remote_addr
    
    if client_ip and ',' in client_ip:
        client_ip = client_ip.split(',')[0].strip()
    
    return client_ip


@auth_bp.route('/login', methods=['GET', 'POST'])
@SecurityManager.csrf_protect
def login():
    """处理用户登录"""
    if session.get('authenticated'):
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        email_or_username = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        
        # Check if account is locked due to failed login attempts
        client_ip = get_client_ip()
        lock_result = login_security_manager.check_account_locked(email_or_username)
        if lock_result['is_locked']:
            error_msg = lock_result['message_zh'] if g.language != 'en' else lock_result['message_en']
            flash(error_msg, 'danger')
            return render_template('login.html')
        
        user = None
        login_successful = False
        
        if password:
            try:
                user = verify_password_login(email_or_username, password)
                if user:
                    login_successful = True
                    email = user.email
                    
                    # Check password expiry (SOC2 compliance)
                    expiry_result = password_policy_manager.check_password_expiry(user.id if user else None)
                    if expiry_result.get('is_expired'):
                        flash('Your password has expired. Please reset your password. / 您的密码已过期，请重置密码。', 'warning')
                        return redirect(url_for('auth.forgot_password'))
                else:
                    email = email_or_username
            except Exception as db_error:
                logger.error(f"数据库连接失败: {db_error}")
                flash('系统暂时无法连接数据库，请稍后再试。Database connection failed, please try again later.', 'danger')
                return render_template('login.html')
        else:
            email = email_or_username
            try:
                login_successful = verify_email(email)
            except Exception as db_error:
                logger.error(f"数据库连接失败: {db_error}")
                flash('系统暂时无法连接数据库，请稍后再试。Database connection failed, please try again later.', 'danger')
                return render_template('login.html')
        
        try:
            client_ip = get_client_ip()
            location = get_client_location(client_ip)
            
            logger.info(f"识别到的客户端IP: {client_ip}, 原始IP: {request.remote_addr}")
            
            login_record = LoginRecord(
                email=email,
                successful=login_successful,
                ip_address=client_ip,
                login_location=location
            )
            logger.info(f"创建登录记录: {email}, 状态: {'成功' if login_successful else '失败'}")
            db.session.add(login_record)
            db.session.commit()
            logger.info("登录记录已保存到数据库")
        except Exception as e:
            logger.error(f"保存登录记录时发生错误: {str(e)}")
            db.session.rollback()
        
        if login_successful:
            session.permanent = True
            session['authenticated'] = True
            session['email'] = email
            
            user = UserAccess.query.filter_by(email=email).first()
            if user:
                session['user_id'] = user.id
                user.last_login = datetime.utcnow()
                db.session.commit()
            
            user_role = get_user_role(email)
            session['role'] = user_role
            
            try:
                from common.rbac import get_user_permissions
                user_permissions = get_user_permissions()
                session['permissions'] = user_permissions.get('permissions', {})
                logger.info(f"用户权限已加载: {len(session['permissions'])} 个模块权限")
            except Exception as rbac_error:
                logger.warning(f"加载用户权限时出错: {rbac_error}")
                session['permissions'] = {}
            
            logger.info(f"用户成功登录: {email}, ID: {session.get('user_id')}, 角色: {user_role}")
            
            # Record successful login and detect suspicious activity
            login_security_manager.record_successful_login(email, client_ip or '')
            user_agent = request.headers.get('User-Agent', '')
            suspicious_result = login_security_manager.detect_suspicious_login(
                user_id=str(session.get('user_id', '')),
                ip=client_ip or '',
                user_agent=user_agent,
                email=email
            )
            if suspicious_result['is_suspicious']:
                logger.warning(f"Suspicious login detected for {email}: {suspicious_result}")
            
            if g.language == 'en':
                flash('Login successful! Welcome to BTC Mining Calculator', 'success')
            else:
                flash('登录成功！欢迎使用BTC挖矿计算器', 'success')
            
            # Role-based redirect after login
            next_url = session.pop('next_url', None)
            if next_url:
                return redirect(next_url)
            
            # Default redirect based on role
            if user_role in ['owner', 'admin']:
                return redirect('/admin/site-owners')
            elif user_role == 'mining_site_owner':
                return redirect('/hosting/host/my-customers')
            elif user_role == 'client':
                return redirect('/hosting/')
            else:
                return redirect(url_for('index'))
        else:
            logger.warning(f"用户登录失败: {email}")
            
            # Record failed login for brute force protection
            login_security_manager.record_failed_login(email, client_ip or '')
            
            if g.language == 'en':
                flash('Login failed! You do not have access permission', 'danger')
            else:
                flash('登录失败！您没有访问权限', 'danger')
            
            return redirect(url_for('auth.unauthorized'))
    
    return render_template('login.html')


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
@SecurityManager.csrf_protect
def forgot_password():
    """处理忘记密码请求"""
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        
        if not email:
            if g.language == 'en':
                flash('Please enter your email address', 'danger')
            else:
                flash('请输入邮箱地址', 'danger')
            return render_template('forgot_password.html')
        
        try:
            user = User.query.filter_by(email=email).first()
            
            if user:
                token = secrets.token_urlsafe(64)
                expires_at = datetime.utcnow() + timedelta(hours=1)
                
                PasswordResetToken.query.filter_by(user_id=user.id, used=False).delete()
                
                reset_token = PasswordResetToken(
                    user_id=user.id,
                    token=token,
                    expires_at=expires_at
                )
                db.session.add(reset_token)
                db.session.commit()
                
                reset_url = url_for('auth.reset_password', token=token, _external=True)
                from gmail_oauth_service import send_password_reset_email
                send_password_reset_email(email, reset_url, g.language)
                
                logger.info(f"密码重置链接已发送至: {email}")
            else:
                logger.info(f"忘记密码请求 - 邮箱不存在: {email}")
        except Exception as e:
            logger.error(f"处理忘记密码请求时出错: {e}")
        
        if g.language == 'en':
            flash('If the email exists in our system, you will receive a password reset link shortly.', 'info')
        else:
            flash('如果该邮箱已注册，您将很快收到密码重置链接。', 'info')
        
        return render_template('forgot_password.html')
    
    return render_template('forgot_password.html')


@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
@SecurityManager.csrf_protect
def reset_password(token):
    """处理密码重置"""
    from werkzeug.security import generate_password_hash
    
    reset_token = PasswordResetToken.query.filter_by(token=token).first()
    valid_token = reset_token and reset_token.is_valid()
    
    if request.method == 'POST':
        if not valid_token:
            if g.language == 'en':
                flash('Invalid or expired reset link. Please request a new one.', 'danger')
            else:
                flash('重置链接无效或已过期，请重新申请。', 'danger')
            return render_template('reset_password.html', valid_token=False, token=token)
        
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Validate password strength using SOC2 password policy
        validation = password_policy_manager.validate_password_strength(password)
        if not validation.is_valid:
            errors = validation.get_errors(g.language)
            flash(' '.join(errors), 'danger')
            return render_template('reset_password.html', valid_token=True, token=token)
        
        if password != confirm_password:
            if g.language == 'en':
                flash('Passwords do not match', 'danger')
            else:
                flash('两次输入的密码不一致', 'danger')
            return render_template('reset_password.html', valid_token=True, token=token)
        
        try:
            user = User.query.get(reset_token.user_id)
            if user:
                user.password_hash = generate_password_hash(password)
                reset_token.used = True
                db.session.commit()
                
                logger.info(f"用户密码重置成功: {user.email}")
                
                if g.language == 'en':
                    flash('Password reset successful! Please login with your new password.', 'success')
                else:
                    flash('密码重置成功！请使用新密码登录。', 'success')
                
                return redirect(url_for('auth.login'))
            else:
                if g.language == 'en':
                    flash('User not found', 'danger')
                else:
                    flash('用户不存在', 'danger')
        except Exception as e:
            logger.error(f"密码重置失败: {e}")
            db.session.rollback()
            if g.language == 'en':
                flash('Failed to reset password. Please try again.', 'danger')
            else:
                flash('密码重置失败，请重试。', 'danger')
        
        return render_template('reset_password.html', valid_token=True, token=token)
    
    return render_template('reset_password.html', valid_token=valid_token, token=token)


@auth_bp.route('/api/wallet/nonce', methods=['POST'])
@rate_limit(max_requests=5, window_minutes=15, feature_name="wallet_nonce")
@SecurityManager.csrf_protect
def wallet_nonce():
    """生成钱包登录签名的nonce"""
    try:
        data = request.get_json()
        wallet_address = data.get('wallet_address')
        
        if not wallet_address:
            return jsonify({'success': False, 'error': 'Missing wallet address'}), 400
        
        if len(wallet_address) != 42 or not wallet_address.startswith('0x'):
            return jsonify({'success': False, 'error': 'Invalid wallet address format'}), 400
        
        wallet_address = wallet_address.lower()
        
        timestamp = str(int(time.time()))
        random_string = secrets.token_urlsafe(16)
        nonce = f"{timestamp}_{random_string}"
        
        message = generate_wallet_login_message(wallet_address, nonce)
        
        user = UserAccess.query.filter_by(wallet_address=wallet_address).first()
        if user:
            user.wallet_nonce = nonce
            db.session.commit()
        else:
            session[f'wallet_nonce_{wallet_address}'] = nonce
        
        logger.info(f"为钱包地址 {wallet_address} 生成了nonce")
        
        return jsonify({
            'success': True,
            'nonce': nonce,
            'message': message,
            'wallet_address': wallet_address
        })
        
    except Exception as e:
        logger.error(f"生成钱包nonce失败: {e}")
        return jsonify({'success': False, 'error': 'Failed to generate nonce'}), 500


@auth_bp.route('/api/wallet/login', methods=['POST'])
@rate_limit(max_requests=3, window_minutes=15, feature_name="wallet_login")
@SecurityManager.csrf_protect
def wallet_login():
    """验证钱包签名并登录用户"""
    try:
        data = request.get_json()
        wallet_address = data.get('wallet_address')
        signature = data.get('signature')
        nonce = data.get('nonce')
        
        if not all([wallet_address, signature, nonce]):
            return jsonify({'success': False, 'error': 'Missing required parameters'}), 400
        
        user = verify_wallet_login(wallet_address, signature, nonce)
        
        if not user:
            return jsonify({'success': False, 'error': 'Wallet authentication failed'}), 401
        
        session_nonce_key = f'wallet_nonce_{wallet_address.lower()}'
        if session_nonce_key in session:
            del session[session_nonce_key]
        
        session.permanent = True
        session['authenticated'] = True
        session['email'] = user.email
        session['role'] = user.role
        session['user_id'] = user.id
        session['login_method'] = 'wallet'
        session['wallet_address'] = user.wallet_address
        
        logger.info(f"钱包用户 {user.wallet_address} 登录成功，用户ID: {user.id}")
        
        try:
            client_ip = get_client_ip()
            
            login_record = LoginRecord(
                email=user.email,
                successful=True,
                ip_address=client_ip,
                login_location="Web3钱包登录"
            )
            db.session.add(login_record)
            db.session.commit()
        except Exception as e:
            logger.error(f"保存钱包登录记录失败: {e}")
        
        redirect_url = session.get('next_url', url_for('index'))
        if 'next_url' in session:
            del session['next_url']
        
        return jsonify({
            'success': True,
            'message': 'Wallet login successful',
            'redirect_url': redirect_url,
            'user': {
                'id': user.id,
                'name': user.name,
                'email': user.email,
                'wallet_address': user.wallet_address,
                'role': user.role
            }
        })
        
    except Exception as e:
        logger.error(f"钱包登录失败: {e}")
        return jsonify({'success': False, 'error': 'Wallet login failed'}), 500


@auth_bp.route('/unauthorized')
def unauthorized():
    """显示未授权页面"""
    return render_template('unauthorized.html')


@auth_bp.route('/logout')
def logout():
    """处理用户登出 / Handle user logout"""
    current_lang = g.language
    
    session.clear()
    session['language'] = current_lang
    
    if current_lang == 'en':
        flash('You have successfully logged out', 'info')
    else:
        flash('您已成功退出登录', 'info')
        
    return redirect(url_for('auth.login'))


@auth_bp.route('/register', methods=['GET', 'POST'])
@SecurityManager.csrf_protect
def register():
    """用户注册页面"""
    if request.method == 'GET':
        return render_template('register.html')
    
    try:
        email = request.form.get('email', '').strip()
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not email or not password:
            flash('邮箱和密码为必填项', 'error')
            return render_template('register.html')
        
        # Validate password strength using SOC2 password policy
        validation = password_policy_manager.validate_password_strength(password)
        if not validation.is_valid:
            errors = validation.get_errors(g.language)
            flash(' '.join(errors), 'danger')
            return render_template('register.html')
        
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            flash('邮箱格式无效', 'error')
            return render_template('register.html')
        
        existing_user = UserAccess.query.filter_by(email=email.lower()).first()
        if existing_user:
            flash('该邮箱已注册', 'error')
            return render_template('register.html')
        
        if username:
            existing_username = UserAccess.query.filter_by(username=username.lower()).first()
            if existing_username:
                flash('该用户名已存在', 'error')
                return render_template('register.html')
        
        new_user = UserAccess(
            name=username or email.split('@')[0],
            email=email.lower(),
            username=username.lower() if username else None,
            role='client'
        )
        
        new_user.set_password(password)
        
        verification_token = new_user.generate_email_verification_token()
        
        db.session.add(new_user)
        db.session.commit()
        
        user_language = g.get('language', 'zh')
        send_verification_email(email, verification_token, user_language)
        
        if user_language == 'en':
            flash('Registration successful! Please check your email and click the verification link to complete registration', 'success')
        else:
            flash('注册成功！请检查您的邮箱并点击验证链接完成注册', 'success')
        return redirect(url_for('auth.login'))
        
    except Exception as e:
        logger.error(f"注册错误: {e}")
        flash('注册失败，请稍后重试', 'error')
        return render_template('register.html')


@auth_bp.route('/verify-email/<token>')
def verify_email_token(token):
    """验证邮箱令牌"""
    try:
        user = UserAccess.query.filter_by(email_verification_token=token).first()
        
        if not user:
            user_language = g.get('language', 'zh')
            if user_language == 'en':
                flash('Invalid verification link', 'error')
            else:
                flash('无效的验证链接', 'error')
            return redirect(url_for('auth.login'))
        
        user.verify_email()
        db.session.commit()
        
        user_language = g.get('language', 'zh')
        if user_language == 'en':
            flash('Email verification successful! You can now log in', 'success')
        else:
            flash('邮箱验证成功！现在可以登录了', 'success')
        return redirect(url_for('auth.login'))
        
    except Exception as e:
        logger.error(f"邮箱验证错误: {e}")
        user_language = g.get('language', 'zh')
        if user_language == 'en':
            flash('Verification failed, please try again', 'error')
        else:
            flash('验证失败，请重试', 'error')
        return redirect(url_for('auth.login'))
