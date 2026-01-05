"""
ABAC Isolation Tests for Control Plane API
Tests Attribute-Based Access Control for customer data isolation
"""
import pytest
import json
import uuid
from datetime import datetime, timedelta


class TestABACIsolation:
    """Test ABAC isolation for customer data"""

    def test_customer_can_only_see_own_miners(self, app, test_site, test_user, test_user2,
                                               test_customer, test_customer2,
                                               test_miner_asset, test_miner_asset2):
        """Test that customers can only see their own MinerAssets"""
        from tests.conftest import create_session_client
        
        with app.app_context():
            client1 = create_session_client(app, test_user)
            
            response1 = client1.get('/api/v1/portal/my-miners')
            
            assert response1.status_code == 200
            data1 = response1.get_json()
            
            miner_ids = [m['id'] for m in data1.get('miners', [])]
            assert test_miner_asset in miner_ids
            assert test_miner_asset2 not in miner_ids

    def test_customer_cannot_propose_command_on_other_customer_assets(
            self, app, test_site, test_user, test_user2,
            test_customer, test_customer2, test_miner_asset2, approval_policy_led):
        """Test that customers cannot propose commands on other customers' assets"""
        from tests.conftest import create_session_client
        
        with app.app_context():
            client1 = create_session_client(app, test_user)
            
            response = client1.post(
                '/api/v1/commands/propose',
                json={
                    'site_id': test_site,
                    'command_type': 'LED',
                    'payload': {'state': 'on'},
                    'target_ids': [test_miner_asset2]
                },
                content_type='application/json'
            )
            
            assert response.status_code == 403
            error_msg = response.get_json()['error']
            assert 'ABAC violation' in error_msg or 'Access denied' in error_msg

    def test_customer_cannot_approve_other_customer_command(
            self, app, test_site, test_user, test_user2,
            test_customer, test_customer2, test_miner_asset2, approval_policy_reboot):
        """Test that customers cannot approve commands affecting other customers' assets"""
        from tests.conftest import create_session_client
        from db import db
        from models_remote_control import RemoteCommand
        from models_control_plane import CommandTarget
        
        with app.app_context():
            command_id = str(uuid.uuid4())
            command = RemoteCommand(
                id=command_id,
                tenant_id=test_user2,
                site_id=test_site,
                requested_by_user_id=test_user2,
                requested_by_role='admin',
                command_type='REBOOT',
                payload_json={'mode': 'soft'},
                target_ids=[test_miner_asset2],
                status='PENDING_APPROVAL',
                require_approval=True,
                expires_at=datetime.utcnow() + timedelta(hours=24)
            )
            db.session.add(command)
            
            target = CommandTarget(
                command_id=command_id,
                asset_id=test_miner_asset2
            )
            db.session.add(target)
            db.session.commit()
            
            client1 = create_session_client(app, test_user)
            
            response = client1.post(
                f'/api/v1/commands/{command_id}/approve',
                json={'reason': 'Trying to approve other customer command'},
                content_type='application/json'
            )
            
            assert response.status_code == 403
            assert 'Access denied' in response.get_json()['error']

    def test_customer_cannot_view_other_customer_command(
            self, app, test_site, test_user, test_user2,
            test_customer, test_customer2, test_miner_asset2):
        """Test access denied when trying to view other customer's command"""
        from tests.conftest import create_session_client
        from db import db
        from models_remote_control import RemoteCommand
        from models_control_plane import CommandTarget
        
        with app.app_context():
            command_id = str(uuid.uuid4())
            command = RemoteCommand(
                id=command_id,
                tenant_id=test_user2,
                site_id=test_site,
                requested_by_user_id=test_user2,
                requested_by_role='admin',
                command_type='LED',
                payload_json={'state': 'on'},
                target_ids=[test_miner_asset2],
                status='QUEUED',
                require_approval=False,
                expires_at=datetime.utcnow() + timedelta(hours=24)
            )
            db.session.add(command)
            
            target = CommandTarget(
                command_id=command_id,
                asset_id=test_miner_asset2
            )
            db.session.add(target)
            db.session.commit()
            
            client1 = create_session_client(app, test_user)
            
            response = client1.get(f'/api/v1/commands/{command_id}')
            
            assert response.status_code == 403
            assert 'Access denied' in response.get_json()['error']

    def test_customer_list_commands_filters_by_ownership(
            self, app, test_site, test_user, test_user2,
            test_customer, test_customer2, test_miner_asset, test_miner_asset2):
        """Test that list commands filters by customer ownership"""
        from tests.conftest import create_session_client
        from db import db
        from models_remote_control import RemoteCommand
        from models_control_plane import CommandTarget
        
        with app.app_context():
            cmd1_id = str(uuid.uuid4())
            cmd1 = RemoteCommand(
                id=cmd1_id,
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
            db.session.add(cmd1)
            target1 = CommandTarget(command_id=cmd1_id, asset_id=test_miner_asset)
            db.session.add(target1)
            
            cmd2_id = str(uuid.uuid4())
            cmd2 = RemoteCommand(
                id=cmd2_id,
                tenant_id=test_user2,
                site_id=test_site,
                requested_by_user_id=test_user2,
                requested_by_role='admin',
                command_type='LED',
                payload_json={'state': 'off'},
                target_ids=[test_miner_asset2],
                status='QUEUED',
                require_approval=False,
                expires_at=datetime.utcnow() + timedelta(hours=24)
            )
            db.session.add(cmd2)
            target2 = CommandTarget(command_id=cmd2_id, asset_id=test_miner_asset2)
            db.session.add(target2)
            
            db.session.commit()
            
            client1 = create_session_client(app, test_user)
            
            response = client1.get('/api/v1/commands')
            
            assert response.status_code == 200
            data = response.get_json()
            
            command_ids = [c['id'] for c in data['commands']]
            assert cmd1_id in command_ids
            assert cmd2_id not in command_ids

    def test_ip_addresses_not_allowed_in_payload(self, app, authenticated_client, test_site, test_miner_asset):
        """Test that IP addresses are blocked from command payloads (cloud security)"""
        with app.app_context():
            response = authenticated_client.post(
                '/api/v1/commands/propose',
                json={
                    'site_id': test_site,
                    'command_type': 'LED',
                    'payload': {'state': 'on', 'ip': '192.168.1.1'},
                    'target_ids': [test_miner_asset]
                },
                content_type='application/json'
            )
            
            assert response.status_code == 400
            assert 'IP addresses' in response.get_json()['error']
