"""
智能电力削减管理系统 - 数据库模型
"""
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import JSON

# 初始化SQLAlchemy，会在应用中绑定
db = SQLAlchemy()

class MinerStatus(db.Model):
    """矿机状态记录模型"""
    __tablename__ = 'miner_status'
    
    id = db.Column(db.Integer, primary_key=True)
    miner_id = db.Column(db.String(100), nullable=False, index=True)
    ip_address = db.Column(db.String(50), nullable=True)
    model = db.Column(db.String(100), nullable=True)
    hashrate = db.Column(db.Float, default=0.0)  # TH/s
    power = db.Column(db.Float, default=0.0)  # W
    temperature = db.Column(db.Float, default=0.0)  # °C
    fan_speed = db.Column(db.Integer, default=0)  # RPM
    error_rate = db.Column(db.Float, default=0.0)  # %
    health_score = db.Column(db.Integer, default=0)  # 0-100
    efficiency = db.Column(db.Float, default=0.0)  # TH/J
    category = db.Column(db.String(1), default='D')  # A, B, C, D
    status = db.Column(db.String(20), default='unknown')  # running, shutdown, unknown
    uptime = db.Column(db.Integer, default=0)  # seconds
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<MinerStatus {self.miner_id} ({self.status})>"
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'miner_id': self.miner_id,
            'ip_address': self.ip_address,
            'model': self.model,
            'hashrate': self.hashrate,
            'power': self.power,
            'temperature': self.temperature,
            'fan_speed': self.fan_speed,
            'error_rate': self.error_rate,
            'health_score': self.health_score,
            'efficiency': self.efficiency,
            'category': self.category,
            'status': self.status,
            'uptime': self.uptime,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None
        }


class MinerOperation(db.Model):
    """矿机操作记录模型"""
    __tablename__ = 'miner_operations'
    
    id = db.Column(db.Integer, primary_key=True)
    miner_id = db.Column(db.String(100), nullable=False, index=True)
    operation_type = db.Column(db.String(20), nullable=False)  # shutdown, startup, rotate
    operation_time = db.Column(db.DateTime, default=datetime.utcnow)
    operator = db.Column(db.String(100), nullable=True)  # 操作人或自动化规则名称
    reason = db.Column(db.String(255), nullable=True)  # 操作原因
    status = db.Column(db.String(20), default='success')  # success, failed
    details = db.Column(db.Text, nullable=True)  # 详细信息JSON
    
    def __repr__(self):
        return f"<MinerOperation {self.operation_type} on {self.miner_id}>"
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'miner_id': self.miner_id,
            'operation_type': self.operation_type,
            'operation_time': self.operation_time.isoformat() if self.operation_time else None,
            'operator': self.operator,
            'reason': self.reason,
            'status': self.status,
            'details': self.details
        }


class PowerReductionPlan(db.Model):
    """电力削减计划模型"""
    __tablename__ = 'power_reduction_plans'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    reduction_percentage = db.Column(db.Float, nullable=False)
    is_active = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    effective_from = db.Column(db.DateTime, nullable=True)
    effective_to = db.Column(db.DateTime, nullable=True)
    created_by = db.Column(db.String(100), nullable=True)
    description = db.Column(db.Text, nullable=True)
    miner_categories = db.Column(db.String(10), default='DCBA')  # 关停顺序，如'DCBA'表示先D再C再B再A
    
    def __repr__(self):
        return f"<PowerReductionPlan {self.name} ({self.reduction_percentage}%)>"
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'name': self.name,
            'reduction_percentage': self.reduction_percentage,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'effective_from': self.effective_from.isoformat() if self.effective_from else None,
            'effective_to': self.effective_to.isoformat() if self.effective_to else None,
            'created_by': self.created_by,
            'description': self.description,
            'miner_categories': self.miner_categories
        }


class RotationSchedule(db.Model):
    """矿机轮换计划模型"""
    __tablename__ = 'rotation_schedules'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    schedule_type = db.Column(db.String(20), default='auto')  # auto, manual
    days_between_rotation = db.Column(db.Integer, default=14)
    next_rotation_date = db.Column(db.DateTime, nullable=True)
    last_rotation_date = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String(100), nullable=True)
    miners_to_shutdown = db.Column(JSON, nullable=True)  # 需要关停的矿机ID列表
    miners_to_start = db.Column(JSON, nullable=True)  # 需要启动的矿机ID列表
    
    def __repr__(self):
        return f"<RotationSchedule {self.name}>"
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'name': self.name,
            'schedule_type': self.schedule_type,
            'days_between_rotation': self.days_between_rotation,
            'next_rotation_date': self.next_rotation_date.isoformat() if self.next_rotation_date else None,
            'last_rotation_date': self.last_rotation_date.isoformat() if self.last_rotation_date else None,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'created_by': self.created_by,
            'miners_to_shutdown': self.miners_to_shutdown,
            'miners_to_start': self.miners_to_start
        }


class PerformanceSnapshot(db.Model):
    """性能快照模型 - 用于存储每日性能数据"""
    __tablename__ = 'performance_snapshots'
    
    id = db.Column(db.Integer, primary_key=True)
    snapshot_date = db.Column(db.Date, nullable=False, index=True)
    total_miners = db.Column(db.Integer, default=0)
    running_miners = db.Column(db.Integer, default=0)
    shutdown_miners = db.Column(db.Integer, default=0)
    total_hashrate = db.Column(db.Float, default=0.0)  # TH/s
    total_power = db.Column(db.Float, default=0.0)  # W
    effective_power_reduction = db.Column(db.Float, default=0.0)  # %
    a_category_count = db.Column(db.Integer, default=0)
    b_category_count = db.Column(db.Integer, default=0)
    c_category_count = db.Column(db.Integer, default=0)
    d_category_count = db.Column(db.Integer, default=0)
    a_shutdown_count = db.Column(db.Integer, default=0)
    b_shutdown_count = db.Column(db.Integer, default=0)
    c_shutdown_count = db.Column(db.Integer, default=0)
    d_shutdown_count = db.Column(db.Integer, default=0)
    
    def __repr__(self):
        return f"<PerformanceSnapshot {self.snapshot_date}>"
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'snapshot_date': self.snapshot_date.isoformat() if self.snapshot_date else None,
            'total_miners': self.total_miners,
            'running_miners': self.running_miners,
            'shutdown_miners': self.shutdown_miners,
            'total_hashrate': self.total_hashrate,
            'total_power': self.total_power,
            'effective_power_reduction': self.effective_power_reduction,
            'a_category_count': self.a_category_count,
            'b_category_count': self.b_category_count,
            'c_category_count': self.c_category_count,
            'd_category_count': self.d_category_count,
            'a_shutdown_count': self.a_shutdown_count,
            'b_shutdown_count': self.b_shutdown_count,
            'c_shutdown_count': self.c_shutdown_count,
            'd_shutdown_count': self.d_shutdown_count
        }


# 用户与权限模型
class PowerUser(db.Model):
    """电力管理系统用户模型"""
    __tablename__ = 'power_users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    role = db.Column(db.String(20), default='viewer')  # admin, operator, viewer
    is_active = db.Column(db.Boolean, default=True)
    last_login = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<PowerUser {self.username}>"