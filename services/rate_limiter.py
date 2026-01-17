"""
Redis-based Rate Limiter for Command Dispatch
Implements sliding window algorithm for rate limiting commands per site + command_type
"""

import logging
import os
import time
from typing import Tuple, Optional, Dict, Any

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    redis = None
    REDIS_AVAILABLE = False
    # Note: logging not yet configured, will use warning later

logger = logging.getLogger(__name__)

if not REDIS_AVAILABLE:
    logger.warning("Redis library not available - rate limiting disabled")

# Rate limit configuration at module level
RATE_LIMITS = {
    'reboot': {'limit': 5, 'window_sec': 300},
    'restart': {'limit': 5, 'window_sec': 300},
    'default': {'limit': 20, 'window_sec': 60}
}

# Global Redis client instance
_redis_client: Optional[redis.Redis] = None


def get_redis_client() -> Optional[redis.Redis]:
    """
    Get or create Redis client from REDIS_URL environment variable
    
    Returns:
        redis.Redis client instance or None if Redis is unavailable
    """
    global _redis_client
    
    if not REDIS_AVAILABLE:
        logger.warning("Redis library not available, rate limiting disabled")
        return None
    
    if _redis_client is not None:
        return _redis_client
    
    redis_url = os.environ.get('REDIS_URL')
    if not redis_url:
        logger.warning("REDIS_URL environment variable not set, rate limiting disabled")
        return None
    
    try:
        _redis_client = redis.from_url(redis_url, decode_responses=True)
        _redis_client.ping()
        logger.info("Redis connection established for rate limiting")
        return _redis_client
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        return None


def _get_rate_limit_config(command_type: str) -> Dict[str, int]:
    """
    Get rate limit config for a specific command type
    
    Args:
        command_type: Command type (e.g., 'reboot', 'restart', 'set_frequency')
    
    Returns:
        Dict with 'limit' and 'window_sec' keys
    """
    command_type_lower = command_type.lower()
    return RATE_LIMITS.get(command_type_lower, RATE_LIMITS['default'])


def _get_rate_limit_key(site_id: int, command_type: str) -> str:
    """
    Generate Redis sorted set key for rate limit tracking
    
    Args:
        site_id: Site ID
        command_type: Command type
    
    Returns:
        Redis key string
    """
    return f"rate_limit:{site_id}:{command_type.lower()}"


def check_rate_limit(site_id: int, command_type: str) -> Tuple[bool, Dict[str, Any]]:
    """
    Check if a command can be dispatched without exceeding rate limit.
    Uses sliding window algorithm with Redis sorted sets.
    
    Args:
        site_id: Site ID
        command_type: Command type (e.g., 'reboot', 'restart', 'set_frequency')
    
    Returns:
        Tuple of (allowed: bool, info_dict: dict)
        
        When REDIS_AVAILABLE is False:
        - Returns (True, {'rate_limit_disabled': True})
        
        When Redis is available:
        info_dict contains:
        - allowed (bool): Whether the command is allowed
        - current_count (int): Current number of commands in the window
        - limit (int): Rate limit threshold
        - window_sec (int): Time window in seconds
        - reset_at (float or None): Unix timestamp when the oldest command exits the window
        - error (str or None): Error message if any
    """
    # If Redis library is not available, return early
    if not REDIS_AVAILABLE:
        logger.warning(
            f"Rate limiting disabled - Redis library not available for site {site_id} command_type={command_type}"
        )
        return True, {'rate_limit_disabled': True}
    
    redis_client = get_redis_client()
    config = _get_rate_limit_config(command_type)
    key = _get_rate_limit_key(site_id, command_type)
    
    info_dict = {
        'allowed': False,
        'current_count': 0,
        'limit': config['limit'],
        'window_sec': config['window_sec'],
        'reset_at': None,
        'error': None
    }
    
    # If Redis is unavailable, allow the command (fail open)
    if redis_client is None:
        logger.warning(
            f"Redis unavailable, allowing command for site {site_id} command_type={command_type}"
        )
        info_dict['allowed'] = True
        info_dict['error'] = 'Redis unavailable'
        return True, info_dict
    
    try:
        now = time.time()
        window_start = now - config['window_sec']
        
        # Remove entries outside the sliding window (older than window_start)
        redis_client.zremrangebyscore(key, '-inf', window_start)
        
        # Count remaining entries within the window
        current_count = redis_client.zcard(key)
        info_dict['current_count'] = current_count
        
        # Check if limit is exceeded
        if current_count >= config['limit']:
            info_dict['allowed'] = False
            
            # Get the oldest entry to calculate when limit will be available again
            oldest = redis_client.zrange(key, 0, 0, withscores=True)
            if oldest:
                oldest_timestamp = oldest[0][1]
                reset_at = oldest_timestamp + config['window_sec']
                info_dict['reset_at'] = reset_at
            
            logger.warning(
                f"Rate limit exceeded for site {site_id} command_type={command_type}: "
                f"{current_count}/{config['limit']} in {config['window_sec']}s window"
            )
        else:
            info_dict['allowed'] = True
        
        return info_dict['allowed'], info_dict
        
    except Exception as e:
        logger.error(
            f"Error checking rate limit for site {site_id} command_type={command_type}: {e}"
        )
        # Allow command if Redis error (fail open for availability)
        info_dict['allowed'] = True
        info_dict['error'] = str(e)
        return True, info_dict


def record_command_dispatch(site_id: int, command_type: str) -> Dict[str, Any]:
    """
    Record a dispatched command in rate limit tracking.
    Adds current timestamp to the sliding window.
    
    Args:
        site_id: Site ID
        command_type: Command type
    
    Returns:
        Status dict with:
        - recorded (bool): Whether the record was successfully saved
        - current_count (int): Current number of commands in the window after recording
        - limit (int): Rate limit threshold
        - error (str or None): Error message if any
    """
    config = _get_rate_limit_config(command_type)
    
    result = {
        'recorded': False,
        'current_count': 0,
        'limit': config['limit'],
        'error': None
    }
    
    # If Redis library is not available, skip recording
    if not REDIS_AVAILABLE:
        logger.debug(
            f"Redis library not available, skipping record for site {site_id} command_type={command_type}"
        )
        result['recorded'] = True  # Consider it recorded if Redis unavailable
        return result
    
    redis_client = get_redis_client()
    key = _get_rate_limit_key(site_id, command_type)
    
    if redis_client is None:
        logger.debug(
            f"Redis unavailable, skipping record for site {site_id} command_type={command_type}"
        )
        result['recorded'] = True  # Consider it recorded if Redis unavailable
        return result
    
    try:
        now = time.time()
        
        # Add current timestamp to the sorted set with timestamp as both member and score
        redis_client.zadd(key, {str(now): now})
        
        # Set expiry on the key to prevent unbounded growth
        # Use window_sec + buffer to ensure all entries can be cleaned up
        redis_client.expire(key, config['window_sec'] + 60)
        
        # Get current count after recording
        current_count = redis_client.zcard(key)
        result['recorded'] = True
        result['current_count'] = current_count
        
        logger.debug(
            f"Recorded command for site {site_id} command_type={command_type}: "
            f"{current_count}/{config['limit']}"
        )
        
        return result
        
    except Exception as e:
        logger.error(
            f"Error recording command for site {site_id} command_type={command_type}: {e}"
        )
        result['recorded'] = False
        result['error'] = str(e)
        return result


def get_rate_limit_status(site_id: int, command_type: str) -> Dict[str, Any]:
    """
    Get current rate limit usage statistics for a site + command type.
    
    Args:
        site_id: Site ID
        command_type: Command type
    
    Returns:
        Status dict with:
        - command_type (str): Normalized command type
        - site_id (int): Site ID
        - current_count (int): Current number of commands in the window
        - limit (int): Rate limit threshold
        - window_sec (int): Time window in seconds
        - usage_percentage (float): Percentage of limit used (0-100+)
        - reset_at (float or None): Unix timestamp when the oldest command exits the window
        - error (str or None): Error message if any
    """
    config = _get_rate_limit_config(command_type)
    
    status = {
        'command_type': command_type.lower(),
        'site_id': site_id,
        'current_count': 0,
        'limit': config['limit'],
        'window_sec': config['window_sec'],
        'usage_percentage': 0.0,
        'reset_at': None,
        'error': None
    }
    
    # If Redis library is not available, return status with error
    if not REDIS_AVAILABLE:
        logger.warning(f"Rate limiting disabled - Redis library not available for site {site_id}")
        status['error'] = 'Redis library not available'
        return status
    
    redis_client = get_redis_client()
    key = _get_rate_limit_key(site_id, command_type)
    
    if redis_client is None:
        status['error'] = 'Redis unavailable'
        return status
    
    try:
        now = time.time()
        window_start = now - config['window_sec']
        
        # Remove old entries outside the sliding window
        redis_client.zremrangebyscore(key, '-inf', window_start)
        
        # Count remaining entries within the window
        current_count = redis_client.zcard(key)
        status['current_count'] = current_count
        status['usage_percentage'] = (current_count / config['limit']) * 100.0
        
        # Get reset time from oldest entry
        oldest = redis_client.zrange(key, 0, 0, withscores=True)
        if oldest:
            oldest_timestamp = oldest[0][1]
            reset_at = oldest_timestamp + config['window_sec']
            status['reset_at'] = reset_at
        
        logger.debug(
            f"Rate limit status for site {site_id} command_type={command_type}: "
            f"{current_count}/{config['limit']} ({status['usage_percentage']:.1f}%)"
        )
        
        return status
        
    except Exception as e:
        logger.error(
            f"Error getting rate limit status for site {site_id} command_type={command_type}: {e}"
        )
        status['error'] = str(e)
        return status
