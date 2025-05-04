import os
import hashlib
import logging
from flask import session, redirect, url_for, flash, request

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 授权用户的邮箱列表 - 在实际应用中，这应该存储在数据库中并加密
# 也可以使用环境变量存储此列表
def get_authorized_emails():
    """获取授权邮箱列表，优先从环境变量获取"""
    env_emails = os.environ.get('AUTHORIZED_EMAILS')
    if env_emails:
        return [email.strip() for email in env_emails.split(',')]
    
    # 默认授权邮箱列表（仅在没有环境变量时使用）
    return [
        'user1@example.com',
        'user2@example.com',
        # 添加您想要授权的电子邮件
    ]

def hash_email(email):
    """使用SHA-256哈希邮箱地址，增加安全性"""
    return hashlib.sha256(email.lower().encode()).hexdigest()

def verify_email(email):
    """验证邮箱是否在授权列表中"""
    if not email:
        return False
        
    # 规范化邮箱地址（转换为小写）
    email = email.lower().strip()
    
    # 检查邮箱是否在授权列表中
    authorized_emails = get_authorized_emails()
    is_authorized = email in authorized_emails
    
    # 记录身份验证尝试（不记录完整邮箱，仅记录哈希值以保护隐私）
    email_hash = hash_email(email)
    if is_authorized:
        logger.info(f"授权成功: {email_hash[:8]}...")
    else:
        logger.warning(f"授权失败: {email_hash[:8]}... 尝试访问")
    
    return is_authorized

def login_required(view_function):
    """装饰器：要求用户登录才能访问特定路由"""
    def wrapped_view(*args, **kwargs):
        if 'authenticated' not in session or not session['authenticated']:
            # 保存用户想要访问的原始URL
            session['next_url'] = request.path
            flash('请先登录以访问该页面', 'warning')
            return redirect(url_for('login'))
        return view_function(*args, **kwargs)
    
    # 必须为Flask路由装饰器
    wrapped_view.__name__ = view_function.__name__
    return wrapped_view