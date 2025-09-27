"""
Routes Package
路由包 - 包含所有用户管理相关的路由
"""

import sys
import os
import logging

# Add user_management_module to path for absolute imports
module_dir = os.path.dirname(os.path.dirname(__file__))
if module_dir not in sys.path:
    sys.path.insert(0, module_dir)

# Add current directory to path for imports
current_dir = os.path.dirname(__file__)
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

logger = logging.getLogger(__name__)

# Import blueprints with proper error handling and logging
try:
    from admin import admin_bp
    logger.info("Successfully imported admin blueprint")
except ImportError as e:
    logger.error(f"Failed to import admin blueprint: {e}")
    admin_bp = None

try:
    from users import users_bp
    logger.info("Successfully imported users blueprint")
except ImportError as e:
    logger.error(f"Failed to import users blueprint: {e}")
    users_bp = None

try:
    from crm import crm_bp
    logger.info("Successfully imported crm blueprint")
except ImportError as e:
    logger.error(f"Failed to import crm blueprint: {e}")
    crm_bp = None

try:
    from billing import billing_bp
    logger.info("Successfully imported billing blueprint")
except ImportError as e:
    logger.error(f"Failed to import billing blueprint: {e}")
    billing_bp = None

try:
    from auth import auth_bp
    logger.info("Successfully imported auth blueprint")
except ImportError as e:
    logger.error(f"Failed to import auth blueprint: {e}")
    auth_bp = None

# 导出所有蓝图
__all__ = ['admin_bp', 'users_bp', 'crm_bp', 'billing_bp', 'auth_bp']

def register_routes(app):
    """注册所有路由蓝图"""
    registered_count = 0
    
    if auth_bp:
        app.register_blueprint(auth_bp, url_prefix='/auth')
        logger.info("Registered auth blueprint")
        registered_count += 1
    else:
        logger.warning("Auth blueprint not available, skipping registration")
        
    if admin_bp:
        app.register_blueprint(admin_bp, url_prefix='/admin')
        logger.info("Registered admin blueprint")
        registered_count += 1
    else:
        logger.warning("Admin blueprint not available, skipping registration")
        
    if users_bp:
        app.register_blueprint(users_bp, url_prefix='/users')
        logger.info("Registered users blueprint")
        registered_count += 1
    else:
        logger.warning("Users blueprint not available, skipping registration")
        
    if crm_bp:
        app.register_blueprint(crm_bp, url_prefix='/crm')
        logger.info("Registered crm blueprint")
        registered_count += 1
    else:
        logger.warning("CRM blueprint not available, skipping registration")
        
    if billing_bp:
        app.register_blueprint(billing_bp, url_prefix='/billing')
        logger.info("Registered billing blueprint")
        registered_count += 1
    else:
        logger.warning("Billing blueprint not available, skipping registration")
        
    logger.info(f"Successfully registered {registered_count}/5 blueprints")
    
    # If critical blueprints are missing, we might want to fail
    if not auth_bp:
        logger.error("CRITICAL: Auth blueprint failed to load - authentication will not work")
        raise ImportError("Critical auth blueprint could not be loaded")