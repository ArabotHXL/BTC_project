"""
User Management Module - Flask Application
用户管理模块主应用文件 - 独立的Flask应用
"""

import os
import logging
from flask import Flask, render_template, session, request
from werkzeug.middleware.proxy_fix import ProxyFix

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_app():
    """创建Flask应用实例"""
    app = Flask(__name__, 
                static_folder='static', 
                static_url_path='/static',
                template_folder='templates')
    
    # 加载配置
    try:
        try:
            from .config import get_config
        except ImportError:
            from config import get_config
        config_class = get_config()
        app.config.from_object(config_class)
        
        # 设置密钥 - 遵循Flask开发指南
        app.secret_key = os.environ.get("SESSION_SECRET") or app.config.get('SECRET_KEY')
        if not app.secret_key:
            raise ValueError("CRITICAL SECURITY ERROR: SESSION_SECRET environment variable must be set")
        
        logger.info("Configuration loaded for user management module")
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        # 应急配置
        app.secret_key = os.environ.get("SESSION_SECRET")
        if not app.secret_key:
            raise ValueError("CRITICAL SECURITY ERROR: SESSION_SECRET must be set")
    
    # 配置代理支持 - 遵循Flask开发指南
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
    
    # 初始化数据库
    try:
        from .database import init_database, create_tables
    except ImportError:
        from database import init_database, create_tables
    db = init_database(app)
    
    # 创建数据库表
    with app.app_context():
        try:
            create_tables(app)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Error creating database tables: {e}")
    
    # Cookie分区中间件 - 支持iframe环境
    class CookiePartitionMiddleware:
        def __init__(self, app, session_cookie_name):
            self.app = app
            self.session_cookie_name = session_cookie_name

        def __call__(self, environ, start_response):
            def _start_response(status, headers, exc_info=None):
                new_headers = []
                for k, v in headers:
                    if k.lower() == 'set-cookie' and v.startswith(f"{self.session_cookie_name}="):
                        # 强化iframe兼容性 - 确保所有必要属性
                        if 'SameSite=None' in v and 'Secure' in v:
                            # 添加Partitioned属性用于Chrome CHIPS
                            if 'Partitioned' not in v:
                                v = v + '; Partitioned'
                            # 确保路径正确
                            if 'Path=/' not in v:
                                v = v + '; Path=/'
                    new_headers.append((k, v))
                return start_response(status, new_headers, exc_info)
            return self.app(environ, _start_response)

    # 应用Cookie中间件
    app.wsgi_app = CookiePartitionMiddleware(app.wsgi_app, app.config.get('SESSION_COOKIE_NAME', 'session'))
    
    # 注册蓝图
    try:
        from .routes import register_routes
    except ImportError:
        from routes import register_routes
    register_routes(app)
    
    # 注册错误处理器
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html', title='页面未找到'), 404

    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal server error: {error}")
        return render_template('errors/500.html', title='服务器错误'), 500

    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template('errors/403.html', title='访问被拒绝'), 403
    
    # 应用安全头
    @app.after_request
    def apply_security_headers(response):
        """应用安全头到所有响应"""
        # 从配置获取安全头
        for header, value in app.config.get('SECURITY_HEADERS', {}).items():
            response.headers[header] = value
        
        # CSP头（如果启用）
        if app.config.get('CSP_ENABLED', False):
            csp_directives = app.config.get('CSP_DIRECTIVES', {})
            if csp_directives:
                csp_header = '; '.join([f"{key} {value}" for key, value in csp_directives.items()])
                response.headers['Content-Security-Policy'] = csp_header
        
        # HTTPS强制（生产环境）
        if os.environ.get('FLASK_ENV') == 'production':
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
        return response
    
    # 上下文处理器 - 为模板提供全局变量
    @app.context_processor
    def inject_global_vars():
        """为所有模板注入全局变量"""
        return {
            'user_role': session.get('role', 'guest'),
            'user_email': session.get('email', ''),
            'user_name': session.get('name', ''),
            'is_authenticated': 'email' in session
        }
    
    # 主页路由
    @app.route('/')
    def index():
        """主页"""
        return render_template('index.html', title='用户管理系统')
    
    # 基本路由 - 用于兼容性
    @app.route('/dashboard')
    def dashboard():
        """主仪表盘 - 重定向到相应的用户界面"""
        if not session.get('authenticated'):
            return redirect(url_for('auth.login'))
        
        user_role = session.get('role', 'guest')
        if user_role in ['owner', 'admin']:
            return redirect(url_for('admin.dashboard'))
        else:
            return redirect(url_for('users.profile'))
    
    # 健康检查端点
    @app.route('/health')
    def health_check():
        """健康检查端点"""
        return {'status': 'healthy', 'module': 'user_management'}, 200
    
    logger.info("User Management Module Flask app created successfully")
    return app

# 为了兼容性，创建应用实例
app = create_app()

if __name__ == '__main__':
    # 开发服务器启动 - 根据任务要求使用端口5003
    app.run(host='0.0.0.0', port=5003, debug=True)