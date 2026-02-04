"""
HashInsight Secure Miner Onboarding Demo
FastAPI Application with ABAC + Guarded Approval

Enterprise-grade security demonstration featuring:
- Three-tier credential protection (Mode 1/2/3)
- ABAC (Attribute-Based Access Control)
- Guarded Approval workflow with Four-Eyes principle
- Immutable audit log with hash chain
- Anti-rollback protection for E2EE credentials
"""
import os
import json
import secrets
import base64
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, Request, Depends, HTTPException, Header
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy.orm import Session

from demo_secure_onboarding.db import (
    init_db, get_db, get_session,
    Tenant, Actor, Site, Miner, Device, ChangeRequest, AuditEvent
)
from demo_secure_onboarding.services.policy_service import (
    evaluate,
    filter_sites_by_abac,
    filter_miners_by_abac,
    check_device_access,
)
from demo_secure_onboarding.services.audit_service import (
    log_audit_event,
    verify_audit_chain,
    get_recent_events,
)
from demo_secure_onboarding.services.credential_service import (
    get_display_credential, store_credential_mode1, store_credential_mode2, 
    store_credential_mode3, reveal_credential_mode1, reveal_credential_mode2,
    reveal_credential_mode3, validate_anti_rollback, migrate_credential
)
from demo_secure_onboarding.services.envelope_kms_service import (
    generate_site_dek,
    wrap_dek,
    compute_fingerprint,
)
from demo_secure_onboarding.services.approval_service import (
    create_change_request, approve_change_request, reject_change_request,
    check_cr_expiry, get_pending_changes, get_all_changes
)
from demo_secure_onboarding.services.discovery_service import (
    simulate_discovery,
    real_discovery,
    create_credential_blob,
)

app = FastAPI(title="HashInsight Secure Miner Onboarding Demo")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

DEMO_ALLOW_STORE_DEVICE_SECRET = os.getenv("DEMO_ALLOW_STORE_DEVICE_SECRET", "true").lower() == "true"


class ActorContext:
    """Actor context for request handling - not a Pydantic model to allow SQLAlchemy objects"""
    def __init__(self):
        self.actor: Optional[Actor] = None
        self.actor_id: Optional[int] = None
        self.actor_name: str = "anonymous"
        self.role: str = "viewer"
        self.tenant_id: Optional[int] = None


async def get_actor_context(
    request: Request,
    x_actor: Optional[str] = Header(None),
    x_role: Optional[str] = Header(None),
    x_tenant: Optional[str] = Header(None),
    x_site: Optional[str] = Header(None),
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> ActorContext:
    """
    Resolve actor from headers or API token.
    Headers: X-Actor, X-Role, X-Tenant, X-Site
    Or: Authorization: Bearer <api_token>
    """
    ctx = ActorContext()
    
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
        actor = db.query(Actor).filter(Actor.api_token == token).first()
        if actor:
            ctx.actor = actor
            ctx.actor_id = actor.id
            ctx.actor_name = actor.actor_name
            ctx.role = actor.role
            ctx.tenant_id = actor.tenant_id
            return ctx
    
    if x_actor:
        ctx.actor_name = x_actor
    
    if x_role and x_role in ("owner", "admin", "operator", "viewer"):
        ctx.role = x_role
    
    if x_tenant:
        try:
            ctx.tenant_id = int(x_tenant)
        except:
            tenant = db.query(Tenant).filter(Tenant.name == x_tenant).first()
            if tenant:
                ctx.tenant_id = tenant.id
    
    if ctx.actor_name and ctx.tenant_id:
        actor = db.query(Actor).filter(
            Actor.actor_name == ctx.actor_name,
            Actor.tenant_id == ctx.tenant_id
        ).first()
        if actor:
            ctx.actor = actor
            ctx.actor_id = actor.id
            ctx.role = actor.role
    
    return ctx


@app.on_event("startup")
async def startup():
    init_db()
    
    db = get_session()
    try:
        if not db.query(Tenant).first():
            tenant = Tenant(name="Demo Mining Corp")
            db.add(tenant)
            db.commit()
            db.refresh(tenant)
            
            owner = Actor(
                tenant_id=tenant.id,
                actor_name="alice_owner",
                role="owner",
                api_token=secrets.token_hex(16)
            )
            admin = Actor(
                tenant_id=tenant.id,
                actor_name="bob_admin",
                role="admin",
                api_token=secrets.token_hex(16)
            )
            operator = Actor(
                tenant_id=tenant.id,
                actor_name="charlie_operator",
                role="operator",
                api_token=secrets.token_hex(16)
            )
            viewer = Actor(
                tenant_id=tenant.id,
                actor_name="dave_viewer",
                role="viewer",
                api_token=secrets.token_hex(16)
            )
            db.add_all([owner, admin, operator, viewer])
            db.commit()
            
            site1 = Site(tenant_id=tenant.id, name="Farm Alpha", ip_mode=1)
            site2 = Site(tenant_id=tenant.id, name="Farm Beta", ip_mode=2)
            dek = generate_site_dek()
            site2.site_dek_wrapped = wrap_dek(dek)
            
            db.add_all([site1, site2])
            db.commit()
            
            for actor in [owner, admin, operator]:
                actor.allowed_site_ids = [site1.id, site2.id]
            viewer.allowed_site_ids = [site1.id]
            db.commit()
            
            print(f"Demo data initialized: Tenant '{tenant.name}' with 2 sites and 4 actors")
    finally:
        db.close()


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/whoami")
async def whoami(ctx: ActorContext = Depends(get_actor_context)):
    """Return current actor context"""
    return {
        "actor_id": ctx.actor_id,
        "actor_name": ctx.actor_name,
        "role": ctx.role,
        "tenant_id": ctx.tenant_id,
        "allowed_site_ids": ctx.actor.allowed_site_ids if ctx.actor else []
    }


@app.get("/api/tenants")
async def list_tenants(db: Session = Depends(get_db)):
    tenants = db.query(Tenant).all()
    return [{"id": t.id, "name": t.name} for t in tenants]


class TenantCreate(BaseModel):
    name: str

@app.post("/api/tenants")
async def create_tenant(
    data: TenantCreate,
    ctx: ActorContext = Depends(get_actor_context),
    db: Session = Depends(get_db)
):
    tenant = Tenant(name=data.name)
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return {"id": tenant.id, "name": tenant.name}


@app.get("/api/actors")
async def list_actors(
    tenant_id: Optional[int] = None,
    ctx: ActorContext = Depends(get_actor_context),
    db: Session = Depends(get_db)
):
    query = db.query(Actor)
    if tenant_id:
        query = query.filter(Actor.tenant_id == tenant_id)
    elif ctx.tenant_id:
        query = query.filter(Actor.tenant_id == ctx.tenant_id)
    
    actors = query.all()
    return [{
        "id": a.id,
        "actor_name": a.actor_name,
        "role": a.role,
        "tenant_id": a.tenant_id,
        "allowed_site_ids": a.allowed_site_ids,
        "api_token": a.api_token if ctx.role in ("owner", "admin") else None
    } for a in actors]


class ActorCreate(BaseModel):
    tenant_id: int
    actor_name: str
    role: str = "viewer"
    allowed_site_ids: List[int] = []
    attributes: Dict[str, Any] = {}

@app.post("/api/actors")
async def create_actor(
    data: ActorCreate,
    ctx: ActorContext = Depends(get_actor_context),
    db: Session = Depends(get_db)
):
    if ctx.role not in ("owner", "admin"):
        raise HTTPException(403, "Only owner/admin can create actors")
    
    actor = Actor(
        tenant_id=data.tenant_id,
        actor_name=data.actor_name,
        role=data.role,
        api_token=secrets.token_hex(16)
    )
    actor.allowed_site_ids = data.allowed_site_ids
    actor.attributes_json = json.dumps(data.attributes)
    
    db.add(actor)
    db.commit()
    db.refresh(actor)
    
    return {
        "id": actor.id,
        "actor_name": actor.actor_name,
        "role": actor.role,
        "api_token": actor.api_token
    }


@app.get("/api/sites")
async def list_sites(
    tenant_id: Optional[int] = None,
    ctx: ActorContext = Depends(get_actor_context),
    db: Session = Depends(get_db)
):
    query = db.query(Site)
    if tenant_id:
        query = query.filter(Site.tenant_id == tenant_id)
    elif ctx.tenant_id:
        query = query.filter(Site.tenant_id == ctx.tenant_id)
    
    sites = query.all()
    
    if ctx.actor:
        sites = filter_sites_by_abac(db, ctx.actor, sites)
    
    return [{
        "id": s.id,
        "name": s.name,
        "tenant_id": s.tenant_id,
        "ip_mode": s.ip_mode,
        "mode_label": {1: "UI Masking", 2: "Server Envelope", 3: "Device E2EE"}.get(s.ip_mode, "Unknown"),
        "has_dek": bool(s.site_dek_wrapped)
    } for s in sites]


class SiteCreate(BaseModel):
    tenant_id: int
    name: str
    ip_mode: int = 1

@app.post("/api/sites")
async def create_site(
    data: SiteCreate,
    ctx: ActorContext = Depends(get_actor_context),
    db: Session = Depends(get_db)
):
    if ctx.role not in ("owner", "admin"):
        raise HTTPException(403, "Only owner/admin can create sites")
    
    site = Site(
        tenant_id=data.tenant_id,
        name=data.name,
        ip_mode=data.ip_mode
    )
    
    if data.ip_mode == 2:
        dek = generate_site_dek()
        site.site_dek_wrapped = wrap_dek(dek)
    
    db.add(site)
    db.commit()
    db.refresh(site)
    
    log_audit_event(
        db, data.tenant_id, "CREATE_SITE",
        actor_id=ctx.actor_id,
        actor_name=ctx.actor_name,
        role=ctx.role,
        site_id=site.id,
        target_type="site",
        target_id=site.id,
        detail={"name": data.name, "ip_mode": data.ip_mode}
    )
    
    return {"id": site.id, "name": site.name, "ip_mode": site.ip_mode}


@app.get("/api/sites/{site_id}/settings")
async def get_site_settings(
    site_id: int,
    ctx: ActorContext = Depends(get_actor_context),
    db: Session = Depends(get_db)
):
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(404, "Site not found")
    
    if ctx.actor:
        allowed, reason = evaluate(db, "READ_SITE", ctx.actor, resource=site)
        if not allowed:
            raise HTTPException(403, reason)
    
    devices = db.query(Device).filter(Device.site_id == site_id, Device.status == "ACTIVE").all()
    miners_count = db.query(Miner).filter(Miner.site_id == site_id).count()
    
    return {
        "site_id": site.id,
        "name": site.name,
        "ip_mode": site.ip_mode,
        "mode_label": {1: "UI Masking", 2: "Server Envelope", 3: "Device E2EE"}.get(site.ip_mode),
        "has_dek": bool(site.site_dek_wrapped),
        "devices_count": len(devices),
        "miners_count": miners_count,
        "devices": [{"id": d.id, "name": d.device_name, "status": d.status} for d in devices]
    }


@app.get("/api/miners")
async def list_miners(
    site_id: Optional[int] = None,
    ctx: ActorContext = Depends(get_actor_context),
    db: Session = Depends(get_db)
):
    query = db.query(Miner)
    if site_id:
        query = query.filter(Miner.site_id == site_id)
    elif ctx.tenant_id:
        query = query.filter(Miner.tenant_id == ctx.tenant_id)
    
    miners = query.all()
    
    if ctx.actor:
        miners = filter_miners_by_abac(db, ctx.actor, miners)
    
    is_admin = ctx.role in ("owner", "admin")
    
    result = []
    for m in miners:
        display_cred = get_display_credential(m.credential_value, m.credential_mode, is_admin)
        result.append({
            "id": m.id,
            "name": m.name,
            "site_id": m.site_id,
            "credential_mode": m.credential_mode,
            "mode_label": {1: "UI Masking", 2: "Server Envelope", 3: "Device E2EE"}.get(m.credential_mode),
            "display_credential": display_cred,
            "fingerprint": m.fingerprint,
            "last_accepted_counter": m.last_accepted_counter
        })
    
    return result


class MinerCreate(BaseModel):
    site_id: int
    name: str
    credential_plaintext_json: Optional[str] = None
    credential_e2ee_b64: Optional[str] = None
    device_id: Optional[int] = None
    counter: int = 1

@app.post("/api/miners")
async def create_miner(
    data: MinerCreate,
    ctx: ActorContext = Depends(get_actor_context),
    db: Session = Depends(get_db)
):
    site = db.query(Site).filter(Site.id == data.site_id).first()
    if not site:
        raise HTTPException(404, "Site not found")
    
    if ctx.actor:
        allowed, reason = evaluate(db, "CREATE_MINER", ctx.actor, resource=site)
        if not allowed:
            log_audit_event(
                db, site.tenant_id, "POLICY_DENY",
                actor_id=ctx.actor_id, actor_name=ctx.actor_name, role=ctx.role,
                site_id=site.id, target_type="miner", detail={"action": "CREATE_MINER", "reason": reason}
            )
            raise HTTPException(403, reason)
    
    if site.ip_mode == 3:
        if data.credential_plaintext_json:
            raise HTTPException(400, "Mode 3 does not accept plaintext credentials - use credential_e2ee_b64")
        if not data.credential_e2ee_b64:
            raise HTTPException(400, "Mode 3 requires credential_e2ee_b64")
        
        cred_value, cred_mode, fingerprint = store_credential_mode3(data.credential_e2ee_b64, data.counter)
    elif site.ip_mode == 2:
        if not data.credential_plaintext_json:
            raise HTTPException(400, "Mode 2 requires credential_plaintext_json")
        if not site.site_dek_wrapped:
            raise HTTPException(500, "Site missing DEK for Mode 2")
        
        cred_value, cred_mode, fingerprint = store_credential_mode2(data.credential_plaintext_json, site.site_dek_wrapped)
    else:
        if not data.credential_plaintext_json:
            raise HTTPException(400, "Mode 1 requires credential_plaintext_json")
        
        cred_value, cred_mode, fingerprint = store_credential_mode1(data.credential_plaintext_json)
    
    miner = Miner(
        tenant_id=site.tenant_id,
        site_id=site.id,
        name=data.name,
        credential_value=cred_value,
        credential_mode=cred_mode,
        fingerprint=fingerprint,
        last_accepted_counter=data.counter if site.ip_mode == 3 else 0
    )
    
    db.add(miner)
    db.commit()
    db.refresh(miner)
    
    log_audit_event(
        db, site.tenant_id, "CREATE_MINER",
        actor_id=ctx.actor_id, actor_name=ctx.actor_name, role=ctx.role,
        site_id=site.id, target_type="miner", target_id=miner.id,
        detail={"name": data.name, "mode": cred_mode, "fingerprint": fingerprint}
    )
    
    return {"id": miner.id, "name": miner.name, "credential_mode": cred_mode, "fingerprint": fingerprint}


class ChangeCreate(BaseModel):
    tenant_id: int
    site_id: Optional[int] = None
    request_type: str
    target_type: str
    target_id: int
    requested_action: Dict[str, Any]
    reason: str

@app.post("/api/changes")
async def create_change(
    data: ChangeCreate,
    ctx: ActorContext = Depends(get_actor_context),
    db: Session = Depends(get_db)
):
    """Create a Change Request for high-risk operations"""
    if not ctx.actor:
        raise HTTPException(401, "Actor authentication required")
    
    target_resource = None
    resource_tenant_id = data.tenant_id
    resource_site_id = data.site_id
    
    if data.target_type == "miner":
        miner = db.query(Miner).filter(Miner.id == data.target_id).first()
        if not miner:
            raise HTTPException(404, f"Miner {data.target_id} not found")
        target_resource = miner
        resource_tenant_id = miner.tenant_id
        resource_site_id = miner.site_id
        
        allowed, reason = evaluate(db, "READ_MINER", ctx.actor, 
                                   resource_tenant_id=resource_tenant_id,
                                   resource_site_id=resource_site_id)
        if not allowed:
            raise HTTPException(403, f"Access denied to miner: {reason}")
            
    elif data.target_type == "site":
        site = db.query(Site).filter(Site.id == data.target_id).first()
        if not site:
            raise HTTPException(404, f"Site {data.target_id} not found")
        target_resource = site
        resource_tenant_id = site.tenant_id
        resource_site_id = site.id
        
        allowed, reason = evaluate(db, "READ_SITE", ctx.actor, resource=site)
        if not allowed:
            raise HTTPException(403, f"Access denied to site: {reason}")
    
    cr, message = create_change_request(
        db,
        tenant_id=resource_tenant_id,
        requester=ctx.actor,
        request_type=data.request_type,
        target_type=data.target_type,
        target_id=data.target_id,
        requested_action=data.requested_action,
        reason=data.reason,
        site_id=resource_site_id
    )
    
    if not cr:
        raise HTTPException(403, message)
    
    return {
        "id": cr.id,
        "status": cr.status,
        "expires_at": cr.expires_at.isoformat() if cr.expires_at else None,
        "message": message
    }


@app.get("/api/changes")
async def list_changes(
    tenant_id: Optional[int] = None,
    site_id: Optional[int] = None,
    status: Optional[str] = None,
    ctx: ActorContext = Depends(get_actor_context),
    db: Session = Depends(get_db)
):
    tid = tenant_id or ctx.tenant_id
    if not tid:
        raise HTTPException(400, "tenant_id required")
    
    changes = get_all_changes(db, tid, site_id, status)
    
    return [{
        "id": cr.id,
        "request_type": cr.request_type,
        "target_type": cr.target_type,
        "target_id": cr.target_id,
        "status": cr.status,
        "reason": cr.reason,
        "requester_id": cr.requester_actor_id,
        "approver_id": cr.approver_actor_id,
        "created_at": cr.created_at.isoformat() if cr.created_at else None,
        "expires_at": cr.expires_at.isoformat() if cr.expires_at else None,
        "is_expired": check_cr_expiry(cr)
    } for cr in changes]


@app.post("/api/changes/{cr_id}/approve")
async def approve_change(
    cr_id: int,
    ctx: ActorContext = Depends(get_actor_context),
    db: Session = Depends(get_db)
):
    """Approve a pending Change Request (Four-Eyes principle)"""
    if not ctx.actor:
        raise HTTPException(401, "Actor authentication required")
    
    cr = db.query(ChangeRequest).filter(ChangeRequest.id == cr_id).first()
    if not cr:
        raise HTTPException(404, "Change request not found")
    
    if cr.target_type == "miner":
        miner = db.query(Miner).filter(Miner.id == cr.target_id).first()
        if not miner:
            raise HTTPException(404, "Target miner no longer exists")
        allowed, reason = evaluate(db, "APPROVE_CHANGE", ctx.actor,
                                   resource_tenant_id=miner.tenant_id,
                                   resource_site_id=miner.site_id)
        if not allowed:
            log_audit_event(
                db, cr.tenant_id, "POLICY_DENY",
                actor_id=ctx.actor_id, actor_name=ctx.actor_name, role=ctx.role,
                site_id=miner.site_id, target_type="change_request", target_id=cr.id,
                detail={"action": "APPROVE_CHANGE", "reason": reason}
            )
            raise HTTPException(403, f"Access denied: {reason}")
    elif cr.target_type == "site":
        site = db.query(Site).filter(Site.id == cr.target_id).first()
        if not site:
            raise HTTPException(404, "Target site no longer exists")
        allowed, reason = evaluate(db, "APPROVE_CHANGE", ctx.actor, resource=site)
        if not allowed:
            log_audit_event(
                db, cr.tenant_id, "POLICY_DENY",
                actor_id=ctx.actor_id, actor_name=ctx.actor_name, role=ctx.role,
                site_id=site.id, target_type="change_request", target_id=cr.id,
                detail={"action": "APPROVE_CHANGE", "reason": reason}
            )
            raise HTTPException(403, f"Access denied: {reason}")
    
    success, message = approve_change_request(db, cr, ctx.actor)
    
    if not success:
        raise HTTPException(403, message)
    
    return {"id": cr.id, "status": cr.status, "message": message}


class RejectData(BaseModel):
    reason: str

@app.post("/api/changes/{cr_id}/reject")
async def reject_change(
    cr_id: int,
    data: RejectData,
    ctx: ActorContext = Depends(get_actor_context),
    db: Session = Depends(get_db)
):
    """Reject a pending Change Request"""
    if not ctx.actor:
        raise HTTPException(401, "Actor authentication required")
    
    cr = db.query(ChangeRequest).filter(ChangeRequest.id == cr_id).first()
    if not cr:
        raise HTTPException(404, "Change request not found")
    
    success, message = reject_change_request(db, cr, ctx.actor, data.reason)
    
    if not success:
        raise HTTPException(400, message)
    
    return {"id": cr.id, "status": cr.status, "message": message}


@app.post("/api/changes/{cr_id}/execute")
async def execute_change(
    cr_id: int,
    ctx: ActorContext = Depends(get_actor_context),
    db: Session = Depends(get_db)
):
    """Execute an approved Change Request"""
    if not ctx.actor:
        raise HTTPException(401, "Actor authentication required")
    
    cr = db.query(ChangeRequest).filter(ChangeRequest.id == cr_id).first()
    if not cr:
        raise HTTPException(404, "Change request not found")
    
    if cr.status != "APPROVED":
        raise HTTPException(400, f"Cannot execute: CR status is {cr.status}")
    
    if check_cr_expiry(cr):
        cr.status = "EXPIRED"
        db.commit()
        raise HTTPException(400, "Cannot execute: CR has expired")
    
    allowed, reason = evaluate(
        db, "EXECUTE_CHANGE", ctx.actor,
        resource_tenant_id=cr.tenant_id,
        resource_site_id=cr.site_id
    )
    if not allowed:
        log_audit_event(
            db, cr.tenant_id, "POLICY_DENY",
            actor_id=ctx.actor_id, actor_name=ctx.actor_name, role=ctx.role,
            site_id=cr.site_id, target_type="change_request", target_id=cr.id,
            detail={"action": "EXECUTE_CHANGE", "reason": reason}
        )
        raise HTTPException(403, reason)
    
    try:
        action = json.loads(cr.requested_action_json)
    except:
        action = {}
    
    result = {}
    
    if cr.request_type == "REVEAL_CREDENTIAL":
        miner = db.query(Miner).filter(Miner.id == cr.target_id).first()
        if not miner:
            raise HTTPException(404, "Miner not found")
        
        allowed, reason = evaluate(db, "REVEAL_CREDENTIAL", ctx.actor,
                                   resource_tenant_id=miner.tenant_id,
                                   resource_site_id=miner.site_id)
        if not allowed:
            log_audit_event(
                db, cr.tenant_id, "POLICY_DENY",
                actor_id=ctx.actor_id, actor_name=ctx.actor_name, role=ctx.role,
                site_id=miner.site_id, target_type="miner", target_id=miner.id,
                detail={"action": "REVEAL_CREDENTIAL", "reason": reason}
            )
            raise HTTPException(403, f"Access denied: {reason}")
        
        site = db.query(Site).filter(Site.id == miner.site_id).first()
        
        if miner.credential_mode == 1:
            result = reveal_credential_mode1(miner.credential_value)
        elif miner.credential_mode == 2:
            if site and site.site_dek_wrapped:
                result = reveal_credential_mode2(miner.credential_value, site.site_dek_wrapped)
            else:
                result = {"error": "Site DEK not found"}
        elif miner.credential_mode == 3:
            result = reveal_credential_mode3()
    
    elif cr.request_type == "CHANGE_SITE_MODE":
        site = db.query(Site).filter(Site.id == cr.target_id).first()
        if not site:
            raise HTTPException(404, "Site not found")
        
        allowed, reason = evaluate(db, "CHANGE_SITE_MODE", ctx.actor, resource=site)
        if not allowed:
            log_audit_event(
                db, cr.tenant_id, "POLICY_DENY",
                actor_id=ctx.actor_id, actor_name=ctx.actor_name, role=ctx.role,
                site_id=site.id, target_type="site", target_id=site.id,
                detail={"action": "CHANGE_SITE_MODE", "reason": reason}
            )
            raise HTTPException(403, f"Access denied: {reason}")
        
        new_mode = action.get("new_mode", site.ip_mode)
        old_mode = site.ip_mode
        
        if new_mode == 2 and not site.site_dek_wrapped:
            dek = generate_site_dek()
            site.site_dek_wrapped = wrap_dek(dek)
        
        site.ip_mode = new_mode
        db.commit()
        
        result = {"old_mode": old_mode, "new_mode": new_mode}
    
    elif cr.request_type == "BATCH_MIGRATE":
        site = db.query(Site).filter(Site.id == cr.target_id).first()
        if not site:
            raise HTTPException(404, "Site not found")
        
        allowed, reason = evaluate(db, "BATCH_MIGRATE", ctx.actor, resource=site)
        if not allowed:
            log_audit_event(
                db, cr.tenant_id, "POLICY_DENY",
                actor_id=ctx.actor_id, actor_name=ctx.actor_name, role=ctx.role,
                site_id=site.id, target_type="site", target_id=site.id,
                detail={"action": "BATCH_MIGRATE", "reason": reason}
            )
            raise HTTPException(403, f"Access denied: {reason}")
        
        miners = db.query(Miner).filter(Miner.site_id == site.id).all()
        migrated = 0
        failed = 0
        
        for miner in miners:
            if miner.credential_mode == site.ip_mode:
                continue
            
            if miner.credential_mode == 3:
                failed += 1
                continue
            
            new_val, new_mode, new_fp, msg = migrate_credential(
                miner.credential_value,
                miner.credential_mode,
                site.ip_mode,
                site.site_dek_wrapped
            )
            
            if new_val:
                miner.credential_value = new_val
                miner.credential_mode = new_mode
                miner.fingerprint = new_fp
                migrated += 1
            else:
                failed += 1
        
        db.commit()
        result = {"migrated": migrated, "failed": failed}
    
    cr.status = "EXECUTED"
    cr.executed_at = datetime.utcnow()
    cr.execution_result_json = json.dumps(result)
    db.commit()
    
    log_audit_event(
        db, cr.tenant_id, f"{cr.request_type}_EXECUTE",
        actor_id=ctx.actor_id, actor_name=ctx.actor_name, role=ctx.role,
        site_id=cr.site_id, target_type=cr.target_type, target_id=cr.target_id,
        detail={"cr_id": cr.id, "result": result}
    )
    
    return {"id": cr.id, "status": cr.status, "result": result}


class DiscoveryScan(BaseModel):
    site_id: int
    cidr: str
    ports: List[int] = [4028]
    simulate: bool = True

@app.post("/api/discovery/scan")
async def discovery_scan(
    data: DiscoveryScan,
    ctx: ActorContext = Depends(get_actor_context),
    db: Session = Depends(get_db)
):
    """Scan network for miners"""
    site = db.query(Site).filter(Site.id == data.site_id).first()
    if not site:
        raise HTTPException(404, "Site not found")
    
    if ctx.actor:
        allowed, reason = evaluate(db, "DISCOVERY_SCAN", ctx.actor, resource=site)
        if not allowed:
            log_audit_event(
                db, site.tenant_id, "POLICY_DENY",
                actor_id=ctx.actor_id, actor_name=ctx.actor_name, role=ctx.role,
                site_id=site.id, detail={"action": "DISCOVERY_SCAN", "reason": reason}
            )
            raise HTTPException(403, reason)
    
    if data.simulate:
        candidates = simulate_discovery(data.cidr, data.ports)
    else:
        candidates = real_discovery(data.cidr, data.ports)
    
    log_audit_event(
        db, site.tenant_id, "DISCOVERY_SCAN",
        actor_id=ctx.actor_id, actor_name=ctx.actor_name, role=ctx.role,
        site_id=site.id,
        detail={"cidr": data.cidr, "found": len(candidates), "simulate": data.simulate}
    )
    
    return {"candidates": candidates, "count": len(candidates)}


class OnboardData(BaseModel):
    site_id: int
    name: str
    credential_plaintext_json: Optional[str] = None
    credential_e2ee_b64: Optional[str] = None
    device_id: Optional[int] = None
    counter: int = 1
    fingerprint: Optional[str] = None

@app.post("/api/discovery/onboard")
async def discovery_onboard(
    data: OnboardData,
    ctx: ActorContext = Depends(get_actor_context),
    db: Session = Depends(get_db)
):
    """Onboard a discovered miner"""
    miner_data = MinerCreate(
        site_id=data.site_id,
        name=data.name,
        credential_plaintext_json=data.credential_plaintext_json,
        credential_e2ee_b64=data.credential_e2ee_b64,
        device_id=data.device_id,
        counter=data.counter
    )
    return await create_miner(miner_data, ctx, db)


class DeviceRegister(BaseModel):
    tenant_id: int
    site_id: int
    device_name: str
    public_key_b64: str
    secret_key_b64: Optional[str] = None

@app.post("/api/devices/register")
async def register_device(
    data: DeviceRegister,
    ctx: ActorContext = Depends(get_actor_context),
    db: Session = Depends(get_db)
):
    """Register an Edge device for E2EE"""
    site = db.query(Site).filter(Site.id == data.site_id).first()
    if not site:
        raise HTTPException(404, "Site not found")
    
    if ctx.actor:
        allowed, reason = evaluate(db, "REGISTER_DEVICE", ctx.actor, resource=site)
        if not allowed:
            raise HTTPException(403, reason)
    
    device_token = secrets.token_hex(32)
    
    device = Device(
        tenant_id=data.tenant_id,
        site_id=data.site_id,
        device_name=data.device_name,
        public_key_b64=data.public_key_b64,
        device_token=device_token,
        status="ACTIVE"
    )
    
    if DEMO_ALLOW_STORE_DEVICE_SECRET and data.secret_key_b64:
        device.secret_key_b64 = data.secret_key_b64
    
    db.add(device)
    db.commit()
    db.refresh(device)
    
    log_audit_event(
        db, data.tenant_id, "REGISTER_DEVICE",
        actor_id=ctx.actor_id, actor_name=ctx.actor_name, role=ctx.role,
        site_id=data.site_id, target_type="device", target_id=device.id,
        detail={"device_name": data.device_name}
    )
    
    return {
        "id": device.id,
        "device_name": device.device_name,
        "device_token": device_token,
        "warning": "Store this token securely - it will not be shown again!" if DEMO_ALLOW_STORE_DEVICE_SECRET else None,
        "demo_note": "DEMO MODE: secret_key stored for edge decrypt simulation. DISABLE IN PRODUCTION!" if device.secret_key_b64 else None
    }


@app.get("/api/devices")
async def list_devices(
    site_id: Optional[int] = None,
    ctx: ActorContext = Depends(get_actor_context),
    db: Session = Depends(get_db)
):
    query = db.query(Device)
    if site_id:
        query = query.filter(Device.site_id == site_id)
    elif ctx.tenant_id:
        query = query.filter(Device.tenant_id == ctx.tenant_id)
    
    devices = query.all()
    
    return [{
        "id": d.id,
        "device_name": d.device_name,
        "site_id": d.site_id,
        "status": d.status,
        "has_secret": bool(d.secret_key_b64),
        "created_at": d.created_at.isoformat() if d.created_at else None
    } for d in devices]


class EdgeDecrypt(BaseModel):
    miner_id: int

@app.post("/api/edge/decrypt")
async def edge_decrypt(
    data: EdgeDecrypt,
    authorization: str = Header(...),
    db: Session = Depends(get_db)
):
    """
    Edge device decrypt endpoint.
    DEMO ONLY: In production, decryption happens on the Edge device itself.
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Device token required")
    
    device_token = authorization[7:]
    
    device = db.query(Device).filter(Device.device_token == device_token).first()
    if not device:
        raise HTTPException(401, "Invalid device token")
    
    allowed, reason = check_device_access(db, device, device_token)
    if not allowed:
        raise HTTPException(403, reason)
    
    miner = db.query(Miner).filter(Miner.id == data.miner_id).first()
    if not miner:
        raise HTTPException(404, "Miner not found")
    
    if miner.site_id != device.site_id:
        raise HTTPException(403, "Device not authorized for this miner's site")
    
    if miner.credential_mode != 3:
        raise HTTPException(400, f"Miner is not in E2EE mode (mode={miner.credential_mode})")
    
    if not miner.credential_value or not miner.credential_value.startswith("E2EE:"):
        raise HTTPException(400, "Invalid E2EE credential format")
    
    if not device.secret_key_b64:
        raise HTTPException(400, "DEMO: Device secret key not stored. In production, decrypt on device.")
    
    try:
        e2ee_payload = miner.credential_value[5:]
        decoded = base64.b64decode(e2ee_payload)
        
        payload_json = decoded.decode('utf-8')
        payload = json.loads(payload_json)
        
        counter = payload.get("counter", 0)
        credential = payload.get("credential", payload)
        
        valid, msg = validate_anti_rollback(miner.last_accepted_counter, counter)
        if not valid:
            log_audit_event(
                db, device.tenant_id, "ANTI_ROLLBACK_REJECT",
                site_id=device.site_id, target_type="miner", target_id=miner.id,
                detail={"counter": counter, "last_accepted": miner.last_accepted_counter, "device_id": device.id}
            )
            raise HTTPException(400, msg)
        
        miner.last_accepted_counter = counter
        db.commit()
        
        log_audit_event(
            db, device.tenant_id, "EDGE_DECRYPT",
            site_id=device.site_id, target_type="miner", target_id=miner.id,
            detail={"counter": counter, "device_id": device.id}
        )
        
        return {
            "miner_id": miner.id,
            "credential_plaintext": credential,
            "counter": counter,
            "demo_warning": "DEMO MODE: Real E2EE uses libsodium sealed box decryption on Edge device"
        }
        
    except json.JSONDecodeError:
        raise HTTPException(400, "Invalid E2EE payload format")
    except Exception as e:
        raise HTTPException(500, f"Decryption error: {str(e)}")


@app.get("/api/audit")
async def list_audit(
    site_id: Optional[int] = None,
    tenant_id: Optional[int] = None,
    limit: int = 50,
    ctx: ActorContext = Depends(get_actor_context),
    db: Session = Depends(get_db)
):
    tid = tenant_id or ctx.tenant_id
    if not tid:
        raise HTTPException(400, "tenant_id required")
    
    events = get_recent_events(db, tid, site_id, limit)
    
    return [{
        "id": e.id,
        "event_type": e.event_type,
        "actor_name": e.actor_name,
        "role": e.role,
        "target_type": e.target_type,
        "target_id": e.target_id,
        "detail": json.loads(e.detail_json) if e.detail_json else {},
        "created_at": e.created_at.isoformat() if e.created_at else None,
        "event_hash": e.event_hash[:12] + "..." if e.event_hash else None
    } for e in events]


@app.get("/api/audit/verify")
async def verify_audit(
    site_id: Optional[int] = None,
    tenant_id: Optional[int] = None,
    ctx: ActorContext = Depends(get_actor_context),
    db: Session = Depends(get_db)
):
    tid = tenant_id or ctx.tenant_id
    if not tid:
        raise HTTPException(400, "tenant_id required")
    
    verify_ok, broken_id = verify_audit_chain(db, tid, site_id)
    
    return {
        "verify_ok": verify_ok,
        "first_broken_event_id": broken_id,
        "status": "INTACT" if verify_ok else "BROKEN"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)
