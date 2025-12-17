"""
系统配置文件 - 集中管理所有配置
"""
import os
import logging
from datetime import timedelta

class Config:
    """基础配置类 - 仅用于开发环境 (DevelopmentConfig继承此类)
    
    ⚠️ SECURITY WARNING: 此类包含开发环境fallback值
    生产环境必须使用ProductionConfig，它会强制要求所有安全配置
    """
    # 基本设置 - 使用稳定密钥确保session一致性
    SECRET_KEY = os.environ.get('SESSION_SECRET')
    if not SECRET_KEY:
        # ⚠️ SECURITY: 仅限开发环境使用的fallback密钥
        # 生产环境必须设置SESSION_SECRET环境变量
        # ProductionConfig会在缺少SESSION_SECRET时抛出错误
        SECRET_KEY = "dev-bitcoin-mining-platform-stable-key-2025"
        logging.warning("⚠️ SECURITY: No SESSION_SECRET set. Using INSECURE development key. DO NOT use in production!")
    
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
    
    # 会话配置 - Replit iframe环境修复 (强化版)
    SESSION_COOKIE_SECURE = True   # 🔧 必须True以配合SameSite=None（现代浏览器要求）
    SESSION_COOKIE_HTTPONLY = True  # 🔐 安全: 防止XSS攻击窃取session cookie
    SESSION_COOKIE_SAMESITE = 'None'  # 🔧 允许跨站点cookie（Replit iframe）
    SESSION_COOKIE_DOMAIN = None  # 🔧 允许跨域cookie
    SESSION_COOKIE_PATH = '/'  # 🔧 确保cookie作用于整个站点
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)  # 8小时会话，避免频繁重登录
    
    # 🔧 强制单worker以解决session一致性问题（开发环境）
    GUNICORN_WORKERS = 1
    
    # 缓存配置
    CACHE_TYPE = 'simple'
    CACHE_DEFAULT_TIMEOUT = 300
    
    # API限制
    API_RATE_LIMIT = '100/hour'
    API_BURST_LIMIT = '20/minute'
    
    # 功能开关 - 托管透明性平台
    ENABLE_BACKGROUND_SERVICES = os.environ.get('ENABLE_BACKGROUND_SERVICES', '0') == '1'
    USAGE_TRACKING_ENABLED = False  # DISABLED: Gold flow module - hosting transparency only
    MINING_BROKER_ENABLED = False  # DISABLED: Gold flow module
    SUBSCRIPTION_ENABLED = True  # ENABLED: 启用订阅系统支持加密货币支付
    BATCH_CALCULATOR_ENABLED = True
    
    # 启用加密货币支付处理
    PAYMENT_PROCESSING_DISABLED = False  # ENABLED: 支持加密货币支付
    CRYPTO_PAYMENT_ENABLED = True  # 新增：启用加密货币支付
    
    # 加密货币支付配置
    SUPPORTED_CRYPTOCURRENCIES = ['BTC', 'ETH', 'USDC']
    CRYPTO_NETWORKS = {
        'BTC': 'bitcoin',
        'ETH': 'ethereum',
        'USDC': 'ethereum'  # USDC运行在以太坊网络
    }
    
    # 安全配置 - 托管透明性平台
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
    
    # API密钥 - 托管透明性平台
    # 托管透明性平台 - 不处理任何支付功能
    COINWARZ_API_KEY = os.environ.get('COINWARZ_API_KEY')
    
    # 挖矿计算常量配置 - 外置硬编码值
    DEFAULT_ELECTRICITY_COST = 0.06  # 默认电费单价 USD/kWh
    DEFAULT_HASHRATE_EH = 900  # 默认网络算力，单位: EH/s
    DEFAULT_BTC_PRICE = 80000  # 默认比特币价格，单位: USD
    DEFAULT_DIFFICULTY = 119.12  # 默认难度，单位: T
    DEFAULT_BLOCK_REWARD = 3.125  # 默认区块奖励，单位: BTC
    
    # 托管相关默认配置
    DEFAULT_HOSTING_ELECTRICITY_RATE = 0.05  # 托管默认电费率 USD/kWh
    
    # 安全配置常量
    HSTS_MAX_AGE = 31536000  # HSTS持续时间（1年）
    
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
    
    # Enable CSP in production for Device Envelope Encryption security
    CSP_ENABLED = True
    
    # Strict CSP for production - SECURE DIRECTIVES ONLY
    # Added 'wasm-unsafe-eval' for libsodium WebAssembly support (device envelope encryption)
    CSP_DIRECTIVES = {
        'default-src': "'self'",
        'script-src': "'self' 'wasm-unsafe-eval' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://cdn.replit.com",
        'style-src': "'self' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://fonts.googleapis.com https://cdn.replit.com",
        'font-src': "'self' https://fonts.gstatic.com https://cdn.jsdelivr.net",
        'img-src': "'self' data: https:",
        'connect-src': "'self' https://api.coingecko.com https://mempool.space https://blockchain.info",
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