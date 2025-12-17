"""
Remote Miner Control Models
命令队列和执行结果数据模型
"""
from datetime import datetime
from db import db
import enum
import uuid


class CommandType(enum.Enum):
    """Remote command types"""
    REBOOT = "REBOOT"
    POWER_MODE = "POWER_MODE"
    CHANGE_POOL = "CHANGE_POOL"
    SET_FREQ = "SET_FREQ"
    THERMAL_POLICY = "THERMAL_POLICY"
    LED = "LED"


class TargetScope(enum.Enum):
    """Command target scope"""
    MINER = "MINER"
    GROUP = "GROUP"
    SITE = "SITE"


class CommandStatus(enum.Enum):
    """Command lifecycle status"""
    PENDING = "PENDING"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


class ResultStatus(enum.Enum):
    """Per-miner execution result status"""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class RemoteCommand(db.Model):
    """Remote miner control command"""
    __tablename__ = 'remote_commands'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = db.Column(db.Integer, db.ForeignKey('user_access.id'), nullable=False)
    site_id = db.Column(db.Integer, db.ForeignKey('hosting_sites.id'), nullable=False)
    requested_by_user_id = db.Column(db.Integer, db.ForeignKey('user_access.id'), nullable=False)
    requested_by_role = db.Column(db.String(50), default='user', nullable=False)
    command_type = db.Column(db.String(50), nullable=False)
    payload_json = db.Column(db.JSON, nullable=False, default=dict)
    target_scope = db.Column(db.String(20), default='MINER', nullable=False)
    target_ids = db.Column(db.JSON, nullable=False, default=list)
    status = db.Column(db.String(30), default='PENDING', nullable=False)
    require_approval = db.Column(db.Boolean, default=False, nullable=False)
    approved_by_user_id = db.Column(db.Integer, db.ForeignKey('user_access.id'), nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)
    idempotency_key = db.Column(db.String(255), nullable=True)
    expires_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    tenant = db.relationship('UserAccess', foreign_keys=[tenant_id], backref='remote_commands_tenant')
    requested_by = db.relationship('UserAccess', foreign_keys=[requested_by_user_id], backref='remote_commands_requested')
    approved_by = db.relationship('UserAccess', foreign_keys=[approved_by_user_id], backref='remote_commands_approved')
    site = db.relationship('HostingSite', backref='remote_commands')
    results = db.relationship('RemoteCommandResult', backref='command', lazy='dynamic', cascade='all, delete-orphan')
    
    def is_terminal(self):
        """Check if command is in a terminal state"""
        return self.status in ('SUCCEEDED', 'FAILED', 'CANCELLED', 'EXPIRED')
    
    def can_cancel(self):
        """Check if command can be cancelled"""
        return self.status in ('PENDING', 'PENDING_APPROVAL', 'QUEUED')
    
    def get_result_summary(self):
        """Get aggregated result counts"""
        results = self.results.all()
        return {
            'total': len(results),
            'succeeded': sum(1 for r in results if r.result_status == 'SUCCEEDED'),
            'failed': sum(1 for r in results if r.result_status == 'FAILED'),
            'pending': sum(1 for r in results if r.result_status in ('PENDING', 'RUNNING')),
            'skipped': sum(1 for r in results if r.result_status == 'SKIPPED'),
        }
    
    def to_dict(self, include_results=False):
        result = {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'site_id': self.site_id,
            'requested_by_user_id': self.requested_by_user_id,
            'requested_by_role': self.requested_by_role,
            'command_type': self.command_type,
            'payload': self.payload_json,
            'target_scope': self.target_scope,
            'target_ids': self.target_ids,
            'status': self.status,
            'require_approval': self.require_approval,
            'approved_by_user_id': self.approved_by_user_id,
            'approved_at': self.approved_at.isoformat() + 'Z' if self.approved_at else None,
            'expires_at': self.expires_at.isoformat() + 'Z' if self.expires_at else None,
            'created_at': self.created_at.isoformat() + 'Z' if self.created_at else None,
            'updated_at': self.updated_at.isoformat() + 'Z' if self.updated_at else None,
        }
        if include_results:
            result['results'] = [r.to_dict() for r in self.results.all()]
            result['result_summary'] = self.get_result_summary()
        return result
    
    def to_edge_dict(self):
        """Minimal dict for Edge device polling"""
        return {
            'command_id': self.id,
            'command_type': self.command_type,
            'payload': self.payload_json,
            'target_ids': self.target_ids,
            'expires_at': self.expires_at.isoformat() + 'Z' if self.expires_at else None,
        }
    
    def __repr__(self):
        return f"<RemoteCommand {self.id[:8]} {self.command_type} {self.status}>"


class RemoteCommandResult(db.Model):
    """Per-miner execution result for a remote command"""
    __tablename__ = 'remote_command_results'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    command_id = db.Column(db.String(36), db.ForeignKey('remote_commands.id', ondelete='CASCADE'), nullable=False)
    edge_device_id = db.Column(db.Integer, db.ForeignKey('edge_devices.id'), nullable=True)
    miner_id = db.Column(db.String(100), nullable=False)
    started_at = db.Column(db.DateTime, nullable=True)
    finished_at = db.Column(db.DateTime, nullable=True)
    result_status = db.Column(db.String(30), default='PENDING', nullable=False)
    result_message = db.Column(db.Text, nullable=True)
    metrics_json = db.Column(db.JSON, default=dict)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    edge_device = db.relationship('EdgeDevice', backref='command_results')
    
    def to_dict(self):
        return {
            'id': self.id,
            'command_id': self.command_id,
            'edge_device_id': self.edge_device_id,
            'miner_id': self.miner_id,
            'started_at': self.started_at.isoformat() + 'Z' if self.started_at else None,
            'finished_at': self.finished_at.isoformat() + 'Z' if self.finished_at else None,
            'result_status': self.result_status,
            'result_message': self.result_message,
            'metrics': self.metrics_json,
            'created_at': self.created_at.isoformat() + 'Z' if self.created_at else None,
        }
    
    def __repr__(self):
        return f"<RemoteCommandResult {self.id[:8]} miner={self.miner_id} {self.result_status}>"


# Payload schemas for validation
COMMAND_PAYLOAD_SCHEMAS = {
    'REBOOT': {
        'type': 'object',
        'properties': {
            'mode': {'type': 'string', 'enum': ['soft', 'hard']},
        },
        'required': ['mode'],
    },
    'POWER_MODE': {
        'type': 'object',
        'properties': {
            'mode': {'type': 'string', 'enum': ['high', 'normal', 'eco']},
        },
        'required': ['mode'],
    },
    'CHANGE_POOL': {
        'type': 'object',
        'properties': {
            'pool_url': {'type': 'string'},
            'worker_name': {'type': 'string'},
            'password': {'type': 'string'},
        },
        'required': ['pool_url', 'worker_name'],
    },
    'SET_FREQ': {
        'type': 'object',
        'properties': {
            'frequency_mhz': {'type': 'integer', 'minimum': 100, 'maximum': 1000},
            'profile': {'type': 'string', 'enum': ['stock', 'overclock', 'underclock']},
        },
    },
    'THERMAL_POLICY': {
        'type': 'object',
        'properties': {
            'fan_mode': {'type': 'string', 'enum': ['auto', 'manual', 'aggressive']},
            'fan_speed_pct': {'type': 'integer', 'minimum': 0, 'maximum': 100},
            'temp_warning_c': {'type': 'integer', 'minimum': 50, 'maximum': 100},
            'temp_critical_c': {'type': 'integer', 'minimum': 60, 'maximum': 110},
        },
    },
    'LED': {
        'type': 'object',
        'properties': {
            'state': {'type': 'string', 'enum': ['on', 'off']},
        },
        'required': ['state'],
    },
}
