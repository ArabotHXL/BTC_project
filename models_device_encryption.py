"""
Device Envelope Encryption Models
X25519 Sealed Box + AES-256-GCM for miner credential management
"""
from datetime import datetime
from db import db
import enum


class DeviceStatus(enum.Enum):
    """Edge device status"""
    ACTIVE = "ACTIVE"
    REVOKED = "REVOKED"
    PENDING = "PENDING"


class CapabilityLevel(enum.Enum):
    """Miner capability levels"""
    DISCOVERY = 1
    TELEMETRY = 2
    CONTROL = 3


class EdgeDevice(db.Model):
    """Edge Collector device with X25519 public key"""
    __tablename__ = 'edge_devices'
    
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('user_access.id'), nullable=False)
    site_id = db.Column(db.Integer, db.ForeignKey('hosting_sites.id'), nullable=True)
    zone_id = db.Column(db.Integer, nullable=True)
    device_name = db.Column(db.String(200), nullable=False)
    device_token = db.Column(db.String(512), unique=True, nullable=True)
    token_hash = db.Column(db.String(64), unique=True, nullable=True, index=True)
    public_key = db.Column(db.Text, nullable=False)
    key_version = db.Column(db.Integer, default=1, nullable=False)
    status = db.Column(db.String(20), default='ACTIVE', nullable=False)
    last_seen_at = db.Column(db.DateTime, nullable=True)
    revoked_at = db.Column(db.DateTime, nullable=True)
    revoked_by = db.Column(db.Integer, db.ForeignKey('user_access.id'), nullable=True)
    hmac_secret = db.Column(db.String(64), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    tenant = db.relationship('UserAccess', foreign_keys=[tenant_id], backref='edge_devices')
    site = db.relationship('HostingSite', backref='edge_devices')
    secrets = db.relationship('MinerSecret', backref='device', lazy='dynamic')
    
    def is_active(self):
        return self.status == 'ACTIVE'
    
    def to_dict(self, include_pubkey=False):
        result = {
            'id': self.id,
            'device_name': self.device_name,
            'site_id': self.site_id,
            'zone_id': self.zone_id,
            'key_version': self.key_version,
            'status': self.status,
            'last_seen_at': self.last_seen_at.isoformat() if self.last_seen_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
        if include_pubkey:
            result['public_key'] = self.public_key
        return result
    
    def __repr__(self):
        return f"<EdgeDevice {self.device_name} ({self.status})>"


class MinerSecret(db.Model):
    """Encrypted miner credentials using device envelope encryption"""
    __tablename__ = 'miner_secrets'
    
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('user_access.id'), nullable=False)
    device_id = db.Column(db.Integer, db.ForeignKey('edge_devices.id'), nullable=False)
    miner_id = db.Column(db.Integer, db.ForeignKey('hosting_miners.id'), nullable=False)
    encrypted_payload = db.Column(db.Text, nullable=False)
    wrapped_dek = db.Column(db.Text, nullable=False)
    nonce = db.Column(db.String(64), nullable=False)
    aad = db.Column(db.JSON, nullable=False)
    counter = db.Column(db.Integer, default=1, nullable=False)
    schema_version = db.Column(db.Integer, default=1, nullable=False)
    key_version = db.Column(db.Integer, default=1, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    tenant = db.relationship('UserAccess', backref='miner_secrets')
    miner = db.relationship('HostingMiner', backref='secrets')
    
    __table_args__ = (
        db.UniqueConstraint('miner_id', 'device_id', name='uq_miner_device'),
    )
    
    def to_dict(self, include_encrypted=True):
        result = {
            'id': self.id,
            'miner_id': self.miner_id,
            'device_id': self.device_id,
            'counter': self.counter,
            'schema_version': self.schema_version,
            'key_version': self.key_version,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_encrypted:
            result['encrypted_payload'] = self.encrypted_payload
            result['wrapped_dek'] = self.wrapped_dek
            result['nonce'] = self.nonce
            result['aad'] = self.aad
        return result
    
    def __repr__(self):
        return f"<MinerSecret miner={self.miner_id} counter={self.counter}>"


class DeviceAuditEvent(db.Model):
    """Security audit log for device operations"""
    __tablename__ = 'device_audit_events'
    
    id = db.Column(db.Integer, primary_key=True)
    event_type = db.Column(db.String(50), nullable=False)
    tenant_id = db.Column(db.Integer, db.ForeignKey('user_access.id'), nullable=True)
    device_id = db.Column(db.Integer, db.ForeignKey('edge_devices.id'), nullable=True)
    miner_id = db.Column(db.Integer, db.ForeignKey('hosting_miners.id'), nullable=True)
    actor_id = db.Column(db.Integer, db.ForeignKey('user_access.id'), nullable=True)
    actor_type = db.Column(db.String(20), default='user')
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.Text, nullable=True)
    event_data = db.Column(db.JSON, nullable=True)
    result = db.Column(db.String(20), default='success')
    error_message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    @classmethod
    def log(cls, event_type, tenant_id=None, device_id=None, miner_id=None, 
            actor_id=None, actor_type='user', ip_address=None, user_agent=None,
            event_data=None, result='success', error_message=None):
        """Create and save an audit event"""
        event = cls(
            event_type=event_type,
            tenant_id=tenant_id,
            device_id=device_id,
            miner_id=miner_id,
            actor_id=actor_id,
            actor_type=actor_type,
            ip_address=ip_address,
            user_agent=user_agent,
            event_data=event_data,
            result=result,
            error_message=error_message
        )
        db.session.add(event)
        db.session.commit()
        return event
    
    def __repr__(self):
        return f"<DeviceAuditEvent {self.event_type} device={self.device_id}>"


class IPScanJob(db.Model):
    """Network IP range scan job for miner discovery"""
    __tablename__ = 'ip_scan_jobs'
    
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('user_access.id'), nullable=False)
    site_id = db.Column(db.Integer, db.ForeignKey('hosting_sites.id'), nullable=True)
    device_id = db.Column(db.Integer, db.ForeignKey('edge_devices.id'), nullable=True)
    ip_range_start = db.Column(db.String(45), nullable=False)
    ip_range_end = db.Column(db.String(45), nullable=False)
    scan_type = db.Column(db.String(30), default='DISCOVERY')
    status = db.Column(db.String(20), default='PENDING')
    total_ips = db.Column(db.Integer, default=0)
    scanned_ips = db.Column(db.Integer, default=0)
    discovered_miners = db.Column(db.Integer, default=0)
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    error_message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    tenant = db.relationship('UserAccess', backref='scan_jobs')
    site = db.relationship('HostingSite', backref='scan_jobs')
    device = db.relationship('EdgeDevice', backref='scan_jobs')
    discovered = db.relationship('DiscoveredMiner', backref='scan_job', lazy='dynamic', cascade='all, delete-orphan')
    
    @property
    def progress_percent(self):
        if self.total_ips == 0:
            return 0
        return round(self.scanned_ips / self.total_ips * 100, 1)
    
    def to_dict(self):
        return {
            'id': self.id,
            'site_id': self.site_id,
            'ip_range_start': self.ip_range_start,
            'ip_range_end': self.ip_range_end,
            'scan_type': self.scan_type,
            'status': self.status,
            'total_ips': self.total_ips,
            'scanned_ips': self.scanned_ips,
            'discovered_miners': self.discovered_miners,
            'progress_percent': self.progress_percent,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
    
    def __repr__(self):
        return f"<IPScanJob {self.ip_range_start}-{self.ip_range_end} ({self.status})>"


class DiscoveredMiner(db.Model):
    """Miners discovered during network scan, pending user confirmation"""
    __tablename__ = 'discovered_miners'
    
    id = db.Column(db.Integer, primary_key=True)
    scan_job_id = db.Column(db.Integer, db.ForeignKey('ip_scan_jobs.id', ondelete='CASCADE'), nullable=False)
    tenant_id = db.Column(db.Integer, db.ForeignKey('user_access.id'), nullable=False)
    ip_address = db.Column(db.String(45), nullable=False)
    api_port = db.Column(db.Integer, default=4028)
    detected_model = db.Column(db.String(100), nullable=True)
    detected_firmware = db.Column(db.String(100), nullable=True)
    detected_hashrate_ghs = db.Column(db.Float, nullable=True)
    mac_address = db.Column(db.String(20), nullable=True)
    hostname = db.Column(db.String(200), nullable=True)
    is_imported = db.Column(db.Boolean, default=False)
    imported_miner_id = db.Column(db.Integer, db.ForeignKey('hosting_miners.id'), nullable=True)
    raw_response = db.Column(db.JSON, nullable=True)
    discovered_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'ip_address': self.ip_address,
            'api_port': self.api_port,
            'detected_model': self.detected_model,
            'detected_firmware': self.detected_firmware,
            'detected_hashrate_ghs': self.detected_hashrate_ghs,
            'mac_address': self.mac_address,
            'hostname': self.hostname,
            'is_imported': self.is_imported,
            'imported_miner_id': self.imported_miner_id,
            'discovered_at': self.discovered_at.isoformat() if self.discovered_at else None,
        }
    
    def __repr__(self):
        return f"<DiscoveredMiner {self.ip_address} model={self.detected_model}>"
