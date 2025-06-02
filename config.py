"""应用配置管理"""
import os
import secrets

class Config:
    """基础配置类"""
    SECRET_KEY = os.environ.get("SESSION_SECRET", secrets.token_hex(32))
    DATABASE_URL = os.environ.get("DATABASE_URL")
    
    # 默认网络参数
    DEFAULT_HASHRATE_EH = 900  # 默认哈希率，单位: EH/s
    DEFAULT_BTC_PRICE = 80000  # 默认比特币价格，单位: USD
    DEFAULT_DIFFICULTY = 119.12  # 默认难度，单位: T
    DEFAULT_BLOCK_REWARD = 3.125  # 默认区块奖励，单位: BTC
    
    # 数据库配置
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }
    
    # 日志配置
    LOG_LEVEL = "DEBUG"