"""
CRM Center Routes
CRM中心路由模块 - 统一CRM功能入口
"""

from flask import Blueprint, render_template, session, g
from auth import login_required
from decorators import requires_role
from translations import get_translation
import logging

logger = logging.getLogger(__name__)

crm_center_bp = Blueprint('crm_center', __name__, url_prefix='/operations')


@crm_center_bp.route('/crm')
@login_required
@requires_role(['admin', 'owner'])
def crm_center():
    """
    CRM Center - CRM中心主页
    整合所有CRM功能的统一界面
    
    集成功能:
    1. CRM仪表盘 (CRM Dashboard) - /crm
    2. 客户管理 (Customer Management) - /crm/customers
    3. 矿场客户 (Mining Customers) - /mine/customers
    4. 用户权限管理 (User Access) - /user-access
    5. 登录记录 (Login Records) - /login-records
    
    权限要求: admin 或 owner
    """
    try:
        current_lang = getattr(g, 'language', session.get('language', 'zh'))
        user_role = session.get('role', 'guest')
        
        logger.info(f"User accessing CRM Center - Role: {user_role}, Language: {current_lang}")
        
        return render_template(
            'crm_center.html',
            current_lang=current_lang,
            user_role=user_role
        )
        
    except Exception as e:
        logger.error(f"Error loading CRM Center: {e}", exc_info=True)
        return render_template(
            'errors/500.html',
            error_message=str(e)
        ), 500
