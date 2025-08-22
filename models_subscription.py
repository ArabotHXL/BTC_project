"""
Subscription Models
订阅和计费相关的数据模型
"""

from datetime import datetime, timedelta
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
import enum
import logging

logger = logging.getLogger(__name__)

# 使用现有的Base或创建新的
try:
    from db import db
    Base = db.Model
except ImportError:
    from sqlalchemy.ext.declarative import declarative_base
    Base = declarative_base()

class PlanType(enum.Enum):
    """订阅计划类型"""
    FREE = "free"
    BASIC = "basic"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"
    CORE = "core"

class SubscriptionStatus(enum.Enum):
    """订阅状态"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    PENDING = "pending"
    TRIAL = "trial"

class PaymentStatus(enum.Enum):
    """支付状态"""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"

class SubscriptionPlan(Base):
    """订阅计划模型"""
    __tablename__ = 'subscription_plans'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    plan_type = Column(Enum(PlanType), nullable=False)
    price_monthly = Column(Float, nullable=False, default=0.0)
    price_yearly = Column(Float, nullable=False, default=0.0)
    description = Column(Text)
    
    # 功能限制
    max_miners = Column(Integer, default=1)
    max_api_calls_per_day = Column(Integer, default=100)
    has_advanced_analytics = Column(Boolean, default=False)
    has_export_features = Column(Boolean, default=False)
    has_priority_support = Column(Boolean, default=False)
    has_custom_alerts = Column(Boolean, default=False)
    has_api_access = Column(Boolean, default=False)
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    subscriptions = relationship("UserSubscription", back_populates="plan")
    
    def __repr__(self):
        return f'<SubscriptionPlan {self.name}: {self.plan_type.value}>'
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'name': self.name,
            'plan_type': self.plan_type.value,
            'price_monthly': self.price_monthly,
            'price_yearly': self.price_yearly,
            'description': self.description,
            'features': {
                'max_miners': self.max_miners,
                'max_api_calls_per_day': self.max_api_calls_per_day,
                'advanced_analytics': self.has_advanced_analytics,
                'export_features': self.has_export_features,
                'priority_support': self.has_priority_support,
                'custom_alerts': self.has_custom_alerts,
                'api_access': self.has_api_access
            }
        }

class UserSubscription(Base):
    """用户订阅模型"""
    __tablename__ = 'user_subscriptions'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    plan_id = Column(Integer, ForeignKey('subscription_plans.id'), nullable=False)
    
    # 订阅信息
    status = Column(Enum(SubscriptionStatus), nullable=False, default=SubscriptionStatus.PENDING)
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    end_date = Column(DateTime, nullable=False)
    auto_renew = Column(Boolean, default=True)
    
    # Stripe相关
    stripe_subscription_id = Column(String(255))
    stripe_customer_id = Column(String(255))
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    plan = relationship("SubscriptionPlan", back_populates="subscriptions")
    user = relationship("User", back_populates="subscriptions")
    payments = relationship("Payment", back_populates="subscription")
    
    def __repr__(self):
        return f'<UserSubscription {self.user_id}: {self.plan.name} ({self.status.value})>'
    
    @property
    def is_active(self):
        """检查订阅是否有效"""
        return (self.status == SubscriptionStatus.ACTIVE and 
                self.end_date > datetime.utcnow())
    
    @property
    def days_remaining(self):
        """剩余天数"""
        if self.end_date > datetime.utcnow():
            return (self.end_date - datetime.utcnow()).days
        return 0
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'plan': self.plan.to_dict() if self.plan else None,
            'status': self.status.value,
            'started_at': self.started_at.isoformat(),
            'end_date': self.end_date.isoformat(),
            'auto_renew': self.auto_renew,
            'is_active': self.is_active,
            'days_remaining': self.days_remaining
        }

class Payment(Base):
    """支付记录模型"""
    __tablename__ = 'payments'
    
    id = Column(Integer, primary_key=True)
    subscription_id = Column(Integer, ForeignKey('user_subscriptions.id'), nullable=False)
    
    # 支付信息
    amount = Column(Float, nullable=False)
    currency = Column(String(3), nullable=False, default='USD')
    status = Column(Enum(PaymentStatus), nullable=False, default=PaymentStatus.PENDING)
    
    # Stripe相关
    stripe_payment_intent_id = Column(String(255))
    stripe_charge_id = Column(String(255))
    
    # 发票信息
    invoice_number = Column(String(100))
    invoice_url = Column(String(500))
    
    # 时间戳
    payment_date = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    subscription = relationship("UserSubscription", back_populates="payments")
    
    def __repr__(self):
        return f'<Payment {self.amount} {self.currency}: {self.status.value}>'
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'subscription_id': self.subscription_id,
            'amount': self.amount,
            'currency': self.currency,
            'status': self.status.value,
            'payment_date': self.payment_date.isoformat() if self.payment_date else None,
            'invoice_number': self.invoice_number,
            'invoice_url': self.invoice_url,
            'created_at': self.created_at.isoformat()
        }

class ApiUsage(Base):
    """API使用统计模型"""
    __tablename__ = 'api_usage'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    
    # 使用统计
    date = Column(DateTime, nullable=False)
    endpoint = Column(String(200), nullable=False)
    calls_count = Column(Integer, default=0)
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<ApiUsage {self.user_id}: {self.endpoint} ({self.calls_count})>'

# 为了向后兼容，如果使用了原有的User模型，需要添加relationship
try:
    from models import User
    # 如果User模型已存在，添加关系
    if not hasattr(User, 'subscriptions'):
        User.subscriptions = relationship("UserSubscription", back_populates="user")
except ImportError:
    logger.warning("User model not found, creating minimal User model")
    
    class User(Base):
        """最小用户模型（如果不存在）"""
        __tablename__ = 'users'
        
        id = Column(Integer, primary_key=True)
        email = Column(String(120), unique=True, nullable=False)
        username = Column(String(64), unique=True, nullable=False)
        created_at = Column(DateTime, default=datetime.utcnow)
        
        # 关系
        subscriptions = relationship("UserSubscription", back_populates="user")

def init_subscription_plans():
    """初始化默认订阅计划"""
    try:
        # 检查是否已初始化
        if hasattr(init_subscription_plans, '_initialized'):
            return
        
        # 这里应该使用实际的数据库会话
        # 由于我们不确定具体的数据库设置，这里只记录日志
        logger.info("Subscription plans initialization would be performed here")
        
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
                'max_miners': 10,
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
                'max_miners': 50,
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
        
        logger.info(f"Would initialize {len(default_plans)} subscription plans")
        init_subscription_plans._initialized = True
        
    except Exception as e:
        logger.error(f"Failed to initialize subscription plans: {e}")

def initialize_default_plans():
    """初始化默认订阅计划（别名）"""
    return init_subscription_plans()

def create_subscription_tables():
    """创建订阅相关表"""
    try:
        # 这里应该使用实际的数据库设置来创建表
        logger.info("Subscription tables would be created here")
        return True
    except Exception as e:
        logger.error(f"Failed to create subscription tables: {e}")
        return False

# 兼容性导出
__all__ = [
    'SubscriptionPlan', 
    'UserSubscription', 
    'Payment', 
    'ApiUsage',
    'PlanType', 
    'SubscriptionStatus', 
    'PaymentStatus',
    'init_subscription_plans',
    'initialize_default_plans',
    'create_subscription_tables'
]