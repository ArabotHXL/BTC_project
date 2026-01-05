"""
Command State Machine Tests for Control Plane API
Tests command lifecycle state transitions
"""
import pytest
import json
import uuid
from datetime import datetime, timedelta


class TestCommandStateMachine:
    """Test command state transitions"""

    def test_command_status_transitions_pending_to_queued(
            self, app, authenticated_client, test_site, test_miner_asset, approval_policy_reboot):
        """Test command status transition: PENDING_APPROVAL -> QUEUED after approval"""
        with app.app_context():
            propose_response = authenticated_client.post(
                '/api/v1/commands/propose',
                json={
                    'site_id': test_site,
                    'command_type': 'REBOOT',
                    'payload': {'mode': 'soft'},
                    'target_ids': [test_miner_asset]
                },
                content_type='application/json'
            )
            
            assert propose_response.status_code == 201
            data = propose_response.get_json()
            assert data['status'] == 'PENDING_APPROVAL'
            command_id = data['command_id']
            
            approve_response = authenticated_client.post(
                f'/api/v1/commands/{command_id}/approve',
                json={'reason': 'Approved'},
                content_type='application/json'
            )
            
            assert approve_response.status_code == 200
            assert approve_response.get_json()['command_status'] == 'QUEUED'

    def test_command_cancellation(
            self, app, authenticated_client, test_site, test_miner_asset, approval_policy_reboot):
        """Test command cancellation via denial"""
        with app.app_context():
            propose_response = authenticated_client.post(
                '/api/v1/commands/propose',
                json={
                    'site_id': test_site,
                    'command_type': 'REBOOT',
                    'payload': {'mode': 'soft'},
                    'target_ids': [test_miner_asset]
                },
                content_type='application/json'
            )
            
            command_id = propose_response.get_json()['command_id']
            
            deny_response = authenticated_client.post(
                f'/api/v1/commands/{command_id}/deny',
                json={'reason': 'Cancelled'},
                content_type='application/json'
            )
            
            assert deny_response.status_code == 200
            assert deny_response.get_json()['command_status'] == 'CANCELLED'
            
            get_response = authenticated_client.get(f'/api/v1/commands/{command_id}')
            assert get_response.status_code == 200
            assert get_response.get_json()['command']['status'] == 'CANCELLED'

    def test_cannot_approve_cancelled_command(
            self, app, authenticated_client, test_site, test_miner_asset, approval_policy_reboot):
        """Test that cancelled commands cannot be approved"""
        with app.app_context():
            propose_response = authenticated_client.post(
                '/api/v1/commands/propose',
                json={
                    'site_id': test_site,
                    'command_type': 'REBOOT',
                    'payload': {'mode': 'soft'},
                    'target_ids': [test_miner_asset]
                },
                content_type='application/json'
            )
            
            command_id = propose_response.get_json()['command_id']
            
            authenticated_client.post(
                f'/api/v1/commands/{command_id}/deny',
                json={'reason': 'Cancelled'},
                content_type='application/json'
            )
            
            approve_response = authenticated_client.post(
                f'/api/v1/commands/{command_id}/approve',
                json={'reason': 'Trying to approve cancelled'},
                content_type='application/json'
            )
            
            assert approve_response.status_code == 400
            assert 'cannot be approved' in approve_response.get_json()['error'].lower()

    def test_command_expiry(self, app, test_site, test_user, test_miner_asset, test_edge_device):
        """Test that expired commands are not returned in polling"""
        from db import db
        from models_remote_control import RemoteCommand
        from models_control_plane import CommandTarget
        
        with app.app_context():
            expired_id = str(uuid.uuid4())
            expired_command = RemoteCommand(
                id=expired_id,
                tenant_id=test_user,
                site_id=test_site,
                requested_by_user_id=test_user,
                requested_by_role='admin',
                command_type='LED',
                payload_json={'state': 'on'},
                target_ids=[test_miner_asset],
                status='QUEUED',
                require_approval=False,
                expires_at=datetime.utcnow() - timedelta(hours=1)
            )
            db.session.add(expired_command)
            
            target = CommandTarget(
                command_id=expired_id,
                asset_id=test_miner_asset
            )
            db.session.add(target)
            db.session.commit()
            
            client = app.test_client()
            
            response = client.get(
                '/api/edge/v1/commands/poll',
                headers={'Authorization': f'Bearer {test_edge_device["token"]}'}
            )
            
            assert response.status_code == 200
            data = response.get_json()
            
            command_ids = [c['command_id'] for c in data['commands']]
            assert expired_id not in command_ids

    def test_command_get_details(self, app, authenticated_client, test_command):
        """Test getting command details"""
        with app.app_context():
            response = authenticated_client.get(f'/api/v1/commands/{test_command}')
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['command']['id'] == test_command
            assert data['command']['status'] == 'PENDING_APPROVAL'

    def test_command_list(self, app, authenticated_client, test_site, test_command):
        """Test listing commands"""
        with app.app_context():
            response = authenticated_client.get(f'/api/v1/commands?site_id={test_site}')
            
            assert response.status_code == 200
            data = response.get_json()
            assert 'commands' in data
            assert 'total' in data

    def test_edge_poll_commands(self, app, test_edge_device, queued_command):
        """Test edge device polling for commands"""
        with app.app_context():
            client = app.test_client()
            
            response = client.get(
                '/api/edge/v1/commands/poll',
                headers={'Authorization': f'Bearer {test_edge_device["token"]}'}
            )
            
            assert response.status_code == 200
            data = response.get_json()
            assert 'commands' in data
            assert 'server_time' in data
            
            command_ids = [c['command_id'] for c in data['commands']]
            assert queued_command['id'] in command_ids

    def test_edge_poll_requires_auth(self, app):
        """Test that edge polling requires authentication"""
        with app.app_context():
            client = app.test_client()
            
            response = client.get('/api/edge/v1/commands/poll')
            
            assert response.status_code == 401

    def test_edge_poll_invalid_token(self, app):
        """Test that invalid token is rejected"""
        with app.app_context():
            client = app.test_client()
            
            response = client.get(
                '/api/edge/v1/commands/poll',
                headers={'Authorization': 'Bearer invalid-token'}
            )
            
            assert response.status_code == 401


class TestRollbackCommand:
    """Test command rollback functionality"""

    def test_rollback_completed_command(
            self, app, authenticated_client, test_site, test_miner_asset, test_user, approval_policy_reboot):
        """Test creating a rollback for a completed command"""
        from db import db
        from models_remote_control import RemoteCommand
        from models_control_plane import CommandTarget
        
        with app.app_context():
            original_id = str(uuid.uuid4())
            original_cmd = RemoteCommand(
                id=original_id,
                tenant_id=test_user,
                site_id=test_site,
                requested_by_user_id=test_user,
                requested_by_role='admin',
                command_type='REBOOT',
                payload_json={'mode': 'soft'},
                target_ids=[test_miner_asset],
                status='COMPLETED',
            )
            db.session.add(original_cmd)
            
            target = CommandTarget(
                command_id=original_id,
                asset_id=test_miner_asset,
            )
            db.session.add(target)
            db.session.commit()
            
            rollback_response = authenticated_client.post(
                f'/api/v1/commands/{original_id}/rollback',
                json={'reason': 'Reverting due to issue'},
                content_type='application/json'
            )
            
            assert rollback_response.status_code == 201
            data = rollback_response.get_json()
            assert data['success'] is True
            assert data['original_command_id'] == original_id
            assert 'rollback_command_id' in data
            assert data['status'] == 'PENDING_APPROVAL'

    def test_rollback_succeeded_command(
            self, app, authenticated_client, test_site, test_miner_asset, test_user, approval_policy_reboot):
        """Test creating a rollback for a command in SUCCEEDED status"""
        from db import db
        from models_remote_control import RemoteCommand
        from models_control_plane import CommandTarget
        
        with app.app_context():
            original_id = str(uuid.uuid4())
            original_cmd = RemoteCommand(
                id=original_id,
                tenant_id=test_user,
                site_id=test_site,
                requested_by_user_id=test_user,
                requested_by_role='admin',
                command_type='REBOOT',
                payload_json={'mode': 'soft'},
                target_ids=[test_miner_asset],
                status='SUCCEEDED',
            )
            db.session.add(original_cmd)
            
            target = CommandTarget(
                command_id=original_id,
                asset_id=test_miner_asset,
            )
            db.session.add(target)
            db.session.commit()
            
            rollback_response = authenticated_client.post(
                f'/api/v1/commands/{original_id}/rollback',
                json={'reason': 'Reverting succeeded command'},
                content_type='application/json'
            )
            
            assert rollback_response.status_code == 201
            data = rollback_response.get_json()
            assert data['success'] is True
            assert data['original_command_id'] == original_id
            assert 'rollback_command_id' in data

    def test_cannot_rollback_pending_command(
            self, app, authenticated_client, test_site, test_miner_asset, approval_policy_reboot):
        """Test that pending commands cannot be rolled back"""
        with app.app_context():
            propose_response = authenticated_client.post(
                '/api/v1/commands/propose',
                json={
                    'site_id': test_site,
                    'command_type': 'REBOOT',
                    'payload': {'mode': 'soft'},
                    'target_ids': [test_miner_asset]
                },
                content_type='application/json'
            )
            
            command_id = propose_response.get_json()['command_id']
            
            rollback_response = authenticated_client.post(
                f'/api/v1/commands/{command_id}/rollback',
                json={'reason': 'Trying to rollback pending'},
                content_type='application/json'
            )
            
            assert rollback_response.status_code == 400
            assert 'Cannot rollback' in rollback_response.get_json()['error']

    def test_rollback_requires_approval(
            self, app, authenticated_client, test_site, test_miner_asset, test_user, approval_policy_reboot):
        """Test that rollback commands require approval like regular commands"""
        from db import db
        from models_remote_control import RemoteCommand
        from models_control_plane import CommandTarget
        
        with app.app_context():
            original_id = str(uuid.uuid4())
            original_cmd = RemoteCommand(
                id=original_id,
                tenant_id=test_user,
                site_id=test_site,
                requested_by_user_id=test_user,
                requested_by_role='admin',
                command_type='REBOOT',
                payload_json={'mode': 'soft'},
                target_ids=[test_miner_asset],
                status='COMPLETED',
            )
            db.session.add(original_cmd)
            
            target = CommandTarget(
                command_id=original_id,
                asset_id=test_miner_asset,
            )
            db.session.add(target)
            db.session.commit()
            
            rollback_response = authenticated_client.post(
                f'/api/v1/commands/{original_id}/rollback',
                json={'reason': 'Rollback test'},
                content_type='application/json'
            )
            
            data = rollback_response.get_json()
            rollback_id = data['rollback_command_id']
            
            approve_response = authenticated_client.post(
                f'/api/v1/commands/{rollback_id}/approve',
                json={'reason': 'Approved rollback'},
                content_type='application/json'
            )
            
            assert approve_response.status_code == 200
            assert approve_response.get_json()['command_status'] == 'QUEUED'
