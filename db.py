# 标准库导入
import os
import logging

# 第三方库导入
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

# 配置日志
logging.basicConfig(level=logging.DEBUG)

# 初始化数据库
class Base(DeclarativeBase):
    pass

# 创建数据库实例
db = SQLAlchemy(model_class=Base)

def init_db(app):
    """初始化数据库连接"""
    # 配置数据库连接
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }

    # 初始化应用
    db.init_app(app)

    # 创建表
    with app.app_context():
        # 导入模型以便创建表
        # 导入所有模型，确保表创建完整
        import models  # noqa: F401
        
        # 创建所有表
        db.create_all()
        
        logging.info("数据库表初始化完成")