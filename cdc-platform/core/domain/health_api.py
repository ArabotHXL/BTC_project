"""
HashInsight CDC Platform - Health Check API Blueprint
系统健康检查API，监控CDC管道状态
"""
import os
import logging
from flask import Blueprint, jsonify
from datetime import datetime, timedelta
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from core.infra.database import db
from core.infra.redis_client import redis_client

logger = logging.getLogger(__name__)

# 创建Blueprint
bp = Blueprint('health', __name__)

# ==================== GET /api/health ====================

@bp.route('/health', methods=['GET'])
def health_check():
    """
    系统健康检查
    
    功能：
    1. 检查Outbox积压量（outbox_backlog）
    2. 检查Kafka消费者延迟（kafka_consumer_lag）- 占位
    3. 检查DLQ死信队列数量（dlq_count）
    4. 检查预测数据新鲜度（forecast_freshness_sec）
    5. 检查Redis缓存命中率（cache_hit_rate）
    6. 返回系统版本信息
    
    curl示例:
    ```bash
    curl -X GET https://api.hashinsight.io/api/health
    ```
    
    响应示例（健康状态）:
    ```json
    {
      "status": "healthy",
      "timestamp": "2025-10-08T22:45:30Z",
      "version": "1.0.0-cdc",
      "checks": {
        "database": {
          "status": "healthy",
          "response_time_ms": 5
        },
        "redis": {
          "status": "healthy",
          "connected_clients": 3
        },
        "outbox": {
          "status": "healthy",
          "backlog": 12,
          "oldest_pending_sec": 30
        },
        "kafka_consumer": {
          "status": "unknown",
          "lag": null,
          "note": "Placeholder - requires Kafka metrics integration"
        },
        "dlq": {
          "status": "healthy",
          "count": 0
        },
        "forecast": {
          "status": "healthy",
          "freshness_sec": 120,
          "last_update": "2025-10-08T22:43:30Z"
        },
        "cache": {
          "status": "healthy",
          "hit_rate": 0.85,
          "total_requests": 1000,
          "hits": 850
        }
      },
      "overall_status": "healthy"
    }
    ```
    
    状态码:
    - 200: 系统健康
    - 503: 系统不健康（有严重问题）
    """
    health_data = {
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'version': os.getenv('APP_VERSION', '1.0.0-cdc'),
        'checks': {},
        'overall_status': 'healthy'
    }
    
    has_critical_issue = False
    
    # 1. 数据库健康检查
    try:
        start_time = datetime.utcnow()
        db.session.execute(text("SELECT 1"))
        response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        health_data['checks']['database'] = {
            'status': 'healthy',
            'response_time_ms': round(response_time, 2)
        }
    except Exception as e:
        logger.error(f"❌ Database health check failed: {e}")
        health_data['checks']['database'] = {
            'status': 'unhealthy',
            'error': str(e)
        }
        has_critical_issue = True
    
    # 2. Redis健康检查
    try:
        redis_health = redis_client.health_check()
        health_data['checks']['redis'] = redis_health
        
        if redis_health.get('status') != 'healthy':
            logger.warning("⚠️ Redis is unhealthy (non-critical)")
    except Exception as e:
        logger.error(f"❌ Redis health check failed: {e}")
        health_data['checks']['redis'] = {
            'status': 'unhealthy',
            'error': str(e)
        }
    
    # 3. Outbox积压检查
    try:
        sql = text("""
            SELECT 
                COUNT(*) FILTER (WHERE processed = false) as backlog,
                EXTRACT(EPOCH FROM (NOW() - MIN(created_at) FILTER (WHERE processed = false))) as oldest_pending_sec
            FROM event_outbox
        """)
        result = db.session.execute(sql).first()
        
        backlog = result.backlog or 0 if result else 0
        oldest_pending_sec = result.oldest_pending_sec or 0 if result else 0
        
        # 判断健康状态（积压>1000或最老事件>5分钟则警告）
        outbox_status = 'healthy'
        if backlog > 1000 or oldest_pending_sec > 300:
            outbox_status = 'degraded'
        
        health_data['checks']['outbox'] = {
            'status': outbox_status,
            'backlog': backlog,
            'oldest_pending_sec': int(oldest_pending_sec)
        }
    except Exception as e:
        logger.error(f"❌ Outbox check failed: {e}")
        health_data['checks']['outbox'] = {
            'status': 'unknown',
            'error': str(e)
        }
    
    # 4. Kafka消费者延迟检查
    try:
        from core.monitoring.kafka_lag import get_consumer_lag_summary  # type: ignore
        
        lag_summary = get_consumer_lag_summary()
        
        if lag_summary.get('status') == 'unavailable':
            health_data['checks']['kafka_consumer'] = {
                'status': 'unavailable',
                'message': 'Kafka monitoring not available'
            }
        else:
            kafka_status = lag_summary.get('status', 'unknown')
            total_lag = lag_summary.get('total_lag_all_groups', 0)
            
            health_data['checks']['kafka_consumer'] = {
                'status': kafka_status,
                'total_lag': total_lag,
                'group_count': lag_summary.get('group_count', 0),
                'groups': lag_summary.get('groups', {})
            }
            
            if kafka_status == 'critical':
                logger.warning(f"⚠️ Kafka consumer lag is critical: {total_lag}")
    
    except Exception as e:
        logger.error(f"❌ Kafka consumer lag check failed: {e}")
        health_data['checks']['kafka_consumer'] = {
            'status': 'error',
            'error': str(e)
        }
    
    # 5. DLQ死信队列检查
    try:
        sql = text("SELECT COUNT(*) FROM event_dlq")
        dlq_count = db.session.execute(sql).scalar() or 0
        
        dlq_status = 'healthy' if dlq_count < 10 else 'degraded'
        
        health_data['checks']['dlq'] = {
            'status': dlq_status,
            'count': dlq_count
        }
        
        if dlq_count > 100:
            logger.warning(f"⚠️ High DLQ count: {dlq_count}")
    except Exception as e:
        logger.error(f"❌ DLQ check failed: {e}")
        health_data['checks']['dlq'] = {
            'status': 'unknown',
            'error': str(e)
        }
    
    # 6. 预测数据新鲜度检查
    try:
        sql = text("""
            SELECT MAX(created_at) as last_update
            FROM forecast_daily
            WHERE date >= CURRENT_DATE
        """)
        result = db.session.execute(sql).first()
        
        if result and result.last_update:
            freshness_sec = int((datetime.utcnow() - result.last_update).total_seconds())
            forecast_status = 'healthy' if freshness_sec < 3600 else 'stale'
            
            health_data['checks']['forecast'] = {
                'status': forecast_status,
                'freshness_sec': freshness_sec,
                'last_update': result.last_update.isoformat()
            }
        else:
            health_data['checks']['forecast'] = {
                'status': 'no_data',
                'freshness_sec': None,
                'last_update': None
            }
    except Exception as e:
        logger.error(f"❌ Forecast check failed: {e}")
        health_data['checks']['forecast'] = {
            'status': 'unknown',
            'error': str(e)
        }
    
    # 7. 缓存命中率检查（从Redis获取统计）
    try:
        cache_hits = int(redis_client.get('cache:hits') or 0)
        cache_misses = int(redis_client.get('cache:misses') or 0)
        total_requests = cache_hits + cache_misses
        
        hit_rate = cache_hits / total_requests if total_requests > 0 else 0
        
        health_data['checks']['cache'] = {
            'status': 'healthy',
            'hit_rate': round(hit_rate, 2),
            'total_requests': total_requests,
            'hits': cache_hits
        }
    except Exception as e:
        logger.error(f"❌ Cache check failed: {e}")
        health_data['checks']['cache'] = {
            'status': 'unknown',
            'error': str(e)
        }
    
    # 确定整体状态
    if has_critical_issue:
        health_data['overall_status'] = 'unhealthy'
        health_data['status'] = 'unhealthy'
        return jsonify(health_data), 503
    
    # 检查是否有降级服务
    degraded_services = [
        check for check in health_data['checks'].values()
        if check.get('status') == 'degraded'
    ]
    
    if degraded_services:
        health_data['overall_status'] = 'degraded'
        health_data['status'] = 'degraded'
    
    return jsonify(health_data), 200
