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
                return redirect(url_for('login'))
            
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
            return render_template('unauthorized.html', 
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
            return redirect(url_for('login'))
        
        current_role = session.get('role', 'guest')
        if current_role != 'owner':
            logging.warning(f"用户 {session.get('email')} (角色: {current_role}) 尝试访问拥有者专属功能")
            return render_template('unauthorized.html', 
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
            return redirect(url_for('login'))
        
        current_role = session.get('role', 'guest')
        if current_role not in ['owner', 'admin']:
            logging.warning(f"用户 {session.get('email')} (角色: {current_role}) 尝试访问管理员功能")
            return render_template('unauthorized.html', 
                                 message='此功能需要管理员或拥有者权限',
                                 required_roles=['owner', 'admin'],
                                 current_role=current_role), 403
        
        return func(*args, **kwargs)
    return wrapper

def requires_crm_access(func):
    """需要CRM访问权限的装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not session.get('authenticated'):
            flash('请先登录以访问此功能', 'warning')
            return redirect(url_for('login'))
        
        current_role = session.get('role', 'guest')
        if current_role not in ['owner', 'admin', 'manager', 'mining_site']:
            logging.warning(f"用户 {session.get('email')} (角色: {current_role}) 尝试访问CRM功能")
            return render_template('unauthorized.html', 
                                 message='此功能需要CRM访问权限',
                                 required_roles=['owner', 'admin', 'manager', 'mining_site'],
                                 current_role=current_role), 403
        
        return func(*args, **kwargs)
    return wrapper

def requires_network_analysis_access(func):
    """需要网络分析访问权限的装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not session.get('authenticated'):
            flash('请先登录以访问此功能', 'warning')
            return redirect(url_for('login'))
        
        current_role = session.get('role', 'guest')
        if current_role not in ['owner', 'admin', 'mining_site']:
            logging.warning(f"用户 {session.get('email')} (角色: {current_role}) 尝试访问网络分析功能")
            return render_template('unauthorized.html', 
                                 message='此功能需要网络分析访问权限',
                                 required_roles=['owner', 'admin', 'mining_site'],
                                 current_role=current_role), 403
        
        return func(*args, **kwargs)
    return wrapper

def requires_batch_calculator_access(func):
    """需要批量计算器访问权限的装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not session.get('authenticated'):
            flash('请先登录以访问此功能', 'warning')
            return redirect(url_for('login'))
        
        current_role = session.get('role', 'guest')
        if current_role not in ['owner', 'admin', 'mining_site']:
            logging.warning(f"用户 {session.get('email')} (角色: {current_role}) 尝试访问批量计算器功能")
            return render_template('unauthorized.html', 
                                 message='此功能需要批量计算器访问权限',
                                 required_roles=['owner', 'admin', 'mining_site'],
                                 current_role=current_role), 403
        
        return func(*args, **kwargs)
    return wrapper

# 数据访问权限装饰器
def requires_own_data_only(user_id_param='user_id'):
    """
    仅访问自己数据的装饰器
    适用于CRM中mining_site角色只能查看自己创建的数据
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not session.get('authenticated'):
                flash('请先登录以访问此功能', 'warning')
                return redirect(url_for('login'))
            
            current_role = session.get('role', 'guest')
            current_user_id = session.get('user_id')
            
            # Owner和Admin可以访问所有数据
            if current_role in ['owner', 'admin']:
                return func(*args, **kwargs)
            
            # 检查请求的数据是否属于当前用户
            requested_user_id = kwargs.get(user_id_param)
            if requested_user_id and str(requested_user_id) != str(current_user_id):
                logging.warning(f"用户 {session.get('email')} 尝试访问其他用户的数据")
                return render_template('unauthorized.html', 
                                     message='您只能访问自己创建的数据',
                                     current_role=current_role), 403
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator

def log_access_attempt(feature_name):
    """记录功能访问尝试的装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            user_email = session.get('email', '匿名用户')
            user_role = session.get('role', '未知角色')
            
            logging.info(f"功能访问: {feature_name} - 用户: {user_email} (角色: {user_role})")
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator

# 组合装饰器示例
def requires_advanced_features(func):
    """需要高级功能权限（批量计算器、网络分析等）"""
    @requires_role(['owner', 'admin', 'mining_site'])
    @log_access_attempt('高级功能')
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper

# 订阅计划相关（临时占位函数）
def get_user_plan(user_id=None):
    """获取用户订阅计划 - 占位函数"""
    # TODO: 实现订阅计划逻辑
    return 'free'

def get_user_subscription(user_id=None):
    """获取用户订阅信息 - 占位函数"""
    # TODO: 实现订阅信息逻辑
    return {'plan': 'free', 'status': 'active'}

def check_miner_limit(user_id=None):
    """检查用户矿机数量限制 - 占位函数"""
    # TODO: 实现矿机数量限制检查
    return True

def require_plan(plan_name):
    """需要特定计划的装饰器 - 占位实现"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # TODO: 实现计划检查
            return func(*args, **kwargs)
        return wrapper
    return decorator

def require_feature(feature_name):
    """需要特定功能的装饰器 - 占位实现"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # TODO: 实现功能检查
            return func(*args, **kwargs)
        return wrapper
    return decorator

def allow_advanced_analytics(func):
    """允许高级分析的装饰器 - 占位实现"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        # TODO: 实现高级分析权限检查
        return func(*args, **kwargs)
    return wrapper

class UpgradeRequired(Exception):
    """需要升级异常 - 占位类"""
    pass

def requires_subscription_plan(required_plan):
    """需要特定订阅计划的装饰器 - 占位实现"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # TODO: 实现订阅计划检查
            return func(*args, **kwargs)
        return wrapper
    return decorator