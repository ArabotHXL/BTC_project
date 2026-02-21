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

class SLAStatus(enum.Enum):
    """SLA状态"""
    EXCELLENT = "优秀"    # 95%+
    GOOD = "良好"         # 90-95%
    ACCEPTABLE = "合格"   # 85-90%
    POOR = "不足"        # 80-85%
    FAILED = "失败"      # <80%

class NFTMintStatus(enum.Enum):
    """NFT铸造状态"""
    PENDING = "待铸造"
    MINTING = "铸造中"
    MINTED = "已铸造"
    FAILED = "铸造失败"
    VERIFIED = "已验证"

class StrategyType(enum.Enum):
    """限电策略类型"""
    PERFORMANCE_PRIORITY = "performance_priority"  # 性能优先
    CUSTOMER_PRIORITY = "customer_priority"  # 客户优先
    FAIR_DISTRIBUTION = "fair_distribution"  # 公平分配
    CUSTOM = "custom"  # 自定义

class ExecutionMode(enum.Enum):
    """执行模式"""
    AUTO = "auto"  # 自动执行
    SEMI_AUTO = "semi_auto"  # 半自动执行
    MANUAL = "manual"  # 手动执行

class PlanStatus(enum.Enum):
    """限电计划状态"""
    PENDING = "pending"  # 待审批
    APPROVED = "approved"  # 已批准
    EXECUTING = "executing"  # 执行中
    RECOVERY_PENDING = "recovery_pending"  # 恢复待处理
    COMPLETED = "completed"  # 已完成
    CANCELLED = "cancelled"  # 已取消

class ExecutionAction(enum.Enum):
    """执行动作"""
    SHUTDOWN = "shutdown"  # 关机
    STARTUP = "startup"  # 开机

class ExecutionStatus(enum.Enum):
    """执行状态"""
    SUCCESS = "SUCCESS"  # 成功
    FAILED = "FAILED"  # 失败

class NotificationType(enum.Enum):
    """通知类型"""
    ADVANCE_24H = "advance_24h"  # 提前24小时通知
    EXECUTION_START = "execution_start"  # 执行开始通知
    WEEKLY_REPORT = "weekly_report"  # 周报

class DeliveryStatus(enum.Enum):
    """发送状态"""
    PENDING = "pending"  # 待发送
    SENT = "sent"  # 已发送
    FAILED = "failed"  # 发送失败

class PriceMode(enum.Enum):
    """电价模式"""
    FIXED = "fixed"  # 固定电价
    PEAK_VALLEY = "peak_valley"  # 峰谷电价
    HOURLY_24 = "hourly_24"  # 24小时电价
    API_REALTIME = "api_realtime"  # API实时电价
    MONTHLY_CONTRACT = "monthly_contract"  # 月度合约电价

class AutomationRuleTriggerType(enum.Enum):
    """自动化规则触发类型"""
    TEMPERATURE_HIGH = "temperature_high"  # 温度过高
    TEMPERATURE_LOW = "temperature_low"    # 温度过低
    HASHRATE_LOW = "hashrate_low"          # 算力过低
    OFFLINE_DURATION = "offline_duration"  # 离线时长
    POWER_HIGH = "power_high"              # 功耗过高

class AutomationRuleActionType(enum.Enum):
    """自动化规则动作类型"""
    POWER_MODE_LOW = "power_mode_low"      # 切换低功耗模式
    POWER_MODE_NORMAL = "power_mode_normal" # 恢复正常模式
    REBOOT = "reboot"                      # 重启
    SEND_ALERT = "send_alert"              # 发送告警
    DISABLE = "disable"                    # 禁用矿机

class SchedulerLock(db.Model):
    """
    🔧 CRITICAL FIX: 调度器领导者锁模型
    Scheduler Leader Lock Model for Single Instance Enforcement
    
    确保在Gunicorn多worker环境下只有一个调度器实例运行
    Ensures only one scheduler instance runs in multi-worker Gunicorn environment
    """
    __tablename__ = 'scheduler_leader_lock'
    
    lock_key = db.Column(db.String(255), primary_key=True, nullable=False)
    process_id = db.Column(db.Integer, nullable=False)
    hostname = db.Column(db.String(255), nullable=False)
    acquired_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    last_heartbeat = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # 附加验证字段
    worker_info = db.Column(db.Text, nullable=True)  # 存储worker详细信息(JSON)
    lock_version = db.Column(db.Integer, nullable=False, default=1)  # 乐观锁版本
    
    def __init__(self, lock_key, process_id, hostname, expires_at, **kwargs):
        self.lock_key = lock_key
        self.process_id = process_id
        self.hostname = hostname
        self.expires_at = expires_at
        self.worker_info = kwargs.get('worker_info')
        
    def __repr__(self):
        return f"<SchedulerLock {self.lock_key}: PID={self.process_id}@{self.hostname}>"
        
    def is_expired(self) -> bool:
        """检查锁是否已过期"""
        return datetime.utcnow() > self.expires_at
        
    def refresh_lock(self, timeout_seconds: int = 300):
        """刷新锁的过期时间和心跳"""
        self.expires_at = datetime.utcnow() + timedelta(seconds=timeout_seconds)
        self.last_heartbeat = datetime.utcnow()
        self.lock_version += 1  # 增加版本号用于乐观锁
        
    def to_dict(self) -> dict:
        """转换为字典格式用于日志记录"""
        return {
            'lock_key': self.lock_key,
            'process_id': self.process_id,
            'hostname': self.hostname,
            'acquired_at': self.acquired_at.isoformat() if self.acquired_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'last_heartbeat': self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            'is_expired': self.is_expired(),
            'lock_version': self.lock_version
        }
        
    @classmethod
    def cleanup_expired_locks(cls):
        """清理所有过期的锁"""
        current_time = datetime.utcnow()
        expired_locks = cls.query.filter(cls.expires_at < current_time).all()  # type: ignore
        
        for lock in expired_locks:
            db.session.delete(lock)
            logging.info(f"🧹 清理过期锁: {lock}")
            
        db.session.commit()
        return len(expired_locks)
        
    @classmethod
    def get_active_lock(cls, lock_key: str):
        """获取指定key的活跃锁"""
        return cls.query.filter_by(lock_key=lock_key).filter(
            cls.expires_at > datetime.utcnow()  # type: ignore
        ).first()
        
    @classmethod
    def acquire_lock(cls, lock_key: str, process_id: int, hostname: str, 
                    timeout_seconds: int = 300, worker_info: str | None = None) -> bool:
        """
        🔧 CRITICAL FIX: 原子性锁获取机制
        Atomic lock acquisition mechanism
        """
        try:
            # 清理过期锁
            cls.cleanup_expired_locks()
            
            # 检查是否已有活跃锁
            existing_lock = cls.get_active_lock(lock_key)
            if existing_lock:
                if existing_lock.process_id == process_id:
                    # 同一进程刷新锁
                    existing_lock.refresh_lock(timeout_seconds)
                    db.session.commit()
                    logging.info(f"🔄 刷新现有锁: {existing_lock}")
                    return True
                else:
                    logging.info(f"⏳ 锁被其他进程持有: {existing_lock}")
                    return False
            
            # 创建新锁
            expires_at = datetime.utcnow() + timedelta(seconds=timeout_seconds)
            new_lock = cls(
                lock_key=lock_key,
                process_id=process_id,
                hostname=hostname,
                expires_at=expires_at,
                worker_info=worker_info
            )
            
            db.session.add(new_lock)
            db.session.commit()
            
            logging.info(f"🔒 获取新锁: {new_lock}")
            return True
            
        except Exception as e:
            db.session.rollback()
            logging.error(f"获取锁失败: {e}")
            return False
            
    @classmethod
    def release_lock(cls, lock_key: str, process_id: int) -> bool:
        """释放指定进程的锁"""
        try:
            lock = cls.query.filter_by(
                lock_key=lock_key, 
                process_id=process_id
            ).first()
            
            if lock:
                db.session.delete(lock)
                db.session.commit()
                logging.info(f"🔓 释放锁: {lock}")
                return True
            else:
                logging.warning(f"⚠️ 未找到要释放的锁: key={lock_key}, pid={process_id}")
                return False
                
        except Exception as e:
            db.session.rollback()
            logging.error(f"释放锁失败: {e}")
            return False

# ============================================================================
# SLA证明NFT系统数据模型
# SLA Proof NFT System Data Models
# ============================================================================

class SLAMetrics(db.Model):
    """
    SLA指标数据表
    存储系统运行指标和性能数据，用于生成月度SLA证书
    """
    __tablename__ = 'sla_metrics'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # 时间信息
    recorded_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    month_year = db.Column(db.Integer, nullable=False, index=True)  # YYYYMM格式，如202509
    
    # 系统可用性指标 (百分比，精确到小数点后2位)
    uptime_percentage = db.Column(db.Numeric(5,2), nullable=False)  # 运行时间百分比
    availability_percentage = db.Column(db.Numeric(5,2), nullable=False)  # 服务可用性
    
    # 响应性能指标
    avg_response_time_ms = db.Column(db.Integer, nullable=False)  # 平均响应时间(毫秒)
    max_response_time_ms = db.Column(db.Integer, nullable=False)  # 最大响应时间
    min_response_time_ms = db.Column(db.Integer, nullable=False)  # 最小响应时间
    
    # 数据准确性指标
    data_accuracy_percentage = db.Column(db.Numeric(5,2), nullable=False)  # 数据准确性
    api_success_rate = db.Column(db.Numeric(5,2), nullable=False)  # API调用成功率
    
    # 透明度指标
    blockchain_verifications = db.Column(db.Integer, default=0)  # 区块链验证次数
    ipfs_uploads = db.Column(db.Integer, default=0)  # IPFS上传次数
    transparency_score = db.Column(db.Numeric(5,2), nullable=False)  # 透明度评分
    
    # 系统错误指标
    error_count = db.Column(db.Integer, default=0)  # 错误总数
    critical_error_count = db.Column(db.Integer, default=0)  # 严重错误数
    downtime_minutes = db.Column(db.Integer, default=0)  # 停机时间(分钟)
    
    # 用户体验指标
    user_satisfaction_score = db.Column(db.Numeric(3,2), nullable=True)  # 用户满意度(1-5分)
    feature_completion_rate = db.Column(db.Numeric(5,2), nullable=False)  # 功能完成率
    
    # 综合评分
    composite_sla_score = db.Column(db.Numeric(6,2), nullable=False)  # 综合SLA评分(0-100)
    sla_status = db.Column(db.Enum(SLAStatus), nullable=False)  # SLA状态等级
    
    # 元数据
    data_source = db.Column(db.String(50), default='system_monitor')  # 数据源
    verified_by_blockchain = db.Column(db.Boolean, default=False)  # 是否已区块链验证
    ipfs_hash = db.Column(db.String(100), nullable=True)  # IPFS哈希
    
    # 索引优化
    __table_args__ = (
        db.Index('idx_sla_metrics_month', 'month_year'),
        db.Index('idx_sla_metrics_score', 'composite_sla_score'),
        db.Index('idx_sla_metrics_time', 'recorded_at'),
    )
    
    def __init__(self, month_year, uptime_percentage, availability_percentage, 
                 avg_response_time_ms, data_accuracy_percentage, api_success_rate,
                 transparency_score, **kwargs):
        self.month_year = month_year
        self.uptime_percentage = uptime_percentage
        self.availability_percentage = availability_percentage
        self.avg_response_time_ms = avg_response_time_ms
        self.data_accuracy_percentage = data_accuracy_percentage
        self.api_success_rate = api_success_rate
        self.transparency_score = transparency_score
        
        # 处理其他可选参数
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        
        # 自动计算综合评分和状态
        self._calculate_composite_score()
    
    def _calculate_composite_score(self):
        """计算综合SLA评分"""
        # 权重分配 (总和100%)
        weights = {
            'uptime': 0.25,        # 运行时间权重25%
            'availability': 0.20,   # 可用性权重20%
            'response': 0.15,       # 响应时间权重15%
            'accuracy': 0.20,       # 数据准确性权重20%
            'api_success': 0.10,    # API成功率权重10%
            'transparency': 0.10    # 透明度权重10%
        }
        
        # 响应时间评分转换 (越低越好，超过1000ms开始扣分)
        response_score = max(0, 100 - (self.avg_response_time_ms - 200) / 10)
        response_score = min(100, response_score)
        
        # 综合评分计算
        composite = (
            float(self.uptime_percentage) * weights['uptime'] +
            float(self.availability_percentage) * weights['availability'] +
            response_score * weights['response'] +
            float(self.data_accuracy_percentage) * weights['accuracy'] +
            float(self.api_success_rate) * weights['api_success'] +
            float(self.transparency_score) * weights['transparency']
        )
        
        self.composite_sla_score = round(composite, 2)
        
        # 根据评分确定SLA状态
        if composite >= 95:
            self.sla_status = SLAStatus.EXCELLENT
        elif composite >= 90:
            self.sla_status = SLAStatus.GOOD
        elif composite >= 85:
            self.sla_status = SLAStatus.ACCEPTABLE
        elif composite >= 80:
            self.sla_status = SLAStatus.POOR
        else:
            self.sla_status = SLAStatus.FAILED
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'recorded_at': self.recorded_at.isoformat() if self.recorded_at else None,
            'month_year': self.month_year,
            'uptime_percentage': float(self.uptime_percentage),
            'availability_percentage': float(self.availability_percentage),
            'avg_response_time_ms': self.avg_response_time_ms,
            'data_accuracy_percentage': float(self.data_accuracy_percentage),
            'api_success_rate': float(self.api_success_rate),
            'transparency_score': float(self.transparency_score),
            'composite_sla_score': float(self.composite_sla_score),
            'sla_status': self.sla_status.value,
            'verified_by_blockchain': self.verified_by_blockchain,
            'ipfs_hash': self.ipfs_hash
        }
    
    def __repr__(self):
        return f"<SLAMetrics {self.month_year}: {self.composite_sla_score}% ({self.sla_status.value})>"

class SLACertificateRecord(db.Model):
    """
    SLA证书记录表
    存储已铸造的NFT证书信息和链上数据
    """
    __tablename__ = 'sla_certificate_records'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # 证书基本信息
    month_year = db.Column(db.Integer, nullable=False, index=True)  # YYYYMM格式
    recipient_address = db.Column(db.String(42), nullable=False, index=True)  # 以太坊地址
    
    # NFT相关信息
    token_id = db.Column(db.String(20), nullable=True, unique=True)  # NFT Token ID
    contract_address = db.Column(db.String(42), nullable=True)  # 合约地址
    transaction_hash = db.Column(db.String(66), nullable=True, unique=True)  # 交易哈希
    block_number = db.Column(db.BigInteger, nullable=True)  # 区块号
    
    # 铸造状态和时间
    mint_status = db.Column(db.Enum(NFTMintStatus), default=NFTMintStatus.PENDING)
    requested_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    minted_at = db.Column(db.DateTime, nullable=True)
    
    # SLA数据关联
    sla_metrics_id = db.Column(db.Integer, db.ForeignKey('sla_metrics.id'), nullable=True)
    sla_metrics = db.relationship('SLAMetrics', backref='certificates')
    
    # NFT元数据
    metadata_ipfs_hash = db.Column(db.String(100), nullable=True)  # 元数据IPFS哈希
    image_ipfs_hash = db.Column(db.String(100), nullable=True)  # SVG图像IPFS哈希
    report_ipfs_hash = db.Column(db.String(100), nullable=True)  # 详细报告IPFS哈希
    
    # 验证信息
    is_verified = db.Column(db.Boolean, default=False)  # 是否已验证
    verified_by = db.Column(db.String(42), nullable=True)  # 验证者地址
    verified_at = db.Column(db.DateTime, nullable=True)  # 验证时间
    verification_note = db.Column(db.Text, nullable=True)  # 验证备注
    
    # 错误信息
    error_message = db.Column(db.Text, nullable=True)  # 错误消息
    retry_count = db.Column(db.Integer, default=0)  # 重试次数
    
    # 索引优化
    __table_args__ = (
        db.Index('idx_certificate_month', 'month_year'),
        db.Index('idx_certificate_recipient', 'recipient_address'),
        db.Index('idx_certificate_status', 'mint_status'),
    )
    
    def __init__(self, month_year, recipient_address, **kwargs):
        self.month_year = month_year
        self.recipient_address = recipient_address
        
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def update_mint_status(self, status: NFTMintStatus, **kwargs):
        """更新铸造状态"""
        self.mint_status = status
        
        if status == NFTMintStatus.MINTED:
            self.minted_at = datetime.utcnow()
        
        # 更新其他相关字段
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'month_year': self.month_year,
            'recipient_address': self.recipient_address,
            'token_id': self.token_id,
            'contract_address': self.contract_address,
            'transaction_hash': self.transaction_hash,
            'mint_status': self.mint_status.value,
            'requested_at': self.requested_at.isoformat() if self.requested_at else None,
            'minted_at': self.minted_at.isoformat() if self.minted_at else None,
            'metadata_ipfs_hash': self.metadata_ipfs_hash,
            'is_verified': self.is_verified,
            'verified_by': self.verified_by,
            'verified_at': self.verified_at.isoformat() if self.verified_at else None
        }
    
    def __repr__(self):
        return f"<SLACertificate {self.month_year} for {self.recipient_address[:8]}...: {self.mint_status.value}>"

class SystemPerformanceLog(db.Model):
    """
    系统性能日志表
    实时记录系统性能数据，用于SLA指标计算
    """
    __tablename__ = 'system_performance_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # 时间戳
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    # 系统资源使用
    cpu_usage_percent = db.Column(db.Numeric(5,2), nullable=False)  # CPU使用率
    memory_usage_percent = db.Column(db.Numeric(5,2), nullable=False)  # 内存使用率
    disk_usage_percent = db.Column(db.Numeric(5,2), nullable=False)  # 磁盘使用率
    
    # 网络指标
    network_latency_ms = db.Column(db.Integer, nullable=False)  # 网络延迟
    bandwidth_utilization = db.Column(db.Numeric(5,2), nullable=False)  # 带宽利用率
    
    # 应用性能
    active_connections = db.Column(db.Integer, default=0)  # 活跃连接数
    requests_per_second = db.Column(db.Numeric(8,2), default=0)  # 每秒请求数
    error_rate = db.Column(db.Numeric(5,2), default=0)  # 错误率
    
    # 数据库性能
    db_connection_count = db.Column(db.Integer, default=0)  # 数据库连接数
    db_query_avg_time_ms = db.Column(db.Integer, default=0)  # 数据库查询平均时间
    
    # API服务状态
    api_endpoints_healthy = db.Column(db.Integer, default=0)  # 健康API端点数
    api_endpoints_unhealthy = db.Column(db.Integer, default=0)  # 不健康API端点数
    
    # 外部服务状态
    external_api_status = db.Column(db.Text, nullable=True)  # 外部API状态(JSON)
    blockchain_sync_status = db.Column(db.Boolean, default=True)  # 区块链同步状态
    ipfs_service_status = db.Column(db.Boolean, default=True)  # IPFS服务状态
    
    # 索引优化
    __table_args__ = (
        db.Index('idx_performance_timestamp', 'timestamp'),
    )
    
    def __init__(self, cpu_usage_percent, memory_usage_percent, disk_usage_percent,
                 network_latency_ms, bandwidth_utilization, **kwargs):
        self.cpu_usage_percent = cpu_usage_percent
        self.memory_usage_percent = memory_usage_percent
        self.disk_usage_percent = disk_usage_percent
        self.network_latency_ms = network_latency_ms
        self.bandwidth_utilization = bandwidth_utilization
        
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'cpu_usage_percent': float(self.cpu_usage_percent),
            'memory_usage_percent': float(self.memory_usage_percent),
            'disk_usage_percent': float(self.disk_usage_percent),
            'network_latency_ms': self.network_latency_ms,
            'bandwidth_utilization': float(self.bandwidth_utilization),
            'active_connections': self.active_connections,
            'requests_per_second': float(self.requests_per_second),
            'error_rate': float(self.error_rate)
        }
    
    def __repr__(self):
        return f"<PerformanceLog {self.timestamp}: CPU={self.cpu_usage_percent}% MEM={self.memory_usage_percent}%>"

class MonthlyReport(db.Model):
    """
    月度报告表
    存储月度SLA综合报告和分析数据
    """
    __tablename__ = 'monthly_reports'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # 报告基本信息
    month_year = db.Column(db.Integer, nullable=False, unique=True, index=True)  # YYYYMM
    generated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # 综合统计
    total_certificates_issued = db.Column(db.Integer, default=0)  # 发出证书数
    average_sla_score = db.Column(db.Numeric(6,2), nullable=False)  # 平均SLA分数
    highest_sla_score = db.Column(db.Numeric(6,2), nullable=False)  # 最高SLA分数
    lowest_sla_score = db.Column(db.Numeric(6,2), nullable=False)  # 最低SLA分数
    
    # 性能统计
    total_uptime_hours = db.Column(db.Integer, nullable=False)  # 总运行时间
    total_downtime_minutes = db.Column(db.Integer, default=0)  # 总停机时间
    average_response_time_ms = db.Column(db.Integer, nullable=False)  # 平均响应时间
    
    # 错误统计
    total_errors = db.Column(db.Integer, default=0)  # 总错误数
    critical_errors = db.Column(db.Integer, default=0)  # 严重错误数
    resolved_errors = db.Column(db.Integer, default=0)  # 已解决错误数
    
    # 透明度统计
    blockchain_verifications = db.Column(db.Integer, default=0)  # 区块链验证数
    ipfs_uploads = db.Column(db.Integer, default=0)  # IPFS上传数
    transparency_audit_score = db.Column(db.Numeric(5,2), nullable=False)  # 透明度审计分数
    
    # 报告文件存储
    report_ipfs_hash = db.Column(db.String(100), nullable=True)  # 完整报告IPFS哈希
    summary_ipfs_hash = db.Column(db.String(100), nullable=True)  # 报告摘要IPFS哈希
    charts_ipfs_hash = db.Column(db.String(100), nullable=True)  # 图表数据IPFS哈希
    
    # 区块链记录
    blockchain_recorded = db.Column(db.Boolean, default=False)  # 是否已记录到区块链
    blockchain_tx_hash = db.Column(db.String(66), nullable=True)  # 区块链交易哈希
    
    # 审计和验证
    audited_by = db.Column(db.String(42), nullable=True)  # 审计者地址
    audit_timestamp = db.Column(db.DateTime, nullable=True)  # 审计时间
    audit_result = db.Column(db.Boolean, nullable=True)  # 审计结果
    audit_notes = db.Column(db.Text, nullable=True)  # 审计备注
    
    def __init__(self, month_year, average_sla_score, highest_sla_score, lowest_sla_score,
                 total_uptime_hours, average_response_time_ms, transparency_audit_score, **kwargs):
        self.month_year = month_year
        self.average_sla_score = average_sla_score
        self.highest_sla_score = highest_sla_score
        self.lowest_sla_score = lowest_sla_score
        self.total_uptime_hours = total_uptime_hours
        self.average_response_time_ms = average_response_time_ms
        self.transparency_audit_score = transparency_audit_score
        
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'month_year': self.month_year,
            'generated_at': self.generated_at.isoformat() if self.generated_at else None,
            'total_certificates_issued': self.total_certificates_issued,
            'average_sla_score': float(self.average_sla_score),
            'highest_sla_score': float(self.highest_sla_score),
            'lowest_sla_score': float(self.lowest_sla_score),
            'total_uptime_hours': self.total_uptime_hours,
            'average_response_time_ms': self.average_response_time_ms,
            'transparency_audit_score': float(self.transparency_audit_score),
            'blockchain_recorded': self.blockchain_recorded,
            'audited_by': self.audited_by,
            'audit_result': self.audit_result
        }
    
    def __repr__(self):
        return f"<MonthlyReport {self.month_year}: Avg={self.average_sla_score}% Certs={self.total_certificates_issued}>"

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
        return cls.query.filter_by(is_active=True).order_by(cls.manufacturer, cls.model_name).all()  # type: ignore

    @classmethod
    def get_by_name(cls, model_name):
        """根据型号名称获取矿机"""
        return cls.query.filter_by(model_name=model_name, is_active=True).first()

    @classmethod
    def get_by_manufacturer(cls, manufacturer):
        """根据制造商获取矿机列表"""
        return cls.query.filter_by(manufacturer=manufacturer, is_active=True).order_by(cls.model_name).all()  # type: ignore

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
    access_days = db.Column(db.Integer, default=0, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=True)
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
    
    # 多租户：用户所属站点（客户只能访问自己站点的数据）
    managed_by_site_id = db.Column(db.Integer, db.ForeignKey('hosting_sites.id'), nullable=True, index=True)
    managed_site = db.relationship('HostingSite', foreign_keys=[managed_by_site_id], backref='site_users')
    
    # 账户状态
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    def __init__(self, name, email, access_days=0, company=None, position=None, notes=None, role="guest", 
                 username=None, password_hash=None, subscription_plan="free", wallet_address=None):
        self.name = name
        self.email = email
        self.username = username
        self.password_hash = password_hash
        self.company = company
        self.position = position
        self.access_days = access_days
        self.expires_at = None
        self.notes = notes
        self.role = role
        self.subscription_plan = subscription_plan
        self.wallet_address = wallet_address

    @property
    def has_access(self):
        """检查用户是否有访问权限"""
        if not self.is_active:
            return False
        if self.expires_at is None:
            return True
        return datetime.utcnow() <= self.expires_at

    @property
    def access_status(self):
        """获取用户访问状态"""
        if not self.is_active:
            return "已停用"
        if self.has_access:
            return "授权访问"
        else:
            return "访问已过期"

    @property
    def days_remaining(self):
        """获取剩余访问天数"""
        if not self.has_access:
            return 0
        if self.expires_at is None:
            return -1
        delta = self.expires_at - datetime.utcnow()
        return max(0, delta.days)

    def extend_access(self, days):
        """延长访问期限"""
        if self.expires_at is None or self.has_access:
            base = self.expires_at if self.expires_at else datetime.utcnow()
            self.expires_at = base + timedelta(days=days)
        else:
            self.expires_at = datetime.utcnow() + timedelta(days=days)
        self.access_days += days

    def revoke_access(self):
        """撤销访问权限（停用账户）"""
        self.is_active = False

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
        """重新计算到期时间（基于access_days，0表示永久有效）"""
        if self.access_days and self.access_days > 0:
            self.expires_at = self.created_at + timedelta(days=self.access_days)
        else:
            self.expires_at = None

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
    
    # 矿场专属扩展字段
    status = db.Column(db.String(20), default='active', nullable=False)  # active, inactive, pending, new
    electricity_cost = db.Column(db.Float, nullable=True)  # 电费成本 $/kWh
    miners_count = db.Column(db.Integer, default=0, nullable=False)  # 矿机数量
    primary_miner_model = db.Column(db.String(100), nullable=True)  # 主要矿机型号（如：Antminer S19 Pro）

    # 关联到矿场主
    created_by_id = db.Column(db.Integer, db.ForeignKey('user_access.id'), nullable=True)
    created_by = db.relationship('UserAccess', foreign_keys=[created_by_id], backref='managed_customers')
    
    # 关联到托管站点（多租户）
    site_id = db.Column(db.Integer, db.ForeignKey('hosting_sites.id'), nullable=True)
    site = db.relationship('HostingSite', foreign_keys=[site_id], backref='customers')
    
    # 关联到系统登录账号（当客户需要登录时）
    user_account_id = db.Column(db.Integer, db.ForeignKey('user_access.id'), nullable=True)
    user_account = db.relationship('UserAccess', foreign_keys=[user_account_id], backref='crm_customer')

    # 关联关系
    contacts = db.relationship('Contact', backref='customer', lazy=True, cascade="all, delete-orphan")
    leads = db.relationship('Lead', backref='customer', lazy=True, cascade="all, delete-orphan")
    deals = db.relationship('Deal', backref='customer', lazy=True, cascade="all, delete-orphan")

    def __init__(self, name, company=None, email=None, phone=None, address=None, tags=None, 
                 customer_type="企业", mining_capacity=None, notes=None, created_by_id=None,
                 status='active', electricity_cost=None, miners_count=0, primary_miner_model=None):
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
        self.status = status
        self.electricity_cost = electricity_cost
        self.miners_count = miners_count
        self.primary_miner_model = primary_miner_model

    def __repr__(self):
        return f"<Customer {self.name} - {self.company}>"

class User(db.Model):
    """用户模型"""
    __tablename__ = 'users'

    id = db.Column(db.String, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    name = db.Column(db.String(80), nullable=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role_id = db.Column(db.String, nullable=True)
    status = db.Column(db.String(20), nullable=True)

    # 时间戳
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 用户角色
    role = db.Column(db.String(20), default='client')  # guest, client, operator, mining_site_owner, admin, owner

    def __repr__(self):
        return f'<User {self.email}>'

class PasswordResetToken(db.Model):
    """密码重置令牌模型"""
    __tablename__ = 'password_reset_tokens'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=False)
    token = db.Column(db.String(128), unique=True, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False, nullable=False)

    user = db.relationship('User', backref=db.backref('reset_tokens', lazy='dynamic'))

    def __init__(self, user_id, token, expires_at):
        self.user_id = user_id
        self.token = token
        self.expires_at = expires_at

    def is_valid(self):
        """检查令牌是否有效"""
        return not self.used and datetime.utcnow() < self.expires_at

    def __repr__(self):
        return f'<PasswordResetToken {self.token[:8]}... for user {self.user_id}>'

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

class Invoice(db.Model):
    """发票管理"""
    __tablename__ = 'crm_invoices'

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('crm_customers.id'), nullable=False)
    deal_id = db.Column(db.Integer, db.ForeignKey('crm_deals.id'), nullable=True)
    invoice_number = db.Column(db.String(50), unique=True, nullable=False)
    
    # 发票状态
    status = db.Column(db.String(20), default='draft', nullable=False)  # draft, sent, paid, overdue, cancelled
    
    # 金额
    amount = db.Column(db.Float, default=0.0, nullable=False)
    currency = db.Column(db.String(10), default="USD", nullable=False)
    tax_amount = db.Column(db.Float, default=0.0, nullable=False)
    total_amount = db.Column(db.Float, default=0.0, nullable=False)
    
    # 日期
    issue_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    due_date = db.Column(db.DateTime, nullable=True)
    paid_date = db.Column(db.DateTime, nullable=True)
    
    # 备注
    description = db.Column(db.Text, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    
    # 创建信息
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user_access.id'), nullable=True)
    created_by = db.relationship('UserAccess', foreign_keys=[created_by_id], backref='created_invoices')
    
    # 关联
    customer = db.relationship('Customer', backref=db.backref('invoices', lazy=True))
    deal = db.relationship('Deal', backref=db.backref('invoices', lazy=True))

    def __repr__(self):
        return f"<Invoice {self.invoice_number} - ${self.total_amount} - {self.status}>"

class Asset(db.Model):
    """资产管理"""
    __tablename__ = 'crm_assets'

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('crm_customers.id'), nullable=False)
    deal_id = db.Column(db.Integer, db.ForeignKey('crm_deals.id'), nullable=True)
    
    # 资产信息
    asset_type = db.Column(db.String(50), nullable=False)  # miner, hosting_slot, equipment
    asset_name = db.Column(db.String(200), nullable=False)
    serial_number = db.Column(db.String(100), nullable=True)
    model = db.Column(db.String(100), nullable=True)
    
    # 状态
    status = db.Column(db.String(20), default='active', nullable=False)  # active, inactive, maintenance, sold
    
    # 价值
    purchase_value = db.Column(db.Float, default=0.0, nullable=False)
    current_value = db.Column(db.Float, default=0.0, nullable=False)
    currency = db.Column(db.String(10), default="USD", nullable=False)
    
    # 位置和配置
    location = db.Column(db.String(200), nullable=True)
    configuration = db.Column(db.Text, nullable=True)  # JSON格式存储配置信息
    
    # 日期
    purchase_date = db.Column(db.DateTime, nullable=True)
    warranty_expiry = db.Column(db.DateTime, nullable=True)
    
    # 备注
    description = db.Column(db.Text, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    
    # 创建信息
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user_access.id'), nullable=True)
    created_by = db.relationship('UserAccess', foreign_keys=[created_by_id], backref='created_assets')
    
    # 关联
    customer = db.relationship('Customer', backref=db.backref('assets', lazy=True))
    deal = db.relationship('Deal', backref=db.backref('assets', lazy=True))

    def __repr__(self):
        return f"<Asset {self.asset_name} - {self.asset_type} - {self.status}>"

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
    
    # 凭证保护模式 (Mode 1=UI Masking, 2=Server Envelope, 3=Device E2EE)
    ip_mode = db.Column(db.Integer, default=1, nullable=False)
    site_dek_wrapped = db.Column(db.Text, nullable=True)  # Mode 2: 加密的 Site DEK
    
    # 站点描述
    description = db.Column(db.Text, nullable=True)
    
    # 功能开关 (Feature Toggles)
    remote_control_enabled = db.Column(db.Boolean, default=True, nullable=False)
    ai_auto_execute_enabled = db.Column(db.Boolean, default=True, nullable=False)
    
    # 多租户：站点归属的矿场主
    owner_id = db.Column(db.Integer, db.ForeignKey('user_access.id'), nullable=True, index=True)
    owner = db.relationship('UserAccess', foreign_keys=[owner_id], backref='owned_sites')
    
    # HI Integration: Organization linkage
    hi_org_id = db.Column(db.Integer, db.ForeignKey('hi_orgs.id'), nullable=True, index=True)
    
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
            'ip_mode': self.ip_mode,
            'remote_control_enabled': self.remote_control_enabled,
            'ai_auto_execute_enabled': self.ai_auto_execute_enabled,
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
    
    # 托管费用和备注
    hosting_fee = db.Column(db.Float, default=0.0, nullable=True)  # 月度托管费用 ($/月)
    notes = db.Column(db.Text, nullable=True)  # 备注信息
    
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
    
    # CGMiner实时监控数据
    temperature_avg = db.Column(db.Float, nullable=True)  # 平均温度 (°C)
    temperature_max = db.Column(db.Float, nullable=True)  # 最高温度 (°C)
    fan_speeds = db.Column(db.Text, nullable=True)  # 风扇转速JSON数组
    fan_avg = db.Column(db.Integer, nullable=True)  # 平均风扇转速 (RPM)
    reject_rate = db.Column(db.Float, nullable=True)  # 拒绝率 (%)
    hardware_errors = db.Column(db.Integer, default=0)  # 硬件错误数
    last_seen = db.Column(db.DateTime, nullable=True)  # 最后在线时间
    cgminer_online = db.Column(db.Boolean, default=False)  # CGMiner是否在线
    pool_url = db.Column(db.String(255), nullable=True)  # 矿池URL
    pool_worker = db.Column(db.String(255), nullable=True)  # 矿池工作名
    uptime_seconds = db.Column(db.Integer, nullable=True)  # 运行时间（秒）
    hashrate_5s = db.Column(db.Float, nullable=True)  # 5秒算力 (TH/s)
    accepted_shares = db.Column(db.Integer, default=0)  # 接受份额
    rejected_shares = db.Column(db.Integer, default=0)  # 拒绝份额
    
    # E2EE (End-to-End Encryption) 字段
    api_port = db.Column(db.Integer, default=4028, nullable=True)  # CGMiner API端口
    encrypted_credentials = db.Column(db.JSON, nullable=True)  # Plan A: 加密的凭证 {ciphertext, iv, salt, algo, version}
    encrypted_connection_full = db.Column(db.JSON, nullable=True)  # Plan B: 完整加密连接信息
    use_full_e2ee = db.Column(db.Boolean, default=False, nullable=False)  # E2EE模式: False=Plan A, True=Plan B
    encrypted_ip = db.Column(db.Text, nullable=True)  # E2EE加密的IP地址
    encrypted_mac = db.Column(db.Text, nullable=True)  # E2EE加密的MAC地址
    encryption_scope = db.Column(db.String(20), default='none', nullable=False)  # none/miner/owner - 加密范围
    ip_encryption_mode = db.Column(db.Integer, default=1, nullable=False)  # IP隐藏策略: 1=UI脱敏, 2=服务器加密, 3=E2EE
    
    # 统一凭证保护字段 (Credential Blob)
    credential_value = db.Column(db.Text, nullable=True)  # 凭证: 明文JSON / ENC:... / E2EE:...
    credential_mode = db.Column(db.Integer, default=1, nullable=False)  # 凭证保护模式 (1/2/3)
    last_accepted_counter = db.Column(db.Integer, default=0, nullable=False)  # 反回滚计数器
    fingerprint = db.Column(db.String(64), nullable=True)  # 凭证指纹
    
    # Device Envelope Encryption - Capability Levels
    # Level 1: DISCOVERY (只读发现) - No credentials needed
    # Level 2: TELEMETRY (遥测数据) - Read-only telemetry access
    # Level 3: CONTROL (完全控制) - Full control requires E2EE credentials
    capability_level = db.Column(db.Integer, default=1, nullable=False)
    bound_device_id = db.Column(db.Integer, db.ForeignKey('edge_devices.id'), nullable=True)
    
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
        import json as json_lib
        
        # 安全解析fan_speeds JSON，防止格式错误导致崩溃
        fan_speeds_parsed = None
        if self.fan_speeds:
            try:
                fan_speeds_parsed = json_lib.loads(self.fan_speeds)
            except (json_lib.JSONDecodeError, TypeError):
                fan_speeds_parsed = None  # 格式错误时返回None
        
        return {
            'id': self.id,
            'site_id': self.site_id,
            'customer_id': self.customer_id,
            'serial_number': self.serial_number,
            'rack_position': self.rack_position,
            'ip_address': self.ip_address,
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
            'last_maintenance': self.last_maintenance.isoformat() if self.last_maintenance else None,
            # CGMiner实时监控数据
            'temperature_avg': self.temperature_avg,
            'temperature_max': self.temperature_max,
            'fan_speeds': fan_speeds_parsed,
            'fan_avg': self.fan_avg,
            'reject_rate': self.reject_rate,
            'hardware_errors': self.hardware_errors,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None,
            'cgminer_online': self.cgminer_online,
            'pool_url': self.pool_url,
            'pool_worker': self.pool_worker,
            'uptime_seconds': self.uptime_seconds,
            'hashrate_5s': self.hashrate_5s,
            'accepted_shares': self.accepted_shares,
            'rejected_shares': self.rejected_shares,
            # E2EE 模式信息 (不包含加密数据，只返回模式状态)
            'api_port': self.api_port,
            'use_full_e2ee': self.use_full_e2ee,
            'has_encrypted_credentials': self.encrypted_credentials is not None,
            'has_encrypted_connection_full': self.encrypted_connection_full is not None,
            'has_encrypted_ip': self.encrypted_ip is not None,
            'has_encrypted_mac': self.encrypted_mac is not None,
            'mac_address': self.mac_address,
            'encryption_scope': self.encryption_scope,
            'ip_encryption_mode': self.ip_encryption_mode,
            'capability_level': self.capability_level,
            'bound_device_id': self.bound_device_id,
            'miner_model': self.miner_model.model_name if self.miner_model else None,
            'hashrate': self.actual_hashrate,
            'power_consumption': self.actual_power,
            'temperature': self.temperature_avg,
            'fan_speed': self.fan_avg,
            'uptime': self.uptime_seconds,
            'notes': self.notes,
        }

class HostingOwnerEncryption(db.Model):
    """矿场主加密元数据 - 存储矿场主级别的加密密钥信息"""
    __tablename__ = 'hosting_owner_encryption'
    
    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('user_access.id'), nullable=False, unique=True, index=True)
    site_id = db.Column(db.Integer, db.ForeignKey('hosting_sites.id'), nullable=True, index=True)
    
    encrypted_data_key = db.Column(db.Text, nullable=False)
    key_salt = db.Column(db.String(64), nullable=False)
    key_iterations = db.Column(db.Integer, default=100000, nullable=False)
    key_algo = db.Column(db.String(32), default='AES-256-GCM', nullable=False)
    key_version = db.Column(db.Integer, default=1, nullable=False)
    
    encrypted_miners_count = db.Column(db.Integer, default=0, nullable=False)
    status = db.Column(db.String(20), default='active', nullable=False)
    
    last_rotated_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    owner = db.relationship('UserAccess', backref='owner_encryption')
    site = db.relationship('HostingSite', backref='owner_encryption')
    
    def to_dict(self):
        return {
            'id': self.id,
            'owner_id': self.owner_id,
            'site_id': self.site_id,
            'key_algo': self.key_algo,
            'key_version': self.key_version,
            'encrypted_miners_count': self.encrypted_miners_count,
            'status': self.status,
            'last_rotated_at': self.last_rotated_at.isoformat() if self.last_rotated_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
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


class MinerBoardTelemetry(db.Model):
    """矿机板级遥测数据 - 芯片级健康追踪
    
    Board-Level Telemetry for Chip Health Tracking
    存储每个哈希板的详细健康数据
    """
    __tablename__ = 'miner_board_telemetry'
    
    id = db.Column(db.Integer, primary_key=True)
    miner_id = db.Column(db.Integer, db.ForeignKey('hosting_miners.id'), nullable=False, index=True)
    site_id = db.Column(db.Integer, db.ForeignKey('hosting_sites.id'), nullable=False, index=True)
    
    board_index = db.Column(db.Integer, nullable=False)
    
    hashrate_ths = db.Column(db.Float, default=0.0, nullable=False)
    temperature_c = db.Column(db.Float, default=0.0, nullable=False)
    
    chips_total = db.Column(db.Integer, default=0, nullable=False)
    chips_ok = db.Column(db.Integer, default=0, nullable=False)
    chips_failed = db.Column(db.Integer, default=0, nullable=False)
    chip_status = db.Column(db.String(200), nullable=True)
    
    frequency_mhz = db.Column(db.Float, default=0.0, nullable=False)
    voltage_mv = db.Column(db.Float, default=0.0, nullable=False)
    
    health = db.Column(db.String(20), default='offline', nullable=False)
    
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    __table_args__ = (
        db.Index('idx_board_telemetry_miner_time', 'miner_id', 'recorded_at'),
        db.Index('idx_board_telemetry_site_time', 'site_id', 'recorded_at'),
        db.Index('idx_board_telemetry_health', 'health'),
    )
    
    miner = db.relationship('HostingMiner', backref=db.backref('board_telemetry', lazy='dynamic'))
    site = db.relationship('HostingSite', backref=db.backref('board_telemetry', lazy='dynamic'))
    
    def __init__(self, miner_id, site_id, board_index, **kwargs):
        self.miner_id = miner_id
        self.site_id = site_id
        self.board_index = board_index
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def to_dict(self):
        return {
            'id': self.id,
            'miner_id': self.miner_id,
            'site_id': self.site_id,
            'board_index': self.board_index,
            'hashrate_ths': self.hashrate_ths,
            'temperature_c': self.temperature_c,
            'chips_total': self.chips_total,
            'chips_ok': self.chips_ok,
            'chips_failed': self.chips_failed,
            'chip_status': self.chip_status,
            'frequency_mhz': self.frequency_mhz,
            'voltage_mv': self.voltage_mv,
            'health': self.health,
            'recorded_at': self.recorded_at.isoformat() if self.recorded_at else None
        }


class HostingMinerOperationLog(db.Model):
    """矿机操作日志表 - 记录所有重要操作（启动、关闭、状态变更等）"""
    __tablename__ = 'hosting_miner_operation_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    miner_id = db.Column(db.Integer, db.ForeignKey('hosting_miners.id'), nullable=False, index=True)
    
    # 操作信息
    operation_type = db.Column(db.String(50), nullable=False, index=True)  # start/shutdown/restart/status_change/approve/reject/delete/edit
    old_status = db.Column(db.String(20), nullable=True)  # 操作前状态
    new_status = db.Column(db.String(20), nullable=True)  # 操作后状态
    
    # 操作人和备注
    operator_id = db.Column(db.Integer, db.ForeignKey('user_access.id'), nullable=False, index=True)
    notes = db.Column(db.Text, nullable=True)  # 操作备注
    
    # 时间戳
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # 关联关系
    miner = db.relationship('HostingMiner', backref='operation_logs')
    operator = db.relationship('UserAccess', backref='miner_operations')
    
    # 索引优化
    __table_args__ = (
        db.Index('idx_miner_operation_logs_miner', 'miner_id'),
        db.Index('idx_miner_operation_logs_operator', 'operator_id'),
        db.Index('idx_miner_operation_logs_type', 'operation_type'),
        db.Index('idx_miner_operation_logs_created', 'created_at'),
    )
    
    def __init__(self, miner_id, operation_type, operator_id, **kwargs):
        self.miner_id = miner_id
        self.operation_type = operation_type
        self.operator_id = operator_id
        
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def to_dict(self):
        return {
            'id': self.id,
            'miner_id': self.miner_id,
            'operation_type': self.operation_type,
            'old_status': self.old_status,
            'new_status': self.new_status,
            'operator_id': self.operator_id,
            'operator_email': self.operator.email if self.operator else None,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

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
    
    # 矿机快照数据（创建工单时的矿机状态）
    miner_id = db.Column(db.Integer, db.ForeignKey('hosting_miners.id'), nullable=True, index=True)
    miner_snapshot = db.Column(db.JSON, nullable=True)  # 矿机状态快照：序列号、位置、客户、算力、功率、温度、IP等
    
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

# ============================================================================
# 矿机批量导入功能数据模型
# Miner Batch Import Data Models
# ============================================================================

class Miner(db.Model):
    """
    矿机基本信息表
    存储矿机的基本配置和连接信息
    """
    __tablename__ = 'miners'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # 矿机唯一标识
    miner_id = db.Column(db.String(100), unique=True, nullable=False, index=True)
    
    # 多租户隔离
    site_id = db.Column(db.String(50), nullable=False, index=True)
    
    # 矿机基本信息
    model = db.Column(db.String(100), nullable=True)  # 矿机型号
    
    # 网络配置
    ip = db.Column(db.String(45), nullable=False, index=True)  # IP地址 (支持IPv4/IPv6)
    port = db.Column(db.String(10), nullable=True)  # 端口号
    api = db.Column(db.String(50), nullable=True)  # API类型
    
    # 认证信息
    username = db.Column(db.String(100), nullable=True)  # 登录用户名
    password = db.Column(db.String(256), nullable=True)  # 登录密码（加密存储）
    
    # 附加信息
    note = db.Column(db.Text, nullable=True)  # 备注信息
    status = db.Column(db.String(50), default='unknown', nullable=False)  # 状态
    source = db.Column(db.String(20), default='import', nullable=False)  # 来源
    
    # 时间戳
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # 用户关联
    user_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=True, index=True)
    user = db.relationship('User', backref='miners')
    
    # HI Integration fields
    hi_tenant_id = db.Column(db.Integer, db.ForeignKey('hi_tenants.id'), nullable=True, index=True)
    nominal_watts = db.Column(db.Integer, nullable=True)
    
    # 索引优化
    __table_args__ = (
        db.Index('idx_miner_miner_id', 'miner_id'),
        db.Index('idx_miner_site_id', 'site_id'),
        db.Index('idx_miner_ip', 'ip'),
        db.Index('idx_miner_site_ip', 'site_id', 'ip'),
    )
    
    def __init__(self, miner_id, site_id, ip, **kwargs):
        self.miner_id = miner_id
        self.site_id = site_id
        self.ip = ip
        
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def __repr__(self):
        return f"<Miner {self.miner_id} ({self.model}): {self.ip}>"
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'miner_id': self.miner_id,
            'site_id': self.site_id,
            'model': self.model,
            'ip': self.ip,
            'port': self.port,
            'api': self.api,
            'username': self.username,
            'note': self.note,
            'status': self.status,
            'source': self.source,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'user_id': self.user_id
        }

class MinerImportJob(db.Model):
    """
    导入任务记录表
    存储矿机批量导入任务的执行记录和统计信息
    """
    __tablename__ = 'miner_import_jobs'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # 任务唯一标识
    job_id = db.Column(db.String(100), unique=True, nullable=False, index=True)
    
    # 多租户隔离
    site_id = db.Column(db.String(50), nullable=False, index=True)
    
    # 用户关联
    user_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=False, index=True)
    user = db.relationship('User', backref='import_jobs')
    
    # 文件信息
    filename = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(20), nullable=False)  # csv, excel, json
    
    # 去重策略
    dedup_strategy = db.Column(db.String(50), nullable=False)  # prefer_import, prefer_existing, reject_conflict
    
    # 统计信息
    total_rows = db.Column(db.Integer, default=0, nullable=False)  # 总行数
    parsed_rows = db.Column(db.Integer, default=0, nullable=False)  # 成功解析行数
    invalid_rows = db.Column(db.Integer, default=0, nullable=False)  # 无效行数
    inserted = db.Column(db.Integer, default=0, nullable=False)  # 新插入数量
    updated = db.Column(db.Integer, default=0, nullable=False)  # 更新数量
    deduped = db.Column(db.Integer, default=0, nullable=False)  # 去重后总数
    
    # 错误信息
    error_csv_path = db.Column(db.String(500), nullable=True)  # 错误CSV文件路径
    
    # 任务状态
    status = db.Column(db.String(20), default='pending', nullable=False)  # pending, processing, completed, failed
    
    # 时间戳
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    # 索引优化
    __table_args__ = (
        db.Index('idx_import_job_id', 'job_id'),
        db.Index('idx_import_site_id', 'site_id'),
        db.Index('idx_import_user_id', 'user_id'),
    )
    
    def __init__(self, job_id, site_id, user_id, filename, file_type, dedup_strategy, **kwargs):
        self.job_id = job_id
        self.site_id = site_id
        self.user_id = user_id
        self.filename = filename
        self.file_type = file_type
        self.dedup_strategy = dedup_strategy
        
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def __repr__(self):
        return f"<MinerImportJob {self.job_id}: {self.status} ({self.inserted} inserted, {self.updated} updated)>"
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'job_id': self.job_id,
            'site_id': self.site_id,
            'user_id': self.user_id,
            'filename': self.filename,
            'file_type': self.file_type,
            'dedup_strategy': self.dedup_strategy,
            'total_rows': self.total_rows,
            'parsed_rows': self.parsed_rows,
            'invalid_rows': self.invalid_rows,
            'inserted': self.inserted,
            'updated': self.updated,
            'deduped': self.deduped,
            'error_csv_path': self.error_csv_path,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }

# ============================================================================
# 智能层事件驱动架构数据模型
# Intelligence Layer Event-Driven Architecture Data Models
# ============================================================================

class EventStatus(enum.Enum):
    """事件状态枚举"""
    PENDING = "待处理"
    PROCESSING = "处理中"
    COMPLETED = "已完成"
    FAILED = "失败"
    RETRYING = "重试中"

class EventOutbox(db.Model):
    """
    事件发件箱表 - Outbox Pattern
    实现事件驱动架构，确保数据变更与事件发布的原子性
    """
    __tablename__ = 'event_outbox'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # 事件基本信息
    event_type = db.Column(db.String(100), nullable=False, index=True)  # miner.added, miner.updated, miner.deleted
    event_payload = db.Column(db.JSON, nullable=False)  # 事件载荷（JSON格式）
    aggregate_id = db.Column(db.String(100), nullable=False, index=True)  # 聚合根ID（如user_id, miner_id）
    aggregate_type = db.Column(db.String(50), nullable=False)  # 聚合根类型（user, miner, portfolio）
    
    # 事件状态
    status = db.Column(db.Enum(EventStatus), default=EventStatus.PENDING, nullable=False, index=True)
    retry_count = db.Column(db.Integer, default=0, nullable=False)
    max_retries = db.Column(db.Integer, default=3, nullable=False)
    
    # 时间戳
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    processing_started_at = db.Column(db.DateTime, nullable=True)  # 开始处理时间
    processed_at = db.Column(db.DateTime, nullable=True)  # 完成/失败时间
    next_retry_at = db.Column(db.DateTime, nullable=True)
    
    # 错误信息
    error_message = db.Column(db.Text, nullable=True)
    error_stacktrace = db.Column(db.Text, nullable=True)
    
    # 元数据
    correlation_id = db.Column(db.String(100), nullable=True)  # 关联ID（用于追踪）
    causation_id = db.Column(db.String(100), nullable=True)  # 因果ID（触发此事件的原因）
    
    # 索引优化（仅保留复合索引和非列定义的索引）
    __table_args__ = (
        db.Index('idx_outbox_aggregate', 'aggregate_id', 'aggregate_type'),
        db.Index('idx_outbox_pending_retry', 'status', 'next_retry_at'),  # 用于查询待重试事件
    )
    
    def __init__(self, event_type, event_payload, aggregate_id, aggregate_type, **kwargs):
        self.event_type = event_type
        self.event_payload = event_payload
        self.aggregate_id = aggregate_id
        self.aggregate_type = aggregate_type
        
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def mark_processing(self):
        """标记事件为处理中"""
        self.status = EventStatus.PROCESSING
        self.processing_started_at = datetime.utcnow()
    
    def mark_completed(self):
        """标记事件为已完成"""
        self.status = EventStatus.COMPLETED
        self.processed_at = datetime.utcnow()
    
    def mark_failed(self, error_message, error_stacktrace=None):
        """标记事件为失败"""
        self.status = EventStatus.FAILED
        self.error_message = error_message
        self.error_stacktrace = error_stacktrace
        self.retry_count += 1
        
        if self.retry_count < self.max_retries:
            self.status = EventStatus.RETRYING
            # 指数退避：2^retry_count 分钟
            delay_minutes = 2 ** self.retry_count
            self.next_retry_at = datetime.utcnow() + timedelta(minutes=delay_minutes)
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'event_type': self.event_type,
            'event_payload': self.event_payload,
            'aggregate_id': self.aggregate_id,
            'aggregate_type': self.aggregate_type,
            'status': self.status.value,
            'retry_count': self.retry_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'processed_at': self.processed_at.isoformat() if self.processed_at else None,
            'error_message': self.error_message
        }
    
    def __repr__(self):
        return f"<EventOutbox {self.id}: {self.event_type} ({self.status.value})>"

class EventFailure(db.Model):
    """
    事件失败记录表
    记录所有失败的事件及其详细信息，用于分析和排错
    """
    __tablename__ = 'event_failures'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # 关联原始事件
    event_id = db.Column(db.Integer, nullable=False, index=True)
    event_type = db.Column(db.String(100), nullable=False)
    event_payload = db.Column(db.JSON, nullable=False)
    
    # 失败信息
    failure_reason = db.Column(db.Text, nullable=False)
    failure_stacktrace = db.Column(db.Text, nullable=True)
    failure_count = db.Column(db.Integer, default=1, nullable=False)
    
    # 时间戳
    first_failed_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_failed_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # 处理状态
    is_resolved = db.Column(db.Boolean, default=False, nullable=False)
    resolved_at = db.Column(db.DateTime, nullable=True)
    resolved_by = db.Column(db.String(100), nullable=True)
    resolution_note = db.Column(db.Text, nullable=True)
    
    def __init__(self, event_id, event_type, event_payload, failure_reason, **kwargs):
        self.event_id = event_id
        self.event_type = event_type
        self.event_payload = event_payload
        self.failure_reason = failure_reason
        
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def __repr__(self):
        return f"<EventFailure {self.id}: Event {self.event_id} ({self.event_type})>"

class ForecastDaily(db.Model):
    """
    每日预测数据表
    存储智能层生成的BTC价格、难度、收益预测数据
    """
    __tablename__ = 'forecast_daily'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # 用户关联
    user_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=True, index=True)
    
    # 预测日期
    forecast_date = db.Column(db.Date, nullable=False, index=True)
    forecast_horizon = db.Column(db.Integer, default=7, nullable=False)  # 预测天数（7/14/30）
    
    # BTC价格预测
    predicted_btc_price = db.Column(db.Numeric(12, 2), nullable=False)
    price_lower_bound = db.Column(db.Numeric(12, 2), nullable=True)  # 95%置信区间下界
    price_upper_bound = db.Column(db.Numeric(12, 2), nullable=True)  # 95%置信区间上界
    
    # 难度预测
    predicted_difficulty = db.Column(db.Numeric(20, 2), nullable=False)
    difficulty_lower_bound = db.Column(db.Numeric(20, 2), nullable=True)
    difficulty_upper_bound = db.Column(db.Numeric(20, 2), nullable=True)
    
    # 收益预测
    predicted_daily_revenue = db.Column(db.Numeric(12, 2), nullable=True)
    revenue_lower_bound = db.Column(db.Numeric(12, 2), nullable=True)
    revenue_upper_bound = db.Column(db.Numeric(12, 2), nullable=True)
    
    # 模型评估指标
    model_name = db.Column(db.String(50), default='ARIMA', nullable=False)  # ARIMA, XGBoost, Ensemble
    rmse = db.Column(db.Numeric(10, 4), nullable=True)  # 均方根误差
    mae = db.Column(db.Numeric(10, 4), nullable=True)  # 平均绝对误差
    confidence_score = db.Column(db.Numeric(5, 2), nullable=True)  # 置信度分数 (0-100)
    
    # 时间戳
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # 索引优化
    __table_args__ = (
        db.Index('idx_forecast_date', 'forecast_date'),
        db.Index('idx_forecast_user', 'user_id', 'forecast_date'),
        db.UniqueConstraint('user_id', 'forecast_date', 'forecast_horizon', name='uq_forecast_user_date_horizon'),
    )
    
    def __init__(self, forecast_date, predicted_btc_price, predicted_difficulty, **kwargs):
        self.forecast_date = forecast_date
        self.predicted_btc_price = predicted_btc_price
        self.predicted_difficulty = predicted_difficulty
        
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'forecast_date': self.forecast_date.isoformat() if self.forecast_date else None,
            'forecast_horizon': self.forecast_horizon,
            'predicted_btc_price': float(self.predicted_btc_price),
            'price_lower_bound': float(self.price_lower_bound) if self.price_lower_bound else None,
            'price_upper_bound': float(self.price_upper_bound) if self.price_upper_bound else None,
            'predicted_difficulty': float(self.predicted_difficulty),
            'predicted_daily_revenue': float(self.predicted_daily_revenue) if self.predicted_daily_revenue else None,
            'model_name': self.model_name,
            'rmse': float(self.rmse) if self.rmse else None,
            'mae': float(self.mae) if self.mae else None,
            'confidence_score': float(self.confidence_score) if self.confidence_score else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f"<ForecastDaily {self.forecast_date}: BTC ${self.predicted_btc_price}>"

class OpsSchedule(db.Model):
    """
    运营调度表
    存储电力削峰排程和矿机开关机调度计划
    """
    __tablename__ = 'ops_schedule'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # 用户关联
    user_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=False, index=True)
    
    # 调度日期和时段
    schedule_date = db.Column(db.Date, nullable=False, index=True)
    hour_of_day = db.Column(db.Integer, nullable=False)  # 0-23小时
    
    # 电价信息
    electricity_price = db.Column(db.Numeric(10, 4), nullable=False)  # $/kWh
    is_peak_hour = db.Column(db.Boolean, default=False, nullable=False)
    
    # 调度决策
    miners_online = db.Column(db.Integer, default=0, nullable=False)  # 在线矿机数
    miners_offline = db.Column(db.Integer, default=0, nullable=False)  # 离线矿机数
    total_power_consumption_kw = db.Column(db.Numeric(12, 2), nullable=False)  # 总功耗(kW)
    
    # 削峰百分比
    curtailment_percentage = db.Column(db.Numeric(5, 2), default=0, nullable=False)  # 削峰百分比
    power_saved_kw = db.Column(db.Numeric(12, 2), default=0, nullable=False)  # 节省功耗(kW)
    cost_saved_usd = db.Column(db.Numeric(12, 2), default=0, nullable=False)  # 节省成本($)
    
    # 优化算法信息
    algorithm_used = db.Column(db.String(50), default='PuLP', nullable=False)  # PuLP, OR-Tools
    optimization_status = db.Column(db.String(20), default='optimal', nullable=False)  # optimal, feasible, infeasible
    computation_time_ms = db.Column(db.Integer, nullable=True)  # 计算耗时(毫秒)
    
    # 时间戳
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # 索引优化
    __table_args__ = (
        db.Index('idx_schedule_user_date', 'user_id', 'schedule_date'),
        db.Index('idx_schedule_date_hour', 'schedule_date', 'hour_of_day'),
        db.UniqueConstraint('user_id', 'schedule_date', 'hour_of_day', name='uq_schedule_user_date_hour'),
    )
    
    def __init__(self, user_id, schedule_date, hour_of_day, electricity_price, total_power_consumption_kw, **kwargs):
        self.user_id = user_id
        self.schedule_date = schedule_date
        self.hour_of_day = hour_of_day
        self.electricity_price = electricity_price
        self.total_power_consumption_kw = total_power_consumption_kw
        
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'schedule_date': self.schedule_date.isoformat() if self.schedule_date else None,
            'hour_of_day': self.hour_of_day,
            'electricity_price': float(self.electricity_price),
            'is_peak_hour': self.is_peak_hour,
            'miners_online': self.miners_online,
            'miners_offline': self.miners_offline,
            'total_power_consumption_kw': float(self.total_power_consumption_kw),
            'curtailment_percentage': float(self.curtailment_percentage),
            'power_saved_kw': float(self.power_saved_kw),
            'cost_saved_usd': float(self.cost_saved_usd),
            'algorithm_used': self.algorithm_used,
            'optimization_status': self.optimization_status
        }
    
    def __repr__(self):
        return f"<OpsSchedule {self.schedule_date} {self.hour_of_day}:00 - {self.miners_online} online>"


# ============================================================================
# 智能限电管理系统数据模型
# Smart Power Curtailment Management System Data Models
# ============================================================================

class MinerPerformanceScore(db.Model):
    """
    矿机性能评分历史
    Miner Performance Score History
    """
    __tablename__ = 'miner_performance_scores'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # 关联字段
    miner_id = db.Column(db.Integer, db.ForeignKey('hosting_miners.id'), nullable=False, index=True)
    
    # 性能评分 (0-100分)
    performance_score = db.Column(db.Numeric(5, 2), nullable=False)  # 综合性能评分
    
    # 性能指标比例
    hashrate_ratio = db.Column(db.Numeric(5, 4), nullable=False)  # 实际/额定算力比例
    power_efficiency_ratio = db.Column(db.Numeric(5, 4), nullable=False)  # 额定/实际功耗比例
    uptime_ratio = db.Column(db.Numeric(5, 4), nullable=False)  # 在线时长比例
    
    # 运行指标
    temperature_avg = db.Column(db.Numeric(5, 2), nullable=True)  # 平均温度
    error_rate = db.Column(db.Numeric(5, 4), nullable=True)  # 错误率
    
    # 评估周期
    evaluation_period_hours = db.Column(db.Integer, nullable=False, default=24)  # 评估周期(小时)
    calculated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)  # 计算时间
    
    # 关联关系
    miner = db.relationship('HostingMiner', backref='performance_scores', foreign_keys=[miner_id])
    
    # 索引优化
    __table_args__ = (
        db.Index('idx_performance_miner_time', 'miner_id', 'calculated_at'),
        db.UniqueConstraint('miner_id', 'calculated_at', name='uq_miner_calculated_at'),
    )
    
    def __init__(self, miner_id, performance_score, hashrate_ratio, power_efficiency_ratio, 
                 uptime_ratio, **kwargs):
        self.miner_id = miner_id
        self.performance_score = performance_score
        self.hashrate_ratio = hashrate_ratio
        self.power_efficiency_ratio = power_efficiency_ratio
        self.uptime_ratio = uptime_ratio
        
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'miner_id': self.miner_id,
            'performance_score': float(self.performance_score),
            'hashrate_ratio': float(self.hashrate_ratio),
            'power_efficiency_ratio': float(self.power_efficiency_ratio),
            'uptime_ratio': float(self.uptime_ratio),
            'temperature_avg': float(self.temperature_avg) if self.temperature_avg else None,
            'error_rate': float(self.error_rate) if self.error_rate else None,
            'evaluation_period_hours': self.evaluation_period_hours,
            'calculated_at': self.calculated_at.isoformat() if self.calculated_at else None
        }
    
    def __repr__(self):
        return f"<MinerPerformanceScore Miner#{self.miner_id}: {self.performance_score}/100>"


class CurtailmentStrategy(db.Model):
    """
    限电策略配置
    Power Curtailment Strategy Configuration
    """
    __tablename__ = 'curtailment_strategies'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # 关联字段
    site_id = db.Column(db.Integer, db.ForeignKey('hosting_sites.id'), nullable=False, index=True)
    
    # 策略基本信息
    name = db.Column(db.String(100), nullable=False)  # 策略名称
    strategy_type = db.Column(db.Enum(StrategyType), nullable=False, default=StrategyType.PERFORMANCE_PRIORITY)
    
    # 权重配置 (三者之和应为1.0)
    performance_weight = db.Column(db.Numeric(3, 2), nullable=False, default=0.7)  # 性能权重
    power_efficiency_weight = db.Column(db.Numeric(3, 2), nullable=False, default=0.2)  # 能效权重
    uptime_weight = db.Column(db.Numeric(3, 2), nullable=False, default=0.1)  # 运行时间权重
    
    # 保护规则
    vip_customer_protection = db.Column(db.Boolean, nullable=False, default=False)  # VIP客户保护
    min_uptime_threshold = db.Column(db.Numeric(3, 2), nullable=False, default=0.8)  # 最低在线时长阈值
    
    # 状态和审计
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)  # 是否启用
    created_by_id = db.Column(db.Integer, nullable=True)  # 创建人ID
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联关系
    site = db.relationship('HostingSite', backref='curtailment_strategies', foreign_keys=[site_id])
    
    # 索引优化
    __table_args__ = (
        db.Index('idx_strategy_site', 'site_id'),
        db.Index('idx_strategy_active', 'is_active'),
    )
    
    def __init__(self, site_id, name, strategy_type, **kwargs):
        self.site_id = site_id
        self.name = name
        self.strategy_type = strategy_type
        
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'site_id': self.site_id,
            'name': self.name,
            'strategy_type': self.strategy_type.value,
            'performance_weight': float(self.performance_weight),
            'power_efficiency_weight': float(self.power_efficiency_weight),
            'uptime_weight': float(self.uptime_weight),
            'vip_customer_protection': self.vip_customer_protection,
            'min_uptime_threshold': float(self.min_uptime_threshold),
            'is_active': self.is_active,
            'created_by_id': self.created_by_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f"<CurtailmentStrategy {self.name} ({self.strategy_type.value})>"


class CurtailmentPlan(db.Model):
    """
    限电计划
    Power Curtailment Plan
    """
    __tablename__ = 'curtailment_plans'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # 关联字段
    site_id = db.Column(db.Integer, db.ForeignKey('hosting_sites.id'), nullable=False, index=True)
    strategy_id = db.Column(db.Integer, db.ForeignKey('curtailment_strategies.id'), nullable=True)
    
    # 计划基本信息
    plan_name = db.Column(db.String(200), nullable=False)  # 计划名称
    
    # 功率削减目标
    target_power_reduction_kw = db.Column(db.Numeric(12, 2), nullable=False)  # 目标削减功率(kW)
    calculated_power_reduction_kw = db.Column(db.Numeric(12, 2), nullable=True)  # 计算削减功率(kW)
    
    # 执行模式
    execution_mode = db.Column(db.Enum(ExecutionMode), nullable=False, default=ExecutionMode.SEMI_AUTO)
    
    # 时间安排
    scheduled_start_time = db.Column(db.DateTime, nullable=False, index=True)  # 计划开始时间
    scheduled_end_time = db.Column(db.DateTime, nullable=True)  # 计划结束时间
    
    # 状态管理
    status = db.Column(db.Enum(PlanStatus), nullable=False, default=PlanStatus.PENDING, index=True)
    
    # 审批信息
    created_by_id = db.Column(db.Integer, nullable=True)  # 创建人ID
    approved_by_id = db.Column(db.Integer, nullable=True)  # 批准人ID
    approved_at = db.Column(db.DateTime, nullable=True)  # 批准时间
    
    # 时间戳
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联关系
    site = db.relationship('HostingSite', backref='curtailment_plans', foreign_keys=[site_id])
    strategy = db.relationship('CurtailmentStrategy', backref='plans', foreign_keys=[strategy_id])
    
    # 索引优化
    __table_args__ = (
        db.Index('idx_plan_site_time', 'site_id', 'scheduled_start_time'),
        db.Index('idx_plan_status', 'status'),
    )
    
    def __init__(self, site_id, plan_name, target_power_reduction_kw, scheduled_start_time, **kwargs):
        self.site_id = site_id
        self.plan_name = plan_name
        self.target_power_reduction_kw = target_power_reduction_kw
        self.scheduled_start_time = scheduled_start_time
        
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'site_id': self.site_id,
            'strategy_id': self.strategy_id,
            'plan_name': self.plan_name,
            'target_power_reduction_kw': float(self.target_power_reduction_kw),
            'calculated_power_reduction_kw': float(self.calculated_power_reduction_kw) if self.calculated_power_reduction_kw else None,
            'execution_mode': self.execution_mode.value,
            'scheduled_start_time': self.scheduled_start_time.isoformat() if self.scheduled_start_time else None,
            'scheduled_end_time': self.scheduled_end_time.isoformat() if self.scheduled_end_time else None,
            'status': self.status.value,
            'created_by_id': self.created_by_id,
            'approved_by_id': self.approved_by_id,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f"<CurtailmentPlan {self.plan_name} ({self.status.value})>"


class CurtailmentExecution(db.Model):
    """
    限电执行记录
    Power Curtailment Execution Record
    """
    __tablename__ = 'curtailment_executions'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # 关联字段
    plan_id = db.Column(db.Integer, db.ForeignKey('curtailment_plans.id'), nullable=False, index=True)
    miner_id = db.Column(db.Integer, db.ForeignKey('hosting_miners.id'), nullable=False, index=True)
    
    # 执行信息
    execution_action = db.Column(db.Enum(ExecutionAction), nullable=False)  # 执行动作
    executed_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)  # 执行时间
    execution_status = db.Column(db.Enum(ExecutionStatus), nullable=False)  # 执行状态
    error_message = db.Column(db.Text, nullable=True)  # 错误信息
    
    # 影响数据
    power_saved_kw = db.Column(db.Numeric(12, 2), nullable=True)  # 节省功率(kW)
    revenue_lost_usd = db.Column(db.Numeric(12, 2), nullable=True)  # 损失收益($)
    execution_duration_seconds = db.Column(db.Integer, nullable=True)  # 执行耗时(秒)
    
    # 区块链记录
    blockchain_tx_hash = db.Column(db.String(66), nullable=True)  # 区块链交易哈希
    
    # 关联关系
    plan = db.relationship('CurtailmentPlan', backref='executions', foreign_keys=[plan_id])
    miner = db.relationship('HostingMiner', backref='curtailment_executions', foreign_keys=[miner_id])
    
    # 索引优化
    __table_args__ = (
        db.Index('idx_execution_plan_miner', 'plan_id', 'miner_id'),
        db.Index('idx_execution_time', 'executed_at'),
    )
    
    def __init__(self, plan_id, miner_id, execution_action, execution_status, **kwargs):
        self.plan_id = plan_id
        self.miner_id = miner_id
        self.execution_action = execution_action
        self.execution_status = execution_status
        
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'plan_id': self.plan_id,
            'miner_id': self.miner_id,
            'execution_action': self.execution_action.value,
            'executed_at': self.executed_at.isoformat() if self.executed_at else None,
            'execution_status': self.execution_status.value,
            'error_message': self.error_message,
            'power_saved_kw': float(self.power_saved_kw) if self.power_saved_kw else None,
            'revenue_lost_usd': float(self.revenue_lost_usd) if self.revenue_lost_usd else None,
            'execution_duration_seconds': self.execution_duration_seconds,
            'blockchain_tx_hash': self.blockchain_tx_hash
        }
    
    def __repr__(self):
        return f"<CurtailmentExecution Plan#{self.plan_id} Miner#{self.miner_id}: {self.execution_action.value} {self.execution_status.value}>"


class CurtailmentNotification(db.Model):
    """
    限电通知记录
    Power Curtailment Notification Record
    """
    __tablename__ = 'curtailment_notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # 关联字段
    plan_id = db.Column(db.Integer, db.ForeignKey('curtailment_plans.id'), nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('crm_customers.id'), nullable=False, index=True)
    
    # 通知信息
    notification_type = db.Column(db.Enum(NotificationType), nullable=False)  # 通知类型
    sent_at = db.Column(db.DateTime, nullable=True, index=True)  # 发送时间
    delivery_status = db.Column(db.Enum(DeliveryStatus), nullable=False, default=DeliveryStatus.PENDING)  # 发送状态
    
    # 邮件内容
    email_subject = db.Column(db.String(200), nullable=True)  # 邮件主题
    email_body = db.Column(db.Text, nullable=True)  # 邮件正文
    
    # 影响数据
    affected_miners_count = db.Column(db.Integer, nullable=True)  # 受影响矿机数量
    estimated_impact_usd = db.Column(db.Numeric(12, 2), nullable=True)  # 预估影响($)
    
    # 关联关系
    plan = db.relationship('CurtailmentPlan', backref='notifications', foreign_keys=[plan_id])
    customer = db.relationship('Customer', backref='curtailment_notifications', foreign_keys=[customer_id])
    
    # 索引优化
    __table_args__ = (
        db.Index('idx_notification_plan_customer', 'plan_id', 'customer_id'),
        db.Index('idx_notification_sent', 'sent_at'),
    )
    
    def __init__(self, plan_id, customer_id, notification_type, **kwargs):
        self.plan_id = plan_id
        self.customer_id = customer_id
        self.notification_type = notification_type
        
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'plan_id': self.plan_id,
            'customer_id': self.customer_id,
            'notification_type': self.notification_type.value,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
            'delivery_status': self.delivery_status.value,
            'email_subject': self.email_subject,
            'email_body': self.email_body,
            'affected_miners_count': self.affected_miners_count,
            'estimated_impact_usd': float(self.estimated_impact_usd) if self.estimated_impact_usd else None
        }
    
    def __repr__(self):
        return f"<CurtailmentNotification Plan#{self.plan_id} Customer#{self.customer_id}: {self.notification_type.value} ({self.delivery_status.value})>"


class PowerPriceConfig(db.Model):
    """
    电价配置
    Power Price Configuration
    """
    __tablename__ = 'power_price_configs'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # 关联字段
    site_id = db.Column(db.Integer, db.ForeignKey('hosting_sites.id'), nullable=False, index=True)
    
    # 配置基本信息
    config_name = db.Column(db.String(100), nullable=False)  # 配置名称
    price_mode = db.Column(db.Enum(PriceMode), nullable=False, default=PriceMode.FIXED)  # 电价模式
    
    # 固定电价
    fixed_price = db.Column(db.Numeric(10, 6), nullable=True)  # 固定电价($/kWh)
    
    # 峰谷电价
    peak_price = db.Column(db.Numeric(10, 6), nullable=True)  # 峰电价($/kWh)
    valley_price = db.Column(db.Numeric(10, 6), nullable=True)  # 谷电价($/kWh)
    peak_hours_start = db.Column(db.Integer, nullable=True)  # 峰时开始小时(0-23)
    peak_hours_end = db.Column(db.Integer, nullable=True)  # 峰时结束小时(0-23)
    
    # 24小时电价
    hourly_prices = db.Column(db.Text, nullable=True)  # JSON格式存储24小时电价数组
    
    # API实时电价
    api_endpoint = db.Column(db.String(500), nullable=True)  # API端点
    
    # 月度合约电价
    contract_price = db.Column(db.Numeric(10, 6), nullable=True)  # 合约电价($/kWh)
    
    # 有效期
    valid_from = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)  # 生效时间
    valid_until = db.Column(db.DateTime, nullable=True)  # 失效时间
    
    # 状态
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)  # 是否启用
    
    # 时间戳
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联关系
    site = db.relationship('HostingSite', backref='power_price_configs', foreign_keys=[site_id])
    
    # 索引优化
    __table_args__ = (
        db.Index('idx_price_config_site_active', 'site_id', 'is_active'),
    )
    
    def __init__(self, site_id, config_name, price_mode, **kwargs):
        self.site_id = site_id
        self.config_name = config_name
        self.price_mode = price_mode
        
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'site_id': self.site_id,
            'config_name': self.config_name,
            'price_mode': self.price_mode.value,
            'fixed_price': float(self.fixed_price) if self.fixed_price else None,
            'peak_price': float(self.peak_price) if self.peak_price else None,
            'valley_price': float(self.valley_price) if self.valley_price else None,
            'peak_hours_start': self.peak_hours_start,
            'peak_hours_end': self.peak_hours_end,
            'hourly_prices': self.hourly_prices,
            'api_endpoint': self.api_endpoint,
            'contract_price': float(self.contract_price) if self.contract_price else None,
            'valid_from': self.valid_from.isoformat() if self.valid_from else None,
            'valid_until': self.valid_until.isoformat() if self.valid_until else None,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f"<PowerPriceConfig {self.config_name} ({self.price_mode.value})>"


# ==================== 温度智能控频模型 ====================

class ThermalProtectionConfig(db.Model):
    """热保护配置 - 温度阈值和频率控制设置"""
    __tablename__ = 'thermal_protection_configs'
    
    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey('hosting_sites.id'), nullable=False, index=True)
    
    # 配置名称
    config_name = db.Column(db.String(100), nullable=False, default='默认热保护配置')
    
    # 温度阈值 (°C)
    warning_temp = db.Column(db.Float, nullable=False, default=70.0)  # 预警温度
    throttle_temp = db.Column(db.Float, nullable=False, default=80.0)  # 开始降频温度
    critical_temp = db.Column(db.Float, nullable=False, default=90.0)  # 临界温度(强制关机)
    recovery_temp = db.Column(db.Float, nullable=False, default=65.0)  # 恢复温度(恢复正常频率)
    
    # 频率控制
    throttle_frequency_percent = db.Column(db.Integer, nullable=False, default=80)  # 降频比例(%)
    min_frequency_percent = db.Column(db.Integer, nullable=False, default=50)  # 最低频率(%)
    
    # 冷却等待时间
    cooldown_minutes = db.Column(db.Integer, nullable=False, default=10)  # 降频后等待时间(分钟)
    
    # 启用状态
    is_enabled = db.Column(db.Boolean, nullable=False, default=True)
    
    # 通知设置
    notify_on_warning = db.Column(db.Boolean, nullable=False, default=True)
    notify_on_throttle = db.Column(db.Boolean, nullable=False, default=True)
    notify_on_critical = db.Column(db.Boolean, nullable=False, default=True)
    notification_email = db.Column(db.String(256), nullable=True)
    
    # 时间戳
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联关系
    site = db.relationship('HostingSite', backref='thermal_configs', foreign_keys=[site_id])
    
    def __init__(self, site_id, **kwargs):
        self.site_id = site_id
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def to_dict(self):
        return {
            'id': self.id,
            'site_id': self.site_id,
            'config_name': self.config_name,
            'warning_temp': self.warning_temp,
            'throttle_temp': self.throttle_temp,
            'critical_temp': self.critical_temp,
            'recovery_temp': self.recovery_temp,
            'throttle_frequency_percent': self.throttle_frequency_percent,
            'min_frequency_percent': self.min_frequency_percent,
            'cooldown_minutes': self.cooldown_minutes,
            'is_enabled': self.is_enabled,
            'notify_on_warning': self.notify_on_warning,
            'notify_on_throttle': self.notify_on_throttle,
            'notify_on_critical': self.notify_on_critical,
            'notification_email': self.notification_email,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f"<ThermalProtectionConfig {self.config_name} (site={self.site_id})>"


class ThermalEventType:
    """热保护事件类型"""
    WARNING = 'warning'  # 温度预警
    THROTTLE = 'throttle'  # 降频
    CRITICAL = 'critical'  # 临界(强制关机)
    RECOVERY = 'recovery'  # 恢复正常


class ThermalEvent(db.Model):
    """热保护事件日志 - 记录所有温度保护事件"""
    __tablename__ = 'thermal_events'
    
    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey('hosting_sites.id'), nullable=False, index=True)
    miner_id = db.Column(db.Integer, db.ForeignKey('hosting_miners.id'), nullable=False, index=True)
    
    # 事件信息
    event_type = db.Column(db.String(20), nullable=False, index=True)  # warning/throttle/critical/recovery
    temperature = db.Column(db.Float, nullable=False)  # 触发时温度
    threshold = db.Column(db.Float, nullable=False)  # 触发阈值
    
    # 动作信息
    action_taken = db.Column(db.String(50), nullable=True)  # 采取的动作
    frequency_before = db.Column(db.Float, nullable=True)  # 降频前频率(MHz)
    frequency_after = db.Column(db.Float, nullable=True)  # 降频后频率(MHz)
    
    # 结果
    success = db.Column(db.Boolean, nullable=False, default=True)
    error_message = db.Column(db.Text, nullable=True)
    
    # 通知状态
    notification_sent = db.Column(db.Boolean, nullable=False, default=False)
    
    # 时间戳
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    resolved_at = db.Column(db.DateTime, nullable=True)  # 事件解决时间
    
    # 关联关系
    site = db.relationship('HostingSite', backref='thermal_events', foreign_keys=[site_id])
    miner = db.relationship('HostingMiner', backref='thermal_events', foreign_keys=[miner_id])
    
    # 索引优化
    __table_args__ = (
        db.Index('idx_thermal_event_site_type', 'site_id', 'event_type'),
        db.Index('idx_thermal_event_miner_created', 'miner_id', 'created_at'),
    )
    
    def __init__(self, site_id, miner_id, event_type, temperature, threshold, **kwargs):
        self.site_id = site_id
        self.miner_id = miner_id
        self.event_type = event_type
        self.temperature = temperature
        self.threshold = threshold
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def to_dict(self):
        return {
            'id': self.id,
            'site_id': self.site_id,
            'miner_id': self.miner_id,
            'event_type': self.event_type,
            'temperature': self.temperature,
            'threshold': self.threshold,
            'action_taken': self.action_taken,
            'frequency_before': self.frequency_before,
            'frequency_after': self.frequency_after,
            'success': self.success,
            'error_message': self.error_message,
            'notification_sent': self.notification_sent,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None
        }
    
    def __repr__(self):
        return f"<ThermalEvent {self.event_type} miner={self.miner_id} temp={self.temperature}°C>"


# ==================== 白标品牌系统模型 ====================

class SiteBranding(db.Model):
    """站点品牌配置 - 白标系统"""
    __tablename__ = 'site_branding'
    
    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey('hosting_sites.id'), nullable=False, unique=True, index=True)
    
    # 品牌信息
    company_name = db.Column(db.String(200), nullable=True)  # 公司名称
    company_slogan = db.Column(db.String(500), nullable=True)  # 公司标语
    
    # Logo 配置
    logo_url = db.Column(db.String(500), nullable=True)  # Logo URL
    logo_light_url = db.Column(db.String(500), nullable=True)  # 浅色背景 Logo
    logo_dark_url = db.Column(db.String(500), nullable=True)  # 深色背景 Logo
    favicon_url = db.Column(db.String(500), nullable=True)  # Favicon URL
    
    # 颜色配置
    primary_color = db.Column(db.String(7), nullable=True, default='#f7931a')  # 主色 (BTC金)
    secondary_color = db.Column(db.String(7), nullable=True, default='#1a1d2e')  # 次色 (深蓝)
    accent_color = db.Column(db.String(7), nullable=True, default='#ffc107')  # 强调色
    
    # 联系信息
    support_email = db.Column(db.String(256), nullable=True)
    support_phone = db.Column(db.String(50), nullable=True)
    website_url = db.Column(db.String(500), nullable=True)
    
    # 社交媒体
    twitter_url = db.Column(db.String(500), nullable=True)
    telegram_url = db.Column(db.String(500), nullable=True)
    discord_url = db.Column(db.String(500), nullable=True)
    
    # 自定义页脚
    footer_text = db.Column(db.Text, nullable=True)
    
    # 启用状态
    is_enabled = db.Column(db.Boolean, nullable=False, default=True)
    
    # 时间戳
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联关系
    site = db.relationship('HostingSite', backref=db.backref('branding', uselist=False), foreign_keys=[site_id])
    
    def __init__(self, site_id, **kwargs):
        self.site_id = site_id
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def to_dict(self):
        return {
            'id': self.id,
            'site_id': self.site_id,
            'company_name': self.company_name,
            'company_slogan': self.company_slogan,
            'logo_url': self.logo_url,
            'logo_light_url': self.logo_light_url,
            'logo_dark_url': self.logo_dark_url,
            'favicon_url': self.favicon_url,
            'primary_color': self.primary_color,
            'secondary_color': self.secondary_color,
            'accent_color': self.accent_color,
            'support_email': self.support_email,
            'support_phone': self.support_phone,
            'website_url': self.website_url,
            'twitter_url': self.twitter_url,
            'telegram_url': self.telegram_url,
            'discord_url': self.discord_url,
            'footer_text': self.footer_text,
            'is_enabled': self.is_enabled,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f"<SiteBranding {self.company_name or 'Unnamed'} (site={self.site_id})>"


# ==================== 电力监控数据模型 ====================
# Power Monitoring Data Models for Energy Management Center
# ===========================================================

class SiteEnergyHourly(db.Model):
    """站点小时用电聚合"""
    __tablename__ = 'site_energy_hourly'
    
    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey('hosting_sites.id'), nullable=False, index=True)
    hour_ts = db.Column(db.DateTime, nullable=False, index=True)  # 小时时间戳
    
    kwh = db.Column(db.Float, default=0.0, nullable=False)  # 用电量 kWh
    avg_kw = db.Column(db.Float, default=0.0, nullable=False)  # 平均功率 kW
    peak_kw = db.Column(db.Float, default=0.0, nullable=False)  # 峰值功率 kW
    cost_usd = db.Column(db.Float, default=0.0, nullable=False)  # 成本 USD
    co2_kg = db.Column(db.Float, default=0.0, nullable=False)  # 碳排放 kg
    
    miner_count = db.Column(db.Integer, default=0, nullable=False)  # 矿机数量
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    __table_args__ = (db.UniqueConstraint('site_id', 'hour_ts', name='uq_site_energy_hourly'),)
    
    site = db.relationship('HostingSite', backref=db.backref('energy_hourly', lazy=True))
    
    def __init__(self, site_id, hour_ts, **kwargs):
        self.site_id = site_id
        self.hour_ts = hour_ts
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def to_dict(self):
        return {
            'id': self.id,
            'site_id': self.site_id,
            'hour_ts': self.hour_ts.isoformat() if self.hour_ts else None,
            'kwh': self.kwh,
            'avg_kw': self.avg_kw,
            'peak_kw': self.peak_kw,
            'cost_usd': self.cost_usd,
            'co2_kg': self.co2_kg,
            'miner_count': self.miner_count,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f"<SiteEnergyHourly site={self.site_id} hour={self.hour_ts} kwh={self.kwh}>"


class SiteEnergyDaily(db.Model):
    """站点日用电聚合"""
    __tablename__ = 'site_energy_daily'
    
    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey('hosting_sites.id'), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False, index=True)
    
    kwh = db.Column(db.Float, default=0.0, nullable=False)
    cost_usd = db.Column(db.Float, default=0.0, nullable=False)
    peak_kw = db.Column(db.Float, default=0.0, nullable=False)
    co2_kg = db.Column(db.Float, default=0.0, nullable=False)
    
    avg_price_per_kwh = db.Column(db.Float, default=0.0, nullable=False)  # 平均电价
    miner_count = db.Column(db.Integer, default=0, nullable=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    __table_args__ = (db.UniqueConstraint('site_id', 'date', name='uq_site_energy_daily'),)
    
    site = db.relationship('HostingSite', backref=db.backref('energy_daily', lazy=True))
    
    def __init__(self, site_id, date, **kwargs):
        self.site_id = site_id
        self.date = date
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def to_dict(self):
        return {
            'id': self.id,
            'site_id': self.site_id,
            'date': self.date.isoformat() if self.date else None,
            'kwh': self.kwh,
            'cost_usd': self.cost_usd,
            'peak_kw': self.peak_kw,
            'co2_kg': self.co2_kg,
            'avg_price_per_kwh': self.avg_price_per_kwh,
            'miner_count': self.miner_count,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f"<SiteEnergyDaily site={self.site_id} date={self.date} kwh={self.kwh}>"


class SiteEnergyMonthly(db.Model):
    """站点月用电聚合"""
    __tablename__ = 'site_energy_monthly'
    
    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey('hosting_sites.id'), nullable=False, index=True)
    month = db.Column(db.Date, nullable=False, index=True)  # 月份第一天
    
    kwh = db.Column(db.Float, default=0.0, nullable=False)
    cost_usd = db.Column(db.Float, default=0.0, nullable=False)
    peak_kw = db.Column(db.Float, default=0.0, nullable=False)
    co2_kg = db.Column(db.Float, default=0.0, nullable=False)
    
    avg_price_per_kwh = db.Column(db.Float, default=0.0, nullable=False)
    
    contract_kwh = db.Column(db.Float, nullable=True)  # 合同用电量
    contract_usage_pct = db.Column(db.Float, nullable=True)  # 用量百分比
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    __table_args__ = (db.UniqueConstraint('site_id', 'month', name='uq_site_energy_monthly'),)
    
    site = db.relationship('HostingSite', backref=db.backref('energy_monthly', lazy=True))
    
    def __init__(self, site_id, month, **kwargs):
        self.site_id = site_id
        self.month = month
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def to_dict(self):
        return {
            'id': self.id,
            'site_id': self.site_id,
            'month': self.month.isoformat() if self.month else None,
            'kwh': self.kwh,
            'cost_usd': self.cost_usd,
            'peak_kw': self.peak_kw,
            'co2_kg': self.co2_kg,
            'avg_price_per_kwh': self.avg_price_per_kwh,
            'contract_kwh': self.contract_kwh,
            'contract_usage_pct': self.contract_usage_pct,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f"<SiteEnergyMonthly site={self.site_id} month={self.month} kwh={self.kwh}>"


class PowerContract(db.Model):
    """电力合同"""
    __tablename__ = 'power_contracts'
    
    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey('hosting_sites.id'), nullable=False, index=True)
    
    provider = db.Column(db.String(200), nullable=False)  # 供电商
    contract_number = db.Column(db.String(100), nullable=True)  # 合同编号
    
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    
    contract_kwh_month = db.Column(db.Float, nullable=True)  # 月合同电量 kWh
    demand_limit_kw = db.Column(db.Float, nullable=True)  # 需量限制 kW
    
    rate_model = db.Column(db.String(20), default='flat', nullable=False)  # flat/tou/index
    base_rate = db.Column(db.Float, nullable=True)  # 基础费率
    
    notes = db.Column(db.Text, nullable=True)
    attachments_url = db.Column(db.String(500), nullable=True)
    
    status = db.Column(db.String(20), default='active', nullable=False)  # active/expired/terminated
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    site = db.relationship('HostingSite', backref=db.backref('power_contracts', lazy=True))
    
    def __init__(self, site_id, provider, start_date, end_date, **kwargs):
        self.site_id = site_id
        self.provider = provider
        self.start_date = start_date
        self.end_date = end_date
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def to_dict(self):
        return {
            'id': self.id,
            'site_id': self.site_id,
            'provider': self.provider,
            'contract_number': self.contract_number,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'contract_kwh_month': self.contract_kwh_month,
            'demand_limit_kw': self.demand_limit_kw,
            'rate_model': self.rate_model,
            'base_rate': self.base_rate,
            'notes': self.notes,
            'attachments_url': self.attachments_url,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f"<PowerContract site={self.site_id} provider={self.provider} status={self.status}>"


class CarbonConfig(db.Model):
    """碳排放配置"""
    __tablename__ = 'carbon_configs'
    
    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey('hosting_sites.id'), nullable=False, unique=True)
    
    kg_co2_per_kwh = db.Column(db.Float, default=0.42, nullable=False)  # 每kWh碳排放 kg
    source_type = db.Column(db.String(50), default='grid', nullable=False)  # grid/renewable/mixed/hydro/solar/wind/nuclear/coal
    
    renewable_percentage = db.Column(db.Float, default=0.0, nullable=True)  # 可再生能源占比
    grid_region = db.Column(db.String(100), nullable=True)  # 电网区域
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    site = db.relationship('HostingSite', backref=db.backref('carbon_config', uselist=False))
    
    def __init__(self, site_id, **kwargs):
        self.site_id = site_id
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def to_dict(self):
        return {
            'id': self.id,
            'site_id': self.site_id,
            'kg_co2_per_kwh': self.kg_co2_per_kwh,
            'source_type': self.source_type,
            'renewable_percentage': self.renewable_percentage,
            'grid_region': self.grid_region,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f"<CarbonConfig site={self.site_id} co2={self.kg_co2_per_kwh}kg/kWh source={self.source_type}>"


class PowerAlert(db.Model):
    """电力告警"""
    __tablename__ = 'power_alerts'
    
    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey('hosting_sites.id'), nullable=False, index=True)
    miner_id = db.Column(db.Integer, db.ForeignKey('hosting_miners.id'), nullable=True, index=True)
    
    alert_type = db.Column(db.String(50), nullable=False)  # POWER_SPIKE/PEAK_HOUR/OVER_CONTRACT/ABNORMAL_CONSUMPTION/PRICE_CHANGE
    severity = db.Column(db.String(20), default='warning', nullable=False)  # info/warning/critical
    
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    context = db.Column(db.JSON, nullable=True)  # 告警上下文数据
    
    status = db.Column(db.String(20), default='active', nullable=False)  # active/acknowledged/resolved
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    acknowledged_at = db.Column(db.DateTime, nullable=True)
    resolved_at = db.Column(db.DateTime, nullable=True)
    
    acknowledged_by_id = db.Column(db.Integer, db.ForeignKey('user_access.id'), nullable=True)
    
    site = db.relationship('HostingSite', backref=db.backref('power_alerts', lazy=True))
    miner = db.relationship('HostingMiner', backref=db.backref('power_alerts', lazy=True))
    acknowledged_by = db.relationship('UserAccess', foreign_keys=[acknowledged_by_id])
    
    def __init__(self, site_id, alert_type, title, message, **kwargs):
        self.site_id = site_id
        self.alert_type = alert_type
        self.title = title
        self.message = message
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def acknowledge(self, user_id):
        """确认告警"""
        self.status = 'acknowledged'
        self.acknowledged_at = datetime.utcnow()
        self.acknowledged_by_id = user_id
    
    def resolve(self):
        """解决告警"""
        self.status = 'resolved'
        self.resolved_at = datetime.utcnow()
    
    def to_dict(self):
        return {
            'id': self.id,
            'site_id': self.site_id,
            'miner_id': self.miner_id,
            'alert_type': self.alert_type,
            'severity': self.severity,
            'title': self.title,
            'message': self.message,
            'context': self.context,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'acknowledged_at': self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'acknowledged_by_id': self.acknowledged_by_id
        }
    
    def __repr__(self):
        return f"<PowerAlert site={self.site_id} type={self.alert_type} severity={self.severity} status={self.status}>"


class SiteElectricityRateHistory(db.Model):
    """站点电价历史记录 - 支持历史电价保留和按时间段计算电费"""
    __tablename__ = 'site_electricity_rate_history'
    
    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey('hosting_sites.id'), nullable=False, index=True)
    
    rate_usd_per_kwh = db.Column(db.Float, nullable=False)
    effective_from = db.Column(db.DateTime, nullable=False, index=True)
    effective_to = db.Column(db.DateTime, nullable=True, index=True)
    
    rate_type = db.Column(db.String(20), default='flat', nullable=False)
    notes = db.Column(db.String(500), nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user_access.id'), nullable=True)
    
    __table_args__ = (
        db.Index('ix_rate_history_site_effective', 'site_id', 'effective_from'),
    )
    
    site = db.relationship('HostingSite', backref=db.backref('rate_history', lazy=True, order_by='SiteElectricityRateHistory.effective_from.desc()'))
    created_by = db.relationship('UserAccess', foreign_keys=[created_by_id])
    
    def __init__(self, site_id, rate_usd_per_kwh, effective_from, **kwargs):
        self.site_id = site_id
        self.rate_usd_per_kwh = rate_usd_per_kwh
        self.effective_from = effective_from
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    @property
    def is_current(self):
        """是否为当前生效的电价"""
        return self.effective_to is None
    
    def to_dict(self):
        return {
            'id': self.id,
            'site_id': self.site_id,
            'rate_usd_per_kwh': self.rate_usd_per_kwh,
            'effective_from': self.effective_from.isoformat() if self.effective_from else None,
            'effective_to': self.effective_to.isoformat() if self.effective_to else None,
            'rate_type': self.rate_type,
            'notes': self.notes,
            'is_current': self.is_current,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'created_by_id': self.created_by_id
        }
    
    def __repr__(self):
        status = 'current' if self.is_current else 'historical'
        return f"<SiteElectricityRateHistory site={self.site_id} rate=${self.rate_usd_per_kwh}/kWh {status}>"


# ============================================================================
# 自动化规则系统数据模型
# Automation Rule System Data Models
# ============================================================================

class AutomationRule(db.Model):
    """自动化规则 - 温度/性能触发器"""
    __tablename__ = 'automation_rules'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    
    # 规则范围
    site_id = db.Column(db.Integer, db.ForeignKey('hosting_sites.id'), nullable=True)  # 可选，限定站点
    miner_ids = db.Column(db.JSON)  # 可选，限定特定矿机ID列表；null表示适用所有
    
    # 触发条件
    trigger_type = db.Column(db.String(50), nullable=False)  # temperature_high, etc.
    trigger_metric = db.Column(db.String(50), nullable=False, default='temp_max')  # temp_max, temp_avg, hashrate, power
    trigger_operator = db.Column(db.String(10), nullable=False, default='>')  # >, <, >=, <=, ==
    trigger_value = db.Column(db.Float, nullable=False)  # 阈值
    trigger_duration_seconds = db.Column(db.Integer, default=0)  # 持续时间（秒），0表示立即触发
    
    # 动作配置
    action_type = db.Column(db.String(50), nullable=False)  # power_mode_low, reboot, etc.
    action_parameters = db.Column(db.JSON, default={})  # 动作参数
    
    # 恢复条件（可选）
    recovery_enabled = db.Column(db.Boolean, default=False)
    recovery_trigger_value = db.Column(db.Float)  # 恢复阈值
    recovery_action_type = db.Column(db.String(50))  # 恢复动作
    
    # 冷却期
    cooldown_seconds = db.Column(db.Integer, default=1800)  # 默认30分钟
    
    # 状态
    is_enabled = db.Column(db.Boolean, default=True)
    priority = db.Column(db.Integer, default=5)  # 1-10，数字越大优先级越高
    
    # 创建信息 (不使用外键约束，因为用户可能在user_access表或users表中)
    created_by = db.Column(db.String)  # 存储用户ID或操作员ID，不强制外键
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    site = db.relationship('HostingSite', backref=db.backref('automation_rules', lazy='dynamic'))
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'site_id': self.site_id,
            'miner_ids': self.miner_ids,
            'trigger_type': self.trigger_type,
            'trigger_metric': self.trigger_metric,
            'trigger_operator': self.trigger_operator,
            'trigger_value': self.trigger_value,
            'trigger_duration_seconds': self.trigger_duration_seconds,
            'action_type': self.action_type,
            'action_parameters': self.action_parameters,
            'recovery_enabled': self.recovery_enabled,
            'recovery_trigger_value': self.recovery_trigger_value,
            'recovery_action_type': self.recovery_action_type,
            'cooldown_seconds': self.cooldown_seconds,
            'is_enabled': self.is_enabled,
            'priority': self.priority,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class AutomationRuleLog(db.Model):
    """自动化规则执行日志"""
    __tablename__ = 'automation_rule_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    rule_id = db.Column(db.Integer, db.ForeignKey('automation_rules.id'), nullable=False)
    miner_id = db.Column(db.Integer, db.ForeignKey('hosting_miners.id'), nullable=False)
    
    # 触发信息
    trigger_value_actual = db.Column(db.Float)  # 实际触发值
    triggered_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 动作执行
    action_type = db.Column(db.String(50))
    action_status = db.Column(db.String(20), default='pending')  # pending, executed, failed
    command_id = db.Column(db.Integer)  # 关联的MinerCommand ID
    
    # 结果
    executed_at = db.Column(db.DateTime)
    result_message = db.Column(db.Text)
    
    # 关系
    rule = db.relationship('AutomationRule', backref=db.backref('logs', lazy='dynamic'))
    miner = db.relationship('HostingMiner', backref=db.backref('automation_logs', lazy='dynamic'))
    
    def to_dict(self):
        return {
            'id': self.id,
            'rule_id': self.rule_id,
            'miner_id': self.miner_id,
            'trigger_value_actual': self.trigger_value_actual,
            'triggered_at': self.triggered_at.isoformat() if self.triggered_at else None,
            'action_type': self.action_type,
            'action_status': self.action_status,
            'command_id': self.command_id,
            'executed_at': self.executed_at.isoformat() if self.executed_at else None,
            'result_message': self.result_message
        }


class AutomationRuleCooldown(db.Model):
    """自动化规则冷却记录 - 防止规则反复触发"""
    __tablename__ = 'automation_rule_cooldowns'
    
    id = db.Column(db.Integer, primary_key=True)
    rule_id = db.Column(db.Integer, db.ForeignKey('automation_rules.id'), nullable=False)
    miner_id = db.Column(db.Integer, db.ForeignKey('hosting_miners.id'), nullable=False)
    last_triggered_at = db.Column(db.DateTime, default=datetime.utcnow)
    cooldown_until = db.Column(db.DateTime, nullable=False)
    
    __table_args__ = (
        db.UniqueConstraint('rule_id', 'miner_id', name='uq_rule_miner_cooldown'),
    )


