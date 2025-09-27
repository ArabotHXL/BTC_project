"""
User Management Module Configuration
用户管理模块配置文件 - 独立的配置管理
"""
import os
import logging
from datetime import timedelta

class Config:
    """基础配置类"""
    # 基本设置 - 使用稳定密钥确保session一致性
    SECRET_KEY = os.environ.get('SESSION_SECRET')
    if not SECRET_KEY:
        # 开发环境使用稳定密钥，避免session在进程重启间丢失
        SECRET_KEY = "dev-user-management-module-stable-key-2025"
        logging.warning("No SESSION_SECRET set. Using stable development key.")
    
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
            'application_name': 'user_management_module'
        }
    }
    
    # Database retry configuration
    DB_MAX_RETRIES = 5
    DB_RETRY_DELAY = 2  # seconds
    DB_CONNECTION_TIMEOUT = 60  # seconds
    
    # 会话配置 - Replit iframe环境修复 (强化版)
    SESSION_COOKIE_SECURE = True   # 必须True以配合SameSite=None（现代浏览器要求）
    SESSION_COOKIE_HTTPONLY = False  # 在iframe环境中禁用以允许JS访问
    SESSION_COOKIE_SAMESITE = 'None'  # 允许跨站点cookie（Replit iframe）
    SESSION_COOKIE_DOMAIN = None  # 允许跨域cookie
    SESSION_COOKIE_PATH = '/'  # 确保cookie作用于整个站点
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)  # 8小时会话，避免频繁重登录
    
    # 强制单worker以解决session一致性问题（开发环境）
    GUNICORN_WORKERS = 1
    
    # 缓存配置
    CACHE_TYPE = 'simple'
    CACHE_DEFAULT_TIMEOUT = 300
    
    # API限制
    API_RATE_LIMIT = '100/hour'
    API_BURST_LIMIT = '20/minute'
    
    # 功能开关 - 用户管理模块
    USER_REGISTRATION_ENABLED = True
    EMAIL_VERIFICATION_ENABLED = True
    PASSWORD_RESET_ENABLED = True
    CRM_ENABLED = True
    BILLING_ENABLED = True
    SUBSCRIPTION_ENABLED = True
    
    # 安全配置 - 用户管理模块
    # CSRF 保护 (使用环境变量或SESSION_SECRET)
    CSRF_ENABLED = True
    CSRF_TOKEN_LIFETIME = 3600  # 1小时
    
    # Content Security Policy (CSP) - 开发环境禁用CSP
    CSP_ENABLED = False
    CSP_DIRECTIVES = {
        'default-src': "'self'",
        'script-src': "'self' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://cdn.replit.com",
        'style-src': "'self' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://fonts.googleapis.com https://cdn.replit.com",
        'font-src': "'self' https://fonts.gstatic.com https://cdn.jsdelivr.net",
        'img-src': "'self' data: https:",
        'connect-src': "'self'",
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
        'USER_OPERATIONS_LIMIT': '200/minute'
    }
    
    # 用户管理配置
    # 默认用户设置
    DEFAULT_USER_ROLE = 'guest'
    DEFAULT_ACCESS_DAYS = 30
    FREE_PLAN_UNLIMITED = True  # 免费计划无时间限制
    
    # 邮箱验证配置
    EMAIL_VERIFICATION_TIMEOUT = 24 * 3600  # 24小时
    
    # 密码策略
    PASSWORD_MIN_LENGTH = 8
    PASSWORD_REQUIRE_UPPERCASE = True
    PASSWORD_REQUIRE_LOWERCASE = True
    PASSWORD_REQUIRE_NUMBERS = True
    PASSWORD_REQUIRE_SPECIAL = True
    
    # CRM配置
    CRM_DEFAULT_CUSTOMER_TYPE = "企业"
    CRM_ACTIVITY_TYPES = ['通话', '邮件', '会议', '演示', '跟进', '其他']
    CRM_LEAD_SOURCES = ['网站', '推荐', '广告', '展会', '电话', '其他']
    
    # 订阅和计费配置
    SUPPORTED_CURRENCIES = ['USD', 'CNY', 'BTC', 'ETH']
    DEFAULT_CURRENCY = 'USD'
    SUBSCRIPTION_PLANS = {
        'free': {'name': '免费版', 'price': 0, 'features': ['基本功能']},
        'basic': {'name': '基础版', 'price': 29, 'features': ['基本功能', 'CRM']},
        'professional': {'name': '专业版', 'price': 99, 'features': ['所有功能', '高级分析']},
        'enterprise': {'name': '企业版', 'price': 299, 'features': ['所有功能', '定制支持']}
    }
    
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
    
    # Replit预览专用配置 - 允许iframe嵌入
    SECURITY_HEADERS = {
        # 移除X-Frame-Options以支持Replit预览窗口
        'X-Content-Type-Options': 'nosniff', 
        'X-XSS-Protection': '1; mode=block',
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
        'Referrer-Policy': 'strict-origin-when-cross-origin',
        'Permissions-Policy': 'geolocation=(), microphone=(), camera=()'
    }
    
    # 开发环境CSP - 禁用CSP以避免所有问题  
    CSP_ENABLED = False
    
    # 开发环境允许更宽松的密码策略
    PASSWORD_MIN_LENGTH = 6
    PASSWORD_REQUIRE_UPPERCASE = False
    PASSWORD_REQUIRE_LOWERCASE = False
    PASSWORD_REQUIRE_NUMBERS = False
    PASSWORD_REQUIRE_SPECIAL = False

class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True
    TEMPLATES_AUTO_RELOAD = False
    EXPLAIN_TEMPLATE_LOADING = False
    
    # 生产环境强制要求SESSION_SECRET - 安全关键
    SECRET_KEY = os.environ.get('SESSION_SECRET')
    if not SECRET_KEY:
        raise ValueError("Production requires SESSION_SECRET environment variable - security critical")
    
    # Production-specific logging
    LOG_LEVEL = 'WARNING'  # More restrictive logging in production
    
    # Enhanced session security for production
    SESSION_COOKIE_DOMAIN = None  # Use default domain handling
    SESSION_COOKIE_PATH = '/'
    
    # Strict CSP for production - SECURE DIRECTIVES ONLY
    CSP_DIRECTIVES = {
        'default-src': "'self'",
        'script-src': "'self' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://cdn.replit.com",
        'style-src': "'self' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://fonts.googleapis.com https://cdn.replit.com",
        'font-src': "'self' https://fonts.gstatic.com https://cdn.jsdelivr.net",
        'img-src': "'self' data: https:",
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