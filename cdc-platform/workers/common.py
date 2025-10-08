"""
HashInsight CDC Platform - Kafka Consumer Common Module
Kafka消费者通用基类、重试机制、DLQ处理、幂等性保证

Author: HashInsight Team
Version: 1.0.0
"""
import os
import sys
import json
import logging
import signal
import traceback
import time
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Callable
from datetime import datetime
from kafka import KafkaConsumer  # type: ignore
from kafka.errors import KafkaError  # type: ignore

# 添加CDC平台核心模块到Python路径
CDC_CORE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'core'))
sys.path.insert(0, CDC_CORE_PATH)

from flask import Flask
from infra.database import db, init_db  # type: ignore
from infra.models import ConsumerInbox, EventDLQ  # type: ignore
from infra.redis_client import redis_client  # type: ignore

logger = logging.getLogger(__name__)

# =====================================================
# Kafka消费者基类
# =====================================================

class KafkaConsumerBase(ABC):
    """
    Kafka消费者基类
    
    提供功能：
    - Kafka连接管理
    - Inbox幂等性保证
    - 分布式锁（Redis）
    - DLQ死信队列处理
    - 重试机制
    - 优雅关闭
    """
    
    def __init__(self, consumer_name: str, topic: str, group_id: str):
        """
        初始化消费者
        
        参数:
            consumer_name: 消费者名称（如 'portfolio-consumer'）
            topic: Kafka主题名称（如 'events.miner'）
            group_id: Kafka消费者组ID
        """
        self.consumer_name = consumer_name
        self.topic = topic
        self.group_id = group_id
        self.consumer = None
        self.running = False
        self.app = None
        
        # 配置参数
        self.kafka_bootstrap_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
        self.max_retries = int(os.getenv('CONSUMER_MAX_RETRIES', 3))
        self.processing_timeout = int(os.getenv('CONSUMER_PROCESSING_TIMEOUT', 300))  # 5分钟
        
        # 注册信号处理器（优雅关闭）
        signal.signal(signal.SIGINT, self._shutdown_handler)
        signal.signal(signal.SIGTERM, self._shutdown_handler)
        
        logger.info(f"✅ {self.consumer_name} initialized: topic={topic}, group={group_id}")
    
    def _init_flask_app(self):
        """初始化Flask应用上下文（用于数据库操作）"""
        self.app = Flask(__name__)
        self.app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
        self.app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        init_db(self.app)
        logger.info("✅ Flask application context initialized")
    
    def _create_consumer(self):
        """创建Kafka消费者实例"""
        try:
            self.consumer = KafkaConsumer(
                self.topic,
                bootstrap_servers=self.kafka_bootstrap_servers,
                group_id=self.group_id,
                auto_offset_reset='earliest',  # 从最早的消息开始消费
                enable_auto_commit=False,  # 手动提交offset（保证至少一次消费）
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                key_deserializer=lambda k: k.decode('utf-8') if k else None,
                max_poll_interval_ms=300000,  # 5分钟
                session_timeout_ms=30000,  # 30秒
                heartbeat_interval_ms=10000,  # 10秒
            )
            logger.info(f"✅ Kafka consumer created: {self.kafka_bootstrap_servers}")
        except KafkaError as e:
            logger.error(f"❌ Failed to create Kafka consumer: {e}")
            raise
    
    def _check_inbox(self, event_id: str) -> bool:
        """
        检查消息是否已被消费（Inbox幂等性）
        
        参数:
            event_id: 事件ID
        
        返回:
            True: 已消费（跳过）
            False: 未消费（处理）
        """
        try:
            if not self.app:
                return False
            with self.app.app_context():
                existing = ConsumerInbox.query.filter_by(
                    consumer_name=self.consumer_name,
                    event_id=event_id
                ).first()
                
                if existing:
                    logger.debug(f"⏭️ Event {event_id} already consumed, skipping (idempotent)")
                    return True
                
                return False
        except Exception as e:
            logger.error(f"❌ Error checking inbox for event {event_id}: {e}")
            # 如果检查失败，为安全起见返回False（尝试处理）
            return False
    
    def _save_to_inbox(self, event_id: str, event_kind: str, user_id: str, 
                       payload: Dict, processing_duration_ms: int):
        """
        保存事件到Inbox（标记已消费）
        
        参数:
            event_id: 事件ID
            event_kind: 事件类型
            user_id: 用户ID
            payload: 事件负载
            processing_duration_ms: 处理耗时（毫秒）
        """
        try:
            if not self.app:
                return
            with self.app.app_context():
                inbox_entry = ConsumerInbox(
                    consumer_name=self.consumer_name,
                    event_id=event_id,
                    event_kind=event_kind,
                    user_id=user_id,
                    payload=payload,
                    processing_duration_ms=str(processing_duration_ms)
                )
                db.session.add(inbox_entry)
                db.session.commit()
                logger.debug(f"📥 Saved to inbox: event_id={event_id}, duration={processing_duration_ms}ms")
        except Exception as e:
            logger.error(f"❌ Error saving to inbox: {e}")
            db.session.rollback()
    
    def _save_to_dlq(self, event_id: str, event_kind: str, payload: Dict, 
                     error_message: str, retry_count: int):
        """
        保存失败事件到死信队列（DLQ）
        
        参数:
            event_id: 事件ID
            event_kind: 事件类型
            payload: 事件负载
            error_message: 错误信息
            retry_count: 重试次数
        """
        try:
            if not self.app:
                return
            with self.app.app_context():
                dlq_entry = EventDLQ(
                    id=f"{event_id}_dlq_{int(time.time())}",
                    consumer_name=self.consumer_name,
                    event_id=event_id,
                    event_kind=event_kind,
                    payload=payload,
                    error_message=error_message,
                    error_stacktrace=traceback.format_exc(),
                    retry_count=str(retry_count)
                )
                db.session.add(dlq_entry)
                db.session.commit()
                logger.error(f"💀 Saved to DLQ: event_id={event_id}, retries={retry_count}, error={error_message}")
        except Exception as e:
            logger.error(f"❌ Error saving to DLQ: {e}")
            db.session.rollback()
    
    def _acquire_lock(self, lock_name: str) -> Optional[Any]:
        """
        获取分布式锁（防止并发处理同一用户的事件）
        
        参数:
            lock_name: 锁名称（如 'recalc:123'）
        
        返回:
            锁对象或None
        """
        lock = redis_client.acquire_lock(
            lock_name=lock_name,
            timeout=self.processing_timeout,
            blocking_timeout=5
        )
        
        if lock:
            logger.debug(f"🔒 Acquired lock: {lock_name}")
        else:
            logger.warning(f"⏳ Failed to acquire lock (already processing): {lock_name}")
        
        return lock
    
    def _release_lock(self, lock):
        """释放分布式锁"""
        if lock:
            redis_client.release_lock(lock)
            logger.debug(f"🔓 Released lock")
    
    def _invalidate_cache(self, cache_key: str):
        """
        失效缓存
        
        参数:
            cache_key: 缓存键（如 'user_portfolio:123'）
        """
        success = redis_client.delete(cache_key)
        if success:
            logger.debug(f"🗑️ Cache invalidated: {cache_key}")
        else:
            logger.warning(f"⚠️ Failed to invalidate cache: {cache_key}")
    
    def _process_with_retry(self, event_id: str, event_kind: str, user_id: str, 
                           payload: Dict, process_func: Callable) -> bool:
        """
        带重试机制的消息处理
        
        参数:
            event_id: 事件ID
            event_kind: 事件类型
            user_id: 用户ID
            payload: 事件负载
            process_func: 处理函数
        
        返回:
            True: 处理成功
            False: 处理失败（已重试max_retries次）
        """
        start_time = time.time()
        retry_count = 0
        last_error = None
        
        while retry_count <= self.max_retries:
            try:
                # 调用处理函数
                process_func(event_id, event_kind, user_id, payload)
                
                # 处理成功：计算耗时并保存到Inbox
                duration_ms = int((time.time() - start_time) * 1000)
                self._save_to_inbox(event_id, event_kind, user_id, payload, duration_ms)
                
                logger.info(f"✅ Event processed successfully: {event_id} (duration={duration_ms}ms)")
                return True
                
            except Exception as e:
                last_error = str(e)
                retry_count += 1
                
                if retry_count <= self.max_retries:
                    # 指数退避重试
                    wait_time = min(2 ** retry_count, 30)  # 最多等待30秒
                    logger.warning(
                        f"⚠️ Event processing failed (retry {retry_count}/{self.max_retries}): "
                        f"{event_id}, error={last_error}, retrying in {wait_time}s..."
                    )
                    time.sleep(wait_time)
                else:
                    # 重试次数耗尽：保存到DLQ
                    logger.error(
                        f"❌ Event processing failed after {self.max_retries} retries: "
                        f"{event_id}, error={last_error}"
                    )
                    self._save_to_dlq(event_id, event_kind, payload, last_error, retry_count - 1)
                    return False
        
        return False
    
    @abstractmethod
    def process_event(self, event_id: str, event_kind: str, user_id: str, payload: Dict):
        """
        处理单个事件（子类必须实现）
        
        参数:
            event_id: 事件ID
            event_kind: 事件类型
            user_id: 用户ID
            payload: 事件负载
        """
        pass
    
    def run(self):
        """运行消费者主循环"""
        logger.info(f"🚀 Starting {self.consumer_name}...")
        
        # 初始化Flask应用上下文
        self._init_flask_app()
        
        # 创建Kafka消费者
        self._create_consumer()
        
        self.running = True
        logger.info(f"✅ {self.consumer_name} is running, listening to topic '{self.topic}'")
        
        try:
            if not self.consumer:
                logger.error("❌ Kafka consumer not initialized")
                return
            for message in self.consumer:
                if not self.running:
                    break
                
                try:
                    # 解析消息
                    event_id = message.value.get('id')
                    event_kind = message.value.get('kind')
                    user_id = message.key or message.value.get('user_id')
                    payload = message.value.get('payload', message.value)
                    
                    if not event_id or not user_id:
                        logger.error(f"❌ Invalid message format (missing id/user_id): {message.value}")
                        if self.consumer:
                            self.consumer.commit()
                        continue
                    
                    logger.info(f"📨 Received event: id={event_id}, kind={event_kind}, user={user_id}")
                    
                    # 检查是否已消费（幂等性）
                    if self._check_inbox(event_id):
                        if self.consumer:
                            self.consumer.commit()
                        continue
                    
                    # 带重试机制的处理
                    success = self._process_with_retry(
                        event_id, event_kind, user_id, payload, self.process_event
                    )
                    
                    # 提交offset（无论成功或失败都提交，避免重复消费）
                    if self.consumer:
                        self.consumer.commit()
                    
                    if success:
                        logger.info(f"✅ Message committed: {event_id}")
                    else:
                        logger.error(f"❌ Message failed and sent to DLQ: {event_id}")
                
                except Exception as e:
                    logger.error(f"❌ Error processing message: {e}\n{traceback.format_exc()}")
                    # 即使出错也提交offset，避免无限重试
                    if self.consumer:
                        self.consumer.commit()
        
        except KeyboardInterrupt:
            logger.info("⏹️ Consumer interrupted by user")
        
        finally:
            self._cleanup()
    
    def _cleanup(self):
        """清理资源"""
        logger.info(f"🧹 Cleaning up {self.consumer_name}...")
        
        if self.consumer:
            self.consumer.close()
            logger.info("✅ Kafka consumer closed")
        
        logger.info(f"✅ {self.consumer_name} stopped gracefully")
    
    def _shutdown_handler(self, signum, frame):
        """信号处理器（优雅关闭）"""
        logger.info(f"🛑 Received shutdown signal ({signum}), stopping consumer...")
        self.running = False


# =====================================================
# 工具函数
# =====================================================

def format_error_message(error: Exception) -> str:
    """
    格式化错误消息
    
    参数:
        error: 异常对象
    
    返回:
        格式化的错误消息
    """
    return f"{type(error).__name__}: {str(error)}"


def extract_user_id(message: Dict) -> Optional[str]:
    """
    从消息中提取user_id
    
    参数:
        message: Kafka消息
    
    返回:
        用户ID或None
    """
    return message.get('user_id') or message.get('payload', {}).get('user_id')


def validate_event_payload(payload: Dict, required_fields: list) -> bool:
    """
    验证事件负载是否包含必需字段
    
    参数:
        payload: 事件负载
        required_fields: 必需字段列表
    
    返回:
        True: 验证通过
        False: 验证失败
    """
    for field in required_fields:
        if field not in payload:
            logger.error(f"❌ Missing required field: {field}")
            return False
    return True
