"""
HashInsight CDC Platform - Workers Module
Kafka消费者Workers模块

包含：
- common: 通用基类和工具函数
- portfolio_consumer: Portfolio重算消费者
- intel_consumer: Intelligence预测消费者

Author: HashInsight Team
Version: 1.0.0
"""

# 导出核心类和函数
from .common import (
    KafkaConsumerBase,
    format_error_message,
    extract_user_id,
    validate_event_payload
)

from .portfolio_consumer import PortfolioConsumer
from .intel_consumer import IntelligenceConsumer

__all__ = [
    'KafkaConsumerBase',
    'PortfolioConsumer',
    'IntelligenceConsumer',
    'format_error_message',
    'extract_user_id',
    'validate_event_payload'
]

__version__ = '1.0.0'
