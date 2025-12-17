"""
CRM服务层工具函数
CRM Service Layer Utilities

提供日期处理、响应格式化、认证和趋势计算等通用工具
Provides common utilities for date handling, response formatting, auth, and trend calculations
"""

from datetime import datetime
from dateutil.relativedelta import relativedelta
from functools import wraps
from flask import jsonify, session
from sqlalchemy import func


def get_month_range(months=12):
    """
    生成过去N个月的日期范围
    Generate date ranges for the past N months
    
    Args:
        months (int): 月份数量，默认12个月
        
    Returns:
        list: 包含月份标签、起始和结束日期的字典列表
    """
    current = datetime.now()
    ranges = []
    
    for i in range(months - 1, -1, -1):
        month_date = current - relativedelta(months=i)
        month_start = month_date.replace(day=1)
        next_month = month_start + relativedelta(months=1)
        
        ranges.append({
            'month': month_start.strftime('%Y-%m'),
            'start': month_start,
            'end': next_month
        })
    
    return ranges


def get_current_month_range():
    """
    获取当前月的日期范围
    Get the current month's date range
    
    Returns:
        dict: 包含start和end的字典
    """
    current = datetime.now().replace(day=1)
    next_month = current + relativedelta(months=1)
    
    return {
        'start': current,
        'end': next_month
    }


def success_response(data=None, message='Success'):
    """
    统一成功响应格式
    Unified success response format
    
    Args:
        data: 响应数据
        message (str): 响应消息
        
    Returns:
        flask.Response: JSON响应
    """
    return jsonify({
        'success': True,
        'data': data,
        'message': message
    })


def error_response(message='Error', code=400):
    """
    统一错误响应格式
    Unified error response format
    
    Args:
        message (str): 错误消息
        code (int): HTTP状态码
        
    Returns:
        tuple: (flask.Response, status_code)
    """
    return jsonify({
        'success': False,
        'message': message
    }), code


def require_auth(f):
    """
    认证装饰器
    Authentication decorator
    
    检查用户是否已登录，未登录返回401错误
    Checks if user is logged in, returns 401 if not
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return error_response('Unauthorized', 401)
        return f(*args, **kwargs)
    return decorated_function


def get_current_user_id():
    """
    获取当前用户ID
    Get current user ID from session
    
    Returns:
        int or None: 用户ID，未登录返回None
    """
    return session.get('user_id')


def can_access_all_data():
    """
    检查当前用户是否可以访问所有数据（Owner/Admin）
    Check if current user can access all data (Owner/Admin roles)
    
    Returns:
        bool: True if user can access all data
    """
    role = session.get('role', 'guest')
    return role in ['owner', 'admin']


def apply_tenant_filter(query, model, user_id=None):
    """
    应用租户隔离过滤器
    Apply tenant isolation filter to query
    
    如果用户是Owner/Admin，返回原始查询（可以看到所有数据）
    否则只返回用户自己创建的数据
    
    Args:
        query: SQLAlchemy查询对象
        model: 模型类（必须有created_by_id字段）
        user_id: 用户ID（如果不提供，从session获取）
        
    Returns:
        SQLAlchemy查询对象（已过滤）
    """
    if can_access_all_data():
        return query
    
    if user_id is None:
        user_id = get_current_user_id()
    
    if user_id is None:
        return query.filter(False)
    
    if hasattr(model, 'created_by_id'):
        return query.filter(model.created_by_id == user_id)
    
    return query


def get_tenant_filter(model, user_id=None):
    """
    获取租户过滤条件（用于计数等场景）
    Get tenant filter condition for count queries etc.
    
    Args:
        model: 模型类（必须有created_by_id字段）
        user_id: 用户ID（如果不提供，从session获取）
        
    Returns:
        SQLAlchemy过滤条件或None（如果是Owner/Admin）
    """
    if can_access_all_data():
        return None
    
    if user_id is None:
        user_id = get_current_user_id()
    
    if user_id is None or not hasattr(model, 'created_by_id'):
        return None
    
    return model.created_by_id == user_id


def verify_resource_access(resource, user_id=None):
    """
    验证用户是否有权访问特定资源
    Verify if user has access to a specific resource
    
    Args:
        resource: 数据库资源对象（必须有created_by_id字段）
        user_id: 用户ID（如果不提供，从session获取）
        
    Returns:
        bool: True if user has access
    """
    if can_access_all_data():
        return True
    
    if user_id is None:
        user_id = get_current_user_id()
    
    if user_id is None:
        return False
    
    if hasattr(resource, 'created_by_id'):
        return resource.created_by_id == user_id
    
    return True


def calculate_monthly_trend(db_session, model, amount_field, date_field, user_id_field, user_id, months=12):
    """
    计算月度趋势（通用函数）
    Calculate monthly trend (generic function)
    
    Args:
        db_session: SQLAlchemy session对象（传入db.session避免循环导入）
        model: SQLAlchemy模型类
        amount_field: 金额字段
        date_field: 日期字段
        user_id_field: 用户ID字段
        user_id: 当前用户ID
        months (int): 月份数量，默认12个月
        
    Returns:
        list: 包含month和amount的字典列表
    """
    ranges = get_month_range(months)
    trend_data = []
    
    for range_info in ranges:
        amount = db_session.query(func.sum(amount_field))\
            .filter(
                user_id_field == user_id,
                date_field >= range_info['start'],
                date_field < range_info['end']
            )\
            .scalar() or 0
        
        trend_data.append({
            'month': range_info['month'],
            'amount': float(amount)
        })
    
    return trend_data


def get_polling_interval():
    """
    推荐的轮询间隔（秒）
    Recommended polling interval in seconds
    
    Returns:
        int: 轮询间隔秒数
    """
    return 30


def success_response_with_polling(data=None, message='Success'):
    """
    带轮询提示的成功响应格式
    Success response format with polling hint
    
    Args:
        data: 响应数据
        message (str): 响应消息
        
    Returns:
        flask.Response: JSON响应，包含轮询配置
    """
    return jsonify({
        'success': True,
        'data': data,
        'message': message,
        'polling': {
            'enabled': True,
            'interval': get_polling_interval()
        }
    })
