"""
Test script for HashInsight Secure Miner Onboarding Demo
Tests ABAC, Guarded Approval, Credential Protection, and Audit Chain
"""
import json
import secrets
from datetime import datetime, timedelta

from db import init_db, get_session, Tenant, Actor, Site, Miner, Device, ChangeRequest, AuditEvent
from services.policy_service import evaluate, filter_sites_by_abac
from services.approval_service import create_change_request, approve_change_request, check_cr_expiry
from services.credential_service import (
    store_credential_mode1, store_credential_mode2, store_credential_mode3,
    reveal_credential_mode1, reveal_credential_mode2, get_display_credential,
    validate_anti_rollback
)
from services.envelope_kms_service import generate_site_dek, wrap_dek, unwrap_dek
from services.audit_service import log_audit_event, verify_audit_chain, get_recent_events
from services.discovery_service import simulate_discovery


_test_session = None

def get_test_session():
    """Get or create shared test session"""
    global _test_session
    if _test_session is None:
        _test_session = get_session()
    return _test_session


def setup_test_data():
    """Create test tenant, actors, and sites"""
    db = get_test_session()
    
    tenant = db.query(Tenant).filter(Tenant.name == "Test Tenant").first()
    if not tenant:
        tenant = Tenant(name="Test Tenant")
        db.add(tenant)
        db.commit()
        db.refresh(tenant)
    
    owner = db.query(Actor).filter(Actor.tenant_id == tenant.id, Actor.role == "owner").first()
    if not owner:
        owner = Actor(tenant_id=tenant.id, actor_name="owner_alice", role="owner", api_token=secrets.token_hex(16))
        operator = Actor(tenant_id=tenant.id, actor_name="operator_bob", role="operator", api_token=secrets.token_hex(16))
        viewer = Actor(tenant_id=tenant.id, actor_name="viewer_charlie", role="viewer", api_token=secrets.token_hex(16))
        db.add_all([owner, operator, viewer])
        db.commit()
        db.refresh(owner)
    else:
        operator = db.query(Actor).filter(Actor.tenant_id == tenant.id, Actor.role == "operator").first()
        viewer = db.query(Actor).filter(Actor.tenant_id == tenant.id, Actor.role == "viewer").first()
    
    site1 = db.query(Site).filter(Site.tenant_id == tenant.id, Site.ip_mode == 1).first()
    if not site1:
        site1 = Site(tenant_id=tenant.id, name="Mode 1 Site", ip_mode=1)
        db.add(site1)
        db.commit()
        db.refresh(site1)
    
    site2 = db.query(Site).filter(Site.tenant_id == tenant.id, Site.ip_mode == 2).first()
    if not site2:
        dek = generate_site_dek()
        site2 = Site(tenant_id=tenant.id, name="Mode 2 Site", ip_mode=2, site_dek_wrapped=wrap_dek(dek))
        db.add(site2)
        db.commit()
        db.refresh(site2)
    
    for actor in [owner, operator]:
        actor.allowed_site_ids = [site1.id, site2.id]
    viewer.allowed_site_ids = [site1.id]
    db.commit()
    
    return tenant, owner, operator, viewer, site1, site2


def test_abac_tenant_isolation():
    """Test RULE-1: Tenant isolation"""
    print("\n=== Test ABAC Tenant Isolation ===")
    db = get_test_session()
    
    other_tenant = Tenant(name="Other Tenant")
    db.add(other_tenant)
    db.commit()
    db.refresh(other_tenant)
    
    other_site = Site(tenant_id=other_tenant.id, name="Other Site", ip_mode=1)
    db.add(other_site)
    db.commit()
    db.refresh(other_site)
    
    owner = db.query(Actor).filter(Actor.actor_name == "owner_alice").first()
    
    allowed, reason = evaluate(db, "READ_SITE", owner, resource=other_site)
    assert not allowed, f"Tenant isolation failed: {reason}"
    print(f"  ✓ Owner cannot access other tenant's site: {reason}")
    
    db.delete(other_site)
    db.delete(other_tenant)
    db.commit()
    print("  ✓ Tenant isolation test PASSED")


def test_abac_site_isolation():
    """Test RULE-2: Site isolation"""
    print("\n=== Test ABAC Site Isolation ===")
    db = get_test_session()
    
    viewer = db.query(Actor).filter(Actor.actor_name == "viewer_charlie").first()
    sites = db.query(Site).filter(Site.tenant_id == viewer.tenant_id).all()
    
    allowed_sites = filter_sites_by_abac(db, viewer, sites)
    allowed_ids = [s.id for s in allowed_sites]
    
    assert len(allowed_sites) == 1, f"Viewer should only see 1 site, got {len(allowed_sites)}"
    print(f"  ✓ Viewer filtered to {len(allowed_sites)} site(s)")
    
    site2 = db.query(Site).filter(Site.name == "Mode 2 Site").first()
    allowed, reason = evaluate(db, "READ_SITE", viewer, resource=site2)
    assert not allowed, "Viewer should not access site2"
    print(f"  ✓ Viewer denied access to site2: {reason}")
    print("  ✓ Site isolation test PASSED")


def test_abac_role_permissions():
    """Test RULE-3 & RULE-4: Role-based permissions"""
    print("\n=== Test ABAC Role Permissions ===")
    db = get_test_session()
    
    viewer = db.query(Actor).filter(Actor.actor_name == "viewer_charlie").first()
    operator = db.query(Actor).filter(Actor.actor_name == "operator_bob").first()
    owner = db.query(Actor).filter(Actor.actor_name == "owner_alice").first()
    site1 = db.query(Site).filter(Site.name == "Mode 1 Site").first()
    
    allowed, reason = evaluate(db, "CREATE_MINER", viewer, resource=site1)
    assert not allowed, "Viewer should not create miners"
    print(f"  ✓ Viewer denied CREATE_MINER: {reason}")
    
    allowed, reason = evaluate(db, "CREATE_MINER", operator, resource=site1)
    assert allowed, f"Operator should create miners: {reason}"
    print(f"  ✓ Operator allowed CREATE_MINER")
    
    allowed, reason = evaluate(db, "CHANGE_SITE_MODE", operator, resource=site1)
    assert not allowed, "Operator should not change site mode"
    print(f"  ✓ Operator denied CHANGE_SITE_MODE: {reason}")
    
    allowed, reason = evaluate(db, "CHANGE_SITE_MODE", owner, resource=site1)
    assert allowed, f"Owner should change site mode: {reason}"
    print(f"  ✓ Owner allowed CHANGE_SITE_MODE")
    print("  ✓ Role permissions test PASSED")


def test_credential_mode1():
    """Test Mode 1: UI Masking"""
    print("\n=== Test Credential Mode 1 (UI Masking) ===")
    
    cred_json = json.dumps({"ip": "192.168.1.100", "port": 4028, "password": "secret123"})
    
    stored, mode, fingerprint = store_credential_mode1(cred_json)
    assert mode == 1
    assert stored == cred_json
    print(f"  ✓ Stored Mode 1 credential (fingerprint: {fingerprint[:12]}...)")
    
    display = get_display_credential(stored, mode, is_admin=False)
    assert "xxx" in display["ip"]
    assert display["password"] == "***"
    print(f"  ✓ Display shows masked IP: {display['ip']}")
    print(f"  ✓ Password is masked: {display['password']}")
    
    revealed = reveal_credential_mode1(stored)
    assert revealed["ip"] == "192.168.1.100"
    assert revealed["password"] == "secret123"
    print(f"  ✓ Revealed credential: ip={revealed['ip']}, password unmasked")
    
    print("  ✓ Mode 1 test PASSED")


def test_credential_mode2():
    """Test Mode 2: Server Envelope Encryption"""
    print("\n=== Test Credential Mode 2 (Server Envelope) ===")
    
    dek = generate_site_dek()
    dek_wrapped = wrap_dek(dek)
    print(f"  ✓ Generated DEK, wrapped length: {len(dek_wrapped)}")
    
    dek_unwrapped = unwrap_dek(dek_wrapped)
    assert dek == dek_unwrapped
    print(f"  ✓ DEK wrap/unwrap verified")
    
    cred_json = json.dumps({"ip": "10.0.0.50", "port": 4028, "password": "encrypted_secret"})
    
    stored, mode, fingerprint = store_credential_mode2(cred_json, dek_wrapped)
    assert mode == 2
    assert stored.startswith("ENC:")
    print(f"  ✓ Stored Mode 2 credential (starts with ENC:)")
    
    display = get_display_credential(stored, mode, is_admin=True)
    assert display["status"] == "[Server Encrypted]"
    print(f"  ✓ Display shows: {display['status']}")
    
    revealed = reveal_credential_mode2(stored, dek_wrapped)
    assert revealed["ip"] == "10.0.0.50"
    print(f"  ✓ Revealed credential: ip={revealed['ip']}")
    
    print("  ✓ Mode 2 test PASSED")


def test_credential_mode3():
    """Test Mode 3: Device E2EE with anti-rollback"""
    print("\n=== Test Credential Mode 3 (Device E2EE) ===")
    
    import base64
    payload = json.dumps({"credential": {"ip": "172.16.0.1", "port": 4028}, "counter": 100})
    e2ee_b64 = base64.b64encode(payload.encode()).decode()
    
    stored, mode, fingerprint = store_credential_mode3(e2ee_b64, counter=100)
    assert mode == 3
    assert stored.startswith("E2EE:")
    print(f"  ✓ Stored Mode 3 credential (starts with E2EE:)")
    
    display = get_display_credential(stored, mode, is_admin=True)
    assert display["status"] == "[E2EE Protected]"
    print(f"  ✓ Display shows: {display['status']}")
    
    valid, msg = validate_anti_rollback(last_accepted_counter=50, new_counter=100)
    assert valid, f"Anti-rollback should pass: {msg}"
    print(f"  ✓ Anti-rollback: new counter 100 > last 50 - {msg}")
    
    valid, msg = validate_anti_rollback(last_accepted_counter=100, new_counter=50)
    assert not valid, "Anti-rollback should reject lower counter"
    print(f"  ✓ Anti-rollback rejected: {msg}")
    
    print("  ✓ Mode 3 test PASSED")


def test_approval_workflow():
    """Test Guarded Approval with Four-Eyes principle"""
    print("\n=== Test Approval Workflow (Four-Eyes) ===")
    db = get_test_session()
    
    operator = db.query(Actor).filter(Actor.actor_name == "operator_bob").first()
    owner = db.query(Actor).filter(Actor.actor_name == "owner_alice").first()
    site1 = db.query(Site).filter(Site.name == "Mode 1 Site").first()
    
    cr, msg = create_change_request(
        db,
        tenant_id=operator.tenant_id,
        requester=operator,
        request_type="REVEAL_CREDENTIAL",
        target_type="miner",
        target_id=999,
        requested_action={"reveal_all": True},
        reason="Need to check miner configuration",
        site_id=site1.id
    )
    assert cr is not None, f"Failed to create CR: {msg}"
    assert cr.status == "PENDING"
    print(f"  ✓ Created CR #{cr.id}: {cr.request_type} - {cr.status}")
    
    success, msg = approve_change_request(db, cr, operator)
    assert not success, "Same person should not approve their own CR"
    print(f"  ✓ Four-Eyes: self-approval blocked - {msg}")
    
    success, msg = approve_change_request(db, cr, owner)
    assert success, f"Owner should approve: {msg}"
    assert cr.status == "APPROVED"
    print(f"  ✓ Owner approved CR: status={cr.status}")
    
    assert check_cr_expiry(cr) == False
    print(f"  ✓ CR not expired (expires at {cr.expires_at})")
    print("  ✓ Approval workflow test PASSED")


def test_audit_chain():
    """Test immutable audit log with hash chain"""
    print("\n=== Test Audit Chain ===")
    db = get_test_session()
    
    tenant = db.query(Tenant).filter(Tenant.name == "Test Tenant").first()
    
    for i in range(3):
        log_audit_event(
            db, tenant.id, f"TEST_EVENT_{i}",
            actor_name="test_user",
            role="admin",
            detail={"test_index": i}
        )
    
    events = get_recent_events(db, tenant.id, limit=10)
    print(f"  ✓ Logged 3 audit events, total {len(events)} in chain")
    
    if events:
        first = events[-1]
        assert first.event_hash is not None
        print(f"  ✓ First event hash: {first.event_hash[:16]}...")
    
    verify_ok, broken_id = verify_audit_chain(db, tenant.id)
    assert verify_ok, f"Audit chain should be intact, broken at {broken_id}"
    print(f"  ✓ Audit chain verified: INTACT")
    print("  ✓ Audit chain test PASSED")


def test_discovery():
    """Test network discovery simulation"""
    print("\n=== Test Discovery ===")
    
    candidates = simulate_discovery("192.168.1.0/24", [4028])
    assert len(candidates) > 0
    print(f"  ✓ Discovered {len(candidates)} miners in 192.168.1.0/24")
    
    first = candidates[0]
    assert "ip" in first
    assert "port" in first
    assert "vendor_hint" in first
    print(f"  ✓ First candidate: {first['ip']}:{first['port']} ({first['vendor_hint']})")
    
    print("  ✓ Discovery test PASSED")


def main():
    print("=" * 60)
    print("HashInsight Secure Miner Onboarding Demo - Test Suite")
    print("=" * 60)
    
    init_db()
    print("✓ Database initialized")
    
    tenant, owner, operator, viewer, site1, site2 = setup_test_data()
    print(f"✓ Test data ready: Tenant '{tenant.name}', Sites: {site1.name}, {site2.name}")
    
    try:
        test_abac_tenant_isolation()
        test_abac_site_isolation()
        test_abac_role_permissions()
        test_credential_mode1()
        test_credential_mode2()
        test_credential_mode3()
        test_approval_workflow()
        test_audit_chain()
        test_discovery()
        
        print("\n" + "=" * 60)
        print("ALL TESTS PASSED ✓")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        raise
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        raise


if __name__ == "__main__":
    main()
