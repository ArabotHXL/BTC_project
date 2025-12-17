
"""
托管功能模块
支持托管商和客户的完整管理流程
"""
from flask import Blueprint

# 创建托管模块蓝图 - 使用唯一名称避免冲突
hosting_bp = Blueprint(
    'hosting_service_bp',  # 使用更具体的名称避免冲突
    __name__,
    template_folder='templates',
    static_folder='static',
    url_prefix='/hosting'
)

from . import routes
