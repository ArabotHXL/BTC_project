"""
Performance Monitor
系统性能监控和指标收集
"""

import logging
import time
import psutil
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
import os
from collections import deque, defaultdict
from functools import wraps

logger = logging.getLogger(__name__)

class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self.metrics_history = deque(maxlen=max_history)
        self.endpoint_metrics = defaultdict(list)
        self.request_times = defaultdict(deque)
        self.error_counts = defaultdict(int)
        self.start_time = datetime.now()
        self.is_monitoring = False
        self.monitor_thread = None
        
        logger.info("Performance Monitor initialized")
    
    def start_monitoring(self, interval: float = 30.0):
        """开始性能监控"""
        if self.is_monitoring:
            logger.warning("Performance monitoring already running")
            return
        
        self.is_monitoring = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            args=(interval,),
            daemon=True
        )
        self.monitor_thread.start()
        logger.info(f"Performance monitoring started with {interval}s interval")
    
    def stop_monitoring(self):
        """停止性能监控"""
        self.is_monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("Performance monitoring stopped")
    
    def _monitor_loop(self, interval: float):
        """监控循环"""
        while self.is_monitoring:
            try:
                metrics = self._collect_system_metrics()
                self.metrics_history.append(metrics)
                
                # 清理过期的请求时间记录
                self._cleanup_old_metrics()
                
                time.sleep(interval)
            except Exception as e:
                logger.error(f"Performance monitoring error: {e}")
                time.sleep(interval)
    
    def _collect_system_metrics(self) -> Dict:
        """收集系统指标"""
        try:
            # CPU和内存指标
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            metrics = {
                'timestamp': datetime.now().isoformat(),
                'cpu': {
                    'percent': cpu_percent,
                    'count': psutil.cpu_count()
                },
                'memory': {
                    'total': memory.total,
                    'available': memory.available,
                    'percent': memory.percent,
                    'used': memory.used
                },
                'disk': {
                    'total': disk.total,
                    'used': disk.used,
                    'free': disk.free,
                    'percent': (disk.used / disk.total) * 100
                }
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to collect system metrics: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'error': str(e)
            }
    
    def _cleanup_old_metrics(self):
        """清理过期指标"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=1)
            
            # 清理请求时间记录
            for endpoint in list(self.request_times.keys()):
                times = self.request_times[endpoint]
                while times and times[0] < cutoff_time:
                    times.popleft()
                
                if not times:
                    del self.request_times[endpoint]
                    
        except Exception as e:
            logger.error(f"Failed to cleanup old metrics: {e}")
    
    def record_request(self, endpoint: str, duration: float, status_code: int = 200):
        """记录请求指标"""
        try:
            now = datetime.now()
            
            # 记录请求时间
            self.request_times[endpoint].append(now)
            
            # 记录端点指标
            metric = {
                'timestamp': now.isoformat(),
                'endpoint': endpoint,
                'duration': duration,
                'status_code': status_code
            }
            
            self.endpoint_metrics[endpoint].append(metric)
            
            # 限制历史记录数量
            if len(self.endpoint_metrics[endpoint]) > 1000:
                self.endpoint_metrics[endpoint] = self.endpoint_metrics[endpoint][-500:]
            
            # 记录错误
            if status_code >= 400:
                self.error_counts[endpoint] += 1
                
        except Exception as e:
            logger.error(f"Failed to record request metric: {e}")
    
    def track_request(self, endpoint: str, duration: float, status_code: int = 200):
        """记录请求指标"""
        try:
            now = datetime.now()
            
            # 记录请求时间
            self.request_times[endpoint].append(now)
            
            # 记录端点指标
            metric = {
                'timestamp': now.isoformat(),
                'endpoint': endpoint,
                'duration': duration,
                'status_code': status_code
            }
            
            self.endpoint_metrics[endpoint].append(metric)
            
            # 限制历史记录数量
            if len(self.endpoint_metrics[endpoint]) > 1000:
                self.endpoint_metrics[endpoint] = self.endpoint_metrics[endpoint][-500:]
            
            # 记录错误
            if status_code >= 400:
                self.error_counts[endpoint] += 1
                
        except Exception as e:
            logger.error(f"Failed to record request metric: {e}")
    
    def get_metrics_summary(self) -> Dict:
        """获取指标摘要"""
        try:
            if not self.metrics_history:
                return {'error': 'No metrics available'}
            
            latest_metrics = self.metrics_history[-1]
            
            # 计算平均值
            cpu_values = [m.get('cpu', {}).get('percent', 0) for m in self.metrics_history if 'cpu' in m]
            memory_values = [m.get('memory', {}).get('percent', 0) for m in self.metrics_history if 'memory' in m]
            
            summary = {
                'uptime': str(datetime.now() - self.start_time),
                'latest_cpu': latest_metrics.get('cpu', {}).get('percent', 0),
                'latest_memory': latest_metrics.get('memory', {}).get('percent', 0),
                'avg_cpu': sum(cpu_values) / len(cpu_values) if cpu_values else 0,
                'avg_memory': sum(memory_values) / len(memory_values) if memory_values else 0,
                'total_requests': sum(len(times) for times in self.request_times.values()),
                'total_errors': sum(self.error_counts.values()),
                'monitored_endpoints': len(self.endpoint_metrics)
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to get metrics summary: {e}")
            return {'error': str(e)}
    
    def get_slow_endpoints(self, threshold_ms: int = 1000) -> Dict:
        """获取慢速端点数据"""
        try:
            slow_endpoints = []
            threshold_seconds = threshold_ms / 1000.0
            
            for endpoint, metrics in self.endpoint_metrics.items():
                if not metrics:
                    continue
                    
                # 计算平均响应时间
                durations = [m['duration'] for m in metrics]
                avg_duration = sum(durations) / len(durations)
                max_duration = max(durations)
                
                if avg_duration >= threshold_seconds:
                    slow_endpoints.append({
                        'endpoint': endpoint,
                        'avg_duration_ms': round(avg_duration * 1000, 2),
                        'max_duration_ms': round(max_duration * 1000, 2),
                        'request_count': len(metrics),
                        'slow_percentage': round(len([d for d in durations if d >= threshold_seconds]) / len(durations) * 100, 2)
                    })
            
            # 按平均响应时间排序
            slow_endpoints.sort(key=lambda x: x['avg_duration_ms'], reverse=True)
            
            return {
                'slow_endpoints': slow_endpoints,
                'threshold_ms': threshold_ms,
                'total_endpoints': len(self.endpoint_metrics)
            }
            
        except Exception as e:
            logger.error(f"Failed to get slow endpoints: {e}")
            return {'error': str(e)}

def monitor():
    """创建并返回性能监控器实例"""
    return PerformanceMonitor()

# 创建全局监控器实例
_global_monitor = None

def get_monitor():
    """获取全局监控器实例"""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = PerformanceMonitor()
    return _global_monitor

# 装饰器：用于自动监控函数性能
def monitor_performance(endpoint_name: str = None):
    """性能监控装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            monitor_instance = get_monitor()
            name = endpoint_name or f"{func.__module__}.{func.__name__}"
            
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                monitor_instance.record_request(name, duration, 200)
                return result
            except Exception as e:
                duration = time.time() - start_time
                monitor_instance.record_request(name, duration, 500)
                raise
        return wrapper
    return decorator

# 导出
__all__ = ['PerformanceMonitor', 'monitor', 'get_monitor', 'monitor_performance']