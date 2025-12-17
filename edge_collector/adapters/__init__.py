"""
Miner Control Adapters
矿机控制适配器

Provides unified interface for controlling different miner types.
"""
from .base import MinerAdapter, AdapterResult
from .cgminer_adapter import CGMinerAdapter
from .simulated_adapter import SimulatedAdapter

__all__ = ['MinerAdapter', 'AdapterResult', 'CGMinerAdapter', 'SimulatedAdapter']
