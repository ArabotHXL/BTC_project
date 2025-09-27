"""
Subscription Service
订阅服务 - 订阅计划和功能访问控制相关的业务逻辑
"""

import logging
from datetime import datetime, timedelta
from models import SubscriptionPlan, UserSubscription, User, UserAccess
from database import db

logger = logging.getLogger(__name__)

class SubscriptionService:
    """订阅服务类"""
    
    @staticmethod
    def get_plan_by_type(plan_type):
        """根据类型获取订阅计划"""
        try:
            return SubscriptionPlan.query.filter_by(plan_type=plan_type).first()
        except Exception as e:
            logger.error(f"根据类型获取订阅计划失败: {e}")
            return None
    
    @staticmethod
    def get_all_plans():
        """获取所有订阅计划"""
        try:
            return SubscriptionPlan.query.all()
        except Exception as e:
            logger.error(f"获取所有订阅计划失败: {e}")
            return []
    
    @staticmethod
    def check_plan_features(user_id, feature_name):
        """检查用户计划是否支持特定功能"""
        try:
            # 获取用户当前订阅
            subscription = UserSubscription.query.filter_by(
                user_id=user_id,
                status='active'
            ).first()
            
            if not subscription:
                # 没有订阅，使用免费计划
                free_plan = SubscriptionService.get_plan_by_type('free')
                if not free_plan:
                    return False
                plan = free_plan
            else:
                plan = subscription.plan
            
            # 检查功能权限
            feature_map = {
                'advanced_analytics': 'has_advanced_analytics',
                'export_features': 'has_export_features',
                'priority_support': 'has_priority_support',
                'custom_alerts': 'has_custom_alerts',
                'api_access': 'has_api_access',
                'crm_access': 'has_crm_access'
            }
            
            if feature_name in feature_map:
                return getattr(plan, feature_map[feature_name], False)
            
            return True  # 默认允许基础功能
            
        except Exception as e:
            logger.error(f"检查计划功能失败: {e}")
            return False
    
    @staticmethod
    def get_plan_limits(user_id):
        """获取用户计划限制"""
        try:
            # 获取用户当前订阅
            subscription = UserSubscription.query.filter_by(
                user_id=user_id,
                status='active'
            ).first()
            
            if not subscription:
                # 没有订阅，使用免费计划
                free_plan = SubscriptionService.get_plan_by_type('free')
                if not free_plan:
                    return {
                        'max_users': 1,
                        'max_api_calls_per_day': 10
                    }
                plan = free_plan
            else:
                plan = subscription.plan
            
            return {
                'max_users': plan.max_users,
                'max_api_calls_per_day': plan.max_api_calls_per_day,
                'plan_name': plan.name,
                'plan_type': plan.plan_type
            }
            
        except Exception as e:
            logger.error(f"获取计划限制失败: {e}")
            return {
                'max_users': 1,
                'max_api_calls_per_day': 10
            }
    
    @staticmethod
    def check_usage_limits(user_id, usage_type, current_usage):
        """检查使用量是否超过限制"""
        try:
            limits = SubscriptionService.get_plan_limits(user_id)
            
            if usage_type == 'users':
                max_limit = limits.get('max_users', 1)
            elif usage_type == 'api_calls':
                max_limit = limits.get('max_api_calls_per_day', 10)
            else:
                return True  # 未知类型，默认允许
            
            # -1 表示无限制
            if max_limit == -1:
                return True
            
            return current_usage < max_limit
            
        except Exception as e:
            logger.error(f"检查使用量限制失败: {e}")
            return False
    
    @staticmethod
    def get_subscription_status(user_id):
        """获取用户订阅状态详情"""
        try:
            subscription = UserSubscription.query.filter_by(
                user_id=user_id,
                status='active'
            ).first()
            
            if not subscription:
                return {
                    'has_subscription': False,
                    'plan_name': 'Free',
                    'plan_type': 'free',
                    'status': 'free',
                    'expires_at': None,
                    'days_remaining': None,
                    'auto_renew': False
                }
            
            return {
                'has_subscription': True,
                'plan_name': subscription.plan.name,
                'plan_type': subscription.plan.plan_type,
                'status': subscription.status,
                'expires_at': subscription.expires_at.isoformat() if subscription.expires_at else None,
                'days_remaining': subscription.days_remaining,
                'auto_renew': subscription.auto_renew,
                'started_at': subscription.started_at.isoformat() if subscription.started_at else None
            }
            
        except Exception as e:
            logger.error(f"获取订阅状态失败: {e}")
            return {
                'has_subscription': False,
                'plan_name': 'Free',
                'plan_type': 'free',
                'status': 'error'
            }
    
    @staticmethod
    def can_upgrade_to_plan(user_id, target_plan_id):
        """检查用户是否可以升级到指定计划"""
        try:
            current_subscription = UserSubscription.query.filter_by(
                user_id=user_id,
                status='active'
            ).first()
            
            target_plan = SubscriptionPlan.query.get(target_plan_id)
            if not target_plan:
                return False, "目标计划不存在"
            
            if not current_subscription:
                # 没有当前订阅，可以升级到任何计划
                return True, "可以订阅"
            
            current_plan = current_subscription.plan
            
            # 定义计划层级
            plan_hierarchy = {
                'free': 0,
                'basic': 1,
                'core': 2,
                'professional': 3,
                'enterprise': 4
            }
            
            current_level = plan_hierarchy.get(current_plan.plan_type, 0)
            target_level = plan_hierarchy.get(target_plan.plan_type, 0)
            
            if target_level > current_level:
                return True, "可以升级"
            elif target_level == current_level:
                return False, "已是相同计划"
            else:
                return True, "可以降级"  # 允许降级
            
        except Exception as e:
            logger.error(f"检查升级权限失败: {e}")
            return False, "检查失败"
    
    @staticmethod
    def calculate_prorated_amount(subscription_id, new_plan_id):
        """计算按比例退费/补费金额"""
        try:
            subscription = UserSubscription.query.get(subscription_id)
            if not subscription:
                return None
            
            new_plan = SubscriptionPlan.query.get(new_plan_id)
            if not new_plan:
                return None
            
            current_plan = subscription.plan
            
            # 计算剩余天数
            if subscription.expires_at:
                remaining_days = (subscription.expires_at - datetime.utcnow()).days
                if remaining_days <= 0:
                    remaining_days = 0
            else:
                remaining_days = 0
            
            # 计算当前计划剩余价值
            current_daily_rate = current_plan.price_monthly / 30
            current_remaining_value = current_daily_rate * remaining_days
            
            # 计算新计划价值
            new_daily_rate = new_plan.price_monthly / 30
            new_plan_value = new_daily_rate * remaining_days
            
            # 计算差额
            prorated_amount = new_plan_value - current_remaining_value
            
            return {
                'remaining_days': remaining_days,
                'current_remaining_value': round(current_remaining_value, 2),
                'new_plan_value': round(new_plan_value, 2),
                'prorated_amount': round(prorated_amount, 2),
                'is_upgrade': prorated_amount > 0
            }
            
        except Exception as e:
            logger.error(f"计算按比例金额失败: {e}")
            return None
    
    @staticmethod
    def get_expiring_subscriptions(days_threshold=7):
        """获取即将到期的订阅"""
        try:
            threshold_date = datetime.utcnow() + timedelta(days=days_threshold)
            
            return UserSubscription.query.filter(
                UserSubscription.status == 'active',
                UserSubscription.expires_at <= threshold_date,
                UserSubscription.expires_at > datetime.utcnow()
            ).all()
            
        except Exception as e:
            logger.error(f"获取即将到期订阅失败: {e}")
            return []
    
    @staticmethod
    def auto_renew_subscriptions():
        """自动续费订阅"""
        try:
            # 获取今天到期且设置了自动续费的订阅
            today = datetime.utcnow().date()
            tomorrow = today + timedelta(days=1)
            
            expiring_subscriptions = UserSubscription.query.filter(
                UserSubscription.status == 'active',
                UserSubscription.auto_renew == True,
                UserSubscription.expires_at >= datetime.combine(today, datetime.min.time()),
                UserSubscription.expires_at < datetime.combine(tomorrow, datetime.min.time())
            ).all()
            
            renewed_count = 0
            
            for subscription in expiring_subscriptions:
                try:
                    # 延长订阅30天（月订阅）
                    subscription.expires_at += timedelta(days=30)
                    
                    # 这里应该创建支付记录或调用支付处理
                    # 简化处理，直接续费
                    
                    renewed_count += 1
                    logger.info(f"自动续费订阅: {subscription.id}")
                    
                except Exception as e:
                    logger.error(f"自动续费订阅 {subscription.id} 失败: {e}")
                    continue
            
            db.session.commit()
            
            logger.info(f"自动续费处理完成，成功续费 {renewed_count} 个订阅")
            return renewed_count
            
        except Exception as e:
            logger.error(f"自动续费处理失败: {e}")
            db.session.rollback()
            return 0
    
    @staticmethod
    def sync_user_access_with_subscription(user_id):
        """同步用户访问权限与订阅状态"""
        try:
            # 获取用户
            user_access = UserAccess.query.filter_by(id=user_id).first()
            if not user_access:
                logger.warning(f"用户 {user_id} 不存在")
                return False
            
            # 获取用户订阅状态
            subscription_status = SubscriptionService.get_subscription_status(user_id)
            
            # 更新用户订阅计划
            user_access.subscription_plan = subscription_status['plan_type']
            
            # 如果有有效订阅，更新访问权限
            if subscription_status['has_subscription'] and subscription_status['expires_at']:
                expires_at = datetime.fromisoformat(subscription_status['expires_at'])
                user_access.expires_at = expires_at
                
                # 如果是付费计划，确保用户有访问权限
                if subscription_status['plan_type'] != 'free':
                    if expires_at > datetime.utcnow():
                        # 确保用户可以访问
                        if not user_access.has_access:
                            user_access.expires_at = expires_at
            
            db.session.commit()
            
            logger.info(f"成功同步用户 {user_id} 访问权限与订阅状态")
            return True
            
        except Exception as e:
            logger.error(f"同步用户访问权限失败: {e}")
            db.session.rollback()
            return False
    
    @staticmethod
    def get_plan_comparison():
        """获取计划对比信息"""
        try:
            plans = SubscriptionPlan.query.order_by(SubscriptionPlan.price_monthly).all()
            
            comparison = []
            for plan in plans:
                features = {
                    'max_users': plan.max_users,
                    'max_api_calls': plan.max_api_calls_per_day,
                    'advanced_analytics': plan.has_advanced_analytics,
                    'export_features': plan.has_export_features,
                    'priority_support': plan.has_priority_support,
                    'custom_alerts': plan.has_custom_alerts,
                    'api_access': plan.has_api_access,
                    'crm_access': plan.has_crm_access
                }
                
                comparison.append({
                    'id': plan.id,
                    'name': plan.name,
                    'plan_type': plan.plan_type,
                    'price_monthly': plan.price_monthly,
                    'price_yearly': plan.price_yearly,
                    'description': plan.description,
                    'features': features,
                    'yearly_savings': (plan.price_monthly * 12 - plan.price_yearly) if plan.price_yearly > 0 else 0
                })
            
            return comparison
            
        except Exception as e:
            logger.error(f"获取计划对比信息失败: {e}")
            return []
    
    @staticmethod
    def get_usage_analytics(user_id, days=30):
        """获取用户使用分析"""
        try:
            # 这里可以扩展为真实的使用情况分析
            # 目前返回模拟数据
            
            limits = SubscriptionService.get_plan_limits(user_id)
            
            return {
                'api_calls_used': 0,  # 实际应该从API使用记录中获取
                'api_calls_limit': limits.get('max_api_calls_per_day', 10),
                'users_count': 1,  # 实际应该统计关联用户数
                'users_limit': limits.get('max_users', 1),
                'plan_utilization': 0.0  # 计划利用率
            }
            
        except Exception as e:
            logger.error(f"获取使用分析失败: {e}")
            return {}