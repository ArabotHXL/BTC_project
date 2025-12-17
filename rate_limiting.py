"""
Redis-based Rate Limiting System
Redis-backed rate limiting for distributed environments with Gunicorn workers

Uses sliding window algorithm with Redis for accurate rate limiting across all workers.
Falls back to thread-safe in-memory storage when Redis is unavailable.
"""
import os
import time
import logging
import threading
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, session, render_template, g, make_response
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

_redis_client = None
_memory_lock = threading.Lock()


def get_redis_client():
    """Get or initialize Redis client with connection pooling"""
    global _redis_client
    
    if _redis_client is not None:
        return _redis_client
    
    redis_url = os.environ.get('REDIS_URL')
    
    if not redis_url:
        logger.warning("REDIS_URL not configured, rate limiting will use in-memory fallback")
        return None
    
    try:
        import redis
        _redis_client = redis.from_url(
            redis_url,
            decode_responses=True,
            socket_timeout=2,
            socket_connect_timeout=2,
            retry_on_timeout=True
        )
        _redis_client.ping()
        logger.info("Redis rate limiter connected successfully")
        return _redis_client
    except Exception as e:
        logger.warning(f"Failed to connect to Redis for rate limiting: {e}")
        return None


_rate_limit_store = {}


def get_client_identifier():
    """获取客户端唯一标识 Get unique client identifier"""
    if session.get('authenticated'):
        return f"user:{session.get('email', 'unknown')}"
    else:
        return f"ip:{request.remote_addr}"


def _check_rate_limit_redis(
    client_id: str,
    max_requests: int,
    window_seconds: int,
    feature_name: str
) -> Tuple[bool, int, int]:
    """
    Check rate limit using Redis sliding window algorithm
    
    Returns:
        Tuple[allowed: bool, remaining: int, reset_time: int]
    """
    redis_client = get_redis_client()
    if not redis_client:
        return _check_rate_limit_memory(client_id, max_requests, window_seconds, feature_name)
    
    try:
        now = time.time()
        window_start = now - window_seconds
        key = f"ratelimit:{feature_name}:{client_id}"
        
        pipe = redis_client.pipeline()
        pipe.zremrangebyscore(key, 0, window_start)
        pipe.zadd(key, {str(now): now})
        pipe.zcard(key)
        pipe.zrange(key, 0, 0, withscores=True)
        pipe.expire(key, window_seconds + 60)
        results = pipe.execute()
        
        current_count = results[2]
        oldest_entries = results[3]
        
        if oldest_entries:
            oldest_timestamp = oldest_entries[0][1]
            reset_time = int(oldest_timestamp + window_seconds)
        else:
            reset_time = int(now + window_seconds)
        
        if current_count > max_requests:
            redis_client.zrem(key, str(now))
            remaining = 0
            return False, remaining, reset_time
        
        remaining = max(0, max_requests - current_count)
        return True, remaining, reset_time
        
    except Exception as e:
        logger.error(f"Redis rate limit error: {e}")
        return _check_rate_limit_memory(client_id, max_requests, window_seconds, feature_name)


def _check_rate_limit_memory(
    client_id: str,
    max_requests: int,
    window_seconds: int,
    feature_name: str
) -> Tuple[bool, int, int]:
    """
    Fallback thread-safe in-memory rate limiting (single worker only)
    """
    now = datetime.now()
    window_start = now - timedelta(seconds=window_seconds)
    store_key = f"{feature_name}:{client_id}"
    
    with _memory_lock:
        if store_key not in _rate_limit_store:
            _rate_limit_store[store_key] = []
        
        _rate_limit_store[store_key] = [
            req_time for req_time in _rate_limit_store[store_key]
            if req_time > window_start
        ]
        
        current_count = len(_rate_limit_store[store_key])
        
        if current_count >= max_requests:
            remaining = 0
            if _rate_limit_store[store_key]:
                oldest = min(_rate_limit_store[store_key])
                reset_time = int((oldest + timedelta(seconds=window_seconds)).timestamp())
            else:
                reset_time = int((now + timedelta(seconds=window_seconds)).timestamp())
            return False, remaining, reset_time
        
        _rate_limit_store[store_key].append(now)
        remaining = max(0, max_requests - current_count - 1)
        if _rate_limit_store[store_key]:
            oldest = min(_rate_limit_store[store_key])
            reset_time = int((oldest + timedelta(seconds=window_seconds)).timestamp())
        else:
            reset_time = int((now + timedelta(seconds=window_seconds)).timestamp())
        return True, remaining, reset_time


def rate_limit(max_requests=10, window_minutes=60, feature_name="basic"):
    """
    Rate limiting decorator with Redis backend
    
    Args:
        max_requests: Maximum requests within window
        window_minutes: Time window in minutes
        feature_name: Feature name for logging and key prefixing
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            client_id = get_client_identifier()
            window_seconds = window_minutes * 60
            
            allowed, remaining, reset_time = _check_rate_limit_redis(
                client_id=client_id,
                max_requests=max_requests,
                window_seconds=window_seconds,
                feature_name=feature_name
            )
            
            if not allowed:
                logger.warning(
                    f"Rate limit exceeded: {client_id} - {feature_name} - "
                    f"0/{max_requests} remaining"
                )
                
                retry_after = max(1, reset_time - int(time.time()))
                
                if not session.get('authenticated'):
                    response = make_response(render_template(
                        'rate_limit_exceeded.html',
                        max_requests=max_requests,
                        window_minutes=window_minutes,
                        feature_name=feature_name
                    ), 429)
                else:
                    response = make_response(jsonify({
                        'error': '请求频率过高 / Rate limit exceeded',
                        'message': f'每{window_minutes}分钟最多{max_requests}次请求 / '
                                   f'Maximum {max_requests} requests per {window_minutes} minutes',
                        'retry_after': retry_after
                    }), 429)
                
                response.headers['X-RateLimit-Limit'] = str(max_requests)
                response.headers['X-RateLimit-Remaining'] = '0'
                response.headers['X-RateLimit-Reset'] = str(reset_time)
                response.headers['Retry-After'] = str(retry_after)
                return response
            
            result = func(*args, **kwargs)
            response = make_response(result)
            response.headers['X-RateLimit-Limit'] = str(max_requests)
            response.headers['X-RateLimit-Remaining'] = str(remaining)
            response.headers['X-RateLimit-Reset'] = str(reset_time)
            return response
        return wrapper
    return decorator


def rate_limit_api(max_requests=100, window_minutes=1, feature_name="api"):
    """
    API-specific rate limiting with higher defaults and JSON responses only
    
    Args:
        max_requests: Maximum requests within window
        window_minutes: Time window in minutes  
        feature_name: Feature name for key prefixing
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            client_id = get_client_identifier()
            window_seconds = window_minutes * 60
            
            allowed, remaining, reset_time = _check_rate_limit_redis(
                client_id=client_id,
                max_requests=max_requests,
                window_seconds=window_seconds,
                feature_name=feature_name
            )
            
            if not allowed:
                logger.warning(
                    f"API rate limit exceeded: {client_id} - {feature_name}"
                )
                retry_after = max(1, reset_time - int(time.time()))
                response = make_response(jsonify({
                    'success': False,
                    'error': 'rate_limit_exceeded',
                    'message': f'Rate limit: {max_requests} requests per {window_minutes} minute(s)',
                    'retry_after_seconds': retry_after
                }), 429)
                response.headers['X-RateLimit-Limit'] = str(max_requests)
                response.headers['X-RateLimit-Remaining'] = '0'
                response.headers['X-RateLimit-Reset'] = str(reset_time)
                response.headers['Retry-After'] = str(retry_after)
                return response
            
            result = func(*args, **kwargs)
            response = make_response(result)
            response.headers['X-RateLimit-Limit'] = str(max_requests)
            response.headers['X-RateLimit-Remaining'] = str(remaining)
            response.headers['X-RateLimit-Reset'] = str(reset_time)
            return response
        return wrapper
    return decorator


def get_rate_limit_info(
    client_id: Optional[str] = None,
    feature_name: str = "basic",
    max_requests: int = 10,
    window_seconds: int = 3600
) -> dict:
    """获取客户端的频率限制信息 Get client rate limit info"""
    if client_id is None:
        try:
            client_id = get_client_identifier()
        except RuntimeError:
            return {
                'requests_count': 0,
                'remaining': max_requests,
                'reset_time': None
            }
    
    redis_client = get_redis_client()
    if redis_client:
        try:
            key = f"ratelimit:{feature_name}:{client_id}"
            now = time.time()
            window_start = now - window_seconds
            
            redis_client.zremrangebyscore(key, 0, window_start)
            count = redis_client.zcard(key)
            oldest_entries = redis_client.zrange(key, 0, 0, withscores=True)
            
            if oldest_entries:
                oldest_timestamp = oldest_entries[0][1]
                reset_time = datetime.fromtimestamp(oldest_timestamp + window_seconds)
            else:
                reset_time = datetime.fromtimestamp(now + window_seconds)
            
            return {
                'requests_count': count,
                'remaining': max(0, max_requests - count),
                'reset_time': reset_time,
                'backend': 'redis'
            }
        except Exception as e:
            logger.error(f"Error getting rate limit info: {e}")
    
    store_key = f"{feature_name}:{client_id}"
    timestamps = _rate_limit_store.get(store_key, [])
    recent_count = len(timestamps)
    
    if timestamps:
        oldest = min(timestamps)
        reset_time = oldest + timedelta(seconds=window_seconds)
    else:
        reset_time = datetime.now() + timedelta(seconds=window_seconds)
    
    return {
        'requests_count': recent_count,
        'remaining': max(0, max_requests - recent_count),
        'reset_time': reset_time,
        'backend': 'memory'
    }


def get_rate_limiter_status() -> dict:
    """Get rate limiter system status"""
    redis_client = get_redis_client()
    
    if redis_client:
        try:
            redis_client.ping()
            return {
                'backend': 'redis',
                'status': 'healthy',
                'distributed': True
            }
        except Exception as e:
            return {
                'backend': 'redis',
                'status': 'error',
                'error': str(e),
                'distributed': False
            }
    
    return {
        'backend': 'memory',
        'status': 'fallback',
        'distributed': False,
        'warning': 'Rate limiting is per-worker only'
    }


def cleanup_expired_records():
    """Clean up expired in-memory records"""
    cutoff = datetime.now() - timedelta(hours=2)
    to_remove = []
    
    for key, timestamps in _rate_limit_store.items():
        _rate_limit_store[key] = [t for t in timestamps if t > cutoff]
        if not _rate_limit_store[key]:
            to_remove.append(key)
    
    for key in to_remove:
        del _rate_limit_store[key]
