"""
Event Contracts - Standardized Event Payload Definitions
事件契约 - 标准化事件载荷定义

Defines all event types and Pydantic models for event payloads in HashInsight.
使用Pydantic模型统一所有事件格式，符合HashInsight架构文档要求。
"""

from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional, Any, Dict, List
from enum import Enum
import uuid


# ============================================================================
# Event Type Enumeration - 事件类型枚举
# ============================================================================

class EventType(str, Enum):
    """事件类型枚举 - Event Type Enumeration"""
    
    # Miner Events - 矿机事件
    MINER_ADDED = "miner.added"
    MINER_UPDATED = "miner.updated"
    MINER_DELETED = "miner.deleted"
    MINER_STATUS_CHANGED = "miner.status_changed"
    MINER_PERFORMANCE_UPDATED = "miner.performance_updated"
    
    # Portfolio Events - 投资组合事件
    PORTFOLIO_RECALCULATED = "portfolio.recalculated"
    
    # Operations Events - 运营事件
    OPS_PLAN_CREATED = "ops.plan_created"
    OPS_PLAN_APPLIED = "ops.plan_applied"
    
    # Treasury Events - 财务事件
    TREASURY_TRADE_EXECUTED = "treasury.trade_executed"
    
    # Web3 Events - Web3事件
    WEB3_MINT_REQUESTED = "web3.mint_requested"
    WEB3_MINT_COMPLETED = "web3.mint_completed"


# ============================================================================
# Base Event Payload - 基础事件载荷
# ============================================================================

class BaseEventPayload(BaseModel):
    """
    基础事件payload模型
    Base Event Payload Model
    
    所有事件载荷的基类，提供统一的事件结构。
    """
    model_config = ConfigDict(
        use_enum_values=True,
        json_encoders={datetime: lambda v: v.isoformat()}
    )
    
    event_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="事件ID - Event ID"
    )
    event_type: EventType = Field(
        ...,
        description="事件类型 - Event Type"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="事件时间戳（UTC）- Event Timestamp (UTC)"
    )
    user_id: int = Field(
        ...,
        description="用户ID - User ID"
    )
    correlation_id: Optional[str] = Field(
        None,
        description="关联ID（用于追踪）- Correlation ID (for tracking)"
    )


# ============================================================================
# Miner Events - 矿机事件
# ============================================================================

class MinerAddedPayload(BaseEventPayload):
    """
    矿机添加事件载荷
    Miner Added Event Payload
    """
    event_type: EventType = Field(
        default=EventType.MINER_ADDED,
        description="事件类型"
    )
    miner_id: int = Field(
        ...,
        description="矿机ID - Miner ID"
    )
    miner_model: str = Field(
        ...,
        description="矿机型号 - Miner Model"
    )
    hashrate_th: float = Field(
        ...,
        description="算力（TH/s）- Hashrate in TH/s",
        gt=0
    )
    power_consumption_w: int = Field(
        ...,
        description="功耗（W）- Power Consumption in Watts",
        gt=0
    )
    quantity: int = Field(
        default=1,
        description="数量 - Quantity",
        ge=1
    )


class MinerUpdatedPayload(BaseEventPayload):
    """
    矿机更新事件载荷
    Miner Updated Event Payload
    """
    event_type: EventType = Field(
        default=EventType.MINER_UPDATED,
        description="事件类型"
    )
    miner_id: int = Field(
        ...,
        description="矿机ID - Miner ID"
    )
    updated_fields: Dict[str, Any] = Field(
        ...,
        description="更新的字段 - Updated Fields"
    )


class MinerDeletedPayload(BaseEventPayload):
    """
    矿机删除事件载荷
    Miner Deleted Event Payload
    """
    event_type: EventType = Field(
        default=EventType.MINER_DELETED,
        description="事件类型"
    )
    miner_id: int = Field(
        ...,
        description="矿机ID - Miner ID"
    )


class MinerStatusChangedPayload(BaseEventPayload):
    """
    矿机状态变更事件载荷
    Miner Status Changed Event Payload
    """
    event_type: EventType = Field(
        default=EventType.MINER_STATUS_CHANGED,
        description="事件类型"
    )
    miner_id: int = Field(
        ...,
        description="矿机ID - Miner ID"
    )
    old_status: str = Field(
        ...,
        description="旧状态 - Old Status"
    )
    new_status: str = Field(
        ...,
        description="新状态 - New Status"
    )


class MinerPerformanceUpdatedPayload(BaseEventPayload):
    """
    矿机性能更新事件载荷
    Miner Performance Updated Event Payload
    """
    event_type: EventType = Field(
        default=EventType.MINER_PERFORMANCE_UPDATED,
        description="事件类型"
    )
    miner_id: int = Field(
        ...,
        description="矿机ID - Miner ID"
    )
    current_hashrate_th: float = Field(
        ...,
        description="当前算力（TH/s）- Current Hashrate in TH/s",
        gt=0
    )
    efficiency_change_pct: Optional[float] = Field(
        None,
        description="效率变化百分比 - Efficiency Change Percentage"
    )


# ============================================================================
# Portfolio Events - 投资组合事件
# ============================================================================

class PortfolioRecalculatedPayload(BaseEventPayload):
    """
    投资组合重新计算事件载荷
    Portfolio Recalculated Event Payload
    """
    event_type: EventType = Field(
        default=EventType.PORTFOLIO_RECALCULATED,
        description="事件类型"
    )
    recalculation_id: str = Field(
        ...,
        description="重算ID - Recalculation ID"
    )
    source_event_ids: List[str] = Field(
        ...,
        description="源事件ID列表 - Source Event IDs"
    )
    metrics: Dict[str, Any] = Field(
        ...,
        description="指标数据（total_hashrate, total_power等）- Metrics Data"
    )


# ============================================================================
# Operations Events - 运营事件
# ============================================================================

class OpsPlanCreatedPayload(BaseEventPayload):
    """
    运营计划创建事件载荷
    Operations Plan Created Event Payload
    """
    event_type: EventType = Field(
        default=EventType.OPS_PLAN_CREATED,
        description="事件类型"
    )
    schedule_date: str = Field(
        ...,
        description="计划日期（YYYY-MM-DD）- Schedule Date",
        pattern=r"^\d{4}-\d{2}-\d{2}$"
    )
    plan_id: str = Field(
        ...,
        description="计划ID - Plan ID"
    )
    optimization_status: str = Field(
        ...,
        description="优化状态 - Optimization Status"
    )


class OpsPlanAppliedPayload(BaseEventPayload):
    """
    运营计划应用事件载荷
    Operations Plan Applied Event Payload
    """
    event_type: EventType = Field(
        default=EventType.OPS_PLAN_APPLIED,
        description="事件类型"
    )
    schedule_date: str = Field(
        ...,
        description="计划日期（YYYY-MM-DD）- Schedule Date",
        pattern=r"^\d{4}-\d{2}-\d{2}$"
    )
    plan_id: str = Field(
        ...,
        description="计划ID - Plan ID"
    )
    execution_status: str = Field(
        ...,
        description="执行状态 - Execution Status"
    )


# ============================================================================
# Treasury Events - 财务事件
# ============================================================================

class TreasuryTradeExecutedPayload(BaseEventPayload):
    """
    财务交易执行事件载荷
    Treasury Trade Executed Event Payload
    """
    event_type: EventType = Field(
        default=EventType.TREASURY_TRADE_EXECUTED,
        description="事件类型"
    )
    trade_id: str = Field(
        ...,
        description="交易ID - Trade ID"
    )
    strategy_name: str = Field(
        ...,
        description="策略名称 - Strategy Name"
    )
    btc_amount: float = Field(
        ...,
        description="BTC数量 - BTC Amount"
    )
    usd_amount: float = Field(
        ...,
        description="USD金额 - USD Amount"
    )
    execution_price: float = Field(
        ...,
        description="执行价格 - Execution Price",
        gt=0
    )
    exchange: str = Field(
        ...,
        description="交易所 - Exchange"
    )


# ============================================================================
# Web3 Events - Web3事件
# ============================================================================

class Web3MintRequestedPayload(BaseEventPayload):
    """
    Web3铸造请求事件载荷
    Web3 Mint Requested Event Payload
    """
    event_type: EventType = Field(
        default=EventType.WEB3_MINT_REQUESTED,
        description="事件类型"
    )
    mint_id: str = Field(
        ...,
        description="铸造ID - Mint ID"
    )
    contract_address: str = Field(
        ...,
        description="合约地址 - Contract Address"
    )
    token_type: str = Field(
        ...,
        description="代币类型（SLA_NFT, HASHRATE_TOKEN）- Token Type"
    )
    metadata: Dict[str, Any] = Field(
        ...,
        description="元数据 - Metadata"
    )


class Web3MintCompletedPayload(BaseEventPayload):
    """
    Web3铸造完成事件载荷
    Web3 Mint Completed Event Payload
    """
    event_type: EventType = Field(
        default=EventType.WEB3_MINT_COMPLETED,
        description="事件类型"
    )
    mint_id: str = Field(
        ...,
        description="铸造ID - Mint ID"
    )
    transaction_hash: str = Field(
        ...,
        description="交易哈希 - Transaction Hash"
    )
    token_id: int = Field(
        ...,
        description="代币ID - Token ID"
    )
    contract_address: str = Field(
        ...,
        description="合约地址 - Contract Address"
    )


# ============================================================================
# Factory Function - 工厂函数
# ============================================================================

def create_event_payload(event_type: EventType, **kwargs) -> BaseEventPayload:
    """
    工厂函数：根据事件类型创建对应payload
    Factory Function: Create event payload based on event type
    
    Args:
        event_type: 事件类型 - Event Type
        **kwargs: 事件参数 - Event Parameters
        
    Returns:
        BaseEventPayload: 事件载荷实例 - Event Payload Instance
        
    Raises:
        ValueError: 未知的事件类型 - Unknown event type
        
    Example:
        >>> payload = create_event_payload(
        ...     EventType.MINER_ADDED,
        ...     event_id="evt_123",
        ...     user_id=1,
        ...     miner_id=101,
        ...     miner_model="Antminer S19 Pro",
        ...     hashrate_th=110.0,
        ...     power_consumption_w=3250
        ... )
    """
    payload_map = {
        EventType.MINER_ADDED: MinerAddedPayload,
        EventType.MINER_UPDATED: MinerUpdatedPayload,
        EventType.MINER_DELETED: MinerDeletedPayload,
        EventType.MINER_STATUS_CHANGED: MinerStatusChangedPayload,
        EventType.MINER_PERFORMANCE_UPDATED: MinerPerformanceUpdatedPayload,
        EventType.PORTFOLIO_RECALCULATED: PortfolioRecalculatedPayload,
        EventType.OPS_PLAN_CREATED: OpsPlanCreatedPayload,
        EventType.OPS_PLAN_APPLIED: OpsPlanAppliedPayload,
        EventType.TREASURY_TRADE_EXECUTED: TreasuryTradeExecutedPayload,
        EventType.WEB3_MINT_REQUESTED: Web3MintRequestedPayload,
        EventType.WEB3_MINT_COMPLETED: Web3MintCompletedPayload,
    }
    
    payload_class = payload_map.get(event_type)
    if not payload_class:
        raise ValueError(f"Unknown event type: {event_type}")
    
    return payload_class(event_type=event_type, **kwargs)


# ============================================================================
# Validation Helper - 验证辅助函数
# ============================================================================

def validate_event_payload(payload: BaseEventPayload) -> bool:
    """
    验证事件载荷是否有效
    Validate if event payload is valid
    
    Args:
        payload: 事件载荷 - Event Payload
        
    Returns:
        bool: 是否有效 - Is Valid
    """
    try:
        # Pydantic will validate on creation
        # This is mainly for re-validation if needed
        payload.model_validate(payload.model_dump())
        return True
    except Exception:
        return False
