"""
Event Publisher - Transaction-Safe Event Publishing System
事件发布器 - 事务安全的事件发布系统

Implements the Outbox Pattern for reliable event publishing.
实现Outbox模式以确保可靠的事件发布。
"""

import logging
from typing import Dict, Any, Optional, Union
from datetime import datetime
import traceback

from db import db
from models import EventOutbox
from intelligence.events.contracts import (
    EventTypes, 
    AggregateTypes,
    create_event_payload,
    validate_event_type,
    validate_aggregate_type,
    MinerEventData,
    PortfolioEventData,
    UserEventData,
    CalculationEventData,
    SLAEventData,
    BlockchainEventData,
    AnalyticsEventData
)

logger = logging.getLogger(__name__)


class EventPublisher:
    """
    事件发布器类
    
    使用Outbox模式实现事务安全的事件发布。
    事件在与主数据相同的事务中保存，确保原子性。
    """
    
    def __init__(self, db_session=None):
        """
        初始化事件发布器
        
        Args:
            db_session: 数据库会话，默认使用db.session
        """
        self.db_session = db_session or db.session
    
    def publish_event(
        self, 
        event_type: str, 
        aggregate_id: Union[str, int], 
        aggregate_type: str, 
        payload: Dict[str, Any],
        correlation_id: Optional[str] = None,
        causation_id: Optional[str] = None,
        max_retries: int = 3
    ) -> Optional[EventOutbox]:
        """
        发布事件到Outbox
        
        此方法将事件保存到EventOutbox表中，与主数据在同一事务中提交。
        事件会由后台worker异步处理。
        
        Args:
            event_type: 事件类型（如 EventTypes.MINER_ADDED）
            aggregate_id: 聚合根ID（如 miner_id, user_id）
            aggregate_type: 聚合根类型（如 AggregateTypes.MINER）
            payload: 事件载荷（JSON格式）
            correlation_id: 关联ID（用于追踪）
            causation_id: 因果ID（触发此事件的原因）
            max_retries: 最大重试次数
            
        Returns:
            EventOutbox: 创建的事件对象，失败时返回None
        """
        try:
            # 验证事件类型
            if not validate_event_type(event_type):
                logger.warning(f"Invalid event type: {event_type}")
            
            # 验证聚合类型
            if not validate_aggregate_type(aggregate_type):
                logger.warning(f"Invalid aggregate type: {aggregate_type}")
            
            # 确保aggregate_id是字符串
            aggregate_id_str = str(aggregate_id)
            
            # 确保payload包含时间戳
            if 'timestamp' not in payload:
                payload['timestamp'] = datetime.utcnow().isoformat()
            
            # 创建EventOutbox记录
            event = EventOutbox(
                event_type=event_type,
                event_payload=payload,
                aggregate_id=aggregate_id_str,
                aggregate_type=aggregate_type,
                correlation_id=correlation_id,
                causation_id=causation_id,
                max_retries=max_retries
            )
            
            # 添加到会话（不立即提交，等待与主数据一起提交）
            self.db_session.add(event)
            
            logger.info(
                f"Event published to outbox: {event_type} "
                f"(aggregate: {aggregate_type}:{aggregate_id_str})"
            )
            
            return event
            
        except Exception as e:
            logger.error(
                f"Failed to publish event {event_type}: {str(e)}\n"
                f"{traceback.format_exc()}"
            )
            return None
    
    def publish_miner_event(
        self, 
        event_type: str, 
        miner_id: int,
        miner_data: Union[MinerEventData, Dict[str, Any]],
        **kwargs
    ) -> Optional[EventOutbox]:
        """
        发布矿机相关事件
        
        Args:
            event_type: 事件类型（如 EventTypes.MINER_ADDED）
            miner_id: 矿机ID
            miner_data: 矿机事件数据（MinerEventData对象或字典）
            **kwargs: 其他参数（correlation_id, causation_id等）
            
        Returns:
            EventOutbox: 创建的事件对象
        """
        try:
            # 创建事件载荷
            payload = create_event_payload(miner_data)
            
            # 发布事件
            return self.publish_event(
                event_type=event_type,
                aggregate_id=miner_id,
                aggregate_type=AggregateTypes.MINER,
                payload=payload,
                **kwargs
            )
            
        except Exception as e:
            logger.error(f"Failed to publish miner event: {str(e)}")
            return None
    
    def publish_portfolio_event(
        self, 
        event_type: str, 
        portfolio_id: int,
        portfolio_data: Union[PortfolioEventData, Dict[str, Any]],
        **kwargs
    ) -> Optional[EventOutbox]:
        """
        发布投资组合相关事件
        
        Args:
            event_type: 事件类型（如 EventTypes.PORTFOLIO_UPDATED）
            portfolio_id: 投资组合ID
            portfolio_data: 投资组合事件数据
            **kwargs: 其他参数
            
        Returns:
            EventOutbox: 创建的事件对象
        """
        try:
            # 创建事件载荷
            payload = create_event_payload(portfolio_data)
            
            # 发布事件
            return self.publish_event(
                event_type=event_type,
                aggregate_id=portfolio_id,
                aggregate_type=AggregateTypes.PORTFOLIO,
                payload=payload,
                **kwargs
            )
            
        except Exception as e:
            logger.error(f"Failed to publish portfolio event: {str(e)}")
            return None
    
    def publish_user_event(
        self, 
        event_type: str, 
        user_id: int,
        user_data: Union[UserEventData, Dict[str, Any]],
        **kwargs
    ) -> Optional[EventOutbox]:
        """
        发布用户相关事件
        
        Args:
            event_type: 事件类型
            user_id: 用户ID
            user_data: 用户事件数据
            **kwargs: 其他参数
            
        Returns:
            EventOutbox: 创建的事件对象
        """
        try:
            payload = create_event_payload(user_data)
            
            return self.publish_event(
                event_type=event_type,
                aggregate_id=user_id,
                aggregate_type=AggregateTypes.USER,
                payload=payload,
                **kwargs
            )
            
        except Exception as e:
            logger.error(f"Failed to publish user event: {str(e)}")
            return None
    
    def publish_calculation_event(
        self, 
        event_type: str, 
        calculation_id: str,
        calculation_data: Union[CalculationEventData, Dict[str, Any]],
        **kwargs
    ) -> Optional[EventOutbox]:
        """
        发布计算相关事件
        
        Args:
            event_type: 事件类型
            calculation_id: 计算ID
            calculation_data: 计算事件数据
            **kwargs: 其他参数
            
        Returns:
            EventOutbox: 创建的事件对象
        """
        try:
            payload = create_event_payload(calculation_data)
            
            return self.publish_event(
                event_type=event_type,
                aggregate_id=calculation_id,
                aggregate_type=AggregateTypes.CALCULATION,
                payload=payload,
                **kwargs
            )
            
        except Exception as e:
            logger.error(f"Failed to publish calculation event: {str(e)}")
            return None
    
    def publish_sla_event(
        self, 
        event_type: str, 
        sla_id: int,
        sla_data: Union[SLAEventData, Dict[str, Any]],
        **kwargs
    ) -> Optional[EventOutbox]:
        """
        发布SLA相关事件
        
        Args:
            event_type: 事件类型
            sla_id: SLA记录ID
            sla_data: SLA事件数据
            **kwargs: 其他参数
            
        Returns:
            EventOutbox: 创建的事件对象
        """
        try:
            payload = create_event_payload(sla_data)
            
            return self.publish_event(
                event_type=event_type,
                aggregate_id=sla_id,
                aggregate_type=AggregateTypes.SLA,
                payload=payload,
                **kwargs
            )
            
        except Exception as e:
            logger.error(f"Failed to publish SLA event: {str(e)}")
            return None
    
    def publish_blockchain_event(
        self, 
        event_type: str, 
        record_id: int,
        blockchain_data: Union[BlockchainEventData, Dict[str, Any]],
        **kwargs
    ) -> Optional[EventOutbox]:
        """
        发布区块链相关事件
        
        Args:
            event_type: 事件类型
            record_id: 记录ID
            blockchain_data: 区块链事件数据
            **kwargs: 其他参数
            
        Returns:
            EventOutbox: 创建的事件对象
        """
        try:
            payload = create_event_payload(blockchain_data)
            
            return self.publish_event(
                event_type=event_type,
                aggregate_id=record_id,
                aggregate_type=AggregateTypes.BLOCKCHAIN,
                payload=payload,
                **kwargs
            )
            
        except Exception as e:
            logger.error(f"Failed to publish blockchain event: {str(e)}")
            return None
    
    def publish_analytics_event(
        self, 
        event_type: str, 
        report_id: str,
        analytics_data: Union[AnalyticsEventData, Dict[str, Any]],
        **kwargs
    ) -> Optional[EventOutbox]:
        """
        发布分析相关事件
        
        Args:
            event_type: 事件类型
            report_id: 报告ID
            analytics_data: 分析事件数据
            **kwargs: 其他参数
            
        Returns:
            EventOutbox: 创建的事件对象
        """
        try:
            payload = create_event_payload(analytics_data)
            
            return self.publish_event(
                event_type=event_type,
                aggregate_id=report_id,
                aggregate_type=AggregateTypes.ANALYTICS,
                payload=payload,
                **kwargs
            )
            
        except Exception as e:
            logger.error(f"Failed to publish analytics event: {str(e)}")
            return None
    
    @staticmethod
    def commit_with_events():
        """
        提交事务（包含事件）
        
        这个方法应该在业务逻辑完成后调用，以确保主数据和事件一起提交。
        如果提交失败，所有更改（包括事件）都会回滚。
        """
        try:
            db.session.commit()
            logger.info("Transaction committed successfully with events")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Transaction rollback due to error: {str(e)}\n{traceback.format_exc()}")
            raise
    
    @staticmethod
    def rollback_with_events():
        """
        回滚事务（包含事件）
        
        当业务逻辑失败时调用，确保主数据和事件都被回滚。
        """
        try:
            db.session.rollback()
            logger.info("Transaction rolled back with events")
        except Exception as e:
            logger.error(f"Rollback failed: {str(e)}")
            raise


# ============================================================================
# 便捷函数 - Convenience Functions
# ============================================================================

# 全局事件发布器实例
_global_publisher = None


def get_event_publisher(db_session=None) -> EventPublisher:
    """
    获取事件发布器实例（单例模式）
    
    Args:
        db_session: 可选的数据库会话
        
    Returns:
        EventPublisher: 事件发布器实例
    """
    global _global_publisher
    
    if _global_publisher is None or db_session is not None:
        _global_publisher = EventPublisher(db_session)
    
    return _global_publisher


def publish_event(event_type: str, aggregate_id: Union[str, int], 
                 aggregate_type: str, payload: Dict[str, Any], **kwargs) -> Optional[EventOutbox]:
    """
    便捷函数：发布事件
    
    使用全局事件发布器发布事件
    """
    publisher = get_event_publisher()
    return publisher.publish_event(event_type, aggregate_id, aggregate_type, payload, **kwargs)


def publish_miner_event(event_type: str, miner_id: int, 
                       miner_data: Union[MinerEventData, Dict[str, Any]], **kwargs) -> Optional[EventOutbox]:
    """便捷函数：发布矿机事件"""
    publisher = get_event_publisher()
    return publisher.publish_miner_event(event_type, miner_id, miner_data, **kwargs)


def publish_portfolio_event(event_type: str, portfolio_id: int,
                            portfolio_data: Union[PortfolioEventData, Dict[str, Any]], 
                            **kwargs) -> Optional[EventOutbox]:
    """便捷函数：发布投资组合事件"""
    publisher = get_event_publisher()
    return publisher.publish_portfolio_event(event_type, portfolio_id, portfolio_data, **kwargs)
