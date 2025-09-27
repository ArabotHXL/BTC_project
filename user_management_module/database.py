"""
Database Configuration Module
数据库配置模块 - 独立的数据库配置，避免循环导入
"""

import os
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

def init_database(app):
    """初始化数据库"""
    # 配置数据库连接
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }
    
    # 初始化数据库扩展
    db.init_app(app)
    
    return db

def create_tables(app):
    """创建数据库表"""
    with app.app_context():
        # 导入所有模型以确保表被创建
        try:
            from . import models  # noqa: F401
        except ImportError:
            import models  # noqa: F401
        db.create_all()