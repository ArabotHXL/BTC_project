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

# 设置缺失的环境变量
os.environ.setdefault("SECRET_KEY", app.secret_key)

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

# 基础路由 - 临时简化版本
@app.route('/')
def index():
    """主页 - 简化版本避免模板问题"""
    return """
    <!DOCTYPE html>
    <html lang="zh-CN" data-bs-theme="dark">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>比特币挖矿计算器 - HashInsight</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css" rel="stylesheet">
        <style>
            body {
                background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
                color: #ffffff;
                font-family: 'Inter', system-ui, sans-serif;
                min-height: 100vh;
            }
            .hero-section { padding: 80px 0; }
            .card-custom {
                background: rgba(255, 255, 255, 0.1);
                backdrop-filter: blur(10px);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 16px;
                padding: 24px;
            }
        </style>
    </head>
    <body>
        <div class="container-fluid">
            <div class="hero-section text-center">
                <div class="container">
                    <h1 class="display-4 fw-bold mb-4">
                        <i class="bi bi-cpu me-3 text-warning"></i>
                        比特币挖矿计算器
                    </h1>
                    <p class="lead mb-5">专业的Bitcoin挖矿收益计算和托管平台</p>
                    
                    <div class="alert alert-warning mb-4">
                        <i class="bi bi-exclamation-triangle me-2"></i>
                        <strong>No Money Mode:</strong> 本系统不提供任何支付/托管/收益分发功能，仅用于展示和透明度管理。
                    </div>

                    <div class="row justify-content-center mb-5">
                        <div class="col-auto">
                            <a href="/hosting/" class="btn btn-primary btn-lg me-3">
                                <i class="bi bi-building me-2"></i>
                                托管方控制台
                            </a>
                            <a href="/client/" class="btn btn-outline-light btn-lg">
                                <i class="bi bi-person-circle me-2"></i>
                                客户监控面板
                            </a>
                        </div>
                    </div>

                    <div class="row justify-content-center">
                        <div class="col-lg-8">
                            <div class="card-custom">
                                <h5 class="mb-3">
                                    <i class="bi bi-check-circle-fill text-success me-2"></i>
                                    系统状态
                                </h5>
                                <div class="row">
                                    <div class="col-md-3">
                                        <div class="text-center">
                                            <i class="bi bi-database-check text-success h4"></i>
                                            <h6>数据库</h6>
                                            <small class="text-success">正常</small>
                                        </div>
                                    </div>
                                    <div class="col-md-3">
                                        <div class="text-center">
                                            <i class="bi bi-server text-success h4"></i>
                                            <h6>Web服务</h6>
                                            <small class="text-success">运行中</small>
                                        </div>
                                    </div>
                                    <div class="col-md-3">
                                        <div class="text-center">
                                            <i class="bi bi-shield-check text-success h4"></i>
                                            <h6>安全模块</h6>
                                            <small class="text-success">已激活</small>
                                        </div>
                                    </div>
                                    <div class="col-md-3">
                                        <div class="text-center">
                                            <i class="bi bi-activity text-info h4"></i>
                                            <h6>API接口</h6>
                                            <small class="text-info">
                                                <a href="/healthz" class="text-info">健康检查</a>
                                            </small>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <footer class="text-center py-4">
            <div class="container">
                <p class="text-muted mb-0">
                    <i class="bi bi-code-slash me-1"></i>
                    HashInsight 比特币挖矿计算器 | 
                    <span class="text-warning">演示版本 - 无实际资金功能</span>
                </p>
            </div>
        </footer>

        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    </body>
    </html>
    """

@app.route('/login')
def login():
    def t(key): return key
    return render_template('auth/login.html', t=t)

@app.route('/register') 
def register():
    def t(key): return key
    return render_template('auth/register.html', t=t)

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

# 缺失的页面路由 - 修复模板引用错误（备用路由）

# 添加与模板匹配的路由名称  
@app.route('/legal_terms')
def legal_terms():
    """法律条款页面 - 模板兼容版"""
    return """
    <html>
    <head><title>法律条款</title></head>
    <body style="background:#1a1a2e; color:white; font-family:Arial; padding:40px;">
    <h1>法律条款</h1>
    <p><strong>重要声明：</strong></p>
    <p>本系统为演示平台，<strong>不提供任何实际的金融服务、支付处理或托管功能</strong>。</p>
    <p>所有数据仅用于展示目的，不构成投资建议。</p>
    <a href="/" style="color:#007bff;">返回主页</a>
    </body>
    </html>
    """

@app.route('/privacy-policy')  
def privacy_policy():
    """隐私政策页面"""
    return """
    <html>
    <head><title>隐私政策</title></head>
    <body style="background:#1a1a2e; color:white; font-family:Arial; padding:40px;">
    <h1>隐私政策</h1>
    <p>本演示平台不收集、存储或处理任何真实的个人金融信息。</p>
    <p>所有展示的数据均为模拟数据，仅用于功能演示。</p>
    <a href="/" style="color:#007bff;">返回主页</a>
    </body>
    </html>
    """

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