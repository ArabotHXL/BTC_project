"""
共享组件和工具
所有模块都可以使用的公共功能
"""

from .database import get_network_data, save_calculation_log
from .auth import require_permission, check_user_quota
from .utils import format_number, calculate_roi

__all__ = [
    'get_network_data',
    'save_calculation_log', 
    'require_permission',
    'check_user_quota',
    'format_number',
    'calculate_roi'
]