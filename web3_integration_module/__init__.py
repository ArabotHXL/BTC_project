"""
Web3集成模块
Web3 Integration Module

完整独立的Web3、区块链、加密货币支付和NFT系统集成模块
"""

__version__ = '1.0.0'
__author__ = 'Web3 Integration Team'
__description__ = 'Independent Web3 integration service for blockchain, payments, and NFT functionality'

from .app import create_app, db

__all__ = ['create_app', 'db']