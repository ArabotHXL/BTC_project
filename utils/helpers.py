"""通用工具函数"""
import logging
from flask import session, g, request
from functools import wraps

def get_user_role(email):
    """根据用户邮箱获取角色"""
    if not email:
        return "guest"
    
    # 特殊邮箱的角色映射
    role_mapping = {
        "owner@example.com": "owner",
        "admin@example.com": "admin", 
        "mine@example.com": "mining_site"
    }
    
    return role_mapping.get(email, "guest")

def has_role(required_roles):
    """检查当前用户是否拥有指定角色之一"""
    if isinstance(required_roles, str):
        required_roles = [required_roles]
    
    current_role = session.get('role', 'guest')
    return current_role in required_roles

def get_client_ip():
    """获取客户端IP地址"""
    if request.environ.get('HTTP_X_FORWARDED_FOR') is None:
        return request.environ['REMOTE_ADDR']
    else:
        return request.environ['HTTP_X_FORWARDED_FOR']

def safe_float(value, default=0.0):
    """安全转换为浮点数"""
    try:
        return float(value) if value is not None else default
    except (ValueError, TypeError):
        return default

def safe_int(value, default=0):
    """安全转换为整数"""
    try:
        return int(value) if value is not None else default
    except (ValueError, TypeError):
        return default

def format_currency(amount):
    """格式化货币显示"""
    if amount is None:
        return "$0.00"
    return f"${amount:,.2f}"

def format_percentage(value):
    """格式化百分比显示"""
    if value is None:
        return "0.00%"
    return f"{value:.2f}%"