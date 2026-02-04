"""
Approval Service - Guarded Approval Workflow Implementation
Handles Change Requests with Four-Eyes principle and controlled execution
"""
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple, List
from sqlalchemy.orm import Session

import sys
sys.path.insert(0, '..')
from demo_secure_onboarding.db import ChangeRequest, Actor, Site, Miner, Device
from .policy_service import evaluate, can_approve
from .audit_service import log_audit_event

CR_EXPIRY_MINUTES = 30


def create_change_request(
    db: Session,
    tenant_id: int,
    requester: Actor,
    request_type: str,
    target_type: str,
    target_id: int,
    requested_action: Dict,
    reason: str,
    site_id: Optional[int] = None
) -> Tuple[Optional[ChangeRequest], str]:
    """
    Create a new Change Request for high-risk operation.
    Anyone with at least operator role can CREATE a request, 
    but only owner/admin can APPROVE and EXECUTE.
    
    Request types:
    - REVEAL_CREDENTIAL
    - CHANGE_SITE_MODE
    - BATCH_MIGRATE
    - DEVICE_REVOKE
    - UPDATE_CREDENTIAL
    """
    allowed, deny_reason = evaluate(
        db, 
        action="CREATE_CHANGE_REQUEST",
        actor=requester,
        resource_tenant_id=tenant_id,
        resource_site_id=site_id
    )
    
    if not allowed:
        log_audit_event(
            db, tenant_id, "POLICY_DENY",
            actor_id=requester.id,
            actor_name=requester.actor_name,
            role=requester.role,
            site_id=site_id,
            target_type=target_type,
            target_id=target_id,
            detail={"action": "CREATE_CHANGE_REQUEST", "reason": deny_reason}
        )
        return None, deny_reason
    
    expires_at = datetime.utcnow() + timedelta(minutes=CR_EXPIRY_MINUTES)
    
    cr = ChangeRequest(
        tenant_id=tenant_id,
        site_id=site_id,
        request_type=request_type,
        target_type=target_type,
        target_id=target_id,
        requested_action_json=json.dumps(requested_action),
        reason=reason,
        status="PENDING",
        requester_actor_id=requester.id,
        expires_at=expires_at
    )
    
    db.add(cr)
    db.commit()
    db.refresh(cr)
    
    event_type = f"{request_type}_REQUEST"
    log_audit_event(
        db, tenant_id, event_type,
        actor_id=requester.id,
        actor_name=requester.actor_name,
        role=requester.role,
        site_id=site_id,
        target_type=target_type,
        target_id=target_id,
        detail={"cr_id": cr.id, "reason": reason, "action": requested_action}
    )
    
    return cr, "Change request created"


def approve_change_request(
    db: Session,
    cr: ChangeRequest,
    approver: Actor
) -> Tuple[bool, str]:
    """
    Approve a pending Change Request.
    Four-Eyes: approver must be different from requester.
    Re-validates ABAC against current resource state (not stale CR data).
    """
    if cr.status != "PENDING":
        return False, f"Cannot approve: CR status is {cr.status}"
    
    if cr.expires_at and datetime.utcnow() > cr.expires_at:
        cr.status = "EXPIRED"
        db.commit()
        return False, "Cannot approve: CR has expired"
    
    requester = db.query(Actor).filter(Actor.id == cr.requester_actor_id).first()
    if not requester:
        return False, "Cannot find requester"
    
    can_do, reason = can_approve(requester, approver)
    if not can_do:
        log_audit_event(
            db, cr.tenant_id, "POLICY_DENY",
            actor_id=approver.id,
            actor_name=approver.actor_name,
            role=approver.role,
            site_id=cr.site_id,
            target_type="change_request",
            target_id=cr.id,
            detail={"action": "APPROVE_CHANGE", "reason": reason}
        )
        return False, reason
    
    resource_tenant_id = None
    resource_site_id = None
    
    if cr.target_type == "miner":
        miner = db.query(Miner).filter(Miner.id == cr.target_id).first()
        if not miner:
            return False, "Target miner no longer exists"
        resource_tenant_id = miner.tenant_id
        resource_site_id = miner.site_id
    elif cr.target_type == "site":
        site = db.query(Site).filter(Site.id == cr.target_id).first()
        if not site:
            return False, "Target site no longer exists"
        resource_tenant_id = site.tenant_id
        resource_site_id = site.id
    else:
        resource_tenant_id = cr.tenant_id
        resource_site_id = cr.site_id
    
    allowed, deny_reason = evaluate(
        db,
        action="APPROVE_CHANGE",
        actor=approver,
        resource_tenant_id=resource_tenant_id,
        resource_site_id=resource_site_id
    )
    
    if not allowed:
        log_audit_event(
            db, cr.tenant_id, "POLICY_DENY",
            actor_id=approver.id,
            actor_name=approver.actor_name,
            role=approver.role,
            site_id=resource_site_id,
            target_type="change_request",
            target_id=cr.id,
            detail={"action": "APPROVE_CHANGE", "reason": deny_reason}
        )
        return False, deny_reason
    
    cr.status = "APPROVED"
    cr.approver_actor_id = approver.id
    db.commit()
    
    log_audit_event(
        db, cr.tenant_id, f"{cr.request_type}_APPROVE",
        actor_id=approver.id,
        actor_name=approver.actor_name,
        role=approver.role,
        site_id=cr.site_id,
        target_type="change_request",
        target_id=cr.id,
        detail={"cr_id": cr.id, "request_type": cr.request_type}
    )
    
    return True, "Approved"


def reject_change_request(
    db: Session,
    cr: ChangeRequest,
    actor: Actor,
    reject_reason: str
) -> Tuple[bool, str]:
    """Reject a pending Change Request"""
    if cr.status != "PENDING":
        return False, f"Cannot reject: CR status is {cr.status}"
    
    cr.status = "REJECTED"
    cr.execution_result_json = json.dumps({"reject_reason": reject_reason})
    db.commit()
    
    log_audit_event(
        db, cr.tenant_id, f"{cr.request_type}_REJECT",
        actor_id=actor.id,
        actor_name=actor.actor_name,
        role=actor.role,
        site_id=cr.site_id,
        target_type="change_request",
        target_id=cr.id,
        detail={"cr_id": cr.id, "reject_reason": reject_reason}
    )
    
    return True, "Rejected"


def check_cr_expiry(cr: ChangeRequest) -> bool:
    """Check if CR is expired"""
    if cr.expires_at and datetime.utcnow() > cr.expires_at:
        return True
    return False


def get_pending_changes(db: Session, tenant_id: int, site_id: Optional[int] = None) -> List[ChangeRequest]:
    """Get pending change requests"""
    query = db.query(ChangeRequest).filter(
        ChangeRequest.tenant_id == tenant_id,
        ChangeRequest.status == "PENDING"
    )
    if site_id:
        query = query.filter(ChangeRequest.site_id == site_id)
    
    return query.order_by(ChangeRequest.created_at.desc()).all()


def get_all_changes(
    db: Session, 
    tenant_id: int, 
    site_id: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = 50
) -> List[ChangeRequest]:
    """Get all change requests with optional filters"""
    query = db.query(ChangeRequest).filter(ChangeRequest.tenant_id == tenant_id)
    
    if site_id:
        query = query.filter(ChangeRequest.site_id == site_id)
    if status:
        query = query.filter(ChangeRequest.status == status)
    
    return query.order_by(ChangeRequest.created_at.desc()).limit(limit).all()
