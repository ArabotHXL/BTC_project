
"""
托管功能模块
支持托管商和客户的完整管理流程
"""
from flask import Blueprint

# 创建托管模块蓝图
hosting_bp = Blueprint(
    'hosting',
    __name__,
    template_folder='templates',
    static_folder='static',
    url_prefix='/hosting'
)

from . import routes
