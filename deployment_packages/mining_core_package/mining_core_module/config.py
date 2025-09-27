"""
挖矿核心模块配置文件
Mining Core Module Configuration

独立配置，无用户认证依赖
"""
import os
import logging
from datetime import timedelta

class Config:
    """基础配置类"""
    # 基本设置
    SECRET_KEY = os.environ.get('SESSION_SECRET', 'mining-core-dev-key-2025')
    
    # 数据库配置 - 增强版连接参数
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///mining_core.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 5,
        'pool_recycle': 300,  # 5 minutes
        'pool_pre_ping': True,  # Test connections before use
        'pool_timeout': 30,     # Wait up to 30 seconds for connection from pool
        'max_overflow': 10,     # Allow up to 10 connections beyond pool_size
        'connect_args': {
            'connect_timeout': 15,
            'application_name': 'mining_core_module'
        }
    }
    
    # 应用配置
    DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'
    TESTING = False
    
    # 服务器配置
    HOST = '0.0.0.0'
    PORT = int(os.environ.get('PORT', 5001))  # 默认端口5001，避免与主应用冲突
    
    # API配置
    API_TIMEOUT = 30
    API_RETRY_COUNT = 3
    API_RATE_LIMIT = 60  # 每分钟最大请求数
    
    # 挖矿计算默认值
    DEFAULT_ELECTRICITY_COST = 0.06  # $/kWh
    DEFAULT_POOL_FEE = 0.025  # 2.5%
    DEFAULT_BLOCK_REWARD = 3.125  # BTC
    BLOCKS_PER_DAY = 144
    
    # CoinWarz API配置
    COINWARZ_API_KEY = os.environ.get('COINWARZ_API_KEY', '')
    COINWARZ_BASE_URL = "https://www.coinwarz.com/v1/api"
    
    # Bitcoin RPC配置
    BITCOIN_RPC_URL = os.environ.get('BITCOIN_RPC_URL', 'https://go.getblock.io/mainnet')
    BITCOIN_RPC_USER = os.environ.get('BITCOIN_RPC_USER', '')
    BITCOIN_RPC_PASSWORD = os.environ.get('BITCOIN_RPC_PASSWORD', '')
    
    # 数据收集配置
    DATA_COLLECTION_INTERVAL = 300  # 5分钟
    HISTORICAL_DATA_DAYS = 365  # 历史数据天数
    
    # 缓存配置
    CACHE_TYPE = 'simple'
    CACHE_DEFAULT_TIMEOUT = 300  # 5分钟
    
    # 日志配置
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO').upper()
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # 安全配置（简化版，无用户认证）
    WTF_CSRF_ENABLED = False  # 禁用CSRF，因为是独立API模块
    
    # 批量计算配置
    MAX_BATCH_SIZE = 1000  # 最大批量计算数量
    BATCH_TIMEOUT = 300  # 批量计算超时时间
    
    # 文件上传配置
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    UPLOAD_FOLDER = 'uploads'
    ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls'}
    
    # CORS配置（允许跨域访问）
    CORS_ORIGINS = ["*"]  # 开发环境允许所有来源
    
    @staticmethod
    def init_app(app):
        """初始化应用配置"""
        # 配置日志
        logging.basicConfig(
            level=getattr(logging, Config.LOG_LEVEL),
            format=Config.LOG_FORMAT
        )
        
        # 创建上传目录
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)

class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True
    
    # 开发环境使用SQLite
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///mining_core_dev.db')
    
    # 开发环境日志级别
    LOG_LEVEL = 'DEBUG'

class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False
    
    # 生产环境必须使用环境变量中的数据库URL
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    
    if not SQLALCHEMY_DATABASE_URI:
        raise ValueError("生产环境必须设置DATABASE_URL环境变量")
    
    # 生产环境安全配置
    SECRET_KEY = os.environ.get('SESSION_SECRET')
    if not SECRET_KEY:
        raise ValueError("生产环境必须设置SESSION_SECRET环境变量")
    
    # 生产环境CORS配置更严格
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '').split(',')
    
    # 生产环境日志级别
    LOG_LEVEL = 'WARNING'

class TestingConfig(Config):
    """测试环境配置"""
    TESTING = True
    DEBUG = True
    
    # 测试环境使用内存数据库
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    
    # 测试环境禁用CSRF
    WTF_CSRF_ENABLED = False

# 配置字典
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

def get_config():
    """获取当前环境配置"""
    env = os.environ.get('FLASK_ENV', 'development')
    return config.get(env, config['default'])