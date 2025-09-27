"""
User Authentication Module
用户认证模块 - 核心认证逻辑

提供用户登录验证、邮箱验证、会话管理等功能
注意：已移除Web3钱包认证相关功能，专注于传统认证方式
"""

import hashlib
import os
import logging
import secrets
import time
from datetime import datetime
from flask import request, redirect, url_for, session
from functools import wraps
from sqlalchemy import or_

# 设置日志 - 生产环境使用INFO级别
log_level = logging.INFO if os.environ.get('FLASK_ENV') == 'production' else logging.DEBUG
logging.basicConfig(level=log_level)

def get_authorized_emails():
    """获取授权邮箱列表，优先从数据库获取，然后从环境变量获取"""
    # 首先从数据库中检查是否有授权用户
    try:
        from ..models import UserAccess
        from ..database import db
        
        authorized_users = UserAccess.query.all()
        if authorized_users:
            valid_users = [user for user in authorized_users if user.has_access]
            if valid_users:
                emails = [user.email for user in valid_users]
                logging.debug(f"从数据库获取到 {len(emails)} 个有效授权邮箱")
                return emails
            else:
                logging.debug("数据库中没有有效授权用户")
    except Exception as e:
        logging.error(f"从数据库获取授权用户时出错: {str(e)}")
    
    # 如果数据库中没有授权用户，从环境变量中获取邮箱列表
    env_emails = os.environ.get('AUTHORIZED_EMAILS')
    if env_emails:
        # 使用逗号分隔多个邮箱
        emails = [email.strip() for email in env_emails.split(',')]
        logging.debug(f"从环境变量获取到 {len(emails)} 个授权邮箱")
        return emails
    
    # 生产环境必须配置授权邮箱
    if os.environ.get('FLASK_ENV') == 'production':
        logging.error("Production environment must configure AUTHORIZED_EMAILS")
        return []
    
    # 仅开发环境使用默认测试邮箱
    logging.warning("Using test emails for development environment only")
    return ['test@localhost']

def verify_password_login(email_or_username, password):
    """验证邮箱/用户名和密码登录"""
    if not email_or_username or not password:
        logging.warning("登录验证失败: 缺少邮箱/用户名或密码")
        return None
    
    # 清理输入
    email_or_username = email_or_username.lower().strip()
    
    try:
        from ..models import UserAccess
        from ..database import db
        
        # 查找用户（支持邮箱或用户名登录）
        user = UserAccess.query.filter(
            or_(UserAccess.email == email_or_username,
                UserAccess.username == email_or_username)
        ).first()
        
        if not user:
            logging.warning(f"用户不存在: {email_or_username}")
            return None
        
        # 检查邮箱是否已验证
        if not user.is_email_verified:
            logging.warning(f"用户 {email_or_username} 邮箱未验证")
            return None
        
        # 验证密码
        if not user.check_password(password):
            logging.warning(f"用户 {email_or_username} 密码错误")
            return None
        
        # 检查访问权限
        if not user.has_access:
            logging.warning(f"用户 {email_or_username} 访问权限已过期")
            return None
        
        # 更新最后登录时间
        user.last_login = datetime.utcnow()
        db.session.commit()
        
        logging.info(f"用户 {email_or_username} 密码登录成功")
        return user
        
    except Exception as e:
        logging.error(f"登录验证过程中出错: {str(e)}")
        return None

def hash_email(email):
    """使用SHA-256哈希邮箱地址，增加安全性"""
    # 创建哈希对象
    hasher = hashlib.sha256()
    # 使用邮箱地址更新哈希值（先转换为字节）
    hasher.update(email.lower().strip().encode('utf-8'))
    # 返回十六进制哈希值
    return hasher.hexdigest()

def create_verification_token(email):
    """为邮箱创建验证令牌"""
    # 使用邮箱哈希和时间戳创建令牌
    timestamp = str(int(time.time()))
    email_hash = hash_email(email)
    # 组合令牌
    token = f"{email_hash[:16]}{timestamp}"
    return token

def verify_email(email):
    """验证邮箱是否有效且授权访问"""
    if not email:
        logging.warning("验证失败: 未提供邮箱")
        return False
    
    # 清理和标准化输入的邮箱
    email = email.lower().strip()
    
    # 首先检查数据库中是否有此用户
    try:
        from ..models import UserAccess
        from ..database import db
        
        user = UserAccess.query.filter_by(email=email).first()
        if user:
            # 检查邮箱是否已验证
            if not user.is_email_verified:
                logging.warning(f"用户 {email} 邮箱未验证")
                return False
                
            # 更新最后登录时间
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            # 检查是否有有效访问权限
            if user.has_access:
                # 将用户角色存储在会话中
                session['role'] = user.role
                logging.info(f"用户 {user.name} ({email}) 验证成功，角色: {user.role}，剩余访问天数: {user.days_remaining}")
                return True
            else:
                logging.warning(f"用户 {user.name} ({email}) 验证失败: 访问权限已过期")
                return False
    except Exception as e:
        logging.error(f"验证用户 {email} 时数据库错误: {str(e)}")
    
    # 如果数据库中没有此用户或出错，尝试使用旧方法验证
    # 获取授权邮箱列表
    authorized_emails = get_authorized_emails()
    
    # 直接验证邮箱
    if email in authorized_emails:
        logging.info(f"邮箱 {email} 验证成功（通过授权列表）")
        
        # 尝试将此邮箱添加到数据库中
        try:
            from ..models import UserAccess
            from ..database import db
            
            # 检查用户是否已存在
            if not UserAccess.query.filter_by(email=email).first():
                new_user = UserAccess(
                    name=email.split('@')[0],  # 使用邮箱前缀作为用户名
                    email=email,
                    access_days=90,  # 默认给予90天访问权限
                    notes="通过授权列表自动添加"
                )
                db.session.add(new_user)
                db.session.commit()
                logging.info(f"已将邮箱 {email} 添加到用户访问数据库")
        except Exception as e:
            logging.error(f"将邮箱 {email} 添加到数据库时出错: {str(e)}")
        
        return True
    
    # 使用哈希值验证（适用于在环境变量中存储的邮箱哈希值）
    email_hash = hash_email(email)
    for auth_email in authorized_emails:
        # 如果授权邮箱已是哈希值（64位十六进制），则直接比较哈希值
        if len(auth_email) == 64 and all(c in '0123456789abcdef' for c in auth_email.lower()):
            if email_hash == auth_email.lower():
                logging.info(f"邮箱哈希值 {email_hash} 验证成功")
                return True
    
    # 验证失败
    logging.warning(f"邮箱 {email} 验证失败")
    return False

def get_user_role(email=None):
    """获取用户角色"""
    # 首先尝试从会话中获取角色
    if session.get('role'):
        return session.get('role')
    
    # 如果会话中没有角色且提供了邮箱，从数据库查询
    if email:
        try:
            from ..models import UserAccess
            
            user = UserAccess.query.filter_by(email=email.lower().strip()).first()
            if user and user.has_access:
                # 将角色存储到会话中
                session['role'] = user.role
                return user.role
        except Exception as e:
            logging.error(f"查询用户角色时出错: {str(e)}")
    
    # 默认返回guest角色
    return 'guest'

def get_user_by_email(email):
    """根据邮箱获取用户"""
    if not email:
        return None
    
    try:
        from ..models import UserAccess
        
        user = UserAccess.query.filter_by(email=email.lower().strip()).first()
        return user
    except Exception as e:
        logging.error(f"根据邮箱获取用户时出错: {str(e)}")
        return None

def get_user_by_username(username):
    """根据用户名获取用户"""
    if not username:
        return None
    
    try:
        from ..models import UserAccess
        
        user = UserAccess.query.filter_by(username=username.lower().strip()).first()
        return user
    except Exception as e:
        logging.error(f"根据用户名获取用户时出错: {str(e)}")
        return None

def create_user(name, email, username=None, password=None, role='guest', company=None, position=None, access_days=30):
    """创建新用户"""
    try:
        from ..models import UserAccess
        from ..database import db
        from werkzeug.security import generate_password_hash
        
        # 检查邮箱是否已存在
        if UserAccess.query.filter_by(email=email.lower().strip()).first():
            logging.warning(f"创建用户失败: 邮箱 {email} 已存在")
            return None
        
        # 检查用户名是否已存在
        if username and UserAccess.query.filter_by(username=username.lower().strip()).first():
            logging.warning(f"创建用户失败: 用户名 {username} 已存在")
            return None
        
        # 创建用户
        new_user = UserAccess(
            name=name,
            email=email.lower().strip(),
            username=username.lower().strip() if username else None,
            password_hash=generate_password_hash(password) if password else None,
            role=role,
            company=company,
            position=position,
            access_days=access_days,
            is_email_verified=True,  # 新创建的用户默认邮箱已验证
            notes=f"用户创建于 {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        logging.info(f"成功创建用户: {email} (角色: {role})")
        return new_user
        
    except Exception as e:
        logging.error(f"创建用户时出错: {str(e)}")
        return None

def update_user_access(user_id, access_days=None, role=None, notes=None):
    """更新用户访问权限"""
    try:
        from ..models import UserAccess
        from ..database import db
        from datetime import timedelta
        
        user = UserAccess.query.get(user_id)
        if not user:
            logging.warning(f"更新用户访问权限失败: 用户ID {user_id} 不存在")
            return False
        
        if access_days is not None:
            user.access_days = access_days
            user.expires_at = datetime.utcnow() + timedelta(days=access_days)
        
        if role is not None:
            user.role = role
        
        if notes is not None:
            user.notes = notes
        
        db.session.commit()
        
        logging.info(f"成功更新用户 {user.email} 的访问权限")
        return True
        
    except Exception as e:
        logging.error(f"更新用户访问权限时出错: {str(e)}")
        return False

def login_required(view_function):
    """装饰器：要求用户登录才能访问特定路由"""
    @wraps(view_function)
    def wrapped_view(*args, **kwargs):
        # 检查用户是否已经登录
        if not session.get('authenticated'):
            # 存储请求的URL，以便登录后重定向
            session['next_url'] = request.url
            # 未登录，重定向到登录页面
            logging.warning(f"未授权访问: {request.path} 重定向到登录页面")
            return redirect(url_for('auth.login'))
        
        # 已登录，继续正常访问
        return view_function(*args, **kwargs)
        
    return wrapped_view

def logout_user():
    """用户登出"""
    try:
        user_email = session.get('email')
        
        # 清除会话数据
        session.clear()
        
        logging.info(f"用户 {user_email} 成功登出")
        return True
        
    except Exception as e:
        logging.error(f"用户登出时出错: {str(e)}")
        return False

def get_current_user():
    """获取当前登录用户"""
    if not session.get('authenticated'):
        return None
    
    user_email = session.get('email')
    if not user_email:
        return None
    
    return get_user_by_email(user_email)

def check_user_permission(required_roles):
    """检查用户权限"""
    if not session.get('authenticated'):
        return False
    
    current_role = session.get('role', 'guest')
    
    # Owner拥有所有权限
    if current_role == 'owner':
        return True
    
    # 检查角色权限
    if isinstance(required_roles, str):
        required_roles = [required_roles]
    
    return current_role in required_roles