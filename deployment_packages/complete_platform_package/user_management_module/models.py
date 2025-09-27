"""
User Management Models
用户管理数据模型 - 包含用户认证、CRM、订阅管理相关的所有数据模型

移除了挖矿计算和Web3相关的模型，专注于用户管理核心功能
"""

from datetime import datetime, timedelta
import enum
import logging
from werkzeug.security import generate_password_hash, check_password_hash
from database import db

logger = logging.getLogger(__name__)

# ============================================================================
# 枚举类型定义
# ============================================================================

class LeadStatus(enum.Enum):
    """潜在客户状态"""
    NEW = "新建"
    CONTACTED = "已联系"
    QUALIFIED = "合格线索"
    NEGOTIATION = "谈判中"
    WON = "已成交"
    LOST = "已流失"

class DealStatus(enum.Enum):
    """交易状态"""
    DRAFT = "草稿"
    PENDING = "待定"
    APPROVED = "已批准"
    SIGNED = "已签署"
    COMPLETED = "已完成"
    CANCELED = "已取消"

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

# ============================================================================
# 用户认证和访问控制模型
# ============================================================================

class UserAccess(db.Model):
    """用户访问权限管理"""
    __tablename__ = 'user_access'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(256), nullable=False, unique=True)
    username = db.Column(db.String(50), nullable=True, unique=True)  # 用户名字段
    password_hash = db.Column(db.String(512), nullable=True)  # 密码哈希字段
    is_email_verified = db.Column(db.Boolean, default=False, nullable=False)  # 邮箱验证状态
    email_verification_token = db.Column(db.String(100), nullable=True)  # 邮箱验证令牌
    company = db.Column(db.String(200), nullable=True)
    position = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    access_days = db.Column(db.Integer, default=30, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    notes = db.Column(db.Text, nullable=True)
    last_login = db.Column(db.DateTime, nullable=True)
    role = db.Column(db.String(20), default="guest", nullable=False)
    subscription_plan = db.Column(db.String(20), default="free", nullable=False)  # 订阅计划
    
    # 创建者关联（管理员可以创建用户）
    created_by_id = db.Column(db.Integer, db.ForeignKey('user_access.id'), nullable=True)
    created_by = db.relationship('UserAccess', foreign_keys=[created_by_id], backref='managed_users', remote_side=[id])

    def __init__(self, name, email, access_days=30, company=None, position=None, notes=None, role="guest", 
                 username=None, password_hash=None, subscription_plan="free"):
        self.name = name
        self.email = email
        self.username = username
        self.password_hash = password_hash
        self.company = company
        self.position = position
        self.access_days = access_days
        self.expires_at = datetime.utcnow() + timedelta(days=access_days)
        self.notes = notes
        self.role = role
        self.subscription_plan = subscription_plan

    @property
    def has_access(self):
        """检查用户是否有访问权限"""
        # Free 订阅计划没有时间限制
        if self.subscription_plan == 'free':
            return True
        return datetime.utcnow() <= self.expires_at

    @property
    def access_status(self):
        """获取用户访问状态"""
        if self.has_access:
            return "有效"
        else:
            return "已过期"

    @property
    def days_remaining(self):
        """剩余访问天数"""
        if self.subscription_plan == 'free':
            return float('inf')  # 免费用户无限制
        
        if self.expires_at and self.expires_at > datetime.utcnow():
            return (self.expires_at - datetime.utcnow()).days
        return 0

    def set_password(self, password):
        """设置密码"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """验证密码"""
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    def extend_access(self, additional_days):
        """延长访问时间"""
        if self.subscription_plan != 'free':
            self.expires_at = max(datetime.utcnow(), self.expires_at) + timedelta(days=additional_days)
            self.access_days += additional_days

    def verify_email(self):
        """验证邮箱"""
        self.is_email_verified = True
        self.email_verification_token = None

    def __repr__(self):
        return f"<UserAccess {self.name} ({self.email}) - {self.role}>"

class User(db.Model):
    """用户模型"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    username = db.Column(db.String(80), unique=True, nullable=True)
    password_hash = db.Column(db.String(256), nullable=False)

    # 用户状态
    is_active = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=False)

    # 时间戳
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)

    # 用户角色
    role = db.Column(db.String(20), default="user", nullable=False)

    # 个人信息
    first_name = db.Column(db.String(80), nullable=True)
    last_name = db.Column(db.String(80), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    company = db.Column(db.String(200), nullable=True)
    position = db.Column(db.String(100), nullable=True)

    # 关系
    subscriptions = db.relationship("UserSubscription", back_populates="user", lazy='dynamic')
    login_records = db.relationship("LoginRecord", backref="user", lazy='dynamic')

    def __init__(self, email, username=None, password=None, **kwargs):
        self.email = email
        self.username = username
        if password:
            self.set_password(password)
        
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def set_password(self, password):
        """设置密码"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """验证密码"""
        return check_password_hash(self.password_hash, password)

    @property
    def full_name(self):
        """获取全名"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username or self.email.split('@')[0]

    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'email': self.email,
            'username': self.username,
            'full_name': self.full_name,
            'role': self.role,
            'is_active': self.is_active,
            'is_verified': self.is_verified,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'company': self.company,
            'position': self.position
        }

    def __repr__(self):
        return f"<User {self.username or self.email}>"

class LoginRecord(db.Model):
    """登录记录表"""
    __tablename__ = 'login_records'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # 登录信息
    login_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    logout_time = db.Column(db.DateTime, nullable=True)
    session_duration = db.Column(db.Integer, nullable=True)  # 会话持续时间（秒）
    
    # 访问信息
    ip_address = db.Column(db.String(45), nullable=True)  # 支持IPv6
    user_agent = db.Column(db.Text, nullable=True)
    login_method = db.Column(db.String(20), default='password')  # password, email, etc.
    
    # 地理位置信息
    country = db.Column(db.String(100), nullable=True)
    city = db.Column(db.String(100), nullable=True)
    timezone = db.Column(db.String(50), nullable=True)
    
    # 安全信息
    is_suspicious = db.Column(db.Boolean, default=False)
    security_flags = db.Column(db.Text, nullable=True)  # JSON格式的安全标志
    
    def __init__(self, user_id, ip_address=None, user_agent=None, login_method='password'):
        self.user_id = user_id
        self.ip_address = ip_address
        self.user_agent = user_agent
        self.login_method = login_method
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'login_time': self.login_time.isoformat() if self.login_time else None,
            'logout_time': self.logout_time.isoformat() if self.logout_time else None,
            'session_duration': self.session_duration,
            'ip_address': self.ip_address,
            'login_method': self.login_method,
            'country': self.country,
            'city': self.city,
            'is_suspicious': self.is_suspicious
        }
    
    def __repr__(self):
        return f"<LoginRecord {self.user_id} at {self.login_time}>"

# ============================================================================
# CRM系统模型
# ============================================================================

class Customer(db.Model):
    """客户信息"""
    __tablename__ = 'crm_customers'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    company = db.Column(db.String(200), nullable=True)
    email = db.Column(db.String(256), nullable=True)
    phone = db.Column(db.String(50), nullable=True)
    address = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    tags = db.Column(db.String(500), nullable=True)  # 存储以逗号分隔的标签
    customer_type = db.Column(db.String(50), default="企业", nullable=False)  # 企业 或 个人
    notes = db.Column(db.Text, nullable=True)  # 客户备注

    # 关联到管理员
    created_by_id = db.Column(db.Integer, db.ForeignKey('user_access.id'), nullable=True)
    created_by = db.relationship('UserAccess', foreign_keys=[created_by_id], backref='managed_customers')

    # 关联关系
    contacts = db.relationship('Contact', backref='customer', lazy=True, cascade="all, delete-orphan")
    leads = db.relationship('Lead', backref='customer', lazy=True, cascade="all, delete-orphan")
    deals = db.relationship('Deal', backref='customer', lazy=True, cascade="all, delete-orphan")

    def __init__(self, name, company=None, email=None, phone=None, address=None, tags=None, 
                 customer_type="企业", notes=None, created_by_id=None):
        self.name = name
        self.company = company
        self.email = email
        self.phone = phone
        self.address = address
        self.tags = tags
        self.customer_type = customer_type
        self.notes = notes
        self.created_by_id = created_by_id

    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'name': self.name,
            'company': self.company,
            'email': self.email,
            'phone': self.phone,
            'address': self.address,
            'customer_type': self.customer_type,
            'tags': self.tags.split(',') if self.tags else [],
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'created_by_id': self.created_by_id
        }

    def __repr__(self):
        return f"<Customer {self.name} - {self.company}>"

class Contact(db.Model):
    """联系人"""
    __tablename__ = 'crm_contacts'

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('crm_customers.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    position = db.Column(db.String(100), nullable=True)
    email = db.Column(db.String(256), nullable=True)
    phone = db.Column(db.String(50), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # 关联到创建者
    created_by_id = db.Column(db.Integer, db.ForeignKey('user_access.id'), nullable=True)
    created_by = db.relationship('UserAccess', foreign_keys=[created_by_id])

    def __init__(self, customer_id, name, position=None, email=None, phone=None, notes=None, created_by_id=None):
        self.customer_id = customer_id
        self.name = name
        self.position = position
        self.email = email
        self.phone = phone
        self.notes = notes
        self.created_by_id = created_by_id

    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'customer_id': self.customer_id,
            'name': self.name,
            'position': self.position,
            'email': self.email,
            'phone': self.phone,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def __repr__(self):
        return f"<Contact {self.name} - {self.position}>"

class Lead(db.Model):
    """潜在客户/线索"""
    __tablename__ = 'crm_leads'

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('crm_customers.id'), nullable=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.Enum(LeadStatus), default=LeadStatus.NEW, nullable=False)
    source = db.Column(db.String(100), nullable=True)  # 线索来源
    estimated_value = db.Column(db.Float, nullable=True)
    probability = db.Column(db.Integer, default=0)  # 成功概率（0-100）
    expected_close_date = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # 关联到负责人
    assigned_to_id = db.Column(db.Integer, db.ForeignKey('user_access.id'), nullable=True)
    assigned_to = db.relationship('UserAccess', foreign_keys=[assigned_to_id])

    # 关联到创建者
    created_by_id = db.Column(db.Integer, db.ForeignKey('user_access.id'), nullable=True)
    created_by = db.relationship('UserAccess', foreign_keys=[created_by_id])

    def __init__(self, title, description=None, customer_id=None, source=None, 
                 estimated_value=None, assigned_to_id=None, created_by_id=None):
        self.title = title
        self.description = description
        self.customer_id = customer_id
        self.source = source
        self.estimated_value = estimated_value
        self.assigned_to_id = assigned_to_id
        self.created_by_id = created_by_id

    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'customer_id': self.customer_id,
            'title': self.title,
            'description': self.description,
            'status': self.status.value,
            'source': self.source,
            'estimated_value': self.estimated_value,
            'probability': self.probability,
            'expected_close_date': self.expected_close_date.isoformat() if self.expected_close_date else None,
            'assigned_to_id': self.assigned_to_id,
            'created_by_id': self.created_by_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def __repr__(self):
        return f"<Lead {self.title} - {self.status.value}>"

class Deal(db.Model):
    """交易/订单"""
    __tablename__ = 'crm_deals'

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('crm_customers.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), default='USD', nullable=False)
    status = db.Column(db.Enum(DealStatus), default=DealStatus.DRAFT, nullable=False)
    probability = db.Column(db.Integer, default=0)  # 成功概率（0-100）
    expected_close_date = db.Column(db.Date, nullable=True)
    actual_close_date = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # 关联到负责人
    assigned_to_id = db.Column(db.Integer, db.ForeignKey('user_access.id'), nullable=True)
    assigned_to = db.relationship('UserAccess', foreign_keys=[assigned_to_id])

    # 关联到创建者
    created_by_id = db.Column(db.Integer, db.ForeignKey('user_access.id'), nullable=True)
    created_by = db.relationship('UserAccess', foreign_keys=[created_by_id])

    def __init__(self, customer_id, title, amount, description=None, currency='USD',
                 assigned_to_id=None, created_by_id=None):
        self.customer_id = customer_id
        self.title = title
        self.amount = amount
        self.description = description
        self.currency = currency
        self.assigned_to_id = assigned_to_id
        self.created_by_id = created_by_id

    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'customer_id': self.customer_id,
            'title': self.title,
            'description': self.description,
            'amount': self.amount,
            'currency': self.currency,
            'status': self.status.value,
            'probability': self.probability,
            'expected_close_date': self.expected_close_date.isoformat() if self.expected_close_date else None,
            'actual_close_date': self.actual_close_date.isoformat() if self.actual_close_date else None,
            'assigned_to_id': self.assigned_to_id,
            'created_by_id': self.created_by_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def __repr__(self):
        return f"<Deal {self.title} - {self.amount} {self.currency}>"

class Activity(db.Model):
    """CRM活动记录"""
    __tablename__ = 'crm_activities'

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('crm_customers.id'), nullable=True)
    lead_id = db.Column(db.Integer, db.ForeignKey('crm_leads.id'), nullable=True)
    deal_id = db.Column(db.Integer, db.ForeignKey('crm_deals.id'), nullable=True)
    
    activity_type = db.Column(db.String(50), nullable=False)  # 通话、邮件、会议等
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    activity_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    duration_minutes = db.Column(db.Integer, nullable=True)
    outcome = db.Column(db.String(100), nullable=True)  # 活动结果
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # 关联到负责人
    performed_by_id = db.Column(db.Integer, db.ForeignKey('user_access.id'), nullable=True)
    performed_by = db.relationship('UserAccess', foreign_keys=[performed_by_id])

    # 建立与其他模型的关系
    customer = db.relationship('Customer', backref='activities')
    lead = db.relationship('Lead', backref='activities')
    deal = db.relationship('Deal', backref='activities')

    def __init__(self, activity_type, title, customer_id=None, lead_id=None, deal_id=None,
                 description=None, performed_by_id=None):
        self.activity_type = activity_type
        self.title = title
        self.customer_id = customer_id
        self.lead_id = lead_id
        self.deal_id = deal_id
        self.description = description
        self.performed_by_id = performed_by_id

    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'customer_id': self.customer_id,
            'lead_id': self.lead_id,
            'deal_id': self.deal_id,
            'activity_type': self.activity_type,
            'title': self.title,
            'description': self.description,
            'activity_date': self.activity_date.isoformat() if self.activity_date else None,
            'duration_minutes': self.duration_minutes,
            'outcome': self.outcome,
            'performed_by_id': self.performed_by_id,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f"<Activity {self.activity_type}: {self.title}>"

# ============================================================================
# 订阅和计费模型
# ============================================================================

class SubscriptionPlan(db.Model):
    """订阅计划模型"""
    __tablename__ = 'subscription_plans'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    plan_type = db.Column(db.Enum(PlanType), nullable=False)
    price_monthly = db.Column(db.Float, nullable=False, default=0.0)
    price_yearly = db.Column(db.Float, nullable=False, default=0.0)
    description = db.Column(db.Text)
    
    # 功能限制
    max_users = db.Column(db.Integer, default=5)
    max_api_calls_per_day = db.Column(db.Integer, default=100)
    has_advanced_analytics = db.Column(db.Boolean, default=False)
    has_export_features = db.Column(db.Boolean, default=False)
    has_priority_support = db.Column(db.Boolean, default=False)
    has_custom_alerts = db.Column(db.Boolean, default=False)
    has_api_access = db.Column(db.Boolean, default=False)
    has_crm_access = db.Column(db.Boolean, default=False)
    
    # 时间戳
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    subscriptions = db.relationship("UserSubscription", back_populates="plan")
    
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
                'max_users': self.max_users,
                'max_api_calls_per_day': self.max_api_calls_per_day,
                'advanced_analytics': self.has_advanced_analytics,
                'export_features': self.has_export_features,
                'priority_support': self.has_priority_support,
                'custom_alerts': self.has_custom_alerts,
                'api_access': self.has_api_access,
                'crm_access': self.has_crm_access
            }
        }

class UserSubscription(db.Model):
    """用户订阅模型"""
    __tablename__ = 'user_subscriptions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    plan_id = db.Column(db.Integer, db.ForeignKey('subscription_plans.id'), nullable=False)
    
    # 订阅信息
    status = db.Column(db.Enum(SubscriptionStatus), nullable=False, default=SubscriptionStatus.PENDING)
    started_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=True)
    cancelled_at = db.Column(db.DateTime, nullable=True)
    auto_renew = db.Column(db.Boolean, default=True)
    
    # 时间戳
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    plan = db.relationship("SubscriptionPlan", back_populates="subscriptions")
    user = db.relationship("User", back_populates="subscriptions")
    payments = db.relationship("Payment", back_populates="subscription")
    
    def __repr__(self):
        return f'<UserSubscription {self.user_id}: {self.plan.name} ({self.status.value})>'
    
    @property
    def is_active(self):
        """检查订阅是否有效"""
        return (self.status == SubscriptionStatus.ACTIVE and 
                (not self.expires_at or self.expires_at > datetime.utcnow()))
    
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

class Payment(db.Model):
    """支付记录模型"""
    __tablename__ = 'payments'
    
    id = db.Column(db.Integer, primary_key=True)
    subscription_id = db.Column(db.Integer, db.ForeignKey('user_subscriptions.id'), nullable=False)
    
    # 支付信息
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), nullable=False, default='USD')
    status = db.Column(db.Enum(PaymentStatus), nullable=False, default=PaymentStatus.PENDING)
    
    # 支付方式类型
    payment_method_type = db.Column(db.Enum(PaymentMethodType), nullable=False, default=PaymentMethodType.STRIPE)
    
    # 传统支付字段
    stripe_payment_intent_id = db.Column(db.String(100), nullable=True)
    stripe_customer_id = db.Column(db.String(100), nullable=True)
    
    # 发票信息
    invoice_number = db.Column(db.String(100))
    invoice_url = db.Column(db.String(500))
    
    # 支付超时和重试
    expires_at = db.Column(db.DateTime, nullable=True)
    retry_count = db.Column(db.Integer, default=0)
    
    # 时间戳
    payment_date = db.Column(db.DateTime)
    confirmed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    subscription = db.relationship("UserSubscription", back_populates="payments")
    
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
            'payment_date': self.payment_date.isoformat() if self.payment_date else None,
            'confirmed_at': self.confirmed_at.isoformat() if self.confirmed_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'created_at': self.created_at.isoformat(),
            'invoice_number': self.invoice_number,
            'invoice_url': self.invoice_url
        }
    
    @property
    def is_confirmed(self):
        """检查支付是否已确认"""
        return self.status == PaymentStatus.COMPLETED
    
    @property
    def is_expired(self):
        """检查支付是否已过期"""
        if self.expires_at:
            return datetime.utcnow() > self.expires_at
        return False

class ApiUsage(db.Model):
    """API使用统计模型"""
    __tablename__ = 'api_usage'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # 使用统计
    date = db.Column(db.DateTime, nullable=False)
    endpoint = db.Column(db.String(200), nullable=False)
    calls_count = db.Column(db.Integer, default=0)
    
    # 时间戳
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<ApiUsage {self.user_id}: {self.endpoint} ({self.calls_count})>'

# ============================================================================
# 工具函数
# ============================================================================

def init_default_subscription_plans():
    """初始化默认订阅计划"""
    try:
        # 检查是否已存在计划
        if SubscriptionPlan.query.first():
            logger.info("订阅计划已存在，跳过初始化")
            return
        
        default_plans = [
            {
                'name': 'Free',
                'plan_type': PlanType.FREE,
                'price_monthly': 0.0,
                'price_yearly': 0.0,
                'max_users': 5,
                'max_api_calls_per_day': 100,
                'description': '免费基础功能访问'
            },
            {
                'name': 'Core',
                'plan_type': PlanType.CORE,
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
                'plan_type': PlanType.PROFESSIONAL,
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
                'plan_type': PlanType.ENTERPRISE,
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
        
    except Exception as e:
        logger.error(f"初始化订阅计划失败: {e}")
        db.session.rollback()

def create_admin_user(email, password, name="Administrator"):
    """创建管理员用户"""
    try:
        # 检查用户是否已存在
        existing_user = UserAccess.query.filter_by(email=email).first()
        if existing_user:
            logger.warning(f"管理员用户 {email} 已存在")
            return existing_user
        
        # 创建管理员用户
        admin_user = UserAccess(
            name=name,
            email=email,
            role="owner",
            subscription_plan="enterprise",
            access_days=365 * 10,  # 10年访问权限
            notes="系统初始化创建的管理员用户"
        )
        admin_user.set_password(password)
        admin_user.verify_email()  # 自动验证邮箱
        
        db.session.add(admin_user)
        db.session.commit()
        
        logger.info(f"成功创建管理员用户: {email}")
        return admin_user
        
    except Exception as e:
        logger.error(f"创建管理员用户失败: {e}")
        db.session.rollback()
        return None