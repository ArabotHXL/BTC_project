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
    CONFIRMING = "confirming"  # 等待区块链确认
    EXPIRED = "expired"  # 支付超时过期

class PaymentMethodType(enum.Enum):
    """支付方式类型"""
    STRIPE = "stripe"
    CRYPTO = "crypto"
    BANK_TRANSFER = "bank_transfer"
    
class CryptoCurrency(enum.Enum):
    """支持的加密货币"""
    BTC = "BTC"
    ETH = "ETH" 
    USDC = "USDC"
    USDT = "USDT"

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
    expires_at = Column(DateTime, nullable=True)  # 使用与数据库表匹配的字段名
    cancelled_at = Column(DateTime, nullable=True)  # 添加缺失的字段
    auto_renew = Column(Boolean, default=True)
    
    # 移除了Stripe集成 - 使用其他支付方案
    
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
                self.expires_at and self.expires_at > datetime.utcnow())
    
    @property
    def days_remaining(self):
        """剩余天数"""
        if self.expires_at and self.expires_at > datetime.utcnow():
            return (self.expires_at - datetime.utcnow()).days
        return 0
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'plan': self.plan.to_dict() if self.plan else None,
            'status': self.status.value,
            'started_at': self.started_at.isoformat(),
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'cancelled_at': self.cancelled_at.isoformat() if self.cancelled_at else None,
            'auto_renew': self.auto_renew,
            'is_active': self.is_active,
            'days_remaining': self.days_remaining
        }

class Payment(Base):
    """支付记录模型 - 支持加密货币和传统支付"""
    __tablename__ = 'payments'
    
    id = Column(Integer, primary_key=True)
    subscription_id = Column(Integer, ForeignKey('user_subscriptions.id'), nullable=False)
    
    # 支付信息
    amount = Column(Float, nullable=False)
    currency = Column(String(10), nullable=False, default='USD')  # 扩展长度以支持USDC等
    status = Column(Enum(PaymentStatus), nullable=False, default=PaymentStatus.PENDING)
    
    # 支付方式类型
    payment_method_type = Column(Enum(PaymentMethodType), nullable=False, default=PaymentMethodType.STRIPE)
    
    # 加密货币支付字段
    crypto_currency = Column(Enum(CryptoCurrency), nullable=True)  # BTC, ETH, USDC等
    wallet_address = Column(String(200), nullable=True)  # 收款钱包地址
    payment_address = Column(String(200), nullable=True)  # 生成的支付地址（用户发送到此地址）
    transaction_hash = Column(String(200), nullable=True)  # 区块链交易哈希
    blockchain_network = Column(String(50), nullable=True)  # bitcoin, ethereum, polygon等
    confirmations = Column(Integer, nullable=True, default=0)  # 区块确认数
    required_confirmations = Column(Integer, nullable=True, default=3)  # 所需确认数
    block_number = Column(Integer, nullable=True)  # 交易所在区块号
    gas_price = Column(Float, nullable=True)  # Gas价格 (仅以太坊)
    gas_used = Column(Integer, nullable=True)  # 使用的Gas数量
    
    # 传统支付字段（保留向后兼容）
    stripe_payment_intent_id = Column(String(100), nullable=True)
    stripe_customer_id = Column(String(100), nullable=True)
    
    # 发票信息
    invoice_number = Column(String(100))
    invoice_url = Column(String(500))
    
    # 支付超时和重试
    expires_at = Column(DateTime, nullable=True)  # 支付超时时间
    retry_count = Column(Integer, default=0)  # 重试次数
    
    # 🔧 CRITICAL FIX: 审计和合规字段增强
    aml_status = Column(String(50), nullable=True)  # AML检查状态
    kyc_status = Column(String(50), nullable=True)  # KYC验证状态
    risk_score = Column(Float, nullable=True)  # 风险评分
    compliance_score = Column(Float, nullable=True)  # 综合合规分数
    compliance_notes = Column(Text, nullable=True)  # 合规备注
    compliance_checked_at = Column(DateTime, nullable=True)  # 合规检查时间
    manual_review_required = Column(Boolean, default=False)  # 是否需要人工审核
    
    # 时间戳
    payment_date = Column(DateTime)
    confirmed_at = Column(DateTime, nullable=True)  # 支付确认时间
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
            'payment_method_type': self.payment_method_type.value,
            
            # 加密货币相关字段
            'crypto_currency': self.crypto_currency.value if self.crypto_currency else None,
            'wallet_address': self.wallet_address,
            'payment_address': self.payment_address,
            'transaction_hash': self.transaction_hash,
            'blockchain_network': self.blockchain_network,
            'confirmations': self.confirmations,
            'required_confirmations': self.required_confirmations,
            'block_number': self.block_number,
            
            # 时间戳
            'payment_date': self.payment_date.isoformat() if self.payment_date else None,
            'confirmed_at': self.confirmed_at.isoformat() if self.confirmed_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'created_at': self.created_at.isoformat(),
            
            # 发票信息
            'invoice_number': self.invoice_number,
            'invoice_url': self.invoice_url,
            
            # 合规信息
            'aml_status': self.aml_status,
            'kyc_status': self.kyc_status,
            'risk_score': self.risk_score
        }
        
    @property
    def is_crypto_payment(self):
        """检查是否为加密货币支付"""
        return self.payment_method_type == PaymentMethodType.CRYPTO
    
    @property
    def is_confirmed(self):
        """检查支付是否已确认"""
        if self.is_crypto_payment:
            return (self.confirmations is not None and 
                   self.required_confirmations is not None and
                   self.confirmations >= self.required_confirmations)
        return self.status == PaymentStatus.COMPLETED
    
    @property
    def is_expired(self):
        """检查支付是否已过期"""
        if self.expires_at:
            return datetime.utcnow() > self.expires_at
        return False

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