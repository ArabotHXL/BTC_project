"""
HashInsight Enterprise - Test Configuration
Control Plane API Test Fixtures

Provides pytest fixtures for Flask integration testing with in-memory SQLite.
"""

import os
import sys
import uuid
import pytest
from datetime import datetime, timedelta

os.environ['SESSION_SECRET'] = 'test-secret-key-for-testing-only'
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['TESTING'] = 'true'


@pytest.fixture(scope='function')
def app():
    """Create Flask application for testing with SQLite"""
    original_db_url = os.environ.get('DATABASE_URL')
    os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
    
    from flask import Flask
    from db import db, Base
    
    test_app = Flask(__name__)
    test_app.config['TESTING'] = True
    test_app.config['WTF_CSRF_ENABLED'] = False
    test_app.config['SECRET_KEY'] = 'test-secret-key'
    test_app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    test_app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {}
    test_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db.init_app(test_app)
    
    from api.control_plane_api import control_plane_bp
    from api.legacy_adapter import legacy_bp
    from api.portal_lite_api import portal_bp
    
    test_app.register_blueprint(control_plane_bp)
    test_app.register_blueprint(legacy_bp)
    test_app.register_blueprint(portal_bp)
    
    with test_app.app_context():
        from models import UserAccess, HostingSite
        from models_device_encryption import EdgeDevice
        from models_remote_control import RemoteCommand, RemoteCommandResult
        from models_control_plane import (
            Zone, HostingCustomer, MinerAsset, MinerCapability,
            PricePlan, PricePlanVersion, DemandLedgerMonthly, Demand15Min,
            CommandApproval, CommandTarget, RetentionPolicy, AuditEvent,
            ApprovalPolicy
        )
        
        db.create_all()
    
    yield test_app
    
    with test_app.app_context():
        db.drop_all()
    
    if original_db_url:
        os.environ['DATABASE_URL'] = original_db_url


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Create test CLI runner"""
    return app.test_cli_runner()


@pytest.fixture
def test_site(app):
    """Create a test hosting site"""
    from db import db
    from models import HostingSite
    
    with app.app_context():
        site = HostingSite(
            name='Test Mining Site',
            slug=f'test-site-{uuid.uuid4().hex[:8]}',
            location='Test Location',
            capacity_mw=100.0,
            electricity_rate=0.05,
            operator_name='Test Operator'
        )
        db.session.add(site)
        db.session.commit()
        site_id = site.id
        
    yield site_id


@pytest.fixture
def test_user(app, test_site):
    """Create a test user"""
    from db import db
    from models import UserAccess
    
    with app.app_context():
        user = UserAccess(
            name='Test User',
            email=f'testuser-{uuid.uuid4().hex[:8]}@example.com',
            username=f'testuser-{uuid.uuid4().hex[:8]}',
            role='admin',
            access_days=365
        )
        db.session.add(user)
        db.session.commit()
        user_id = user.id
        
    yield user_id


@pytest.fixture
def test_user2(app, test_site):
    """Create a second test user for dual approval tests"""
    from db import db
    from models import UserAccess
    
    with app.app_context():
        user = UserAccess(
            name='Test User 2',
            email=f'testuser2-{uuid.uuid4().hex[:8]}@example.com',
            username=f'testuser2-{uuid.uuid4().hex[:8]}',
            role='admin',
            access_days=365
        )
        db.session.add(user)
        db.session.commit()
        user_id = user.id
        
    yield user_id


@pytest.fixture
def test_customer(app, test_site, test_user):
    """Create a test customer (linked to test_user)"""
    from db import db
    from models_control_plane import HostingCustomer
    
    with app.app_context():
        customer = HostingCustomer(
            site_id=test_site,
            user_id=test_user,
            name='Customer 1',
            company='Test Company',
            email=f'customer1-{uuid.uuid4().hex[:8]}@example.com'
        )
        db.session.add(customer)
        db.session.commit()
        customer_id = customer.id
        
    yield customer_id


@pytest.fixture
def test_customer2(app, test_site, test_user2):
    """Create a second test customer for ABAC tests"""
    from db import db
    from models_control_plane import HostingCustomer
    
    with app.app_context():
        customer = HostingCustomer(
            site_id=test_site,
            user_id=test_user2,
            name='Customer 2',
            company='Other Company',
            email=f'customer2-{uuid.uuid4().hex[:8]}@example.com'
        )
        db.session.add(customer)
        db.session.commit()
        customer_id = customer.id
        
    yield customer_id


@pytest.fixture
def test_miner_asset(app, test_site, test_customer):
    """Create a test miner asset owned by customer 1"""
    from db import db
    from models_control_plane import MinerAsset
    
    with app.app_context():
        asset = MinerAsset(
            site_id=test_site,
            customer_id=test_customer,
            model='Antminer S19 Pro',
            vendor='Bitmain',
            serial_number=f'TEST-MINER-{uuid.uuid4().hex[:8]}',
            hashrate_th=110.0,
            power_w=3250.0
        )
        db.session.add(asset)
        db.session.commit()
        asset_id = asset.id
        
    yield asset_id


@pytest.fixture
def test_miner_asset2(app, test_site, test_customer2):
    """Create a test miner asset owned by customer 2 (for ABAC tests)"""
    from db import db
    from models_control_plane import MinerAsset
    
    with app.app_context():
        asset = MinerAsset(
            site_id=test_site,
            customer_id=test_customer2,
            model='Antminer S19 Pro',
            vendor='Bitmain',
            serial_number=f'TEST-MINER-{uuid.uuid4().hex[:8]}',
            hashrate_th=110.0,
            power_w=3250.0
        )
        db.session.add(asset)
        db.session.commit()
        asset_id = asset.id
        
    yield asset_id


@pytest.fixture
def test_edge_device(app, test_site, test_user):
    """Create a test edge device with token"""
    from db import db
    from models_device_encryption import EdgeDevice
    
    device_token = f'test-device-token-{uuid.uuid4().hex}'
    
    with app.app_context():
        device = EdgeDevice(
            tenant_id=test_user,
            site_id=test_site,
            device_name=f'Test Edge Collector {uuid.uuid4().hex[:8]}',
            device_token=device_token,
            public_key='test-public-key',
            status='ACTIVE'
        )
        db.session.add(device)
        db.session.commit()
        device_id = device.id
        
    yield {'id': device_id, 'token': device_token}


@pytest.fixture
def approval_policy_led(app, test_site):
    """Create approval policy for LED (LOW risk, no approval required)"""
    from db import db
    from models_control_plane import ApprovalPolicy
    
    with app.app_context():
        policy = ApprovalPolicy(
            site_id=test_site,
            action_type='LED',
            risk_tier='LOW',
            require_approval=False,
            require_dual_approval=False
        )
        db.session.add(policy)
        db.session.commit()
        policy_id = policy.id
        
    yield policy_id


@pytest.fixture
def approval_policy_reboot(app, test_site):
    """Create approval policy for REBOOT (MEDIUM risk, single approval)"""
    from db import db
    from models_control_plane import ApprovalPolicy
    
    with app.app_context():
        policy = ApprovalPolicy(
            site_id=test_site,
            action_type='REBOOT',
            risk_tier='MEDIUM',
            require_approval=True,
            require_dual_approval=False
        )
        db.session.add(policy)
        db.session.commit()
        policy_id = policy.id
        
    yield policy_id


@pytest.fixture
def approval_policy_change_pool(app, test_site):
    """Create approval policy for CHANGE_POOL (HIGH risk, dual approval)"""
    from db import db
    from models_control_plane import ApprovalPolicy
    
    with app.app_context():
        policy = ApprovalPolicy(
            site_id=test_site,
            action_type='CHANGE_POOL',
            risk_tier='HIGH',
            require_approval=True,
            require_dual_approval=True,
            dual_approval_threshold_count=1
        )
        db.session.add(policy)
        db.session.commit()
        policy_id = policy.id
        
    yield policy_id


@pytest.fixture
def authenticated_client(client, app, test_user):
    """Return client with authenticated session"""
    with client.session_transaction() as sess:
        sess['user_id'] = test_user
        sess['authenticated'] = True
    return client


def create_session_client(app, user_id):
    """Helper to create an authenticated client for a specific user"""
    cl = app.test_client()
    with cl.session_transaction() as sess:
        sess['user_id'] = user_id
        sess['authenticated'] = True
    return cl


@pytest.fixture
def test_command(app, test_site, test_user, test_miner_asset):
    """Create a test command in PENDING_APPROVAL status"""
    from db import db
    from models_remote_control import RemoteCommand
    from models_control_plane import CommandTarget
    
    command_id = str(uuid.uuid4())
    
    with app.app_context():
        command = RemoteCommand(
            id=command_id,
            tenant_id=test_user,
            site_id=test_site,
            requested_by_user_id=test_user,
            requested_by_role='admin',
            command_type='REBOOT',
            payload_json={'mode': 'soft'},
            target_ids=[test_miner_asset],
            status='PENDING_APPROVAL',
            require_approval=True,
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        db.session.add(command)
        
        target = CommandTarget(
            command_id=command_id,
            asset_id=test_miner_asset
        )
        db.session.add(target)
        db.session.commit()
        
    yield command_id


@pytest.fixture
def queued_command(app, test_site, test_user, test_miner_asset, test_edge_device):
    """Create a test command in QUEUED status for edge polling"""
    from db import db
    from models_remote_control import RemoteCommand
    from models_control_plane import CommandTarget
    
    command_id = str(uuid.uuid4())
    
    with app.app_context():
        command = RemoteCommand(
            id=command_id,
            tenant_id=test_user,
            site_id=test_site,
            requested_by_user_id=test_user,
            requested_by_role='admin',
            command_type='LED',
            payload_json={'state': 'on'},
            target_ids=[test_miner_asset],
            status='QUEUED',
            require_approval=False,
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        db.session.add(command)
        
        target = CommandTarget(
            command_id=command_id,
            asset_id=test_miner_asset
        )
        db.session.add(target)
        db.session.commit()
        
    yield {'id': command_id, 'target_ids': [test_miner_asset]}
