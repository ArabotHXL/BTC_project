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

# 导出
__all__ = ['PerformanceMonitor', 'monitor', 'get_monitor']
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
            
            # 网络指标
            network = psutil.net_io_counters()
            
            # 进程指标
            process = psutil.Process()
            process_memory = process.memory_info()
            
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
                    'percent': disk.percent
                },
                'network': {
                    'bytes_sent': network.bytes_sent,
                    'bytes_recv': network.bytes_recv,
                    'packets_sent': network.packets_sent,
                    'packets_recv': network.packets_recv
                },
                'process': {
                    'memory_rss': process_memory.rss,
                    'memory_vms': process_memory.vms,
                    'cpu_percent': process.cpu_percent()
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
        """清理过期的指标数据"""
        cutoff_time = datetime.now() - timedelta(hours=1)
        
        for endpoint in list(self.request_times.keys()):
            times = self.request_times[endpoint]
            while times and times[0]['timestamp'] < cutoff_time:
                times.popleft()
    
    def record_request(self, endpoint: str, duration: float, status_code: int = 200):
        """记录请求性能"""
        try:
            timestamp = datetime.now()
            
            # 记录请求时间
            self.request_times[endpoint].append({
                'timestamp': timestamp,
                'duration': duration,
                'status_code': status_code
            })
            
            # 限制历史记录数量
            if len(self.request_times[endpoint]) > 1000:
                self.request_times[endpoint].popleft()
            
            # 记录错误
            if status_code >= 400:
                self.error_counts[endpoint] += 1
            
        except Exception as e:
            logger.error(f"Failed to record request: {e}")
    
    def get_endpoint_stats(self, endpoint: str) -> Dict:
        """获取端点统计"""
        try:
            times = list(self.request_times.get(endpoint, []))
            if not times:
                return {
                    'endpoint': endpoint,
                    'total_requests': 0,
                    'error_count': self.error_counts.get(endpoint, 0)
                }
            
            durations = [t['duration'] for t in times]
            recent_times = [t for t in times if t['timestamp'] > datetime.now() - timedelta(minutes=5)]
            
            return {
                'endpoint': endpoint,
                'total_requests': len(times),
                'error_count': self.error_counts.get(endpoint, 0),
                'avg_response_time': sum(durations) / len(durations),
                'min_response_time': min(durations),
                'max_response_time': max(durations),
                'recent_requests_5min': len(recent_times),
                'last_request': times[-1]['timestamp'].isoformat() if times else None
            }
            
        except Exception as e:
            logger.error(f"Failed to get endpoint stats: {e}")
            return {'endpoint': endpoint, 'error': str(e)}
    
    def get_system_summary(self) -> Dict:
        """获取系统摘要"""
        try:
            if not self.metrics_history:
                return {'error': 'No metrics available'}
            
            latest = self.metrics_history[-1]
            uptime = datetime.now() - self.start_time
            
            # 计算平均CPU和内存使用率
            recent_metrics = list(self.metrics_history)[-10:]  # 最近10个数据点
            avg_cpu = sum(m.get('cpu', {}).get('percent', 0) for m in recent_metrics) / len(recent_metrics)
            avg_memory = sum(m.get('memory', {}).get('percent', 0) for m in recent_metrics) / len(recent_metrics)
            
            return {
                'uptime_seconds': uptime.total_seconds(),
                'uptime_formatted': str(uptime),
                'current_cpu_percent': latest.get('cpu', {}).get('percent', 0),
                'current_memory_percent': latest.get('memory', {}).get('percent', 0),
                'avg_cpu_percent': avg_cpu,
                'avg_memory_percent': avg_memory,
                'total_memory_gb': latest.get('memory', {}).get('total', 0) / (1024**3),
                'available_memory_gb': latest.get('memory', {}).get('available', 0) / (1024**3),
                'disk_usage_percent': latest.get('disk', {}).get('percent', 0),
                'total_endpoints': len(self.request_times),
                'total_requests': sum(len(times) for times in self.request_times.values()),
                'total_errors': sum(self.error_counts.values()),
                'timestamp': latest.get('timestamp')
            }
            
        except Exception as e:
            logger.error(f"Failed to get system summary: {e}")
            return {'error': str(e)}
    
    def get_performance_report(self) -> Dict:
        """获取性能报告"""
        try:
            system_summary = self.get_system_summary()
            
            # 获取所有端点统计
            endpoint_stats = {}
            for endpoint in self.request_times.keys():
                endpoint_stats[endpoint] = self.get_endpoint_stats(endpoint)
            
            # 计算总体统计
            all_durations = []
            for times in self.request_times.values():
                all_durations.extend([t['duration'] for t in times])
            
            overall_stats = {}
            if all_durations:
                overall_stats = {
                    'total_requests': len(all_durations),
                    'avg_response_time': sum(all_durations) / len(all_durations),
                    'min_response_time': min(all_durations),
                    'max_response_time': max(all_durations),
                    'p95_response_time': sorted(all_durations)[int(len(all_durations) * 0.95)] if all_durations else 0,
                    'p99_response_time': sorted(all_durations)[int(len(all_durations) * 0.99)] if all_durations else 0
                }
            
            return {
                'system': system_summary,
                'endpoints': endpoint_stats,
                'overall': overall_stats,
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to generate performance report: {e}")
            return {'error': str(e)}
    
    def export_metrics(self, filepath: str) -> bool:
        """导出指标数据"""
        try:
            report = self.get_performance_report()
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Performance metrics exported to {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export metrics: {e}")
            return False

# 装饰器用于自动记录请求性能
def monitor_performance(endpoint_name: str = None):
    """性能监控装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            endpoint = endpoint_name or func.__name__
            status_code = 200
            
            try:
                result = func(*args, **kwargs)
                
                # 尝试从Flask响应中获取状态码
                if hasattr(result, 'status_code'):
                    status_code = result.status_code
                
                return result
                
            except Exception as e:
                status_code = 500
                raise
            finally:
                duration = time.time() - start_time
                if 'performance_monitor' in globals():
                    performance_monitor.record_request(endpoint, duration, status_code)
        
        return wrapper
    return decorator

# 全局性能监控实例
performance_monitor = PerformanceMonitor()

def start_performance_monitoring(interval: float = 30.0):
    """启动性能监控"""
    performance_monitor.start_monitoring(interval)

def stop_performance_monitoring():
    """停止性能监控"""
    performance_monitor.stop_monitoring()

def get_performance_summary() -> Dict:
    """获取性能摘要"""
    return performance_monitor.get_system_summary()

# 兼容性导出
__all__ = [
    'PerformanceMonitor', 
    'performance_monitor', 
    'monitor_performance',
    'start_performance_monitoring',
    'stop_performance_monitoring',
    'get_performance_summary'
]