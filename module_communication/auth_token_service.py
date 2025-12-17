"""
Unified Authentication Token Service
统一认证令牌服务 - 为模块间通信提供令牌管理
"""

import os
import logging
from typing import Dict, Optional, List, Any
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, g
from functools import wraps

from common.auth import jwt_manager, api_key_manager, auth_middleware
from common.config import config
from common.utils import format_error_response, format_success_response, rate_limiter

logger = logging.getLogger(__name__)

class AuthTokenService:
    """统一认证令牌服务"""
    
    def __init__(self):
        self.jwt_manager = jwt_manager
        self.api_key_manager = api_key_manager
        self.auth_middleware = auth_middleware
        
        # 为每个模块生成初始API密钥
        self._initialize_module_keys()
    
    def _initialize_module_keys(self):
        """初始化模块API密钥"""
        modules = ['mining_core', 'web3_integration', 'user_management']
        
        for module_name in modules:
            # 检查环境变量中是否已有API密钥
            env_key = f"{module_name.upper()}_API_KEY"
            existing_key = os.environ.get(env_key)
            
            if existing_key:
                # 注册现有密钥
                self.api_key_manager.active_keys[existing_key] = {
                    'module_name': module_name,
                    'permissions': self._get_module_permissions(module_name),
                    'created_at': datetime.utcnow(),
                    'last_used': None,
                    'usage_count': 0
                }
                logger.info(f"Registered existing API key for {module_name}")
            else:
                # 生成新的API密钥
                new_key = self.api_key_manager.generate_api_key(
                    module_name, 
                    self._get_module_permissions(module_name)
                )
                logger.info(f"Generated new API key for {module_name}: {new_key[:8]}...")
    
    def _get_module_permissions(self, module_name: str) -> List[str]:
        """获取模块权限列表"""
        permissions_map = {
            'mining_core': [
                'mining:calculate',
                'mining:analyze',
                'mining:report',
                'user:verify',
                'user:subscription_check'
            ],
            'web3_integration': [
                'web3:authenticate',
                'web3:payment',
                'web3:nft_mint',
                'web3:blockchain_store',
                'user:kyc_update',
                'user:payment_update'
            ],
            'user_management': [
                'user:create',
                'user:authenticate',
                'user:authorize',
                'user:subscription',
                'user:billing',
                'user:crm'
            ]
        }
        return permissions_map.get(module_name, [])
    
    def generate_inter_module_token(self, 
                                  source_module: str, 
                                  target_module: str, 
                                  operation: str,
                                  user_context: Dict[str, Any] = None) -> str:
        """生成模块间通信令牌"""
        payload = {
            'source_module': source_module,
            'target_module': target_module,
            'operation': operation,
            'token_type': 'inter_module',
            'created_at': datetime.utcnow().isoformat()
        }
        
        # 如果有用户上下文，包含在令牌中
        if user_context:
            payload['user_context'] = user_context
        
        # 生成短期令牌（1小时有效）
        return self.jwt_manager.generate_token(payload, expiration_hours=1)
    
    def validate_inter_module_request(self, 
                                    source_module: str, 
                                    target_module: str, 
                                    operation: str,
                                    token: str) -> Optional[Dict[str, Any]]:
        """验证模块间通信请求"""
        try:
            # 验证JWT令牌
            payload = self.jwt_manager.verify_token(token)
            if not payload:
                return None
            
            # 检查令牌类型
            if payload.get('token_type') != 'inter_module':
                logger.warning(f"Invalid token type for inter-module request: {payload.get('token_type')}")
                return None
            
            # 检查模块和操作匹配
            if (payload.get('source_module') != source_module or 
                payload.get('target_module') != target_module or 
                payload.get('operation') != operation):
                logger.warning(f"Token mismatch for inter-module request")
                return None
            
            logger.debug(f"Successfully validated inter-module request: {source_module} -> {target_module}:{operation}")
            return payload
            
        except Exception as e:
            logger.error(f"Failed to validate inter-module request: {e}")
            return None
    
    def generate_user_session_token(self, 
                                  user_id: str, 
                                  email: str, 
                                  role: str, 
                                  subscription_level: str = 'free',
                                  permissions: List[str] = None) -> str:
        """生成用户会话令牌"""
        return self.jwt_manager.generate_user_token(
            user_id, email, role, subscription_level
        )
    
    def validate_user_session(self, token: str) -> Optional[Dict[str, Any]]:
        """验证用户会话令牌"""
        payload = self.jwt_manager.verify_token(token)
        if payload and payload.get('token_type') == 'user_authentication':
            return payload
        return None
    
    def check_user_permissions(self, 
                             user_token: str, 
                             required_permissions: List[str],
                             required_subscription: str = None) -> Dict[str, Any]:
        """检查用户权限和订阅级别"""
        payload = self.validate_user_session(user_token)
        if not payload:
            return {
                'authorized': False,
                'error': 'Invalid or expired token'
            }
        
        user_role = payload.get('role', 'guest')
        user_permissions = payload.get('permissions', [])
        user_subscription = payload.get('subscription_level', 'free')
        
        # 管理员和所有者拥有所有权限
        if user_role in ['admin', 'owner']:
            return {
                'authorized': True,
                'user_id': payload.get('user_id'),
                'role': user_role,
                'subscription_level': user_subscription
            }
        
        # 检查具体权限
        if required_permissions:
            has_permission = any(perm in user_permissions for perm in required_permissions)
            if not has_permission:
                return {
                    'authorized': False,
                    'error': 'Insufficient permissions',
                    'required_permissions': required_permissions
                }
        
        # 检查订阅级别
        if required_subscription:
            subscription_hierarchy = ['free', 'basic', 'premium', 'enterprise']
            user_level = subscription_hierarchy.index(user_subscription) if user_subscription in subscription_hierarchy else 0
            required_level = subscription_hierarchy.index(required_subscription) if required_subscription in subscription_hierarchy else 0
            
            if user_level < required_level:
                return {
                    'authorized': False,
                    'error': 'Insufficient subscription level',
                    'current_subscription': user_subscription,
                    'required_subscription': required_subscription
                }
        
        return {
            'authorized': True,
            'user_id': payload.get('user_id'),
            'role': user_role,
            'subscription_level': user_subscription
        }

# 创建Flask应用用于令牌服务
def create_auth_service_app():
    """创建认证服务Flask应用"""
    app = Flask(__name__)
    app.secret_key = config.jwt_config['secret_key']
    
    auth_service = AuthTokenService()
    
    @app.before_request
    def rate_limit_check():
        """速率限制检查"""
        if config.security_config['rate_limit_enabled']:
            client_ip = request.remote_addr
            if not rate_limiter.is_allowed(client_ip):
                return jsonify(format_error_response(
                    'RATE_LIMIT_EXCEEDED',
                    'Too many requests'
                )), 429
    
    @app.route('/health')
    def health():
        """健康检查"""
        return jsonify({
            'status': 'healthy',
            'service': 'auth_token_service',
            'timestamp': datetime.utcnow().isoformat()
        })
    
    @app.route('/tokens/inter-module', methods=['POST'])
    def generate_inter_module_token():
        """生成模块间通信令牌"""
        try:
            data = request.get_json()
            if not data:
                return jsonify(format_error_response(
                    'INVALID_REQUEST',
                    'JSON body required'
                )), 400
            
            # 验证请求参数
            required_fields = ['source_module', 'target_module', 'operation']
            for field in required_fields:
                if field not in data:
                    return jsonify(format_error_response(
                        'MISSING_FIELD',
                        f'Required field missing: {field}'
                    )), 400
            
            # 验证API密钥
            auth_result = auth_service.auth_middleware.authenticate_request(dict(request.headers))
            if not auth_result:
                return jsonify(format_error_response(
                    'AUTHENTICATION_REQUIRED',
                    'Valid API key required'
                )), 401
            
            # 生成令牌
            token = auth_service.generate_inter_module_token(
                data['source_module'],
                data['target_module'], 
                data['operation'],
                data.get('user_context')
            )
            
            return jsonify(format_success_response({
                'token': token,
                'expires_in': 3600  # 1小时
            }))
            
        except Exception as e:
            logger.error(f"Failed to generate inter-module token: {e}")
            return jsonify(format_error_response(
                'TOKEN_GENERATION_FAILED',
                'Failed to generate token'
            )), 500
    
    @app.route('/tokens/validate', methods=['POST'])
    def validate_token():
        """验证令牌"""
        try:
            data = request.get_json()
            if not data or 'token' not in data:
                return jsonify(format_error_response(
                    'INVALID_REQUEST',
                    'Token required'
                )), 400
            
            payload = auth_service.jwt_manager.verify_token(data['token'])
            if not payload:
                return jsonify(format_error_response(
                    'INVALID_TOKEN',
                    'Token is invalid or expired'
                )), 401
            
            return jsonify(format_success_response({
                'valid': True,
                'payload': payload
            }))
            
        except Exception as e:
            logger.error(f"Failed to validate token: {e}")
            return jsonify(format_error_response(
                'VALIDATION_FAILED',
                'Failed to validate token'
            )), 500
    
    @app.route('/users/permissions', methods=['POST'])
    def check_user_permissions():
        """检查用户权限"""
        try:
            data = request.get_json()
            if not data or 'user_token' not in data:
                return jsonify(format_error_response(
                    'INVALID_REQUEST',
                    'User token required'
                )), 400
            
            result = auth_service.check_user_permissions(
                data['user_token'],
                data.get('required_permissions', []),
                data.get('required_subscription')
            )
            
            status_code = 200 if result['authorized'] else 403
            return jsonify(format_success_response(result)), status_code
            
        except Exception as e:
            logger.error(f"Failed to check user permissions: {e}")
            return jsonify(format_error_response(
                'PERMISSION_CHECK_FAILED',
                'Failed to check permissions'
            )), 500
    
    @app.route('/api-keys/rotate', methods=['POST'])
    def rotate_api_key():
        """轮换API密钥"""
        try:
            data = request.get_json()
            if not data or 'module_name' not in data:
                return jsonify(format_error_response(
                    'INVALID_REQUEST',
                    'Module name required'
                )), 400
            
            # 验证当前API密钥
            auth_result = auth_service.auth_middleware.authenticate_request(dict(request.headers))
            if not auth_result:
                return jsonify(format_error_response(
                    'AUTHENTICATION_REQUIRED',
                    'Valid API key required'
                )), 401
            
            # 获取当前密钥
            current_key = request.headers.get(config.security_config['api_key_header'])
            
            # 轮换密钥
            new_key = auth_service.api_key_manager.rotate_api_key(current_key, data['module_name'])
            
            return jsonify(format_success_response({
                'new_api_key': new_key,
                'module_name': data['module_name']
            }))
            
        except Exception as e:
            logger.error(f"Failed to rotate API key: {e}")
            return jsonify(format_error_response(
                'KEY_ROTATION_FAILED',
                'Failed to rotate API key'
            )), 500
    
    return app

# 全局认证服务实例
auth_token_service = AuthTokenService()

if __name__ == '__main__':
    app = create_auth_service_app()
    port = int(os.environ.get('AUTH_SERVICE_PORT', 5004))
    app.run(host='0.0.0.0', port=port, debug=False)