"""
系统配置文件 - 集中管理所有配置
"""
import os
from datetime import timedelta

class Config:
    """基础配置类"""
    # 基本设置
    SECRET_KEY = os.environ.get('SESSION_SECRET') or 'dev-secret-key-change-in-production'
    
    # 数据库配置
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'pool_recycle': 300,
        'pool_pre_ping': True,
        'max_overflow': 20,
        'connect_args': {
            'connect_timeout': 10,
            'application_name': 'btc_mining_calculator'
        }
    }
    
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