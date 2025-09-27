"""
挖矿核心模块 - 主Flask应用
Mining Core Module - Main Flask Application

独立的Flask应用，专注于挖矿计算和数据分析
"""
import os
import logging
from flask import Flask, render_template, jsonify, request
# CORS support removed for simpler deployment
from werkzeug.middleware.proxy_fix import ProxyFix

# 导入配置和模型
from config import get_config
from models import db

def create_app(config_name=None):
    """应用工厂函数"""
    app = Flask(__name__, 
                static_folder='static', 
                static_url_path='/static',
                template_folder='templates')
    
    # 加载配置
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    config_class = get_config()
    app.config.from_object(config_class)
    
    # 初始化配置
    config_class.init_app(app)
    
    # 配置WSGI中间件
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
    
    # 初始化扩展
    db.init_app(app)
    
    # 配置CORS (简化版本，无需额外依赖)
    @app.after_request
    def after_request(response):
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
        return response
    
    # 注册蓝图
    register_blueprints(app)
    
    # 注册错误处理器
    register_error_handlers(app)
    
    # 创建数据库表
    with app.app_context():
        db.create_all()
        
        # 初始化示例数据
        initialize_sample_data()
    
    # 配置日志
    configure_logging(app)
    
    return app

def register_blueprints(app):
    """注册蓝图"""
    try:
        # 注册主路由
        from routes.calculator import calculator_bp
        from routes.analytics import analytics_bp
        from routes.batch import batch_bp
        
        app.register_blueprint(calculator_bp, url_prefix='/calculator')
        app.register_blueprint(analytics_bp, url_prefix='/analytics')
        app.register_blueprint(batch_bp, url_prefix='/batch')
        
        # 注册模块蓝图
        from modules.calculator import calculator_bp as calc_module_bp
        from modules.analytics.routes import analytics_bp as analytics_module_bp
        
        app.register_blueprint(calc_module_bp, url_prefix='/modules/calculator')
        app.register_blueprint(analytics_module_bp, url_prefix='/modules/analytics')
        
        logging.info("所有蓝图注册成功")
        
    except ImportError as e:
        logging.warning(f"部分蓝图注册失败: {e}")

def register_error_handlers(app):
    """注册错误处理器"""
    
    @app.errorhandler(404)
    def not_found(error):
        if request.is_json:
            return jsonify({'error': 'Not Found', 'message': '请求的资源不存在'}), 404
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        logging.error(f"Internal server error: {error}")
        if request.is_json:
            return jsonify({'error': 'Internal Server Error', 'message': '服务器内部错误'}), 500
        return render_template('errors/500.html'), 500
    
    @app.errorhandler(400)
    def bad_request(error):
        if request.is_json:
            return jsonify({'error': 'Bad Request', 'message': '请求参数错误'}), 400
        return render_template('errors/400.html'), 400

def configure_logging(app):
    """配置日志"""
    if not app.debug and not app.testing:
        # 生产环境日志配置
        if not os.path.exists('logs'):
            os.mkdir('logs')
        
        file_handler = logging.FileHandler('logs/mining_core.log')
        file_handler.setFormatter(logging.Formatter(app.config['LOG_FORMAT']))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        
        app.logger.setLevel(logging.INFO)
        app.logger.info('Mining Core Module startup')

def initialize_sample_data():
    """初始化示例数据"""
    try:
        from models import MinerModel, NetworkSnapshot
        
        # 检查是否已有数据
        if MinerModel.query.first() is None:
            # 添加示例矿机数据
            sample_miners = [
                {
                    'model_name': 'Antminer S19 Pro',
                    'manufacturer': 'Bitmain',
                    'reference_hashrate': 110.0,
                    'reference_power': 3250,
                    'reference_price': 2500.0,
                    'chip_type': 'BM1397',
                    'is_active': True
                },
                {
                    'model_name': 'WhatsMiner M30S++',
                    'manufacturer': 'MicroBT',
                    'reference_hashrate': 112.0,
                    'reference_power': 3472,
                    'reference_price': 2800.0,
                    'chip_type': 'BM1391',
                    'is_active': True
                },
                {
                    'model_name': 'Antminer S21',
                    'manufacturer': 'Bitmain',
                    'reference_hashrate': 200.0,
                    'reference_power': 3550,
                    'reference_price': 4500.0,
                    'chip_type': 'BM1570',
                    'is_active': True
                }
            ]
            
            for miner_data in sample_miners:
                miner = MinerModel(**miner_data)
                db.session.add(miner)
            
            # 添加示例网络快照数据
            network_snapshot = NetworkSnapshot(
                btc_price=43000.0,
                network_difficulty=83148355189239.0,
                network_hashrate=650.0,
                block_reward=3.125
            )
            db.session.add(network_snapshot)
            
            db.session.commit()
            logging.info("示例数据初始化完成")
            
    except Exception as e:
        logging.error(f"示例数据初始化失败: {e}")
        db.session.rollback()


if __name__ == '__main__':
    # 开发环境直接运行
    app.run(
        host=app.config.get('HOST', '0.0.0.0'),
        port=app.config.get('PORT', 5001),
        debug=app.config.get('DEBUG', True)
    )