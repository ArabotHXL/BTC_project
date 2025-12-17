"""
Utility Functions for Module Communication
模块间通信工具函数
"""

import json
import time
import logging
import requests
from typing import Dict, Any, Optional, List
from datetime import datetime
from functools import wraps
import threading

logger = logging.getLogger(__name__)

class CircuitBreaker:
    """熔断器模式实现"""
    
    def __init__(self, 
                 failure_threshold: int = 5, 
                 recovery_timeout: int = 60, 
                 expected_exception: type = Exception):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
        self._lock = threading.Lock()
    
    def __call__(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with self._lock:
                if self.state == 'OPEN':
                    if self._should_attempt_reset():
                        self.state = 'HALF_OPEN'
                    else:
                        raise Exception(f"Circuit breaker is OPEN for {func.__name__}")
                
                try:
                    result = func(*args, **kwargs)
                    self._on_success()
                    return result
                except self.expected_exception as e:
                    self._on_failure()
                    raise e
        
        return wrapper
    
    def _should_attempt_reset(self) -> bool:
        """检查是否应该尝试重置熔断器"""
        return (time.time() - self.last_failure_time) >= self.recovery_timeout
    
    def _on_success(self):
        """成功时的处理"""
        self.failure_count = 0
        self.state = 'CLOSED'
    
    def _on_failure(self):
        """失败时的处理"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = 'OPEN'

class RetryMechanism:
    """重试机制"""
    
    def __init__(self, 
                 max_retries: int = 3, 
                 backoff_factor: float = 1.0, 
                 retry_exceptions: tuple = (Exception,)):
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.retry_exceptions = retry_exceptions
    
    def __call__(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(self.max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except self.retry_exceptions as e:
                    last_exception = e
                    if attempt < self.max_retries:
                        sleep_time = self.backoff_factor * (2 ** attempt)
                        logger.warning(f"Attempt {attempt + 1} failed for {func.__name__}, retrying in {sleep_time}s: {e}")
                        time.sleep(sleep_time)
                    else:
                        logger.error(f"All {self.max_retries + 1} attempts failed for {func.__name__}")
                        raise last_exception
            
            raise last_exception
        
        return wrapper

class RateLimiter:
    """速率限制器"""
    
    def __init__(self, max_requests: int = 100, time_window: int = 60):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = {}
        self._lock = threading.Lock()
    
    def is_allowed(self, identifier: str) -> bool:
        """检查是否允许请求"""
        with self._lock:
            current_time = time.time()
            
            # 清理过期记录
            if identifier in self.requests:
                self.requests[identifier] = [
                    req_time for req_time in self.requests[identifier]
                    if current_time - req_time < self.time_window
                ]
            
            # 检查当前请求数
            request_count = len(self.requests.get(identifier, []))
            
            if request_count >= self.max_requests:
                logger.warning(f"Rate limit exceeded for {identifier}")
                return False
            
            # 记录当前请求
            if identifier not in self.requests:
                self.requests[identifier] = []
            self.requests[identifier].append(current_time)
            
            return True

class HealthChecker:
    """健康检查器"""
    
    def __init__(self, timeout: int = 5):
        self.timeout = timeout
    
    def check_module_health(self, module_config: Dict[str, Any]) -> Dict[str, Any]:
        """检查模块健康状态"""
        try:
            url = f"{module_config['base_url']}{module_config['health_endpoint']}"
            
            start_time = time.time()
            response = requests.get(url, timeout=self.timeout)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                health_data = response.json() if response.headers.get('content-type') == 'application/json' else {}
                
                return {
                    'status': 'healthy',
                    'response_time': response_time,
                    'timestamp': datetime.utcnow().isoformat(),
                    'details': health_data
                }
            else:
                return {
                    'status': 'unhealthy',
                    'response_time': response_time,
                    'timestamp': datetime.utcnow().isoformat(),
                    'error': f"HTTP {response.status_code}"
                }
                
        except requests.exceptions.Timeout:
            return {
                'status': 'unhealthy',
                'timestamp': datetime.utcnow().isoformat(),
                'error': 'Connection timeout'
            }
        except requests.exceptions.ConnectionError:
            return {
                'status': 'unhealthy',
                'timestamp': datetime.utcnow().isoformat(),
                'error': 'Connection refused'
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'timestamp': datetime.utcnow().isoformat(),
                'error': str(e)
            }
    
    def check_all_modules(self, modules_config: Dict[str, Dict]) -> Dict[str, Dict]:
        """检查所有模块健康状态"""
        results = {}
        
        for module_name, config in modules_config.items():
            results[module_name] = self.check_module_health(config)
        
        return results

class RequestLogger:
    """请求日志记录器"""
    
    def __init__(self, log_level: int = logging.INFO):
        self.logger = logging.getLogger('module_communication.requests')
        self.logger.setLevel(log_level)
    
    def log_request(self, 
                   method: str, 
                   url: str, 
                   headers: Dict[str, str] = None, 
                   body: str = None, 
                   module_name: str = None):
        """记录请求"""
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'method': method,
            'url': url,
            'module': module_name
        }
        
        if headers:
            # 过滤敏感头信息
            safe_headers = {k: v for k, v in headers.items() 
                          if k.lower() not in ['authorization', 'x-api-key']}
            log_data['headers'] = safe_headers
        
        if body and len(body) < 1000:  # 只记录较小的请求体
            log_data['body'] = body
        
        self.logger.info(f"Request: {json.dumps(log_data)}")
    
    def log_response(self, 
                    status_code: int, 
                    response_time: float, 
                    response_body: str = None, 
                    module_name: str = None):
        """记录响应"""
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'status_code': status_code,
            'response_time': response_time,
            'module': module_name
        }
        
        if response_body and len(response_body) < 1000:  # 只记录较小的响应体
            log_data['response_body'] = response_body
        
        if status_code >= 400:
            self.logger.error(f"Response: {json.dumps(log_data)}")
        else:
            self.logger.info(f"Response: {json.dumps(log_data)}")

def format_error_response(error_code: str, 
                        message: str, 
                        details: Dict[str, Any] = None) -> Dict[str, Any]:
    """格式化错误响应"""
    response = {
        'error': {
            'code': error_code,
            'message': message,
            'timestamp': datetime.utcnow().isoformat()
        }
    }
    
    if details:
        response['error']['details'] = details
    
    return response

def format_success_response(data: Any, 
                          message: str = None, 
                          metadata: Dict[str, Any] = None) -> Dict[str, Any]:
    """格式化成功响应"""
    response = {
        'data': data,
        'timestamp': datetime.utcnow().isoformat()
    }
    
    if message:
        response['message'] = message
    
    if metadata:
        response['metadata'] = metadata
    
    return response

def validate_module_response(response_data: Dict[str, Any], 
                           required_fields: List[str] = None) -> bool:
    """验证模块响应格式"""
    if not isinstance(response_data, dict):
        return False
    
    if required_fields:
        for field in required_fields:
            if field not in response_data:
                logger.warning(f"Missing required field in response: {field}")
                return False
    
    return True

# 全局实例
health_checker = HealthChecker()
request_logger = RequestLogger()
rate_limiter = RateLimiter()