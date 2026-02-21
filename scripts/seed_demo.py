#!/usr/bin/env python3
"""
HI Integration - Demo Data Seeder
Creates comprehensive demo data using hi_ models.
Idempotent: checks before creating. Each section wrapped in try/except.
"""
import os
import sys
import logging
import random
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def seed_demo():
    from app import app
    from db import db
    from models_hi import (HiOrg, HiTenant, HiGroup, HiAuditLog,
                           HiCurtailmentPlan, HiTariff, HiContract,
                           HiUsageRecord, HiInvoice)
    from models import HostingSite, Miner, UserAccess

    with app.app_context():
        now = datetime.utcnow()

        # ============================================================
        # PHASE 1: Core entities
        # ============================================================
        print("\n" + "="*60)
        print("PHASE 1: Core entities (org, tenants, site, miners, groups)")
        print("="*60)

        # --- Self org ---
        try:
            self_org = HiOrg.query.filter_by(org_type='self').first()
            if not self_org:
                logger.error("Run init_db.py first! No self org found.")
                return
            logger.info(f"Self org: {self_org.name} (id={self_org.id})")
        except Exception as e:
            logger.error(f"Failed to get self org: {e}")
            return

        # --- Self tenant ---
        try:
            self_tenant = HiTenant.query.filter_by(org_id=self_org.id, tenant_type='self').first()
            if not self_tenant:
                logger.error("Run init_db.py first! No self tenant found.")
                return
            logger.info(f"Self tenant: {self_tenant.name} (id={self_tenant.id})")
        except Exception as e:
            logger.error(f"Failed to get self tenant: {e}")
            return

        # --- Demo hosting site ---
        demo_site = None
        try:
            demo_site = HostingSite.query.first()
            if not demo_site:
                demo_site = HostingSite(
                    name='Demo Mining Farm',
                    slug='demo-farm',
                    location='Texas, USA',
                    capacity_mw=5.0,
                    electricity_rate=0.045,
                    operator_name='HashInsight Ops'
                )
                demo_site.status = 'online'
                db.session.add(demo_site)
                db.session.flush()
                logger.info(f"Created demo site: {demo_site.name} (id={demo_site.id})")
            else:
                logger.info(f"Using existing site: {demo_site.name} (id={demo_site.id})")
        except Exception as e:
            logger.error(f"Failed to create/get demo site: {e}")
            db.session.rollback()

        if not demo_site:
            logger.error("Cannot proceed without a hosting site")
            return

        # --- Client tenants ---
        alpha_tenant = None
        beta_tenant = None
        try:
            alpha_tenant = HiTenant.query.filter_by(org_id=self_org.id, name='Alpha Mining Corp').first()
            if not alpha_tenant:
                alpha_tenant = HiTenant(
                    org_id=self_org.id,
                    name='Alpha Mining Corp',
                    tenant_type='client',
                    status='active'
                )
                db.session.add(alpha_tenant)
                db.session.flush()
                logger.info(f"Created Alpha tenant (id={alpha_tenant.id})")
            else:
                logger.info(f"Alpha tenant exists (id={alpha_tenant.id})")

            beta_tenant = HiTenant.query.filter_by(org_id=self_org.id, name='Beta Hash Holdings').first()
            if not beta_tenant:
                beta_tenant = HiTenant(
                    org_id=self_org.id,
                    name='Beta Hash Holdings',
                    tenant_type='client',
                    status='active'
                )
                db.session.add(beta_tenant)
                db.session.flush()
                logger.info(f"Created Beta tenant (id={beta_tenant.id})")
            else:
                logger.info(f"Beta tenant exists (id={beta_tenant.id})")

            db.session.commit()
        except Exception as e:
            logger.error(f"Failed to create client tenants: {e}")
            db.session.rollback()

        client_tenants = [alpha_tenant, beta_tenant]

        # --- Miners (20 total) ---
        try:
            existing_demo_miner = Miner.query.filter(Miner.miner_id.like('demo-miner-%')).first()
            if not existing_demo_miner:
                miners_config = []
                for i in range(1, 11):
                    miners_config.append({
                        'miner_id': f'demo-miner-{i:03d}',
                        'ip': f'192.168.1.{100+i}',
                        'model': 'Antminer S19 Pro',
                        'hi_tenant_id': self_tenant.id,
                        'nominal_watts': 3250.0,
                    })
                for i in range(11, 16):
                    miners_config.append({
                        'miner_id': f'demo-miner-{i:03d}',
                        'ip': f'192.168.1.{100+i}',
                        'model': 'Antminer S21',
                        'hi_tenant_id': alpha_tenant.id if alpha_tenant else self_tenant.id,
                        'nominal_watts': 3500.0,
                    })
                for i in range(16, 21):
                    miners_config.append({
                        'miner_id': f'demo-miner-{i:03d}',
                        'ip': f'192.168.1.{100+i}',
                        'model': 'Antminer S19 Pro',
                        'hi_tenant_id': beta_tenant.id if beta_tenant else self_tenant.id,
                        'nominal_watts': 3250.0,
                    })

                for mc in miners_config:
                    miner = Miner(
                        miner_id=mc['miner_id'],
                        site_id=str(demo_site.id),
                        ip=mc['ip'],
                        model=mc['model'],
                        status='online',
                        source='demo_seed'
                    )
                    miner.hi_tenant_id = mc['hi_tenant_id']
                    miner.nominal_watts = mc['nominal_watts']
                    db.session.add(miner)

                db.session.commit()
                logger.info("Created 20 demo miners")
            else:
                logger.info("Demo miners already exist, skipping")
        except Exception as e:
            logger.error(f"Failed to create miners: {e}")
            db.session.rollback()

        # --- HiGroups (3) ---
        try:
            existing_group = HiGroup.query.filter_by(site_id=demo_site.id, name='Self-Mining Group A').first()
            if not existing_group:
                groups_config = [
                    {
                        'name': 'Self-Mining Group A',
                        'tenant_id': self_tenant.id,
                        'priority': 10,
                        'selector_json': {
                            'miner_count': 10,
                            'watts_per_miner': 3250,
                            'hashrate_per_miner_th': 110
                        }
                    },
                    {
                        'name': 'Alpha Group 1',
                        'tenant_id': alpha_tenant.id if alpha_tenant else self_tenant.id,
                        'priority': 20,
                        'selector_json': {
                            'miner_count': 5,
                            'watts_per_miner': 3500,
                            'hashrate_per_miner_th': 200
                        }
                    },
                    {
                        'name': 'Beta Group 1',
                        'tenant_id': beta_tenant.id if beta_tenant else self_tenant.id,
                        'priority': 30,
                        'selector_json': {
                            'miner_count': 5,
                            'watts_per_miner': 3250,
                            'hashrate_per_miner_th': 110
                        }
                    },
                ]
                for gc in groups_config:
                    group = HiGroup(
                        site_id=demo_site.id,
                        tenant_id=gc['tenant_id'],
                        name=gc['name'],
                        selector_json=gc['selector_json'],
                        priority=gc['priority']
                    )
                    db.session.add(group)
                db.session.commit()
                logger.info("Created 3 HiGroups")
            else:
                logger.info("HiGroups already exist, skipping")
        except Exception as e:
            logger.error(f"Failed to create groups: {e}")
            db.session.rollback()

        # --- Audit log entries (20) ---
        try:
            existing_audit_count = HiAuditLog.query.filter_by(org_id=self_org.id).count()
            if existing_audit_count < 20:
                action_types = ['SYSTEM_INIT', 'TENANT_CREATE', 'GROUP_CREATE', 'MINER_LIST',
                                'SITE_UPDATE', 'USER_LOGIN', 'PLAN_CREATE', 'PLAN_SIMULATE',
                                'CONFIG_UPDATE', 'DATA_EXPORT']
                entity_types = ['system', 'tenant', 'group', 'miner', 'site', 'user', 'plan', 'config']
                needed = 20 - existing_audit_count
                for i in range(needed):
                    action_type = action_types[i % len(action_types)]
                    entity_type = entity_types[i % len(entity_types)]
                    audit = HiAuditLog(
                        org_id=self_org.id,
                        tenant_id=self_tenant.id if i % 3 == 0 else (alpha_tenant.id if alpha_tenant and i % 3 == 1 else (beta_tenant.id if beta_tenant else self_tenant.id)),
                        action_type=action_type,
                        entity_type=entity_type,
                        entity_id=str(i + 1),
                        detail_json={'demo_entry': i + 1, 'source': 'seed_demo'}
                    )
                    db.session.add(audit)
                db.session.commit()
                logger.info(f"Created {needed} audit log entries (total now >= 20)")
            else:
                logger.info(f"Audit log already has {existing_audit_count} entries, skipping")
        except Exception as e:
            logger.error(f"Failed to create audit logs: {e}")
            db.session.rollback()

        # ============================================================
        # PHASE 2: Curtailment plans
        # ============================================================
        print("\n" + "="*60)
        print("PHASE 2: Curtailment plans (simulate, execute, verify)")
        print("="*60)

        plan1 = None
        plan2 = None
        try:
            plan1 = HiCurtailmentPlan.query.filter_by(
                org_id=self_org.id, name='Demo Site-Wide Curtailment'
            ).first()
            if not plan1:
                plan1 = HiCurtailmentPlan(
                    org_id=self_org.id,
                    site_id=demo_site.id,
                    tenant_scope='site_wide',
                    name='Demo Site-Wide Curtailment',
                    objective='save_cost',
                    inputs_json={
                        'duration_hours': 4,
                        'electricity_rate': 0.045,
                        'min_online_pct': 0.3,
                        'protected_groups': [],
                        'max_offline_groups': 3
                    },
                    status='draft'
                )
                db.session.add(plan1)
                db.session.flush()
                logger.info(f"Created Plan 1: Demo Site-Wide Curtailment (id={plan1.id})")
            else:
                logger.info(f"Plan 1 exists (id={plan1.id}, status={plan1.status})")

            plan2 = HiCurtailmentPlan.query.filter_by(
                org_id=self_org.id, name='Alpha Tenant Curtailment'
            ).first()
            if not plan2:
                plan2 = HiCurtailmentPlan(
                    org_id=self_org.id,
                    site_id=demo_site.id,
                    tenant_scope='tenant_only',
                    tenant_id=alpha_tenant.id if alpha_tenant else self_tenant.id,
                    name='Alpha Tenant Curtailment',
                    objective='keep_profit',
                    inputs_json={
                        'duration_hours': 4,
                        'electricity_rate': 0.045,
                        'min_online_pct': 0.3,
                        'protected_groups': [],
                        'max_offline_groups': 2
                    },
                    status='draft'
                )
                db.session.add(plan2)
                db.session.flush()
                logger.info(f"Created Plan 2: Alpha Tenant Curtailment (id={plan2.id})")
            else:
                logger.info(f"Plan 2 exists (id={plan2.id}, status={plan2.status})")

            db.session.commit()
        except Exception as e:
            logger.error(f"Failed to create curtailment plans: {e}")
            db.session.rollback()

        # Run simulate -> execute -> verify on Plan 1
        if plan1 and plan1.status == 'draft':
            try:
                from services.curtailment_engine import CurtailmentEngine

                logger.info("Simulating Plan 1...")
                sim_result = CurtailmentEngine.simulate(plan1.id)
                if 'error' not in sim_result:
                    logger.info(f"Simulation result: {sim_result.get('expected', {}).get('groups_affected', 0)} groups affected")
                else:
                    logger.warning(f"Simulation error: {sim_result['error']}")

                logger.info("Executing Plan 1...")
                exec_result = CurtailmentEngine.execute(plan1.id)
                if 'error' not in exec_result:
                    logger.info(f"Execution result: {exec_result.get('actions_created', 0)} actions created")
                else:
                    logger.warning(f"Execution error: {exec_result['error']}")

                plan1_fresh = HiCurtailmentPlan.query.get(plan1.id)
                if plan1_fresh and plan1_fresh.status == 'executing':
                    logger.info("Verifying Plan 1...")
                    verify_result = CurtailmentEngine.verify(plan1.id)
                    if 'error' not in verify_result:
                        logger.info(f"Verification result: status={verify_result.get('status')}")
                    else:
                        logger.warning(f"Verification error: {verify_result['error']}")
            except Exception as e:
                logger.error(f"Curtailment engine failed: {e}")
                db.session.rollback()
        else:
            logger.info("Plan 1 already processed or not available, skipping curtailment engine")

        # ============================================================
        # PHASE 3: Billing (tariffs, contracts, users, usage, invoices)
        # ============================================================
        print("\n" + "="*60)
        print("PHASE 3: Billing (tariffs, contracts, users, usage, invoices)")
        print("="*60)

        # --- Tariff ---
        tariff = None
        try:
            tariff = HiTariff.query.filter_by(org_id=self_org.id, name='Standard Flat Rate').first()
            if not tariff:
                tariff = HiTariff(
                    org_id=self_org.id,
                    name='Standard Flat Rate',
                    tariff_type='flat',
                    params_json={'flat_rate': 0.045},
                    currency='USD'
                )
                db.session.add(tariff)
                db.session.flush()
                logger.info(f"Created tariff: {tariff.name} (id={tariff.id})")
            else:
                logger.info(f"Tariff exists: {tariff.name} (id={tariff.id})")
            db.session.commit()
        except Exception as e:
            logger.error(f"Failed to create tariff: {e}")
            db.session.rollback()

        # --- Contracts ---
        alpha_contract = None
        beta_contract = None
        try:
            if alpha_tenant and tariff:
                alpha_contract = HiContract.query.filter_by(
                    org_id=self_org.id, tenant_id=alpha_tenant.id
                ).first()
                if not alpha_contract:
                    alpha_contract = HiContract(
                        org_id=self_org.id,
                        tenant_id=alpha_tenant.id,
                        site_id=demo_site.id,
                        tariff_id=tariff.id,
                        hosting_fee_type='per_kw',
                        hosting_fee_params_json={'rate': 45.0},
                        curtailment_split_pct=20.0,
                        billing_cycle='monthly',
                        effective_from=now - timedelta(days=90),
                        effective_to=now + timedelta(days=275)
                    )
                    db.session.add(alpha_contract)
                    db.session.flush()
                    logger.info(f"Created Alpha contract (id={alpha_contract.id})")
                else:
                    logger.info(f"Alpha contract exists (id={alpha_contract.id})")

            if beta_tenant and tariff:
                beta_contract = HiContract.query.filter_by(
                    org_id=self_org.id, tenant_id=beta_tenant.id
                ).first()
                if not beta_contract:
                    beta_contract = HiContract(
                        org_id=self_org.id,
                        tenant_id=beta_tenant.id,
                        site_id=demo_site.id,
                        tariff_id=tariff.id,
                        hosting_fee_type='per_miner',
                        hosting_fee_params_json={'rate': 100.0, 'miner_count': 5},
                        curtailment_split_pct=15.0,
                        billing_cycle='monthly',
                        effective_from=now - timedelta(days=90),
                        effective_to=now + timedelta(days=275)
                    )
                    db.session.add(beta_contract)
                    db.session.flush()
                    logger.info(f"Created Beta contract (id={beta_contract.id})")
                else:
                    logger.info(f"Beta contract exists (id={beta_contract.id})")

            db.session.commit()
        except Exception as e:
            logger.error(f"Failed to create contracts: {e}")
            db.session.rollback()

        # --- Client tenant users ---
        try:
            user_configs = [
                {'email': 'client_alpha@demo.com', 'name': 'Alpha Mining Corp Admin', 'username': 'client_alpha'},
                {'email': 'client_beta@demo.com', 'name': 'Beta Hash Holdings Admin', 'username': 'client_beta'},
            ]
            for uc in user_configs:
                user = UserAccess.query.filter_by(email=uc['email']).first()
                if not user:
                    user = UserAccess(
                        name=uc['name'],
                        email=uc['email'],
                        role='client',
                        username=uc['username']
                    )
                    user.set_password('demo123')
                    user.is_active = True
                    user.is_email_verified = True
                    db.session.add(user)
                    logger.info(f"Created user: {uc['email']}")
                else:
                    logger.info(f"User exists: {uc['email']}")
            db.session.commit()
        except Exception as e:
            logger.error(f"Failed to create client users: {e}")
            db.session.rollback()

        # --- Usage records ---
        period_start = datetime(now.year, now.month, 1)
        period_end = now

        from services.usage_service import UsageService
        for tenant in client_tenants:
            if not tenant:
                continue
            try:
                logger.info(f"Generating usage for tenant {tenant.name}...")
                usage_result = UsageService.generate_usage(
                    org_id=self_org.id,
                    site_id=demo_site.id,
                    tenant_id=tenant.id,
                    period_start=period_start,
                    period_end=period_end
                )
                logger.info(f"Usage for {tenant.name}: {usage_result.get('kwh_estimated', 0):.2f} kWh")
            except Exception as e:
                db.session.rollback()
                logger.warning(f"UsageService failed for {tenant.name}, creating manual record: {e}")
                try:
                    existing = HiUsageRecord.query.filter_by(
                        org_id=self_org.id, site_id=demo_site.id, tenant_id=tenant.id,
                        period_start=period_start
                    ).first()
                    if not existing:
                        groups = HiGroup.query.filter_by(site_id=demo_site.id, tenant_id=tenant.id).all()
                        total_watts = sum(
                            (g.selector_json or {}).get('miner_count', 0) * (g.selector_json or {}).get('watts_per_miner', 3000)
                            for g in groups
                        )
                        duration_hours = (period_end - period_start).total_seconds() / 3600
                        kwh = (total_watts / 1000) * duration_hours
                        record = HiUsageRecord(
                            org_id=self_org.id,
                            site_id=demo_site.id,
                            tenant_id=tenant.id,
                            period_start=period_start,
                            period_end=period_end,
                            kwh_estimated=round(kwh, 2),
                            avg_kw_estimated=round(total_watts / 1000, 2),
                            method='nominal_watts',
                            evidence_json={
                                'total_miners': sum((g.selector_json or {}).get('miner_count', 0) for g in groups),
                                'total_watts': total_watts,
                                'duration_hours': round(duration_hours, 2),
                                'source': 'seed_demo_fallback'
                            }
                        )
                        db.session.add(record)
                        db.session.commit()
                        logger.info(f"Created manual usage record for {tenant.name}: {kwh:.2f} kWh")
                    else:
                        logger.info(f"Usage record already exists for {tenant.name}")
                except Exception as e2:
                    logger.error(f"Manual usage record creation also failed: {e2}")
                    db.session.rollback()

        # --- Invoices ---
        from services.billing_service import BillingService
        contracts_to_bill = []
        if alpha_contract:
            contracts_to_bill.append(alpha_contract)
        if beta_contract:
            contracts_to_bill.append(beta_contract)

        for contract in contracts_to_bill:
            try:
                logger.info(f"Generating invoice for contract {contract.id}...")
                inv_result = BillingService.generate_invoice(
                    contract_id=contract.id,
                    period_start=period_start,
                    period_end=period_end
                )
                if isinstance(inv_result, dict) and 'error' in inv_result:
                    logger.warning(f"Invoice error: {inv_result['error']}")
                else:
                    logger.info(f"Invoice generated: total=${inv_result.get('total', 0):.2f}")
            except Exception as e:
                logger.error(f"Failed to generate invoice for contract {contract.id}: {e}")
                db.session.rollback()

        # ============================================================
        # SUMMARY
        # ============================================================
        print(f"\n{'='*60}")
        print("DEMO DATA SUMMARY")
        print(f"{'='*60}")
        print(f"Org: {self_org.name} (id={self_org.id})")
        print(f"Self Tenant: {self_tenant.name} (id={self_tenant.id})")
        if alpha_tenant:
            print(f"Alpha Tenant: {alpha_tenant.name} (id={alpha_tenant.id})")
        if beta_tenant:
            print(f"Beta Tenant: {beta_tenant.name} (id={beta_tenant.id})")
        print(f"Site: {demo_site.name} (id={demo_site.id})")

        try:
            print(f"Groups: {HiGroup.query.filter_by(site_id=demo_site.id).count()}")
            print(f"Miners: {Miner.query.filter(Miner.miner_id.like('demo-miner-%')).count()}")
            print(f"Curtailment Plans: {HiCurtailmentPlan.query.filter_by(org_id=self_org.id).count()}")
            if tariff:
                print(f"Tariff: {tariff.name} (id={tariff.id})")
            print(f"Contracts: {HiContract.query.filter_by(org_id=self_org.id).count()}")
            print(f"Usage Records: {HiUsageRecord.query.filter_by(org_id=self_org.id).count()}")
            print(f"Invoices: {HiInvoice.query.filter_by(org_id=self_org.id).count()}")
            print(f"Audit Logs: {HiAuditLog.query.filter_by(org_id=self_org.id).count()}")
        except Exception as e:
            logger.warning(f"Summary query error: {e}")

        print(f"\nLogin credentials:")
        print(f"  Operator: admin@local / admin123")
        print(f"  Client Alpha: client_alpha@demo.com / demo123")
        print(f"  Client Beta: client_beta@demo.com / demo123")
        print(f"\nDemo seeding complete!")

if __name__ == '__main__':
    seed_demo()
