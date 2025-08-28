"""
CRM客户关系管理模块
独立的客户管理系统，包含自己的路由、模板和静态资源
"""
from flask import Blueprint

# 创建CRM模块蓝图
crm_bp = Blueprint(
    'crm',
    __name__,
    template_folder='templates',
    static_folder='static',
    static_url_path='/crm/static'
)

from . import routes