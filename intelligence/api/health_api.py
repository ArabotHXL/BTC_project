"""
Intelligence Layer - Health Check API
======================================

Flask blueprint for system health monitoring endpoints.

Endpoints:
- GET /api/intelligence/health - System health check with metrics
"""

import logging
from datetime import datetime, timedelta
from flask import Blueprint, jsonify
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from db import db
from common.rbac import require_permission, Permission
from intelligence.monitoring.slo_tracker import slo_metrics

logger = logging.getLogger(__name__)

health_bp = Blueprint('health_api', __name__, url_prefix='/api/intelligence')


@health_bp.route('/health', methods=['GET'])
def intelligence_health_check():
    """
    Intelligence layer system health check
    
    Returns:
        JSON with health status including:
        - Database connection status
        - Redis connection status
        - Outbox backlog count (pending/retrying events)
        - Event failure count (last 24h)
        - Forecast latency
        - Optimization runtime metrics
    """
    try:
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'services': {},
            'metrics': {}
        }
        
        try:
            db.session.execute(text('SELECT 1'))
            db.session.commit()
            health_status['services']['database'] = {
                'status': 'connected',
                'type': 'postgresql'
            }
        except SQLAlchemyError as e:
            logger.error(f"Database health check failed: {str(e)}")
            health_status['services']['database'] = {
                'status': 'disconnected',
                'error': str(e)
            }
            health_status['status'] = 'degraded'
        
        redis_status = check_redis_connection()
        health_status['services']['redis'] = redis_status
        if redis_status['status'] != 'connected':
            health_status['status'] = 'degraded'
        
        try:
            outbox_query = text("""
                SELECT COUNT(*) as backlog
                FROM event_outbox
                WHERE status IN ('PENDING', 'RETRYING')
                AND created_at > :cutoff_time
            """)
            
            cutoff_time = datetime.utcnow() - timedelta(hours=24)
            result = db.session.execute(outbox_query, {'cutoff_time': cutoff_time}).fetchone()
            
            if result:
                health_status['metrics']['outbox_backlog'] = result[0]
            else:
                health_status['metrics']['outbox_backlog'] = 0
                
        except SQLAlchemyError as e:
            logger.warning(f"Unable to query outbox backlog: {str(e)}")
            health_status['metrics']['outbox_backlog'] = None
        
        try:
            event_failures_query = text("""
                SELECT COUNT(*) as failures
                FROM event_failures
                WHERE first_failed_at > :cutoff_time
            """)
            
            cutoff_time = datetime.utcnow() - timedelta(hours=24)
            result = db.session.execute(event_failures_query, {'cutoff_time': cutoff_time}).fetchone()
            
            if result:
                health_status['metrics']['event_failures_24h'] = result[0]
                if result[0] > 10:
                    health_status['status'] = 'degraded'
            else:
                health_status['metrics']['event_failures_24h'] = 0
                
        except SQLAlchemyError as e:
            logger.warning(f"Unable to query event failures: {str(e)}")
            health_status['metrics']['event_failures_24h'] = None
        
        # DLQ (Dead Letter Queue) count - 累积的未恢复死信总数
        try:
            dlq_query = text("""
                SELECT COUNT(*) as dlq_count
                FROM event_failures
                WHERE is_resolved = FALSE
            """)
            
            result = db.session.execute(dlq_query).fetchone()
            
            if result:
                dlq_count = result[0]
                health_status['metrics']['dlq_count'] = dlq_count
                # DLQ超过50条认为系统有问题
                if dlq_count > 50:
                    health_status['status'] = 'degraded'
                    logger.warning(f"High DLQ count detected: {dlq_count} unresolved failures")
            else:
                health_status['metrics']['dlq_count'] = 0
                
        except SQLAlchemyError as e:
            logger.warning(f"Unable to query DLQ count: {str(e)}")
            health_status['metrics']['dlq_count'] = None
        
        try:
            forecast_latency_query = text("""
                SELECT 
                    AVG(EXTRACT(EPOCH FROM (updated_at - created_at))) as avg_latency_seconds,
                    MAX(EXTRACT(EPOCH FROM (updated_at - created_at))) as max_latency_seconds
                FROM forecast_daily
                WHERE created_at > :cutoff_time
            """)
            
            cutoff_time = datetime.utcnow() - timedelta(hours=24)
            result = db.session.execute(forecast_latency_query, {'cutoff_time': cutoff_time}).fetchone()
            
            if result and result[0]:
                health_status['metrics']['forecast_latency'] = {
                    'avg_seconds': float(result[0]),
                    'max_seconds': float(result[1])
                }
            else:
                health_status['metrics']['forecast_latency'] = None
                
        except SQLAlchemyError as e:
            logger.warning(f"Unable to query forecast latency: {str(e)}")
            health_status['metrics']['forecast_latency'] = None
        
        try:
            optimization_query = text("""
                SELECT 
                    COUNT(*) as total_optimizations,
                    AVG(computation_time_ms) as avg_runtime_ms,
                    MAX(computation_time_ms) as max_runtime_ms
                FROM ops_schedule
                WHERE created_at > :cutoff_time
            """)
            
            cutoff_time = datetime.utcnow() - timedelta(hours=24)
            result = db.session.execute(optimization_query, {'cutoff_time': cutoff_time}).fetchone()
            
            if result and result[0]:
                health_status['metrics']['optimization_runtime'] = {
                    'count_24h': result[0],
                    'avg_ms': float(result[1]) if result[1] else 0,
                    'max_ms': float(result[2]) if result[2] else 0
                }
            else:
                health_status['metrics']['optimization_runtime'] = {
                    'count_24h': 0,
                    'avg_ms': 0,
                    'max_ms': 0
                }
                
        except SQLAlchemyError as e:
            logger.warning(f"Unable to query optimization runtime: {str(e)}")
            health_status['metrics']['optimization_runtime'] = None
        
        # ========== 新增监控指标 ==========
        
        # 1. 缓存命中率统计 (Cache Hit Rate)
        cache_hit_rate = get_cache_hit_rate()
        health_status['metrics']['cache_hit_rate'] = cache_hit_rate
        
        # 2. 预测数据新鲜度 (Forecast Freshness)
        forecast_freshness = get_forecast_freshness()
        health_status['metrics']['forecast_freshness'] = forecast_freshness
        if forecast_freshness and forecast_freshness.get('status') == 'stale':
            health_status['status'] = 'degraded'
        
        # 3. P95响应时间 (P95 Response Time / TTR)
        p95_response = get_p95_response_time()
        health_status['metrics']['p95_response_time'] = p95_response
        if p95_response and p95_response.get('status') == 'degraded':
            health_status['status'] = 'degraded'
        
        # 4. 重算成功率 (Recalculation Success Rate)
        success_rate = get_recalc_success_rate()
        health_status['metrics']['recalc_success_rate'] = success_rate
        if success_rate and success_rate.get('status') == 'degraded':
            health_status['status'] = 'degraded'
        
        # 5. SLO摘要 (SLO Summary from SLO Tracker)
        slo_summary = slo_metrics.get_summary()
        health_status['slo'] = {
            'p95_ttr_ms': slo_summary['p95_ttr_ms'],
            'success_rate': slo_summary['success_rate_pct'],
            'compliant': slo_summary['slo_compliance']['compliant'],
            'alerts': slo_summary['slo_compliance']['alerts']
        }
        
        status_code = 200 if health_status['status'] == 'healthy' else 503
        
        logger.info(f"Health check completed: {health_status['status']}")
        
        return jsonify(health_status), status_code
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 503


@health_bp.route('/health/slo', methods=['GET'])
def get_slo_metrics():
    """
    SLO监控端点（包含阈值配置）
    
    Returns:
        JSON with detailed SLO metrics including:
        - P95 TTR (Time To Recalculate)
        - Success rate
        - Latency distribution
        - SLO compliance status
        - Current alert thresholds
    """
    try:
        from intelligence.monitoring.alert_config import AlertThresholds
        
        summary = slo_metrics.get_summary()
        
        return jsonify({
            'success': True,
            'slo_metrics': summary,
            'alert_thresholds': {
                'p95_ttr': {
                    'warning_ms': AlertThresholds.P95_TTR_WARNING,
                    'critical_ms': AlertThresholds.P95_TTR_CRITICAL
                },
                'success_rate': {
                    'warning_pct': AlertThresholds.SUCCESS_RATE_WARNING,
                    'critical_pct': AlertThresholds.SUCCESS_RATE_CRITICAL
                },
                'cache_hit_rate': {
                    'warning_pct': AlertThresholds.CACHE_HIT_RATE_WARNING,
                    'critical_pct': AlertThresholds.CACHE_HIT_RATE_CRITICAL
                }
            },
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"SLO metrics retrieval failed: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500


def check_redis_connection():
    """
    Check Redis connection status
    
    Returns:
        dict: Redis connection status
    """
    try:
        from intelligence.cache_manager import IntelligenceCacheManager
        
        cache_manager = IntelligenceCacheManager()
        
        if cache_manager.cache:
            test_key = 'health_check_test'
            test_value = 'ok'
            
            cache_manager.cache.set(test_key, test_value, timeout=10)
            retrieved_value = cache_manager.cache.get(test_key)
            
            if retrieved_value == test_value:
                cache_manager.cache.delete(test_key)
                return {
                    'status': 'connected',
                    'type': 'redis'
                }
            else:
                return {
                    'status': 'error',
                    'type': 'redis',
                    'error': 'Value mismatch in cache test'
                }
        else:
            return {
                'status': 'unavailable',
                'type': 'redis',
                'message': 'Cache manager not initialized'
            }
            
    except ImportError as e:
        logger.warning(f"Redis cache not available: {str(e)}")
        return {
            'status': 'unavailable',
            'type': 'redis',
            'error': 'Cache module not available'
        }
    except Exception as e:
        logger.error(f"Redis health check failed: {str(e)}")
        return {
            'status': 'error',
            'type': 'redis',
            'error': str(e)
        }


def get_cache_hit_rate():
    """
    缓存命中率统计 - 从Redis获取缓存命中/未命中统计
    Cache Hit Rate - Get cache hit/miss statistics from Redis
    
    Returns:
        dict: 缓存命中率数据，格式：
            {
                "hit_rate_percent": 85.5,
                "hits": 1000,
                "misses": 150
            }
            如果无法获取统计信息，返回None
    """
    try:
        from intelligence.cache_manager import IntelligenceCacheManager
        
        cache_manager = IntelligenceCacheManager()
        
        if not cache_manager.cache:
            logger.warning("Cache not initialized, cannot get hit rate stats")
            return None
        
        # 尝试从Redis获取统计信息
        # Try to get stats from Redis INFO command
        try:
            # Flask-Caching使用redis-py，尝试访问底层Redis连接
            # 检查是否为RedisCache类型
            if hasattr(cache_manager.cache.cache, '_write_client'):
                redis_client = cache_manager.cache.cache._write_client
                info = redis_client.info('stats')
                
                keyspace_hits = info.get('keyspace_hits', 0)
                keyspace_misses = info.get('keyspace_misses', 0)
                
                total = keyspace_hits + keyspace_misses
                
                if total == 0:
                    # 没有缓存操作，返回0%命中率
                    return {
                        "hit_rate_percent": 0.0,
                        "hits": 0,
                        "misses": 0
                    }
                
                hit_rate = (keyspace_hits / total) * 100
                
                return {
                    "hit_rate_percent": round(hit_rate, 2),
                    "hits": keyspace_hits,
                    "misses": keyspace_misses
                }
            else:
                # 不是RedisCache，无法获取统计信息
                logger.warning("Cache backend does not support stats (not Redis)")
                return None
            
        except AttributeError:
            # 无法访问底层Redis客户端
            logger.warning("Cannot access Redis client for stats, cache hit rate unavailable")
            return None
        except Exception as e:
            logger.warning(f"Error getting Redis stats: {str(e)}")
            return None
            
    except ImportError:
        logger.warning("Cache manager not available")
        return None
    except Exception as e:
        logger.error(f"Error getting cache hit rate: {str(e)}")
        return None


def get_forecast_freshness():
    """
    预测数据新鲜度 - 查询最新预测记录的时间，判断数据是否新鲜
    Forecast Freshness - Check how recent the latest forecast data is
    
    Returns:
        dict: 预测数据新鲜度，格式：
            {
                "last_updated_seconds_ago": 45,
                "status": "fresh|stale"
            }
            阈值：<120s为fresh，>=120s为stale
            如果查询失败，返回None
    """
    try:
        # 查询最新的预测记录created_at时间
        forecast_query = text("""
            SELECT created_at
            FROM forecast_daily
            ORDER BY created_at DESC
            LIMIT 1
        """)
        
        result = db.session.execute(forecast_query).fetchone()
        
        if not result or not result[0]:
            logger.warning("No forecast data found in database")
            return None
        
        latest_forecast_time = result[0]
        current_time = datetime.utcnow()
        
        # 计算时间差（秒）
        time_diff = (current_time - latest_forecast_time).total_seconds()
        
        # 判断新鲜度：<120s为fresh，>=120s为stale
        status = 'fresh' if time_diff < 120 else 'stale'
        
        return {
            "last_updated_seconds_ago": int(time_diff),
            "status": status
        }
        
    except SQLAlchemyError as e:
        logger.warning(f"Unable to query forecast freshness: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Error getting forecast freshness: {str(e)}")
        return None


def get_p95_response_time():
    """
    P95响应时间（TTR - Time To Response）- 从event_outbox表计算处理时间的P95分位数
    P95 Response Time - Calculate P95 percentile of processing time from event_outbox
    
    注意：event_outbox表没有processing_time列，使用以下逻辑：
    - 如果有processing_started_at，计算 (processed_at - processing_started_at)
    - 否则使用 (processed_at - created_at)
    
    Returns:
        dict: P95响应时间数据，格式：
            {
                "p95_seconds": 3.2,
                "status": "ok|degraded"
            }
            阈值：<=5s为ok，>5s为degraded
            如果查询失败，返回None
    """
    try:
        # 计算处理时间的P95分位数
        # 只统计已完成或失败的事件（有明确结束时间的）
        p95_query = text("""
            SELECT 
                PERCENTILE_CONT(0.95) WITHIN GROUP (
                    ORDER BY 
                        CASE 
                            WHEN processing_started_at IS NOT NULL 
                            THEN EXTRACT(EPOCH FROM (processed_at - processing_started_at))
                            ELSE EXTRACT(EPOCH FROM (processed_at - created_at))
                        END
                ) as p95_seconds
            FROM event_outbox
            WHERE processed_at IS NOT NULL
                AND status IN ('COMPLETED', 'FAILED')
                AND created_at > :cutoff_time
        """)
        
        # 统计最近24小时的数据
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        result = db.session.execute(p95_query, {'cutoff_time': cutoff_time}).fetchone()
        
        if not result or result[0] is None:
            logger.warning("No completed events found for P95 calculation")
            return None
        
        p95_seconds = float(result[0])
        
        # 判断状态：<=5s为ok，>5s为degraded
        status = 'ok' if p95_seconds <= 5.0 else 'degraded'
        
        return {
            "p95_seconds": round(p95_seconds, 2),
            "status": status
        }
        
    except SQLAlchemyError as e:
        logger.warning(f"Unable to query P95 response time: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Error getting P95 response time: {str(e)}")
        return None


def get_recalc_success_rate():
    """
    重算成功率 - 统计event_outbox中COMPLETED vs FAILED的比率
    Recalculation Success Rate - Calculate success rate from event_outbox
    
    Returns:
        dict: 重算成功率数据，格式：
            {
                "success_rate_percent": 99.95,
                "total": 10000,
                "failed": 5,
                "status": "ok|degraded"
            }
            阈值：>=99.9%为ok，<99.9%为degraded
            如果查询失败，返回None
    """
    try:
        # 统计最近24小时的成功和失败事件
        success_rate_query = text("""
            SELECT 
                COUNT(*) FILTER (WHERE status = 'COMPLETED') as completed,
                COUNT(*) FILTER (WHERE status = 'FAILED') as failed,
                COUNT(*) as total
            FROM event_outbox
            WHERE status IN ('COMPLETED', 'FAILED')
                AND created_at > :cutoff_time
        """)
        
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        result = db.session.execute(success_rate_query, {'cutoff_time': cutoff_time}).fetchone()
        
        if not result or result[2] == 0:
            logger.warning("No completed/failed events found for success rate calculation")
            return None
        
        completed = result[0] or 0
        failed = result[1] or 0
        total = result[2]
        
        # 计算成功率
        success_rate = (completed / total * 100) if total > 0 else 0
        
        # 判断状态：>=99.9%为ok，<99.9%为degraded
        status = 'ok' if success_rate >= 99.9 else 'degraded'
        
        return {
            "success_rate_percent": round(success_rate, 2),
            "total": total,
            "failed": failed,
            "status": status
        }
        
    except SQLAlchemyError as e:
        logger.warning(f"Unable to query recalc success rate: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Error getting recalc success rate: {str(e)}")
        return None
