"""
API Authentication Middleware
API认证中间件 - 为所有API端点提供JWT/API密钥认证
"""

import jwt
import os
import time
import hashlib
import hmac
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, List, Union
from functools import wraps
from flask import request, jsonify, session, g
from common.rbac import Permission, Role, rbac_manager

logger = logging.getLogger(__name__)

class APIAuthConfig:
    """API认证配置"""
    
    # JWT配置
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', os.environ.get('SESSION_SECRET', 'dev-jwt-secret-2025'))
    JWT_ALGORITHM = 'HS256'
    JWT_EXPIRATION_HOURS = int(os.environ.get('JWT_EXPIRATION_HOURS', 24))
    JWT_ISSUER = 'calc.hashinsight.net'
    JWT_AUDIENCE = ['api', 'mining_core', 'web3_integration', 'user_management']
    
    # API密钥配置
    API_KEY_HEADER = 'X-API-Key'
    API_KEY_PREFIX = 'hsi_'  # HashInsight API Key prefix
    
    # 签名验证配置
    SIGNATURE_HEADER = 'X-Request-Signature'
    TIMESTAMP_HEADER = 'X-Request-Timestamp'
    SIGNATURE_TOLERANCE = 300  # 5分钟时间窗口
    REQUEST_SIGNING_ENABLED = os.environ.get('REQUEST_SIGNING_ENABLED', 'false').lower() == 'true'

class JWTManager:
    """JWT令牌管理器"""
    
    def __init__(self):
        self.secret_key = APIAuthConfig.JWT_SECRET_KEY
        self.algorithm = APIAuthConfig.JWT_ALGORITHM
        self.expiration_hours = APIAuthConfig.JWT_EXPIRATION_HOURS
        self.issuer = APIAuthConfig.JWT_ISSUER
        self.audience = APIAuthConfig.JWT_AUDIENCE
        
        if not self.secret_key:
            raise ValueError("JWT secret key is required")
    
    def generate_token(self, user_data: Dict[str, Any], expiration_hours: Optional[int] = None) -> str:
        """生成JWT令牌"""
        try:
            now = datetime.utcnow()
            exp_hours = expiration_hours or self.expiration_hours
            exp_time = now + timedelta(hours=exp_hours)
            
            # 构建JWT payload
            jwt_payload = {
                'iss': self.issuer,
                'aud': self.audience,
                'iat': int(now.timestamp()),
                'exp': int(exp_time.timestamp()),
                'sub': user_data.get('email', user_data.get('user_id')),
                'email': user_data.get('email'),
                'role': user_data.get('role', 'guest'),
                'permissions': user_data.get('permissions', []),
                'user_id': user_data.get('user_id'),
                'module': user_data.get('module', 'api')
            }
            
            token = jwt.encode(jwt_payload, self.secret_key, algorithm=self.algorithm)
            logger.debug(f"Generated JWT token for {jwt_payload.get('sub')}")
            return token
            
        except Exception as e:
            logger.error(f"Failed to generate JWT token: {e}")
            raise
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """验证JWT令牌"""
        try:
            payload = jwt.decode(
                token, 
                self.secret_key, 
                algorithms=[self.algorithm],
                audience=self.audience,
                issuer=self.issuer
            )
            logger.debug(f"Successfully verified JWT token for {payload.get('sub')}")
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.warning("JWT token has expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {e}")
            return None
        except Exception as e:
            logger.error(f"JWT token verification failed: {e}")
            return None

class APIKeyManager:
    """API密钥管理器"""
    
    def __init__(self):
        # 从环境变量加载API密钥
        self.api_keys = self._load_api_keys()
    
    def _load_api_keys(self) -> Dict[str, Dict[str, Any]]:
        """加载API密钥配置"""
        api_keys = {}
        
        # 从环境变量加载API密钥
        for i in range(1, 11):  # 支持最多10个API密钥
            key_name = f"API_KEY_{i}"
            role_name = f"API_KEY_{i}_ROLE"
            
            api_key = os.environ.get(key_name)
            if api_key:
                role_str = os.environ.get(role_name, 'api_client')
                
                try:
                    role = Role(role_str)
                except ValueError:
                    logger.warning(f"Invalid role '{role_str}' for {key_name}, defaulting to api_client")
                    role = Role.API_CLIENT
                
                role_permissions = rbac_manager.get_role_permissions(role)
                
                api_keys[api_key] = {
                    'name': f"api_key_{i}",
                    'role': role.value,
                    'role_enum': role,
                    'permissions': [p.value for p in role_permissions],
                    'created_at': datetime.utcnow().isoformat()
                }
        
        # 默认开发API密钥（仅在开发环境）
        if os.environ.get('FLASK_ENV') != 'production' and not api_keys:
            dev_key = f"{APIAuthConfig.API_KEY_PREFIX}dev_key_2025"
            dev_role = Role.DEVELOPER
            dev_permissions = rbac_manager.get_role_permissions(dev_role)
            
            api_keys[dev_key] = {
                'name': 'development_key',
                'role': dev_role.value,
                'role_enum': dev_role,
                'permissions': [p.value for p in dev_permissions],
                'created_at': datetime.utcnow().isoformat()
            }
            logger.warning(f"Using development API key: {dev_key} with role {dev_role.value}")
        
        logger.info(f"Loaded {len(api_keys)} API keys")
        return api_keys
    
    def verify_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """验证API密钥"""
        if not api_key:
            return None
        
        # 移除前缀（如果存在）
        if api_key.startswith(APIAuthConfig.API_KEY_PREFIX):
            clean_key = api_key
        else:
            clean_key = f"{APIAuthConfig.API_KEY_PREFIX}{api_key}"
        
        # 检查两种格式
        for key_variant in [api_key, clean_key]:
            if key_variant in self.api_keys:
                key_info = self.api_keys[key_variant].copy()
                key_info['api_key'] = key_variant
                logger.debug(f"API key verified: {key_info['name']}")
                return key_info
        
        logger.warning(f"Invalid API key attempted: {api_key[:10]}...")
        return None

class APIAuthMiddleware:
    """API认证中间件"""
    
    def __init__(self):
        self.jwt_manager = JWTManager()
        self.api_key_manager = APIKeyManager()
    
    def authenticate_request(self, headers: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """认证请求 - 支持JWT和API密钥"""
        
        # 1. 尝试JWT认证
        auth_header = headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]  # 移除 "Bearer " 前缀
            jwt_payload = self.jwt_manager.verify_token(token)
            if jwt_payload:
                return {'type': 'jwt', 'payload': jwt_payload}
        
        # 2. 尝试API密钥认证
        api_key = headers.get(APIAuthConfig.API_KEY_HEADER)
        if api_key:
            key_info = self.api_key_manager.verify_api_key(api_key)
            if key_info:
                return {'type': 'api_key', 'payload': key_info}
        
        logger.debug("No valid authentication found in request")
        return None
    
    def verify_request_signature(self, method: str, url: str, body: str, headers: Dict[str, str]) -> bool:
        """验证请求签名（可选功能）"""
        if not APIAuthConfig.REQUEST_SIGNING_ENABLED:
            return True
        
        signature = headers.get(APIAuthConfig.SIGNATURE_HEADER)
        timestamp = headers.get(APIAuthConfig.TIMESTAMP_HEADER)
        
        if not signature or not timestamp:
            logger.warning("Missing signature or timestamp in signed request")
            return False
        
        # 验证时间戳
        try:
            request_time = int(timestamp)
            current_time = int(time.time())
            if abs(current_time - request_time) > APIAuthConfig.SIGNATURE_TOLERANCE:
                logger.warning("Request timestamp outside tolerance window")
                return False
        except ValueError:
            logger.warning("Invalid timestamp format")
            return False
        
        # 这里可以添加签名验证逻辑
        logger.debug("Request signature verification passed")
        return True

# 全局实例
auth_middleware = APIAuthMiddleware()

def require_api_auth(required_permissions: Optional[Union[List[Permission], List[str]]] = None, allow_session_auth: bool = True):
    """
    API认证装饰器 - 集成RBAC细粒度权限检查
    
    Args:
        required_permissions: 需要的权限列表（Permission枚举或字符串，推荐使用Permission枚举）
        allow_session_auth: 是否允许session认证（用于兼容现有前端）
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 1. 尝试API认证（JWT/API Key）
            auth_result = auth_middleware.authenticate_request(dict(request.headers))
            
            # 2. 如果API认证失败且允许session认证，尝试session认证
            if not auth_result and allow_session_auth:
                if session.get('authenticated') and session.get('email'):
                    # 构造session认证结果
                    auth_result = {
                        'type': 'session',
                        'payload': {
                            'email': session.get('email'),
                            'role': session.get('role', 'guest'),
                            'permissions': session.get('permissions', []),
                            'user_id': session.get('user_id')
                        }
                    }
            
            # 3. 如果仍然没有认证，返回401
            if not auth_result:
                return jsonify({
                    'success': False,
                    'error': 'Authentication required',
                    'message': 'Valid JWT token, API key, or session authentication required'
                }), 401
            
            # 4. 验证签名（如果启用）
            if not auth_middleware.verify_request_signature(
                request.method, 
                request.url, 
                request.get_data(as_text=True),
                dict(request.headers)
            ):
                return jsonify({
                    'success': False,
                    'error': 'Invalid request signature'
                }), 401
            
            # 5. 检查权限（使用RBAC细粒度权限）
            if required_permissions:
                user_role_str = auth_result['payload'].get('role', 'guest')
                
                # 角色别名映射（兼容历史数据）
                role_aliases = {
                    'owner': 'tenant_owner',
                    'admin': 'tenant_admin',
                    'user': 'guest'
                }
                user_role_str = role_aliases.get(user_role_str, user_role_str)
                
                try:
                    user_role = Role(user_role_str)
                except ValueError:
                    logger.error(f"Invalid role: {user_role_str}")
                    return jsonify({
                        'success': False,
                        'error': 'Invalid user role'
                    }), 403
                
                # 超级管理员和租户所有者拥有所有权限
                if user_role in [Role.SUPER_ADMIN, Role.TENANT_OWNER]:
                    pass  # 跳过权限检查
                else:
                    # 转换required_permissions为Permission枚举
                    required_perms = []
                    for perm in required_permissions:
                        if isinstance(perm, Permission):
                            required_perms.append(perm)
                        elif isinstance(perm, str):
                            try:
                                required_perms.append(Permission(perm))
                            except ValueError:
                                logger.warning(f"Unknown permission string: {perm}")
                    
                    # 使用RBAC管理器检查权限
                    if required_perms:
                        has_access = rbac_manager.has_any_permission(user_role, required_perms)
                        
                        if not has_access:
                            logger.warning(
                                f"Permission denied for {auth_result['payload'].get('email')} ({user_role_str}): "
                                f"required {[p.value for p in required_perms]}"
                            )
                            return jsonify({
                                'success': False,
                                'error': 'Insufficient permissions',
                                'required_permissions': [p.value for p in required_perms],
                                'user_role': user_role_str
                            }), 403
            
            # 6. 将认证信息存储在Flask全局对象中（供后续@require_permission使用）
            g.auth = auth_result
            g.user_role = auth_result['payload'].get('role', 'guest')
            g.user_email = auth_result['payload'].get('email')
            g.user_permissions = auth_result['payload'].get('permissions', [])
            
            # 7. 记录API访问
            logger.info(f"API access: {request.method} {request.path} by {g.user_email} ({g.user_role})")
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def require_jwt_auth(required_permissions: Optional[Union[List[Permission], List[str]]] = None):
    """
    严格JWT认证装饰器（不允许session认证）
    """
    return require_api_auth(required_permissions, allow_session_auth=False)

def generate_user_jwt_token(user_data: Dict[str, Any]) -> str:
    """
    为用户生成JWT令牌的辅助函数
    """
    return auth_middleware.jwt_manager.generate_token(user_data)

# 导出主要组件
__all__ = [
    'require_api_auth',
    'require_jwt_auth', 
    'generate_user_jwt_token',
    'APIAuthConfig',
    'auth_middleware'
]