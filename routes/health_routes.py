"""
HashInsight Enterprise - Health & Status Routes
健康检查和状态路由

提供以下端点:
- /health - 快速存活检查 (无DB探测)
- /health/deep - 深度健康检查 (含数据库状态)
- /api/health - API健康检查
- /status - 负载均衡器状态
- /ready - 部署就绪检查
- /alive - 存活探测
"""

import os
import logging
from datetime import datetime
from flask import Blueprint, jsonify, redirect, url_for

logger = logging.getLogger(__name__)

system_health_bp = Blueprint('system_health', __name__)


@system_health_bp.route('/health', methods=['GET'])
def health_check():
    """Fast liveness health check for Autoscale deployment - responds immediately without DB check"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    }), 200


@system_health_bp.route('/health/deep', methods=['GET'])
def deep_health_check():
    """Deep health check endpoint with database status for monitoring"""
    try:
        from db import db
        from database_health import db_health_manager
        from sqlalchemy import text
        
        database_url = os.environ.get('DATABASE_URL')
        db_status = db_health_manager.check_database_connection(database_url)
        
        if db_status['connected']:
            try:
                db.session.execute(text('SELECT 1'))
                db.session.commit()
            except Exception as e:
                logger.warning(f"SQLAlchemy health check failed: {e}")
                return jsonify({
                    'status': 'degraded',
                    'database': {'status': 'connected_with_issues', 'error': str(e)},
                    'timestamp': datetime.now().isoformat()
                }), 200
            
            return jsonify({
                'status': 'healthy',
                'database': {'status': 'connected', 'version': db_status.get('database_version', 'Unknown')},
                'timestamp': datetime.now().isoformat()
            }), 200
        else:
            return jsonify({
                'status': 'unhealthy',
                'database': {'status': 'disconnected', 'error': db_status.get('error', 'Unknown')},
                'timestamp': datetime.now().isoformat()
            }), 503
            
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'database': {'status': 'error', 'error': str(e)},
            'timestamp': datetime.now().isoformat()
        }), 500


@system_health_bp.route('/api/health', methods=['GET'])
def api_health_check():
    """API health check endpoint"""
    return health_check()


@system_health_bp.route('/status', methods=['GET'])
def status_check():
    """Basic status endpoint for load balancer health checks"""
    return jsonify({"status": "ok"}), 200


@system_health_bp.route('/status/<site_slug>')
def public_site_status(site_slug):
    """公开的站点状态页面 - 重定向到托管模块"""
    try:
        return redirect(url_for('hosting.public_site_status', site_slug=site_slug))
    except Exception as e:
        logger.error(f"Public site status redirect failed: {e}")
        return jsonify({"error": "Site not found"}), 404


@system_health_bp.route('/ready', methods=['GET'])
def readiness_check():
    """Lightweight readiness probe for deployment health checks"""
    try:
        return jsonify({
            "status": "ready", 
            "app": "running",
            "timestamp": datetime.now().isoformat()
        }), 200
    except Exception:
        return jsonify({"status": "not_ready"}), 503


@system_health_bp.route('/alive', methods=['GET'])
def liveness_check():
    """Minimal liveness probe - just return OK"""
    return "OK", 200
