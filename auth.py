import hashlib
import os
import logging
from flask import request, redirect, url_for, session
from functools import wraps

# 设置日志
logging.basicConfig(level=logging.DEBUG)

def get_authorized_emails():
    """获取授权邮箱列表，优先从环境变量获取"""
    # 从环境变量中获取邮箱列表
    env_emails = os.environ.get('AUTHORIZED_EMAILS')
    if env_emails:
        # 使用逗号分隔多个邮箱
        emails = [email.strip() for email in env_emails.split(',')]
        logging.debug(f"从环境变量获取到 {len(emails)} 个授权邮箱")
        return emails
    
    # 默认授权邮箱列表
    default_emails = [
        'admin@example.com',
        'support@example.com',
        'btc@example.com'
    ]
    logging.debug(f"使用默认的 {len(default_emails)} 个授权邮箱")
    return default_emails

def hash_email(email):
    """使用SHA-256哈希邮箱地址，增加安全性"""
    # 创建哈希对象
    hasher = hashlib.sha256()
    # 使用邮箱地址更新哈希值（先转换为字节）
    hasher.update(email.lower().strip().encode('utf-8'))
    # 返回十六进制哈希值
    return hasher.hexdigest()

def verify_email(email):
    """验证邮箱是否在授权列表中"""
    # 获取授权邮箱列表
    authorized_emails = get_authorized_emails()
    
    # 清理和标准化输入的邮箱
    email = email.lower().strip() if email else ""
    
    # 直接验证邮箱
    if email in authorized_emails:
        logging.info(f"邮箱 {email} 验证成功")
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
            return redirect(url_for('login'))
        
        # 已登录，继续正常访问
        return view_function(*args, **kwargs)
        
    return wrapped_view