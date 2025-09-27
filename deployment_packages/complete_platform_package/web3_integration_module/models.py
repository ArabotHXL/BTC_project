"""
Web3集成模块数据模型
Web3 Integration Module Data Models

包含所有Web3相关的数据库模型：
- 区块链验证记录
- 加密货币支付记录
- NFT证书记录
- 合规检查记录
- 钱包和地址管理
"""

from datetime import datetime, timedelta
import enum
import logging
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, Enum as SQLEnum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

logger = logging.getLogger(__name__)

# 使用app.py中的数据库实例
try:
    from .app import db
    Base = db.Model
except ImportError:
    # 如果无法从 app.py 导入，使用独立的Base
    from sqlalchemy.ext.declarative import declarative_base
    Base = declarative_base()

# 枚举定义
class BlockchainVerificationStatus(enum.Enum):
    """区块链验证状态"""
    PENDING = "pending"
    REGISTERED = "registered"
    VERIFIED = "verified"
    FAILED = "failed"
    EXPIRED = "expired"

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

class SLAStatus(enum.Enum):
    """SLA状态"""
    EXCELLENT = "excellent"    # 95%+
    GOOD = "good"             # 90-95%
    ACCEPTABLE = "acceptable" # 85-90%
    POOR = "poor"            # 80-85%
    FAILED = "failed"        # <80%

class NFTMintStatus(enum.Enum):
    """NFT铸造状态"""
    PENDING = "pending"
    MINTING = "minting"
    MINTED = "minted"
    FAILED = "failed"
    VERIFIED = "verified"

class ComplianceStatus(enum.Enum):
    """合规状态"""
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"
    REVIEW_REQUIRED = "review_required"
    BLOCKED = "blocked"

class RiskLevel(enum.Enum):
    """风险等级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

# 数据库模型

class User(Base):
    """用户模型 - 简化版本，仅包含Web3相关字段"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(64), unique=True, nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    password_hash = Column(String(256), nullable=True)  # 可选，支持钱包登录
    
    # Web3相关字段
    wallet_address = Column(String(42), nullable=True)  # 以太坊地址
    wallet_provider = Column(String(50), nullable=True)  # MetaMask, WalletConnect等
    wallet_verified = Column(Boolean, default=False)
    wallet_verified_at = Column(DateTime, nullable=True)
    
    # 合规相关
    kyc_status = Column(SQLEnum(ComplianceStatus), default=ComplianceStatus.PENDING)
    kyc_verified_at = Column(DateTime, nullable=True)
    risk_level = Column(SQLEnum(RiskLevel), default=RiskLevel.LOW)
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    payments = relationship("Payment", back_populates="user")
    wallet_sessions = relationship("WalletSession", back_populates="user")
    sla_certificates = relationship("SLACertificateRecord", back_populates="user")
    compliance_checks = relationship("ComplianceCheck", back_populates="user")

class WalletSession(Base):
    """钱包会话记录"""
    __tablename__ = 'wallet_sessions'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    wallet_address = Column(String(42), nullable=False)
    wallet_provider = Column(String(50), nullable=False)
    session_token = Column(String(128), nullable=False, unique=True)
    
    # 签名验证
    signature = Column(Text, nullable=False)
    message = Column(Text, nullable=False)
    nonce = Column(String(64), nullable=False)
    
    # 会话状态
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime, nullable=False)
    
    # IP和用户代理
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow)
    
    # 关系
    user = relationship("User", back_populates="wallet_sessions")

class Payment(Base):
    """支付记录"""
    __tablename__ = 'payments'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    
    # 支付基本信息
    payment_id = Column(String(64), unique=True, nullable=False)
    amount_usd = Column(Float, nullable=False)
    method_type = Column(SQLEnum(PaymentMethodType), nullable=False)
    status = Column(SQLEnum(PaymentStatus), default=PaymentStatus.PENDING)
    
    # 加密货币支付字段
    crypto_currency = Column(SQLEnum(CryptoCurrency), nullable=True)
    crypto_amount = Column(Float, nullable=True)
    payment_address = Column(String(128), nullable=True)
    transaction_hash = Column(String(128), nullable=True)
    confirmations = Column(Integer, default=0)
    required_confirmations = Column(Integer, default=1)
    
    # 区块链信息
    block_number = Column(Integer, nullable=True)
    gas_price = Column(String(32), nullable=True)
    gas_used = Column(Integer, nullable=True)
    
    # Stripe支付字段
    stripe_payment_intent_id = Column(String(128), nullable=True)
    stripe_client_secret = Column(String(128), nullable=True)
    
    # 支付元数据
    description = Column(Text, nullable=True)
    payment_metadata = Column(JSON, nullable=True)
    failure_reason = Column(Text, nullable=True)
    
    # 合规检查
    compliance_check_id = Column(String(64), nullable=True)
    compliance_status = Column(SQLEnum(ComplianceStatus), nullable=True)
    
    # 超时和过期
    expires_at = Column(DateTime, nullable=True)
    confirmed_at = Column(DateTime, nullable=True)
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    user = relationship("User", back_populates="payments")

class BlockchainRecord(Base):
    """区块链验证记录"""
    __tablename__ = 'blockchain_records'
    
    id = Column(Integer, primary_key=True)
    
    # 数据标识
    data_hash = Column(String(66), unique=True, nullable=False)  # Keccak256 hash
    site_id = Column(String(64), nullable=False)
    
    # 区块链信息
    transaction_hash = Column(String(66), nullable=True)
    block_number = Column(Integer, nullable=True)
    contract_address = Column(String(42), nullable=True)
    registrar_address = Column(String(42), nullable=True)
    
    # IPFS信息
    ipfs_cid = Column(String(128), nullable=True)
    encrypted_data = Column(Boolean, default=False)
    
    # 验证状态
    status = Column(SQLEnum(BlockchainVerificationStatus), default=BlockchainVerificationStatus.PENDING)
    verification_count = Column(Integer, default=0)
    
    # 元数据
    data_type = Column(String(64), nullable=True)
    data_size = Column(Integer, nullable=True)
    record_metadata = Column(JSON, nullable=True)
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    registered_at = Column(DateTime, nullable=True)
    verified_at = Column(DateTime, nullable=True)

class SLACertificateRecord(Base):
    """SLA证书NFT记录"""
    __tablename__ = 'sla_certificates'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    
    # NFT信息
    token_id = Column(Integer, nullable=True)
    contract_address = Column(String(42), nullable=True)
    token_uri = Column(Text, nullable=True)
    ipfs_cid = Column(String(128), nullable=True)
    
    # SLA信息
    month_year = Column(Integer, nullable=False)  # YYYYMM格式
    sla_score = Column(Float, nullable=False)
    uptime_percentage = Column(Float, nullable=True)
    response_time_avg = Column(Float, nullable=True)
    accuracy_percentage = Column(Float, nullable=True)
    transparency_score = Column(Float, nullable=True)
    
    # 证书状态
    status = Column(SQLEnum(SLAStatus), nullable=False)
    mint_status = Column(SQLEnum(NFTMintStatus), default=NFTMintStatus.PENDING)
    
    # 验证信息
    is_verified = Column(Boolean, default=False)
    verifier_address = Column(String(42), nullable=True)
    verification_note = Column(Text, nullable=True)
    verified_at = Column(DateTime, nullable=True)
    
    # 铸造信息
    mint_transaction_hash = Column(String(66), nullable=True)
    mint_block_number = Column(Integer, nullable=True)
    mint_gas_used = Column(Integer, nullable=True)
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    minted_at = Column(DateTime, nullable=True)
    
    # 关系
    user = relationship("User", back_populates="sla_certificates")

class ComplianceCheck(Base):
    """合规检查记录"""
    __tablename__ = 'compliance_checks'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    
    # 检查基本信息
    check_id = Column(String(64), unique=True, nullable=False)
    check_type = Column(String(32), nullable=False)  # payment, kyc, aml等
    status = Column(SQLEnum(ComplianceStatus), nullable=False)
    
    # 风险评估
    risk_level = Column(SQLEnum(RiskLevel), nullable=False)
    risk_score = Column(Float, nullable=False)
    risk_factors = Column(JSON, nullable=True)
    
    # 检查结果
    approved = Column(Boolean, nullable=False)
    failure_reason = Column(Text, nullable=True)
    
    # 检查详情
    details = Column(JSON, nullable=True)
    external_check_id = Column(String(128), nullable=True)  # 外部AML API的检查ID
    
    # 检查器信息
    checker_type = Column(String(32), nullable=True)  # internal, chainalysis等
    checker_version = Column(String(16), nullable=True)
    
    # 时间戳和过期
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    
    # 关系
    user = relationship("User", back_populates="compliance_checks")

class PaymentMonitorLog(Base):
    """支付监控日志"""
    __tablename__ = 'payment_monitor_logs'
    
    id = Column(Integer, primary_key=True)
    payment_id = Column(String(64), nullable=False)
    
    # 监控信息
    check_type = Column(String(32), nullable=False)  # confirmation, timeout等
    old_status = Column(String(32), nullable=True)
    new_status = Column(String(32), nullable=True)
    
    # 区块链数据
    block_number = Column(Integer, nullable=True)
    confirmations = Column(Integer, nullable=True)
    transaction_found = Column(Boolean, nullable=True)
    
    # 监控结果
    success = Column(Boolean, nullable=False)
    error_message = Column(Text, nullable=True)
    response_data = Column(JSON, nullable=True)
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)

class NFTMintingQueue(Base):
    """NFT铸造队列"""
    __tablename__ = 'nft_minting_queue'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    certificate_id = Column(Integer, ForeignKey('sla_certificates.id'), nullable=False)
    
    # 铸造任务信息
    task_id = Column(String(64), unique=True, nullable=False)
    priority = Column(Integer, default=0)  # 优先级，数字越大优先级越高
    
    # 铸造参数
    contract_address = Column(String(42), nullable=False)
    recipient_address = Column(String(42), nullable=False)
    token_uri = Column(Text, nullable=False)
    mint_metadata = Column(JSON, nullable=True)
    
    # 状态和结果
    status = Column(SQLEnum(NFTMintStatus), default=NFTMintStatus.PENDING)
    transaction_hash = Column(String(66), nullable=True)
    token_id = Column(Integer, nullable=True)
    gas_used = Column(Integer, nullable=True)
    
    # 重试机制
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    last_error = Column(Text, nullable=True)
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    next_retry_at = Column(DateTime, nullable=True)

class SchedulerLock(Base):
    """调度器领导者锁模型"""
    __tablename__ = 'scheduler_leader_lock'
    
    lock_key = Column(String(255), primary_key=True, nullable=False)
    process_id = Column(Integer, nullable=False)
    hostname = Column(String(255), nullable=False)
    acquired_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    last_heartbeat = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # 附加验证字段
    worker_info = Column(Text, nullable=True)  # 存储worker详细信息(JSON)
    lock_version = Column(Integer, nullable=False, default=1)  # 乐观锁版本
    
    def __init__(self, lock_key, process_id, hostname, expires_at, **kwargs):
        self.lock_key = lock_key
        self.process_id = process_id
        self.hostname = hostname
        self.expires_at = expires_at
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    def is_expired(self):
        """检查锁是否已过期"""
        return datetime.utcnow() > self.expires_at
    
    def update_heartbeat(self):
        """更新心跳时间"""
        self.last_heartbeat = datetime.utcnow()

# 导出所有模型
__all__ = [
    'Base', 'User', 'WalletSession', 'Payment', 'BlockchainRecord', 
    'SLACertificateRecord', 'ComplianceCheck', 'PaymentMonitorLog', 
    'NFTMintingQueue', 'SchedulerLock',
    'BlockchainVerificationStatus', 'PaymentStatus', 'PaymentMethodType', 
    'CryptoCurrency', 'SLAStatus', 'NFTMintStatus', 'ComplianceStatus', 
    'RiskLevel'
]