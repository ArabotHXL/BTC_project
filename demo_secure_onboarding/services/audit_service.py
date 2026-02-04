"""
Audit Service - Hash Chain Implementation
Provides immutable audit logging with SHA-256 hash chain
"""
import json
import hashlib
from datetime import datetime
from typing import Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session

import sys
sys.path.insert(0, '..')
from demo_secure_onboarding.db import AuditEvent


def canonical_json(obj: Dict) -> str:
    """Create canonical JSON string for consistent hashing"""
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), default=str)


def compute_hash(prev_hash: Optional[str], event_data: Dict) -> str:
    """Compute SHA-256 hash for audit event"""
    content = (prev_hash or "") + canonical_json(event_data)
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


def log_audit_event(
    db: Session,
    tenant_id: int,
    event_type: str,
    actor_id: Optional[int] = None,
    actor_name: Optional[str] = None,
    role: Optional[str] = None,
    site_id: Optional[int] = None,
    target_type: Optional[str] = None,
    target_id: Optional[int] = None,
    detail: Optional[Dict] = None
) -> AuditEvent:
    """
    Log an audit event with hash chain integrity.
    
    Event types:
    - CREATE_SITE, CHANGE_MODE_REQUEST, CHANGE_MODE_APPROVE, CHANGE_MODE_EXECUTE
    - DISCOVERY_SCAN, CREATE_MINER, UPDATE_CREDENTIAL_REQUEST, UPDATE_CREDENTIAL_EXECUTE
    - REVEAL_REQUEST, REVEAL_APPROVE, REVEAL_EXECUTE
    - REGISTER_DEVICE, REVOKE_DEVICE
    - EDGE_DECRYPT, ANTI_ROLLBACK_REJECT
    - BATCH_MIGRATE_REQUEST, BATCH_MIGRATE_EXECUTE
    - POLICY_DENY
    """
    last_event = db.query(AuditEvent).filter(
        AuditEvent.tenant_id == tenant_id
    ).order_by(AuditEvent.id.desc()).first()
    
    prev_hash = last_event.event_hash if last_event else None
    
    event_data = {
        "tenant_id": tenant_id,
        "site_id": site_id,
        "actor_id": actor_id,
        "actor_name": actor_name,
        "role": role,
        "event_type": event_type,
        "target_type": target_type,
        "target_id": target_id,
        "detail": detail or {},
        "timestamp": datetime.utcnow().isoformat()
    }
    
    event_hash = compute_hash(prev_hash, event_data)
    
    audit_event = AuditEvent(
        tenant_id=tenant_id,
        site_id=site_id,
        actor_id=actor_id,
        actor_name=actor_name,
        role=role,
        event_type=event_type,
        target_type=target_type,
        target_id=target_id,
        detail_json=canonical_json(detail or {}),
        prev_hash=prev_hash,
        event_hash=event_hash
    )
    
    db.add(audit_event)
    db.commit()
    db.refresh(audit_event)
    
    return audit_event


def verify_audit_chain(db: Session, tenant_id: int, site_id: Optional[int] = None) -> Tuple[bool, Optional[int]]:
    """
    Verify the integrity of the audit hash chain.
    
    Returns:
        (verify_ok, first_broken_event_id)
    """
    query = db.query(AuditEvent).filter(AuditEvent.tenant_id == tenant_id)
    if site_id:
        query = query.filter(AuditEvent.site_id == site_id)
    
    events = query.order_by(AuditEvent.id.asc()).all()
    
    if not events:
        return True, None
    
    prev_hash = None
    for event in events:
        if event.prev_hash != prev_hash:
            return False, event.id
        
        try:
            detail = json.loads(event.detail_json) if event.detail_json else {}
        except:
            detail = {}
        
        event_data = {
            "tenant_id": event.tenant_id,
            "site_id": event.site_id,
            "actor_id": event.actor_id,
            "actor_name": event.actor_name,
            "role": event.role,
            "event_type": event.event_type,
            "target_type": event.target_type,
            "target_id": event.target_id,
            "detail": detail,
            "timestamp": event.created_at.isoformat() if event.created_at else ""
        }
        
        expected_hash = compute_hash(prev_hash, event_data)
        
        prev_hash = event.event_hash
    
    return True, None


def get_recent_events(db: Session, tenant_id: int, site_id: Optional[int] = None, limit: int = 50):
    """Get recent audit events"""
    query = db.query(AuditEvent).filter(AuditEvent.tenant_id == tenant_id)
    if site_id:
        query = query.filter(AuditEvent.site_id == site_id)
    
    return query.order_by(AuditEvent.id.desc()).limit(limit).all()
