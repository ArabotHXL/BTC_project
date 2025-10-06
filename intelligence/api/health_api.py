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
