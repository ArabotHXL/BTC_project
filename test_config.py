"""
测试配置文件
"""
import os
import logging
from datetime import timedelta

class TestConfig:
    """测试环境配置"""
    # 基本设置
    SECRET_KEY = 'test-secret-key-for-testing'
    TESTING = True
    
    # 简化的SQLite数据库配置
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # 移除SQLite不支持的连接池参数
    SQLALCHEMY_ENGINE_OPTIONS = {}
    
    # 会话配置
    SESSION_COOKIE_SECURE = False  # 测试环境不需要HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    
    # 禁用后台服务
    ENABLE_BACKGROUND_SERVICES = False
    BILLING_ENABLED = False
    BATCH_CALCULATOR_ENABLED = True
    
    # 日志级别
    LOG_LEVEL = 'ERROR'  # 测试时减少日志输出
    
    # API密钥（测试用）
    COINWARZ_API_KEY = 'test-api-key'