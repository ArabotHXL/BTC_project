"""
权限控制装饰器
提供细粒度的功能访问控制
"""

from functools import wraps
from flask import session, redirect, url_for, render_template, flash
import logging

def requires_role(required_roles):
    """
    角色权限装饰器
    参数：required_roles - 允许访问的角色列表（字符串或列表）
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 检查用户是否已登录
            if not session.get('authenticated'):
                flash('请先登录以访问此功能', 'warning')
                return redirect(url_for('auth.login'))
            
            # 标准化角色列表
            if isinstance(required_roles, str):
                roles = [required_roles]
            else:
                roles = required_roles
            
            # 获取当前用户角色
            current_role = session.get('role', 'guest')
            
            # Owner拥有所有权限
            if current_role == 'owner':
                return func(*args, **kwargs)
            
            # 检查角色权限
            if current_role in roles:
                return func(*args, **kwargs)
            
            # 权限不足
            logging.warning(f"用户 {session.get('email')} (角色: {current_role}) 尝试访问需要 {roles} 权限的功能")
            return render_template('errors/403.html', 
                                 message=f'此功能需要以下角色权限: {", ".join(roles)}',
                                 required_roles=roles,
                                 current_role=current_role), 403
        
        return wrapper
    return decorator

def requires_owner_only(func):
    """仅限拥有者访问的装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not session.get('authenticated'):
            flash('请先登录以访问此功能', 'warning')
            return redirect(url_for('auth.login'))
        
        current_role = session.get('role', 'guest')
        if current_role != 'owner':
            logging.warning(f"用户 {session.get('email')} (角色: {current_role}) 尝试访问拥有者专属功能")
            return render_template('errors/403.html', 
                                 message='此功能仅限系统拥有者访问',
                                 required_roles=['owner'],
                                 current_role=current_role), 403
        
        return func(*args, **kwargs)
    return wrapper

def requires_admin_or_owner(func):
    """需要管理员或拥有者权限的装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not session.get('authenticated'):
            flash('请先登录以访问此功能', 'warning')
            return redirect(url_for('auth.login'))
        
        current_role = session.get('role', 'guest')
        if current_role not in ['owner', 'admin']:
            logging.warning(f"用户 {session.get('email')} (角色: {current_role}) 尝试访问管理员功能")
            return render_template('errors/403.html', 
                                 message='此功能需要管理员或拥有者权限',
                                 required_roles=['owner', 'admin'],
                                 current_role=current_role), 403
        
        return func(*args, **kwargs)
    return wrapper

def requires_crm_access(func):
    """需要CRM访问权限的装饰器 - 仅限拥有者和管理员"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not session.get('authenticated'):
            flash('请先登录以访问此功能', 'warning')
            return redirect(url_for('auth.login'))
        
        current_role = session.get('role', 'guest')
        if current_role not in ['owner', 'admin']:
            logging.warning(f"用户 {session.get('email')} (角色: {current_role}) 尝试访问CRM功能")
            return render_template('errors/403.html', 
                                 message='CRM系统仅限拥有者和管理员使用',
                                 required_roles=['owner', 'admin'],
                                 current_role=current_role), 403
        
        return func(*args, **kwargs)
    return wrapper

def requires_billing_access(func):
    """需要计费访问权限的装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not session.get('authenticated'):
            flash('请先登录以访问此功能', 'warning')
            return redirect(url_for('auth.login'))
        
        current_role = session.get('role', 'guest')
        if current_role not in ['owner', 'admin']:
            logging.warning(f"用户 {session.get('email')} (角色: {current_role}) 尝试访问计费功能")
            return render_template('errors/403.html', 
                                 message='计费系统仅限拥有者和管理员使用',
                                 required_roles=['owner', 'admin'],
                                 current_role=current_role), 403
        
        return func(*args, **kwargs)
    return wrapper

def requires_user_management_access(func):
    """需要用户管理访问权限的装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not session.get('authenticated'):
            flash('请先登录以访问此功能', 'warning')
            return redirect(url_for('auth.login'))
        
        current_role = session.get('role', 'guest')
        if current_role not in ['owner', 'admin']:
            logging.warning(f"用户 {session.get('email')} (角色: {current_role}) 尝试访问用户管理功能")
            return render_template('errors/403.html', 
                                 message='用户管理功能仅限拥有者和管理员使用',
                                 required_roles=['owner', 'admin'],
                                 current_role=current_role), 403
        
        return func(*args, **kwargs)
    return wrapper

def api_key_required(func):
    """API密钥验证装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
        
        if not api_key:
            return {'error': 'API密钥未提供'}, 401
        
        # 这里应该验证API密钥的有效性
        # 简单实现：检查是否以umm_开头
        if not api_key.startswith('umm_'):
            return {'error': 'API密钥格式无效'}, 401
        
        # 在实际应用中，这里应该从数据库验证API密钥
        return func(*args, **kwargs)
    
    return wrapper

def log_access(func):
    """访问日志装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        user_email = session.get('email', 'anonymous')
        user_role = session.get('role', 'guest')
        ip_address = request.remote_addr
        
        logging.info(f"用户访问: {user_email} (角色: {user_role}) - IP: {ip_address} - 功能: {func.__name__}")
        
        return func(*args, **kwargs)
    
    return wrapper