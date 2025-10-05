"""
Web3 Center Routes
Web3中心路由模块 - 统一Web3功能入口
"""

from flask import Blueprint, render_template, session, g
from auth import login_required
from decorators import requires_role
from translations import get_translation
import logging

logger = logging.getLogger(__name__)

web3_center_bp = Blueprint('web3_center', __name__, url_prefix='/operations')


@web3_center_bp.route('/web3')
@login_required
@requires_role(['mining_site', 'admin', 'owner'])
def web3_center():
    """
    Web3 Center - Web3中心主页
    整合所有Web3功能的统一界面
    
    集成功能:
    1. Web3概览 (Web3 Overview) - /web3-dashboard
    2. 区块链验证 (Blockchain Verification) - /blockchain-verification
    3. SLA NFT管理 (SLA NFT Manager) - /sla-nft-manager
    4. 透明度验证中心 (Transparency Center) - /transparency-verification-center
    5. 加密支付管理 (Crypto Payment) - /crypto-payment-dashboard (需要admin权限)
    """
    try:
        current_lang = getattr(g, 'language', session.get('language', 'zh'))
        user_role = session.get('role', 'guest')
        
        logger.info(f"User accessing Web3 Center - Role: {user_role}, Language: {current_lang}")
        
        return render_template(
            'web3_center.html',
            current_lang=current_lang,
            user_role=user_role
        )
        
    except Exception as e:
        logger.error(f"Error loading Web3 Center: {e}", exc_info=True)
        return render_template(
            'errors/500.html',
            error_message=str(e)
        ), 500
