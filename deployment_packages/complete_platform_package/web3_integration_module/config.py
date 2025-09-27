"""
Web3集成模块配置
Configuration for Web3 Integration Module
"""

import os
from datetime import timedelta

class Config:
    """基础配置类"""
    
    # Flask基础配置
    SECRET_KEY = os.environ.get('SESSION_SECRET') or 'dev-secret-change-in-production'
    DEBUG = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    
    # 数据库配置
    DATABASE_URL = os.environ.get('DATABASE_URL') or 'postgresql://localhost/web3_integration'
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # 会话配置
    SESSION_TIMEOUT = timedelta(hours=24)
    PERMANENT_SESSION_LIFETIME = SESSION_TIMEOUT
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'false').lower() == 'true'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Web3和区块链配置
    BLOCKCHAIN_ENABLE_MAINNET_WRITES = os.environ.get('BLOCKCHAIN_ENABLE_MAINNET_WRITES', 'false').lower() == 'true'
    BLOCKCHAIN_PRIVATE_KEY = os.environ.get('BLOCKCHAIN_PRIVATE_KEY')
    BLOCKCHAIN_DISABLE_IPFS = os.environ.get('BLOCKCHAIN_DISABLE_IPFS', 'false').lower() == 'true'
    
    # 网络RPC配置
    BASE_MAINNET_RPC = os.environ.get('BASE_MAINNET_RPC', 'https://mainnet.base.org')
    BASE_TESTNET_RPC = os.environ.get('BASE_TESTNET_RPC', 'https://sepolia.base.org')
    ETH_MAINNET_RPC = os.environ.get('ETH_MAINNET_RPC')
    ETH_TESTNET_RPC = os.environ.get('ETH_TESTNET_RPC')
    BTC_RPC_URL = os.environ.get('BTC_RPC_URL')
    
    # 合约地址
    MINING_REGISTRY_CONTRACT_ADDRESS = os.environ.get('MINING_REGISTRY_CONTRACT_ADDRESS')
    SLA_NFT_CONTRACT_ADDRESS = os.environ.get('SLA_NFT_CONTRACT_ADDRESS')
    
    # 钱包地址
    BTC_WALLET_ADDRESS = os.environ.get('BTC_WALLET_ADDRESS')
    ETH_WALLET_ADDRESS = os.environ.get('ETH_WALLET_ADDRESS')
    USDC_WALLET_ADDRESS = os.environ.get('USDC_WALLET_ADDRESS')
    
    # IPFS/Pinata配置
    PINATA_JWT = os.environ.get('PINATA_JWT')
    PINATA_API_URL = os.environ.get('PINATA_API_URL', 'https://api.pinata.cloud')
    
    # 加密配置
    ENCRYPTION_PASSWORD = os.environ.get('ENCRYPTION_PASSWORD')
    ENCRYPTION_SALT = os.environ.get('ENCRYPTION_SALT')
    
    # HD钱包配置
    HD_WALLET_MNEMONIC = os.environ.get('HD_WALLET_MNEMONIC')
    
    # 外部API密钥
    ETHERSCAN_API_KEY = os.environ.get('ETHERSCAN_API_KEY')
    AML_API_KEY = os.environ.get('AML_API_KEY')
    AML_API_URL = os.environ.get('AML_API_URL', 'https://api.chainalysis.com')
    
    # 合规配置
    AML_CHECKS_ENABLED = os.environ.get('AML_CHECKS_ENABLED', 'true').lower() == 'true'
    KYC_CHECKS_ENABLED = os.environ.get('KYC_CHECKS_ENABLED', 'true').lower() == 'true'
    AUDIT_LOGGING_ENABLED = os.environ.get('AUDIT_LOGGING_ENABLED', 'true').lower() == 'true'
    
    # 风险阈值
    MAX_DAILY_AMOUNT = float(os.environ.get('MAX_DAILY_AMOUNT', '10000'))
    MAX_MONTHLY_AMOUNT = float(os.environ.get('MAX_MONTHLY_AMOUNT', '50000'))
    MIN_AGE_REQUIREMENT = int(os.environ.get('MIN_AGE_REQUIREMENT', '18'))
    HIGH_RISK_THRESHOLD = float(os.environ.get('HIGH_RISK_THRESHOLD', '0.7'))
    SUSPICIOUS_COUNTRIES = os.environ.get('SUSPICIOUS_COUNTRIES', '').split(',') if os.environ.get('SUSPICIOUS_COUNTRIES') else []
    
    # NFT铸造配置
    SLA_AUTO_MINT_ENABLED = os.environ.get('SLA_AUTO_MINT_ENABLED', 'true').lower() == 'true'
    SLA_MINT_DAY = int(os.environ.get('SLA_MINT_DAY', '3'))
    SLA_MINT_HOUR = int(os.environ.get('SLA_MINT_HOUR', '8'))
    SLA_MINT_RETRY_ATTEMPTS = int(os.environ.get('SLA_MINT_RETRY_ATTEMPTS', '3'))
    SLA_MINT_RETRY_INTERVAL = int(os.environ.get('SLA_MINT_RETRY_INTERVAL', '3600'))
    SLA_MINT_BATCH_SIZE = int(os.environ.get('SLA_MINT_BATCH_SIZE', '10'))
    SLA_MINT_GAS_LIMIT = int(os.environ.get('SLA_MINT_GAS_LIMIT', '500000'))
    SLA_MINT_GAS_PRICE_MULTIPLIER = float(os.environ.get('SLA_MINT_GAS_PRICE_MULTIPLIER', '1.2'))
    
    # 支付监控配置
    PAYMENT_MONITOR_ENABLED = os.environ.get('PAYMENT_MONITOR_ENABLED', 'true').lower() == 'true'
    PAYMENT_MONITOR_INTERVAL = int(os.environ.get('PAYMENT_MONITOR_INTERVAL', '30'))
    PAYMENT_TIMEOUT_HOURS = int(os.environ.get('PAYMENT_TIMEOUT_HOURS', '24'))
    
    # 服务器配置
    HOST = os.environ.get('HOST', '0.0.0.0')
    PORT = int(os.environ.get('PORT', '5002'))
    
    # 日志配置
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = os.environ.get('LOG_FILE', 'web3_integration.log')
    
    # CORS配置
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*').split(',')
    
    # 限流配置
    RATELIMIT_DEFAULT = os.environ.get('RATELIMIT_DEFAULT', '100 per hour')
    RATELIMIT_STORAGE_URL = os.environ.get('RATELIMIT_STORAGE_URL', 'memory://')

class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True
    BLOCKCHAIN_ENABLE_MAINNET_WRITES = False
    SESSION_COOKIE_SECURE = False
    LOG_LEVEL = 'DEBUG'

class TestingConfig(Config):
    """测试环境配置"""
    TESTING = True
    BLOCKCHAIN_ENABLE_MAINNET_WRITES = False
    DATABASE_URL = os.environ.get('TEST_DATABASE_URL') or 'postgresql://localhost/web3_integration_test'
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    WTF_CSRF_ENABLED = False
    AML_CHECKS_ENABLED = False
    KYC_CHECKS_ENABLED = False

class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    LOG_LEVEL = 'INFO'
    
    # 生产环境安全检查
    @classmethod
    def validate_production_config(cls):
        """验证生产环境配置"""
        required_vars = [
            'SECRET_KEY',
            'DATABASE_URL',
            'ENCRYPTION_PASSWORD',
            'ENCRYPTION_SALT',
            'PINATA_JWT'
        ]
        
        missing_vars = [var for var in required_vars if not os.environ.get(var)]
        
        if missing_vars:
            raise ValueError(
                f"生产环境缺少必需的环境变量: {', '.join(missing_vars)}"
            )
        
        # 检查密钥强度
        secret_key = os.environ.get('SECRET_KEY', '')
        if len(secret_key) < 32:
            raise ValueError("SECRET_KEY长度必须至少32个字符")
        
        encryption_password = os.environ.get('ENCRYPTION_PASSWORD', '')
        if len(encryption_password) < 16:
            raise ValueError("ENCRYPTION_PASSWORD长度必须至少16个字符")

# 配置字典
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

def get_config():
    """获取当前配置"""
    env = os.environ.get('FLASK_ENV', 'development')
    return config.get(env, config['default'])