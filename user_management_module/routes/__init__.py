"""
Routes Package
路由包 - 包含所有用户管理相关的路由
"""

import sys
import os

# Add current directory to path for imports
current_dir = os.path.dirname(__file__)
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

try:
    from .admin import admin_bp
    from .users import users_bp 
    from .crm import crm_bp
    from .billing import billing_bp
    from .auth import auth_bp
except ImportError:
    try:
        from routes.admin import admin_bp
        from routes.users import users_bp 
        from routes.crm import crm_bp
        from routes.billing import billing_bp
        from routes.auth import auth_bp
    except ImportError:
        from admin import admin_bp
        from users import users_bp 
        from crm import crm_bp
        from billing import billing_bp
        from auth import auth_bp

# 导出所有蓝图
__all__ = ['admin_bp', 'users_bp', 'crm_bp', 'billing_bp', 'auth_bp']

def register_routes(app):
    """注册所有路由蓝图"""
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(users_bp, url_prefix='/users')
    app.register_blueprint(crm_bp, url_prefix='/crm')
    app.register_blueprint(billing_bp, url_prefix='/billing')