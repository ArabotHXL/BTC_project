#!/usr/bin/env python3
"""
Prometheus Metrics Exporter
Prometheus指标导出器

导出应用性能指标供Prometheus抓取
Export application performance metrics for Prometheus scraping

指标类型：
- 请求延迟 (request_latency_seconds)
- 请求计数 (request_count_total)  
- 错误率 (error_rate)
- 缓存命中率 (cache_hit_rate)
- 数据库查询时间 (db_query_duration_seconds)
- SLO合规性 (slo_compliance)
"""

import time
import logging
from typing import Dict, List, Optional
from collections import defaultdict
from datetime import datetime
import threading

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PrometheusMetrics:
    """Prometheus指标收集器"""
    
    def __init__(self):
        """初始化指标收集器"""
        self._metrics = {
            # Counter metrics (累计值)
            'request_count_total': defaultdict(int),
            'error_count_total': defaultdict(int),
            'cache_hits_total': 0,
            'cache_misses_total': 0,
            'db_queries_total': 0,
            
            # Histogram metrics (分布统计)
            'request_latency_seconds': defaultdict(list),
            'db_query_duration_seconds': defaultdict(list),
            
            # Gauge metrics (当前值)
            'active_requests': 0,
            'cache_hit_rate': 0.0,
            'error_rate': 0.0,
            'slo_compliance': 100.0,
        }
        
        self._lock = threading.Lock()
        logger.info("✅ Prometheus指标收集器已初始化")
    
    def record_request(self, endpoint: str, method: str, status_code: int, 
                      duration_seconds: float):
        """
        记录HTTP请求
        
        Parameters:
        -----------
        endpoint : str
            请求端点
        method : str
            HTTP方法
        status_code : int
            响应状态码
        duration_seconds : float
            请求耗时（秒）
        """
        with self._lock:
            # 记录请求计数
            key = f'{method}_{endpoint}_{status_code}'
            self._metrics['request_count_total'][key] += 1
            
            # 记录延迟
            latency_key = f'{method}_{endpoint}'
            self._metrics['request_latency_seconds'][latency_key].append(duration_seconds)
            
            # 记录错误
            if status_code >= 400:
                error_key = f'{method}_{endpoint}'
                self._metrics['error_count_total'][error_key] += 1
    
    def record_cache_hit(self):
        """记录缓存命中"""
        with self._lock:
            self._metrics['cache_hits_total'] += 1
            self._update_cache_hit_rate()
    
    def record_cache_miss(self):
        """记录缓存未命中"""
        with self._lock:
            self._metrics['cache_misses_total'] += 1
            self._update_cache_hit_rate()
    
    def record_db_query(self, query_type: str, duration_seconds: float):
        """
        记录数据库查询
        
        Parameters:
        -----------
        query_type : str
            查询类型 (select, insert, update, delete)
        duration_seconds : float
            查询耗时（秒）
        """
        with self._lock:
            self._metrics['db_queries_total'] += 1
            self._metrics['db_query_duration_seconds'][query_type].append(duration_seconds)
    
    def update_active_requests(self, count: int):
        """更新活跃请求数"""
        with self._lock:
            self._metrics['active_requests'] = count
    
    def update_slo_compliance(self, compliance_percentage: float):
        """更新SLO合规百分比"""
        with self._lock:
            self._metrics['slo_compliance'] = compliance_percentage
    
    def _update_cache_hit_rate(self):
        """更新缓存命中率"""
        hits = self._metrics['cache_hits_total']
        misses = self._metrics['cache_misses_total']
        total = hits + misses
        
        if total > 0:
            self._metrics['cache_hit_rate'] = (hits / total) * 100
    
    def _calculate_percentile(self, values: List[float], percentile: int) -> float:
        """计算百分位数"""
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        index = int(len(sorted_values) * (percentile / 100.0))
        index = min(index, len(sorted_values) - 1)
        return sorted_values[index]
    
    def export_metrics(self) -> str:
        """
        导出Prometheus格式的指标
        
        Returns:
        --------
        str : Prometheus格式的指标文本
        """
        with self._lock:
            lines = []
            
            # Header
            lines.append("# HashInsight Prometheus Metrics")
            lines.append(f"# Generated at {datetime.utcnow().isoformat()}Z")
            lines.append("")
            
            # Request count metrics
            lines.append("# HELP request_count_total Total number of HTTP requests")
            lines.append("# TYPE request_count_total counter")
            for key, count in self._metrics['request_count_total'].items():
                parts = key.split('_', 2)
                if len(parts) == 3:
                    method, endpoint, status = parts
                    lines.append(
                        f'request_count_total{{method="{method}",endpoint="{endpoint}",status="{status}"}} {count}'
                    )
            lines.append("")
            
            # Error count metrics
            lines.append("# HELP error_count_total Total number of errors")
            lines.append("# TYPE error_count_total counter")
            for key, count in self._metrics['error_count_total'].items():
                parts = key.split('_', 1)
                if len(parts) == 2:
                    method, endpoint = parts
                    lines.append(
                        f'error_count_total{{method="{method}",endpoint="{endpoint}"}} {count}'
                    )
            lines.append("")
            
            # Request latency metrics (histogram)
            lines.append("# HELP request_latency_seconds HTTP request latency in seconds")
            lines.append("# TYPE request_latency_seconds histogram")
            for key, values in self._metrics['request_latency_seconds'].items():
                if values:
                    parts = key.split('_', 1)
                    if len(parts) == 2:
                        method, endpoint = parts
                        p50 = self._calculate_percentile(values, 50)
                        p95 = self._calculate_percentile(values, 95)
                        p99 = self._calculate_percentile(values, 99)
                        
                        lines.append(
                            f'request_latency_seconds{{method="{method}",endpoint="{endpoint}",quantile="0.5"}} {p50:.4f}'
                        )
                        lines.append(
                            f'request_latency_seconds{{method="{method}",endpoint="{endpoint}",quantile="0.95"}} {p95:.4f}'
                        )
                        lines.append(
                            f'request_latency_seconds{{method="{method}",endpoint="{endpoint}",quantile="0.99"}} {p99:.4f}'
                        )
            lines.append("")
            
            # Cache metrics
            lines.append("# HELP cache_hits_total Total number of cache hits")
            lines.append("# TYPE cache_hits_total counter")
            lines.append(f'cache_hits_total {self._metrics["cache_hits_total"]}')
            lines.append("")
            
            lines.append("# HELP cache_misses_total Total number of cache misses")
            lines.append("# TYPE cache_misses_total counter")
            lines.append(f'cache_misses_total {self._metrics["cache_misses_total"]}')
            lines.append("")
            
            lines.append("# HELP cache_hit_rate Cache hit rate percentage")
            lines.append("# TYPE cache_hit_rate gauge")
            lines.append(f'cache_hit_rate {self._metrics["cache_hit_rate"]:.2f}')
            lines.append("")
            
            # Database metrics
            lines.append("# HELP db_queries_total Total number of database queries")
            lines.append("# TYPE db_queries_total counter")
            lines.append(f'db_queries_total {self._metrics["db_queries_total"]}')
            lines.append("")
            
            lines.append("# HELP db_query_duration_seconds Database query duration in seconds")
            lines.append("# TYPE db_query_duration_seconds histogram")
            for query_type, values in self._metrics['db_query_duration_seconds'].items():
                if values:
                    p50 = self._calculate_percentile(values, 50)
                    p95 = self._calculate_percentile(values, 95)
                    p99 = self._calculate_percentile(values, 99)
                    
                    lines.append(
                        f'db_query_duration_seconds{{query_type="{query_type}",quantile="0.5"}} {p50:.4f}'
                    )
                    lines.append(
                        f'db_query_duration_seconds{{query_type="{query_type}",quantile="0.95"}} {p95:.4f}'
                    )
                    lines.append(
                        f'db_query_duration_seconds{{query_type="{query_type}",quantile="0.99"}} {p99:.4f}'
                    )
            lines.append("")
            
            # Active requests
            lines.append("# HELP active_requests Number of active HTTP requests")
            lines.append("# TYPE active_requests gauge")
            lines.append(f'active_requests {self._metrics["active_requests"]}')
            lines.append("")
            
            # SLO compliance
            lines.append("# HELP slo_compliance SLO compliance percentage")
            lines.append("# TYPE slo_compliance gauge")
            lines.append(f'slo_compliance {self._metrics["slo_compliance"]:.2f}')
            lines.append("")
            
            # Error rate
            total_requests = sum(self._metrics['request_count_total'].values())
            total_errors = sum(self._metrics['error_count_total'].values())
            error_rate = (total_errors / total_requests * 100) if total_requests > 0 else 0.0
            
            lines.append("# HELP error_rate Error rate percentage")
            lines.append("# TYPE error_rate gauge")
            lines.append(f'error_rate {error_rate:.2f}')
            lines.append("")
            
            return '\n'.join(lines)
    
    def get_summary(self) -> Dict:
        """获取指标摘要"""
        with self._lock:
            total_requests = sum(self._metrics['request_count_total'].values())
            total_errors = sum(self._metrics['error_count_total'].values())
            
            return {
                'total_requests': total_requests,
                'total_errors': total_errors,
                'error_rate': (total_errors / total_requests * 100) if total_requests > 0 else 0.0,
                'cache_hit_rate': self._metrics['cache_hit_rate'],
                'total_db_queries': self._metrics['db_queries_total'],
                'active_requests': self._metrics['active_requests'],
                'slo_compliance': self._metrics['slo_compliance']
            }


# 全局指标收集器实例
metrics_collector = PrometheusMetrics()


def metrics_middleware(app):
    """
    Flask中间件：自动收集请求指标
    
    Parameters:
    -----------
    app : Flask
        Flask应用实例
    """
    @app.before_request
    def before_request():
        """请求前钩子"""
        import flask
        flask.g.start_time = time.time()
        metrics_collector.update_active_requests(
            metrics_collector._metrics['active_requests'] + 1
        )
    
    @app.after_request
    def after_request(response):
        """请求后钩子"""
        import flask
        
        if hasattr(flask.g, 'start_time'):
            duration = time.time() - flask.g.start_time
            
            metrics_collector.record_request(
                endpoint=flask.request.endpoint or 'unknown',
                method=flask.request.method,
                status_code=response.status_code,
                duration_seconds=duration
            )
            
            metrics_collector.update_active_requests(
                metrics_collector._metrics['active_requests'] - 1
            )
        
        return response
    
    logger.info("✅ Prometheus指标中间件已启用")


def register_metrics_endpoint(app, endpoint='/metrics'):
    """
    注册Prometheus指标端点
    
    Parameters:
    -----------
    app : Flask
        Flask应用实例
    endpoint : str
        指标端点路径
    """
    @app.route(endpoint)
    def prometheus_metrics():
        """Prometheus指标端点"""
        from flask import Response
        metrics_text = metrics_collector.export_metrics()
        return Response(metrics_text, mimetype='text/plain')
    
    logger.info(f"✅ Prometheus指标端点已注册: {endpoint}")


if __name__ == '__main__':
    # 测试指标导出
    collector = PrometheusMetrics()
    
    # 模拟一些请求
    collector.record_request('/api/calculate', 'POST', 200, 0.123)
    collector.record_request('/api/calculate', 'POST', 200, 0.145)
    collector.record_request('/api/calculate', 'POST', 500, 0.234)
    collector.record_request('/health', 'GET', 200, 0.005)
    
    # 模拟缓存
    collector.record_cache_hit()
    collector.record_cache_hit()
    collector.record_cache_miss()
    
    # 模拟数据库查询
    collector.record_db_query('select', 0.023)
    collector.record_db_query('insert', 0.045)
    
    # 导出指标
    print(collector.export_metrics())
    print("\n" + "="*60)
    print("Summary:", collector.get_summary())
