"""
Billing routes for subscription management.
"""
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, flash
from auth import login_required
import logging

# Create blueprint
billing_bp = Blueprint('billing', __name__)

logger = logging.getLogger(__name__)

@billing_bp.route('/plans')
@login_required
def show_plans():
    """显示订阅计划页面"""
    try:
        return render_template('billing_plans.html')
    except Exception as e:
        logger.error(f"Error loading billing plans: {e}")
        flash('订阅计划页面暂时不可用', 'error')
        return redirect(url_for('index'))

@billing_bp.route('/subscribe/<plan_id>')
@login_required
def subscribe(plan_id):
    """订阅计划处理"""
    try:
        # 暂时返回维护页面
        flash('订阅功能正在维护中，请稍后再试', 'info')
        return redirect(url_for('billing.show_plans'))
    except Exception as e:
        logger.error(f"Error processing subscription: {e}")
        flash('订阅处理失败', 'error')
        return redirect(url_for('billing.show_plans'))