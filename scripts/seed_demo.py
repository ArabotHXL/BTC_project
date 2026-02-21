#!/usr/bin/env python3
"""
AB Integration - Demo Data Seeder
Creates sample data for testing: sites, tenants, miners, groups, contracts, invoices.
Idempotent: checks before creating.
"""
import os
import sys
import logging
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def seed_demo():
    from app import app
    from db import db
    from models_ab import (Org, Tenant, MinerGroup, ABAuditLog,
                           ABCurtailmentPlan, Tariff, ABContract,
                           ABUsageRecord, ABInvoice)
    from models import HostingSite, UserAccess
    
    with app.app_context():
        # Get or create self org
        self_org = Org.query.filter_by(org_type='self').first()
        if not self_org:
            logger.error("Run init_db.py first!")
            return
        
        # Get self tenant
        self_tenant = Tenant.query.filter_by(org_id=self_org.id, tenant_type='self').first()
        
        # Create demo site if needed
        demo_site = HostingSite.query.filter_by(slug='demo-farm-alpha').first()
        if not demo_site:
            demo_site = HostingSite(
                name='Demo Farm Alpha',
                slug='demo-farm-alpha',
                location='Texas, USA',
                capacity_mw=10.0,
                electricity_rate=0.045,
                operator_name='HashInsight Ops'
            )
            demo_site.status = 'online'
            demo_site.used_capacity_mw = 6.5
            demo_site.electricity_source = 'Natural Gas + Solar'
            db.session.add(demo_site)
            db.session.flush()
            logger.info(f"Created demo site: {demo_site.name} (id={demo_site.id})")
        else:
            logger.info(f"Demo site exists: {demo_site.name} (id={demo_site.id})")
        
        # Create client tenants
        client_names = [
            ('Alpha Mining Corp', 'client_alpha@demo.com'),
            ('Beta Hash Holdings', 'client_beta@demo.com')
        ]
        
        client_tenants = []
        for name, email in client_names:
            tenant = Tenant.query.filter_by(org_id=self_org.id, name=name).first()
            if not tenant:
                tenant = Tenant(
                    org_id=self_org.id,
                    name=name,
                    tenant_type='client',
                    status='active'
                )
                db.session.add(tenant)
                db.session.flush()
                logger.info(f"Created client tenant: {name} (id={tenant.id})")
                
                # Create a tenant user
                user = UserAccess.query.filter_by(email=email).first()
                if not user:
                    user = UserAccess(
                        name=f'{name} Admin',
                        email=email,
                        role='client',
                        username=email.split('@')[0]
                    )
                    user.set_password('demo123')
                    user.is_active = True
                    user.managed_by_site_id = demo_site.id
                    db.session.add(user)
                    db.session.flush()
                    logger.info(f"Created tenant user: {email} (id={user.id})")
            
            client_tenants.append(tenant)
        
        # Create groups for each tenant
        all_tenants = [self_tenant] + client_tenants
        for i, tenant in enumerate(all_tenants):
            if not tenant:
                continue
            existing = MinerGroup.query.filter_by(site_id=demo_site.id, tenant_id=tenant.id).first()
            if not existing:
                miner_counts = [20, 15, 10] if tenant.tenant_type == 'self' else [10 - i*3, 5]
                for j, mc in enumerate(miner_counts):
                    group = MinerGroup(
                        site_id=demo_site.id,
                        tenant_id=tenant.id,
                        name=f'{tenant.name} - Group {j+1}',
                        selector_json={
                            'miner_count': mc,
                            'watts_per_miner': 3000 + j * 200,
                            'hashrate_per_miner_th': 100 + j * 10,
                            'model': f'Antminer S19 XP {"Pro" if j == 0 else "Standard"}'
                        },
                        priority=(i + 1) * 10 + j
                    )
                    db.session.add(group)
                logger.info(f"Created groups for tenant: {tenant.name}")
        
        db.session.flush()
        
        # Create tariff
        tariff = Tariff.query.filter_by(org_id=self_org.id, name='Standard Flat Rate').first()
        if not tariff:
            tariff = Tariff(
                org_id=self_org.id,
                name='Standard Flat Rate',
                tariff_type='flat',
                params_json={'flat_rate': 0.045},
                currency='USD'
            )
            db.session.add(tariff)
            db.session.flush()
            logger.info(f"Created tariff: {tariff.name} (id={tariff.id})")
        
        # Create contracts for client tenants
        now = datetime.utcnow()
        for tenant in client_tenants:
            contract = ABContract.query.filter_by(org_id=self_org.id, tenant_id=tenant.id).first()
            if not contract:
                contract = ABContract(
                    org_id=self_org.id,
                    tenant_id=tenant.id,
                    site_id=demo_site.id,
                    tariff_id=tariff.id,
                    hosting_fee_type='per_kw',
                    hosting_fee_params_json={'rate': 45.0},
                    curtailment_split_pct=20.0,
                    billing_cycle='monthly',
                    effective_from=now - timedelta(days=90),
                    effective_to=now + timedelta(days=275)
                )
                db.session.add(contract)
                db.session.flush()
                logger.info(f"Created contract for {tenant.name} (id={contract.id})")
        
        db.session.flush()
        
        # Create usage records
        period_start = datetime(now.year, now.month, 1)
        period_end = now
        
        for tenant in client_tenants:
            existing = ABUsageRecord.query.filter_by(
                org_id=self_org.id, tenant_id=tenant.id,
                period_start=period_start
            ).first()
            if not existing:
                groups = MinerGroup.query.filter_by(site_id=demo_site.id, tenant_id=tenant.id).all()
                total_watts = sum(
                    (g.selector_json or {}).get('miner_count', 0) * (g.selector_json or {}).get('watts_per_miner', 3000)
                    for g in groups
                )
                duration_hours = (period_end - period_start).total_seconds() / 3600
                kwh = (total_watts / 1000) * duration_hours
                
                record = ABUsageRecord(
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
                        'duration_hours': round(duration_hours, 2)
                    }
                )
                db.session.add(record)
                logger.info(f"Created usage record for {tenant.name}")
        
        db.session.flush()
        
        # Create sample curtailment plan
        plan = ABCurtailmentPlan.query.filter_by(org_id=self_org.id, name='Demo Curtailment Plan').first()
        if not plan:
            plan = ABCurtailmentPlan(
                org_id=self_org.id,
                site_id=demo_site.id,
                tenant_scope='site_wide',
                name='Demo Curtailment Plan',
                objective='save_cost',
                inputs_json={
                    'electricity_rate': 0.045,
                    'duration_hours': 4,
                    'min_online_pct': 0.3,
                    'protected_groups': [],
                    'max_offline_groups': 3
                },
                status='draft'
            )
            db.session.add(plan)
            logger.info("Created demo curtailment plan")
        
        # Create sample invoices
        for tenant in client_tenants:
            contract = ABContract.query.filter_by(org_id=self_org.id, tenant_id=tenant.id).first()
            usage = ABUsageRecord.query.filter_by(org_id=self_org.id, tenant_id=tenant.id).first()
            if contract and usage:
                existing_inv = ABInvoice.query.filter_by(contract_id=contract.id).first()
                if not existing_inv:
                    rate = 0.045
                    electricity_cost = round(usage.kwh_estimated * rate, 2)
                    fee_rate = (contract.hosting_fee_params_json or {}).get('rate', 45.0)
                    hosting_fee = round(usage.avg_kw_estimated * fee_rate, 2)
                    
                    invoice = ABInvoice(
                        org_id=self_org.id,
                        tenant_id=tenant.id,
                        contract_id=contract.id,
                        period_start=period_start,
                        period_end=period_end,
                        subtotal=electricity_cost + hosting_fee,
                        total=round(electricity_cost + hosting_fee, 2),
                        line_items_json=[
                            {
                                'type': 'electricity',
                                'description': f'Electricity ({usage.kwh_estimated:.2f} kWh @ ${rate}/kWh)',
                                'quantity': usage.kwh_estimated,
                                'unit_price': rate,
                                'amount': electricity_cost
                            },
                            {
                                'type': 'hosting_fee',
                                'description': f'Hosting fee ({usage.avg_kw_estimated:.2f} kW @ ${fee_rate}/kW)',
                                'quantity': usage.avg_kw_estimated,
                                'unit_price': fee_rate,
                                'amount': hosting_fee
                            }
                        ],
                        evidence_json={
                            'usage_record_ids': [usage.id],
                            'tariff_id': tariff.id,
                            'generated_at': datetime.utcnow().isoformat()
                        }
                    )
                    db.session.add(invoice)
                    logger.info(f"Created invoice for {tenant.name}")
        
        db.session.commit()
        logger.info("\nDemo data seeding complete!")
        
        # Summary
        print(f"\n{'='*50}")
        print("DEMO DATA SUMMARY")
        print(f"{'='*50}")
        print(f"Org: {self_org.name} (id={self_org.id})")
        print(f"Self Tenant: {self_tenant.name if self_tenant else 'N/A'} (id={self_tenant.id if self_tenant else 'N/A'})")
        for t in client_tenants:
            print(f"Client Tenant: {t.name} (id={t.id})")
        print(f"Site: {demo_site.name} (id={demo_site.id})")
        print(f"Tariff: {tariff.name} (id={tariff.id})")
        print(f"Groups: {MinerGroup.query.filter_by(site_id=demo_site.id).count()}")
        print(f"Contracts: {ABContract.query.filter_by(org_id=self_org.id).count()}")
        print(f"Usage Records: {ABUsageRecord.query.filter_by(org_id=self_org.id).count()}")
        print(f"Invoices: {ABInvoice.query.filter_by(org_id=self_org.id).count()}")
        print(f"Curtailment Plans: {ABCurtailmentPlan.query.filter_by(org_id=self_org.id).count()}")
        print(f"\nLogin credentials:")
        print(f"  Operator: admin@local / admin123")
        print(f"  Client Alpha: client_alpha@demo.com / demo123")
        print(f"  Client Beta: client_beta@demo.com / demo123")

if __name__ == '__main__':
    seed_demo()
