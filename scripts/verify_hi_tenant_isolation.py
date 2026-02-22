#!/usr/bin/env python3
"""
HI Integration Tenant Isolation Verification Script (P0 Gate)

Tests:
1. HiTenantMembership model + records
2. Role mapping
3. API endpoint isolation (tenant_id param override)
4. Auto-bind (no session hi_tenant_id)
5. Role persistence (session hi_tenant_id set, tenant_admin must not downgrade)
6. Cross-ID access (plan/invoice by ID)
7. Unbound user 403 with error code
8. Operator scope
"""
import sys
import os
import logging
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

PASS = 0
FAIL = 0


def check(desc, condition):
    global PASS, FAIL
    if condition:
        PASS += 1
        logger.info(f"  ✅ {desc}")
    else:
        FAIL += 1
        logger.info(f"  ❌ {desc}")


def run_verification():
    global PASS, FAIL
    from app import app
    from db import db
    from models_hi import (HiOrg, HiTenant, HiGroup, HiTenantMembership,
                           HiCurtailmentPlan, HiUsageRecord, HiInvoice)
    from models import UserAccess, Miner

    with app.app_context():
        logger.info("=" * 60)
        logger.info("HI Integration Tenant Isolation Verification (P0 Gate)")
        logger.info("=" * 60)

        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()

        logger.info("\n[1] HiTenantMembership model check")
        check("hi_tenant_memberships table exists", 'hi_tenant_memberships' in tables)

        logger.info("\n[2] Membership records")
        memberships = HiTenantMembership.query.all()
        check(f"Memberships count >= 2 (found {len(memberships)})", len(memberships) >= 2)

        alpha_user = UserAccess.query.filter_by(email='client_alpha@demo.com').first()
        beta_user = UserAccess.query.filter_by(email='client_beta@demo.com').first()

        if alpha_user:
            alpha_mem = HiTenantMembership.query.filter_by(user_id=alpha_user.id).first()
            check(f"Alpha user has membership (tenant_id={alpha_mem.tenant_id if alpha_mem else None})",
                  alpha_mem is not None)
            if alpha_mem:
                check("Alpha membership is_default=True", alpha_mem.is_default is True)
                check("Alpha membership role=tenant_admin", alpha_mem.member_role == 'tenant_admin')
        else:
            check("Alpha user exists", False)

        if beta_user:
            beta_mem = HiTenantMembership.query.filter_by(user_id=beta_user.id).first()
            check(f"Beta user has membership (tenant_id={beta_mem.tenant_id if beta_mem else None})",
                  beta_mem is not None)
            if beta_mem:
                check("Beta membership is_default=True", beta_mem.is_default is True)
                check("Beta membership role=tenant_admin", beta_mem.member_role == 'tenant_admin')
        else:
            check("Beta user exists", False)

        logger.info("\n[3] Role mapping verification")
        from common.hi_tenant import ROLE_TO_HI_ROLE
        check("owner -> operator_admin", ROLE_TO_HI_ROLE.get('owner') == 'operator_admin')
        check("admin -> operator_admin", ROLE_TO_HI_ROLE.get('admin') == 'operator_admin')
        check("operator -> operator_ops (not tenant_admin)", ROLE_TO_HI_ROLE.get('operator') == 'operator_ops')
        check("client -> tenant_viewer", ROLE_TO_HI_ROLE.get('client') == 'tenant_viewer')

        alpha_tenant = HiTenant.query.filter(HiTenant.name.ilike('%alpha%')).first()
        beta_tenant = HiTenant.query.filter(HiTenant.name.ilike('%beta%')).first()

        if not (alpha_tenant and beta_tenant and alpha_user and beta_user):
            logger.info("  ⚠️  Skipping API tests - missing test data")
            return FAIL == 0

        client = app.test_client()

        logger.info("\n[4] API endpoint isolation tests (tenant_id param override)")
        with client.session_transaction() as sess:
            sess['authenticated'] = True
            sess['user_id'] = alpha_user.id
            sess['role'] = 'client'
            sess['hi_tenant_id'] = alpha_tenant.id

        resp = client.get('/api/hi/tenants')
        check(f"Alpha /tenants returns 200 (got {resp.status_code})", resp.status_code == 200)
        tenants = resp.get_json()
        tenant_ids = [t['id'] for t in tenants]
        check("Alpha only sees own tenant", tenant_ids == [alpha_tenant.id])

        resp = client.get(f'/api/hi/miners?tenant_id={beta_tenant.id}')
        check(f"Alpha querying beta miners -> 403 (got {resp.status_code})", resp.status_code == 403)

        resp = client.get(f'/api/hi/groups?tenant_id={beta_tenant.id}')
        check(f"Alpha querying beta groups -> 403 (got {resp.status_code})", resp.status_code == 403)

        resp = client.get(f'/api/hi/curtailment/plans?tenant_id={beta_tenant.id}')
        check(f"Alpha querying beta plans -> 403 (got {resp.status_code})", resp.status_code == 403)

        resp = client.get(f'/api/hi/usage?tenant_id={beta_tenant.id}')
        check(f"Alpha querying beta usage -> 403 (got {resp.status_code})", resp.status_code == 403)

        resp = client.get(f'/api/hi/invoices?tenant_id={beta_tenant.id}')
        check(f"Alpha querying beta invoices -> 403 (got {resp.status_code})", resp.status_code == 403)

        resp = client.get(f'/api/hi/contracts?tenant_id={beta_tenant.id}')
        check(f"Alpha querying beta contracts -> 403 (got {resp.status_code})", resp.status_code == 403)

        # ===== NEW P0 TESTS =====

        logger.info("\n[5] Auto-bind test (no session hi_tenant_id)")
        with client.session_transaction() as sess:
            sess.clear()
            sess['authenticated'] = True
            sess['user_id'] = alpha_user.id
            sess['role'] = 'client'

        resp = client.get('/api/hi/me')
        check(f"Alpha auto-bind /me returns 200 (got {resp.status_code})", resp.status_code == 200)
        if resp.status_code == 200:
            me = resp.get_json()
            check(f"Alpha auto-bind hi_tenant_id={me.get('hi_tenant_id')} == {alpha_tenant.id}",
                  me.get('hi_tenant_id') == alpha_tenant.id)
            check(f"Alpha auto-bind hi_role={me.get('hi_role')} == tenant_admin",
                  me.get('hi_role') == 'tenant_admin')

        with client.session_transaction() as sess:
            sess.clear()
            sess['authenticated'] = True
            sess['user_id'] = beta_user.id
            sess['role'] = 'client'

        resp = client.get('/api/hi/me')
        check(f"Beta auto-bind /me returns 200 (got {resp.status_code})", resp.status_code == 200)
        if resp.status_code == 200:
            me = resp.get_json()
            check(f"Beta auto-bind hi_tenant_id={me.get('hi_tenant_id')} == {beta_tenant.id}",
                  me.get('hi_tenant_id') == beta_tenant.id)
            check(f"Beta auto-bind hi_role={me.get('hi_role')} == tenant_admin",
                  me.get('hi_role') == 'tenant_admin')

        logger.info("\n[6] Role persistence test (session has hi_tenant_id, role must not downgrade)")
        with client.session_transaction() as sess:
            sess.clear()
            sess['authenticated'] = True
            sess['user_id'] = alpha_user.id
            sess['role'] = 'client'
            sess['hi_tenant_id'] = alpha_tenant.id

        resp = client.get('/api/hi/me')
        check(f"Alpha with session /me returns 200 (got {resp.status_code})", resp.status_code == 200)
        if resp.status_code == 200:
            me = resp.get_json()
            check(f"Alpha role persistence: hi_role={me.get('hi_role')} == tenant_admin (not tenant_viewer)",
                  me.get('hi_role') == 'tenant_admin')

        logger.info("\n[7] Cross-ID access test (plan/invoice by ID)")
        self_org = HiOrg.query.filter_by(org_type='self').first()

        beta_plan = HiCurtailmentPlan.query.filter_by(tenant_id=beta_tenant.id).first()
        if not beta_plan and self_org:
            from models import HostingSite
            demo_site = HostingSite.query.first()
            if demo_site:
                beta_plan = HiCurtailmentPlan(
                    org_id=self_org.id,
                    site_id=demo_site.id,
                    tenant_scope='tenant_only',
                    tenant_id=beta_tenant.id,
                    name='Beta Test Plan (verify)',
                    objective='save_cost',
                    inputs_json={},
                    status='draft',
                    created_by=beta_user.id
                )
                db.session.add(beta_plan)
                db.session.commit()

        beta_invoice = HiInvoice.query.filter_by(tenant_id=beta_tenant.id).first()
        if not beta_invoice and self_org:
            beta_invoice = HiInvoice(
                org_id=self_org.id,
                tenant_id=beta_tenant.id,
                contract_id=None,
                period_start=datetime(2026, 1, 1),
                period_end=datetime(2026, 1, 31),
                total_kwh=1000.0,
                total_amount=500.0,
                currency='USD',
                status='draft',
                line_items_json=[]
            )
            db.session.add(beta_invoice)
            db.session.commit()

        with client.session_transaction() as sess:
            sess.clear()
            sess['authenticated'] = True
            sess['user_id'] = alpha_user.id
            sess['role'] = 'client'
            sess['hi_tenant_id'] = alpha_tenant.id

        if beta_plan:
            resp = client.get(f'/api/hi/curtailment/plans/{beta_plan.id}/report')
            check(f"Alpha accessing beta plan report -> {resp.status_code} (must be 403/404)",
                  resp.status_code in (403, 404))
        else:
            check("Beta plan exists for cross-ID test", False)

        if beta_invoice:
            resp = client.get(f'/api/hi/invoices/{beta_invoice.id}')
            check(f"Alpha accessing beta invoice -> {resp.status_code} (must be 403/404)",
                  resp.status_code in (403, 404))

            resp = client.get(f'/api/hi/invoices/{beta_invoice.id}/export.csv')
            check(f"Alpha accessing beta invoice CSV -> {resp.status_code} (must be 403/404)",
                  resp.status_code in (403, 404))
        else:
            check("Beta invoice exists for cross-ID test", False)

        logger.info("\n[8] Unbound user 403 with error code HI_TENANT_BINDING_REQUIRED")
        unbound_user = UserAccess.query.filter_by(email='unbound_test_987654@test.com').first()
        if not unbound_user:
            unbound_user = UserAccess(
                name='Unbound Test User',
                email='unbound_test_987654@test.com',
                role='client',
                username='unbound_test_user_987654'
            )
            unbound_user.set_password('test123')
            unbound_user.is_active = True
            unbound_user.is_email_verified = True
            db.session.add(unbound_user)
            db.session.commit()

        try:
            with client.session_transaction() as sess:
                sess.clear()
                sess['authenticated'] = True
                sess['user_id'] = unbound_user.id
                sess['role'] = 'client'

            resp = client.get('/api/hi/miners')
            check(f"Unbound user /miners -> 403 (got {resp.status_code})", resp.status_code == 403)

            if resp.status_code == 403:
                data = resp.get_json()
                error_code = None
                if isinstance(data, dict):
                    if 'error' in data and isinstance(data['error'], dict):
                        error_code = data['error'].get('code')
                    elif 'code' in data:
                        error_code = data.get('code')
                check(f"Unbound 403 code={error_code} == HI_TENANT_BINDING_REQUIRED",
                      error_code == 'HI_TENANT_BINDING_REQUIRED')
        finally:
            HiTenantMembership.query.filter_by(user_id=unbound_user.id).delete()
            db.session.delete(unbound_user)
            db.session.commit()

        logger.info("\n[9] Operator scope test")
        admin_user = UserAccess.query.filter_by(role='admin').first()
        if admin_user:
            with client.session_transaction() as sess:
                sess.clear()
                sess['authenticated'] = True
                sess['user_id'] = admin_user.id
                sess['role'] = 'admin'

            resp = client.get('/api/hi/tenants')
            check(f"Admin /tenants returns 200 (got {resp.status_code})", resp.status_code == 200)
            tenants = resp.get_json()
            check(f"Admin sees multiple tenants ({len(tenants)} found)", len(tenants) >= 2)

            resp = client.get('/api/hi/me')
            me = resp.get_json()
            check(f"Admin hi_role=operator_admin (got {me.get('hi_role')})",
                  me.get('hi_role') == 'operator_admin')
            check("Admin hi_tenant_id is None", me.get('hi_tenant_id') is None)
        else:
            check("Admin user exists for operator test", False)

        logger.info("\n" + "=" * 60)
        total = PASS + FAIL
        logger.info(f"Results: {PASS}/{total} passed, {FAIL} failed")
        if FAIL == 0:
            logger.info("✅ HI tenant isolation OK")
        else:
            logger.info(f"⚠️  {FAIL} check(s) FAILED - review above")
        logger.info("=" * 60)

    return FAIL == 0


if __name__ == '__main__':
    success = run_verification()
    sys.exit(0 if success else 1)
