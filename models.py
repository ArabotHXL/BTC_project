# 标准库导入
from datetime import datetime, timedelta
import enum
import logging

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

class MinerModel(db.Model):
    """矿机型号信息数据库模型"""
    __tablename__ = 'miner_models'
    
    id = db.Column(db.Integer, primary_key=True)
    model_name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    manufacturer = db.Column(db.String(50), nullable=False)  # 制造商 (Antminer, WhatsMiner, etc.)
    reference_hashrate = db.Column(db.Float, nullable=False)  # 参考算力 (TH/s)
    reference_power = db.Column(db.Integer, nullable=False)  # 参考功耗 (W)
    reference_efficiency = db.Column(db.Float, nullable=True)  # 参考能效比 (W/TH)
    release_date = db.Column(db.Date, nullable=True)  # 发布日期
    reference_price = db.Column(db.Float, nullable=True)  # 参考价格 ($)
    is_active = db.Column(db.Boolean, default=True)  # 是否可用
    is_liquid_cooled = db.Column(db.Boolean, default=False)  # 是否水冷
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 技术规格
    chip_type = db.Column(db.String(50), nullable=True)  # 芯片类型
    fan_count = db.Column(db.Integer, nullable=True)  # 风扇数量
    operating_temp_min = db.Column(db.Integer, nullable=True)  # 最低工作温度
    operating_temp_max = db.Column(db.Integer, nullable=True)  # 最高工作温度
    noise_level = db.Column(db.Integer, nullable=True)  # 噪音等级 (dB)
    
    # 尺寸信息
    length_mm = db.Column(db.Float, nullable=True)  # 长度(mm)
    width_mm = db.Column(db.Float, nullable=True)   # 宽度(mm) 
    height_mm = db.Column(db.Float, nullable=True)  # 高度(mm)
    weight_kg = db.Column(db.Float, nullable=True)  # 重量(kg)
    
    def __init__(self, model_name, manufacturer, reference_hashrate, reference_power, **kwargs):
        self.model_name = model_name
        self.manufacturer = manufacturer
        self.reference_hashrate = reference_hashrate
        self.reference_power = reference_power
        
        # 自动计算参考能效比
        if reference_hashrate > 0:
            self.reference_efficiency = round(reference_power / reference_hashrate, 2)
        
        # 处理其他可选参数
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def __repr__(self):
        return f"<MinerModel {self.model_name}: {self.reference_hashrate}TH/s, {self.reference_power}W>"
    
    def to_dict(self):
        """转换为字典格式，便于JSON序列化"""
        return {
            'id': self.id,
            'model_name': self.model_name,
            'manufacturer': self.manufacturer,
            'reference_hashrate': self.reference_hashrate,
            'reference_power': self.reference_power,
            'reference_efficiency': self.reference_efficiency,
            'reference_price': self.reference_price,
            'is_active': self.is_active,
            'is_liquid_cooled': self.is_liquid_cooled,
            'release_date': self.release_date.isoformat() if self.release_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'chip_type': self.chip_type,
            'fan_count': self.fan_count,
            'operating_temp_min': self.operating_temp_min,
            'operating_temp_max': self.operating_temp_max,
            'noise_level': self.noise_level,
            'length_mm': self.length_mm,
            'width_mm': self.width_mm,
            'height_mm': self.height_mm,
            'weight_kg': self.weight_kg
        }
    
    @classmethod
    def get_active_miners(cls):
        """获取所有启用的矿机型号"""
        from app import db
        return db.session.query(cls).filter_by(is_active=True).order_by(cls.manufacturer, cls.model_name).all()
    
    @classmethod
    def get_by_name(cls, model_name):
        """根据型号名称获取矿机"""
        from app import db
        return db.session.query(cls).filter_by(model_name=model_name, is_active=True).first()
    
    @classmethod
    def get_by_manufacturer(cls, manufacturer):
        """根据制造商获取矿机列表"""
        from app import db
        return db.session.query(cls).filter_by(manufacturer=manufacturer, is_active=True).order_by(cls.model_name).all()

class UserMiner(db.Model):
    """用户矿机设备数据库模型 - 存储用户的实际矿机信息"""
    __tablename__ = 'user_miners'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # 关联字段
    user_id = db.Column(db.Integer, db.ForeignKey('user_access.id'), nullable=False, index=True)
    miner_model_id = db.Column(db.Integer, db.ForeignKey('miner_models.id'), nullable=False, index=True)
    
    # 用户自定义信息
    custom_name = db.Column(db.String(100), nullable=True)  # 用户自定义名称
    quantity = db.Column(db.Integer, nullable=False, default=1)  # 数量
    
    # 实际用户数据 (覆盖系统默认值)
    actual_hashrate = db.Column(db.Float, nullable=False)  # 实际算力 (TH/s)
    actual_power = db.Column(db.Integer, nullable=False)  # 实际功耗 (W)
    actual_price = db.Column(db.Float, nullable=False)  # 实际购买价格 ($)
    electricity_cost = db.Column(db.Float, nullable=False)  # 电费成本 ($/kWh)
    decay_rate_monthly = db.Column(db.Float, nullable=False, default=0.5)  # 月衰减率 (%)
    
    # 设备管理信息
    status = db.Column(db.String(20), nullable=False, default='active')  # active/maintenance/offline/sold
    location = db.Column(db.String(200), nullable=True)  # 存放位置
    purchase_date = db.Column(db.Date, nullable=True)  # 购买日期
    notes = db.Column(db.Text, nullable=True)  # 用户备注
    
    # 维修和历史记录
    original_hashrate = db.Column(db.Float, nullable=True)  # 原始算力，用于对比衰减
    last_maintenance_date = db.Column(db.Date, nullable=True)  # 上次维修日期
    maintenance_count = db.Column(db.Integer, nullable=False, default=0)  # 维修次数
    
    # 时间戳
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # 关联关系
    user = db.relationship('UserAccess', backref='miners', foreign_keys=[user_id])
    miner_model = db.relationship('MinerModel', backref='user_instances', foreign_keys=[miner_model_id])
    
    def __init__(self, user_id, miner_model_id, actual_hashrate, actual_power, 
                 actual_price, electricity_cost, quantity=1, **kwargs):
        self.user_id = user_id
        self.miner_model_id = miner_model_id
        self.actual_hashrate = actual_hashrate
        self.actual_power = actual_power
        self.actual_price = actual_price
        self.electricity_cost = electricity_cost
        self.quantity = quantity
        
        # 设置原始算力为当前算力（如果没有提供的话）
        if 'original_hashrate' not in kwargs:
            self.original_hashrate = actual_hashrate
        
        # 处理其他可选参数
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def __repr__(self):
        model_name = self.miner_model.model_name if self.miner_model else "Unknown"
        return f"<UserMiner {self.custom_name or model_name} x{self.quantity}: {self.actual_hashrate}TH/s>"
    
    def to_dict(self):
        """转换为字典格式，便于JSON序列化"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'miner_model_id': self.miner_model_id,
            'miner_model_name': self.miner_model.model_name if self.miner_model else None,
            'custom_name': self.custom_name,
            'quantity': self.quantity,
            'actual_hashrate': self.actual_hashrate,
            'actual_power': self.actual_power,
            'actual_price': self.actual_price,
            'electricity_cost': self.electricity_cost,
            'decay_rate_monthly': self.decay_rate_monthly,
            'status': self.status,
            'location': self.location,
            'purchase_date': self.purchase_date.isoformat() if self.purchase_date else None,
            'notes': self.notes,
            'original_hashrate': self.original_hashrate,
            'last_maintenance_date': self.last_maintenance_date.isoformat() if self.last_maintenance_date else None,
            'maintenance_count': self.maintenance_count,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def calculate_total_hashrate(self):
        """计算总算力"""
        return self.actual_hashrate * self.quantity
    
    def calculate_total_power(self):
        """计算总功耗"""
        return self.actual_power * self.quantity
    
    def calculate_hashrate_degradation(self):
        """计算算力衰减百分比"""
        if not self.original_hashrate or self.original_hashrate == 0:
            return 0
        return ((self.original_hashrate - self.actual_hashrate) / self.original_hashrate) * 100
    
    def update_after_maintenance(self, new_hashrate, maintenance_notes=None):
        """维修后更新算力"""
        self.actual_hashrate = new_hashrate
        self.last_maintenance_date = datetime.utcnow().date()
        self.maintenance_count += 1
        if maintenance_notes:
            current_notes = self.notes or ""
            maintenance_log = f"\n[{datetime.utcnow().strftime('%Y-%m-%d')}] 维修记录: {maintenance_notes}"
            self.notes = current_notes + maintenance_log
        self.updated_at = datetime.utcnow()
    
    @classmethod
    def get_user_miners(cls, user_id, status=None):
        """获取用户的矿机列表"""
        from app import db
        query = db.session.query(cls).filter_by(user_id=user_id)
        if status:
            query = query.filter_by(status=status)
        return query.order_by(cls.created_at.desc()).all()
    
    @classmethod
    def get_user_miner_summary(cls, user_id):
        """获取用户矿机汇总信息"""
        from app import db
        miners = cls.get_user_miners(user_id, status='active')
        
        total_miners = sum(miner.quantity for miner in miners)
        total_hashrate = sum(miner.calculate_total_hashrate() for miner in miners)
        total_power = sum(miner.calculate_total_power() for miner in miners)
        
        return {
            'total_miners': total_miners,
            'total_hashrate': total_hashrate,
            'total_power': total_power,
            'active_records': len(miners)
        }

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
    username = db.Column(db.String(50), nullable=True, unique=True)  # 新增用户名字段
    password_hash = db.Column(db.String(512), nullable=True)  # 新增密码哈希字段
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
    subscription_plan = db.Column(db.String(20), default="free", nullable=False)  # 订阅计划: free, basic, pro
    
    # 创建者关联（矿场主可以创建客户）
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
    
    def set_password(self, password):
        """设置密码哈希"""
        from werkzeug.security import generate_password_hash
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """验证密码"""
        from werkzeug.security import check_password_hash
        # 检查密码哈希是否存在且不为空字符串
        if not self.password_hash or self.password_hash.strip() == '':
            return False
        try:
            return check_password_hash(self.password_hash, password)
        except ValueError as e:
            # 如果密码哈希格式无效，记录错误并返回False
            logging.warning(f"密码哈希格式无效: {e}")
            return False
    
    def generate_email_verification_token(self):
        """生成邮箱验证令牌"""
        import secrets
        self.email_verification_token = secrets.token_urlsafe(32)
        return self.email_verification_token
    
    def verify_email(self):
        """验证邮箱"""
        self.is_email_verified = True
        self.email_verification_token = None
    
    def calculate_expiry(self):
        """重新计算到期时间（基于access_days）"""
        self.expires_at = self.created_at + timedelta(days=self.access_days)
        
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