"""
智能电力削减管理系统 - 数据库模型
定义系统中使用的数据库表结构
"""
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import JSON
from datetime import datetime
import json
import os

# 使用主应用中的数据库实例
from db import db

class MinerStatus(db.Model):
    """矿机状态模型"""
    __tablename__ = 'miner_status'
    
    id = db.Column(db.Integer, primary_key=True)
    miner_id = db.Column(db.String(50), unique=True, nullable=False)
    ip_address = db.Column(db.String(50), nullable=True)
    model = db.Column(db.String(50), nullable=True)
    status = db.Column(db.String(20), default='unknown', nullable=False) # running, shutdown, unknown
    category = db.Column(db.String(1), default='D', nullable=False) # A, B, C, D
    hashrate = db.Column(db.Float, default=0.0, nullable=False)
    power = db.Column(db.Float, default=0.0, nullable=False)
    temperature = db.Column(db.Float, default=0.0, nullable=False)
    fan_speed = db.Column(db.Integer, default=0, nullable=False)
    error_rate = db.Column(db.Float, default=0.0, nullable=False)
    health_score = db.Column(db.Float, default=0.0, nullable=False)
    efficiency = db.Column(db.Float, default=0.0, nullable=False)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    extra_data = db.Column(JSON, nullable=True)
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'miner_id': self.miner_id,
            'ip_address': self.ip_address,
            'model': self.model,
            'status': self.status,
            'category': self.category,
            'hashrate': self.hashrate,
            'power': self.power,
            'temperature': self.temperature,
            'fan_speed': self.fan_speed,
            'error_rate': self.error_rate,
            'health_score': self.health_score,
            'efficiency': self.efficiency,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'extra_data': self.extra_data
        }
    
    def __repr__(self):
        return f'<MinerStatus {self.miner_id}>'

class MinerOperation(db.Model):
    """矿机操作记录模型"""
    __tablename__ = 'miner_operations'
    
    id = db.Column(db.Integer, primary_key=True)
    miner_id = db.Column(db.String(50), nullable=False)
    operation_type = db.Column(db.String(20), nullable=False) # shutdown, startup, rotate
    operation_time = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    operator = db.Column(db.String(50), default='system', nullable=False)
    reason = db.Column(db.String(200), nullable=True)
    status = db.Column(db.String(20), default='success', nullable=False) # success, failed
    details = db.Column(JSON, nullable=True)
    
    def to_dict(self):
        """转换为字典"""
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
    
    def __repr__(self):
        return f'<MinerOperation {self.id}: {self.operation_type} on {self.miner_id}>'

class PowerReductionPlan(db.Model):
    """电力削减计划模型"""
    __tablename__ = 'power_reduction_plans'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    reduction_percentage = db.Column(db.Float, default=10.0, nullable=False)
    miner_categories = db.Column(db.String(10), default='DCBA', nullable=False) # 关停优先级
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    created_by = db.Column(db.String(50), default='system', nullable=False)
    is_active = db.Column(db.Boolean, default=False, nullable=False)
    execution_count = db.Column(db.Integer, default=0, nullable=False)
    last_executed = db.Column(db.DateTime, nullable=True)
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'name': self.name,
            'reduction_percentage': self.reduction_percentage,
            'miner_categories': self.miner_categories,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'created_by': self.created_by,
            'is_active': self.is_active,
            'execution_count': self.execution_count,
            'last_executed': self.last_executed.isoformat() if self.last_executed else None
        }
    
    def __repr__(self):
        return f'<PowerReductionPlan {self.id}: {self.name} ({self.reduction_percentage}%)>'

class RotationSchedule(db.Model):
    """矿机轮换计划模型"""
    __tablename__ = 'rotation_schedules'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    miner_category = db.Column(db.String(1), default='C', nullable=False) # 轮换的矿机类别
    days_between_rotation = db.Column(db.Integer, default=14, nullable=False)
    next_rotation_date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    created_by = db.Column(db.String(50), default='system', nullable=False)
    is_active = db.Column(db.Boolean, default=False, nullable=False)
    execution_count = db.Column(db.Integer, default=0, nullable=False)
    last_executed = db.Column(db.DateTime, nullable=True)
    miners_to_shutdown = db.Column(JSON, nullable=True) # 计划关停的矿机ID列表
    miners_to_start = db.Column(JSON, nullable=True) # 计划启动的矿机ID列表
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'name': self.name,
            'miner_category': self.miner_category,
            'days_between_rotation': self.days_between_rotation,
            'next_rotation_date': self.next_rotation_date.isoformat() if self.next_rotation_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'created_by': self.created_by,
            'is_active': self.is_active,
            'execution_count': self.execution_count,
            'last_executed': self.last_executed.isoformat() if self.last_executed else None,
            'miners_to_shutdown': self.miners_to_shutdown,
            'miners_to_start': self.miners_to_start
        }
    
    def __repr__(self):
        return f'<RotationSchedule {self.id}: {self.name} (every {self.days_between_rotation} days)>'

class PerformanceSnapshot(db.Model):
    """系统性能快照模型"""
    __tablename__ = 'performance_snapshots'
    
    id = db.Column(db.Integer, primary_key=True)
    snapshot_date = db.Column(db.Date, nullable=False, unique=True)
    total_miners = db.Column(db.Integer, default=0, nullable=False)
    running_miners = db.Column(db.Integer, default=0, nullable=False)
    shutdown_miners = db.Column(db.Integer, default=0, nullable=False)
    total_hashrate = db.Column(db.Float, default=0.0, nullable=False) # TH/s
    total_power = db.Column(db.Float, default=0.0, nullable=False) # W
    category_stats = db.Column(JSON, nullable=True)
    effective_power_reduction = db.Column(db.Float, default=0.0, nullable=False) # %
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'snapshot_date': self.snapshot_date.isoformat() if self.snapshot_date else None,
            'total_miners': self.total_miners,
            'running_miners': self.running_miners,
            'shutdown_miners': self.shutdown_miners,
            'total_hashrate': self.total_hashrate,
            'total_power': self.total_power,
            'category_stats': self.category_stats,
            'effective_power_reduction': self.effective_power_reduction,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f'<PerformanceSnapshot {self.id}: {self.snapshot_date}>'