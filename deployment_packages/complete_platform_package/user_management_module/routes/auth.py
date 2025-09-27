"""
Authentication Routes
认证路由 - 用户登录、注册、邮箱验证等
"""

from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, flash
from datetime import datetime
import logging
import sys
import os

# Add module paths to system path
module_root = os.path.dirname(os.path.dirname(__file__))
if module_root not in sys.path:
    sys.path.insert(0, module_root)

try:
    # Try relative imports first
    from ..auth.authentication import (
        verify_password_login, verify_email, logout_user, 
        create_user, get_current_user
    )
    from ..security.security_manager import SecurityManager
    from ..models import UserAccess, User, LoginRecord
    from ..database import db
except (ImportError, ValueError):
    try:
        # Try absolute imports from user_management_module
        from user_management_module.auth.authentication import (
            verify_password_login, verify_email, logout_user, 
            create_user, get_current_user
        )
        from user_management_module.security.security_manager import SecurityManager
        from user_management_module.models import UserAccess, User, LoginRecord
        from user_management_module.database import db
    except ImportError:
        # Final fallback for direct execution
        from auth.authentication import (
            verify_password_login, verify_email, logout_user, 
            create_user, get_current_user
        )
        from security.security_manager import SecurityManager
        from models import UserAccess, User, LoginRecord
        from database import db

logger = logging.getLogger(__name__)

# 创建蓝图
auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """用户登录"""
    if request.method == 'GET':
        # 如果用户已登录，重定向到仪表盘
        if session.get('authenticated'):
            return redirect(url_for('dashboard'))
        
        # 生成CSRF令牌
        csrf_token = SecurityManager.generate_csrf_token()
        
        return render_template('auth/login.html', 
                             title='用户登录',
                             csrf_token=csrf_token)
    
    # POST请求处理
    try:
        # 获取表单数据
        data = request.get_json() if request.is_json else request.form
        
        email_or_username = data.get('email_or_username', '').strip()
        password = data.get('password', '')
        remember_me = data.get('remember_me', False)
        
        if not email_or_username or not password:
            error = '请输入邮箱/用户名和密码'
            if request.is_json:
                return jsonify({'success': False, 'error': error}), 400
            else:
                flash(error, 'error')
                return redirect(url_for('auth.login'))
        
        # 验证用户登录
        user = verify_password_login(email_or_username, password)
        
        if user:
            # 登录成功，设置会话
            session['authenticated'] = True
            session['email'] = user.email
            session['user_id'] = user.id
            session['name'] = user.name
            session['role'] = user.role
            session.permanent = remember_me
            
            # 记录登录
            login_record = LoginRecord(
                user_id=user.id,
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent', ''),
                login_method='password'
            )
            db.session.add(login_record)
            db.session.commit()
            
            logger.info(f"用户 {user.email} 登录成功")
            
            # 获取重定向URL
            next_url = session.pop('next_url', None) or url_for('dashboard')
            
            if request.is_json:
                return jsonify({
                    'success': True, 
                    'message': '登录成功',
                    'redirect_url': next_url
                })
            else:
                flash('登录成功', 'success')
                return redirect(next_url)
        else:
            error = '邮箱/用户名或密码错误'
            if request.is_json:
                return jsonify({'success': False, 'error': error}), 401
            else:
                flash(error, 'error')
                return redirect(url_for('auth.login'))
                
    except Exception as e:
        logger.error(f"登录过程中出错: {e}")
        error = '登录过程中出现错误，请重试'
        if request.is_json:
            return jsonify({'success': False, 'error': error}), 500
        else:
            flash(error, 'error')
            return redirect(url_for('auth.login'))

@auth_bp.route('/logout')
def logout():
    """用户登出"""
    try:
        user_email = session.get('email')
        
        # 更新登录记录
        if session.get('user_id'):
            login_record = LoginRecord.query.filter_by(
                user_id=session['user_id']
            ).order_by(LoginRecord.login_time.desc()).first()
            
            if login_record and not login_record.logout_time:
                login_record.logout_time = datetime.utcnow()
                login_record.session_duration = int(
                    (login_record.logout_time - login_record.login_time).total_seconds()
                )
                db.session.commit()
        
        # 登出用户
        logout_user()
        
        flash('您已成功退出', 'success')
        logger.info(f"用户 {user_email} 成功登出")
        
        return redirect(url_for('auth.login'))
        
    except Exception as e:
        logger.error(f"登出过程中出错: {e}")
        flash('登出过程中出现错误', 'error')
        return redirect(url_for('index'))

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """用户注册"""
    if request.method == 'GET':
        # 生成CSRF令牌
        csrf_token = SecurityManager.generate_csrf_token()
        
        return render_template('auth/register.html', 
                             title='用户注册',
                             csrf_token=csrf_token)
    
    # POST请求处理
    try:
        # 获取表单数据
        data = request.get_json() if request.is_json else request.form
        
        name = SecurityManager.sanitize_input(data.get('name', '').strip())
        email = SecurityManager.sanitize_input(data.get('email', '').strip().lower())
        username = SecurityManager.sanitize_input(data.get('username', '').strip().lower())
        password = data.get('password', '')
        confirm_password = data.get('confirm_password', '')
        company = SecurityManager.sanitize_input(data.get('company', '').strip())
        position = SecurityManager.sanitize_input(data.get('position', '').strip())
        
        # 验证输入
        if not all([name, email, password]):
            error = '请填写所有必需字段'
            if request.is_json:
                return jsonify({'success': False, 'error': error}), 400
            else:
                flash(error, 'error')
                return redirect(url_for('auth.register'))
        
        # 验证邮箱格式
        if not SecurityManager.validate_email(email):
            error = '邮箱格式无效'
            if request.is_json:
                return jsonify({'success': False, 'error': error}), 400
            else:
                flash(error, 'error')
                return redirect(url_for('auth.register'))
        
        # 验证密码
        password_valid, password_message = SecurityManager.validate_password_strength(password)
        if not password_valid:
            if request.is_json:
                return jsonify({'success': False, 'error': password_message}), 400
            else:
                flash(password_message, 'error')
                return redirect(url_for('auth.register'))
        
        # 验证密码确认
        if password != confirm_password:
            error = '两次输入的密码不一致'
            if request.is_json:
                return jsonify({'success': False, 'error': error}), 400
            else:
                flash(error, 'error')
                return redirect(url_for('auth.register'))
        
        # 创建用户
        user = create_user(
            name=name,
            email=email,
            username=username if username else None,
            password=password,
            role='guest',  # 新注册用户默认为guest
            company=company,
            position=position,
            access_days=30  # 默认30天访问权限
        )
        
        if user:
            logger.info(f"用户 {email} 注册成功")
            
            message = '注册成功！您现在可以登录了。'
            if request.is_json:
                return jsonify({
                    'success': True, 
                    'message': message,
                    'redirect_url': url_for('auth.login')
                })
            else:
                flash(message, 'success')
                return redirect(url_for('auth.login'))
        else:
            error = '注册失败，邮箱或用户名可能已存在'
            if request.is_json:
                return jsonify({'success': False, 'error': error}), 400
            else:
                flash(error, 'error')
                return redirect(url_for('auth.register'))
                
    except Exception as e:
        logger.error(f"注册过程中出错: {e}")
        error = '注册过程中出现错误，请重试'
        if request.is_json:
            return jsonify({'success': False, 'error': error}), 500
        else:
            flash(error, 'error')
            return redirect(url_for('auth.register'))

@auth_bp.route('/verify-email')
def verify_email_endpoint():
    """邮箱验证端点"""
    try:
        token = request.args.get('token')
        email = request.args.get('email')
        
        if not token or not email:
            flash('验证链接无效', 'error')
            return redirect(url_for('auth.login'))
        
        # 验证邮箱
        user = UserAccess.query.filter_by(email=email.lower().strip()).first()
        
        if not user:
            flash('用户不存在', 'error')
            return redirect(url_for('auth.login'))
        
        if user.email_verification_token == token:
            user.verify_email()
            db.session.commit()
            
            flash('邮箱验证成功！您现在可以登录了。', 'success')
            logger.info(f"用户 {email} 邮箱验证成功")
            
            return redirect(url_for('auth.login'))
        else:
            flash('验证链接无效或已过期', 'error')
            return redirect(url_for('auth.login'))
            
    except Exception as e:
        logger.error(f"邮箱验证过程中出错: {e}")
        flash('验证过程中出现错误', 'error')
        return redirect(url_for('auth.login'))

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """忘记密码"""
    if request.method == 'GET':
        # 生成CSRF令牌
        csrf_token = SecurityManager.generate_csrf_token()
        
        return render_template('auth/forgot_password.html', 
                             title='忘记密码',
                             csrf_token=csrf_token)
    
    # POST请求处理
    try:
        # 获取表单数据
        data = request.get_json() if request.is_json else request.form
        email = SecurityManager.sanitize_input(data.get('email', '').strip().lower())
        
        if not email:
            error = '请输入邮箱地址'
            if request.is_json:
                return jsonify({'success': False, 'error': error}), 400
            else:
                flash(error, 'error')
                return redirect(url_for('auth.forgot_password'))
        
        # 验证邮箱格式
        if not SecurityManager.validate_email(email):
            error = '邮箱格式无效'
            if request.is_json:
                return jsonify({'success': False, 'error': error}), 400
            else:
                flash(error, 'error')
                return redirect(url_for('auth.forgot_password'))
        
        # 查找用户
        user = UserAccess.query.filter_by(email=email).first()
        
        if user:
            # 生成重置令牌
            reset_token = SecurityManager.generate_secure_token()
            user.password_reset_token = reset_token
            user.password_reset_expires = datetime.utcnow() + timedelta(hours=24)
            db.session.commit()
            
            # 这里应该发送邮件，但为了简化，我们只记录日志
            logger.info(f"为用户 {email} 生成了密码重置令牌: {reset_token}")
        
        # 无论用户是否存在，都显示相同的消息（安全考虑）
        message = '如果该邮箱存在于我们的系统中，您将收到密码重置链接。'
        if request.is_json:
            return jsonify({'success': True, 'message': message})
        else:
            flash(message, 'info')
            return redirect(url_for('auth.login'))
            
    except Exception as e:
        logger.error(f"忘记密码处理中出错: {e}")
        error = '处理请求时出现错误，请重试'
        if request.is_json:
            return jsonify({'success': False, 'error': error}), 500
        else:
            flash(error, 'error')
            return redirect(url_for('auth.forgot_password'))

@auth_bp.route('/check-auth')
def check_auth():
    """检查用户认证状态（API端点）"""
    try:
        if session.get('authenticated'):
            user = get_current_user()
            return jsonify({
                'authenticated': True,
                'user': {
                    'email': session.get('email'),
                    'name': session.get('name'),
                    'role': session.get('role'),
                    'user_id': session.get('user_id')
                } if user else None
            })
        else:
            return jsonify({'authenticated': False})
            
    except Exception as e:
        logger.error(f"检查认证状态时出错: {e}")
        return jsonify({'authenticated': False, 'error': str(e)}), 500