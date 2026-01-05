"""
Control Plane Models - 控制平面核心数据模型
100MW+ 矿场运营管理系统

包含：Zone分区、Customer隔离、PricePlan价格计划、DemandLedger需量账本、
CommandApproval审批记录、AuditEvent审计事件等
"""
import enum
import uuid
import hashlib
import json
from datetime import datetime
from db import db


class RiskTier(enum.Enum):
    """风险等级"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class ApprovalDecision(enum.Enum):
    """审批决定"""
    APPROVE = "APPROVE"
    DENY = "DENY"


class MissingDataPolicy(enum.Enum):
    """缺口数据处理策略"""
    CARRY_FORWARD = "carry_forward"
    INTERPOLATE = "interpolate"
    MARK_MISSING = "mark_missing"


class EnergySource(enum.Enum):
    """能源类型"""
    HYDRO = "hydro"
    SOLAR = "solar"
    WIND = "wind"
    NUCLEAR = "nuclear"
    NATURAL_GAS = "natural_gas"
    COAL = "coal"
    GRID = "grid"


class ZoneType(enum.Enum):
    """分区类型"""
    ROOM = "room"
    CONTAINER = "container"
    POWER = "power"
    BUILDING = "building"


class Zone(db.Model):
    """分区模型 - Site下的逻辑分区（机房/集装箱/电力分区）"""
    __tablename__ = 'zones'
    
    id = db.Column(db.Integer, primary_key=True)
    zone_id = db.Column(db.String(50), unique=True, nullable=False, default=lambda: f"zone_{uuid.uuid4().hex[:8]}")
    site_id = db.Column(db.Integer, db.ForeignKey('hosting_sites.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    zone_type = db.Column(db.String(50), default='room')
    description = db.Column(db.Text)
    capacity_kw = db.Column(db.Float, default=0)
    contracted_capacity_kw = db.Column(db.Float, default=0)
    energy_source = db.Column(db.String(50), default='grid')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    site = db.relationship('HostingSite', backref=db.backref('zones', lazy='dynamic'))
    
    def to_dict(self):
        return {
            'id': self.id,
            'zone_id': self.zone_id,
            'site_id': self.site_id,
            'name': self.name,
            'zone_type': self.zone_type,
            'description': self.description,
            'capacity_kw': self.capacity_kw,
            'contracted_capacity_kw': self.contracted_capacity_kw,
            'energy_source': self.energy_source,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class HostingCustomer(db.Model):
    """托管客户 - 与Site关联的客户（用于客户隔离）"""
    __tablename__ = 'hosting_customers'
    
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.String(50), unique=True, nullable=False, default=lambda: f"cust_{uuid.uuid4().hex[:8]}")
    site_id = db.Column(db.Integer, db.ForeignKey('hosting_sites.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user_access.id'), nullable=True)
    name = db.Column(db.String(200), nullable=False)
    company = db.Column(db.String(200))
    email = db.Column(db.String(256))
    phone = db.Column(db.String(50))
    contract_start = db.Column(db.DateTime)
    contract_end = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    site = db.relationship('HostingSite', backref=db.backref('hosting_customers', lazy='dynamic'))
    user = db.relationship('UserAccess', backref=db.backref('hosting_customer_profile', uselist=False))
    
    def to_dict(self):
        return {
            'id': self.id,
            'customer_id': self.customer_id,
            'site_id': self.site_id,
            'user_id': self.user_id,
            'name': self.name,
            'company': self.company,
            'email': self.email,
            'phone': self.phone,
            'contract_start': self.contract_start.isoformat() if self.contract_start else None,
            'contract_end': self.contract_end.isoformat() if self.contract_end else None,
            'is_active': self.is_active,
        }


class MinerAsset(db.Model):
    """逻辑矿机资产 - 云端只存逻辑ID，不存IP/凭据"""
    __tablename__ = 'cp_miner_assets'
    
    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.String(50), unique=True, nullable=False, default=lambda: f"miner_{uuid.uuid4().hex[:8]}")
    site_id = db.Column(db.Integer, db.ForeignKey('hosting_sites.id'), nullable=False)
    zone_id = db.Column(db.Integer, db.ForeignKey('zones.id'), nullable=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('hosting_customers.id'), nullable=True)
    model = db.Column(db.String(100))
    vendor = db.Column(db.String(100))
    serial_number = db.Column(db.String(100))
    firmware = db.Column(db.String(100))
    hashrate_th = db.Column(db.Float, default=0)
    power_w = db.Column(db.Float, default=0)
    tags = db.Column(db.JSON, default=list)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    site = db.relationship('HostingSite', backref=db.backref('cp_miner_assets', lazy='dynamic'))
    zone = db.relationship('Zone', backref=db.backref('cp_miner_assets', lazy='dynamic'))
    customer = db.relationship('HostingCustomer', backref=db.backref('cp_miner_assets', lazy='dynamic'))
    
    def to_dict(self):
        return {
            'id': self.id,
            'asset_id': self.asset_id,
            'site_id': self.site_id,
            'zone_id': self.zone_id,
            'customer_id': self.customer_id,
            'model': self.model,
            'vendor': self.vendor,
            'serial_number': self.serial_number,
            'firmware': self.firmware,
            'hashrate_th': self.hashrate_th,
            'power_w': self.power_w,
            'tags': self.tags,
            'is_active': self.is_active,
        }


class MinerCapability(db.Model):
    """矿机能力探测结果"""
    __tablename__ = 'cp_miner_capabilities'
    
    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.Integer, db.ForeignKey('cp_miner_assets.id'), nullable=False)
    supports_actions = db.Column(db.JSON, default=list)
    firmware_features = db.Column(db.JSON, default=dict)
    detected_at = db.Column(db.DateTime, default=datetime.utcnow)
    detected_by_edge_id = db.Column(db.String(50))
    
    asset = db.relationship('MinerAsset', backref=db.backref('capabilities', lazy='dynamic'))
    
    def to_dict(self):
        return {
            'id': self.id,
            'asset_id': self.asset_id,
            'supports_actions': self.supports_actions,
            'firmware_features': self.firmware_features,
            'detected_at': self.detected_at.isoformat() if self.detected_at else None,
        }


class PricePlan(db.Model):
    """价格计划"""
    __tablename__ = 'price_plans'
    
    id = db.Column(db.Integer, primary_key=True)
    price_plan_id = db.Column(db.String(50), unique=True, nullable=False, default=lambda: f"plan_{uuid.uuid4().hex[:8]}")
    site_id = db.Column(db.Integer, db.ForeignKey('hosting_sites.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    site = db.relationship('HostingSite', backref=db.backref('price_plans', lazy='dynamic'))
    
    def to_dict(self):
        return {
            'id': self.id,
            'price_plan_id': self.price_plan_id,
            'site_id': self.site_id,
            'name': self.name,
            'description': self.description,
            'is_active': self.is_active,
        }


class PricePlanVersion(db.Model):
    """价格计划版本 - 支持版本化和历史追溯"""
    __tablename__ = 'price_plan_versions'
    
    id = db.Column(db.Integer, primary_key=True)
    version_id = db.Column(db.String(50), unique=True, nullable=False, default=lambda: f"ppv_{uuid.uuid4().hex[:8]}")
    price_plan_id = db.Column(db.Integer, db.ForeignKey('price_plans.id'), nullable=False)
    version_number = db.Column(db.Integer, default=1)
    effective_from = db.Column(db.DateTime, nullable=False)
    effective_to = db.Column(db.DateTime)
    timezone = db.Column(db.String(50), default='UTC')
    granularity = db.Column(db.String(20), default='hourly')
    source_file_hash = db.Column(db.String(64))
    source_file_name = db.Column(db.String(255))
    missing_data_policy = db.Column(db.String(50), default='carry_forward')
    payload_json = db.Column(db.JSON, nullable=False, default=dict)
    created_by = db.Column(db.Integer, db.ForeignKey('user_access.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    price_plan = db.relationship('PricePlan', backref=db.backref('versions', lazy='dynamic'))
    creator = db.relationship('UserAccess', backref=db.backref('price_plan_versions_created', lazy='dynamic'))
    
    def to_dict(self):
        return {
            'id': self.id,
            'version_id': self.version_id,
            'price_plan_id': self.price_plan_id,
            'version_number': self.version_number,
            'effective_from': self.effective_from.isoformat() if self.effective_from else None,
            'effective_to': self.effective_to.isoformat() if self.effective_to else None,
            'timezone': self.timezone,
            'granularity': self.granularity,
            'missing_data_policy': self.missing_data_policy,
            'source_file_hash': self.source_file_hash,
            'source_file_name': self.source_file_name,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class DemandLedgerMonthly(db.Model):
    """月度需量账本 - 15分钟需量峰值追踪"""
    __tablename__ = 'demand_ledger_monthly'
    
    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey('hosting_sites.id'), nullable=False)
    zone_id = db.Column(db.Integer, db.ForeignKey('zones.id'), nullable=True)
    year = db.Column(db.Integer, nullable=False)
    month = db.Column(db.Integer, nullable=False)
    peak_kw = db.Column(db.Float, default=0)
    peak_window_start = db.Column(db.DateTime)
    peak_window_end = db.Column(db.DateTime)
    source = db.Column(db.String(20), default='measured')
    price_plan_version_id = db.Column(db.Integer, db.ForeignKey('price_plan_versions.id'), nullable=True)
    demand_charge_usd = db.Column(db.Float, default=0)
    total_consumption_kwh = db.Column(db.Float, default=0)
    energy_charge_usd = db.Column(db.Float, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    site = db.relationship('HostingSite', backref=db.backref('demand_ledgers', lazy='dynamic'))
    zone = db.relationship('Zone', backref=db.backref('demand_ledgers', lazy='dynamic'))
    price_plan_version = db.relationship('PricePlanVersion', backref=db.backref('demand_ledgers', lazy='dynamic'))
    
    __table_args__ = (
        db.UniqueConstraint('site_id', 'zone_id', 'year', 'month', name='uq_demand_ledger_site_zone_month'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'site_id': self.site_id,
            'zone_id': self.zone_id,
            'year': self.year,
            'month': self.month,
            'peak_kw': self.peak_kw,
            'peak_window_start': self.peak_window_start.isoformat() if self.peak_window_start else None,
            'peak_window_end': self.peak_window_end.isoformat() if self.peak_window_end else None,
            'source': self.source,
            'demand_charge_usd': self.demand_charge_usd,
            'total_consumption_kwh': self.total_consumption_kwh,
            'energy_charge_usd': self.energy_charge_usd,
        }


class Demand15Min(db.Model):
    """15分钟需量数据点"""
    __tablename__ = 'demand_15min'
    
    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey('hosting_sites.id'), nullable=False)
    zone_id = db.Column(db.Integer, db.ForeignKey('zones.id'), nullable=True)
    window_start = db.Column(db.DateTime, nullable=False)
    window_end = db.Column(db.DateTime, nullable=False)
    avg_power_kw = db.Column(db.Float, default=0)
    max_power_kw = db.Column(db.Float, default=0)
    min_power_kw = db.Column(db.Float, default=0)
    sample_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    site = db.relationship('HostingSite', backref=db.backref('demand_15min_records', lazy='dynamic'))
    zone = db.relationship('Zone', backref=db.backref('demand_15min_records', lazy='dynamic'))
    
    __table_args__ = (
        db.Index('ix_demand_15min_site_window', 'site_id', 'window_start'),
        db.UniqueConstraint('site_id', 'zone_id', 'window_start', name='uq_demand_15min_site_zone_window'),
    )


class CommandApproval(db.Model):
    """命令审批记录 - 支持单人/二人审批"""
    __tablename__ = 'command_approvals'
    
    id = db.Column(db.Integer, primary_key=True)
    approval_id = db.Column(db.String(50), unique=True, nullable=False, default=lambda: f"apr_{uuid.uuid4().hex[:8]}")
    command_id = db.Column(db.Text, nullable=False)
    approver_user_id = db.Column(db.Integer, db.ForeignKey('user_access.id'), nullable=False)
    decision = db.Column(db.String(20), nullable=False)
    reason = db.Column(db.Text)
    step = db.Column(db.Integer, default=1)
    decided_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    approver = db.relationship('UserAccess', backref=db.backref('command_approvals_made', lazy='dynamic'))
    
    def to_dict(self):
        return {
            'id': self.id,
            'approval_id': self.approval_id,
            'command_id': self.command_id,
            'approver_user_id': self.approver_user_id,
            'decision': self.decision,
            'reason': self.reason,
            'step': self.step,
            'decided_at': self.decided_at.isoformat() if self.decided_at else None,
        }


class CommandTarget(db.Model):
    """命令目标 - 支持批量命令"""
    __tablename__ = 'command_targets'
    
    id = db.Column(db.Integer, primary_key=True)
    command_id = db.Column(db.Text, nullable=False)
    asset_id = db.Column(db.Integer, db.ForeignKey('cp_miner_assets.id'), nullable=False)
    
    asset = db.relationship('MinerAsset', backref=db.backref('command_targets', lazy='dynamic'))


class RetentionPolicy(db.Model):
    """数据保留策略"""
    __tablename__ = 'retention_policies'
    
    id = db.Column(db.Integer, primary_key=True)
    policy_id = db.Column(db.String(50), unique=True, nullable=False, default=lambda: f"ret_{uuid.uuid4().hex[:8]}")
    name = db.Column(db.String(200), nullable=False)
    audit_days = db.Column(db.Integer, default=365)
    telemetry_days = db.Column(db.Integer, default=365)
    billing_days = db.Column(db.Integer, default=365*3)
    ticket_days = db.Column(db.Integer, default=365*2)
    is_default = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'policy_id': self.policy_id,
            'name': self.name,
            'audit_days': self.audit_days,
            'telemetry_days': self.telemetry_days,
            'billing_days': self.billing_days,
            'ticket_days': self.ticket_days,
            'is_default': self.is_default,
        }


class AuditEvent(db.Model):
    """审计事件 - 不可抵赖的事件记录（带hash链）"""
    __tablename__ = 'audit_events'
    
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.String(50), unique=True, nullable=False, default=lambda: f"evt_{uuid.uuid4().hex[:12]}")
    site_id = db.Column(db.Integer, db.ForeignKey('hosting_sites.id'), nullable=True)
    actor_type = db.Column(db.String(20), nullable=False)
    actor_id = db.Column(db.String(50), nullable=False)
    event_type = db.Column(db.String(100), nullable=False)
    ref_type = db.Column(db.String(50))
    ref_id = db.Column(db.String(50))
    payload_json = db.Column(db.JSON, default=dict)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    prev_hash = db.Column(db.String(64))
    event_hash = db.Column(db.String(64))
    
    site = db.relationship('HostingSite', backref=db.backref('audit_events', lazy='dynamic'))
    
    __table_args__ = (
        db.Index('ix_audit_events_site_type', 'site_id', 'event_type'),
        db.Index('ix_audit_events_created', 'created_at'),
        db.Index('ix_audit_events_ref', 'ref_type', 'ref_id'),
    )
    
    def compute_hash(self):
        """计算事件hash"""
        data = {
            'event_id': self.event_id,
            'site_id': self.site_id,
            'actor_type': self.actor_type,
            'actor_id': self.actor_id,
            'event_type': self.event_type,
            'ref_type': self.ref_type,
            'ref_id': self.ref_id,
            'payload': self.payload_json,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'prev_hash': self.prev_hash,
        }
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
    
    def to_dict(self):
        return {
            'id': self.id,
            'event_id': self.event_id,
            'site_id': self.site_id,
            'actor_type': self.actor_type,
            'actor_id': self.actor_id,
            'event_type': self.event_type,
            'ref_type': self.ref_type,
            'ref_id': self.ref_id,
            'payload': self.payload_json,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'prev_hash': self.prev_hash,
            'event_hash': self.event_hash,
        }


class ApprovalPolicy(db.Model):
    """审批策略配置"""
    __tablename__ = 'approval_policies'
    
    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey('hosting_sites.id'), nullable=True)
    action_type = db.Column(db.String(50))
    risk_tier = db.Column(db.String(20), default='MEDIUM')
    require_approval = db.Column(db.Boolean, default=True)
    require_dual_approval = db.Column(db.Boolean, default=False)
    dual_approval_threshold_count = db.Column(db.Integer, default=100)
    dual_approval_threshold_kw = db.Column(db.Float, default=1000)
    dual_approval_threshold_percent = db.Column(db.Float, default=1.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    site = db.relationship('HostingSite', backref=db.backref('approval_policies', lazy='dynamic'))
    
    def to_dict(self):
        return {
            'id': self.id,
            'site_id': self.site_id,
            'action_type': self.action_type,
            'risk_tier': self.risk_tier,
            'require_approval': self.require_approval,
            'require_dual_approval': self.require_dual_approval,
            'dual_approval_threshold_count': self.dual_approval_threshold_count,
            'dual_approval_threshold_kw': self.dual_approval_threshold_kw,
            'dual_approval_threshold_percent': self.dual_approval_threshold_percent,
        }


def get_approval_requirement(site_id, action_type, target_count=1, est_kw_impact=0):
    """获取审批要求"""
    policy = ApprovalPolicy.query.filter_by(site_id=site_id, action_type=action_type).first()
    if not policy:
        policy = ApprovalPolicy.query.filter_by(site_id=None, action_type=action_type).first()
    if not policy:
        return {'require_approval': True, 'require_dual_approval': False, 'steps_required': 1}
    
    require_dual = policy.require_dual_approval
    if not require_dual:
        if policy.risk_tier == 'HIGH':
            if target_count > policy.dual_approval_threshold_count:
                require_dual = True
            elif est_kw_impact > policy.dual_approval_threshold_kw:
                require_dual = True
    
    return {
        'require_approval': policy.require_approval,
        'require_dual_approval': require_dual,
        'steps_required': 2 if require_dual else 1,
        'risk_tier': policy.risk_tier,
    }
