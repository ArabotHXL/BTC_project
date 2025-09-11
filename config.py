"""
系统配置文件 - 集中管理所有配置
"""
import os
import logging
from datetime import timedelta

class Config:
    """基础配置类"""
    # 基本设置 - 生产环境必须设置
    SECRET_KEY = os.environ.get('SESSION_SECRET')
    if not SECRET_KEY:
        import secrets
        SECRET_KEY = secrets.token_hex(32)
        logging.warning("No SESSION_SECRET set. Generated random key for this session.")
    
    # 数据库配置 - 增强版连接参数
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'pool_recycle': 300,  # 5 minutes
        'pool_pre_ping': True,  # Test connections before use
        'pool_timeout': 30,     # Wait up to 30 seconds for connection from pool
        'max_overflow': 20,     # Allow up to 20 connections beyond pool_size
        'connect_args': {
            'connect_timeout': 15,  # Increased timeout for Neon
            'application_name': 'btc_mining_calculator'
        }
    }
    
    # Database retry configuration
    DB_MAX_RETRIES = 5
    DB_RETRY_DELAY = 2  # seconds
    DB_CONNECTION_TIMEOUT = 60  # seconds
    
    # 会话配置 - 托管透明性平台安全设置
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)  # 2小时安全会话
    
    # 缓存配置
    CACHE_TYPE = 'simple'
    CACHE_DEFAULT_TIMEOUT = 300
    
    # API限制
    API_RATE_LIMIT = '100/hour'
    API_BURST_LIMIT = '20/minute'
    
    # 功能开关
    ENABLE_BACKGROUND_SERVICES = os.environ.get('ENABLE_BACKGROUND_SERVICES', '0') == '1'
    BILLING_ENABLED = False  # DISABLED: Gold flow module - was: os.environ.get('STRIPE_SECRET_KEY') is not None
    MINING_BROKER_ENABLED = False  # DISABLED: Gold flow module
    SUBSCRIPTION_ENABLED = False  # DISABLED: Gold flow module
    BATCH_CALCULATOR_ENABLED = True
    
    # 安全配置 - 托管透明性平台
    # CSRF 保护 (使用环境变量或SESSION_SECRET)
    CSRF_ENABLED = True
    CSRF_TOKEN_LIFETIME = 3600  # 1小时
    
    # Content Security Policy (CSP) - 生产级严格策略
    CSP_ENABLED = True
    CSP_DIRECTIVES = {
        'default-src': "'self'",
        'script-src': "'self' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com",
        'style-src': "'self' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://fonts.googleapis.com",
        'font-src': "'self' https://fonts.gstatic.com https://cdn.jsdelivr.net",
        'img-src': "'self' data: https:",
        'connect-src': "'self' https://api.coingecko.com https://mempool.space https://blockchain.info",
        'frame-src': "'none'",
        'object-src': "'none'",
        'base-uri': "'self'",
        'form-action': "'self'"
    }
    
    # 安全头配置
    SECURITY_HEADERS = {
        'X-Frame-Options': 'DENY',
        'X-Content-Type-Options': 'nosniff', 
        'X-XSS-Protection': '1; mode=block',
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
        'Referrer-Policy': 'strict-origin-when-cross-origin',
        'Permissions-Policy': 'geolocation=(), microphone=(), camera=()'
    }
    
    # 速率限制配置
    RATE_LIMITING = {
        'ENABLED': True,
        'GLOBAL_RATE_LIMIT': '1000/hour',
        'LOGIN_RATE_LIMIT': '10/minute',
        'API_RATE_LIMIT': '100/minute',
        'HOSTING_DATA_LIMIT': '200/minute'
    }
    
    # API密钥
    STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY')
    COINWARZ_API_KEY = os.environ.get('COINWARZ_API_KEY')
    
    # 日志配置
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # 性能优化
    SEND_FILE_MAX_AGE_DEFAULT = 31536000  # 静态文件缓存1年
    TEMPLATES_AUTO_RELOAD = False
    
class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True
    TEMPLATES_AUTO_RELOAD = True
    
class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True
    TEMPLATES_AUTO_RELOAD = False
    EXPLAIN_TEMPLATE_LOADING = False
    
    # Production-specific logging
    LOG_LEVEL = 'WARNING'  # More restrictive logging in production
    
    # Enhanced session security for production
    SESSION_COOKIE_DOMAIN = None  # Use default domain handling
    SESSION_COOKIE_PATH = '/'
    
    # Strict CSP for production
    CSP_DIRECTIVES = {
        'default-src': "'self'",
        'script-src': "'self'",  # More restrictive - remove CDN if not needed
        'style-src': "'self' 'unsafe-inline'",  # Inline styles only if necessary
        'font-src': "'self'",
        'img-src': "'self' data:",
        'connect-src': "'self'",
        'frame-src': "'none'",
        'object-src': "'none'",
        'base-uri': "'self'",
        'form-action': "'self'",
        'upgrade-insecure-requests': ""
    }
    
# 根据环境变量选择配置
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

def get_config():
    """获取当前环境配置"""
    env = os.environ.get('FLASK_ENV', 'development')
    return config.get(env, config['default'])