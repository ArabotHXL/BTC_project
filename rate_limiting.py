"""
使用频率限制系统 - 防止匿名用户滥用
"""
import time
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, session, render_template, g
import logging

# 内存存储 - 生产环境建议使用Redis
_rate_limit_store = {}

def get_client_identifier():
    """获取客户端唯一标识"""
    if session.get('authenticated'):
        return f"user:{session.get('email', 'unknown')}"
    else:
        # 未登录用户使用IP地址
        return f"ip:{request.remote_addr}"

def rate_limit(max_requests=10, window_minutes=60, feature_name="basic"):
    """
    频率限制装饰器
    
    Args:
        max_requests: 时间窗口内最大请求数
        window_minutes: 时间窗口长度（分钟）
        feature_name: 功能名称（用于日志）
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            client_id = get_client_identifier()
            now = datetime.now()
            window_start = now - timedelta(minutes=window_minutes)
            
            # 清理过期记录
            _cleanup_expired_records(window_start)
            
            # 获取客户端请求记录
            if client_id not in _rate_limit_store:
                _rate_limit_store[client_id] = []
            
            # 过滤时间窗口内的请求
            recent_requests = [
                req_time for req_time in _rate_limit_store[client_id] 
                if req_time > window_start
            ]
            
            # 检查是否超过限制
            if len(recent_requests) >= max_requests:
                logging.warning(f"频率限制触发: {client_id} - {feature_name} - {len(recent_requests)}/{max_requests}")
                
                # 未登录用户显示注册引导
                if not session.get('authenticated'):
                    return render_template('rate_limit_exceeded.html',
                                         max_requests=max_requests,
                                         window_minutes=window_minutes,
                                         feature_name=feature_name), 429
                else:
                    # 登录用户显示普通限制信息
                    return jsonify({
                        'error': '请求频率过高',
                        'message': f'每{window_minutes}分钟最多{max_requests}次请求',
                        'retry_after': window_minutes * 60
                    }), 429
            
            # 记录新请求
            recent_requests.append(now)
            _rate_limit_store[client_id] = recent_requests
            
            # 在响应头中添加限制信息
            response = func(*args, **kwargs)
            if hasattr(response, 'headers'):
                response.headers['X-RateLimit-Limit'] = str(max_requests)
                response.headers['X-RateLimit-Remaining'] = str(max_requests - len(recent_requests))
                response.headers['X-RateLimit-Reset'] = str(int((window_start + timedelta(minutes=window_minutes)).timestamp()))
            
            return response
        return wrapper
    return decorator

def _cleanup_expired_records(cutoff_time):
    """清理过期的请求记录"""
    to_remove = []
    for client_id in _rate_limit_store:
        _rate_limit_store[client_id] = [
            req_time for req_time in _rate_limit_store[client_id] 
            if req_time > cutoff_time
        ]
        if not _rate_limit_store[client_id]:
            to_remove.append(client_id)
    
    for client_id in to_remove:
        del _rate_limit_store[client_id]

def get_rate_limit_info(client_id=None):
    """获取客户端的频率限制信息"""
    if client_id is None:
        client_id = get_client_identifier()
    
    if client_id not in _rate_limit_store:
        return {
            'requests_count': 0,
            'remaining': 10,  # 默认限制
            'reset_time': None
        }
    
    recent_count = len(_rate_limit_store[client_id])
    return {
        'requests_count': recent_count,
        'remaining': max(0, 10 - recent_count),
        'reset_time': datetime.now() + timedelta(minutes=60)
    }