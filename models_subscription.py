"""
订阅计划模型 - Subscription Plan Models
"""
from app import db
from datetime import datetime
from enum import Enum

class PlanType(Enum):
    FREE = "free"
    BASIC = "basic"
    PRO = "pro"

class SubscriptionPlan(db.Model):
    """订阅计划模型"""
    __tablename__ = 'subscription_plans'
    
    id = db.Column(db.String(50), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, default=0)
    currency = db.Column(db.String(10), default='USD')
    
    # 功能限制
    max_miners = db.Column(db.Integer, default=1)
    max_historical_days = db.Column(db.Integer, default=7)
    allow_batch_calculator = db.Column(db.Boolean, default=False)
    allow_crm_system = db.Column(db.Boolean, default=False)
    allow_advanced_analytics = db.Column(db.Boolean, default=False)
    allow_api_access = db.Column(db.Boolean, default=False)
    allow_custom_scenarios = db.Column(db.Boolean, default=False)
    allow_professional_reports = db.Column(db.Boolean, default=False)
    allow_user_management = db.Column(db.Boolean, default=False)
    allow_priority_support = db.Column(db.Boolean, default=False)
    
    # 矿机模型访问
    available_miner_models = db.Column(db.Integer, default=3)  # 可用矿机型号数量
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<SubscriptionPlan {self.name}>'
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'name': self.name,
            'price': self.price,
            'currency': self.currency,
            'max_miners': self.max_miners,
            'max_historical_days': self.max_historical_days,
            'allow_batch_calculator': self.allow_batch_calculator,
            'allow_crm_system': self.allow_crm_system,
            'allow_advanced_analytics': self.allow_advanced_analytics,
            'allow_api_access': self.allow_api_access,
            'allow_custom_scenarios': self.allow_custom_scenarios,
            'allow_professional_reports': self.allow_professional_reports,
            'allow_user_management': self.allow_user_management,
            'allow_priority_support': self.allow_priority_support,
            'available_miner_models': self.available_miner_models
        }

class UserSubscription(db.Model):
    """用户订阅模型"""
    __tablename__ = 'user_subscriptions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    plan_id = db.Column(db.String(50), db.ForeignKey('subscription_plans.id'), nullable=False)
    
    # 订阅状态
    status = db.Column(db.String(20), default='active')  # active, cancelled, expired
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime)
    cancelled_at = db.Column(db.DateTime)
    
    # 支付信息
    stripe_subscription_id = db.Column(db.String(100))
    stripe_customer_id = db.Column(db.String(100))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    plan = db.relationship('SubscriptionPlan', backref='subscribers')
    
    def __repr__(self):
        return f'<UserSubscription {self.user_id} - {self.plan_id}>'
    
    def is_active(self):
        """检查订阅是否有效"""
        if self.status != 'active':
            return False
        if self.expires_at and self.expires_at < datetime.utcnow():
            return False
        return True

def initialize_default_plans():
    """初始化默认订阅计划"""
    from app import app, db
    
    with app.app_context():
        # 检查是否已存在计划
        if SubscriptionPlan.query.first():
            return
        
        # Free Plan
        free_plan = SubscriptionPlan()
        free_plan.id = 'free'
        free_plan.name = 'Free'
        free_plan.price = 0
        free_plan.max_miners = 1
        free_plan.max_historical_days = 7
        free_plan.allow_batch_calculator = False
        free_plan.allow_crm_system = False
        free_plan.allow_advanced_analytics = False
        free_plan.allow_api_access = False
        free_plan.allow_custom_scenarios = False
        free_plan.allow_professional_reports = False
        free_plan.allow_user_management = False
        free_plan.allow_priority_support = False
        free_plan.available_miner_models = 3
        
        # Basic Plan
        basic_plan = SubscriptionPlan(
            id='basic',
            name='Basic',
            price=29.0,
            max_miners=5,
            max_historical_days=30,
            allow_batch_calculator=True,
            allow_crm_system=True,
            allow_advanced_analytics=False,
            allow_api_access=False,
            allow_custom_scenarios=False,
            allow_professional_reports=True,
            allow_user_management=False,
            allow_priority_support=False,
            available_miner_models=17
        )
        
        # Pro Plan
        pro_plan = SubscriptionPlan(
            id='pro',
            name='Pro',
            price=99.0,
            max_miners=10,
            max_historical_days=365,
            allow_batch_calculator=True,
            allow_crm_system=True,
            allow_advanced_analytics=True,
            allow_api_access=True,
            allow_custom_scenarios=True,
            allow_professional_reports=True,
            allow_user_management=True,
            allow_priority_support=True,
            available_miner_models=17
        )
        
        db.session.add_all([free_plan, basic_plan, pro_plan])
        db.session.commit()
        
        print("默认订阅计划已初始化")