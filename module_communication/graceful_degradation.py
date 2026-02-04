"""
Graceful Degradation and Fallback Mechanisms
优雅降级和回退机制 - 确保在模块不可用时系统仍能正常运行
"""

import logging
import time
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime, timedelta
from functools import wraps
from dataclasses import dataclass, field

try:
    from .common.config import config
    from .common.utils import CircuitBreaker, format_error_response, format_success_response
except ImportError:
    from common.config import config
    from common.utils import CircuitBreaker, format_error_response, format_success_response
try:
    from .service_registry import service_registry
except ImportError:
    from service_registry import service_registry

logger = logging.getLogger(__name__)

@dataclass
class FallbackConfig:
    """回退配置类"""
    cache_ttl: int = 300  # 缓存TTL（秒）
    max_retries: int = 3
    retry_delay: float = 1.0
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: int = 60
    fallback_data_ttl: int = 3600  # 回退数据TTL（秒）

class GracefulDegradationManager:
    """优雅降级管理器"""
    
    def __init__(self, fallback_config: FallbackConfig = None):
        self.config = fallback_config or FallbackConfig()
        self.cache = {}
        self.fallback_data = {}
        self.circuit_breakers = {}
        self.service_health_status = {}
        
        logger.info("Graceful Degradation Manager initialized")
    
    def get_circuit_breaker(self, service_name: str) -> CircuitBreaker:
        """获取或创建服务的熔断器"""
        if service_name not in self.circuit_breakers:
            self.circuit_breakers[service_name] = CircuitBreaker(
                failure_threshold=self.config.circuit_breaker_threshold,
                recovery_timeout=self.config.circuit_breaker_timeout
            )
        return self.circuit_breakers[service_name]
    
    def is_service_healthy(self, service_name: str) -> bool:
        """检查服务是否健康"""
        instances = service_registry.discover_service(service_name, healthy_only=True)
        is_healthy = len(instances) > 0
        
        # 更新服务健康状态
        self.service_health_status[service_name] = {
            'healthy': is_healthy,
            'instance_count': len(instances),
            'last_check': datetime.utcnow()
        }
        
        return is_healthy
    
    def cache_response(self, cache_key: str, data: Any, ttl: int = None):
        """缓存响应数据"""
        ttl = ttl or self.config.cache_ttl
        expires_at = datetime.utcnow() + timedelta(seconds=ttl)
        
        self.cache[cache_key] = {
            'data': data,
            'cached_at': datetime.utcnow(),
            'expires_at': expires_at
        }
        
        logger.debug(f"Cached response for key: {cache_key}")
    
    def get_cached_response(self, cache_key: str) -> Optional[Any]:
        """获取缓存的响应"""
        if cache_key in self.cache:
            cache_entry = self.cache[cache_key]
            if datetime.utcnow() < cache_entry['expires_at']:
                logger.debug(f"Cache hit for key: {cache_key}")
                return cache_entry['data']
            else:
                # 清理过期缓存
                del self.cache[cache_key]
                logger.debug(f"Cache expired for key: {cache_key}")
        
        return None
    
    def set_fallback_data(self, service_name: str, operation: str, data: Any):
        """设置回退数据"""
        fallback_key = f"{service_name}:{operation}"
        self.fallback_data[fallback_key] = {
            'data': data,
            'updated_at': datetime.utcnow()
        }
        logger.info(f"Set fallback data for {fallback_key}")
    
    def get_fallback_data(self, service_name: str, operation: str) -> Optional[Any]:
        """获取回退数据"""
        fallback_key = f"{service_name}:{operation}"
        
        if fallback_key in self.fallback_data:
            fallback_entry = self.fallback_data[fallback_key]
            
            # 检查回退数据是否过期
            age = (datetime.utcnow() - fallback_entry['updated_at']).total_seconds()
            if age < self.config.fallback_data_ttl:
                logger.info(f"Using fallback data for {fallback_key}")
                return fallback_entry['data']
            else:
                logger.warning(f"Fallback data expired for {fallback_key}")
        
        return None
    
    def with_fallback(self, 
                     service_name: str, 
                     operation: str, 
                     primary_func: Callable,
                     fallback_func: Callable = None,
                     cache_result: bool = True) -> Any:
        """使用回退机制执行操作"""
        cache_key = f"{service_name}:{operation}:{hash(str(primary_func.__name__))}"
        
        # 1. 尝试从缓存获取
        if cache_result:
            cached_result = self.get_cached_response(cache_key)
            if cached_result:
                return cached_result
        
        # 2. 检查服务健康状态
        if not self.is_service_healthy(service_name):
            logger.warning(f"Service {service_name} is unhealthy, trying fallback")
            return self._execute_fallback(service_name, operation, fallback_func)
        
        # 3. 尝试执行主要功能
        circuit_breaker = self.get_circuit_breaker(service_name)
        
        try:
            @circuit_breaker
            def execute_primary():
                return primary_func()
            
            result = execute_primary()
            
            # 成功时缓存结果和更新回退数据
            if cache_result:
                self.cache_response(cache_key, result)
            
            if result and result.get('success', True):
                self.set_fallback_data(service_name, operation, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Primary function failed for {service_name}:{operation}: {e}")
            return self._execute_fallback(service_name, operation, fallback_func, str(e))
    
    def _execute_fallback(self, 
                         service_name: str, 
                         operation: str, 
                         fallback_func: Callable = None,
                         primary_error: str = None) -> Any:
        """执行回退逻辑"""
        
        # 1. 尝试自定义回退函数
        if fallback_func:
            try:
                logger.info(f"Executing custom fallback for {service_name}:{operation}")
                return fallback_func()
            except Exception as e:
                logger.error(f"Custom fallback failed for {service_name}:{operation}: {e}")
        
        # 2. 尝试使用回退数据
        fallback_data = self.get_fallback_data(service_name, operation)
        if fallback_data:
            # 标记数据来源为回退
            if isinstance(fallback_data, dict):
                fallback_data['_fallback'] = True
                fallback_data['_fallback_reason'] = primary_error or 'Service unavailable'
            return fallback_data
        
        # 3. 返回默认错误响应
        logger.error(f"No fallback available for {service_name}:{operation}")
        return format_error_response(
            'SERVICE_UNAVAILABLE',
            f'Service {service_name} is temporarily unavailable',
            {'service': service_name, 'operation': operation, 'fallback_attempted': True}
        )

# 装饰器版本的优雅降级
def with_graceful_degradation(service_name: str, 
                            operation: str, 
                            fallback_func: Callable = None,
                            cache_result: bool = True):
    """优雅降级装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            manager = graceful_degradation_manager
            
            def primary_func():
                return func(*args, **kwargs)
            
            return manager.with_fallback(
                service_name=service_name,
                operation=operation,
                primary_func=primary_func,
                fallback_func=fallback_func,
                cache_result=cache_result
            )
        
        return wrapper
    return decorator

# 服务特定的回退函数
class ServiceFallbacks:
    """服务特定的回退函数集合"""
    
    @staticmethod
    def user_authentication_fallback():
        """用户认证回退"""
        return format_error_response(
            'AUTH_SERVICE_UNAVAILABLE',
            'Authentication service is temporarily unavailable. Please try again later.',
            {'fallback': True, 'retry_after': 60}
        )
    
    @staticmethod
    def mining_calculation_fallback():
        """挖矿计算回退"""
        # 返回基本的计算结果
        return format_success_response({
            'fallback': True,
            'message': 'Using cached market data for calculation',
            'daily_profit_usd': 15.0,  # 基于历史平均值
            'warning': 'Results based on cached data and may not be current'
        })
    
    @staticmethod
    def web3_payment_fallback():
        """Web3支付回退"""
        return format_error_response(
            'PAYMENT_SERVICE_UNAVAILABLE',
            'Payment service is temporarily unavailable. Your request has been queued.',
            {
                'fallback': True,
                'queued': True,
                'estimated_processing_time': '5-10 minutes'
            }
        )
    
    @staticmethod
    def subscription_check_fallback():
        """订阅检查回退"""
        # 在无法验证时，给予基本访问权限
        return format_success_response({
            'fallback': True,
            'subscription_level': 'free',
            'features': {
                'basic_calculations': True,
                'advanced_analytics': False,
                'api_access': False
            },
            'warning': 'Unable to verify subscription. Basic access granted.'
        })

# 健康监控和自动恢复
class ServiceHealthMonitor:
    """服务健康监控器"""
    
    def __init__(self, check_interval: int = 30):
        self.check_interval = check_interval
        self.degradation_manager = graceful_degradation_manager
        self.monitoring_active = False
    
    def start_monitoring(self):
        """开始健康监控"""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        
        import threading
        def monitor_loop():
            while self.monitoring_active:
                try:
                    self._check_all_services()
                    time.sleep(self.check_interval)
                except Exception as e:
                    logger.error(f"Health monitoring error: {e}")
                    time.sleep(5)
        
        monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        monitor_thread.start()
        
        logger.info("Service health monitoring started")
    
    def stop_monitoring(self):
        """停止健康监控"""
        self.monitoring_active = False
        logger.info("Service health monitoring stopped")
    
    def _check_all_services(self):
        """检查所有服务的健康状态"""
        services = ['mining_core', 'web3_integration', 'user_management']
        
        for service_name in services:
            try:
                is_healthy = self.degradation_manager.is_service_healthy(service_name)
                
                # 如果服务恢复健康，重置熔断器
                if is_healthy and service_name in self.degradation_manager.circuit_breakers:
                    circuit_breaker = self.degradation_manager.circuit_breakers[service_name]
                    if circuit_breaker.state == 'OPEN':
                        circuit_breaker.state = 'CLOSED'
                        circuit_breaker.failure_count = 0
                        logger.info(f"Service {service_name} recovered, circuit breaker reset")
                
            except Exception as e:
                logger.error(f"Health check failed for {service_name}: {e}")

# 全局实例
graceful_degradation_manager = GracefulDegradationManager()
service_health_monitor = ServiceHealthMonitor()

# 启动函数
def start_graceful_degradation():
    """启动优雅降级系统"""
    service_health_monitor.start_monitoring()
    logger.info("Graceful degradation system started")

def stop_graceful_degradation():
    """停止优雅降级系统"""
    service_health_monitor.stop_monitoring()
    logger.info("Graceful degradation system stopped")
