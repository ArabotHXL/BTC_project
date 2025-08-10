# 标准库导入
from datetime import datetime, timedelta
import enum

# 本地模块导入
from db import db

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

class NetworkSnapshot(db.Model):
    """网络状态快照记录"""
    __tablename__ = 'network_snapshots'
    
    id = db.Column(db.Integer, primary_key=True)
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    btc_price = db.Column(db.Float, nullable=False)
    network_difficulty = db.Column(db.Float, nullable=False)
    network_hashrate = db.Column(db.Float, nullable=False)  # 单位: EH/s
    block_reward = db.Column(db.Float, nullable=False, default=3.125)
    
    # API来源标记
    price_source = db.Column(db.String(50), default='coingecko')
    data_source = db.Column(db.String(50), default='blockchain.info')
    
    # 数据质量标记
    is_valid = db.Column(db.Boolean, default=True)
    api_response_time = db.Column(db.Float, nullable=True)  # API响应时间(秒)
    
    def __init__(self, btc_price, network_difficulty, network_hashrate, block_reward=3.125, 
                 price_source='coingecko', data_source='blockchain.info', is_valid=True, api_response_time=None):
        self.btc_price = btc_price
        self.network_difficulty = network_difficulty
        self.network_hashrate = network_hashrate
        self.block_reward = block_reward
        self.price_source = price_source
        self.data_source = data_source
        self.is_valid = is_valid
        self.api_response_time = api_response_time
    
    def __repr__(self):
        return f"<NetworkSnapshot {self.recorded_at}: BTC=${self.btc_price}, Difficulty={self.network_difficulty}T>"
    
    def to_dict(self):
        """转换为字典格式，便于JSON序列化"""
        return {
            'id': self.id,
            'recorded_at': self.recorded_at.isoformat(),
            'btc_price': self.btc_price,
            'network_difficulty': self.network_difficulty,
            'network_hashrate': self.network_hashrate,
            'block_reward': self.block_reward,
            'price_source': self.price_source,
            'data_source': self.data_source,
            'is_valid': self.is_valid
        }

class LoginRecord(db.Model):
    """记录用户登录信息的模型"""
    __tablename__ = 'login_records'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(256), nullable=False)
    login_time = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    successful = db.Column(db.Boolean, default=True, nullable=False)
    ip_address = db.Column(db.String(50), nullable=True)
    login_location = db.Column(db.String(512), nullable=True)
    
    def __init__(self, email, successful=True, ip_address=None, login_location=None):
        self.email = email
        self.successful = successful
        self.ip_address = ip_address
        self.login_location = login_location
    
    def __repr__(self):
        """格式化模型的字符串表示"""
        status = "成功" if self.successful else "失败"
        return f"<LoginRecord {self.email} - {self.login_time} - {status}>"

class UserAccess(db.Model):
    """用户访问权限管理"""
    __tablename__ = 'user_access'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(256), nullable=False, unique=True)
    company = db.Column(db.String(200), nullable=True)
    position = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    access_days = db.Column(db.Integer, default=30, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    notes = db.Column(db.Text, nullable=True)
    last_login = db.Column(db.DateTime, nullable=True)
    role = db.Column(db.String(20), default="guest", nullable=False)
    
    # 创建者关联（矿场主可以创建客户）
    created_by_id = db.Column(db.Integer, db.ForeignKey('user_access.id'), nullable=True)
    created_by = db.relationship('UserAccess', foreign_keys=[created_by_id], backref='managed_users', remote_side=[id])
    
    def __init__(self, name, email, access_days=30, company=None, position=None, notes=None, role="guest"):
        self.name = name
        self.email = email
        self.company = company
        self.position = position
        self.access_days = access_days
        self.expires_at = datetime.utcnow() + timedelta(days=access_days)
        self.notes = notes
        self.role = role
    
    @property
    def has_access(self):
        """检查用户是否有访问权限"""
        return datetime.utcnow() <= self.expires_at
    
    @property
    def access_status(self):
        """获取用户访问状态"""
        if self.has_access:
            return "授权访问"
        else:
            return "访问已过期"
    
    @property
    def days_remaining(self):
        """获取剩余访问天数"""
        if not self.has_access:
            return 0
        delta = self.expires_at - datetime.utcnow()
        return max(0, delta.days)
    
    def extend_access(self, days):
        """延长访问期限"""
        if self.has_access:
            self.expires_at = self.expires_at + timedelta(days=days)
        else:
            self.expires_at = datetime.utcnow() + timedelta(days=days)
        self.access_days += days
        
    def revoke_access(self):
        """撤销访问权限"""
        self.expires_at = datetime.utcnow() - timedelta(days=1)
        
    def __repr__(self):
        return f"<UserAccess {self.name} ({self.email}) - {self.access_status}>"
        
# CRM相关模型
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
    mining_capacity = db.Column(db.Float, nullable=True)  # 挖矿容量（MW）
    notes = db.Column(db.Text, nullable=True)  # 客户备注
    
    # 关联到矿场主
    created_by_id = db.Column(db.Integer, db.ForeignKey('user_access.id'), nullable=True)
    created_by = db.relationship('UserAccess', foreign_keys=[created_by_id], backref='managed_customers')
    
    # 关联关系
    contacts = db.relationship('Contact', backref='customer', lazy=True, cascade="all, delete-orphan")
    leads = db.relationship('Lead', backref='customer', lazy=True, cascade="all, delete-orphan")
    deals = db.relationship('Deal', backref='customer', lazy=True, cascade="all, delete-orphan")
    
    def __init__(self, name, company=None, email=None, phone=None, address=None, tags=None, 
                 customer_type="企业", mining_capacity=None, notes=None, created_by_id=None):
        self.name = name
        self.company = company
        self.email = email
        self.phone = phone
        self.address = address
        self.tags = tags
        self.customer_type = customer_type
        self.mining_capacity = mining_capacity
        self.notes = notes
        self.created_by_id = created_by_id
    
    def __repr__(self):
        return f"<Customer {self.name} - {self.company}>"

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
    role = db.Column(db.String(20), default='user')  # user, admin, manager
    
    def __repr__(self):
        return f'<User {self.email}>'

class Contact(db.Model):
    """客户联系人"""
    __tablename__ = 'crm_contacts'
    
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('crm_customers.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    position = db.Column(db.String(100), nullable=True)
    email = db.Column(db.String(256), nullable=True)
    phone = db.Column(db.String(50), nullable=True)
    primary = db.Column(db.Boolean, default=False, nullable=False)  # 是否为主要联系人
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    notes = db.Column(db.Text, nullable=True)
    
    def __init__(self, customer_id, name, position=None, email=None, phone=None, primary=False, notes=None):
        self.customer_id = customer_id
        self.name = name
        self.position = position
        self.email = email
        self.phone = phone
        self.primary = primary
        self.notes = notes
    
    def __repr__(self):
        return f"<Contact {self.name} - {self.position}>"

class Lead(db.Model):
    """潜在商机"""
    __tablename__ = 'crm_leads'
    
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('crm_customers.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    status = db.Column(db.Enum(LeadStatus), default=LeadStatus.NEW, nullable=False)
    source = db.Column(db.String(100), nullable=True)  # 来源
    estimated_value = db.Column(db.Float, default=0.0, nullable=False)  # 预估价值
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # 负责人关联到用户
    assigned_to_id = db.Column(db.Integer, db.ForeignKey('user_access.id'), nullable=True)
    assigned_to_user = db.relationship('UserAccess', foreign_keys=[assigned_to_id], backref='assigned_leads')
    assigned_to = db.Column(db.String(100), nullable=True)  # 负责人名称 (冗余字段)
    
    # 创建者关联
    created_by_id = db.Column(db.Integer, db.ForeignKey('user_access.id'), nullable=True)
    created_by = db.relationship('UserAccess', foreign_keys=[created_by_id], backref='created_leads')
    
    description = db.Column(db.Text, nullable=True)
    next_follow_up = db.Column(db.DateTime, nullable=True)  # 下次跟进时间
    
    # 关联
    activities = db.relationship('Activity', backref='lead', lazy=True, cascade="all, delete-orphan")
    
    def __init__(self, customer_id, title, status=LeadStatus.NEW, source=None, estimated_value=0.0, 
                 assigned_to_id=None, assigned_to=None, created_by_id=None, description=None, next_follow_up=None):
        self.customer_id = customer_id
        self.title = title
        self.status = status
        self.source = source
        self.estimated_value = estimated_value
        self.assigned_to_id = assigned_to_id
        self.assigned_to = assigned_to
        self.created_by_id = created_by_id
        self.description = description
        self.next_follow_up = next_follow_up
    
    def __repr__(self):
        return f"<Lead {self.title} - {self.status.value}>"

class Deal(db.Model):
    """交易项目"""
    __tablename__ = 'crm_deals'
    
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('crm_customers.id'), nullable=False)
    lead_id = db.Column(db.Integer, db.ForeignKey('crm_leads.id'), nullable=True)
    title = db.Column(db.String(200), nullable=False)
    status = db.Column(db.Enum(DealStatus), default=DealStatus.DRAFT, nullable=False)
    value = db.Column(db.Float, default=0.0, nullable=False)  # 交易金额
    currency = db.Column(db.String(10), default="USD", nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    expected_close_date = db.Column(db.DateTime, nullable=True)
    closed_date = db.Column(db.DateTime, nullable=True)
    
    # 负责人关联到用户
    assigned_to_id = db.Column(db.Integer, db.ForeignKey('user_access.id'), nullable=True)
    assigned_to_user = db.relationship('UserAccess', foreign_keys=[assigned_to_id], backref='assigned_deals')
    assigned_to = db.Column(db.String(100), nullable=True)  # 负责人名称 (冗余字段)
    
    # 创建者关联
    created_by_id = db.Column(db.Integer, db.ForeignKey('user_access.id'), nullable=True)
    created_by = db.relationship('UserAccess', foreign_keys=[created_by_id], backref='created_deals')
    
    description = db.Column(db.Text, nullable=True)
    
    # 挖矿相关属性
    mining_capacity = db.Column(db.Float, nullable=True)  # 挖矿容量（MW）
    electricity_cost = db.Column(db.Float, nullable=True)  # 电费价格 (kWh)
    contract_term = db.Column(db.Integer, nullable=True)  # 合同期限(月)
    
    # 矿场中介业务相关字段
    commission_type = db.Column(db.String(20), default="percentage", nullable=False)  # 佣金类型: percentage / fixed
    commission_rate = db.Column(db.Float, nullable=True)  # 抽成比例 (%)
    commission_amount = db.Column(db.Float, nullable=True)  # 固定佣金金额 (USD)
    mining_farm_name = db.Column(db.String(200), nullable=True)  # 矿场名称
    mining_farm_location = db.Column(db.String(200), nullable=True)  # 矿场位置
    client_investment = db.Column(db.Float, nullable=True)  # 客户投资金额
    monthly_profit_estimate = db.Column(db.Float, nullable=True)  # 预估月利润
    
    # 关联
    activities = db.relationship('Activity', backref='deal', lazy=True, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Deal {self.title} - {self.status.value} - ${self.value}>"

class CommissionRecord(db.Model):
    """佣金收入记录"""
    __tablename__ = 'commission_records'
    
    id = db.Column(db.Integer, primary_key=True)
    deal_id = db.Column(db.Integer, db.ForeignKey('crm_deals.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('crm_customers.id'), nullable=False)
    
    record_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    record_month = db.Column(db.String(7), nullable=False)  # 格式: 2025-01
    
    # 客户挖矿数据
    client_monthly_profit = db.Column(db.Float, nullable=False)  # 客户月利润
    client_btc_mined = db.Column(db.Float, nullable=True)  # 客户月产BTC
    btc_price = db.Column(db.Float, nullable=True)  # 当月BTC价格
    
    # 佣金计算
    commission_type = db.Column(db.String(20), nullable=False)  # percentage / fixed
    commission_rate = db.Column(db.Float, nullable=True)  # 抽成比例
    commission_amount = db.Column(db.Float, nullable=False)  # 实际佣金金额
    
    # 支付状态
    paid = db.Column(db.Boolean, default=False, nullable=False)
    paid_date = db.Column(db.DateTime, nullable=True)
    
    notes = db.Column(db.Text, nullable=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user_access.id'), nullable=True)
    
    def __repr__(self):
        return f"<CommissionRecord {self.record_month} - ${self.commission_amount}>"

class CommissionEditHistory(db.Model):
    """佣金记录编辑历史"""
    __tablename__ = 'commission_edit_history'
    
    id = db.Column(db.Integer, primary_key=True)
    commission_record_id = db.Column(db.Integer, db.ForeignKey('commission_records.id'), nullable=False)
    
    # 编辑信息
    edited_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    edited_by_id = db.Column(db.Integer, db.ForeignKey('user_access.id'), nullable=True)
    edited_by_name = db.Column(db.String(100), nullable=True)
    
    # 编辑的字段和值
    field_name = db.Column(db.String(50), nullable=False)  # 被修改的字段名
    old_value = db.Column(db.Text, nullable=True)  # 原值
    new_value = db.Column(db.Text, nullable=True)  # 新值
    change_reason = db.Column(db.String(200), nullable=True)  # 修改原因
    
    def __repr__(self):
        return f"<EditHistory {self.field_name}: {self.old_value} -> {self.new_value}>"

class Activity(db.Model):
    """客户活动记录"""
    __tablename__ = 'crm_activities'
    
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('crm_customers.id'), nullable=False)
    lead_id = db.Column(db.Integer, db.ForeignKey('crm_leads.id'), nullable=True)
    deal_id = db.Column(db.Integer, db.ForeignKey('crm_deals.id'), nullable=True)
    type = db.Column(db.String(50), default="备注", nullable=False)  # 备注, 电话, 会议, 邮件等
    summary = db.Column(db.String(200), nullable=False)
    details = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # 创建人关联到用户
    created_by_id = db.Column(db.Integer, db.ForeignKey('user_access.id'), nullable=True)
    created_by_user = db.relationship('UserAccess', foreign_keys=[created_by_id], backref='created_activities')
    created_by = db.Column(db.String(100), nullable=True)  # 创建人名称 (冗余字段，方便显示)
    
    # 关联到客户
    customer = db.relationship('Customer', backref=db.backref('activities', lazy=True))
    
    def __init__(self, customer_id, summary, type="备注", lead_id=None, deal_id=None, details=None, 
                 created_by_id=None, created_by=None):
        self.customer_id = customer_id
        self.summary = summary
        self.type = type
        self.lead_id = lead_id
        self.deal_id = deal_id
        self.details = details
        self.created_by_id = created_by_id
        self.created_by = created_by
    
    def __repr__(self):
        return f"<Activity {self.type} - {self.summary}>"