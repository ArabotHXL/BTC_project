"""
CRM服务层基础类
CRM Service Layer Base Classes

提供所有服务类的基础功能
Provides base functionality for all service classes
"""

from flask import session


class BaseService:
    """
    CRM服务基类
    Base service class for CRM operations
    
    提供通用的服务层方法，如用户过滤、数据转换等
    Provides common service layer methods like user filtering, data conversion, etc.
    """
    
    @staticmethod
    def get_user_id():
        """
        获取当前登录用户ID
        Get current logged-in user ID
        
        Returns:
            int or None: 用户ID
        """
        return session.get('user_id')
    
    @staticmethod
    def filter_by_user(query, model):
        """
        按当前用户过滤查询
        Filter query by current user
        
        Args:
            query: SQLAlchemy查询对象
            model: 模型类，需要有created_by_id字段
            
        Returns:
            query: 过滤后的查询对象
        """
        user_id = BaseService.get_user_id()
        return query.filter(model.created_by_id == user_id)
    
    @staticmethod
    def safe_float(value, default=0.0):
        """
        安全转换为float，防止NaN和异常
        Safely convert to float, preventing NaN and exceptions
        
        Args:
            value: 待转换的值
            default (float): 转换失败时的默认值
            
        Returns:
            float: 转换后的值或默认值
        """
        try:
            return float(value) if value is not None else default
        except (ValueError, TypeError):
            return default
    
    @staticmethod
    def safe_int(value, default=0):
        """
        安全转换为int，防止异常
        Safely convert to int, preventing exceptions
        
        Args:
            value: 待转换的值
            default (int): 转换失败时的默认值
            
        Returns:
            int: 转换后的值或默认值
        """
        try:
            return int(value) if value is not None else default
        except (ValueError, TypeError):
            return default
    
    @staticmethod
    def safe_percentage(numerator, denominator, default=0.0):
        """
        安全计算百分比
        Safely calculate percentage
        
        Args:
            numerator: 分子
            denominator: 分母
            default (float): 分母为0时的默认值
            
        Returns:
            float: 百分比值（0-100）
        """
        try:
            if denominator and denominator > 0:
                return round((float(numerator) / float(denominator)) * 100, 2)
            return default
        except (ValueError, TypeError, ZeroDivisionError):
            return default
