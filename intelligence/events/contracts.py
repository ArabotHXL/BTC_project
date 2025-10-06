"""
Event Contracts - Event Type Constants and Data Structures
事件契约 - 事件类型常量和数据结构

Defines all event types and their corresponding data structures for the intelligence layer.
"""

from typing import Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict


# ============================================================================
# Event Type Constants - 事件类型常量
# ============================================================================

class EventTypes:
    """事件类型常量集合"""
    
    # Miner Events - 矿机事件
    MINER_ADDED = "miner.added"
    MINER_UPDATED = "miner.updated"
    MINER_DELETED = "miner.deleted"
    MINER_STATUS_CHANGED = "miner.status_changed"
    MINER_PERFORMANCE_UPDATED = "miner.performance_updated"
    
    # Portfolio Events - 投资组合事件
    PORTFOLIO_CREATED = "portfolio.created"
    PORTFOLIO_UPDATED = "portfolio.updated"
    PORTFOLIO_DELETED = "portfolio.deleted"
    PORTFOLIO_MINER_ADDED = "portfolio.miner_added"
    PORTFOLIO_MINER_REMOVED = "portfolio.miner_removed"
    
    # User Events - 用户事件
    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    USER_DELETED = "user.deleted"
    USER_ROLE_CHANGED = "user.role_changed"
    
    # Calculation Events - 计算事件
    CALCULATION_STARTED = "calculation.started"
    CALCULATION_COMPLETED = "calculation.completed"
    CALCULATION_FAILED = "calculation.failed"
    
    # SLA Events - SLA事件
    SLA_METRICS_RECORDED = "sla.metrics_recorded"
    SLA_CERTIFICATE_REQUESTED = "sla.certificate_requested"
    SLA_CERTIFICATE_MINTED = "sla.certificate_minted"
    
    # Blockchain Events - 区块链事件
    BLOCKCHAIN_VERIFICATION_STARTED = "blockchain.verification_started"
    BLOCKCHAIN_VERIFICATION_COMPLETED = "blockchain.verification_completed"
    BLOCKCHAIN_VERIFICATION_FAILED = "blockchain.verification_failed"
    
    # Analytics Events - 分析事件
    ANALYTICS_REPORT_GENERATED = "analytics.report_generated"
    ANALYTICS_INSIGHT_DETECTED = "analytics.insight_detected"


# ============================================================================
# Aggregate Type Constants - 聚合类型常量
# ============================================================================

class AggregateTypes:
    """聚合类型常量"""
    MINER = "miner"
    PORTFOLIO = "portfolio"
    USER = "user"
    CALCULATION = "calculation"
    SLA = "sla"
    BLOCKCHAIN = "blockchain"
    ANALYTICS = "analytics"


# ============================================================================
# Event Data Classes - 事件数据类
# ============================================================================

@dataclass
class MinerEventData:
    """矿机事件数据"""
    miner_id: int
    model_name: str
    hashrate: Optional[float] = None
    power_consumption: Optional[int] = None
    efficiency: Optional[float] = None
    status: Optional[str] = None
    owner_id: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)


@dataclass
class PortfolioEventData:
    """投资组合事件数据"""
    portfolio_id: int
    user_id: int
    portfolio_name: Optional[str] = None
    total_hashrate: Optional[float] = None
    total_power: Optional[int] = None
    miner_count: Optional[int] = None
    miner_ids: Optional[list] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)


@dataclass
class UserEventData:
    """用户事件数据"""
    user_id: int
    username: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    previous_role: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)


@dataclass
class CalculationEventData:
    """计算事件数据"""
    calculation_id: str
    calculation_type: str
    user_id: Optional[int] = None
    input_parameters: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    duration_ms: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)


@dataclass
class SLAEventData:
    """SLA事件数据"""
    sla_id: int
    month_year: int
    composite_score: Optional[float] = None
    uptime_percentage: Optional[float] = None
    certificate_token_id: Optional[str] = None
    recipient_address: Optional[str] = None
    transaction_hash: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)


@dataclass
class BlockchainEventData:
    """区块链事件数据"""
    record_id: int
    blockchain_type: str
    transaction_hash: Optional[str] = None
    block_number: Optional[int] = None
    contract_address: Optional[str] = None
    verification_status: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)


@dataclass
class AnalyticsEventData:
    """分析事件数据"""
    report_id: str
    report_type: str
    user_id: Optional[int] = None
    insight_type: Optional[str] = None
    insight_data: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)


# ============================================================================
# Helper Functions - 辅助函数
# ============================================================================

def create_event_payload(event_data, **extra_fields) -> Dict[str, Any]:
    """
    创建事件载荷
    
    Args:
        event_data: 事件数据对象（dataclass实例）
        **extra_fields: 额外字段
        
    Returns:
        Dict[str, Any]: 事件载荷字典
    """
    if hasattr(event_data, 'to_dict'):
        payload = event_data.to_dict()
    elif isinstance(event_data, dict):
        payload = event_data.copy()
    else:
        payload = {}
    
    # 添加时间戳
    payload['timestamp'] = datetime.utcnow().isoformat()
    
    # 添加额外字段
    payload.update(extra_fields)
    
    return payload


def validate_event_type(event_type: str) -> bool:
    """
    验证事件类型是否有效
    
    Args:
        event_type: 事件类型字符串
        
    Returns:
        bool: 是否有效
    """
    valid_types = [
        getattr(EventTypes, attr) 
        for attr in dir(EventTypes) 
        if not attr.startswith('_')
    ]
    return event_type in valid_types


def validate_aggregate_type(aggregate_type: str) -> bool:
    """
    验证聚合类型是否有效
    
    Args:
        aggregate_type: 聚合类型字符串
        
    Returns:
        bool: 是否有效
    """
    valid_types = [
        getattr(AggregateTypes, attr) 
        for attr in dir(AggregateTypes) 
        if not attr.startswith('_')
    ]
    return aggregate_type in valid_types
