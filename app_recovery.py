# 紧急恢复版本的 app.py - Sprint 1 版本
import logging
import os
from datetime import datetime, timedelta
from flask import Flask, jsonify, request, render_template, redirect, url_for, flash, session
from flask_login import LoginManager, login_required, current_user
import sqlite3
import traceback

# 基础配置
logging.basicConfig(level=logging.INFO)

# 创建Flask应用
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "change-me-please")

# 数据库初始化
from db import db
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///hashinsight.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
db.init_app(app)

# 登录管理器
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# 导入模型
with app.app_context():
    try:
        import models
        db.create_all()
        logging.info("数据库表创建完成")
    except Exception as e:
        logging.error(f"数据库初始化失败: {e}")

# 用户加载器
@login_manager.user_loader
def load_user(user_id):
    from models import UserAccess
    return UserAccess.query.get(int(user_id))

# 基础路由
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
def login():
    return render_template('auth/login.html')

@app.route('/register') 
def register():
    return render_template('auth/register.html')

# 注册托管模块
try:
    from modules.hosting import hosting_bp
    app.register_blueprint(hosting_bp)
    logging.info("托管功能模块已注册")
except ImportError as e:
    logging.warning(f"托管功能模块不可用: {e}")

# 注册客户模块
try:
    from modules.client import client_bp
    app.register_blueprint(client_bp)
    logging.info("客户功能模块已注册")
except ImportError as e:
    logging.warning(f"客户功能模块不可用: {e}")

# 注册健康检查端点 (Sprint 1 要求)
try:
    from health_check import register_health_check
    register_health_check(app)
    logging.info("健康检查端点已注册")
except ImportError as e:
    logging.warning(f"健康检查模块不可用: {e}")

# 初始化安全中间件 (Sprint 1 安全要求)
try:
    from security_middleware import init_security_middleware
    init_security_middleware(app)
    logging.info("安全中间件已初始化")
except ImportError as e:
    logging.warning(f"安全中间件不可用: {e}")

# Sprint 1 - 演示数据生成API (全局路由)
@app.route('/api/generate-demo-data', methods=['POST'])
@login_required
def generate_demo_data_global():
    """全局演示数据生成接口"""
    try:
        from demo_data_generator import generate_demo_data
        success = generate_demo_data()
        
        if success:
            return jsonify({
                'success': True,
                'message': '演示数据生成成功！包含2个站点、20台矿机和7天历史数据',
                'redirect': '/hosting/'
            })
        else:
            return jsonify({
                'success': False,
                'error': '数据生成失败，请查看日志'
            }), 500
    except Exception as e:
        logging.error(f"生成演示数据失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Sprint 1 - No Money Mode 提醒路由
@app.route('/no-money-mode')
def no_money_mode():
    """No Money Mode 声明页面"""
    return jsonify({
        'status': 'No Money Mode Active',
        'message': '本系统不提供任何支付/托管/收益分发功能，仅用于展示和透明度管理。',
        'features_disabled': [
            '支付处理', '资金托管', '收益分发', 
            '真实交易', '账户余额', '提现功能'
        ],
        'features_enabled': [
            '数据展示', '透明度管理', '系统监控',
            '演示数据', 'API接口', '健康检查'
        ]
    })

# 错误处理
@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('errors/500.html'), 500

@app.errorhandler(403) 
def forbidden_error(error):
    return render_template('errors/403.html'), 403

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)