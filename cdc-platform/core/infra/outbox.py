"""
HashInsight CDC Platform - Outbox Publisher
Transactional Outbox模式实现，确保事件与业务操作的原子性
"""
import os
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)

class OutboxPublisher:
    """
    Outbox事件发布器
    
    核心功能：
    1. 在数据库事务内写入event_outbox表
    2. 支持幂等性（idempotency_key）
    3. 自动设置tenant_id（多租户支持）
    4. Debezium CDC会自动捕获并发布到Kafka
    """
    
    def __init__(self, db):
        """
        初始化Outbox发布器
        
        参数:
            db: SQLAlchemy数据库实例
        """
        self.db = db
        logger.info("✅ OutboxPublisher initialized")
    
    def publish(
        self,
        kind: str,
        user_id: str,
        payload: Dict[str, Any],
        entity_id: Optional[str] = None,
        tenant_id: str = 'default',
        idempotency_key: Optional[str] = None
    ) -> Optional[str]:
        """
        发布事件到Outbox表（在当前事务内）
        
        参数:
            kind: 事件类型（如 'miner.added', 'treasury.trade_executed'）
            user_id: 用户ID（作为Kafka消息键，保证同一用户的事件顺序）
            payload: 事件负载（JSON）
            entity_id: 实体ID（可选）
            tenant_id: 租户ID（默认'default'）
            idempotency_key: 幂等键（可选，防止重复事件）
        
        返回:
            事件ID或None（如果失败）
        
        示例:
            >>> outbox.publish(
            ...     kind='miner.added',
            ...     user_id='user123',
            ...     payload={'miner_id': 'miner456', 'hashrate': 100},
            ...     entity_id='miner456',
            ...     idempotency_key='add_miner_user123_miner456'
            ... )
        """
        try:
            # 生成事件ID
            event_id = str(uuid.uuid4())
            
            # 如果未提供幂等键，使用事件ID作为幂等键
            if not idempotency_key:
                idempotency_key = event_id
            
            # 准备SQL参数
            params = {
                'id': event_id,
                'kind': kind,
                'user_id': user_id,
                'tenant_id': tenant_id,
                'entity_id': entity_id,
                'payload': payload,  # SQLAlchemy会自动转换为JSONB
                'idempotency_key': idempotency_key,
                'created_at': datetime.utcnow(),
                'processed': False
            }
            
            # 插入event_outbox表
            # 使用 ON CONFLICT DO NOTHING 实现幂等性
            sql = text("""
                INSERT INTO event_outbox (
                    id, kind, user_id, tenant_id, entity_id, 
                    payload, idempotency_key, created_at, processed
                )
                VALUES (
                    :id, :kind, :user_id, :tenant_id, :entity_id,
                    :payload::jsonb, :idempotency_key, :created_at, :processed
                )
                ON CONFLICT (idempotency_key) DO NOTHING
                RETURNING id
            """)
            
            result = self.db.session.execute(sql, params)
            inserted_id = result.scalar()
            
            if inserted_id:
                logger.info(
                    f"📤 Event published to outbox: "
                    f"kind={kind}, user={user_id}, tenant={tenant_id}, id={event_id}"
                )
                return event_id
            else:
                logger.warning(
                    f"⚠️ Duplicate event ignored (idempotency): "
                    f"kind={kind}, key={idempotency_key}"
                )
                return None
        
        except SQLAlchemyError as e:
            logger.error(f"❌ Failed to publish event to outbox: {e}")
            raise
    
    def publish_batch(
        self,
        events: list[Dict[str, Any]],
        tenant_id: str = 'default'
    ) -> int:
        """
        批量发布事件
        
        参数:
            events: 事件列表，每个事件包含 kind, user_id, payload 等字段
            tenant_id: 租户ID
        
        返回:
            成功发布的事件数量
        
        示例:
            >>> events = [
            ...     {'kind': 'miner.added', 'user_id': 'user1', 'payload': {...}},
            ...     {'kind': 'miner.updated', 'user_id': 'user1', 'payload': {...}}
            ... ]
            >>> count = outbox.publish_batch(events)
        """
        count = 0
        
        try:
            for event in events:
                event_id = self.publish(
                    kind=event['kind'],
                    user_id=event['user_id'],
                    payload=event['payload'],
                    entity_id=event.get('entity_id'),
                    tenant_id=event.get('tenant_id', tenant_id),
                    idempotency_key=event.get('idempotency_key')
                )
                
                if event_id:
                    count += 1
            
            logger.info(f"📤 Batch published: {count}/{len(events)} events")
            return count
        
        except Exception as e:
            logger.error(f"❌ Batch publish failed: {e}")
            raise
    
    def get_pending_events(self, limit: int = 100) -> list:
        """
        获取待处理的事件（用于备用轮询机制）
        
        参数:
            limit: 返回数量限制
        
        返回:
            待处理事件列表
        """
        try:
            sql = text("""
                SELECT id, kind, user_id, tenant_id, entity_id, 
                       payload, created_at
                FROM event_outbox
                WHERE processed = false
                ORDER BY created_at ASC
                LIMIT :limit
            """)
            
            result = self.db.session.execute(sql, {'limit': limit})
            events = []
            
            for row in result:
                events.append({
                    'id': row.id,
                    'kind': row.kind,
                    'user_id': row.user_id,
                    'tenant_id': row.tenant_id,
                    'entity_id': row.entity_id,
                    'payload': row.payload,
                    'created_at': row.created_at
                })
            
            return events
        
        except SQLAlchemyError as e:
            logger.error(f"❌ Failed to get pending events: {e}")
            return []
    
    def mark_as_processed(self, event_id: str) -> bool:
        """
        标记事件为已处理（用于备用轮询机制）
        
        参数:
            event_id: 事件ID
        
        返回:
            是否成功
        """
        try:
            sql = text("""
                UPDATE event_outbox
                SET processed = true, processed_at = :processed_at
                WHERE id = :event_id
            """)
            
            self.db.session.execute(sql, {
                'event_id': event_id,
                'processed_at': datetime.utcnow()
            })
            self.db.session.commit()
            
            logger.debug(f"✅ Event marked as processed: {event_id}")
            return True
        
        except SQLAlchemyError as e:
            logger.error(f"❌ Failed to mark event as processed: {e}")
            self.db.session.rollback()
            return False
    
    def cleanup_old_events(self, days: int = 7) -> int:
        """
        清理已处理的旧事件
        
        参数:
            days: 保留天数
        
        返回:
            删除的事件数量
        """
        try:
            sql = text("""
                DELETE FROM event_outbox
                WHERE processed = true
                AND processed_at < NOW() - INTERVAL ':days days'
            """)
            
            result = self.db.session.execute(sql, {'days': days})
            count = result.rowcount
            self.db.session.commit()
            
            logger.info(f"🧹 Cleaned up {count} old outbox events (>{days} days)")
            return count
        
        except SQLAlchemyError as e:
            logger.error(f"❌ Cleanup failed: {e}")
            self.db.session.rollback()
            return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取Outbox统计信息
        
        返回:
            统计字典
        """
        try:
            sql = text("""
                SELECT 
                    COUNT(*) FILTER (WHERE processed = false) as pending,
                    COUNT(*) FILTER (WHERE processed = true) as processed,
                    COUNT(*) as total,
                    MIN(created_at) FILTER (WHERE processed = false) as oldest_pending
                FROM event_outbox
            """)
            
            result = self.db.session.execute(sql).first()
            
            return {
                'pending': result.pending or 0,
                'processed': result.processed or 0,
                'total': result.total or 0,
                'oldest_pending': result.oldest_pending.isoformat() if result.oldest_pending else None
            }
        
        except SQLAlchemyError as e:
            logger.error(f"❌ Failed to get stats: {e}")
            return {'error': str(e)}
