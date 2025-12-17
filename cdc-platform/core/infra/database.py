"""
HashInsight CDC Platform - Database Infrastructure
SQLAlchemy数据库初始化和连接管理
"""
import os
import logging
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text, event
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import Pool

logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    """SQLAlchemy声明式基类"""
    pass

# 创建全局db实例
db = SQLAlchemy(model_class=Base)

def init_db(app):
    """
    初始化数据库连接
    
    参数:
        app: Flask应用实例
    """
    # 数据库配置
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is required")
    
    # 配置SQLAlchemy
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_size': int(os.getenv('DB_POOL_SIZE', 10)),
        'pool_recycle': int(os.getenv('DB_POOL_RECYCLE', 3600)),
        'pool_pre_ping': True,  # 连接健康检查
        'pool_timeout': 30,
        'max_overflow': int(os.getenv('DB_MAX_OVERFLOW', 20)),
        'echo': os.getenv('SQL_ECHO', 'false').lower() == 'true',  # SQL日志
    }
    
    # 初始化Flask-SQLAlchemy
    db.init_app(app)
    
    # 注册连接池事件监听器
    @event.listens_for(Pool, "connect")
    def set_session_parameters(dbapi_conn, connection_record):
        """
        设置PostgreSQL session参数
        用于Row Level Security (RLS)和性能优化
        """
        cursor = dbapi_conn.cursor()
        
        # 设置默认超时
        cursor.execute("SET statement_timeout = '30s'")
        
        # 设置时区
        cursor.execute("SET timezone = 'UTC'")
        
        # 设置搜索路径
        cursor.execute("SET search_path = public")
        
        cursor.close()
    
    # 创建应用上下文内的表（开发环境）
    with app.app_context():
        # 仅在开发环境自动创建表
        if os.getenv('FLASK_ENV') == 'development':
            try:
                # 导入所有模型以确保表被创建
                from .models import EventOutbox, ConsumerInbox, EventDLQ
                
                db.create_all()
                logger.info("✅ Database tables created successfully")
            except Exception as e:
                logger.warning(f"⚠️ Could not create tables (may already exist): {e}")
        
        # 测试数据库连接
        try:
            with db.engine.connect() as conn:
                result = conn.execute(text("SELECT version()"))
                version = result.scalar()
                logger.info(f"✅ Database connected: {version[:50]}...")
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            raise
    
    logger.info("✅ Database initialization completed")
    return db


def get_db_session():
    """
    获取数据库会话（用于独立脚本）
    
    返回:
        db.session: SQLAlchemy会话对象
    """
    return db.session


def execute_raw_sql(sql: str, params: dict = None):
    """
    执行原始SQL查询
    
    参数:
        sql: SQL查询语句
        params: 查询参数字典
    
    返回:
        查询结果
    """
    try:
        with db.engine.connect() as conn:
            result = conn.execute(text(sql), params or {})
            conn.commit()
            return result
    except Exception as e:
        logger.error(f"SQL execution failed: {e}")
        raise


def set_session_context(user_id: str, tenant_id: str = 'default', role: str = 'user'):
    """
    设置PostgreSQL会话上下文（用于Row Level Security）
    
    参数:
        user_id: 用户ID
        tenant_id: 租户ID
        role: 用户角色
    """
    import re
    
    # SQL注入防护：严格验证输入值格式
    # 只允许字母数字、下划线、连字符和UUID格式
    SAFE_PATTERN = re.compile(r'^[a-zA-Z0-9_\-]+$')
    
    if not SAFE_PATTERN.match(user_id):
        raise ValueError(f"Invalid user_id format: {user_id}")
    if not SAFE_PATTERN.match(tenant_id):
        raise ValueError(f"Invalid tenant_id format: {tenant_id}")
    if not SAFE_PATTERN.match(role):
        raise ValueError(f"Invalid role format: {role}")
    
    try:
        with db.engine.connect() as conn:
            # PostgreSQL SET命令不支持参数化，使用严格验证后的值
            conn.execute(text(f"SET app.user_id = '{user_id}'"))
            conn.execute(text(f"SET app.tenant_id = '{tenant_id}'"))
            conn.execute(text(f"SET app.role = '{role}'"))
            conn.commit()
            logger.debug(f"Session context set: user={user_id}, tenant={tenant_id}, role={role}")
    except Exception as e:
        logger.error(f"Failed to set session context: {e}")
        raise
