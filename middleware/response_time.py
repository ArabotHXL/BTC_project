"""
响应时间中间件 - Response Time Middleware
Request/Response Timing and Performance Monitoring

功能：
- 请求响应时间追踪
- 性能指标收集
- 慢请求告警
- P95/P99延迟统计

目标：API响应时间p95 ≤250ms
"""

import time
import logging
from datetime import datetime
from functools import wraps
from collections import deque
from typing import Optional, Callable, Dict, List
from flask import request, Response, g
import numpy as np

logger = logging.getLogger(__name__)

class ResponseTimeMiddleware:
    """响应时间中间件"""
    
    def __init__(self, app=None, 
                 slow_request_threshold_ms: int = 250,
                 history_size: int = 10000):
        """
        初始化响应时间中间件
        
        Parameters:
        -----------
        app : Flask
            Flask应用实例
        slow_request_threshold_ms : int
            慢请求阈值（毫秒）
        history_size : int
            历史记录大小
        """
        self.threshold_ms = slow_request_threshold_ms
        self.history_size = history_size
        self.request_times = deque(maxlen=history_size)
        self.endpoint_stats = {}  # 按端点统计
        self.stats = {
            'total_requests': 0,
            'slow_requests': 0,
            'total_time_ms': 0.0,
            'avg_time_ms': 0.0,
            'min_time_ms': float('inf'),
            'max_time_ms': 0.0
        }
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """注册中间件到Flask应用"""
        app.before_request(self.before_request)
        app.after_request(self.after_request)
        app.teardown_request(self.teardown_request)
        logger.info(f"响应时间中间件已注册（慢请求阈值: {self.threshold_ms}ms）")
    
    def before_request(self):
        """请求开始前记录时间"""
        g.request_start_time = time.time()
        g.request_id = self._generate_request_id()
    
    def after_request(self, response: Response) -> Response:
        """请求结束后计算响应时间"""
        if not hasattr(g, 'request_start_time'):
            return response
        
        # 计算响应时间
        response_time = (time.time() - g.request_start_time) * 1000  # 毫秒
        
        # 添加响应时间头
        response.headers['X-Response-Time'] = f"{response_time:.2f}ms"
        response.headers['X-Request-ID'] = getattr(g, 'request_id', 'unknown')
        
        # 记录请求信息
        self._record_request(
            endpoint=request.endpoint or 'unknown',
            method=request.method,
            path=request.path,
            status_code=response.status_code,
            response_time_ms=response_time
        )
        
        # 检查是否为慢请求
        if response_time > self.threshold_ms:
            self._log_slow_request(
                endpoint=request.endpoint,
                method=request.method,
                path=request.path,
                response_time_ms=response_time,
                status_code=response.status_code
            )
        
        return response
    
    def teardown_request(self, exception=None):
        """请求结束清理"""
        if exception:
            logger.error(f"请求异常: {exception}")
    
    def _generate_request_id(self) -> str:
        """生成唯一请求ID"""
        import uuid
        return str(uuid.uuid4())[:8]
    
    def _record_request(self, endpoint: str, method: str, path: str, 
                       status_code: int, response_time_ms: float):
        """记录请求统计"""
        # 更新全局统计
        self.stats['total_requests'] += 1
        self.stats['total_time_ms'] += response_time_ms
        self.stats['avg_time_ms'] = self.stats['total_time_ms'] / self.stats['total_requests']
        self.stats['min_time_ms'] = min(self.stats['min_time_ms'], response_time_ms)
        self.stats['max_time_ms'] = max(self.stats['max_time_ms'], response_time_ms)
        
        if response_time_ms > self.threshold_ms:
            self.stats['slow_requests'] += 1
        
        # 记录到历史
        self.request_times.append(response_time_ms)
        
        # 更新端点统计
        if endpoint not in self.endpoint_stats:
            self.endpoint_stats[endpoint] = {
                'count': 0,
                'total_time_ms': 0.0,
                'avg_time_ms': 0.0,
                'min_time_ms': float('inf'),
                'max_time_ms': 0.0,
                'slow_count': 0,
                'times': deque(maxlen=1000)  # 每个端点保留1000条记录
            }
        
        ep_stats = self.endpoint_stats[endpoint]
        ep_stats['count'] += 1
        ep_stats['total_time_ms'] += response_time_ms
        ep_stats['avg_time_ms'] = ep_stats['total_time_ms'] / ep_stats['count']
        ep_stats['min_time_ms'] = min(ep_stats['min_time_ms'], response_time_ms)
        ep_stats['max_time_ms'] = max(ep_stats['max_time_ms'], response_time_ms)
        ep_stats['times'].append(response_time_ms)
        
        if response_time_ms > self.threshold_ms:
            ep_stats['slow_count'] += 1
    
    def _log_slow_request(self, endpoint: str, method: str, path: str, 
                         response_time_ms: float, status_code: int):
        """记录慢请求"""
        logger.warning(
            f"慢请求检测 [{method} {path}] "
            f"响应时间: {response_time_ms:.2f}ms "
            f"(阈值: {self.threshold_ms}ms) "
            f"状态码: {status_code} "
            f"端点: {endpoint}"
        )
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        # 计算百分位数
        if self.request_times:
            times_array = np.array(list(self.request_times))
            p50 = np.percentile(times_array, 50)
            p95 = np.percentile(times_array, 95)
            p99 = np.percentile(times_array, 99)
        else:
            p50 = p95 = p99 = 0
        
        slow_request_rate = (
            (self.stats['slow_requests'] / self.stats['total_requests'] * 100)
            if self.stats['total_requests'] > 0
            else 0
        )
        
        return {
            **self.stats,
            'slow_request_rate': f"{slow_request_rate:.2f}%",
            'p50_ms': round(p50, 2),
            'p95_ms': round(p95, 2),
            'p99_ms': round(p99, 2),
            'threshold_ms': self.threshold_ms,
            'p95_meets_target': p95 <= self.threshold_ms
        }
    
    def get_endpoint_statistics(self) -> Dict:
        """获取端点统计信息"""
        endpoint_stats = {}
        
        for endpoint, stats in self.endpoint_stats.items():
            if stats['times']:
                times_array = np.array(list(stats['times']))
                p95 = np.percentile(times_array, 95)
            else:
                p95 = 0
            
            slow_rate = (stats['slow_count'] / stats['count'] * 100) if stats['count'] > 0 else 0
            
            endpoint_stats[endpoint] = {
                'count': stats['count'],
                'avg_time_ms': round(stats['avg_time_ms'], 2),
                'min_time_ms': round(stats['min_time_ms'], 2),
                'max_time_ms': round(stats['max_time_ms'], 2),
                'p95_ms': round(p95, 2),
                'slow_count': stats['slow_count'],
                'slow_rate': f"{slow_rate:.2f}%",
                'meets_target': p95 <= self.threshold_ms
            }
        
        # 按p95排序
        sorted_stats = sorted(
            endpoint_stats.items(),
            key=lambda x: x[1]['p95_ms'],
            reverse=True
        )
        
        return dict(sorted_stats)
    
    def export_metrics(self) -> Dict:
        """
        导出Prometheus指标
        Export metrics for Prometheus
        """
        stats = self.get_statistics()
        
        return {
            'http_request_duration_seconds': {
                'p50': stats['p50_ms'] / 1000,
                'p95': stats['p95_ms'] / 1000,
                'p99': stats['p99_ms'] / 1000,
                'avg': stats['avg_time_ms'] / 1000,
                'min': stats['min_time_ms'] / 1000,
                'max': stats['max_time_ms'] / 1000
            },
            'http_requests_total': stats['total_requests'],
            'http_slow_requests_total': stats['slow_requests'],
            'http_slow_request_rate': float(stats['slow_request_rate'].rstrip('%'))
        }
    
    def reset_statistics(self):
        """重置统计数据"""
        self.request_times.clear()
        self.endpoint_stats.clear()
        self.stats = {
            'total_requests': 0,
            'slow_requests': 0,
            'total_time_ms': 0.0,
            'avg_time_ms': 0.0,
            'min_time_ms': float('inf'),
            'max_time_ms': 0.0
        }
        logger.info("响应时间统计已重置")


# ============================================================================
# 装饰器：响应时间监控
# Decorator: Response Time Monitoring
# ============================================================================

def monitor_response_time(threshold_ms: int = 250):
    """
    响应时间监控装饰器
    
    Parameters:
    -----------
    threshold_ms : int
        慢请求阈值（毫秒）
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                
                response_time = (time.time() - start_time) * 1000
                
                if response_time > threshold_ms:
                    logger.warning(
                        f"慢函数 [{func.__name__}]: {response_time:.2f}ms "
                        f"(阈值: {threshold_ms}ms)"
                    )
                else:
                    logger.debug(
                        f"函数 [{func.__name__}]: {response_time:.2f}ms"
                    )
                
                return result
            
            except Exception as e:
                response_time = (time.time() - start_time) * 1000
                logger.error(
                    f"函数异常 [{func.__name__}]: {response_time:.2f}ms, "
                    f"错误: {e}"
                )
                raise
        
        return wrapper
    return decorator


# ============================================================================
# 性能分析工具
# Performance Analysis Tools
# ============================================================================

class PerformanceAnalyzer:
    """性能分析器"""
    
    @staticmethod
    def analyze_slow_endpoints(middleware: ResponseTimeMiddleware, 
                               top_n: int = 10) -> List[Dict]:
        """
        分析最慢的端点
        
        Parameters:
        -----------
        middleware : ResponseTimeMiddleware
            中间件实例
        top_n : int
            返回前N个最慢端点
            
        Returns:
        --------
        List[Dict] : 最慢端点列表
        """
        endpoint_stats = middleware.get_endpoint_statistics()
        
        # 按p95排序并取前N个
        slowest = sorted(
            endpoint_stats.items(),
            key=lambda x: x[1]['p95_ms'],
            reverse=True
        )[:top_n]
        
        return [
            {
                'endpoint': endpoint,
                **stats,
                'optimization_priority': 'High' if stats['p95_ms'] > 500 else 'Medium' if stats['p95_ms'] > 250 else 'Low'
            }
            for endpoint, stats in slowest
        ]
    
    @staticmethod
    def generate_performance_report(middleware: ResponseTimeMiddleware, 
                                   output_file: str = 'performance_report.json') -> Dict:
        """
        生成性能报告
        
        Parameters:
        -----------
        middleware : ResponseTimeMiddleware
            中间件实例
        output_file : str
            输出文件路径
            
        Returns:
        --------
        Dict : 性能报告
        """
        import json
        
        report = {
            'generated_at': datetime.now().isoformat(),
            'global_statistics': middleware.get_statistics(),
            'endpoint_statistics': middleware.get_endpoint_statistics(),
            'slowest_endpoints': PerformanceAnalyzer.analyze_slow_endpoints(middleware, top_n=10),
            'recommendations': []
        }
        
        # 生成优化建议
        stats = middleware.get_statistics()
        if stats['p95_ms'] > 250:
            report['recommendations'].append({
                'issue': 'P95延迟超过目标',
                'current': f"{stats['p95_ms']:.2f}ms",
                'target': '≤250ms',
                'severity': 'High',
                'suggestions': [
                    '启用响应压缩',
                    '优化数据库查询',
                    '实现缓存策略',
                    '使用异步处理'
                ]
            })
        
        # 保存报告
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"✓ 性能报告已保存到: {output_file}")
        
        return report


# ============================================================================
# 示例使用
# Usage Example
# ============================================================================

if __name__ == '__main__':
    from flask import Flask, jsonify
    import time
    
    app = Flask(__name__)
    
    # 注册响应时间中间件
    response_time = ResponseTimeMiddleware(
        app,
        slow_request_threshold_ms=100
    )
    
    @app.route('/api/fast')
    def fast_endpoint():
        """快速端点"""
        return jsonify({'message': 'This is fast'})
    
    @app.route('/api/slow')
    @monitor_response_time(threshold_ms=50)
    def slow_endpoint():
        """慢速端点（模拟）"""
        time.sleep(0.2)  # 模拟200ms延迟
        return jsonify({'message': 'This is slow'})
    
    @app.route('/api/stats')
    def statistics():
        """获取统计信息"""
        stats = response_time.get_statistics()
        endpoint_stats = response_time.get_endpoint_statistics()
        
        return jsonify({
            'global': stats,
            'endpoints': endpoint_stats
        })
    
    @app.route('/api/report')
    def performance_report():
        """生成性能报告"""
        report = PerformanceAnalyzer.generate_performance_report(response_time)
        return jsonify(report)
    
    print("响应时间中间件测试服务器已启动")
    print("访问 http://localhost:5000/api/fast 测试快速端点")
    print("访问 http://localhost:5000/api/slow 测试慢速端点")
    print("访问 http://localhost:5000/api/stats 查看统计信息")
    print("访问 http://localhost:5000/api/report 生成性能报告")
    
    app.run(debug=True)
