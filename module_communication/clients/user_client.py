"""
User Management Module API Client
用户管理模块API客户端
"""

import requests
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from ..common.config import config
from ..common.auth import jwt_manager
from ..common.utils import RetryMechanism, CircuitBreaker, format_error_response, request_logger

logger = logging.getLogger(__name__)

class UserManagementClient:
    """用户管理模块API客户端"""
    
    def __init__(self, api_key: str = None, base_url: str = None):
        self.module_config = config.get_module_config('user_management')
        self.base_url = base_url or self.module_config['base_url']
        self.api_key = api_key
        self.timeout = self.module_config['timeout']
        
        # 设置重试和熔断器
        self.retry = RetryMechanism(max_retries=self.module_config['max_retries'])
        self.circuit_breaker = CircuitBreaker()
        
        logger.info(f"Initialized User Management client for {self.base_url}")
    
    def _make_request(self, 
                     method: str, 
                     endpoint: str, 
                     data: Dict[str, Any] = None,
                     user_token: str = None,
                     **kwargs) -> Dict[str, Any]:
        """发起API请求"""
        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'ModuleCommunication/1.0'
        }
        
        # 添加认证头
        if self.api_key:
            headers[config.security_config['api_key_header']] = self.api_key
        
        if user_token:
            headers[config.security_config['jwt_header']] = f"{config.security_config['jwt_prefix']}{user_token}"
        
        # 记录请求
        request_logger.log_request(method, url, headers, str(data) if data else None, 'user_management')
        
        try:
            start_time = datetime.now()
            
            if method.upper() == 'GET':
                response = requests.get(url, headers=headers, timeout=self.timeout, **kwargs)
            elif method.upper() == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=self.timeout, **kwargs)
            elif method.upper() == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=self.timeout, **kwargs)
            elif method.upper() == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=self.timeout, **kwargs)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response_time = (datetime.now() - start_time).total_seconds()
            
            # 记录响应
            request_logger.log_response(
                response.status_code, 
                response_time, 
                response.text[:1000] if len(response.text) < 1000 else None,
                'user_management'
            )
            
            # 处理响应
            if response.status_code >= 400:
                error_data = response.json() if response.headers.get('content-type') == 'application/json' else {}
                logger.error(f"User Management API error {response.status_code}: {error_data}")
                return {
                    'success': False,
                    'error': error_data.get('error', f'HTTP {response.status_code}'),
                    'status_code': response.status_code
                }
            
            result = response.json() if response.headers.get('content-type') == 'application/json' else {'data': response.text}
            return {
                'success': True,
                'data': result,
                'response_time': response_time
            }
            
        except requests.exceptions.Timeout:
            logger.error(f"Timeout calling User Management API: {url}")
            return {
                'success': False,
                'error': 'Request timeout',
                'status_code': 408
            }
        except requests.exceptions.ConnectionError:
            logger.error(f"Connection error calling User Management API: {url}")
            return {
                'success': False,
                'error': 'Connection failed',
                'status_code': 503
            }
        except Exception as e:
            logger.error(f"Unexpected error calling User Management API: {e}")
            return {
                'success': False,
                'error': str(e),
                'status_code': 500
            }
    
    @RetryMechanism(max_retries=3)
    @CircuitBreaker(failure_threshold=5)
    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        return self._make_request('GET', '/health')
    
    @RetryMechanism(max_retries=3)
    def authenticate_user(self, 
                         email: str, 
                         password: str) -> Dict[str, Any]:
        """用户认证"""
        data = {
            'email': email,
            'password': password
        }
        return self._make_request('POST', '/api/auth/login', data)
    
    @RetryMechanism(max_retries=3)
    def validate_user_token(self, user_token: str) -> Dict[str, Any]:
        """验证用户令牌"""
        data = {'token': user_token}
        return self._make_request('POST', '/api/auth/validate', data)
    
    @RetryMechanism(max_retries=3)
    def get_user_profile(self, 
                        user_id: str,
                        user_token: str = None) -> Dict[str, Any]:
        """获取用户资料"""
        return self._make_request('GET', f'/api/users/{user_id}/profile', user_token=user_token)
    
    @RetryMechanism(max_retries=3)
    def update_user_profile(self, 
                          user_id: str,
                          profile_data: Dict[str, Any],
                          user_token: str = None) -> Dict[str, Any]:
        """更新用户资料"""
        return self._make_request('PUT', f'/api/users/{user_id}/profile', profile_data, user_token)
    
    @RetryMechanism(max_retries=3)
    def check_user_subscription(self, 
                              user_id: str,
                              required_level: str = None) -> Dict[str, Any]:
        """检查用户订阅状态"""
        params = {}
        if required_level:
            params['required_level'] = required_level
        
        return self._make_request('GET', f'/api/users/{user_id}/subscription', params)
    
    @RetryMechanism(max_retries=3)
    def update_user_subscription(self, 
                               user_id: str,
                               subscription_data: Dict[str, Any],
                               user_token: str = None) -> Dict[str, Any]:
        """更新用户订阅"""
        return self._make_request('PUT', f'/api/users/{user_id}/subscription', subscription_data, user_token)
    
    @RetryMechanism(max_retries=3)
    def check_user_permissions(self, 
                             user_id: str,
                             required_permissions: List[str],
                             user_token: str = None) -> Dict[str, Any]:
        """检查用户权限"""
        data = {
            'user_id': user_id,
            'required_permissions': required_permissions
        }
        return self._make_request('POST', '/api/users/permissions/check', data, user_token)
    
    @RetryMechanism(max_retries=3)
    def create_user_account(self, 
                          user_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建用户账户"""
        return self._make_request('POST', '/api/users/create', user_data)
    
    @RetryMechanism(max_retries=3)
    def update_user_kyc_status(self, 
                             user_id: str,
                             kyc_status: str,
                             kyc_data: Dict[str, Any] = None,
                             user_token: str = None) -> Dict[str, Any]:
        """更新用户KYC状态"""
        data = {
            'kyc_status': kyc_status,
            'kyc_data': kyc_data or {}
        }
        return self._make_request('PUT', f'/api/users/{user_id}/kyc', data, user_token)
    
    @RetryMechanism(max_retries=3)
    def process_payment_completion(self, 
                                 user_id: str,
                                 payment_data: Dict[str, Any],
                                 user_token: str = None) -> Dict[str, Any]:
        """处理支付完成"""
        return self._make_request('POST', f'/api/users/{user_id}/payments/complete', payment_data, user_token)
    
    @RetryMechanism(max_retries=3)
    def get_user_billing_history(self, 
                               user_id: str,
                               limit: int = 50,
                               offset: int = 0,
                               user_token: str = None) -> Dict[str, Any]:
        """获取用户账单历史"""
        params = {
            'limit': limit,
            'offset': offset
        }
        return self._make_request('GET', f'/api/users/{user_id}/billing/history', params, user_token)
    
    @RetryMechanism(max_retries=3)
    def create_billing_record(self, 
                            user_id: str,
                            billing_data: Dict[str, Any],
                            user_token: str = None) -> Dict[str, Any]:
        """创建账单记录"""
        return self._make_request('POST', f'/api/users/{user_id}/billing/create', billing_data, user_token)
    
    @RetryMechanism(max_retries=3)
    def get_crm_customer_data(self, 
                            user_id: str,
                            user_token: str = None) -> Dict[str, Any]:
        """获取CRM客户数据"""
        return self._make_request('GET', f'/api/crm/customers/{user_id}', user_token=user_token)
    
    @RetryMechanism(max_retries=3)
    def update_crm_customer_data(self, 
                               user_id: str,
                               crm_data: Dict[str, Any],
                               user_token: str = None) -> Dict[str, Any]:
        """更新CRM客户数据"""
        return self._make_request('PUT', f'/api/crm/customers/{user_id}', crm_data, user_token)
    
    @RetryMechanism(max_retries=3)
    def log_user_activity(self, 
                         user_id: str,
                         activity_data: Dict[str, Any],
                         user_token: str = None) -> Dict[str, Any]:
        """记录用户活动"""
        return self._make_request('POST', f'/api/users/{user_id}/activities', activity_data, user_token)
    
    @RetryMechanism(max_retries=3)
    def get_user_analytics(self, 
                         user_id: str,
                         metrics: List[str] = None,
                         period: str = '30d',
                         user_token: str = None) -> Dict[str, Any]:
        """获取用户分析数据"""
        params = {'period': period}
        if metrics:
            params['metrics'] = ','.join(metrics)
        
        return self._make_request('GET', f'/api/users/{user_id}/analytics', params, user_token)
    
    @RetryMechanism(max_retries=3)
    def check_user_role(self, 
                       user_id: str,
                       required_roles: List[str],
                       user_token: str = None) -> Dict[str, Any]:
        """检查用户角色"""
        data = {
            'user_id': user_id,
            'required_roles': required_roles
        }
        return self._make_request('POST', '/api/users/roles/check', data, user_token)
    
    @RetryMechanism(max_retries=3)
    def get_subscription_plans(self) -> Dict[str, Any]:
        """获取订阅计划列表"""
        return self._make_request('GET', '/api/billing/plans')
    
    @RetryMechanism(max_retries=3)
    def upgrade_user_subscription(self, 
                                user_id: str,
                                plan_id: str,
                                payment_method: str = 'crypto',
                                user_token: str = None) -> Dict[str, Any]:
        """升级用户订阅"""
        data = {
            'plan_id': plan_id,
            'payment_method': payment_method
        }
        return self._make_request('POST', f'/api/users/{user_id}/subscription/upgrade', data, user_token)

# 辅助函数，用于获取默认的User Management客户端实例
def get_user_client(api_key: str = None) -> UserManagementClient:
    """获取User Management客户端实例"""
    return UserManagementClient(api_key=api_key)