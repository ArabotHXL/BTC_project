"""
Web3集成模块主应用
Main Flask Application for Web3 Integration Module
"""

import os
import logging
from flask import Flask, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass

# 全局数据库实例
db = SQLAlchemy(model_class=Base)

def create_app(config_name=None):
    """应用工厂函数"""
    
    # 创建Flask应用
    app = Flask(__name__)
    
    # 加载配置
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    try:
        from .config import config
    except ImportError:
        # Fallback for standalone execution
        from config import config
    app.config.from_object(config[config_name])
    
    # 生产环境配置验证
    if config_name == 'production':
        config[config_name].validate_production_config()
    
    # 设置代理修复
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
    
    # 初始化数据库
    db.init_app(app)
    
    # 注册蓝图
    register_blueprints(app)
    
    # 注册错误处理器
    register_error_handlers(app)
    
    # 注册钩子函数
    register_hooks(app)
    
    # 创建数据库表
    with app.app_context():
        # 导入模型以确保表被创建
        try:
            from . import models
        except ImportError:
            # Fallback for standalone execution
            import models
        db.create_all()
        
        # 启动后台服务
        start_background_services(app)
    
    logger.info(f"Web3集成模块已启动，环境: {config_name}")
    return app

def register_blueprints(app):
    """注册蓝图"""
    
    # 导入并注册路由蓝图
    try:
        from .routes.auth import auth_bp
        from .routes.payments import payments_bp
        from .routes.nft import nft_bp
        from .routes.compliance import compliance_bp
    except ImportError:
        # Fallback for standalone execution
        from routes.auth import auth_bp
        from routes.payments import payments_bp
        from routes.nft import nft_bp
        from routes.compliance import compliance_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(payments_bp)
    app.register_blueprint(nft_bp)
    app.register_blueprint(compliance_bp)
    
    # 注册主页路由
    @app.route('/')
    def index():
        """主页"""
        return jsonify({
            'service': 'Web3 Integration Module',
            'version': '1.0.0',
            'status': 'running',
            'endpoints': {
                'auth': '/auth',
                'payments': '/payments',
                'nft': '/nft',
                'compliance': '/compliance'
            },
            'features': [
                'Wallet Authentication',
                'Cryptocurrency Payments',
                'SLA NFT Certificates',
                'AML/KYC Compliance',
                'Blockchain Integration',
                'IPFS Storage'
            ]
        })
    
    @app.route('/health')
    def health_check():
        """健康检查"""
        try:
            # 检查数据库连接
            db.session.execute('SELECT 1')
            
            # 检查服务状态
            try:
                from .services.blockchain import blockchain_integration
                from .services.payment_monitor import payment_monitor_service
                from .services.nft_minting import sla_nft_minting_system
            except ImportError:
                # Fallback for standalone execution
                from services.blockchain import blockchain_integration
                from services.payment_monitor import payment_monitor_service
                from services.nft_minting import sla_nft_minting_system
            
            blockchain_status = blockchain_integration.w3 is not None and blockchain_integration.w3.is_connected() if blockchain_integration.w3 else False
            payment_monitor_status = payment_monitor_service.get_service_status()
            nft_minting_status = sla_nft_minting_system.get_minting_statistics()
            
            return jsonify({
                'status': 'healthy',
                'database': 'connected',
                'blockchain': 'connected' if blockchain_status else 'disconnected',
                'services': {
                    'payment_monitor': payment_monitor_status,
                    'nft_minting': nft_minting_status
                },
                'timestamp': db.func.now()
            })
            
        except Exception as e:
            logger.error(f"健康检查失败: {e}")
            return jsonify({
                'status': 'unhealthy',
                'error': str(e)
            }), 503
    
    @app.route('/api/info')
    def api_info():
        """API信息"""
        return jsonify({
            'name': 'Web3 Integration Module API',
            'version': '1.0.0',
            'description': 'Independent Web3 integration service for blockchain, payments, and NFT functionality',
            'documentation': '/docs',
            'support': {
                'cryptocurrencies': ['BTC', 'ETH', 'USDC'],
                'networks': ['Bitcoin', 'Ethereum', 'Base L2'],
                'features': [
                    'Wallet Authentication (MetaMask, WalletConnect)',
                    'Cryptocurrency Payment Processing',
                    'NFT Certificate Minting',
                    'AML/KYC Compliance Checks',
                    'IPFS Data Storage',
                    'Smart Contract Interaction'
                ]
            }
        })

def register_error_handlers(app):
    """注册错误处理器"""
    
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({'error': 'Bad request', 'message': str(error)}), 400
    
    @app.errorhandler(401)
    def unauthorized(error):
        return jsonify({'error': 'Unauthorized', 'message': 'Authentication required'}), 401
    
    @app.errorhandler(403)
    def forbidden(error):
        return jsonify({'error': 'Forbidden', 'message': 'Insufficient permissions'}), 403
    
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Not found', 'message': 'Resource not found'}), 404
    
    @app.errorhandler(429)
    def rate_limit_exceeded(error):
        return jsonify({'error': 'Rate limit exceeded', 'message': 'Too many requests'}), 429
    
    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"内部服务器错误: {error}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error', 'message': 'Something went wrong'}), 500
    
    @app.errorhandler(Exception)
    def handle_exception(error):
        logger.error(f"未处理的异常: {error}")
        return jsonify({'error': 'Unexpected error', 'message': 'An unexpected error occurred'}), 500

def register_hooks(app):
    """注册钩子函数"""
    
    @app.before_request
    def before_request():
        """请求前处理"""
        # 记录请求日志
        from flask import request
        logger.debug(f"请求: {request.method} {request.url}")
    
    @app.after_request
    def after_request(response):
        """请求后处理"""
        # 添加安全头
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        # CORS头（如果需要）
        if app.config.get('CORS_ORIGINS'):
            origins = app.config['CORS_ORIGINS']
            if '*' in origins:
                response.headers['Access-Control-Allow-Origin'] = '*'
            else:
                response.headers['Access-Control-Allow-Origin'] = ','.join(origins)
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        
        return response
    
    @app.teardown_appcontext
    def close_db(error):
        """清理数据库连接"""
        if error:
            db.session.rollback()
        db.session.remove()

def start_background_services(app):
    """启动后台服务"""
    try:
        if app.config.get('PAYMENT_MONITOR_ENABLED', True):
            try:
                from .services.payment_monitor import payment_monitor_service
            except ImportError:
                from services.payment_monitor import payment_monitor_service
            payment_monitor_service.start_monitoring()
            logger.info("支付监控服务已启动")
        
        if app.config.get('SLA_AUTO_MINT_ENABLED', True):
            try:
                from .services.nft_minting import sla_nft_minting_system
            except ImportError:
                from services.nft_minting import sla_nft_minting_system
            sla_nft_minting_system.start_minting_service()
            logger.info("NFT铸造服务已启动")
            
    except Exception as e:
        logger.error(f"启动后台服务失败: {e}")

def stop_background_services():
    """停止后台服务"""
    try:
        try:
            from .services.payment_monitor import payment_monitor_service
            from .services.nft_minting import sla_nft_minting_system
        except ImportError:
            from services.payment_monitor import payment_monitor_service
            from services.nft_minting import sla_nft_minting_system
        
        payment_monitor_service.stop_monitoring()
        sla_nft_minting_system.stop_minting_service()
        
        logger.info("后台服务已停止")
        
    except Exception as e:
        logger.error(f"停止后台服务失败: {e}")

# 创建应用实例
app = create_app()

# 命令行接口
@app.cli.command()
def init_db():
    """初始化数据库"""
    db.create_all()
    print("数据库表已创建")

@app.cli.command()
def reset_db():
    """重置数据库"""
    db.drop_all()
    db.create_all()
    print("数据库已重置")

@app.cli.command()
def test():
    """运行测试"""
    import pytest
    pytest.main(['-v', 'tests/'])

if __name__ == '__main__':
    # 直接运行时的配置
    port = int(os.environ.get('PORT', 5002))
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    
    try:
        app.run(host='0.0.0.0', port=port, debug=debug)
    except KeyboardInterrupt:
        logger.info("接收到停止信号")
        stop_background_services()
    except Exception as e:
        logger.error(f"应用启动失败: {e}")
        stop_background_services()
        raise