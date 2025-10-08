"""
HashInsight CDC Platform - Main Flask Application
包含Outbox模式的API Gateway和Domain Services
"""
import os
import logging
from flask import Flask, jsonify, request, g
from flask_cors import CORS
from datetime import datetime
import jwt
from functools import wraps

# 导入本地模块
from core.infra.database import db, init_db
from core.infra.redis_client import redis_client
from core.infra.outbox import OutboxPublisher
from core.domain import miners_api, intelligence_api, treasury_api, health_api

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建Flask应用
app = Flask(__name__)
CORS(app)

# 配置
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET'] = os.getenv('JWT_SECRET', 'dev-secret')

# 初始化数据库
init_db(app)

# 初始化Outbox发布器
outbox_publisher = OutboxPublisher(db)

# ==================== 中间件 ====================

def jwt_required(scopes=[]):
    """JWT认证装饰器，支持Scope验证"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            auth_header = request.headers.get('Authorization')
            
            if not auth_header:
                return jsonify({'error': 'Missing authorization header'}), 401
            
            try:
                token = auth_header.split(' ')[1] if ' ' in auth_header else auth_header
                payload = jwt.decode(token, app.config['JWT_SECRET'], algorithms=['HS256'])
                
                # 设置上下文
                g.user_id = payload.get('user_id')
                g.tenant_id = payload.get('tenant_id', 'default')
                g.role = payload.get('role', 'user')
                g.scopes = payload.get('scopes', [])
                
                # 验证Scope
                if scopes:
                    if not any(scope in g.scopes for scope in scopes):
                        return jsonify({'error': f'Missing required scope: {scopes}'}), 403
                
                # 设置PostgreSQL session变量（用于RLS）
                with db.engine.connect() as conn:
                    conn.execute(f"SET app.user_id = '{g.user_id}'")
                    conn.execute(f"SET app.tenant_id = '{g.tenant_id}'")
                    conn.execute(f"SET app.role = '{g.role}'")
                    conn.commit()
                
                return f(*args, **kwargs)
            
            except jwt.ExpiredSignatureError:
                return jsonify({'error': 'Token expired'}), 401
            except jwt.InvalidTokenError as e:
                return jsonify({'error': f'Invalid token: {str(e)}'}), 401
        
        return decorated_function
    return decorator

def rate_limit():
    """速率限制装饰器（使用Redis）"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(g, 'user_id'):
                return f(*args, **kwargs)
            
            key = f"rate_limit:{g.user_id}:{datetime.utcnow().minute}"
            count = redis_client.incr(key)
            redis_client.expire(key, 60)
            
            limit = int(os.getenv('RATE_LIMIT_PER_MINUTE', 60))
            
            if count > limit:
                return jsonify({'error': 'Rate limit exceeded'}), 429
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator

# ==================== 路由注册 ====================

# 注册API蓝图
app.register_blueprint(miners_api.bp, url_prefix='/api')
app.register_blueprint(intelligence_api.bp, url_prefix='/api/intelligence')
app.register_blueprint(treasury_api.bp, url_prefix='/api/treasury')
app.register_blueprint(health_api.bp, url_prefix='/api')

# ==================== 根路由 ====================

@app.route('/')
def index():
    """API根路径"""
    return jsonify({
        'name': 'HashInsight CDC Platform',
        'version': os.getenv('APP_VERSION', '1.0.0-cdc'),
        'status': 'running',
        'endpoints': {
            'miners': '/api/miners',
            'intelligence': '/api/intelligence/forecast',
            'treasury': '/api/treasury/execute',
            'health': '/api/health'
        }
    })

# ==================== 错误处理 ====================

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal error: {error}")
    return jsonify({'error': 'Internal server error'}), 500

# ==================== 应用启动 ====================

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
