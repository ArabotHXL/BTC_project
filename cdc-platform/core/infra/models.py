"""
HashInsight CDC Platform - Database Models
数据库模型定义（用于ORM）
"""
from sqlalchemy import Column, String, Boolean, DateTime, JSON, Text
from sqlalchemy.sql import func
from .database import Base

class EventOutbox(Base):
    """事件发件箱表（Transactional Outbox模式）"""
    __tablename__ = 'event_outbox'
    
    id = Column(String, primary_key=True)
    kind = Column(String, nullable=False, index=True)
    user_id = Column(String, nullable=False, index=True)
    tenant_id = Column(String, nullable=False, default='default', index=True)
    entity_id = Column(String)
    payload = Column(JSON, nullable=False)
    idempotency_key = Column(String, unique=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    processed = Column(Boolean, nullable=False, default=False, index=True)
    processed_at = Column(DateTime(timezone=True))

class ConsumerInbox(Base):
    """消费者收件箱表（幂等消费）"""
    __tablename__ = 'consumer_inbox'
    
    consumer_name = Column(String, primary_key=True)
    event_id = Column(String, primary_key=True)
    event_kind = Column(String, nullable=False)
    user_id = Column(String, nullable=False, index=True)
    payload = Column(JSON, nullable=False)
    consumed_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    processing_duration_ms = Column(Text)

class EventDLQ(Base):
    """死信队列表（失败事件）"""
    __tablename__ = 'event_dlq'
    
    id = Column(String, primary_key=True)
    consumer_name = Column(String, nullable=False, index=True)
    event_id = Column(String, nullable=False)
    event_kind = Column(String, nullable=False)
    payload = Column(JSON, nullable=False)
    error_message = Column(Text)
    error_stacktrace = Column(Text)
    retry_count = Column(Text, nullable=False, default='0')
    first_failed_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    last_failed_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    resolved = Column(Boolean, nullable=False, default=False, index=True)
    resolved_at = Column(DateTime(timezone=True))
