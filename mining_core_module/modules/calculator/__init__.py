"""
挖矿计算器模块
独立的页面模块，包含自己的路由、模板和静态资源
"""
from flask import Blueprint

# 创建计算器模块蓝图
calculator_bp = Blueprint(
    'calculator',
    __name__,
    template_folder='templates',
    static_folder='static',
    static_url_path='/calculator/static'
)

from . import routes