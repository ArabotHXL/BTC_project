"""
客户视角模块
为托管平台的客户提供专用界面和功能
"""
from flask import Blueprint

# 创建客户模块的Blueprint
client_bp = Blueprint(
    'client', 
    __name__,
    template_folder='templates',
    static_folder='static',
    url_prefix='/client'
)

# 导入路由，确保Blueprint注册路由
from . import routes