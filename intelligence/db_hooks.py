"""
Database Hooks - SQLAlchemy Event Listeners for Intelligence Layer
数据库钩子 - 智能层的SQLAlchemy事件监听器

Automatically triggers events when database changes occur.
Uses the Outbox Pattern to ensure reliable event publishing.
"""

import logging
from typing import Any, Dict
from sqlalchemy import event
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import get_history

from intelligence.events.publisher import get_event_publisher
from intelligence.events.contracts import EventTypes, AggregateTypes, MinerEventData

logger = logging.getLogger(__name__)


def _extract_changed_fields(target, context) -> Dict[str, Any]:
    """
    提取已修改的字段
    
    Args:
        target: SQLAlchemy模型实例
        context: SQLAlchemy事件上下文
        
    Returns:
        Dict[str, Any]: 已修改字段的字典 {field_name: {'old': old_value, 'new': new_value}}
    """
    changed_fields = {}
    
    try:
        state = context.get_attribute_state(target, 'id')
        if state is None:
            return changed_fields
        
        # 获取所有已修改的属性
        for attr in context.attrs:
            history = get_history(target, attr.key)
            
            if history.has_changes():
                old_value = history.deleted[0] if history.deleted else None
                new_value = history.added[0] if history.added else None
                
                changed_fields[attr.key] = {
                    'old': str(old_value) if old_value is not None else None,
                    'new': str(new_value) if new_value is not None else None
                }
    except Exception as e:
        logger.warning(f"Failed to extract changed fields: {str(e)}")
    
    return changed_fields


def _safe_publish_event(event_publisher, event_type: str, aggregate_id: Any, 
                        aggregate_type: str, payload: Dict[str, Any]) -> bool:
    """
    安全地发布事件，捕获错误以防止事务回滚
    
    Args:
        event_publisher: EventPublisher实例
        event_type: 事件类型
        aggregate_id: 聚合根ID
        aggregate_type: 聚合根类型
        payload: 事件载荷
        
    Returns:
        bool: 发布是否成功
    """
    try:
        result = event_publisher.publish_event(
            event_type=event_type,
            aggregate_id=aggregate_id,
            aggregate_type=aggregate_type,
            payload=payload
        )
        
        if result:
            logger.info(
                f"Event published successfully: {event_type} "
                f"(aggregate: {aggregate_type}:{aggregate_id})"
            )
            return True
        else:
            logger.warning(
                f"Event publishing returned None: {event_type} "
                f"(aggregate: {aggregate_type}:{aggregate_id})"
            )
            return False
            
    except Exception as e:
        logger.error(
            f"Failed to publish event {event_type} for {aggregate_type}:{aggregate_id}: {str(e)}",
            exc_info=True
        )
        return False


# ============================================================================
# UserMiner Event Listeners - 用户矿机事件监听器
# ============================================================================

def on_user_miner_after_insert(mapper, connection, target):
    """
    UserMiner插入后事件监听器
    
    当用户添加新矿机时，发布MINER_ADDED事件
    """
    try:
        # 获取事件发布器
        publisher = get_event_publisher()
        
        # 构建矿机事件数据
        miner_data = MinerEventData(
            miner_id=target.id,
            model_name=target.custom_name or f"Miner-{target.id}",
            hashrate=float(target.actual_hashrate) if target.actual_hashrate else None,
            power_consumption=int(target.actual_power) if target.actual_power else None,
            efficiency=(float(target.actual_hashrate) / float(target.actual_power) 
                       if target.actual_hashrate and target.actual_power else None),
            status=target.status,
            owner_id=target.user_id,
            metadata={
                'miner_model_id': target.miner_model_id,
                'quantity': target.quantity,
                'actual_price': float(target.actual_price) if target.actual_price else None,
                'electricity_cost': float(target.electricity_cost) if target.electricity_cost else None,
                'decay_rate_monthly': float(target.decay_rate_monthly) if target.decay_rate_monthly else None,
                'location': target.location,
                'purchase_date': target.purchase_date.isoformat() if target.purchase_date else None,
                'source': 'user_miner'
            }
        )
        
        # 发布事件
        _safe_publish_event(
            event_publisher=publisher,
            event_type=EventTypes.MINER_ADDED,
            aggregate_id=target.id,
            aggregate_type=AggregateTypes.MINER,
            payload=miner_data.to_dict()
        )
        
    except Exception as e:
        logger.error(
            f"Error in on_user_miner_after_insert for UserMiner {target.id}: {str(e)}",
            exc_info=True
        )


def on_user_miner_after_update(mapper, connection, target):
    """
    UserMiner更新后事件监听器
    
    当用户矿机信息更新时，发布MINER_UPDATED事件
    """
    try:
        # 获取事件发布器
        publisher = get_event_publisher()
        
        # 提取已修改的字段
        from sqlalchemy import inspect
        state = inspect(target)
        changed_fields = {}
        
        for attr in state.attrs:
            history = attr.load_history()
            if history.has_changes():
                old_value = history.deleted[0] if history.deleted else None
                new_value = history.added[0] if history.added else getattr(target, attr.key)
                
                changed_fields[attr.key] = {
                    'old': str(old_value) if old_value is not None else None,
                    'new': str(new_value) if new_value is not None else None
                }
        
        # 构建矿机事件数据
        miner_data = MinerEventData(
            miner_id=target.id,
            model_name=target.custom_name or f"Miner-{target.id}",
            hashrate=float(target.actual_hashrate) if target.actual_hashrate else None,
            power_consumption=int(target.actual_power) if target.actual_power else None,
            efficiency=(float(target.actual_hashrate) / float(target.actual_power) 
                       if target.actual_hashrate and target.actual_power else None),
            status=target.status,
            owner_id=target.user_id,
            metadata={
                'changed_fields': changed_fields,
                'miner_model_id': target.miner_model_id,
                'quantity': target.quantity,
                'actual_price': float(target.actual_price) if target.actual_price else None,
                'electricity_cost': float(target.electricity_cost) if target.electricity_cost else None,
                'decay_rate_monthly': float(target.decay_rate_monthly) if target.decay_rate_monthly else None,
                'location': target.location,
                'source': 'user_miner'
            }
        )
        
        # 发布事件
        _safe_publish_event(
            event_publisher=publisher,
            event_type=EventTypes.MINER_UPDATED,
            aggregate_id=target.id,
            aggregate_type=AggregateTypes.MINER,
            payload=miner_data.to_dict()
        )
        
    except Exception as e:
        logger.error(
            f"Error in on_user_miner_after_update for UserMiner {target.id}: {str(e)}",
            exc_info=True
        )


def on_user_miner_after_delete(mapper, connection, target):
    """
    UserMiner删除后事件监听器
    
    当用户矿机被删除时，发布MINER_DELETED事件
    """
    try:
        # 获取事件发布器
        publisher = get_event_publisher()
        
        # 构建删除事件载荷（只包含基本信息）
        payload = {
            'miner_id': target.id,
            'model_name': target.custom_name or f"Miner-{target.id}",
            'owner_id': target.user_id,
            'deleted_at': None,  # Will be set by event publisher
            'metadata': {
                'miner_model_id': target.miner_model_id,
                'status': target.status,
                'source': 'user_miner'
            }
        }
        
        # 发布事件
        _safe_publish_event(
            event_publisher=publisher,
            event_type=EventTypes.MINER_DELETED,
            aggregate_id=target.id,
            aggregate_type=AggregateTypes.MINER,
            payload=payload
        )
        
    except Exception as e:
        logger.error(
            f"Error in on_user_miner_after_delete for UserMiner {target.id}: {str(e)}",
            exc_info=True
        )


# ============================================================================
# Miner (Batch Import) Event Listeners - 批量导入矿机事件监听器
# ============================================================================

def on_miner_after_insert(mapper, connection, target):
    """
    Miner插入后事件监听器
    
    当通过批量导入添加新矿机时，发布MINER_ADDED事件
    """
    try:
        # 获取事件发布器
        publisher = get_event_publisher()
        
        # 构建矿机事件数据
        miner_data = MinerEventData(
            miner_id=target.id,
            model_name=target.model or target.miner_id,
            hashrate=None,  # Batch import may not have hashrate
            power_consumption=None,  # Batch import may not have power
            efficiency=None,
            status=target.status,
            owner_id=None,  # Batch import may not have owner initially
            metadata={
                'miner_id_external': target.miner_id,
                'site_id': target.site_id,
                'ip': target.ip,
                'port': target.port,
                'api': target.api,
                'source': target.source or 'batch_import',
                'note': target.note
            }
        )
        
        # 发布事件
        _safe_publish_event(
            event_publisher=publisher,
            event_type=EventTypes.MINER_ADDED,
            aggregate_id=target.id,
            aggregate_type=AggregateTypes.MINER,
            payload=miner_data.to_dict()
        )
        
    except Exception as e:
        logger.error(
            f"Error in on_miner_after_insert for Miner {target.id}: {str(e)}",
            exc_info=True
        )


# ============================================================================
# Hook Setup Function - 钩子设置函数
# ============================================================================

def setup_intelligence_hooks():
    """
    注册所有智能层数据库事件监听器
    
    此函数应在应用启动时调用，以注册所有事件监听器。
    使用SQLAlchemy的事件系统自动触发事件发布。
    
    示例:
        from intelligence.db_hooks import setup_intelligence_hooks
        
        # 在app.py中调用
        with app.app_context():
            setup_intelligence_hooks()
    """
    try:
        # 导入模型（延迟导入以避免循环依赖）
        from models import UserMiner, Miner
        
        # 注册UserMiner事件监听器
        event.listens_for(UserMiner, 'after_insert')(on_user_miner_after_insert)
        event.listens_for(UserMiner, 'after_update')(on_user_miner_after_update)
        event.listens_for(UserMiner, 'after_delete')(on_user_miner_after_delete)
        
        # 注册Miner事件监听器（批量导入）
        event.listens_for(Miner, 'after_insert')(on_miner_after_insert)
        
        logger.info("Intelligence database hooks registered successfully")
        logger.info("Registered hooks:")
        logger.info("  - UserMiner: after_insert, after_update, after_delete")
        logger.info("  - Miner: after_insert (batch import)")
        
    except Exception as e:
        logger.error(
            f"Failed to setup intelligence hooks: {str(e)}",
            exc_info=True
        )
        raise


def teardown_intelligence_hooks():
    """
    移除所有智能层数据库事件监听器
    
    此函数用于测试或应用关闭时清理事件监听器。
    """
    try:
        # 导入模型
        from models import UserMiner, Miner
        
        # 移除UserMiner事件监听器
        event.remove(UserMiner, 'after_insert', on_user_miner_after_insert)
        event.remove(UserMiner, 'after_update', on_user_miner_after_update)
        event.remove(UserMiner, 'after_delete', on_user_miner_after_delete)
        
        # 移除Miner事件监听器
        event.remove(Miner, 'after_insert', on_miner_after_insert)
        
        logger.info("Intelligence database hooks removed successfully")
        
    except Exception as e:
        logger.error(
            f"Failed to teardown intelligence hooks: {str(e)}",
            exc_info=True
        )
        raise


# ============================================================================
# Utility Functions - 工具函数
# ============================================================================

def is_hooks_registered() -> bool:
    """
    检查事件监听器是否已注册
    
    Returns:
        bool: 如果所有监听器都已注册则返回True
    """
    try:
        from models import UserMiner, Miner
        
        # 检查UserMiner监听器
        user_miner_has_insert = event.contains(UserMiner, 'after_insert', on_user_miner_after_insert)
        user_miner_has_update = event.contains(UserMiner, 'after_update', on_user_miner_after_update)
        user_miner_has_delete = event.contains(UserMiner, 'after_delete', on_user_miner_after_delete)
        
        # 检查Miner监听器
        miner_has_insert = event.contains(Miner, 'after_insert', on_miner_after_insert)
        
        return all([
            user_miner_has_insert,
            user_miner_has_update,
            user_miner_has_delete,
            miner_has_insert
        ])
        
    except Exception as e:
        logger.error(f"Failed to check hooks registration: {str(e)}")
        return False
