#!/usr/bin/env python3
"""
熔断器模式实现
Circuit Breaker Pattern Implementation

防止级联故障，提升系统韧性
Prevent cascading failures and improve system resilience

状态机：
- CLOSED: 正常状态，所有请求通过
- OPEN: 熔断状态，直接失败，不调用后端
- HALF_OPEN: 半开状态，允许部分请求测试后端是否恢复

State Machine:
- CLOSED: Normal state, all requests pass through
- OPEN: Circuit broken, fail fast without calling backend
- HALF_OPEN: Half-open, allow some requests to test if backend recovered
"""

import time
import logging
import threading
from enum import Enum
from typing import Callable, Any, Optional
from functools import wraps
from collections import deque
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """熔断器状态"""
    CLOSED = "closed"  # 正常
    OPEN = "open"  # 熔断
    HALF_OPEN = "half_open"  # 半开


class CircuitBreakerError(Exception):
    """熔断器异常"""
    pass


class CircuitBreakerOpenError(CircuitBreakerError):
    """熔断器打开异常"""
    pass


class CircuitBreaker:
    """
    熔断器
    Circuit Breaker
    
    Parameters:
    -----------
    failure_threshold : int
        失败阈值（连续失败次数）
    recovery_timeout : int
        恢复超时（秒）- OPEN状态持续时间
    expected_exception : tuple
        预期的异常类型（这些异常会触发熔断）
    name : str
        熔断器名称
    """
    
    def __init__(self, 
                 failure_threshold: int = 5,
                 recovery_timeout: int = 60,
                 expected_exception: tuple = (Exception,),
                 name: str = "default"):
        """初始化熔断器"""
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.name = name
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.last_state_change = time.time()
        
        self._lock = threading.Lock()
        
        # 统计信息
        self.stats = {
            'total_calls': 0,
            'successful_calls': 0,
            'failed_calls': 0,
            'rejected_calls': 0,
            'state_changes': []
        }
        
        logger.info(f"✅ 熔断器已初始化: {name} (失败阈值={failure_threshold}, 恢复超时={recovery_timeout}s)")
    
    def _change_state(self, new_state: CircuitState, reason: str = ""):
        """
        改变熔断器状态
        
        Parameters:
        -----------
        new_state : CircuitState
            新状态
        reason : str
            状态变更原因
        """
        old_state = self.state
        self.state = new_state
        self.last_state_change = time.time()
        
        # 记录状态变更
        self.stats['state_changes'].append({
            'from': old_state.value,
            'to': new_state.value,
            'reason': reason,
            'timestamp': datetime.utcnow().isoformat() + "Z"
        })
        
        logger.warning(
            f"🔄 熔断器 {self.name} 状态变更: {old_state.value} -> {new_state.value} "
            f"(原因: {reason})"
        )
    
    def _should_attempt_reset(self) -> bool:
        """
        判断是否应该尝试重置（进入HALF_OPEN状态）
        
        Returns:
        --------
        bool : 是否应该尝试重置
        """
        if self.state != CircuitState.OPEN:
            return False
        
        if self.last_failure_time is None:
            return True
        
        elapsed = time.time() - self.last_failure_time
        return elapsed >= self.recovery_timeout
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        通过熔断器调用函数
        
        Parameters:
        -----------
        func : Callable
            要调用的函数
        *args, **kwargs
            函数参数
            
        Returns:
        --------
        Any : 函数返回值
        
        Raises:
        -------
        CircuitBreakerOpenError : 熔断器打开，拒绝调用
        """
        with self._lock:
            self.stats['total_calls'] += 1
            
            # 检查是否需要尝试重置
            if self._should_attempt_reset():
                self._change_state(CircuitState.HALF_OPEN, "恢复超时已过，尝试重置")
            
            # 如果熔断器打开，直接拒绝
            if self.state == CircuitState.OPEN:
                self.stats['rejected_calls'] += 1
                raise CircuitBreakerOpenError(
                    f"Circuit breaker '{self.name}' is OPEN. "
                    f"Wait {self.recovery_timeout}s for recovery."
                )
        
        # 执行函数调用
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
            
        except self.expected_exception as e:
            self._on_failure(e)
            raise
    
    def _on_success(self):
        """处理成功调用"""
        with self._lock:
            self.stats['successful_calls'] += 1
            self.success_count += 1
            
            if self.state == CircuitState.HALF_OPEN:
                # 半开状态下成功，重置熔断器
                self.failure_count = 0
                self.success_count = 0
                self._change_state(CircuitState.CLOSED, "测试成功，服务恢复")
                
            elif self.state == CircuitState.CLOSED:
                # 正常状态下成功，重置失败计数
                self.failure_count = 0
    
    def _on_failure(self, exception: Exception):
        """处理失败调用"""
        with self._lock:
            self.stats['failed_calls'] += 1
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            logger.warning(
                f"⚠️  熔断器 {self.name} 记录失败 "
                f"(失败计数: {self.failure_count}/{self.failure_threshold}): {exception}"
            )
            
            if self.state == CircuitState.HALF_OPEN:
                # 半开状态下失败，重新打开熔断器
                self._change_state(CircuitState.OPEN, "测试失败，重新熔断")
                
            elif self.state == CircuitState.CLOSED:
                # 正常状态下失败次数达到阈值，打开熔断器
                if self.failure_count >= self.failure_threshold:
                    self._change_state(
                        CircuitState.OPEN,
                        f"连续失败{self.failure_count}次，触发熔断"
                    )
    
    def get_state(self) -> str:
        """获取当前状态"""
        return self.state.value
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        with self._lock:
            total = self.stats['total_calls']
            success_rate = (self.stats['successful_calls'] / total * 100) if total > 0 else 0
            failure_rate = (self.stats['failed_calls'] / total * 100) if total > 0 else 0
            rejection_rate = (self.stats['rejected_calls'] / total * 100) if total > 0 else 0
            
            return {
                'name': self.name,
                'state': self.state.value,
                'failure_count': self.failure_count,
                'success_count': self.success_count,
                'last_failure_time': datetime.fromtimestamp(self.last_failure_time).isoformat() if self.last_failure_time else None,
                'last_state_change': datetime.fromtimestamp(self.last_state_change).isoformat(),
                'stats': {
                    'total_calls': total,
                    'successful_calls': self.stats['successful_calls'],
                    'failed_calls': self.stats['failed_calls'],
                    'rejected_calls': self.stats['rejected_calls'],
                    'success_rate': f"{success_rate:.2f}%",
                    'failure_rate': f"{failure_rate:.2f}%",
                    'rejection_rate': f"{rejection_rate:.2f}%"
                },
                'recent_state_changes': self.stats['state_changes'][-5:]  # 最近5次状态变更
            }
    
    def reset(self):
        """手动重置熔断器"""
        with self._lock:
            self.failure_count = 0
            self.success_count = 0
            self._change_state(CircuitState.CLOSED, "手动重置")
            logger.info(f"🔄 熔断器 {self.name} 已手动重置")


def circuit_breaker(failure_threshold: int = 5,
                    recovery_timeout: int = 60,
                    expected_exception: tuple = (Exception,),
                    name: Optional[str] = None):
    """
    熔断器装饰器
    Circuit Breaker Decorator
    
    Parameters:
    -----------
    failure_threshold : int
        失败阈值
    recovery_timeout : int
        恢复超时（秒）
    expected_exception : tuple
        预期的异常类型
    name : str
        熔断器名称
    """
    def decorator(func: Callable) -> Callable:
        breaker_name = name or f"{func.__module__}.{func.__name__}"
        breaker = CircuitBreaker(
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            expected_exception=expected_exception,
            name=breaker_name
        )
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            return breaker.call(func, *args, **kwargs)
        
        # 附加熔断器到函数，方便访问统计信息
        wrapper.circuit_breaker = breaker
        
        return wrapper
    
    return decorator


class CircuitBreakerRegistry:
    """熔断器注册表"""
    
    def __init__(self):
        """初始化注册表"""
        self._breakers = {}
        self._lock = threading.Lock()
    
    def register(self, name: str, breaker: CircuitBreaker):
        """注册熔断器"""
        with self._lock:
            self._breakers[name] = breaker
            logger.info(f"✅ 熔断器已注册: {name}")
    
    def get(self, name: str) -> Optional[CircuitBreaker]:
        """获取熔断器"""
        return self._breakers.get(name)
    
    def get_all_stats(self) -> dict:
        """获取所有熔断器的统计信息"""
        with self._lock:
            return {
                name: breaker.get_stats()
                for name, breaker in self._breakers.items()
            }
    
    def reset_all(self):
        """重置所有熔断器"""
        with self._lock:
            for breaker in self._breakers.values():
                breaker.reset()
            logger.info("🔄 所有熔断器已重置")


# 全局熔断器注册表
circuit_breaker_registry = CircuitBreakerRegistry()


if __name__ == '__main__':
    # 测试熔断器
    import random
    
    @circuit_breaker(failure_threshold=3, recovery_timeout=5, name="test_api")
    def unstable_api_call():
        """模拟不稳定的API调用"""
        if random.random() < 0.7:  # 70%失败率
            raise Exception("API call failed")
        return "Success"
    
    print("测试熔断器...")
    
    for i in range(15):
        try:
            result = unstable_api_call()
            print(f"[{i+1}] ✅ {result}")
        except CircuitBreakerOpenError as e:
            print(f"[{i+1}] 🚫 Circuit breaker open: {e}")
        except Exception as e:
            print(f"[{i+1}] ❌ Failed: {e}")
        
        time.sleep(0.5)
    
    # 打印统计信息
    print("\n" + "="*60)
    print("熔断器统计:")
    print("="*60)
    import json
    print(json.dumps(unstable_api_call.circuit_breaker.get_stats(), indent=2, ensure_ascii=False))
