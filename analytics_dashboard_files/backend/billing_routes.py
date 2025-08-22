"""
Billing and Subscription Management Routes
提供Stripe集成和订阅管理功能
"""

from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, flash
import logging
import os
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# 创建蓝图
billing_bp = Blueprint('billing', __name__)

# 模拟Stripe配置（生产环境需要真实密钥）
STRIPE_ENABLED = os.environ.get('STRIPE_SECRET_KEY') is not None

@billing_bp.route('/subscription')
def subscription_page():
    """订阅管理页面"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return redirect(url_for('login'))
        
        # 模拟订阅数据（生产环境应从数据库获取）
        subscription_data = {
            'plan': 'Core',
            'status': 'active',
            'next_billing': (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
            'amount': 20.00,
            'currency': 'USD'
        }
        
        return render_template('billing/subscription.html', 
                             subscription=subscription_data,
                             stripe_enabled=STRIPE_ENABLED)
    except Exception as e:
        logger.error(f"订阅页面错误: {e}")
        flash('无法加载订阅信息', 'error')
        return redirect(url_for('dashboard'))

@billing_bp.route('/api/billing/create-checkout-session', methods=['POST'])
def create_checkout_session():
    """创建Stripe结账会话"""
    try:
        if not STRIPE_ENABLED:
            return jsonify({
                'success': False,
                'error': 'Stripe未配置'
            }), 400
        
        data = request.get_json()
        plan = data.get('plan', 'core')
        
        # 模拟Stripe会话创建
        # 生产环境需要实际Stripe集成
        session_data = {
            'id': f'cs_test_{datetime.now().timestamp()}',
            'url': 'https://checkout.stripe.com/pay/example'
        }
        
        return jsonify({
            'success': True,
            'session_id': session_data['id'],
            'checkout_url': session_data['url']
        })
        
    except Exception as e:
        logger.error(f"创建结账会话错误: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@billing_bp.route('/api/billing/webhook', methods=['POST'])
def stripe_webhook():
    """Stripe Webhook处理"""
    try:
        if not STRIPE_ENABLED:
            return jsonify({'error': 'Stripe未配置'}), 400
        
        # 模拟webhook处理
        # 生产环境需要验证Stripe签名
        event_type = request.headers.get('Stripe-Event-Type', 'unknown')
        
        logger.info(f"收到Stripe webhook: {event_type}")
        
        return jsonify({'received': True})
        
    except Exception as e:
        logger.error(f"Webhook处理错误: {e}")
        return jsonify({'error': str(e)}), 500

@billing_bp.route('/api/billing/subscription-status')
def get_subscription_status():
    """获取订阅状态"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({
                'success': False,
                'error': '未登录'
            }), 401
        
        # 模拟订阅状态（生产环境从数据库获取）
        status = {
            'plan': 'Core',
            'status': 'active',
            'expires_at': (datetime.now() + timedelta(days=30)).isoformat(),
            'features': {
                'advanced_analytics': True,
                'api_access': True,
                'export_data': True,
                'priority_support': True
            }
        }
        
        return jsonify({
            'success': True,
            'subscription': status
        })
        
    except Exception as e:
        logger.error(f"获取订阅状态错误: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def register_billing_routes(app):
    """注册计费路由到应用"""
    try:
        app.register_blueprint(billing_bp, url_prefix='/billing')
        logger.info("Billing routes registered successfully")
    except Exception as e:
        logger.error(f"Failed to register billing routes: {e}")

# 兼容性导出
__all__ = ['billing_bp', 'register_billing_routes']