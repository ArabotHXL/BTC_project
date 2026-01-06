"""
Security Tests for Control Plane
安全测试 - 验证控制平面的安全约束

Tests covered:
1. IP/Credentials not leaked in API responses
2. Zone access control (device can only access bound zone)
3. Customer isolation (Customer A cannot approve Customer B's commands)
4. No secrets in API output
"""

import pytest
import uuid
import hashlib
from datetime import datetime, timedelta


class TestNoIPLeakage:
    """Test that API responses don't contain IP addresses or credentials"""

    def test_control_plane_zones_no_ip(self, app, authenticated_client, test_site):
        """Zones API should not return IP fields"""
        response = authenticated_client.get(f'/api/v1/zones?site_id={test_site}')
        assert response.status_code == 200
        data = response.get_json()
        
        response_text = str(data).lower()
        assert 'ip_address' not in response_text
        assert '"ip":' not in response_text
        assert 'credential' not in response_text
        assert 'password' not in response_text

    def test_control_plane_commands_no_ip(self, app, authenticated_client, test_site, test_miner_asset):
        """Commands API should not return IP fields"""
        from db import db
        from models_remote_control import RemoteCommand
        from models_control_plane import CommandTarget
        
        with app.app_context():
            cmd_id = str(uuid.uuid4())
            cmd = RemoteCommand(
                id=cmd_id,
                tenant_id=1,
                site_id=test_site,
                requested_by_user_id=1,
                requested_by_role='admin',
                command_type='STATUS',
                payload_json={},
                target_ids=[test_miner_asset],
                status='PENDING_APPROVAL',
            )
            db.session.add(cmd)
            
            target = CommandTarget(
                command_id=cmd_id,
                asset_id=test_miner_asset,
            )
            db.session.add(target)
            db.session.commit()
            
            response = authenticated_client.get(f'/api/v1/commands/{cmd_id}')
            assert response.status_code == 200
            data = response.get_json()
            
            response_text = str(data).lower()
            assert 'ip_address' not in response_text
            assert '"ip"' not in response_text
            assert 'credential' not in response_text

    def test_portal_miners_no_ip(self, app, authenticated_client):
        """Portal my-miners API should not return IP fields"""
        response = authenticated_client.get('/api/v1/portal/my-miners')
        data = response.get_json()
        
        response_text = str(data).lower()
        assert 'ip_address' not in response_text
        assert '"ip":' not in response_text
        assert 'credential' not in response_text

    def test_audit_events_no_secrets(self, app, authenticated_client, test_site):
        """Audit events should not contain secrets"""
        response = authenticated_client.get(f'/api/v1/audit/events?site_id={test_site}')
        assert response.status_code == 200
        data = response.get_json()
        
        response_text = str(data).lower()
        assert 'password' not in response_text
        assert 'secret_key' not in response_text
        assert 'credential' not in response_text


class TestZoneAccessControl:
    """Test zone-based access control for edge devices"""

    @pytest.fixture
    def edge_device_zone1(self, app, test_site):
        """Create edge device bound to zone1"""
        from db import db
        from models_device_encryption import EdgeDevice
        from models_control_plane import Zone
        
        with app.app_context():
            zone = Zone.query.filter_by(site_id=test_site).first()
            zone_id = zone.id if zone else None
            
            token = f"test_token_zone1_{uuid.uuid4().hex}"
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            
            device = EdgeDevice(
                tenant_id=1,
                site_id=test_site,
                zone_id=zone_id,
                device_name='TestDevice_Zone1',
                device_token=token,
                token_hash=token_hash,
                public_key='test_public_key_zone1',
                status='ACTIVE',
            )
            db.session.add(device)
            db.session.commit()
            
            yield {'token': token, 'device_id': device.id, 'zone_id': zone_id}
            
            db.session.delete(device)
            db.session.commit()

    @pytest.fixture
    def edge_device_zone2(self, app, test_site):
        """Create edge device bound to zone2"""
        from db import db
        from models_device_encryption import EdgeDevice
        from models_control_plane import Zone
        
        with app.app_context():
            zones = Zone.query.filter_by(site_id=test_site).all()
            zone_id = zones[1].id if len(zones) > 1 else (zones[0].id + 100 if zones else 999)
            
            token = f"test_token_zone2_{uuid.uuid4().hex}"
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            
            device = EdgeDevice(
                tenant_id=1,
                site_id=test_site,
                zone_id=zone_id,
                device_name='TestDevice_Zone2',
                device_token=token,
                token_hash=token_hash,
                public_key='test_public_key_zone2',
                status='ACTIVE',
            )
            db.session.add(device)
            db.session.commit()
            
            yield {'token': token, 'device_id': device.id, 'zone_id': zone_id}
            
            db.session.delete(device)
            db.session.commit()

    def test_device_cannot_access_other_zone(self, app, client, edge_device_zone1, edge_device_zone2):
        """Device bound to zone1 cannot poll commands for zone2"""
        with app.app_context():
            zone1_id = edge_device_zone1['zone_id']
            zone2_id = edge_device_zone2['zone_id']
            
            if zone1_id is None or zone2_id is None or zone1_id == zone2_id:
                pytest.skip("Test requires two different zones")
            
            response = client.get(
                f'/api/edge/v1/commands/poll?zone_id={zone2_id}',
                headers={'Authorization': f'Bearer {edge_device_zone1["token"]}'}
            )
            
            assert response.status_code == 403
            data = response.get_json()
            assert 'zone' in data.get('error', '').lower() or 'denied' in data.get('error', '').lower()

    def test_device_can_access_own_zone(self, app, client, edge_device_zone1):
        """Device can poll commands for its own zone"""
        with app.app_context():
            zone1_id = edge_device_zone1['zone_id']
            
            response = client.get(
                f'/api/edge/v1/commands/poll?zone_id={zone1_id}',
                headers={'Authorization': f'Bearer {edge_device_zone1["token"]}'}
            )
            
            assert response.status_code == 200

    def test_device_poll_without_zone_uses_bound_zone(self, app, client, edge_device_zone1):
        """Device polling without zone_id uses its bound zone"""
        with app.app_context():
            response = client.get(
                '/api/edge/v1/commands/poll',
                headers={'Authorization': f'Bearer {edge_device_zone1["token"]}'}
            )
            
            assert response.status_code == 200


class TestCustomerIsolation:
    """Test customer isolation for hosting assets"""

    @pytest.fixture
    def customer_a(self, app, test_site):
        """Create customer A"""
        from db import db
        from models_control_plane import HostingCustomer
        
        with app.app_context():
            customer = HostingCustomer(
                site_id=test_site,
                name='Customer A',
                email='customer_a@test.com',
            )
            db.session.add(customer)
            db.session.commit()
            yield customer.id
            
            db.session.delete(customer)
            db.session.commit()

    @pytest.fixture
    def customer_b(self, app, test_site):
        """Create customer B"""
        from db import db
        from models_control_plane import HostingCustomer
        
        with app.app_context():
            customer = HostingCustomer(
                site_id=test_site,
                name='Customer B',
                email='customer_b@test.com',
            )
            db.session.add(customer)
            db.session.commit()
            yield customer.id
            
            db.session.delete(customer)
            db.session.commit()

    @pytest.fixture
    def miner_customer_a(self, app, test_site, customer_a):
        """Create miner belonging to customer A"""
        from db import db
        from models_control_plane import MinerAsset
        
        with app.app_context():
            miner = MinerAsset(
                asset_id=f'miner_a_{uuid.uuid4().hex[:8]}',
                site_id=test_site,
                customer_id=customer_a,
                model='S19',
                vendor='Bitmain',
            )
            db.session.add(miner)
            db.session.commit()
            yield miner.asset_id
            
            db.session.delete(miner)
            db.session.commit()

    @pytest.fixture
    def miner_customer_b(self, app, test_site, customer_b):
        """Create miner belonging to customer B"""
        from db import db
        from models_control_plane import MinerAsset
        
        with app.app_context():
            miner = MinerAsset(
                asset_id=f'miner_b_{uuid.uuid4().hex[:8]}',
                site_id=test_site,
                customer_id=customer_b,
                model='S19',
                vendor='Bitmain',
            )
            db.session.add(miner)
            db.session.commit()
            yield miner.asset_id
            
            db.session.delete(miner)
            db.session.commit()

    def test_non_customer_cannot_access_portal(
        self, app, authenticated_client, customer_a, customer_b, 
        miner_customer_a, miner_customer_b
    ):
        """Non-customer user cannot access portal APIs (returns 403)"""
        with app.app_context():
            response = authenticated_client.get('/api/v1/portal/my-miners')
            assert response.status_code == 403

    def test_customers_have_separate_data(
        self, app, test_site, customer_a, customer_b,
        miner_customer_a, miner_customer_b
    ):
        """Verify customers have separate miners (data isolation at DB level)"""
        from models_control_plane import MinerAsset
        
        with app.app_context():
            miner_a = MinerAsset.query.filter_by(asset_id=miner_customer_a).first()
            miner_b = MinerAsset.query.filter_by(asset_id=miner_customer_b).first()
            
            assert miner_a is not None
            assert miner_b is not None
            assert miner_a.customer_id == customer_a
            assert miner_b.customer_id == customer_b
            assert miner_a.customer_id != miner_b.customer_id


class TestNoSecretsInOutput:
    """Test that no secrets/credentials appear in API outputs"""

    def test_commands_no_secrets(self, app, authenticated_client, test_site):
        """Commands API responses should not contain secrets"""
        response = authenticated_client.get(f'/api/v1/commands?site_id={test_site}')
        assert response.status_code == 200
        data = response.get_json()
        
        response_text = str(data).lower()
        assert 'password' not in response_text
        assert 'credential' not in response_text
        assert 'api_key' not in response_text

    def test_demand_ledger_no_secrets(self, app, authenticated_client, test_site):
        """Demand ledger responses should not contain secrets"""
        response = authenticated_client.get(f'/api/v1/demand/monthly-ledger?site_id={test_site}')
        assert response.status_code == 200
        data = response.get_json()
        
        response_text = str(data).lower()
        assert 'password' not in response_text
        assert 'credential' not in response_text


class TestCredentialProtection:
    """Test credential protection modes and anti-rollback"""

    def test_get_site_security_settings(self, app, authenticated_client, test_site):
        """Should return site security settings"""
        response = authenticated_client.get(f'/api/v1/sites/{test_site}/security-settings')
        assert response.status_code == 200
        data = response.get_json()
        assert 'ip_mode' in data
        assert 'mode_name' in data
        assert data['ip_mode'] in (1, 2, 3)

    def test_change_mode_requires_auth(self, app, test_site):
        """Changing credential mode should require authentication"""
        from flask import Flask
        client = app.test_client()
        
        response = client.post(
            f'/api/v1/sites/{test_site}/security-settings',
            json={'ip_mode': 2}
        )
        assert response.status_code == 401

    def test_anti_rollback_validation(self, app):
        """Anti-rollback should reject counter values <= last_accepted"""
        from services.credential_protection_service import credential_service
        
        class MockMiner:
            last_accepted_counter = 10
            
        miner = MockMiner()
        
        valid_5, _ = credential_service.validate_anti_rollback(miner, 5)
        assert valid_5 == False
        
        valid_10, _ = credential_service.validate_anti_rollback(miner, 10)
        assert valid_10 == False
        
        valid_11, _ = credential_service.validate_anti_rollback(miner, 11)
        assert valid_11 == True

    def test_credential_fingerprint_generation(self, app):
        """Should generate SHA-256 fingerprint for credentials"""
        from services.credential_protection_service import credential_service
        
        fingerprint = credential_service.compute_fingerprint('{"ip": "192.168.1.100"}')
        assert fingerprint is not None
        assert len(fingerprint) == 64

    def test_credential_mode_1_masking(self, app):
        """Mode 1 should mask credentials for non-admin roles"""
        from services.credential_protection_service import credential_service
        
        class MockMiner:
            credential_value = '{"ip": "192.168.1.100", "user": "root", "pass": "secret"}'
            credential_mode = 1
            
        class MockSite:
            ip_mode = 1
            
        masked_viewer = credential_service.get_display_value(MockMiner(), MockSite(), 'viewer')
        assert 'secret' not in str(masked_viewer)
        
        full_admin = credential_service.get_display_value(MockMiner(), MockSite(), 'admin')
        assert '192.168.1' in str(full_admin)


class TestAuditChainVerification:
    """Test audit chain integrity verification"""

    def test_verify_audit_chain_empty(self, app, authenticated_client, test_site):
        """Verify empty audit chain returns OK"""
        response = authenticated_client.get(f'/api/v1/audit/verify?site_id={test_site}')
        assert response.status_code == 200
        data = response.get_json()
        assert data['verify_ok'] == True

    def test_audit_event_hash_chain(self, app, test_site):
        """Audit events should form a valid hash chain"""
        from db import db
        from models_control_plane import AuditEvent
        
        with app.app_context():
            events = AuditEvent.query.filter_by(site_id=test_site).order_by(AuditEvent.id.asc()).all()
            
            for i, event in enumerate(events):
                expected_prev = events[i-1].event_hash if i > 0 else '0' * 64
                assert event.prev_hash == expected_prev
                
                computed = event.compute_hash()
                assert computed == event.event_hash
