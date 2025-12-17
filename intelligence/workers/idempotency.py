"""
Idempotency Decorator for Worker Tasks
======================================

This module provides a Redis-based idempotency decorator to cache task results
and ensure tasks can be safely retried without side effects.
"""

import functools
import json
import logging
import inspect
import hashlib
from typing import Callable, Any
from datetime import datetime, date
from redis import Redis, RedisError
import os

logger = logging.getLogger(__name__)


def get_redis_client():
    """Get Redis client from environment configuration."""
    redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    return Redis.from_url(redis_url, decode_responses=True)


class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder for datetime objects."""
    
    def default(self, o):
        if isinstance(o, (datetime, date)):
            return {
                '__type__': 'datetime',
                'value': o.isoformat()
            }
        return super().default(o)


def datetime_decoder(dct):
    """Custom JSON decoder for datetime objects."""
    if '__type__' in dct and dct['__type__'] == 'datetime':
        return datetime.fromisoformat(dct['value'])
    return dct


def idempotent(result_key_template: str, ttl: int = 3600, include_all_args: bool = True, graceful_degradation: bool = True):
    """
    Idempotency decorator - caches task execution results.
    
    Args:
        result_key_template: Result key template, e.g., "result:recalc:{user_id}"
        ttl: Result cache time in seconds (default 3600)
        include_all_args: If True, hash all arguments and append to key for uniqueness (default True)
        graceful_degradation: If True, execute task without caching if Redis unavailable (default True)
    
    Usage:
        @idempotent("result:task:{user_id}", ttl=1800, include_all_args=True)
        def my_task(user_id, other_param=None):
            ...
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                sig = inspect.signature(func)
                bound_args = sig.bind(*args, **kwargs)
                bound_args.apply_defaults()
                
                format_params = {}
                for param_name, param_value in bound_args.arguments.items():
                    if hasattr(param_value, 'isoformat'):
                        format_params[param_name] = param_value.isoformat()
                    else:
                        format_params[param_name] = param_value
                
                result_key = result_key_template.format(**format_params)
                
                if include_all_args:
                    args_dict = dict(bound_args.arguments)
                    args_json = json.dumps(args_dict, sort_keys=True, cls=DateTimeEncoder)
                    args_hash = hashlib.md5(args_json.encode()).hexdigest()[:8]
                    result_key = f"{result_key}:{args_hash}"
                    logger.debug(f"Generated idempotency key with args hash: {result_key}")
                
            except Exception as e:
                logger.warning(f"Failed to construct result key from template '{result_key_template}': {e}")
                if graceful_degradation:
                    logger.info(f"Executing {func.__name__} without idempotency due to key construction error")
                    return func(*args, **kwargs)
                raise
            
            try:
                redis_client = get_redis_client()
                
                cached_result = redis_client.get(result_key)
                if cached_result:
                    logger.info(f"Returning cached idempotent result for '{result_key}'")
                    return json.loads(cached_result, object_hook=datetime_decoder)
                
            except RedisError as e:
                logger.error(f"Redis error checking cached result for {func.__name__}: {e}")
                if graceful_degradation:
                    logger.info(f"Executing {func.__name__} without idempotency check due to Redis error")
                else:
                    raise
            
            result = func(*args, **kwargs)
            
            try:
                redis_client = get_redis_client()
                serialized_result = json.dumps(result, cls=DateTimeEncoder)
                redis_client.setex(result_key, ttl, serialized_result)
                logger.info(f"Cached idempotent result for '{result_key}' (TTL: {ttl}s)")
                
            except RedisError as e:
                logger.error(f"Redis error caching result for {func.__name__}: {e}")
                if not graceful_degradation:
                    raise
                
            except (TypeError, ValueError) as e:
                logger.error(f"Failed to serialize result for {func.__name__}: {e}")
                if not graceful_degradation:
                    raise
            
            return result
        
        return wrapper
    return decorator
