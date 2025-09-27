"""
挖矿核心模块路由包
Mining Core Module Routes Package

独立路由模块，无用户认证依赖
"""

from flask import Blueprint

# 导出所有蓝图
__all__ = ['calculator_bp', 'analytics_bp', 'batch_bp']