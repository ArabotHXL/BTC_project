import hashlib
import os
import logging
import secrets
import time
from datetime import datetime
from flask import request, redirect, url_for, session
from functools import wraps
from models import UserAccess
from db import db
from eth_account.messages import encode_defunct
from eth_account import Account

# 设置日志 - 生产环境使用INFO级别
log_level = logging.INFO if os.environ.get('FLASK_ENV') == 'production' else logging.DEBUG
logging.basicConfig(level=log_level)

def get_authorized_emails():
    """获取授权邮箱列表，优先从数据库获取，然后从环境变量获取"""
    # 首先从数据库中检查是否有授权用户
    try:
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
    
    # 查找用户（支持邮箱或用户名登录）
    from sqlalchemy import or_
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
    import time
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

def sync_user_roles(email):
    """Sync roles between User and UserAccess tables to prevent conflicts.
    UserAccess is the authoritative source for roles.
    
    Returns: The canonical role from UserAccess, or None if user not found
    """
    if not email:
        return None
    
    email = email.lower().strip()
    
    try:
        from models import User
        
        user_access = UserAccess.query.filter_by(email=email).first()
        user = User.query.filter_by(email=email).first()
        
        if not user_access:
            return None
        
        canonical_role = user_access.role
        
        if user and user.role != canonical_role:
            logging.warning(f"Role conflict detected for {email}: users.role='{user.role}' vs user_access.role='{canonical_role}'. Syncing to '{canonical_role}'")
            user.role = canonical_role
            db.session.commit()
            logging.info(f"Synced user role for {email} to '{canonical_role}'")
        
        return canonical_role
    except Exception as e:
        logging.error(f"Error syncing user roles for {email}: {str(e)}")
        return None


def get_user_role(email=None):
    """获取用户角色"""
    # 首先尝试从会话中获取角色
    if session.get('role'):
        return session.get('role')
    
    # 如果会话中没有角色且提供了邮箱，从数据库查询
    if email:
        try:
            sync_user_roles(email)
            
            user = UserAccess.query.filter_by(email=email.lower().strip()).first()
            if user and user.has_access:
                # 将角色存储到会话中
                session['role'] = user.role
                return user.role
        except Exception as e:
            logging.error(f"查询用户角色时出错: {str(e)}")
    
    # 默认返回guest角色
    return 'guest'

def generate_wallet_login_message(wallet_address, nonce):
    """生成钱包登录签名消息"""
    message = f"Welcome to HashInsight BTC Mining Calculator!\n\nSign this message to login with your wallet.\n\nWallet: {wallet_address}\nNonce: {nonce}\nTimestamp: {int(time.time())}"
    return message

def verify_wallet_signature(wallet_address, signature, message):
    """验证钱包签名"""
    try:
        # 编码消息
        message_hash = encode_defunct(text=message)
        
        # 恢复签名者地址
        recovered_address = Account.recover_message(message_hash, signature=signature)
        
        # 比较地址（不区分大小写）
        return recovered_address.lower() == wallet_address.lower()
    except Exception as e:
        logging.error(f"钱包签名验证失败: {e}")
        return False

def create_or_get_user_by_wallet(wallet_address):
    """根据钱包地址创建或获取用户"""
    if not wallet_address:
        return None
    
    # 标准化地址格式
    wallet_address = wallet_address.lower()
    
    # 查找现有用户
    user = UserAccess.query.filter_by(wallet_address=wallet_address).first()
    
    if user:
        logging.info(f"找到现有钱包用户: {wallet_address}")
        return user
    
    # 创建新用户
    try:
        # 生成用户名（基于钱包地址）
        username = f"wallet_{wallet_address[:8]}"
        
        # 检查用户名是否已存在，如果存在则添加数字后缀
        counter = 1
        original_username = username
        while UserAccess.query.filter_by(username=username).first():
            username = f"{original_username}_{counter}"
            counter += 1
        
        new_user = UserAccess(
            name=f"Wallet User {wallet_address[:8]}",
            email=f"wallet_{wallet_address[:8]}@wallet.local",  # 虚拟邮箱
            username=username,
            wallet_address=wallet_address,
            access_days=90,  # 默认90天访问权限
            role="guest",
            subscription_plan="free",
            notes="通过Web3钱包创建的用户"
        )
        
        # 标记钱包和邮箱为已验证
        new_user.wallet_verified = True
        new_user.is_email_verified = True
        
        db.session.add(new_user)
        db.session.commit()
        
        logging.info(f"创建新钱包用户: {wallet_address}")
        return new_user
        
    except Exception as e:
        logging.error(f"创建钱包用户失败: {e}")
        db.session.rollback()
        return None

def verify_wallet_login(wallet_address, signature, nonce):
    """验证钱包登录 - 增强nonce安全验证"""
    if not wallet_address or not signature or not nonce:
        logging.warning("钱包登录验证失败: 缺少必要参数")
        return None
    
    # 标准化地址格式
    wallet_address = wallet_address.lower()
    
    # CRITICAL FIX: 严格的nonce验证和过期检查
    user = UserAccess.query.filter_by(wallet_address=wallet_address).first()
    
    # 验证nonce是否存在且匹配（存储的或session中的）
    stored_nonce = None
    if user and user.wallet_nonce:
        stored_nonce = user.wallet_nonce
    else:
        # 检查session中的临时nonce
        from flask import session
        session_nonce_key = f'wallet_nonce_{wallet_address}'
        stored_nonce = session.get(session_nonce_key)
    
    if not stored_nonce:
        logging.warning(f"钱包登录验证失败: 未找到有效nonce - {wallet_address}")
        return None
    
    if stored_nonce != nonce:
        logging.warning(f"钱包登录验证失败: nonce不匹配 - {wallet_address}")
        return None
    
    # CRITICAL FIX: nonce过期验证 (5分钟TTL)
    try:
        nonce_parts = nonce.split('_')
        if len(nonce_parts) < 2:
            logging.warning(f"钱包登录验证失败: nonce格式无效 - {wallet_address}")
            return None
        
        nonce_timestamp = int(nonce_parts[0])
        current_timestamp = int(time.time())
        nonce_age = current_timestamp - nonce_timestamp
        
        # 5分钟TTL (300秒)
        if nonce_age > 300:
            logging.warning(f"钱包登录验证失败: nonce已过期 (age: {nonce_age}s) - {wallet_address}")
            # 立即清除过期的nonce
            if user:
                user.wallet_nonce = None
                db.session.commit()
            from flask import session
            session_nonce_key = f'wallet_nonce_{wallet_address}'
            if session_nonce_key in session:
                del session[session_nonce_key]
            return None
        
        logging.debug(f"Nonce验证通过: age={nonce_age}s (TTL=300s) - {wallet_address}")
        
    except (ValueError, IndexError) as e:
        logging.warning(f"钱包登录验证失败: nonce时间戳解析错误 - {wallet_address}: {e}")
        return None
    
    # 生成预期的消息
    message = generate_wallet_login_message(wallet_address, nonce)
    
    # 验证签名
    if not verify_wallet_signature(wallet_address, signature, message):
        logging.warning(f"钱包签名验证失败: {wallet_address}")
        return None
    
    # CRITICAL FIX: 立即清除使用过的nonce，防止重放攻击
    if user:
        user.wallet_nonce = None
    from flask import session
    session_nonce_key = f'wallet_nonce_{wallet_address}'
    if session_nonce_key in session:
        del session[session_nonce_key]
    
    # 查找或创建用户
    if not user:
        user = create_or_get_user_by_wallet(wallet_address)
    
    if not user:
        logging.warning(f"无法创建或查找钱包用户: {wallet_address}")
        return None
    
    # 检查访问权限
    if not user.has_access:
        logging.warning(f"钱包用户访问权限已过期: {wallet_address}")
        return None
    
    # 更新最后登录时间
    user.last_login = datetime.utcnow()
    
    db.session.commit()
    
    logging.info(f"钱包用户 {wallet_address} 登录成功，nonce已清除")
    return user

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