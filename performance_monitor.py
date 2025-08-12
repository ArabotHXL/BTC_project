"""
性能监控工具 - 跟踪系统性能指标
"""
import time
import logging
import psutil
from functools import wraps
from typing import Callable, Dict, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self):
        self._metrics = {
            'requests': [],
            'database_queries': [],
            'api_calls': [],
            'errors': []
        }
        self._start_time = time.time()
    
    def track_request(self, endpoint: str, duration: float, status_code: int):
        """跟踪请求性能"""
        self._metrics['requests'].append({
            'endpoint': endpoint,
            'duration': duration,
            'status_code': status_code,
            'timestamp': datetime.now()
        })
        
        # 保留最近1000条记录
        if len(self._metrics['requests']) > 1000:
            self._metrics['requests'] = self._metrics['requests'][-1000:]
    
    def track_database_query(self, query_type: str, duration: float):
        """跟踪数据库查询性能"""
        self._metrics['database_queries'].append({
            'type': query_type,
            'duration': duration,
            'timestamp': datetime.now()
        })
        
        if len(self._metrics['database_queries']) > 500:
            self._metrics['database_queries'] = self._metrics['database_queries'][-500:]
    
    def track_api_call(self, api_name: str, duration: float, success: bool):
        """跟踪外部API调用"""
        self._metrics['api_calls'].append({
            'api': api_name,
            'duration': duration,
            'success': success,
            'timestamp': datetime.now()
        })
        
        if len(self._metrics['api_calls']) > 500:
            self._metrics['api_calls'] = self._metrics['api_calls'][-500:]
    
    def track_error(self, error_type: str, message: str):
        """跟踪错误"""
        self._metrics['errors'].append({
            'type': error_type,
            'message': message,
            'timestamp': datetime.now()
        })
        
        if len(self._metrics['errors']) > 100:
            self._metrics['errors'] = self._metrics['errors'][-100:]
    
    def get_system_stats(self) -> Dict:
        """获取系统状态"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_used_mb': memory.used / 1024 / 1024,
                'memory_total_mb': memory.total / 1024 / 1024,
                'disk_percent': disk.percent,
                'disk_used_gb': disk.used / 1024 / 1024 / 1024,
                'disk_total_gb': disk.total / 1024 / 1024 / 1024,
                'uptime_hours': (time.time() - self._start_time) / 3600
            }
        except Exception as e:
            logger.error(f"Failed to get system stats: {e}")
            return {}
    
    def get_performance_summary(self) -> Dict:
        """获取性能摘要"""
        now = datetime.now()
        one_hour_ago = now - timedelta(hours=1)
        
        # 计算最近1小时的指标
        recent_requests = [
            r for r in self._metrics['requests']
            if r['timestamp'] > one_hour_ago
        ]
        
        recent_queries = [
            q for q in self._metrics['database_queries']
            if q['timestamp'] > one_hour_ago
        ]
        
        recent_api_calls = [
            a for a in self._metrics['api_calls']
            if a['timestamp'] > one_hour_ago
        ]
        
        # 计算平均响应时间
        avg_request_time = (
            sum(r['duration'] for r in recent_requests) / len(recent_requests)
            if recent_requests else 0
        )
        
        avg_query_time = (
            sum(q['duration'] for q in recent_queries) / len(recent_queries)
            if recent_queries else 0
        )
        
        # 计算成功率
        successful_api_calls = sum(1 for a in recent_api_calls if a['success'])
        api_success_rate = (
            (successful_api_calls / len(recent_api_calls) * 100)
            if recent_api_calls else 100
        )
        
        # 错误统计
        recent_errors = [
            e for e in self._metrics['errors']
            if e['timestamp'] > one_hour_ago
        ]
        
        return {
            'requests_per_hour': len(recent_requests),
            'avg_request_time_ms': avg_request_time * 1000,
            'database_queries_per_hour': len(recent_queries),
            'avg_query_time_ms': avg_query_time * 1000,
            'api_calls_per_hour': len(recent_api_calls),
            'api_success_rate': f"{api_success_rate:.1f}%",
            'errors_per_hour': len(recent_errors),
            'system_stats': self.get_system_stats()
        }
    
    def get_slow_endpoints(self, threshold_ms: float = 1000) -> List[Dict]:
        """获取慢速端点"""
        slow_requests = [
            r for r in self._metrics['requests']
            if r['duration'] * 1000 > threshold_ms
        ]
        
        # 按端点分组统计
        endpoint_stats = {}
        for req in slow_requests:
            endpoint = req['endpoint']
            if endpoint not in endpoint_stats:
                endpoint_stats[endpoint] = {
                    'count': 0,
                    'total_time': 0,
                    'max_time': 0
                }
            
            endpoint_stats[endpoint]['count'] += 1
            endpoint_stats[endpoint]['total_time'] += req['duration']
            endpoint_stats[endpoint]['max_time'] = max(
                endpoint_stats[endpoint]['max_time'],
                req['duration']
            )
        
        # 转换为列表并排序
        results = []
        for endpoint, stats in endpoint_stats.items():
            results.append({
                'endpoint': endpoint,
                'slow_requests': stats['count'],
                'avg_time_ms': (stats['total_time'] / stats['count']) * 1000,
                'max_time_ms': stats['max_time'] * 1000
            })
        
        return sorted(results, key=lambda x: x['max_time_ms'], reverse=True)[:10]

# 全局性能监控实例
monitor = PerformanceMonitor()

def measure_performance(metric_type: str = 'request'):
    """性能测量装饰器"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                # 记录性能指标
                if metric_type == 'request':
                    endpoint = func.__name__
                    status_code = 200
                    monitor.track_request(endpoint, duration, status_code)
                elif metric_type == 'database':
                    monitor.track_database_query(func.__name__, duration)
                elif metric_type == 'api':
                    monitor.track_api_call(func.__name__, duration, True)
                
                # 记录慢速操作
                if duration > 1.0:  # 超过1秒
                    logger.warning(
                        f"Slow {metric_type}: {func.__name__} took {duration:.2f}s"
                    )
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                
                # 记录错误
                monitor.track_error(type(e).__name__, str(e))
                
                if metric_type == 'api':
                    monitor.track_api_call(func.__name__, duration, False)
                
                raise
        
        return wrapper
    return decorator