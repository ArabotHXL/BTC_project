"""
Distributed Lock Decorator for Worker Tasks
==========================================

This module provides a Redis-based distributed lock decorator to ensure
only one instance of a task runs at a time across multiple workers.
"""

import functools
import logging
import inspect
import uuid
from typing import Callable
from datetime import datetime
from redis import Redis, RedisError
import os

logger = logging.getLogger(__name__)


def get_redis_client():
    """Get Redis client from environment configuration."""
    redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    return Redis.from_url(redis_url, decode_responses=True)


def distributed_lock(key_template: str, timeout: int = 300, graceful_degradation: bool = True):
    """
    Distributed lock decorator using Redis.
    
    Args:
        key_template: Lock key template, e.g., "lock:recalc:{user_id}"
        timeout: Lock timeout in seconds (default 300)
        graceful_degradation: If True, execute task without lock if Redis unavailable (default True)
    
    Usage:
        @distributed_lock("lock:task:{user_id}", timeout=300)
        def my_task(user_id):
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
                
                lock_key = key_template.format(**format_params)
                
            except Exception as e:
                logger.warning(f"Failed to construct lock key from template '{key_template}': {e}")
                if graceful_degradation:
                    logger.info(f"Executing {func.__name__} without lock due to key construction error")
                    return func(*args, **kwargs)
                raise
            
            redis_client = None
            lock_acquired = False
            lock_value = str(uuid.uuid4())
            
            try:
                redis_client = get_redis_client()
                
                lock_acquired = redis_client.set(lock_key, lock_value, nx=True, ex=timeout)
                
                if not lock_acquired:
                    logger.warning(f"Could not acquire lock '{lock_key}', task already running")
                    return {
                        'status': 'skipped',
                        'reason': 'lock_acquisition_failed',
                        'lock_key': lock_key,
                        'timestamp': datetime.utcnow()
                    }
                
                logger.info(f"Acquired lock '{lock_key}' with token {lock_value[:8]}... for {func.__name__}")
                result = func(*args, **kwargs)
                return result
                
            except RedisError as e:
                logger.error(f"Redis error in distributed lock for {func.__name__}: {e}")
                if graceful_degradation:
                    logger.info(f"Executing {func.__name__} without lock due to Redis error")
                    return func(*args, **kwargs)
                raise
                
            except Exception as e:
                logger.error(f"Error in {func.__name__}: {e}", exc_info=True)
                raise
                
            finally:
                if lock_acquired and redis_client:
                    try:
                        release_script = """
                        if redis.call("get", KEYS[1]) == ARGV[1] then
                            return redis.call("del", KEYS[1])
                        else
                            return 0
                        end
                        """
                        released = redis_client.eval(release_script, 1, lock_key, lock_value)
                        if released:
                            logger.info(f"Released lock '{lock_key}' (token {lock_value[:8]}...)")
                        else:
                            logger.warning(f"Lock '{lock_key}' was already released or acquired by another worker (token mismatch)")
                    except RedisError as e:
                        logger.error(f"Failed to release lock '{lock_key}': {e}")
        
        return wrapper
    return decorator
