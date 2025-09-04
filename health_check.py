"""
健康检查端点 - Sprint 1 要求
提供 /healthz 端点用于系统健康监控
"""
from flask import jsonify, current_app
from datetime import datetime
import os
import psutil
from db import db
from sqlalchemy import text

def register_health_check(app):
    """注册健康检查端点到Flask应用"""
    
    @app.route('/healthz')
    def health_check_endpoint():
        """系统健康检查端点
        
        检查项目：
        - 数据库连接
        - 内存使用
        - 磁盘空间  
        - 关键模块状态
        """
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'version': '1.0.0-sprint1',
            'checks': {}
        }
        
        overall_healthy = True
        
        # 数据库连接检查
        try:
            result = db.session.execute(text('SELECT 1')).fetchone()
            health_status['checks']['database'] = {
                'status': 'healthy',
                'response_time_ms': 'ok'
            }
        except Exception as e:
            health_status['checks']['database'] = {
                'status': 'unhealthy', 
                'error': str(e)
            }
            overall_healthy = False
        
        # 内存使用检查
        try:
            memory = psutil.virtual_memory()
            memory_usage = memory.percent
            health_status['checks']['memory'] = {
                'status': 'healthy' if memory_usage < 85 else 'warning',
                'usage_percent': memory_usage,
                'available_mb': round(memory.available / 1024 / 1024, 1)
            }
            if memory_usage and memory_usage >= 90:
                overall_healthy = False
        except:
            health_status['checks']['memory'] = {'status': 'unknown'}
        
        # 磁盘空间检查
        try:
            disk = psutil.disk_usage('/')
            disk_usage = disk.percent
            health_status['checks']['disk'] = {
                'status': 'healthy' if disk_usage < 85 else 'warning',
                'usage_percent': disk_usage,
                'free_gb': round(disk.free / 1024 / 1024 / 1024, 1)
            }
            if disk_usage >= 95:
                overall_healthy = False
        except:
            health_status['checks']['disk'] = {'status': 'unknown'}
        
        # 托管模块状态检查
        try:
            from modules.hosting import hosting_bp
            from modules.client import client_bp
            health_status['checks']['hosting_modules'] = {
                'status': 'healthy',
                'hosting_blueprint': 'loaded',
                'client_blueprint': 'loaded'
            }
        except ImportError as e:
            health_status['checks']['hosting_modules'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
            overall_healthy = False
        
        # 环境配置检查
        required_env_vars = [
            'DATABASE_URL', 'SECRET_KEY', 'SESSION_SECRET'
        ]
        missing_vars = [var for var in required_env_vars if not os.environ.get(var)]
        if missing_vars:
            health_status['checks']['environment'] = {
                'status': 'unhealthy',
                'missing_variables': missing_vars
            }
            overall_healthy = False
        else:
            health_status['checks']['environment'] = {
                'status': 'healthy',
                'no_money_mode': os.environ.get('NO_MONEY_MODE', 'false').lower() == 'true'
            }
        
        # 设置总体状态
        health_status['status'] = 'healthy' if overall_healthy else 'unhealthy'
        
        # 返回适当的HTTP状态码
        status_code = 200 if overall_healthy else 503
        return jsonify(health_status), status_code
    
    @app.route('/ready')
    def readiness_check_endpoint():
        """就绪检查 - 检查应用是否准备好接受流量"""
        try:
            # 快速数据库连接检查
            db.session.execute(text('SELECT 1'))
            
            # 检查关键表是否存在
            tables_check = db.session.execute(text(
                "SELECT COUNT(*) FROM information_schema.tables WHERE table_name IN ('hosting_sites', 'hosting_miners', 'user_access')"
            )).scalar()
            
            if tables_check >= 3:
                return jsonify({
                    'status': 'ready',
                    'timestamp': datetime.now().isoformat()
                }), 200
            else:
                return jsonify({
                    'status': 'not_ready',
                    'reason': 'database_tables_missing',
                    'timestamp': datetime.now().isoformat()
                }), 503
                
        except Exception as e:
            return jsonify({
                'status': 'not_ready',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }), 503
    
    @app.route('/live')  
    def liveness_check_endpoint():
        """存活检查 - 最基本的检查，应用是否还在运行"""
        return jsonify({
            'status': 'alive',
            'timestamp': datetime.now().isoformat(),
            'uptime_seconds': psutil.boot_time() if hasattr(psutil, 'boot_time') else 'unknown'
        }), 200