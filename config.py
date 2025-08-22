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
    
    # 会话配置
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    
    # 缓存配置
    CACHE_TYPE = 'simple'
    CACHE_DEFAULT_TIMEOUT = 300
    
    # API限制
    API_RATE_LIMIT = '100/hour'
    API_BURST_LIMIT = '20/minute'
    
    # 功能开关
    ENABLE_BACKGROUND_SERVICES = os.environ.get('ENABLE_BACKGROUND_SERVICES', '0') == '1'
    BILLING_ENABLED = os.environ.get('STRIPE_SECRET_KEY') is not None
    BATCH_CALCULATOR_ENABLED = True
    
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
    SESSION_COOKIE_SECURE = True
    
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