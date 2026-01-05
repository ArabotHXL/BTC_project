"""
Control Plane Seed Data
创建示例数据：1 Site, 2 Zone, 2 Customer, 若干 MinerAsset, 1 EdgeDevice
"""
import os
import sys
import uuid
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db
from models import UserAccess, HostingSite
from models_device_encryption import EdgeDevice
from models_control_plane import (
    Zone, HostingCustomer, MinerAsset, MinerCapability,
    PricePlan, PricePlanVersion, RetentionPolicy, ApprovalPolicy
)


def seed_control_plane_data():
    """Seed control plane demonstration data"""
    with app.app_context():
        print("🌱 Seeding Control Plane data...")
        
        site = HostingSite.query.first()
        if not site:
            print("Creating demo site...")
            site = HostingSite(
                name="Demo Mining Farm 50MW",
                location="Texas, USA",
                capacity_mw=50.0,
                electricity_rate=0.05,
            )
            db.session.add(site)
            db.session.flush()
        
        print(f"Using site: {site.name} (ID: {site.id})")
        
        existing_zones = Zone.query.filter_by(site_id=site.id).count()
        if existing_zones == 0:
            print("Creating zones...")
            zone1 = Zone(
                site_id=site.id,
                name="Building A - Container Row 1",
                zone_type="container",
                capacity_kw=10000,
                contracted_capacity_kw=8000,
                energy_source="grid",
            )
            zone2 = Zone(
                site_id=site.id,
                name="Building B - Indoor Facility",
                zone_type="room",
                capacity_kw=15000,
                contracted_capacity_kw=12000,
                energy_source="hydro",
            )
            db.session.add_all([zone1, zone2])
            db.session.flush()
            print(f"Created zones: {zone1.zone_id}, {zone2.zone_id}")
        else:
            zone1 = Zone.query.filter_by(site_id=site.id).first()
            zone2 = Zone.query.filter_by(site_id=site.id).offset(1).first() or zone1
        
        existing_customers = HostingCustomer.query.filter_by(site_id=site.id).count()
        if existing_customers == 0:
            print("Creating hosting customers...")
            
            user1 = UserAccess.query.filter_by(email='customer1@demo.com').first()
            if not user1:
                from werkzeug.security import generate_password_hash
                user1 = UserAccess(
                    username='customer1',
                    email='customer1@demo.com',
                    password_hash=generate_password_hash('Demo123!'),
                    role='customer',
                )
                db.session.add(user1)
                db.session.flush()
            
            user2 = UserAccess.query.filter_by(email='customer2@demo.com').first()
            if not user2:
                from werkzeug.security import generate_password_hash
                user2 = UserAccess(
                    username='customer2',
                    email='customer2@demo.com',
                    password_hash=generate_password_hash('Demo123!'),
                    role='customer',
                )
                db.session.add(user2)
                db.session.flush()
            
            customer1 = HostingCustomer(
                site_id=site.id,
                user_id=user1.id,
                name="Alpha Mining Corp",
                company="Alpha Mining Corporation",
                email="ops@alphamining.com",
                contract_start=datetime.utcnow() - timedelta(days=180),
                contract_end=datetime.utcnow() + timedelta(days=365),
            )
            customer2 = HostingCustomer(
                site_id=site.id,
                user_id=user2.id,
                name="Beta Hash LLC",
                company="Beta Hash Limited",
                email="admin@betahash.io",
                contract_start=datetime.utcnow() - timedelta(days=90),
                contract_end=datetime.utcnow() + timedelta(days=275),
            )
            db.session.add_all([customer1, customer2])
            db.session.flush()
            print(f"Created customers: {customer1.customer_id}, {customer2.customer_id}")
        else:
            customer1 = HostingCustomer.query.filter_by(site_id=site.id).first()
            customer2 = HostingCustomer.query.filter_by(site_id=site.id).offset(1).first() or customer1
        
        existing_assets = MinerAsset.query.filter_by(site_id=site.id).count()
        if existing_assets == 0:
            print("Creating miner assets...")
            
            miner_models = [
                ("Antminer S19 Pro", "Bitmain", 110, 3250),
                ("Antminer S19j Pro+", "Bitmain", 122, 3355),
                ("Whatsminer M50S", "MicroBT", 126, 3276),
                ("Whatsminer M50", "MicroBT", 114, 3306),
            ]
            
            assets = []
            for i in range(20):
                model_info = miner_models[i % len(miner_models)]
                customer = customer1 if i < 12 else customer2
                zone = zone1 if i < 10 else zone2
                
                asset = MinerAsset(
                    site_id=site.id,
                    zone_id=zone.id if zone else None,
                    customer_id=customer.id if customer else None,
                    model=model_info[0],
                    vendor=model_info[1],
                    serial_number=f"SN{site.id:03d}{i:05d}",
                    firmware="stock",
                    hashrate_th=model_info[2],
                    power_w=model_info[3],
                    tags=["production"],
                )
                assets.append(asset)
            
            db.session.add_all(assets)
            db.session.flush()
            print(f"Created {len(assets)} miner assets")
            
            for asset in assets[:5]:
                cap = MinerCapability(
                    asset_id=asset.id,
                    supports_actions=["REBOOT", "POWER_MODE", "SET_FREQ", "LED"],
                    firmware_features={"api_version": "3.0", "dual_tune": True},
                    detected_by_edge_id="edge_demo",
                )
                db.session.add(cap)
        
        existing_edge = EdgeDevice.query.filter_by(site_id=site.id).first()
        if not existing_edge:
            print("Creating edge device...")
            edge = EdgeDevice(
                edge_device_id=f"edge_{uuid.uuid4().hex[:8]}",
                site_id=site.id,
                name="Primary Edge Collector",
                device_token=f"tok_{uuid.uuid4().hex}",
                status="ACTIVE",
            )
            db.session.add(edge)
            db.session.flush()
            print(f"Created edge device: {edge.edge_device_id}, token: {edge.device_token}")
        
        existing_policy = RetentionPolicy.query.filter_by(is_default=True).first()
        if not existing_policy:
            print("Creating retention policy...")
            policy = RetentionPolicy(
                name="Default 1-Year Retention",
                audit_days=365,
                telemetry_days=365,
                billing_days=1095,
                ticket_days=730,
                is_default=True,
            )
            db.session.add(policy)
        
        existing_approval = ApprovalPolicy.query.filter_by(site_id=None).first()
        if not existing_approval:
            print("Creating approval policies...")
            policies = [
                ApprovalPolicy(
                    site_id=None,
                    action_type="REBOOT",
                    risk_tier="MEDIUM",
                    require_approval=True,
                    require_dual_approval=False,
                ),
                ApprovalPolicy(
                    site_id=None,
                    action_type="CHANGE_POOL",
                    risk_tier="HIGH",
                    require_approval=True,
                    require_dual_approval=True,
                    dual_approval_threshold_count=10,
                ),
                ApprovalPolicy(
                    site_id=None,
                    action_type="POWER_MODE",
                    risk_tier="MEDIUM",
                    require_approval=True,
                    require_dual_approval=False,
                ),
                ApprovalPolicy(
                    site_id=None,
                    action_type="SET_FREQ",
                    risk_tier="MEDIUM",
                    require_approval=True,
                    require_dual_approval=False,
                ),
                ApprovalPolicy(
                    site_id=None,
                    action_type="LED",
                    risk_tier="LOW",
                    require_approval=False,
                    require_dual_approval=False,
                ),
            ]
            db.session.add_all(policies)
        
        existing_plan = PricePlan.query.filter_by(site_id=site.id).first()
        if not existing_plan:
            print("Creating price plan...")
            plan = PricePlan(
                site_id=site.id,
                name="Standard TOU Rate",
                description="Time-of-Use electricity rate plan",
            )
            db.session.add(plan)
            db.session.flush()
            
            version = PricePlanVersion(
                price_plan_id=plan.id,
                version_number=1,
                effective_from=datetime.utcnow() - timedelta(days=30),
                timezone="America/Chicago",
                granularity="hourly",
                missing_data_policy="carry_forward",
                payload_json={
                    "rates": [
                        {"hour_start": 0, "hour_end": 6, "rate_per_kwh": 0.04, "period": "off_peak"},
                        {"hour_start": 6, "hour_end": 14, "rate_per_kwh": 0.06, "period": "normal"},
                        {"hour_start": 14, "hour_end": 20, "rate_per_kwh": 0.12, "period": "peak"},
                        {"hour_start": 20, "hour_end": 24, "rate_per_kwh": 0.06, "period": "normal"},
                    ],
                    "demand_rate_per_kw": 15.0,
                    "currency": "USD",
                },
            )
            db.session.add(version)
            print(f"Created price plan: {plan.price_plan_id}")
        
        db.session.commit()
        print("✅ Control Plane seed data created successfully!")
        
        print("\n📊 Summary:")
        print(f"  - Site: {site.name}")
        print(f"  - Zones: {Zone.query.filter_by(site_id=site.id).count()}")
        print(f"  - Customers: {HostingCustomer.query.filter_by(site_id=site.id).count()}")
        print(f"  - Miner Assets: {MinerAsset.query.filter_by(site_id=site.id).count()}")
        print(f"  - Edge Devices: {EdgeDevice.query.filter_by(site_id=site.id).count()}")
        print(f"  - Price Plans: {PricePlan.query.filter_by(site_id=site.id).count()}")


if __name__ == '__main__':
    seed_control_plane_data()
