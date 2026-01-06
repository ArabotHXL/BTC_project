"""
SQLite Database Models for HashInsight Secure Miner Onboarding Demo
7 tables: tenants, actors, sites, miners, devices, change_requests, audit_events
"""
import os
import json
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

DATABASE_URL = os.getenv("DEMO_DATABASE_URL", "sqlite:///./demo_secure.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class Tenant(Base):
    __tablename__ = "tenants"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    sites = relationship("Site", back_populates="tenant")
    actors = relationship("Actor", back_populates="tenant")


class Actor(Base):
    """ABAC Actor model - represents users with attributes for access control"""
    __tablename__ = "actors"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    actor_name = Column(String(100), nullable=False)
    role = Column(String(20), nullable=False, default="viewer")  # owner/admin/operator/viewer
    allowed_site_ids_json = Column(Text, default="[]")  # JSON list of site IDs
    attributes_json = Column(Text, default="{}")  # department, region, clearance, etc.
    api_token = Column(String(64), unique=True, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    tenant = relationship("Tenant", back_populates="actors")
    
    @property
    def allowed_site_ids(self):
        try:
            return json.loads(self.allowed_site_ids_json or "[]")
        except:
            return []
    
    @allowed_site_ids.setter
    def allowed_site_ids(self, value):
        self.allowed_site_ids_json = json.dumps(value)
    
    @property
    def attributes(self):
        try:
            return json.loads(self.attributes_json or "{}")
        except:
            return {}


class Site(Base):
    __tablename__ = "sites"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    name = Column(String(100), nullable=False)
    ip_mode = Column(Integer, default=1)  # 1=UI Masking, 2=Server Envelope, 3=Device E2EE
    site_dek_wrapped = Column(Text, nullable=True)  # Mode 2: wrapped DEK
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    tenant = relationship("Tenant", back_populates="sites")
    miners = relationship("Miner", back_populates="site")
    devices = relationship("Device", back_populates="site")


class Miner(Base):
    __tablename__ = "miners"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=False)
    name = Column(String(100), nullable=False)
    credential_value = Column(Text, nullable=True)  # plain JSON or ENC:... or E2EE:...
    credential_mode = Column(Integer, default=1)  # 1/2/3
    fingerprint = Column(String(64), nullable=True)
    last_accepted_counter = Column(Integer, default=0)  # anti-rollback
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    site = relationship("Site", back_populates="miners")


class Device(Base):
    """Edge Device for Mode 3 E2EE"""
    __tablename__ = "devices"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=False)
    device_name = Column(String(100), nullable=False)
    public_key_b64 = Column(Text, nullable=False)
    secret_key_b64 = Column(Text, nullable=True)  # DEMO ONLY - production禁用
    device_token = Column(String(64), unique=True, nullable=False)
    status = Column(String(20), default="ACTIVE")  # ACTIVE/REVOKED
    created_at = Column(DateTime, default=datetime.utcnow)
    
    site = relationship("Site", back_populates="devices")


class ChangeRequest(Base):
    """Guarded Approval workflow - Change Requests for high-risk operations"""
    __tablename__ = "change_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=True)
    request_type = Column(String(50), nullable=False)  # REVEAL_CREDENTIAL, CHANGE_SITE_MODE, BATCH_MIGRATE, DEVICE_REVOKE, UPDATE_CREDENTIAL
    target_type = Column(String(50), nullable=True)  # site/miner/device
    target_id = Column(Integer, nullable=True)
    requested_action_json = Column(Text, nullable=False)  # action details
    reason = Column(Text, nullable=False)
    status = Column(String(20), default="PENDING")  # DRAFT/PENDING/APPROVED/EXECUTED/REJECTED/EXPIRED
    requester_actor_id = Column(Integer, ForeignKey("actors.id"), nullable=False)
    approver_actor_id = Column(Integer, ForeignKey("actors.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    executed_at = Column(DateTime, nullable=True)
    execution_result_json = Column(Text, nullable=True)
    
    requester = relationship("Actor", foreign_keys=[requester_actor_id])
    approver = relationship("Actor", foreign_keys=[approver_actor_id])


class AuditEvent(Base):
    """Immutable audit log with hash chain"""
    __tablename__ = "audit_events"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=True)
    actor_id = Column(Integer, nullable=True)
    actor_name = Column(String(100), nullable=True)
    role = Column(String(20), nullable=True)
    event_type = Column(String(50), nullable=False)
    target_type = Column(String(50), nullable=True)
    target_id = Column(Integer, nullable=True)
    detail_json = Column(Text, nullable=True)
    prev_hash = Column(String(64), nullable=True)
    event_hash = Column(String(64), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


def init_db():
    Base.metadata.create_all(bind=engine)


def get_session():
    return SessionLocal()
