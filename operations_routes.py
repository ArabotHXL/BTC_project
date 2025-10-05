"""
Mining Operations Center Routes
统一的挖矿运营中心路由模块
"""

from flask import Blueprint, render_template, session, g
from auth import login_required
from decorators import requires_role
from translations import get_translation
import logging

logger = logging.getLogger(__name__)

operations_bp = Blueprint('operations', __name__, url_prefix='/operations')


@operations_bp.route('/mining')
@login_required
@requires_role(['mining_site', 'admin', 'owner'])
def mining_operations_center():
    """
    Mining Operations Center - 挖矿运营中心主页
    整合所有挖矿相关功能的统一界面
    """
    try:
        current_lang = getattr(g, 'language', session.get('language', 'zh'))
        user_role = session.get('role', 'guest')
        
        logger.info(f"User accessing Mining Operations Center - Role: {user_role}, Language: {current_lang}")
        
        return render_template(
            'mining_operations_center.html',
            current_lang=current_lang,
            user_role=user_role
        )
        
    except Exception as e:
        logger.error(f"Error loading Mining Operations Center: {e}", exc_info=True)
        return render_template(
            'errors/500.html',
            error_message=str(e)
        ), 500
