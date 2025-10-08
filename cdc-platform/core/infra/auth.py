"""
HashInsight CDC Platform - Authentication Middleware
JWT认证和授权装饰器
"""
import os
import logging
from functools import wraps
from flask import request, jsonify, g
import jwt
from datetime import datetime
from .redis_client import redis_client

logger = logging.getLogger(__name__)

def get_jwt_secret():
    """获取JWT密钥"""
    return os.getenv('JWT_SECRET', 'dev-secret')

def jwt_required(scopes=[]):
    """
    JWT认证装饰器，支持Scope验证
    
    参数:
        scopes: 所需的权限范围列表（如 ['miners:write', 'admin']）
    
    用法:
        @jwt_required(scopes=['miners:write'])
        def create_miner():
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            auth_header = request.headers.get('Authorization')
            
            if not auth_header:
                return jsonify({'error': 'Missing authorization header'}), 401
            
            try:
                token = auth_header.split(' ')[1] if ' ' in auth_header else auth_header
                payload = jwt.decode(token, get_jwt_secret(), algorithms=['HS256'])
                
                # 设置上下文
                g.user_id = payload.get('user_id')
                g.tenant_id = payload.get('tenant_id', 'default')
                g.role = payload.get('role', 'user')
                g.scopes = payload.get('scopes', [])
                
                # 验证Scope
                if scopes:
                    if not any(scope in g.scopes for scope in scopes):
                        return jsonify({'error': f'Missing required scope: {scopes}'}), 403
                
                return f(*args, **kwargs)
            
            except jwt.ExpiredSignatureError:
                return jsonify({'error': 'Token expired'}), 401
            except jwt.InvalidTokenError as e:
                return jsonify({'error': f'Invalid token: {str(e)}'}), 401
        
        return decorated_function
    return decorator

def rate_limit(limit_per_minute=60):
    """
    速率限制装饰器（使用Redis）
    
    参数:
        limit_per_minute: 每分钟最大请求数
    
    用法:
        @rate_limit(limit_per_minute=30)
        def some_endpoint():
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(g, 'user_id'):
                return f(*args, **kwargs)
            
            key = f"rate_limit:{g.user_id}:{datetime.utcnow().minute}"
            count = redis_client.incr(key)
            redis_client.expire(key, 60)
            
            if count > limit_per_minute:
                return jsonify({'error': 'Rate limit exceeded'}), 429
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator
