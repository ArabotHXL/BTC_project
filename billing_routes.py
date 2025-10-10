"""
Billing Routes - 计费和支付路由
为BTC Mining Calculator平台提供完整的订阅和支付管理

功能包括：
- 订阅计划展示和选择
- 加密货币支付处理
- 支付状态监控
- 支付历史和收据
- 订阅管理
"""

import os
import logging
import json
from datetime import datetime, timedelta
from flask import (
    Blueprint, render_template, request, jsonify, session, 
    redirect, url_for, flash, current_app
)
from sqlalchemy.exc import SQLAlchemyError

# 本地导入
from auth import login_required
from models_subscription import (
    SubscriptionPlan, UserSubscription, Payment,
    PaymentStatus, PaymentMethodType, CryptoCurrency,
    PlanType, SubscriptionStatus
)
from crypto_payment_service import crypto_payment_service
from models import User
from db import db

logger = logging.getLogger(__name__)

# 创建Blueprint
billing_bp = Blueprint('billing', __name__, url_prefix='/billing')

@billing_bp.route('/plans')
def plans():
    """订阅计划页面"""
    try:
        # 获取所有可用的订阅计划
        subscription_plans = SubscriptionPlan.query.all()
        
        # 如果没有计划，创建默认计划
        if not subscription_plans:
            create_default_plans()
            subscription_plans = SubscriptionPlan.query.all()
        
        # 获取当前用户的订阅状态
        current_subscription = None
        if session.get('authenticated'):
            user_email = session.get('email')
            user = User.query.filter_by(email=user_email).first()
            if user:
                current_subscription = UserSubscription.query.filter_by(
                    user_id=user.id,
                    status=SubscriptionStatus.ACTIVE
                ).first()
        
        return render_template('billing/plans.html', 
                             plans=subscription_plans,
                             current_subscription=current_subscription,
                             current_lang=session.get('language', 'zh'))
                             
    except Exception as e:
        logger.error(f"获取订阅计划失败: {e}")
        flash('获取订阅计划失败，请稍后重试', 'error')
        return redirect(url_for('index'))

@billing_bp.route('/subscribe/<int:plan_id>')
@login_required
def subscribe(plan_id):
    """订阅页面 - 显示支付选项"""
    try:
        # 获取订阅计划
        plan = SubscriptionPlan.query.get_or_404(plan_id)
        
        # 获取当前用户
        user_email = session.get('email')
        user = User.query.filter_by(email=user_email).first()
        if not user:
            flash('用户未找到', 'error')
            return redirect(url_for('billing.plans'))
        
        # 检查用户是否已有活跃订阅
        existing_subscription = UserSubscription.query.filter_by(
            user_id=user.id,
            status=SubscriptionStatus.ACTIVE
        ).first()
        
        if existing_subscription:
            flash('您已经有活跃的订阅', 'warning')
            return redirect(url_for('billing.manage'))
        
        # 支持的加密货币
        supported_cryptos = [
            {'code': 'BTC', 'name': 'Bitcoin', 'symbol': '₿'},
            {'code': 'ETH', 'name': 'Ethereum', 'symbol': 'Ξ'},
            {'code': 'USDC', 'name': 'USD Coin', 'symbol': '$'}
        ]
        
        return render_template('billing/subscribe.html',
                             plan=plan,
                             supported_cryptos=supported_cryptos,
                             current_lang=session.get('language', 'zh'))
                             
    except Exception as e:
        logger.error(f"订阅页面错误: {e}")
        flash('访问订阅页面失败', 'error')
        return redirect(url_for('billing.plans'))

@billing_bp.route('/process-payment', methods=['POST'])
@login_required
def process_payment():
    """处理支付请求"""
    try:
        data = request.get_json()
        
        # 验证必需字段
        required_fields = ['plan_id', 'payment_method', 'billing_cycle']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'缺少必需字段: {field}'}), 400
        
        plan_id = data['plan_id']
        payment_method = data['payment_method']
        billing_cycle = data['billing_cycle']  # 'monthly' or 'yearly'
        
        # 获取订阅计划
        plan = SubscriptionPlan.query.get(plan_id)
        if not plan:
            return jsonify({'success': False, 'error': '订阅计划不存在'}), 404
        
        # 获取当前用户
        user_email = session.get('email')
        user = User.query.filter_by(email=user_email).first()
        if not user:
            return jsonify({'success': False, 'error': '用户未找到'}), 401
        
        # 计算支付金额
        if billing_cycle == 'yearly':
            amount = plan.price_yearly
        else:
            amount = plan.price_monthly
        
        if amount <= 0:
            return jsonify({'success': False, 'error': '免费计划无需支付'}), 400
        
        # 创建用户订阅记录
        subscription = UserSubscription(
            user_id=user.id,
            plan_id=plan.id,
            status=SubscriptionStatus.PENDING,
            started_at=datetime.utcnow()
        )
        db.session.add(subscription)
        db.session.flush()  # 获取subscription.id
        
        # 处理加密货币支付
        if payment_method in ['BTC', 'ETH', 'USDC']:
            payment = crypto_payment_service.create_payment(
                subscription_id=subscription.id,
                amount=amount,
                currency='USD',
                crypto_currency=payment_method
            )
            
            if not payment:
                db.session.rollback()
                return jsonify({'success': False, 'error': '创建支付失败'}), 500
            
            # 生成支付二维码
            qr_code = crypto_payment_service.generate_payment_qr_code(payment)
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'payment_id': payment.id,
                'payment_address': payment.payment_address,
                'amount': payment.amount,
                'currency': payment.currency,
                'qr_code': qr_code,
                'expires_at': payment.expires_at.isoformat(),
                'required_confirmations': payment.required_confirmations
            })
        
        # 处理其他支付方式（Stripe等）
        else:
            db.session.rollback()
            return jsonify({'success': False, 'error': '不支持的支付方式'}), 400
            
    except Exception as e:
        logger.error(f"处理支付请求失败: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': '处理支付失败'}), 500

@billing_bp.route('/payment-status/<int:payment_id>')
@login_required
def payment_status(payment_id):
    """检查支付状态"""
    try:
        # 获取支付记录
        payment = Payment.query.get_or_404(payment_id)
        
        # 验证支付属于当前用户
        user_email = session.get('email')
        user = User.query.filter_by(email=user_email).first()
        if not user or payment.subscription.user_id != user.id:
            return jsonify({'success': False, 'error': '无权访问'}), 403
        
        # 检查支付状态更新
        status_updated = crypto_payment_service.check_payment_status(payment)
        
        return jsonify({
            'success': True,
            'payment': payment.to_dict(),
            'status_updated': status_updated
        })
        
    except Exception as e:
        logger.error(f"检查支付状态失败: {e}")
        return jsonify({'success': False, 'error': '检查支付状态失败'}), 500

@billing_bp.route('/payment/<int:payment_id>')
@login_required
def payment_details(payment_id):
    """支付详情页面"""
    try:
        # 获取支付记录
        payment = Payment.query.get_or_404(payment_id)
        
        # 验证支付属于当前用户
        user_email = session.get('email')
        user = User.query.filter_by(email=user_email).first()
        if not user or payment.subscription.user_id != user.id:
            flash('无权访问此支付记录', 'error')
            return redirect(url_for('billing.manage'))
        
        # 检查支付状态
        crypto_payment_service.check_payment_status(payment)
        
        # 生成二维码（如果需要）
        qr_code = None
        if payment.status == PaymentStatus.PENDING and payment.is_crypto_payment:
            qr_code = crypto_payment_service.generate_payment_qr_code(payment)
        
        return render_template('billing/payment_details.html',
                             payment=payment,
                             qr_code=qr_code,
                             current_lang=session.get('language', 'zh'))
                             
    except Exception as e:
        logger.error(f"获取支付详情失败: {e}")
        flash('获取支付详情失败', 'error')
        return redirect(url_for('billing.manage'))

@billing_bp.route('/manage')
@login_required
def manage():
    """订阅管理页面"""
    try:
        # 获取当前用户
        user_email = session.get('email')
        user = User.query.filter_by(email=user_email).first()
        if not user:
            flash('用户未找到', 'error')
            return redirect(url_for('index'))
        
        # 获取用户订阅
        subscriptions = UserSubscription.query.filter_by(user_id=user.id).all()
        
        # 获取支付历史
        payments = []
        for subscription in subscriptions:
            payments.extend(subscription.payments)
        
        # 按创建时间排序
        payments.sort(key=lambda x: x.created_at, reverse=True)
        
        return render_template('billing/manage.html',
                             subscriptions=subscriptions,
                             payments=payments,
                             current_lang=session.get('language', 'zh'))
                             
    except Exception as e:
        logger.error(f"获取订阅管理页面失败: {e}")
        flash('获取订阅信息失败', 'error')
        return redirect(url_for('index'))

@billing_bp.route('/cancel-subscription/<int:subscription_id>', methods=['POST'])
@login_required
def cancel_subscription(subscription_id):
    """取消订阅"""
    try:
        # 获取订阅记录
        subscription = UserSubscription.query.get_or_404(subscription_id)
        
        # 验证订阅属于当前用户
        user_email = session.get('email')
        user = User.query.filter_by(email=user_email).first()
        if not user or subscription.user_id != user.id:
            return jsonify({'success': False, 'error': '无权操作'}), 403
        
        # 取消订阅
        subscription.status = SubscriptionStatus.CANCELLED
        subscription.cancelled_at = datetime.utcnow()
        subscription.auto_renew = False
        
        db.session.commit()
        
        logger.info(f"用户 {user.email} 取消了订阅 {subscription.id}")
        
        return jsonify({'success': True, 'message': '订阅已成功取消'})
        
    except Exception as e:
        logger.error(f"取消订阅失败: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': '取消订阅失败'}), 500

@billing_bp.route('/invoice/<int:payment_id>')
@login_required
def invoice(payment_id):
    """生成支付发票"""
    try:
        # 获取支付记录
        payment = Payment.query.get_or_404(payment_id)
        
        # 验证支付属于当前用户
        user_email = session.get('email')
        user = User.query.filter_by(email=user_email).first()
        if not user or payment.subscription.user_id != user.id:
            flash('无权访问此发票', 'error')
            return redirect(url_for('billing.manage'))
        
        # 只有已完成的支付才能生成发票
        if payment.status != PaymentStatus.COMPLETED:
            flash('只有已完成的支付才能生成发票', 'error')
            return redirect(url_for('billing.payment_details', payment_id=payment_id))
        
        return render_template('billing/invoice.html',
                             payment=payment,
                             user=user,
                             current_lang=session.get('language', 'zh'))
                             
    except Exception as e:
        logger.error(f"生成发票失败: {e}")
        flash('生成发票失败', 'error')
        return redirect(url_for('billing.manage'))

@billing_bp.route('/webhook/payment-confirmation', methods=['POST'])
def payment_webhook():
    """支付确认Webhook - 用于外部系统通知"""
    try:
        data = request.get_json()
        
        # 验证Webhook签名（生产环境必需）
        # signature = request.headers.get('X-Webhook-Signature')
        # if not verify_webhook_signature(signature, data):
        #     return jsonify({'error': 'Invalid signature'}), 403
        
        payment_id = data.get('payment_id')
        transaction_hash = data.get('transaction_hash')
        confirmations = data.get('confirmations', 0)
        
        if not payment_id:
            return jsonify({'error': 'Missing payment_id'}), 400
        
        # 获取支付记录
        payment = Payment.query.get(payment_id)
        if not payment:
            return jsonify({'error': 'Payment not found'}), 404
        
        # 更新支付信息
        payment.transaction_hash = transaction_hash
        payment.confirmations = confirmations
        
        # 如果确认数足够，处理支付确认
        if confirmations >= payment.required_confirmations:
            crypto_payment_service.process_confirmed_payment(payment)
        
        db.session.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        logger.error(f"处理支付Webhook失败: {e}")
        return jsonify({'error': 'Internal server error'}), 500

def create_default_plans():
    """创建默认订阅计划"""
    try:
        default_plans = [
            {
                'name': 'Free',
                'plan_type': PlanType.FREE,
                'price_monthly': 0.0,
                'price_yearly': 0.0,
                'max_miners': 10,
                'max_api_calls_per_day': 100,
                'description': 'Basic mining calculator access'
            },
            {
                'name': 'Core',
                'plan_type': PlanType.CORE,
                'price_monthly': 20.0,
                'price_yearly': 200.0,
                'max_miners': 50,
                'max_api_calls_per_day': 1000,
                'has_advanced_analytics': True,
                'has_api_access': True,
                'description': 'Advanced analytics and API access'
            },
            {
                'name': 'Professional',
                'plan_type': PlanType.PROFESSIONAL,
                'price_monthly': 50.0,
                'price_yearly': 500.0,
                'max_miners': 100,
                'max_api_calls_per_day': 10000,
                'has_advanced_analytics': True,
                'has_export_features': True,
                'has_priority_support': True,
                'has_api_access': True,
                'description': 'Full feature access for professionals'
            },
            {
                'name': 'Enterprise',
                'plan_type': PlanType.ENTERPRISE,
                'price_monthly': 200.0,
                'price_yearly': 2000.0,
                'max_miners': -1,  # Unlimited
                'max_api_calls_per_day': -1,  # Unlimited
                'has_advanced_analytics': True,
                'has_export_features': True,
                'has_priority_support': True,
                'has_custom_alerts': True,
                'has_api_access': True,
                'description': 'Enterprise-grade solution with unlimited access'
            }
        ]
        
        for plan_data in default_plans:
            existing_plan = SubscriptionPlan.query.filter_by(name=plan_data['name']).first()
            if not existing_plan:
                plan = SubscriptionPlan(**plan_data)
                db.session.add(plan)
        
        db.session.commit()
        logger.info("默认订阅计划已创建")
        
    except Exception as e:
        logger.error(f"创建默认订阅计划失败: {e}")
        db.session.rollback()

@billing_bp.route('/payment-options')
@login_required
def payment_options():
    """支付方式页面 - 显示和管理支付方式"""
    try:
        user_email = session.get('email')
        user = User.query.filter_by(email=user_email).first()
        
        if not user:
            flash('用户未找到', 'error')
            return redirect(url_for('index'))
        
        # 获取用户的订阅信息
        active_subscription = UserSubscription.query.filter_by(
            user_id=user.id,
            status=SubscriptionStatus.ACTIVE
        ).first()
        
        # 支持的加密货币
        supported_cryptos = [
            {
                'code': 'BTC',
                'name': 'Bitcoin',
                'symbol': '₿',
                'network': 'Bitcoin Mainnet',
                'description': 'Industry standard, highest security'
            },
            {
                'code': 'ETH',
                'name': 'Ethereum',
                'symbol': 'Ξ',
                'network': 'Ethereum Mainnet',
                'description': 'Smart contract payments with Web3 integration'
            },
            {
                'code': 'USDC',
                'name': 'USD Coin',
                'symbol': '$',
                'network': 'Multiple chains supported',
                'description': 'Stable cryptocurrency pegged to USD'
            }
        ]
        
        return render_template('billing/payment_options.html',
                             supported_cryptos=supported_cryptos,
                             active_subscription=active_subscription,
                             current_lang=session.get('language', 'zh'))
                             
    except Exception as e:
        logger.error(f"访问支付方式页面失败: {e}")
        flash('访问支付方式页面失败', 'error')
        return redirect(url_for('index'))

@billing_bp.route('/payment-history')
@login_required
def payment_history():
    """支付历史页面"""
    try:
        user_email = session.get('email')
        user = User.query.filter_by(email=user_email).first()
        
        if not user:
            flash('用户未找到', 'error')
            return redirect(url_for('index'))
        
        # 获取用户的所有支付记录
        payments = Payment.query.filter_by(user_id=user.id).order_by(
            Payment.created_at.desc()
        ).all()
        
        # 格式化支付记录
        payment_records = []
        for payment in payments:
            payment_records.append({
                'id': payment.id,
                'amount': float(payment.amount_usd),
                'currency': payment.payment_method.value if payment.payment_method else 'Unknown',
                'status': payment.status.value if payment.status else 'Unknown',
                'created_at': payment.created_at.strftime('%Y-%m-%d %H:%M') if payment.created_at else 'N/A',
                'tx_hash': payment.crypto_tx_hash if payment.crypto_tx_hash else None,
                'subscription_id': payment.subscription_id
            })
        
        return render_template('billing/payment_history.html',
                             payments=payment_records,
                             current_lang=session.get('language', 'zh'))
                             
    except Exception as e:
        logger.error(f"获取支付历史失败: {e}")
        flash('获取支付历史失败', 'error')
        return redirect(url_for('index'))

# 初始化时创建默认计划
try:
    create_default_plans()
except Exception as e:
    logger.error(f"初始化默认计划失败: {e}")

# 导出Blueprint
__all__ = ['billing_bp']