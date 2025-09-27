"""
Billing Service
计费服务 - 订阅和支付相关的业务逻辑
"""

import logging
from datetime import datetime, timedelta
from sqlalchemy import func
try:
    from ..models import SubscriptionPlan, UserSubscription, Payment, User
    from ..database import db
except ImportError:
    from models import SubscriptionPlan, UserSubscription, Payment, User
    from database import db

logger = logging.getLogger(__name__)

class BillingService:
    """计费服务类"""
    
    @staticmethod
    def create_default_plans():
        """创建默认订阅计划"""
        try:
            # 检查是否已存在计划
            if SubscriptionPlan.query.first():
                logger.info("订阅计划已存在，跳过初始化")
                return True
            
            default_plans = [
                {
                    'name': 'Free',
                    'plan_type': 'free',
                    'price_monthly': 0.0,
                    'price_yearly': 0.0,
                    'max_users': 5,
                    'max_api_calls_per_day': 100,
                    'description': '免费基础功能访问'
                },
                {
                    'name': 'Core',
                    'plan_type': 'core',
                    'price_monthly': 20.0,
                    'price_yearly': 200.0,
                    'max_users': 10,
                    'max_api_calls_per_day': 1000,
                    'has_advanced_analytics': True,
                    'has_api_access': True,
                    'description': '核心功能和API访问'
                },
                {
                    'name': 'Professional',
                    'plan_type': 'professional',
                    'price_monthly': 50.0,
                    'price_yearly': 500.0,
                    'max_users': 25,
                    'max_api_calls_per_day': 10000,
                    'has_advanced_analytics': True,
                    'has_export_features': True,
                    'has_priority_support': True,
                    'has_api_access': True,
                    'has_crm_access': True,
                    'description': '专业版完整功能访问'
                },
                {
                    'name': 'Enterprise',
                    'plan_type': 'enterprise',
                    'price_monthly': 200.0,
                    'price_yearly': 2000.0,
                    'max_users': -1,  # Unlimited
                    'max_api_calls_per_day': -1,  # Unlimited
                    'has_advanced_analytics': True,
                    'has_export_features': True,
                    'has_priority_support': True,
                    'has_custom_alerts': True,
                    'has_api_access': True,
                    'has_crm_access': True,
                    'description': '企业级解决方案，无限制访问'
                }
            ]
            
            for plan_data in default_plans:
                plan = SubscriptionPlan(**plan_data)
                db.session.add(plan)
            
            db.session.commit()
            logger.info(f"成功初始化 {len(default_plans)} 个订阅计划")
            return True
            
        except Exception as e:
            logger.error(f"初始化订阅计划失败: {e}")
            db.session.rollback()
            return False
    
    @staticmethod
    def create_free_subscription(user_id, plan_id, subscription_days=365):
        """创建免费订阅"""
        try:
            # 检查用户是否已有活跃订阅
            existing_subscription = UserSubscription.query.filter_by(
                user_id=user_id,
                status='active'
            ).first()
            
            if existing_subscription:
                logger.warning(f"用户 {user_id} 已有活跃订阅")
                return None
            
            subscription = UserSubscription(
                user_id=user_id,
                plan_id=plan_id,
                status='active',
                started_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(days=subscription_days),
                auto_renew=True
            )
            
            db.session.add(subscription)
            db.session.commit()
            
            logger.info(f"成功创建免费订阅: 用户 {user_id}")
            return subscription
            
        except Exception as e:
            logger.error(f"创建免费订阅失败: {e}")
            db.session.rollback()
            return None
    
    @staticmethod
    def create_paid_subscription(user_id, plan_id, amount, billing_cycle):
        """创建付费订阅（待支付状态）"""
        try:
            # 检查用户是否已有活跃订阅
            existing_subscription = UserSubscription.query.filter_by(
                user_id=user_id,
                status='active'
            ).first()
            
            if existing_subscription:
                logger.warning(f"用户 {user_id} 已有活跃订阅")
                return None
            
            # 计算订阅期限
            if billing_cycle == 'yearly':
                subscription_days = 365
            else:
                subscription_days = 30
            
            subscription = UserSubscription(
                user_id=user_id,
                plan_id=plan_id,
                status='pending',
                started_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(days=subscription_days),
                auto_renew=False
            )
            
            db.session.add(subscription)
            db.session.flush()  # 获取subscription.id
            
            # 创建支付记录
            payment = Payment(
                subscription_id=subscription.id,
                amount=amount,
                currency='USD',
                status='pending',
                payment_method_type='stripe',
                expires_at=datetime.utcnow() + timedelta(hours=24)  # 24小时支付期限
            )
            
            db.session.add(payment)
            db.session.commit()
            
            logger.info(f"成功创建付费订阅: 用户 {user_id}, 金额 {amount}")
            return subscription
            
        except Exception as e:
            logger.error(f"创建付费订阅失败: {e}")
            db.session.rollback()
            return None
    
    @staticmethod
    def activate_subscription(subscription_id):
        """激活订阅"""
        try:
            subscription = UserSubscription.query.get(subscription_id)
            if not subscription:
                logger.warning(f"激活订阅失败: 订阅ID {subscription_id} 不存在")
                return False
            
            subscription.status = 'active'
            subscription.started_at = datetime.utcnow()
            
            db.session.commit()
            
            logger.info(f"成功激活订阅: {subscription_id}")
            return True
            
        except Exception as e:
            logger.error(f"激活订阅失败: {e}")
            db.session.rollback()
            return False
    
    @staticmethod
    def cancel_subscription(subscription_id):
        """取消订阅"""
        try:
            subscription = UserSubscription.query.get(subscription_id)
            if not subscription:
                logger.warning(f"取消订阅失败: 订阅ID {subscription_id} 不存在")
                return False
            
            subscription.status = 'cancelled'
            subscription.cancelled_at = datetime.utcnow()
            subscription.auto_renew = False
            
            db.session.commit()
            
            logger.info(f"成功取消订阅: {subscription_id}")
            return True
            
        except Exception as e:
            logger.error(f"取消订阅失败: {e}")
            db.session.rollback()
            return False
    
    @staticmethod
    def upgrade_subscription(user_id, new_plan_id):
        """升级订阅"""
        try:
            # 获取当前活跃订阅
            current_subscription = UserSubscription.query.filter_by(
                user_id=user_id,
                status='active'
            ).first()
            
            if not current_subscription:
                logger.warning(f"升级订阅失败: 用户 {user_id} 没有活跃订阅")
                return None
            
            # 获取新计划
            new_plan = SubscriptionPlan.query.get(new_plan_id)
            if not new_plan:
                logger.warning(f"升级订阅失败: 计划ID {new_plan_id} 不存在")
                return None
            
            # 取消当前订阅
            current_subscription.status = 'cancelled'
            current_subscription.cancelled_at = datetime.utcnow()
            
            # 创建新订阅
            new_subscription = UserSubscription(
                user_id=user_id,
                plan_id=new_plan_id,
                status='active',
                started_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(days=30),  # 默认30天
                auto_renew=True
            )
            
            db.session.add(new_subscription)
            db.session.commit()
            
            logger.info(f"成功升级订阅: 用户 {user_id} 升级到计划 {new_plan_id}")
            return new_subscription
            
        except Exception as e:
            logger.error(f"升级订阅失败: {e}")
            db.session.rollback()
            return None
    
    @staticmethod
    def process_payment(payment_id, payment_method='manual'):
        """处理支付"""
        try:
            payment = Payment.query.get(payment_id)
            if not payment:
                logger.warning(f"处理支付失败: 支付ID {payment_id} 不存在")
                return False
            
            # 更新支付状态
            payment.status = 'completed'
            payment.payment_date = datetime.utcnow()
            payment.confirmed_at = datetime.utcnow()
            
            # 激活相关订阅
            subscription = payment.subscription
            if subscription and subscription.status == 'pending':
                subscription.status = 'active'
                subscription.started_at = datetime.utcnow()
            
            db.session.commit()
            
            logger.info(f"成功处理支付: {payment_id}")
            return True
            
        except Exception as e:
            logger.error(f"处理支付失败: {e}")
            db.session.rollback()
            return False
    
    @staticmethod
    def get_user_subscription(user_id):
        """获取用户当前订阅"""
        try:
            return UserSubscription.query.filter_by(
                user_id=user_id,
                status='active'
            ).first()
        except Exception as e:
            logger.error(f"获取用户订阅失败: {e}")
            return None
    
    @staticmethod
    def get_subscription_history(user_id):
        """获取用户订阅历史"""
        try:
            return UserSubscription.query.filter_by(user_id=user_id).order_by(
                UserSubscription.created_at.desc()
            ).all()
        except Exception as e:
            logger.error(f"获取订阅历史失败: {e}")
            return []
    
    @staticmethod
    def get_payment_history(user_id):
        """获取用户支付历史"""
        try:
            payments = db.session.query(Payment).join(UserSubscription).filter(
                UserSubscription.user_id == user_id
            ).order_by(Payment.created_at.desc()).all()
            
            return payments
        except Exception as e:
            logger.error(f"获取支付历史失败: {e}")
            return []
    
    @staticmethod
    def get_billing_stats():
        """获取计费统计"""
        try:
            # 基本统计
            total_subscriptions = UserSubscription.query.count()
            active_subscriptions = UserSubscription.query.filter_by(status='active').count()
            pending_subscriptions = UserSubscription.query.filter_by(status='pending').count()
            cancelled_subscriptions = UserSubscription.query.filter_by(status='cancelled').count()
            
            # 收入统计
            total_revenue = db.session.query(func.sum(Payment.amount)).filter(
                Payment.status == 'completed'
            ).scalar() or 0
            
            # 本月收入
            current_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            monthly_revenue = db.session.query(func.sum(Payment.amount)).filter(
                Payment.status == 'completed',
                Payment.payment_date >= current_month
            ).scalar() or 0
            
            # 计划分布
            plan_distribution = {}
            plans = SubscriptionPlan.query.all()
            for plan in plans:
                count = UserSubscription.query.filter_by(
                    plan_id=plan.id,
                    status='active'
                ).count()
                plan_distribution[plan.name] = count
            
            # 即将到期的订阅
            expiring_soon = UserSubscription.query.filter(
                UserSubscription.status == 'active',
                UserSubscription.expires_at <= datetime.utcnow() + timedelta(days=7)
            ).count()
            
            return {
                'total_subscriptions': total_subscriptions,
                'active_subscriptions': active_subscriptions,
                'pending_subscriptions': pending_subscriptions,
                'cancelled_subscriptions': cancelled_subscriptions,
                'total_revenue': float(total_revenue),
                'monthly_revenue': float(monthly_revenue),
                'plan_distribution': plan_distribution,
                'expiring_soon': expiring_soon
            }
            
        except Exception as e:
            logger.error(f"获取计费统计失败: {e}")
            return {}
    
    @staticmethod
    def get_revenue_analysis(days=30):
        """获取收入分析"""
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # 按日期统计收入
            daily_revenue = {}
            payments = Payment.query.filter(
                Payment.status == 'completed',
                Payment.payment_date >= start_date
            ).all()
            
            for payment in payments:
                if payment.payment_date:
                    date_key = payment.payment_date.strftime('%Y-%m-%d')
                    if date_key not in daily_revenue:
                        daily_revenue[date_key] = 0
                    daily_revenue[date_key] += payment.amount
            
            # 按计划统计收入
            plan_revenue = {}
            for payment in payments:
                plan_name = payment.subscription.plan.name
                if plan_name not in plan_revenue:
                    plan_revenue[plan_name] = 0
                plan_revenue[plan_name] += payment.amount
            
            return {
                'daily_revenue': daily_revenue,
                'plan_revenue': plan_revenue,
                'total_period_revenue': sum(daily_revenue.values())
            }
            
        except Exception as e:
            logger.error(f"获取收入分析失败: {e}")
            return {}
    
    @staticmethod
    def get_subscription_forecast():
        """获取订阅预测"""
        try:
            # 即将到期的订阅
            next_7_days = datetime.utcnow() + timedelta(days=7)
            next_30_days = datetime.utcnow() + timedelta(days=30)
            
            expiring_7_days = UserSubscription.query.filter(
                UserSubscription.status == 'active',
                UserSubscription.expires_at <= next_7_days,
                UserSubscription.expires_at > datetime.utcnow()
            ).count()
            
            expiring_30_days = UserSubscription.query.filter(
                UserSubscription.status == 'active',
                UserSubscription.expires_at <= next_30_days,
                UserSubscription.expires_at > datetime.utcnow()
            ).count()
            
            # 预计收入损失
            expiring_subscriptions = UserSubscription.query.filter(
                UserSubscription.status == 'active',
                UserSubscription.expires_at <= next_30_days,
                UserSubscription.expires_at > datetime.utcnow()
            ).all()
            
            potential_revenue_loss = 0
            for subscription in expiring_subscriptions:
                plan = subscription.plan
                if plan:
                    potential_revenue_loss += plan.price_monthly
            
            return {
                'expiring_7_days': expiring_7_days,
                'expiring_30_days': expiring_30_days,
                'potential_revenue_loss': float(potential_revenue_loss)
            }
            
        except Exception as e:
            logger.error(f"获取订阅预测失败: {e}")
            return {}
    
    @staticmethod
    def extend_subscription(subscription_id, additional_days):
        """延长订阅"""
        try:
            subscription = UserSubscription.query.get(subscription_id)
            if not subscription:
                logger.warning(f"延长订阅失败: 订阅ID {subscription_id} 不存在")
                return False
            
            # 延长到期时间
            if subscription.expires_at:
                subscription.expires_at += timedelta(days=additional_days)
            else:
                subscription.expires_at = datetime.utcnow() + timedelta(days=additional_days)
            
            db.session.commit()
            
            logger.info(f"成功延长订阅 {subscription_id} {additional_days} 天")
            return True
            
        except Exception as e:
            logger.error(f"延长订阅失败: {e}")
            db.session.rollback()
            return False