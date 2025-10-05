"""
Data Analytics Center Routes
数据分析中心路由模块 - 统一数据分析功能入口
"""

from flask import Blueprint, render_template, session, g
from auth import login_required
from decorators import requires_role
from translations import get_translation
import logging

logger = logging.getLogger(__name__)

analytics_center_bp = Blueprint('analytics_center', __name__, url_prefix='/operations')


@analytics_center_bp.route('/analytics')
@login_required
@requires_role(['mining_site', 'admin', 'owner'])
def analytics_center():
    """
    Data Analytics Center - 数据分析中心主页
    整合所有数据分析功能的统一界面
    
    集成功能:
    1. 技术指标分析 (Technical Analysis) - /analytics
    2. 市场数据分析 (Market Analysis) - /analytics#market
    3. 网络历史数据 (Network History) - /network-history
    4. ROI热力图 (ROI Heatmap) - /analytics#roi-heatmap
    """
    try:
        current_lang = getattr(g, 'language', session.get('language', 'zh'))
        user_role = session.get('role', 'guest')
        
        logger.info(f"User accessing Data Analytics Center - Role: {user_role}, Language: {current_lang}")
        
        return render_template(
            'analytics_center.html',
            current_lang=current_lang,
            user_role=user_role
        )
        
    except Exception as e:
        logger.error(f"Error loading Data Analytics Center: {e}", exc_info=True)
        return render_template(
            'errors/500.html',
            error_message=str(e)
        ), 500
