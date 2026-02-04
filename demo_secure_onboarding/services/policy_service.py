"""
ABAC Policy Service - Attribute-Based Access Control
Implements 5 mandatory isolation rules + centralized policy evaluation
"""
from typing import Dict, Any, Optional, Tuple, List
from sqlalchemy.orm import Session

import sys
sys.path.insert(0, '..')
from ..db import Actor, Site, Miner, Device


ROLE_HIERARCHY = {
    "owner": 4,
    "admin": 3,
    "operator": 2,
    "viewer": 1
}


def get_role_level(role: str) -> int:
    return ROLE_HIERARCHY.get(role, 0)


def evaluate(
    db: Session,
    action: str,
    actor: Actor,
    resource_type: Optional[str] = None,
    resource: Optional[Any] = None,
    resource_tenant_id: Optional[int] = None,
    resource_site_id: Optional[int] = None
) -> Tuple[bool, str]:
    """
    Evaluate ABAC policy for an action.
    
    Actions:
    - READ_SITE, READ_MINER, READ_DEVICE, READ_AUDIT
    - CREATE_SITE, CREATE_MINER, REGISTER_DEVICE
    - REVEAL_CREDENTIAL, CHANGE_MODE, BATCH_MIGRATE, REVOKE_DEVICE
    - DISCOVERY_SCAN, ONBOARD_MINER
    - EDGE_DECRYPT
    - UPDATE_CREDENTIAL
    - APPROVE_CHANGE, EXECUTE_CHANGE
    
    Returns:
        (allow: bool, reason: str)
    """
    if resource:
        if hasattr(resource, 'tenant_id'):
            resource_tenant_id = resource.tenant_id
        if hasattr(resource, 'site_id'):
            resource_site_id = resource.site_id
        elif isinstance(resource, Site) and hasattr(resource, 'id'):
            resource_site_id = resource.id
    
    if resource_tenant_id and actor.tenant_id != resource_tenant_id:
        return False, f"RULE-1 DENY: Tenant isolation - actor.tenant_id={actor.tenant_id} != resource.tenant_id={resource_tenant_id}"
    
    if resource_site_id:
        allowed_sites = actor.allowed_site_ids
        if allowed_sites is not None:
            if resource_site_id not in allowed_sites:
                return False, f"RULE-2 DENY: Site isolation - site_id={resource_site_id} not in actor.allowed_site_ids={allowed_sites}"
    
    sensitive_actions = [
        "REVEAL_CREDENTIAL", "CHANGE_MODE", "CHANGE_SITE_MODE", "BATCH_MIGRATE", 
        "APPROVE_CHANGE", "EXECUTE_CHANGE", "REVOKE_DEVICE"
    ]
    if action in sensitive_actions:
        if actor.role not in ("owner", "admin"):
            return False, f"RULE-3 DENY: Sensitive action '{action}' requires role in [owner, admin], got '{actor.role}'"
    
    operator_actions = ["DISCOVERY_SCAN", "ONBOARD_MINER", "CREATE_MINER", "CREATE_CHANGE_REQUEST"]
    if action in operator_actions:
        if get_role_level(actor.role) < get_role_level("operator"):
            return False, f"RULE-4 DENY: Action '{action}' requires at least operator role, got '{actor.role}'"
    
    return True, "ALLOW"


def check_device_access(
    db: Session,
    device: Device,
    device_token: str
) -> Tuple[bool, str]:
    """
    RULE-5: Edge decrypt access control
    Device must be ACTIVE and token must match
    """
    if device.status != "ACTIVE":
        return False, "RULE-5 DENY: Device is not ACTIVE"
    
    if device.device_token != device_token:
        return False, "RULE-5 DENY: Device token mismatch"
    
    return True, "ALLOW"


def filter_sites_by_abac(db: Session, actor: Actor, sites: List[Site]) -> List[Site]:
    """Filter sites list based on ABAC rules"""
    result = []
    allowed_sites = actor.allowed_site_ids
    
    for site in sites:
        if site.tenant_id != actor.tenant_id:
            continue
        
        if allowed_sites is not None and site.id not in allowed_sites:
            continue
        
        result.append(site)
    
    return result


def filter_miners_by_abac(db: Session, actor: Actor, miners: List[Miner]) -> List[Miner]:
    """Filter miners list based on ABAC rules"""
    result = []
    allowed_sites = actor.allowed_site_ids
    
    for miner in miners:
        if miner.tenant_id != actor.tenant_id:
            continue
        
        if allowed_sites is not None and miner.site_id not in allowed_sites:
            continue
        
        result.append(miner)
    
    return result


def can_approve(requester: Actor, approver: Actor) -> Tuple[bool, str]:
    """
    Check if approver can approve a request from requester.
    Four-Eyes principle: approver != requester
    """
    if requester.id == approver.id:
        return False, "Four-Eyes DENY: Approver cannot be the same as requester"
    
    if approver.role not in ("owner", "admin"):
        return False, f"Four-Eyes DENY: Approver role must be owner/admin, got '{approver.role}'"
    
    return True, "ALLOW"
