"""
CRM服务层 - 统一服务层基础架构
CRM Service Layer - Unified Service Layer Foundation

这个模块提供CRM系统的通用服务层功能，包括：
- 日期处理工具
- 响应格式化
- 认证装饰器
- 趋势计算
- 基础服务类
- 地理位置服务

使用示例：
    from crm_services import get_month_range, success_response, require_auth
    
    @crm_bp.route('/api/example')
    @require_auth
    def example_endpoint():
        user_id = get_current_user_id()
        ranges = get_month_range(12)
        return success_response(data={'ranges': ranges})
"""

from .base import BaseService
from .utils import (
    get_month_range,
    get_current_month_range,
    success_response,
    error_response,
    require_auth,
    get_current_user_id,
    calculate_monthly_trend,
    get_polling_interval,
    success_response_with_polling,
    can_access_all_data,
    apply_tenant_filter,
    get_tenant_filter,
    verify_resource_access
)

__all__ = [
    'BaseService',
    'get_month_range',
    'get_current_month_range',
    'success_response',
    'error_response',
    'require_auth',
    'get_current_user_id',
    'calculate_monthly_trend',
    'get_polling_interval',
    'success_response_with_polling',
    'can_access_all_data',
    'apply_tenant_filter',
    'get_tenant_filter',
    'verify_resource_access'
]

__version__ = '1.0.0'
