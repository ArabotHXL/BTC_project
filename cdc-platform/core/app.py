"""
HashInsight CDC Platform - Main Flask Application
包含Outbox模式的API Gateway和Domain Services
"""
import os
import logging
from flask import Flask, jsonify
from flask_cors import CORS

# 导入本地模块
from core.infra.database import db, init_db
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
