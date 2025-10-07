"""
Events Module - Standardized Event System
事件模块 - 标准化事件系统

This module provides standardized event contracts using Pydantic models
for all events in the HashInsight system.
"""

from .contracts import (
    # Event Type Enum
    EventType,
    
    # Base Event Payload
    BaseEventPayload,
    
    # Miner Event Payloads
    MinerAddedPayload,
    MinerUpdatedPayload,
    MinerDeletedPayload,
    MinerStatusChangedPayload,
    MinerPerformanceUpdatedPayload,
    
    # Portfolio Event Payloads
    PortfolioRecalculatedPayload,
    
    # Operations Event Payloads
    OpsPlanCreatedPayload,
    OpsPlanAppliedPayload,
    
    # Treasury Event Payloads
    TreasuryTradeExecutedPayload,
    
    # Web3 Event Payloads
    Web3MintRequestedPayload,
    Web3MintCompletedPayload,
    
    # Factory Function
    create_event_payload,
    
    # Validation Helper
    validate_event_payload,
)

__all__ = [
    # Event Type Enum
    "EventType",
    
    # Base Event Payload
    "BaseEventPayload",
    
    # Miner Event Payloads
    "MinerAddedPayload",
    "MinerUpdatedPayload",
    "MinerDeletedPayload",
    "MinerStatusChangedPayload",
    "MinerPerformanceUpdatedPayload",
    
    # Portfolio Event Payloads
    "PortfolioRecalculatedPayload",
    
    # Operations Event Payloads
    "OpsPlanCreatedPayload",
    "OpsPlanAppliedPayload",
    
    # Treasury Event Payloads
    "TreasuryTradeExecutedPayload",
    
    # Web3 Event Payloads
    "Web3MintRequestedPayload",
    "Web3MintCompletedPayload",
    
    # Factory Function
    "create_event_payload",
    
    # Validation Helper
    "validate_event_payload",
]
