"""
Billing Routes
计费路由 - 订阅管理和支付处理
"""

from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, flash
from datetime import datetime, timedelta
import logging
try:
    from ..auth.decorators import requires_billing_access
    from ..auth.authentication import login_required, get_current_user
    from ..models import SubscriptionPlan, UserSubscription, Payment, User
    from ..database import db
    from ..services.billing_service import BillingService
except ImportError:
    from auth.decorators import requires_billing_access
    from auth.authentication import login_required, get_current_user
    from models import SubscriptionPlan, UserSubscription, Payment, User
    from database import db
    from services.billing_service import BillingService

logger = logging.getLogger(__name__)

# 创建蓝图
billing_bp = Blueprint('billing', __name__)

@billing_bp.route('/plans')
def plans():
    """订阅计划页面"""
    try:
        # 获取所有可用的订阅计划
        subscription_plans = SubscriptionPlan.query.all()
        
        # 如果没有计划，创建默认计划
        if not subscription_plans:
            BillingService.create_default_plans()
            subscription_plans = SubscriptionPlan.query.all()
        
        # 获取当前用户的订阅状态
        current_subscription = None
        if session.get('authenticated'):
            user = get_current_user()
            if user:
                current_subscription = UserSubscription.query.filter_by(
                    user_id=user.id,
                    status='active'
                ).first()
        
        return render_template('billing/plans.html', 
                             plans=subscription_plans,
                             current_subscription=current_subscription)
                             
    except Exception as e:
        logger.error(f"获取订阅计划失败: {e}")
        flash('获取订阅计划失败，请稍后重试', 'error')
        return redirect(url_for('index'))

@billing_bp.route('/subscribe/<int:plan_id>')
@login_required
def subscribe(plan_id):
    """订阅页面"""
    try:
        # 获取订阅计划
        plan = SubscriptionPlan.query.get_or_404(plan_id)
        
        # 获取当前用户
        user = get_current_user()
        if not user:
            flash('用户未找到', 'error')
            return redirect(url_for('billing.plans'))
        
        # 检查用户是否已有活跃订阅
        existing_subscription = UserSubscription.query.filter_by(
            user_id=user.id,
            status='active'
        ).first()
        
        if existing_subscription:
            flash('您已经有活跃的订阅', 'warning')
            return redirect(url_for('billing.manage'))
        
        return render_template('billing/subscribe.html',
                             plan=plan)
                             
    except Exception as e:
        logger.error(f"订阅页面错误: {e}")
        flash('访问订阅页面失败', 'error')
        return redirect(url_for('billing.plans'))

@billing_bp.route('/process-subscription', methods=['POST'])
@login_required
def process_subscription():
    """处理订阅请求"""
    try:
        data = request.get_json()
        
        # 验证必需字段
        required_fields = ['plan_id', 'billing_cycle']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'缺少必需字段: {field}'}), 400
        
        plan_id = data['plan_id']
        billing_cycle = data['billing_cycle']  # 'monthly' or 'yearly'
        
        # 获取订阅计划
        plan = SubscriptionPlan.query.get(plan_id)
        if not plan:
            return jsonify({'success': False, 'error': '订阅计划不存在'}), 404
        
        # 获取当前用户
        user = get_current_user()
        if not user:
            return jsonify({'success': False, 'error': '用户未找到'}), 401
        
        # 计算金额和订阅期限
        if billing_cycle == 'yearly':
            amount = plan.price_yearly
            subscription_days = 365
        else:
            amount = plan.price_monthly
            subscription_days = 30
        
        # 处理免费计划
        if amount <= 0:
            subscription = BillingService.create_free_subscription(user.id, plan.id, subscription_days)
            if subscription:
                return jsonify({
                    'success': True,
                    'message': '免费订阅激活成功',
                    'subscription_id': subscription.id
                })
            else:
                return jsonify({'success': False, 'error': '激活免费订阅失败'}), 500
        
        # 处理付费计划 - 创建pending订阅记录
        subscription = BillingService.create_paid_subscription(user.id, plan.id, amount, billing_cycle)
        
        if subscription:
            return jsonify({
                'success': True,
                'message': '订阅创建成功，请联系管理员完成支付',
                'subscription_id': subscription.id,
                'amount': amount,
                'billing_cycle': billing_cycle
            })
        else:
            return jsonify({'success': False, 'error': '创建订阅失败'}), 500
            
    except Exception as e:
        logger.error(f"处理订阅请求失败: {e}")
        return jsonify({'success': False, 'error': '处理订阅失败'}), 500

@billing_bp.route('/manage')
@login_required
def manage():
    """订阅管理页面"""
    try:
        # 获取当前用户
        user = get_current_user()
        if not user:
            flash('用户未找到', 'error')
            return redirect(url_for('index'))
        
        # 获取用户订阅
        subscriptions = UserSubscription.query.filter_by(user_id=user.id).order_by(
            UserSubscription.created_at.desc()
        ).all()
        
        # 获取支付历史
        payments = []
        for subscription in subscriptions:
            payments.extend(subscription.payments)
        
        # 按创建时间排序
        payments.sort(key=lambda x: x.created_at, reverse=True)
        
        return render_template('billing/manage.html',
                             subscriptions=subscriptions,
                             payments=payments)
                             
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
        user = get_current_user()
        if not user or subscription.user_id != user.id:
            return jsonify({'success': False, 'error': '无权操作'}), 403
        
        # 取消订阅
        result = BillingService.cancel_subscription(subscription_id)
        
        if result:
            logger.info(f"用户 {user.email} 取消了订阅 {subscription.id}")
            return jsonify({'success': True, 'message': '订阅已成功取消'})
        else:
            return jsonify({'success': False, 'error': '取消订阅失败'}), 500
        
    except Exception as e:
        logger.error(f"取消订阅失败: {e}")
        return jsonify({'success': False, 'error': '取消订阅失败'}), 500

@billing_bp.route('/upgrade/<int:plan_id>')
@login_required
def upgrade(plan_id):
    """升级订阅"""
    try:
        user = get_current_user()
        if not user:
            flash('用户未找到', 'error')
            return redirect(url_for('billing.plans'))
        
        # 获取目标计划
        target_plan = SubscriptionPlan.query.get_or_404(plan_id)
        
        # 获取当前活跃订阅
        current_subscription = UserSubscription.query.filter_by(
            user_id=user.id,
            status='active'
        ).first()
        
        if not current_subscription:
            flash('您当前没有活跃订阅', 'error')
            return redirect(url_for('billing.plans'))
        
        return render_template('billing/upgrade.html',
                             current_subscription=current_subscription,
                             target_plan=target_plan)
                             
    except Exception as e:
        logger.error(f"升级页面错误: {e}")
        flash('访问升级页面失败', 'error')
        return redirect(url_for('billing.plans'))

@billing_bp.route('/invoice/<int:payment_id>')
@login_required
def invoice(payment_id):
    """生成支付发票"""
    try:
        # 获取支付记录
        payment = Payment.query.get_or_404(payment_id)
        
        # 验证支付属于当前用户
        user = get_current_user()
        if not user or payment.subscription.user_id != user.id:
            flash('无权访问此发票', 'error')
            return redirect(url_for('billing.manage'))
        
        # 只有已完成的支付才能生成发票
        if payment.status != 'completed':
            flash('只有已完成的支付才能生成发票', 'error')
            return redirect(url_for('billing.manage'))
        
        return render_template('billing/invoice.html',
                             payment=payment,
                             user=user)
                             
    except Exception as e:
        logger.error(f"生成发票失败: {e}")
        flash('生成发票失败', 'error')
        return redirect(url_for('billing.manage'))

# 管理员功能
@billing_bp.route('/admin/subscriptions')
@login_required
@requires_billing_access
def admin_subscriptions():
    """管理员订阅管理页面"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 20
        
        subscriptions = UserSubscription.query.order_by(
            UserSubscription.created_at.desc()
        ).paginate(page=page, per_page=per_page, error_out=False)
        
        return render_template('billing/admin_subscriptions.html',
                             title='订阅管理',
                             subscriptions=subscriptions)
                             
    except Exception as e:
        logger.error(f"管理员订阅管理页面错误: {e}")
        flash('加载订阅管理页面失败', 'error')
        return redirect(url_for('admin.dashboard'))

@billing_bp.route('/admin/activate-subscription/<int:subscription_id>', methods=['POST'])
@login_required
@requires_billing_access
def admin_activate_subscription(subscription_id):
    """管理员激活订阅"""
    try:
        subscription = UserSubscription.query.get_or_404(subscription_id)
        
        result = BillingService.activate_subscription(subscription_id)
        
        if result:
            message = f'订阅 {subscription_id} 已激活'
            logger.info(message)
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'success': False, 'error': '激活订阅失败'}), 500
        
    except Exception as e:
        logger.error(f"管理员激活订阅错误: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@billing_bp.route('/admin/plans')
@login_required
@requires_billing_access
def admin_plans():
    """管理员计划管理页面"""
    try:
        plans = SubscriptionPlan.query.all()
        
        return render_template('billing/admin_plans.html',
                             title='计划管理',
                             plans=plans)
                             
    except Exception as e:
        logger.error(f"管理员计划管理页面错误: {e}")
        flash('加载计划管理页面失败', 'error')
        return redirect(url_for('admin.dashboard'))

# API接口
@billing_bp.route('/api/plans')
def api_plans():
    """获取订阅计划API"""
    try:
        plans = SubscriptionPlan.query.all()
        
        return jsonify({
            'success': True,
            'data': [plan.to_dict() for plan in plans]
        })
        
    except Exception as e:
        logger.error(f"获取订阅计划API错误: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@billing_bp.route('/api/subscription-status')
@login_required
def api_subscription_status():
    """获取用户订阅状态API"""
    try:
        user = get_current_user()
        if not user:
            return jsonify({'success': False, 'error': '用户不存在'}), 404
        
        subscription = UserSubscription.query.filter_by(
            user_id=user.id,
            status='active'
        ).first()
        
        if subscription:
            return jsonify({
                'success': True,
                'data': {
                    'has_subscription': True,
                    'subscription': subscription.to_dict()
                }
            })
        else:
            return jsonify({
                'success': True,
                'data': {
                    'has_subscription': False,
                    'subscription': None
                }
            })
        
    except Exception as e:
        logger.error(f"获取订阅状态API错误: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@billing_bp.route('/api/subscriptions')
@login_required
@requires_billing_access
def api_subscriptions():
    """获取订阅列表API"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        status_filter = request.args.get('status', '').strip()
        
        query = UserSubscription.query
        
        if status_filter:
            query = query.filter(UserSubscription.status == status_filter)
        
        subscriptions = query.order_by(UserSubscription.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'success': True,
            'data': [subscription.to_dict() for subscription in subscriptions.items],
            'pagination': {
                'page': subscriptions.page,
                'pages': subscriptions.pages,
                'per_page': subscriptions.per_page,
                'total': subscriptions.total
            }
        })
        
    except Exception as e:
        logger.error(f"获取订阅列表API错误: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@billing_bp.route('/api/billing-stats')
@login_required
@requires_billing_access
def api_billing_stats():
    """获取计费统计API"""
    try:
        stats = BillingService.get_billing_stats()
        
        return jsonify({
            'success': True,
            'data': stats
        })
        
    except Exception as e:
        logger.error(f"获取计费统计API错误: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500