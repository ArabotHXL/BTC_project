"""
System Monitoring Blueprint
系统监控Blueprint

Unified monitoring API endpoints that aggregate health checks and performance metrics
from all modules (Database, Redis, Intelligence Layer, CDC Platform, Scheduler)

统一的监控API端点，聚合所有模块的健康检查和性能指标数据

Endpoints:
- GET /api/monitoring/overview - System health overview
- GET /api/monitoring/metrics - Performance metrics
- GET /api/monitoring/alerts - Alert list
"""

import logging
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, render_template
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from db import db
from common.rbac import require_permission, Permission
from intelligence.monitoring.slo_tracker import slo_metrics

logger = logging.getLogger(__name__)

monitoring_bp = Blueprint('monitoring', __name__, url_prefix='/api/monitoring')


@monitoring_bp.route('/dashboard', methods=['GET'])
@require_permission([Permission.SYSTEM_ADMIN])
def monitoring_dashboard():
    """
    Monitoring dashboard page
    系统监控仪表盘页面
    
    Returns:
        HTML template for monitoring dashboard
    """
    return render_template('admin/monitoring_dashboard.html',
                         title='System Monitoring',
                         page='monitoring_dashboard')


@monitoring_bp.route('/overview', methods=['GET'])
@require_permission([Permission.SYSTEM_ADMIN])
def system_overview():
    """
    System health overview
    系统健康概览
    
    Aggregates status from all modules:
    - Database (PostgreSQL)
    - Redis Cache
    - Intelligence Layer (Outbox, SLO)
    - CDC Platform (Kafka lag)
    - Scheduler (Task execution)
    
    Returns:
        JSON with overall system status and module details
    """
    try:
        modules = {}
        overall_status = 'healthy'
        healthy_count = 0
        degraded_count = 0
        unhealthy_count = 0
        
        db_status = check_database_health()
        modules['database'] = db_status
        if db_status['status'] == 'healthy':
            healthy_count += 1
        elif db_status['status'] == 'degraded':
            degraded_count += 1
        else:
            unhealthy_count += 1
            overall_status = 'unhealthy'
        
        redis_status = check_redis_health()
        modules['redis'] = redis_status
        if redis_status['status'] == 'healthy':
            healthy_count += 1
        elif redis_status['status'] == 'degraded':
            degraded_count += 1
            if overall_status == 'healthy':
                overall_status = 'degraded'
        else:
            unhealthy_count += 1
            overall_status = 'unhealthy'
        
        intel_status = check_intelligence_health()
        modules['intelligence'] = intel_status
        if intel_status['status'] == 'healthy':
            healthy_count += 1
        elif intel_status['status'] == 'degraded':
            degraded_count += 1
            if overall_status == 'healthy':
                overall_status = 'degraded'
        else:
            unhealthy_count += 1
            overall_status = 'unhealthy'
        
        cdc_status = check_cdc_health()
        modules['cdc'] = cdc_status
        if cdc_status['status'] == 'healthy':
            healthy_count += 1
        elif cdc_status['status'] == 'degraded':
            degraded_count += 1
            if overall_status == 'healthy':
                overall_status = 'degraded'
        else:
            unhealthy_count += 1
            overall_status = 'unhealthy'
        
        scheduler_status = check_scheduler_health()
        modules['scheduler'] = scheduler_status
        if scheduler_status['status'] == 'healthy':
            healthy_count += 1
        elif scheduler_status['status'] == 'degraded':
            degraded_count += 1
            if overall_status == 'healthy':
                overall_status = 'degraded'
        else:
            unhealthy_count += 1
            overall_status = 'unhealthy'
        
        return jsonify({
            'status': overall_status,
            'timestamp': datetime.utcnow().isoformat(),
            'modules': modules,
            'summary': {
                'total_modules': 5,
                'healthy_count': healthy_count,
                'degraded_count': degraded_count,
                'unhealthy_count': unhealthy_count
            }
        })
        
    except Exception as e:
        logger.error(f"System overview failed: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500


@monitoring_bp.route('/metrics', methods=['GET'])
@require_permission([Permission.SYSTEM_ADMIN])
def performance_metrics():
    """
    Performance metrics endpoint
    性能指标端点
    
    Aggregates performance data from:
    - SLO tracker (P95 TTR, success rate, latency distribution)
    - Prometheus exporter (API metrics, cache hit rate)
    
    Returns:
        JSON with SLO and API performance metrics
    """
    try:
        slo_summary = slo_metrics.get_summary()
        
        slo_data = {
            'p95_ttr': slo_summary.get('p95_ttr_ms'),
            'p50_ttr': slo_summary.get('p50_ttr_ms'),
            'avg_ttr': slo_summary.get('avg_ttr_ms'),
            'success_rate': slo_summary.get('success_rate_pct'),
            'latency_distribution': slo_summary.get('latency_distribution', {})
        }
        
        try:
            from monitoring.prometheus_exporter import metrics_collector
            
            prom_summary = metrics_collector.get_summary()
            
            api_data = {
                'request_rate': prom_summary.get('total_requests', 0),
                'error_rate': prom_summary.get('error_rate', 0.0),
                'active_requests': prom_summary.get('active_requests', 0)
            }
            
            cache_data = {
                'hit_rate': prom_summary.get('cache_hit_rate', 0.0),
                'total_requests': (
                    metrics_collector._metrics.get('cache_hits_total', 0) + 
                    metrics_collector._metrics.get('cache_misses_total', 0)
                ),
                'hits': metrics_collector._metrics.get('cache_hits_total', 0)
            }
            
        except (ImportError, AttributeError) as e:
            logger.warning(f"Prometheus metrics unavailable: {str(e)}")
            api_data = {
                'request_rate': 'N/A',
                'error_rate': 'N/A',
                'active_requests': 'N/A'
            }
            cache_data = {
                'hit_rate': 'N/A',
                'total_requests': 'N/A',
                'hits': 'N/A'
            }
        
        return jsonify({
            'success': True,
            'timestamp': datetime.utcnow().isoformat(),
            'slo': slo_data,
            'api': api_data,
            'cache': cache_data
        })
        
    except Exception as e:
        logger.error(f"Performance metrics retrieval failed: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500


@monitoring_bp.route('/alerts', methods=['GET'])
@require_permission([Permission.SYSTEM_ADMIN])
def system_alerts():
    """
    System alerts endpoint
    系统告警端点
    
    Checks for:
    - SLO violations (from slo_tracker)
    - Circuit breaker status
    - Outbox backlog
    - Kafka lag (CDC platform)
    
    Returns:
        JSON with list of active alerts
    """
    try:
        alerts = []
        
        slo_compliance = slo_metrics.check_slo_compliance()
        if not slo_compliance.get('compliant', True):
            for alert in slo_compliance.get('alerts', []):
                alerts.append({
                    'severity': alert.get('severity', 'warning'),
                    'module': 'intelligence',
                    'metric': alert.get('metric'),
                    'message': alert.get('message'),
                    'timestamp': datetime.utcnow().isoformat()
                })
        
        outbox_alert = check_outbox_backlog()
        if outbox_alert:
            alerts.append(outbox_alert)
        
        kafka_alert = check_kafka_lag()
        if kafka_alert:
            alerts.append(kafka_alert)
        
        circuit_breaker_alert = check_circuit_breaker()
        if circuit_breaker_alert:
            alerts.append(circuit_breaker_alert)
        
        return jsonify({
            'success': True,
            'timestamp': datetime.utcnow().isoformat(),
            'alerts': alerts,
            'count': len(alerts)
        })
        
    except Exception as e:
        logger.error(f"Alert retrieval failed: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500


def check_database_health():
    """
    Check database health
    检查数据库健康状态
    
    Returns:
        dict: Database health status with response time
    """
    try:
        import time
        start_time = time.time()
        
        db.session.execute(text('SELECT 1'))
        db.session.commit()
        
        response_time_ms = (time.time() - start_time) * 1000
        
        return {
            'status': 'healthy',
            'response_time_ms': round(response_time_ms, 2),
            'type': 'postgresql'
        }
    except SQLAlchemyError as e:
        logger.error(f"Database health check failed: {str(e)}")
        return {
            'status': 'unhealthy',
            'error': str(e),
            'type': 'postgresql'
        }


def check_redis_health():
    """
    Check Redis health
    检查Redis健康状态
    
    Returns:
        dict: Redis health status
    """
    try:
        from intelligence.api.health_api import check_redis_connection
        
        redis_status = check_redis_connection()
        
        if redis_status.get('status') == 'connected':
            return {
                'status': 'healthy',
                'type': 'redis'
            }
        elif redis_status.get('status') == 'unavailable':
            return {
                'status': 'degraded',
                'message': 'Redis unavailable (optional service)',
                'type': 'redis'
            }
        else:
            return {
                'status': 'unhealthy',
                'error': redis_status.get('error', 'Unknown error'),
                'type': 'redis'
            }
            
    except ImportError:
        logger.warning("Redis check module not available")
        return {
            'status': 'unknown',
            'message': 'Redis module not available',
            'type': 'redis'
        }
    except Exception as e:
        logger.error(f"Redis health check failed: {str(e)}")
        return {
            'status': 'unknown',
            'error': str(e),
            'type': 'redis'
        }


def check_intelligence_health():
    """
    Check Intelligence Layer health
    检查智能层健康状态
    
    Returns:
        dict: Intelligence layer health with outbox backlog and P95 TTR
    """
    try:
        outbox_query = text("""
            SELECT COUNT(*) as backlog
            FROM event_outbox
            WHERE status IN ('PENDING', 'RETRYING')
            AND created_at > :cutoff_time
        """)
        
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        result = db.session.execute(outbox_query, {'cutoff_time': cutoff_time}).fetchone()
        
        outbox_backlog = result[0] if result else 0
        
        p95_ttr = slo_metrics.get_p95_ttr()
        
        status = 'healthy'
        if outbox_backlog > 50:
            status = 'degraded'
        if outbox_backlog > 200:
            status = 'unhealthy'
        
        return {
            'status': status,
            'outbox_backlog': outbox_backlog,
            'p95_ttr': p95_ttr
        }
        
    except SQLAlchemyError as e:
        logger.warning(f"Unable to query intelligence health: {str(e)}")
        return {
            'status': 'unknown',
            'error': str(e)
        }
    except Exception as e:
        logger.error(f"Intelligence health check failed: {str(e)}")
        return {
            'status': 'unknown',
            'error': str(e)
        }


def check_cdc_health():
    """
    Check CDC Platform health
    检查CDC平台健康状态
    
    Returns:
        dict: CDC platform health with Kafka lag
    """
    try:
        kafka_lag_query = text("""
            SELECT 
                COALESCE(SUM(lag), 0) as total_lag
            FROM kafka_consumer_offsets
            WHERE last_updated > :cutoff_time
        """)
        
        cutoff_time = datetime.utcnow() - timedelta(minutes=5)
        result = db.session.execute(kafka_lag_query, {'cutoff_time': cutoff_time}).fetchone()
        
        kafka_lag = result[0] if result else 0
        
        status = 'healthy'
        if kafka_lag > 1000:
            status = 'degraded'
        if kafka_lag > 10000:
            status = 'unhealthy'
        
        return {
            'status': status,
            'kafka_lag': kafka_lag
        }
        
    except SQLAlchemyError:
        return {
            'status': 'unknown',
            'message': 'CDC monitoring table not available'
        }
    except Exception as e:
        logger.error(f"CDC health check failed: {str(e)}")
        return {
            'status': 'unknown',
            'error': str(e)
        }


def check_scheduler_health():
    """
    Check Scheduler health
    检查调度器健康状态
    
    Returns:
        dict: Scheduler health with tasks executed count
    """
    try:
        scheduler_query = text("""
            SELECT COUNT(*) as tasks_executed
            FROM scheduled_tasks
            WHERE status = 'COMPLETED'
            AND executed_at > :cutoff_time
        """)
        
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        result = db.session.execute(scheduler_query, {'cutoff_time': cutoff_time}).fetchone()
        
        tasks_executed = result[0] if result else 0
        
        return {
            'status': 'healthy',
            'tasks_executed': tasks_executed
        }
        
    except SQLAlchemyError:
        return {
            'status': 'unknown',
            'message': 'Scheduler monitoring table not available'
        }
    except Exception as e:
        logger.error(f"Scheduler health check failed: {str(e)}")
        return {
            'status': 'unknown',
            'error': str(e)
        }


def check_outbox_backlog():
    """
    Check for outbox backlog alerts
    检查Outbox积压告警
    
    Returns:
        dict or None: Alert if backlog exceeds threshold
    """
    try:
        outbox_query = text("""
            SELECT COUNT(*) as backlog
            FROM event_outbox
            WHERE status IN ('PENDING', 'RETRYING')
            AND created_at > :cutoff_time
        """)
        
        cutoff_time = datetime.utcnow() - timedelta(hours=1)
        result = db.session.execute(outbox_query, {'cutoff_time': cutoff_time}).fetchone()
        
        backlog = result[0] if result else 0
        
        if backlog > 100:
            return {
                'severity': 'critical' if backlog > 500 else 'warning',
                'module': 'intelligence',
                'metric': 'outbox_backlog',
                'message': f'Outbox backlog high: {backlog} pending events',
                'timestamp': datetime.utcnow().isoformat()
            }
        
        return None
        
    except SQLAlchemyError as e:
        logger.warning(f"Unable to check outbox backlog: {str(e)}")
        return None


def check_kafka_lag():
    """
    Check for Kafka consumer lag alerts
    检查Kafka延迟告警
    
    Returns:
        dict or None: Alert if lag exceeds threshold
    """
    try:
        kafka_lag_query = text("""
            SELECT 
                consumer_group,
                SUM(lag) as total_lag
            FROM kafka_consumer_offsets
            WHERE last_updated > :cutoff_time
            GROUP BY consumer_group
            HAVING SUM(lag) > 1000
        """)
        
        cutoff_time = datetime.utcnow() - timedelta(minutes=5)
        result = db.session.execute(kafka_lag_query, {'cutoff_time': cutoff_time}).fetchone()
        
        if result:
            consumer_group = result[0]
            lag = result[1]
            
            return {
                'severity': 'critical' if lag > 10000 else 'warning',
                'module': 'cdc',
                'metric': 'kafka_lag',
                'message': f'Kafka consumer lag high for {consumer_group}: {lag} messages',
                'timestamp': datetime.utcnow().isoformat()
            }
        
        return None
        
    except SQLAlchemyError:
        return None


def check_circuit_breaker():
    """
    Check circuit breaker status
    检查熔断器状态
    
    Returns:
        dict or None: Alert if circuit breaker is open
    """
    try:
        circuit_breaker_query = text("""
            SELECT 
                service_name,
                state,
                failure_count
            FROM circuit_breaker_state
            WHERE state = 'OPEN'
            AND updated_at > :cutoff_time
        """)
        
        cutoff_time = datetime.utcnow() - timedelta(minutes=15)
        result = db.session.execute(circuit_breaker_query, {'cutoff_time': cutoff_time}).fetchone()
        
        if result:
            service_name = result[0]
            state = result[1]
            failure_count = result[2]
            
            return {
                'severity': 'critical',
                'module': 'api_gateway',
                'metric': 'circuit_breaker',
                'message': f'Circuit breaker OPEN for {service_name} (failures: {failure_count})',
                'timestamp': datetime.utcnow().isoformat()
            }
        
        return None
        
    except SQLAlchemyError:
        return None
