#!/usr/bin/env python3
"""
HI Integration Tenant Isolation Verification Script

Tests cross-tenant isolation:
1. Membership-based tenant binding
2. Operator org-scoped access
3. Tenant users blocked from other tenants' data
4. Unbound users get 403
"""
import sys
import os
import json
import logging

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
        logger.info("HI Integration Tenant Isolation Verification")
        logger.info("=" * 60)

        # 1. Check model exists
        logger.info("\n[1] HiTenantMembership model check")
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        check("hi_tenant_memberships table exists", 'hi_tenant_memberships' in tables)

        # 2. Check memberships exist
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
        else:
            check("Beta user exists", False)

        # 3. Test ROLE_TO_HI_ROLE mapping
        logger.info("\n[3] Role mapping verification")
        from common.hi_tenant import ROLE_TO_HI_ROLE
        check("owner -> operator_admin", ROLE_TO_HI_ROLE.get('owner') == 'operator_admin')
        check("admin -> operator_admin", ROLE_TO_HI_ROLE.get('admin') == 'operator_admin')
        check("operator -> operator_ops (not tenant_admin)", ROLE_TO_HI_ROLE.get('operator') == 'operator_ops')
        check("client -> tenant_viewer", ROLE_TO_HI_ROLE.get('client') == 'tenant_viewer')

        # 4. API isolation tests using test client
        logger.info("\n[4] API endpoint isolation tests")

        alpha_tenant = HiTenant.query.filter(HiTenant.name.ilike('%alpha%')).first()
        beta_tenant = HiTenant.query.filter(HiTenant.name.ilike('%beta%')).first()

        if not (alpha_tenant and beta_tenant and alpha_user and beta_user):
            logger.info("  ⚠️  Skipping API tests - missing test data")
        else:
            client = app.test_client()

            # Login as alpha
            with client.session_transaction() as sess:
                sess['authenticated'] = True
                sess['user_id'] = alpha_user.id
                sess['role'] = 'client'
                sess['hi_tenant_id'] = alpha_tenant.id

            # Alpha should see own tenant data
            resp = client.get('/api/hi/tenants')
            check(f"Alpha /tenants returns 200 (got {resp.status_code})", resp.status_code == 200)
            tenants = resp.get_json()
            tenant_ids = [t['id'] for t in tenants]
            check("Alpha only sees own tenant", tenant_ids == [alpha_tenant.id])

            # Alpha tries to access beta miners via tenant_id param
            resp = client.get(f'/api/hi/miners?tenant_id={beta_tenant.id}')
            check(f"Alpha querying beta miners -> 403 (got {resp.status_code})", resp.status_code == 403)

            # Alpha tries to access beta groups via tenant_id param
            resp = client.get(f'/api/hi/groups?tenant_id={beta_tenant.id}')
            check(f"Alpha querying beta groups -> 403 (got {resp.status_code})", resp.status_code == 403)

            # Alpha tries to access beta curtailment plans
            resp = client.get(f'/api/hi/curtailment/plans?tenant_id={beta_tenant.id}')
            check(f"Alpha querying beta plans -> 403 (got {resp.status_code})", resp.status_code == 403)

            # Alpha tries to access beta usage
            resp = client.get(f'/api/hi/usage?tenant_id={beta_tenant.id}')
            check(f"Alpha querying beta usage -> 403 (got {resp.status_code})", resp.status_code == 403)

            # Alpha tries to access beta invoices
            resp = client.get(f'/api/hi/invoices?tenant_id={beta_tenant.id}')
            check(f"Alpha querying beta invoices -> 403 (got {resp.status_code})", resp.status_code == 403)

            # Alpha tries to access beta contracts
            resp = client.get(f'/api/hi/contracts?tenant_id={beta_tenant.id}')
            check(f"Alpha querying beta contracts -> 403 (got {resp.status_code})", resp.status_code == 403)

            # 5. Unbound user test
            logger.info("\n[5] Unbound user isolation test")
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
                    sess['authenticated'] = True
                    sess['user_id'] = unbound_user.id
                    sess['role'] = 'client'
                    if 'hi_tenant_id' in sess:
                        del sess['hi_tenant_id']

                resp = client.get('/api/hi/tenants')
                check(f"Unbound user /tenants returns 403 (status={resp.status_code})",
                      resp.status_code == 403)

                resp = client.get('/api/hi/miners')
                if resp.status_code == 403:
                    check("Unbound user /miners -> 403", True)
                elif resp.status_code == 200:
                    data = resp.get_json()
                    check("Unbound user /miners -> empty list", data == [])
                else:
                    check(f"Unbound user /miners -> unexpected {resp.status_code}", False)
            finally:
                db.session.delete(unbound_user)
                db.session.commit()

            # 6. Operator test
            logger.info("\n[6] Operator scope test")
            admin_user = UserAccess.query.filter_by(role='admin').first()
            if admin_user:
                with client.session_transaction() as sess:
                    sess['authenticated'] = True
                    sess['user_id'] = admin_user.id
                    sess['role'] = 'admin'
                    if 'hi_tenant_id' in sess:
                        del sess['hi_tenant_id']

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

        # Summary
        logger.info("\n" + "=" * 60)
        total = PASS + FAIL
        logger.info(f"Results: {PASS}/{total} passed, {FAIL} failed")
        if FAIL == 0:
            logger.info("🎉 All isolation checks PASSED!")
        else:
            logger.info(f"⚠️  {FAIL} check(s) FAILED - review above")
        logger.info("=" * 60)

    return FAIL == 0


if __name__ == '__main__':
    success = run_verification()
    sys.exit(0 if success else 1)
