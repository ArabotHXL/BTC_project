"""
HashInsight Enterprise - Collector Security Module
采集器安全模块

Features:
- Telemetry payload schema validation
- Rate limiting per collector key
- Request size limiting
- Audit logging enhancements

Usage:
    from services.collector_security import (
        validate_telemetry_payload,
        RateLimiter,
        check_rate_limit
    )
"""

import time
import logging
from functools import wraps
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from flask import request, jsonify, g

logger = logging.getLogger('CollectorSecurity')

MAX_PAYLOAD_SIZE = 10 * 1024 * 1024  # 10MB
MAX_MINERS_PER_UPLOAD = 5000
MAX_REQUEST_RATE = 60  # requests per minute per key
RATE_LIMIT_WINDOW = 60  # seconds


class TelemetryValidationError(Exception):
    """Telemetry validation error with structured details"""
    
    def __init__(self, message: str, field: str = "", miner_id: str = ""):
        self.message = message
        self.field = field
        self.miner_id = miner_id
        super().__init__(f"[{field}] {message}" if field else message)


TELEMETRY_SCHEMA = {
    'miner_id': {'type': str, 'required': True, 'max_length': 50},
    'ip_address': {'type': str, 'required': False, 'max_length': 45},
    'online': {'type': bool, 'required': False},
    'hashrate_ghs': {'type': (int, float), 'required': False, 'min': 0, 'max': 1e12},
    'hashrate_5s_ghs': {'type': (int, float), 'required': False, 'min': 0, 'max': 1e12},
    'hashrate_expected_ghs': {'type': (int, float), 'required': False, 'min': 0, 'max': 1e12},
    'temperature_avg': {'type': (int, float), 'required': False, 'min': -50, 'max': 150},
    'temperature_min': {'type': (int, float), 'required': False, 'min': -50, 'max': 150},
    'temperature_max': {'type': (int, float), 'required': False, 'min': -50, 'max': 150},
    'temperature_chips': {'type': list, 'required': False, 'max_items': 100},
    'fan_speeds': {'type': list, 'required': False, 'max_items': 20},
    'frequency_avg': {'type': (int, float), 'required': False, 'min': 0, 'max': 10000},
    'accepted_shares': {'type': int, 'required': False, 'min': 0},
    'rejected_shares': {'type': int, 'required': False, 'min': 0},
    'hardware_errors': {'type': int, 'required': False, 'min': 0},
    'uptime_seconds': {'type': int, 'required': False, 'min': 0},
    'power_consumption': {'type': (int, float), 'required': False, 'min': 0, 'max': 100000},
    'efficiency': {'type': (int, float), 'required': False, 'min': 0, 'max': 1000},
    'pool_url': {'type': str, 'required': False, 'max_length': 255},
    'worker_name': {'type': str, 'required': False, 'max_length': 100},
    'pool_latency_ms': {'type': (int, float), 'required': False, 'min': 0, 'max': 60000},
    'boards': {'type': list, 'required': False, 'max_items': 10},
    'boards_total': {'type': int, 'required': False, 'min': 0, 'max': 20},
    'boards_healthy': {'type': int, 'required': False, 'min': 0, 'max': 20},
    'overall_health': {'type': str, 'required': False, 'max_length': 20},
    'model': {'type': str, 'required': False, 'max_length': 100},
    'firmware_version': {'type': str, 'required': False, 'max_length': 50},
    'error_message': {'type': str, 'required': False, 'max_length': 500},
    'latency_ms': {'type': (int, float), 'required': False, 'min': 0, 'max': 60000},
}

VALID_HEALTH_STATUS = frozenset({'healthy', 'degraded', 'critical', 'offline', 'unknown'})


def validate_single_miner(miner_data: Dict[str, Any], index: int = 0) -> Tuple[bool, Optional[str]]:
    """
    Validate a single miner telemetry record
    
    Returns:
        (is_valid, error_message)
    """
    if not isinstance(miner_data, dict):
        return False, f"Miner at index {index} is not a dict"
    
    for field, rules in TELEMETRY_SCHEMA.items():
        value = miner_data.get(field)
        
        if value is None:
            if rules.get('required', False):
                return False, f"Missing required field '{field}' in miner at index {index}"
            continue
        
        expected_type = rules['type']
        if not isinstance(value, expected_type):
            return False, f"Invalid type for '{field}' in miner at index {index}: expected {expected_type}, got {type(value)}"
        
        if isinstance(value, str):
            max_length = rules.get('max_length')
            if max_length and len(value) > max_length:
                return False, f"Field '{field}' exceeds max length {max_length} in miner at index {index}"
        
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            min_val = rules.get('min')
            max_val = rules.get('max')
            if min_val is not None and value < min_val:
                return False, f"Field '{field}' below minimum {min_val} in miner at index {index}"
            if max_val is not None and value > max_val:
                return False, f"Field '{field}' exceeds maximum {max_val} in miner at index {index}"
        
        if isinstance(value, list):
            max_items = rules.get('max_items')
            if max_items and len(value) > max_items:
                return False, f"Field '{field}' exceeds max items {max_items} in miner at index {index}"
    
    overall_health = miner_data.get('overall_health', '')
    if overall_health and overall_health not in VALID_HEALTH_STATUS:
        return False, f"Invalid overall_health '{overall_health}' in miner at index {index}"
    
    return True, None


def validate_telemetry_payload(data: Any, strict: bool = False) -> Tuple[bool, Optional[str], List[Dict[str, Any]]]:
    """
    Validate entire telemetry payload
    
    Args:
        data: The payload to validate (should be a list)
        strict: If True, fail on first invalid miner. If False, skip invalid miners.
    
    Returns:
        (is_valid, error_message, sanitized_data)
        
    Note:
        - Returns error if ALL miners in payload are invalid
        - In strict mode, returns error on first invalid miner
        - In non-strict mode, skips invalid miners but returns error if none remain valid
    """
    if not isinstance(data, list):
        return False, "Payload must be an array of miner data", []
    
    if len(data) > MAX_MINERS_PER_UPLOAD:
        return False, f"Payload exceeds maximum {MAX_MINERS_PER_UPLOAD} miners per upload", []
    
    if len(data) == 0:
        return True, None, []
    
    sanitized = []
    seen_miner_ids = set()
    validation_errors = []
    
    for i, miner_data in enumerate(data):
        is_valid, error = validate_single_miner(miner_data, i)
        
        if not is_valid:
            validation_errors.append(error)
            logger.warning(f"Validation failed: {error}")
            if strict:
                return False, error, []
            continue
        
        miner_id = miner_data.get('miner_id', '')
        if miner_id in seen_miner_ids:
            logger.warning(f"Duplicate miner_id '{miner_id}' at index {i}, skipping")
            continue
        seen_miner_ids.add(miner_id)
        
        sanitized_miner = {}
        for field in TELEMETRY_SCHEMA.keys():
            if field in miner_data:
                sanitized_miner[field] = miner_data[field]
        
        sanitized.append(sanitized_miner)
    
    if len(sanitized) == 0 and len(data) > 0:
        first_error = validation_errors[0] if validation_errors else "All miners failed validation"
        return False, f"No valid miners in payload. First error: {first_error}", []
    
    return True, None, sanitized


class RateLimiter:
    """
    In-memory rate limiter with sliding window
    
    For production, use Redis-backed implementation
    """
    
    def __init__(self, max_requests: int = MAX_REQUEST_RATE, window_seconds: int = RATE_LIMIT_WINDOW):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: Dict[str, List[float]] = {}
        self._cleanup_interval = 300
        self._last_cleanup = time.time()
    
    def _cleanup_old_entries(self):
        """Remove stale entries to prevent memory leak"""
        now = time.time()
        if now - self._last_cleanup < self._cleanup_interval:
            return
        
        cutoff = now - self.window_seconds * 2
        keys_to_remove = []
        
        for key, timestamps in self._requests.items():
            self._requests[key] = [t for t in timestamps if t > cutoff]
            if not self._requests[key]:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self._requests[key]
        
        self._last_cleanup = now
    
    def is_allowed(self, key: str) -> Tuple[bool, int, int]:
        """
        Check if request is allowed
        
        Returns:
            (allowed, remaining, reset_in_seconds)
        """
        self._cleanup_old_entries()
        
        now = time.time()
        cutoff = now - self.window_seconds
        
        if key not in self._requests:
            self._requests[key] = []
        
        self._requests[key] = [t for t in self._requests[key] if t > cutoff]
        
        current_count = len(self._requests[key])
        remaining = max(0, self.max_requests - current_count)
        
        if current_count < self.max_requests:
            self._requests[key].append(now)
            return True, remaining - 1, self.window_seconds
        
        oldest = min(self._requests[key]) if self._requests[key] else now
        reset_in = int(oldest + self.window_seconds - now)
        
        return False, 0, reset_in
    
    def get_stats(self, key: str) -> Dict[str, Any]:
        """Get rate limit stats for a key"""
        now = time.time()
        cutoff = now - self.window_seconds
        
        if key not in self._requests:
            return {
                'current_count': 0,
                'max_requests': self.max_requests,
                'window_seconds': self.window_seconds,
                'remaining': self.max_requests
            }
        
        timestamps = [t for t in self._requests[key] if t > cutoff]
        current_count = len(timestamps)
        
        return {
            'current_count': current_count,
            'max_requests': self.max_requests,
            'window_seconds': self.window_seconds,
            'remaining': max(0, self.max_requests - current_count)
        }


_rate_limiter = RateLimiter()


def get_rate_limiter() -> RateLimiter:
    """Get the global rate limiter instance"""
    return _rate_limiter


def check_rate_limit(key_identifier: str) -> Tuple[bool, Dict[str, Any]]:
    """
    Check rate limit for a collector key
    
    Returns:
        (allowed, headers_dict)
    """
    allowed, remaining, reset_in = _rate_limiter.is_allowed(key_identifier)
    
    headers = {
        'X-RateLimit-Limit': str(_rate_limiter.max_requests),
        'X-RateLimit-Remaining': str(remaining),
        'X-RateLimit-Reset': str(reset_in)
    }
    
    return allowed, headers


def rate_limit_decorator(f):
    """
    Decorator to apply rate limiting to collector endpoints
    
    Requires @verify_collector_key to be applied first
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        key_hash = getattr(g, 'collector_key', None)
        if key_hash:
            key_identifier = key_hash.key_hash[:16]
        else:
            key_identifier = request.remote_addr or 'unknown'
        
        allowed, headers = check_rate_limit(key_identifier)
        
        if not allowed:
            response = jsonify({
                'success': False,
                'error': 'Rate limit exceeded',
                'retry_after': headers['X-RateLimit-Reset']
            })
            response.status_code = 429
            for key, value in headers.items():
                response.headers[key] = value
            return response
        
        result = f(*args, **kwargs)
        
        if hasattr(result, 'headers'):
            for key, value in headers.items():
                result.headers[key] = value
        
        return result
    
    return decorated


def check_request_size(max_size: int = MAX_PAYLOAD_SIZE):
    """
    Decorator to check request body size
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            content_length = request.content_length
            
            if content_length and content_length > max_size:
                return jsonify({
                    'success': False,
                    'error': f'Request body exceeds maximum size of {max_size // (1024*1024)}MB'
                }), 413
            
            return f(*args, **kwargs)
        return decorated
    return decorator


def log_security_event(event_type: str, details: Dict[str, Any], level: str = 'info'):
    """
    Log security-related events
    
    Events:
    - rate_limit_exceeded
    - validation_failed
    - auth_failed
    - suspicious_request
    """
    log_entry = {
        'timestamp': datetime.utcnow().isoformat(),
        'event_type': event_type,
        'ip_address': request.remote_addr,
        'user_agent': request.user_agent.string if request.user_agent else None,
        'details': details
    }
    
    if level == 'warning':
        logger.warning(f"Security Event: {event_type}", extra=log_entry)
    elif level == 'error':
        logger.error(f"Security Event: {event_type}", extra=log_entry)
    else:
        logger.info(f"Security Event: {event_type}", extra=log_entry)
