# 标准库导入
from datetime import datetime, timedelta
import enum
import logging

# 本地模块导入
from db import db

class BlockchainVerificationStatus(enum.Enum):
    """区块链验证状态"""
    PENDING = "待验证"
    REGISTERED = "已注册"
    VERIFIED = "已验证"
    FAILED = "验证失败"
    EXPIRED = "已过期"

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
        return cls.query.filter_by(is_active=True).order_by(cls.manufacturer, cls.model_name).all()

    @classmethod
    def get_by_name(cls, model_name):
        """根据型号名称获取矿机"""
        return cls.query.filter_by(model_name=model_name, is_active=True).first()

    @classmethod
    def get_by_manufacturer(cls, manufacturer):
        """根据制造商获取矿机列表"""
        return cls.query.filter_by(manufacturer=manufacturer, is_active=True).order_by(cls.model_name).all()

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
    
    # Web3钱包认证支持
    wallet_address = db.Column(db.String(42), nullable=True, unique=True, index=True)  # 以太坊钱包地址
    wallet_verified = db.Column(db.Boolean, default=False, nullable=False)  # 钱包验证状态
    wallet_nonce = db.Column(db.String(100), nullable=True)  # 钱包签名随机数

    # 创建者关联（矿场主可以创建客户）
    created_by_id = db.Column(db.Integer, db.ForeignKey('user_access.id'), nullable=True)
    created_by = db.relationship('UserAccess', foreign_keys=[created_by_id], backref='managed_users', remote_side=[id])

    def __init__(self, name, email, access_days=30, company=None, position=None, notes=None, role="guest", 
                 username=None, password_hash=None, subscription_plan="free", wallet_address=None):
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
        self.wallet_address = wallet_address

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

    def generate_wallet_nonce(self):
        """生成钱包签名随机数"""
        import secrets
        import time
        timestamp = str(int(time.time()))
        random_string = secrets.token_urlsafe(16)
        self.wallet_nonce = f"{timestamp}_{random_string}"
        return self.wallet_nonce

    def verify_wallet_signature(self, signature, message):
        """验证钱包签名"""
        if not self.wallet_address or not signature:
            return False
        
        try:
            from eth_account.messages import encode_defunct
            from eth_account import Account
            
            # 编码消息
            message_hash = encode_defunct(text=message)
            
            # 恢复签名者地址
            recovered_address = Account.recover_message(message_hash, signature=signature)
            
            # 比较地址（不区分大小写）
            return recovered_address.lower() == self.wallet_address.lower()
        except Exception as e:
            logging.error(f"钱包签名验证失败: {e}")
            return False

    def set_wallet_address(self, wallet_address):
        """设置钱包地址"""
        if wallet_address:
            # 标准化地址格式
            wallet_address = wallet_address.lower()
            # 验证地址格式
            if len(wallet_address) == 42 and wallet_address.startswith('0x'):
                self.wallet_address = wallet_address
                self.wallet_verified = False  # 重置验证状态
                return True
        return False

    def verify_wallet(self):
        """标记钱包为已验证"""
        self.wallet_verified = True
        self.wallet_nonce = None  # 清除使用过的nonce

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

# ==================== 托管平台数据模型 ====================

class HostingSite(db.Model):
    """托管站点管理"""
    __tablename__ = 'hosting_sites'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(50), unique=True, nullable=False, index=True)  # 用于公开状态页面
    location = db.Column(db.String(200), nullable=False)
    capacity_mw = db.Column(db.Float, nullable=False)  # 总容量(MW)
    used_capacity_mw = db.Column(db.Float, default=0.0, nullable=False)  # 已用容量(MW)
    
    # 站点状态
    status = db.Column(db.String(20), default='online', nullable=False)  # online/offline/maintenance
    operator_name = db.Column(db.String(100), nullable=False)  # 运营商名称
    contact_email = db.Column(db.String(256), nullable=True)
    contact_phone = db.Column(db.String(50), nullable=True)
    
    # 电力信息
    electricity_rate = db.Column(db.Float, nullable=False)  # 电费费率 ($/kWh)
    electricity_source = db.Column(db.String(50), nullable=True)  # 电力来源
    
    # 时间戳
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # 关联关系
    miners = db.relationship('HostingMiner', backref='site', lazy=True, cascade="all, delete-orphan")
    incidents = db.relationship('HostingIncident', backref='site', lazy=True, cascade="all, delete-orphan")
    
    def __init__(self, name, slug, location, capacity_mw, electricity_rate, operator_name, **kwargs):
        self.name = name
        self.slug = slug
        self.location = location
        self.capacity_mw = capacity_mw
        self.electricity_rate = electricity_rate
        self.operator_name = operator_name
        
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    @property
    def utilization_rate(self):
        """计算容量利用率"""
        if self.capacity_mw == 0:
            return 0
        return (self.used_capacity_mw / self.capacity_mw) * 100
    
    @property
    def available_capacity_mw(self):
        """可用容量"""
        return self.capacity_mw - self.used_capacity_mw
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'slug': self.slug,
            'location': self.location,
            'capacity_mw': self.capacity_mw,
            'used_capacity_mw': self.used_capacity_mw,
            'available_capacity_mw': self.available_capacity_mw,
            'utilization_rate': self.utilization_rate,
            'status': self.status,
            'operator_name': self.operator_name,
            'electricity_rate': self.electricity_rate,
            'created_at': self.created_at.isoformat()
        }

class HostingMiner(db.Model):
    """托管矿机实例"""
    __tablename__ = 'hosting_miners'

    id = db.Column(db.Integer, primary_key=True)
    
    # 关联字段
    site_id = db.Column(db.Integer, db.ForeignKey('hosting_sites.id'), nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('user_access.id'), nullable=False, index=True)
    miner_model_id = db.Column(db.Integer, db.ForeignKey('miner_models.id'), nullable=False, index=True)
    
    # 设备信息
    serial_number = db.Column(db.String(100), unique=True, nullable=False, index=True)
    rack_position = db.Column(db.String(50), nullable=True)  # 机架位置
    ip_address = db.Column(db.String(45), nullable=True)  # 支持IPv6
    mac_address = db.Column(db.String(17), nullable=True)
    
    # 实际性能数据
    actual_hashrate = db.Column(db.Float, nullable=False)  # 实际算力 (TH/s)
    actual_power = db.Column(db.Float, nullable=False)  # 实际功耗 (W)
    
    # 状态管理
    status = db.Column(db.String(20), default='active', nullable=False)  # active/offline/maintenance/error
    health_score = db.Column(db.Integer, default=100, nullable=False)  # 健康度评分 0-100
    
    # 审核工作流字段
    approval_status = db.Column(db.String(20), default='draft')  # draft, pending_approval, approved, rejected
    submitted_by = db.Column(db.Integer, db.ForeignKey('user_access.id'), nullable=True)  # 申请人
    approved_by = db.Column(db.Integer, db.ForeignKey('user_access.id'), nullable=True)  # 审核人
    approval_notes = db.Column(db.Text, nullable=True)  # 审核备注
    submitted_at = db.Column(db.DateTime, nullable=True)  # 申请时间
    approved_at = db.Column(db.DateTime, nullable=True)  # 审核时间
    
    # 运营数据
    install_date = db.Column(db.DateTime, nullable=True)  # 安装日期
    last_maintenance = db.Column(db.DateTime, nullable=True)  # 上次维护时间
    maintenance_count = db.Column(db.Integer, default=0, nullable=False)
    
    # 时间戳
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # 关联关系
    customer = db.relationship('UserAccess', foreign_keys=[customer_id], backref='hosted_miners')
    miner_model = db.relationship('MinerModel', foreign_keys=[miner_model_id])
    submitter = db.relationship('UserAccess', foreign_keys=[submitted_by], backref='submitted_miners')
    approver = db.relationship('UserAccess', foreign_keys=[approved_by], backref='approved_miners')
    telemetry_data = db.relationship('MinerTelemetry', backref='miner', lazy=True, cascade="all, delete-orphan")
    
    def __init__(self, site_id, customer_id, miner_model_id, serial_number, actual_hashrate, actual_power, **kwargs):
        self.site_id = site_id
        self.customer_id = customer_id
        self.miner_model_id = miner_model_id
        self.serial_number = serial_number
        self.actual_hashrate = actual_hashrate
        self.actual_power = actual_power
        
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def to_dict(self):
        return {
            'id': self.id,
            'site_id': self.site_id,
            'customer_id': self.customer_id,
            'serial_number': self.serial_number,
            'rack_position': self.rack_position,
            'miner_model_name': self.miner_model.model_name if self.miner_model else None,
            'actual_hashrate': self.actual_hashrate,
            'actual_power': self.actual_power,
            'status': self.status,
            'health_score': self.health_score,
            'approval_status': self.approval_status,
            'submitted_by': self.submitted_by,
            'approved_by': self.approved_by,
            'approval_notes': self.approval_notes,
            'submitted_at': self.submitted_at.isoformat() if self.submitted_at else None,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'install_date': self.install_date.isoformat() if self.install_date else None,
            'last_maintenance': self.last_maintenance.isoformat() if self.last_maintenance else None
        }

class MinerTelemetry(db.Model):
    """矿机遥测数据"""
    __tablename__ = 'miner_telemetry'

    id = db.Column(db.Integer, primary_key=True)
    miner_id = db.Column(db.Integer, db.ForeignKey('hosting_miners.id'), nullable=False, index=True)
    
    # 性能指标
    hashrate = db.Column(db.Float, nullable=False)  # 当前算力
    power_consumption = db.Column(db.Float, nullable=False)  # 当前功耗
    temperature = db.Column(db.Float, nullable=True)  # 温度
    fan_speed = db.Column(db.Integer, nullable=True)  # 风扇转速
    
    # 矿池数据
    pool_url = db.Column(db.String(200), nullable=True)
    pool_worker = db.Column(db.String(100), nullable=True)
    accepted_shares = db.Column(db.BigInteger, default=0)
    rejected_shares = db.Column(db.BigInteger, default=0)
    
    # 记录时间
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    def __init__(self, miner_id, hashrate, power_consumption, **kwargs):
        self.miner_id = miner_id
        self.hashrate = hashrate
        self.power_consumption = power_consumption
        
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

class HostingIncident(db.Model):
    """托管事件记录"""
    __tablename__ = 'hosting_incidents'

    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey('hosting_sites.id'), nullable=False, index=True)
    
    # 事件信息
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    severity = db.Column(db.String(20), default='low', nullable=False)  # low/medium/high/critical
    status = db.Column(db.String(20), default='open', nullable=False)  # open/investigating/resolved/closed
    
    # 影响范围
    affected_miners = db.Column(db.Text, nullable=True)  # JSON格式存储受影响的矿机列表
    estimated_loss = db.Column(db.Float, default=0.0, nullable=False)  # 预估损失
    
    # 时间追踪
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    first_response_at = db.Column(db.DateTime, nullable=True)  # 首次响应时间
    resolved_at = db.Column(db.DateTime, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # 负责人
    assigned_to_id = db.Column(db.Integer, db.ForeignKey('user_access.id'), nullable=True)
    assigned_to = db.relationship('UserAccess', foreign_keys=[assigned_to_id], backref='assigned_incidents')
    
    def __init__(self, site_id, title, severity='low', **kwargs):
        self.site_id = site_id
        self.title = title
        self.severity = severity
        
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

class HostingTicket(db.Model):
    """工单系统"""
    __tablename__ = 'hosting_tickets'

    id = db.Column(db.Integer, primary_key=True)
    
    # 基本信息
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    priority = db.Column(db.String(20), default='medium', nullable=False)  # low/medium/high/urgent
    status = db.Column(db.String(20), default='open', nullable=False)  # open/assigned/in_progress/resolved/closed
    category = db.Column(db.String(50), nullable=True)  # hardware/network/power/other
    
    # 关联信息
    customer_id = db.Column(db.Integer, db.ForeignKey('user_access.id'), nullable=False, index=True)
    site_id = db.Column(db.Integer, db.ForeignKey('hosting_sites.id'), nullable=True, index=True)
    assigned_to_id = db.Column(db.Integer, db.ForeignKey('user_access.id'), nullable=True)
    
    # SLA追踪
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    first_response_at = db.Column(db.DateTime, nullable=True)  # 首次响应时间
    resolved_at = db.Column(db.DateTime, nullable=True)  # 解决时间
    
    # 关联关系
    customer = db.relationship('UserAccess', foreign_keys=[customer_id], backref='tickets')
    assigned_to = db.relationship('UserAccess', foreign_keys=[assigned_to_id], backref='assigned_tickets')
    
    def __init__(self, title, customer_id, **kwargs):
        self.title = title
        self.customer_id = customer_id
        
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    @property
    def response_time_minutes(self):
        """首响时间（分钟）"""
        if not self.first_response_at:
            return None
        delta = self.first_response_at - self.created_at
        return int(delta.total_seconds() / 60)
    
    @property
    def resolution_time_hours(self):
        """解决时间（小时）"""
        if not self.resolved_at:
            return None
        delta = self.resolved_at - self.created_at
        return round(delta.total_seconds() / 3600, 1)

class HostingBill(db.Model):
    """托管账单"""
    __tablename__ = 'hosting_bills'

    id = db.Column(db.Integer, primary_key=True)
    
    # 账单基本信息
    bill_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('user_access.id'), nullable=False, index=True)
    site_id = db.Column(db.Integer, db.ForeignKey('hosting_sites.id'), nullable=False, index=True)
    
    # 计费周期
    billing_period_start = db.Column(db.Date, nullable=False)
    billing_period_end = db.Column(db.Date, nullable=False)
    
    # 费用明细
    electricity_cost = db.Column(db.Float, default=0.0, nullable=False)  # 电费
    hosting_fee = db.Column(db.Float, default=0.0, nullable=False)  # 托管费
    maintenance_cost = db.Column(db.Float, default=0.0, nullable=False)  # 维护费
    penalty_cost = db.Column(db.Float, default=0.0, nullable=False)  # 罚金/扣费
    discount = db.Column(db.Float, default=0.0, nullable=False)  # 折扣
    total_amount = db.Column(db.Float, nullable=False)  # 总金额
    
    # 账单状态
    status = db.Column(db.String(20), default='draft', nullable=False)  # draft/sent/paid/overdue/cancelled
    
    # 时间戳
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    sent_at = db.Column(db.DateTime, nullable=True)
    paid_at = db.Column(db.DateTime, nullable=True)
    due_date = db.Column(db.Date, nullable=True)
    
    # 关联关系
    customer = db.relationship('UserAccess', foreign_keys=[customer_id], backref='hosting_bills')
    site = db.relationship('HostingSite', foreign_keys=[site_id], backref='bills')
    bill_items = db.relationship('HostingBillItem', backref='bill', lazy=True, cascade="all, delete-orphan")
    
    def calculate_total(self):
        """计算总金额"""
        self.total_amount = (self.electricity_cost + self.hosting_fee + 
                           self.maintenance_cost + self.penalty_cost - self.discount)
        return self.total_amount

class HostingBillItem(db.Model):
    """账单明细项"""
    __tablename__ = 'hosting_bill_items'

    id = db.Column(db.Integer, primary_key=True)
    bill_id = db.Column(db.Integer, db.ForeignKey('hosting_bills.id'), nullable=False, index=True)
    
    # 明细信息
    item_type = db.Column(db.String(50), nullable=False)  # electricity/hosting/maintenance/penalty/discount
    description = db.Column(db.String(500), nullable=False)
    quantity = db.Column(db.Float, default=1.0, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    
    # 关联矿机（可选）
    miner_id = db.Column(db.Integer, db.ForeignKey('hosting_miners.id'), nullable=True)
    miner = db.relationship('HostingMiner', foreign_keys=[miner_id])


class BlockchainRecord(db.Model):
    """区块链数据记录模型 - 存储链上记录和IPFS数据"""
    __tablename__ = 'blockchain_records'

    id = db.Column(db.Integer, primary_key=True)
    
    # 数据标识
    data_hash = db.Column(db.String(66), unique=True, nullable=False, index=True)  # 0x + 64位十六进制
    ipfs_cid = db.Column(db.String(100), nullable=False, index=True)  # IPFS内容标识符
    
    # 站点信息
    site_id = db.Column(db.String(100), nullable=False, index=True)  # 矿场站点ID
    site_name = db.Column(db.String(200), nullable=True)  # 站点名称
    
    # 区块链信息
    blockchain_network = db.Column(db.String(50), default='Base L2', nullable=False)  # 区块链网络
    contract_address = db.Column(db.String(42), nullable=True)  # 智能合约地址
    transaction_hash = db.Column(db.String(66), nullable=True, index=True)  # 交易哈希
    block_number = db.Column(db.BigInteger, nullable=True)  # 区块号
    gas_used = db.Column(db.Integer, nullable=True)  # 使用的gas
    gas_price = db.Column(db.BigInteger, nullable=True)  # gas价格
    
    # 数据内容摘要
    mining_data_summary = db.Column(db.Text, nullable=True)  # 挖矿数据摘要（JSON格式）
    hashrate_th = db.Column(db.Float, nullable=True)  # 算力 (TH/s)
    power_consumption_w = db.Column(db.Float, nullable=True)  # 功耗 (W)
    daily_btc_production = db.Column(db.Float, nullable=True)  # 日产BTC
    daily_revenue_usd = db.Column(db.Float, nullable=True)  # 日收入 (USD)
    
    # 验证状态
    verification_status = db.Column(
        db.Enum(BlockchainVerificationStatus), 
        default=BlockchainVerificationStatus.PENDING, 
        nullable=False
    )
    verification_count = db.Column(db.Integer, default=0, nullable=False)  # 验证次数
    last_verified_at = db.Column(db.DateTime, nullable=True)  # 最后验证时间
    
    # 数据完整性
    data_version = db.Column(db.String(10), default='1.0', nullable=False)  # 数据版本
    encryption_enabled = db.Column(db.Boolean, default=True, nullable=False)  # 是否加密
    data_integrity_hash = db.Column(db.String(64), nullable=True)  # 数据完整性哈希
    
    # 关联信息
    user_id = db.Column(db.Integer, db.ForeignKey('user_access.id'), nullable=True, index=True)  # 关联用户
    created_by = db.Column(db.String(100), default='system', nullable=False)  # 创建者
    
    # 时间戳
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    blockchain_timestamp = db.Column(db.DateTime, nullable=True)  # 区块链时间戳
    data_timestamp = db.Column(db.DateTime, nullable=False)  # 数据生成时间戳
    
    # 元数据
    record_metadata = db.Column(db.Text, nullable=True)  # 额外元数据（JSON格式）
    notes = db.Column(db.Text, nullable=True)  # 备注
    
    # 关联关系
    user = db.relationship('UserAccess', foreign_keys=[user_id], backref='blockchain_records')
    
    def __init__(self, data_hash, ipfs_cid, site_id, **kwargs):
        """初始化区块链记录"""
        self.data_hash = data_hash
        self.ipfs_cid = ipfs_cid
        self.site_id = site_id
        self.data_timestamp = kwargs.get('data_timestamp', datetime.utcnow())
        
        # 处理其他可选参数
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def __repr__(self):
        return f"<BlockchainRecord {self.data_hash[:16]}... Site: {self.site_id}>"
    
    def to_dict(self):
        """转换为字典格式，便于JSON序列化"""
        return {
            'id': self.id,
            'data_hash': self.data_hash,
            'ipfs_cid': self.ipfs_cid,
            'site_id': self.site_id,
            'site_name': self.site_name,
            'blockchain_network': self.blockchain_network,
            'contract_address': self.contract_address,
            'transaction_hash': self.transaction_hash,
            'block_number': self.block_number,
            'verification_status': self.verification_status.value if self.verification_status else None,
            'verification_count': self.verification_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'data_timestamp': self.data_timestamp.isoformat() if self.data_timestamp else None
        }
    
    @classmethod
    def get_by_data_hash(cls, data_hash):
        """根据数据哈希获取记录"""
        return cls.query.filter_by(data_hash=data_hash).first()
    
    @classmethod
    def get_by_site(cls, site_id, limit=None):
        """根据站点ID获取记录"""
        query = cls.query.filter_by(site_id=site_id).order_by(cls.created_at.desc())
        if limit:
            query = query.limit(limit)
        return query.all()
    
    def update_verification_status(self, status):
        """更新验证状态"""
        self.verification_status = status
        self.verification_count += 1
        self.last_verified_at = datetime.utcnow()

class HostingAuditLog(db.Model):
    """审计日志"""
    __tablename__ = 'hosting_audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    
    # 操作信息
    user_id = db.Column(db.Integer, db.ForeignKey('user_access.id'), nullable=False, index=True)
    action = db.Column(db.String(100), nullable=False)  # 操作类型
    resource_type = db.Column(db.String(50), nullable=False)  # 资源类型
    resource_id = db.Column(db.String(50), nullable=True)  # 资源ID
    
    # 详细信息
    details = db.Column(db.Text, nullable=True)  # JSON格式的详细信息
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(500), nullable=True)
    
    # 时间戳
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # 关联关系
    user = db.relationship('UserAccess', foreign_keys=[user_id], backref='audit_logs')
    
    def __init__(self, user_id, action, resource_type, **kwargs):
        self.user_id = user_id
        self.action = action
        self.resource_type = resource_type
        
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

class HostingUsageRecord(db.Model):
    """托管使用记录"""
    __tablename__ = 'hosting_usage_records'

    id = db.Column(db.Integer, primary_key=True)
    
    # 使用记录基本信息
    record_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('user_access.id'), nullable=False, index=True)
    site_id = db.Column(db.Integer, db.ForeignKey('hosting_sites.id'), nullable=False, index=True)
    
    # 使用周期
    usage_period_start = db.Column(db.Date, nullable=False)
    usage_period_end = db.Column(db.Date, nullable=False)
    
    # 费用明细
    electricity_cost = db.Column(db.Float, default=0.0, nullable=False)  # 电费
    hosting_fee = db.Column(db.Float, default=0.0, nullable=False)  # 托管费
    maintenance_cost = db.Column(db.Float, default=0.0, nullable=False)  # 维护费
    penalty_cost = db.Column(db.Float, default=0.0, nullable=False)  # 罚金/扣费
    discount = db.Column(db.Float, default=0.0, nullable=False)  # 折扣
    total_amount = db.Column(db.Float, nullable=False)  # 总金额
    
    # 使用记录状态
    status = db.Column(db.String(20), default='draft', nullable=False)  # draft/completed/cancelled
    
    # 时间戳
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    completed_at = db.Column(db.DateTime, nullable=True)
    report_date = db.Column(db.Date, nullable=True)
    
    # 关联关系
    customer = db.relationship('UserAccess', foreign_keys=[customer_id], backref='hosting_usage_records')
    site = db.relationship('HostingSite', foreign_keys=[site_id], backref='usage_records')
    usage_items = db.relationship('HostingUsageItem', backref='usage_record', lazy=True, cascade="all, delete-orphan")
    
    def calculate_total(self):
        """计算总金额"""
        self.total_amount = (self.electricity_cost + self.hosting_fee + 
                           self.maintenance_cost + self.penalty_cost - self.discount)
        return self.total_amount

class HostingUsageItem(db.Model):
    """使用记录明细项"""
    __tablename__ = 'hosting_usage_items'

    id = db.Column(db.Integer, primary_key=True)
    usage_record_id = db.Column(db.Integer, db.ForeignKey('hosting_usage_records.id'), nullable=False, index=True)
    
    # 明细信息
    item_type = db.Column(db.String(50), nullable=False)  # electricity/hosting/maintenance/penalty/discount
    description = db.Column(db.String(500), nullable=False)
    quantity = db.Column(db.Float, default=1.0, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    
    # 关联矿机（可选）
    miner_id = db.Column(db.Integer, db.ForeignKey('hosting_miners.id'), nullable=True)
    miner = db.relationship('HostingMiner', foreign_keys=[miner_id])


class BlockchainRecord(db.Model):
    """区块链数据记录模型 - 存储链上记录和IPFS数据"""
    __tablename__ = 'blockchain_records'

    id = db.Column(db.Integer, primary_key=True)
    
    # 数据标识
    data_hash = db.Column(db.String(66), unique=True, nullable=False, index=True)  # 0x + 64位十六进制
    ipfs_cid = db.Column(db.String(100), nullable=False, index=True)  # IPFS内容标识符
    
    # 站点信息
    site_id = db.Column(db.String(100), nullable=False, index=True)  # 矿场站点ID
    site_name = db.Column(db.String(200), nullable=True)  # 站点名称
    
    # 区块链信息
    blockchain_network = db.Column(db.String(50), default='Base L2', nullable=False)  # 区块链网络
    contract_address = db.Column(db.String(42), nullable=True)  # 智能合约地址
    transaction_hash = db.Column(db.String(66), nullable=True, index=True)  # 交易哈希
    block_number = db.Column(db.BigInteger, nullable=True)  # 区块号
    gas_used = db.Column(db.Integer, nullable=True)  # 使用的gas
    gas_price = db.Column(db.BigInteger, nullable=True)  # gas价格
    
    # 数据内容摘要
    mining_data_summary = db.Column(db.Text, nullable=True)  # 挖矿数据摘要（JSON格式）
    hashrate_th = db.Column(db.Float, nullable=True)  # 算力 (TH/s)
    power_consumption_w = db.Column(db.Float, nullable=True)  # 功耗 (W)
    daily_btc_production = db.Column(db.Float, nullable=True)  # 日产BTC
    daily_revenue_usd = db.Column(db.Float, nullable=True)  # 日收入 (USD)
    
    # 验证状态
    verification_status = db.Column(
        db.Enum(BlockchainVerificationStatus), 
        default=BlockchainVerificationStatus.PENDING, 
        nullable=False
    )
    verification_count = db.Column(db.Integer, default=0, nullable=False)  # 验证次数
    last_verified_at = db.Column(db.DateTime, nullable=True)  # 最后验证时间
    
    # 数据完整性
    data_version = db.Column(db.String(10), default='1.0', nullable=False)  # 数据版本
    encryption_enabled = db.Column(db.Boolean, default=True, nullable=False)  # 是否加密
    data_integrity_hash = db.Column(db.String(64), nullable=True)  # 数据完整性哈希
    
    # 关联信息
    user_id = db.Column(db.Integer, db.ForeignKey('user_access.id'), nullable=True, index=True)  # 关联用户
    created_by = db.Column(db.String(100), default='system', nullable=False)  # 创建者
    
    # 时间戳
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    blockchain_timestamp = db.Column(db.DateTime, nullable=True)  # 区块链时间戳
    data_timestamp = db.Column(db.DateTime, nullable=False)  # 数据生成时间戳
    
    # 元数据
    record_metadata = db.Column(db.Text, nullable=True)  # 额外元数据（JSON格式）
    notes = db.Column(db.Text, nullable=True)  # 备注
    
    # 关联关系
    user = db.relationship('UserAccess', foreign_keys=[user_id], backref='blockchain_records')
    
    def __init__(self, data_hash, ipfs_cid, site_id, **kwargs):
        """初始化区块链记录"""
        self.data_hash = data_hash
        self.ipfs_cid = ipfs_cid
        self.site_id = site_id
        self.data_timestamp = kwargs.get('data_timestamp', datetime.utcnow())
        
        # 处理其他可选参数
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def __repr__(self):
        return f"<BlockchainRecord {self.data_hash[:16]}... Site: {self.site_id}>"
    
    def to_dict(self):
        """转换为字典格式，便于JSON序列化"""
        return {
            'id': self.id,
            'data_hash': self.data_hash,
            'ipfs_cid': self.ipfs_cid,
            'site_id': self.site_id,
            'site_name': self.site_name,
            'blockchain_network': self.blockchain_network,
            'contract_address': self.contract_address,
            'transaction_hash': self.transaction_hash,
            'block_number': self.block_number,
            'verification_status': self.verification_status.value if self.verification_status else None,
            'verification_count': self.verification_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'data_timestamp': self.data_timestamp.isoformat() if self.data_timestamp else None
        }
    
    @classmethod
    def get_by_data_hash(cls, data_hash):
        """根据数据哈希获取记录"""
        return cls.query.filter_by(data_hash=data_hash).first()
    
    @classmethod
    def get_by_site(cls, site_id, limit=None):
        """根据站点ID获取记录"""
        query = cls.query.filter_by(site_id=site_id).order_by(cls.created_at.desc())
        if limit:
            query = query.limit(limit)
        return query.all()
    
    def update_verification_status(self, status):
        """更新验证状态"""
        self.verification_status = status
        self.verification_count += 1
        self.last_verified_at = datetime.utcnow()