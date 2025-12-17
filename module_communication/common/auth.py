"""
Authentication and Authorization Module
认证和授权模块 - JWT令牌管理和API密钥验证
"""

import jwt
import time
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, List
from functools import wraps
import logging

from .config import config

logger = logging.getLogger(__name__)

class JWTManager:
    """JWT令牌管理器"""
    
    def __init__(self):
        self.secret_key = config.jwt_config['secret_key']
        self.algorithm = config.jwt_config['algorithm']
        self.expiration_delta = config.jwt_config['expiration_delta']
        self.issuer = config.jwt_config['issuer']
        self.audience = config.jwt_config['audience']
        
        if not self.secret_key:
            raise ValueError("JWT secret key is required")
    
    def generate_token(self, 
                      payload: Dict[str, Any], 
                      expiration_hours: Optional[int] = None) -> str:
        """生成JWT令牌"""
        try:
            now = datetime.utcnow()
            exp_hours = expiration_hours or (self.expiration_delta / 3600)
            exp_time = now + timedelta(hours=exp_hours)
            
            # 构建JWT payload
            jwt_payload = {
                'iss': self.issuer,
                'aud': self.audience,
                'iat': int(now.timestamp()),
                'exp': int(exp_time.timestamp()),
                'sub': payload.get('user_id', payload.get('module_name')),
                **payload
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
            logger.error(f"Failed to verify JWT token: {e}")
            return None
    
    def generate_module_token(self, 
                            module_name: str, 
                            permissions: List[str] = None) -> str:
        """生成模块间通信令牌"""
        payload = {
            'module_name': module_name,
            'permissions': permissions or [],
            'token_type': 'module_communication',
            'created_at': datetime.utcnow().isoformat()
        }
        return self.generate_token(payload)
    
    def generate_user_token(self, 
                          user_id: str, 
                          email: str, 
                          role: str, 
                          subscription_level: str = 'free') -> str:
        """生成用户认证令牌"""
        payload = {
            'user_id': user_id,
            'email': email,
            'role': role,
            'subscription_level': subscription_level,
            'token_type': 'user_authentication',
            'created_at': datetime.utcnow().isoformat()
        }
        return self.generate_token(payload)

class APIKeyManager:
    """API密钥管理器"""
    
    def __init__(self):
        self.active_keys = {}  # 在实际应用中应该存储在数据库中
    
    def generate_api_key(self, module_name: str, permissions: List[str] = None) -> str:
        """生成API密钥"""
        key = secrets.token_urlsafe(32)
        self.active_keys[key] = {
            'module_name': module_name,
            'permissions': permissions or [],
            'created_at': datetime.utcnow(),
            'last_used': None,
            'usage_count': 0
        }
        logger.info(f"Generated API key for module {module_name}")
        return key
    
    def verify_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """验证API密钥"""
        if api_key in self.active_keys:
            key_info = self.active_keys[api_key]
            key_info['last_used'] = datetime.utcnow()
            key_info['usage_count'] += 1
            logger.debug(f"API key verified for module {key_info['module_name']}")
            return key_info
        
        logger.warning(f"Invalid API key attempted: {api_key[:8]}...")
        return None
    
    def rotate_api_key(self, old_key: str, module_name: str) -> str:
        """轮换API密钥"""
        if old_key in self.active_keys:
            del self.active_keys[old_key]
        
        new_key = self.generate_api_key(module_name)
        logger.info(f"API key rotated for module {module_name}")
        return new_key

class RequestSigner:
    """请求签名器"""
    
    def __init__(self, secret_key: str):
        self.secret_key = secret_key.encode('utf-8')
    
    def sign_request(self, method: str, url: str, body: str = '', timestamp: int = None) -> Dict[str, str]:
        """签名请求"""
        if timestamp is None:
            timestamp = int(time.time())
        
        # 构建签名字符串
        sign_string = f"{method}\n{url}\n{body}\n{timestamp}"
        
        # 生成HMAC签名
        signature = hmac.new(
            self.secret_key,
            sign_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return {
            'signature': signature,
            'timestamp': str(timestamp)
        }
    
    def verify_signature(self, 
                        method: str, 
                        url: str, 
                        body: str, 
                        signature: str, 
                        timestamp: str,
                        tolerance: int = 300) -> bool:
        """验证请求签名"""
        try:
            request_timestamp = int(timestamp)
            current_timestamp = int(time.time())
            
            # 检查时间戳是否在容忍范围内
            if abs(current_timestamp - request_timestamp) > tolerance:
                logger.warning(f"Request timestamp out of tolerance: {timestamp}")
                return False
            
            # 重新计算签名并比较
            expected_sig = self.sign_request(method, url, body, request_timestamp)['signature']
            
            # 使用常数时间比较防止时间攻击
            return hmac.compare_digest(signature, expected_sig)
            
        except Exception as e:
            logger.error(f"Failed to verify signature: {e}")
            return False

class AuthMiddleware:
    """认证中间件"""
    
    def __init__(self):
        self.jwt_manager = JWTManager()
        self.api_key_manager = APIKeyManager()
        self.request_signer = RequestSigner(config.jwt_config['secret_key'])
    
    def authenticate_request(self, headers: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """认证请求"""
        # 尝试JWT认证
        auth_header = headers.get(config.security_config['jwt_header'], '')
        if auth_header.startswith(config.security_config['jwt_prefix']):
            token = auth_header[len(config.security_config['jwt_prefix']):]
            payload = self.jwt_manager.verify_token(token)
            if payload:
                return {'type': 'jwt', 'payload': payload}
        
        # 尝试API密钥认证
        api_key = headers.get(config.security_config['api_key_header'])
        if api_key:
            key_info = self.api_key_manager.verify_api_key(api_key)
            if key_info:
                return {'type': 'api_key', 'payload': key_info}
        
        logger.warning("No valid authentication found in request")
        return None
    
    def verify_request_signature(self, 
                               method: str, 
                               url: str, 
                               body: str, 
                               headers: Dict[str, str]) -> bool:
        """验证请求签名"""
        if not config.security_config['request_signing_enabled']:
            return True
        
        signature = headers.get(config.security_config['signature_header'])
        timestamp = headers.get(config.security_config['timestamp_header'])
        
        if not signature or not timestamp:
            logger.warning("Missing signature or timestamp in signed request")
            return False
        
        return self.request_signer.verify_signature(
            method, url, body, signature, timestamp,
            config.security_config['signature_tolerance']
        )

def require_auth(required_permissions: List[str] = None):
    """认证装饰器"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from flask import request, jsonify, g
            
            auth_middleware = AuthMiddleware()
            
            # 认证请求
            auth_result = auth_middleware.authenticate_request(dict(request.headers))
            if not auth_result:
                return jsonify({'error': 'Authentication required'}), 401
            
            # 验证签名（如果启用）
            if not auth_middleware.verify_request_signature(
                request.method, 
                request.url, 
                request.get_data(as_text=True),
                dict(request.headers)
            ):
                return jsonify({'error': 'Invalid request signature'}), 401
            
            # 检查权限
            if required_permissions:
                user_permissions = auth_result['payload'].get('permissions', [])
                user_role = auth_result['payload'].get('role', 'guest')
                
                # 管理员和所有者拥有所有权限
                if user_role not in ['admin', 'owner']:
                    if not any(perm in user_permissions for perm in required_permissions):
                        return jsonify({'error': 'Insufficient permissions'}), 403
            
            # 将认证信息存储在Flask全局对象中
            g.auth = auth_result
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# 全局实例
jwt_manager = JWTManager()
api_key_manager = APIKeyManager()
auth_middleware = AuthMiddleware()