"""
HashInsight Edge Collector - 矿场边缘数据采集器
Mining Farm Edge Data Collector

模块结构:
- models.py: 数据模型 (BoardStatus, MinerSnapshot)
- cgminer_client.py: CGMiner TCP客户端 (带重试机制)
- parsers.py: 板级数据解析器
- main.py: CLI测试工具
- cgminer_collector.py: 批量采集主程序
"""

from .models import BoardStatus, MinerSnapshot
from .cgminer_client import CGMinerClient, CGMinerError
from .parsers import parse_board_health, extract_board_indices, determine_board_status

__all__ = [
    'BoardStatus',
    'MinerSnapshot', 
    'CGMinerClient',
    'CGMinerError',
    'parse_board_health',
    'extract_board_indices',
    'determine_board_status'
]
