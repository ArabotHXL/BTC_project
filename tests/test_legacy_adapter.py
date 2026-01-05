"""
Legacy Adapter Tests for Control Plane API
Tests deprecated /api/collector/* endpoints
"""
import pytest
import json
import uuid
from datetime import datetime, timedelta


class TestLegacyAdapter:
    """Test legacy API adapter endpoints"""

    def test_legacy_pending_commands_returns_deprecated_notice(
            self, app, test_edge_device, queued_command):
        """Test /api/collector/commands/pending returns deprecated notice"""
        with app.app_context():
            client = app.test_client()
            
            response = client.get(
                '/api/collector/commands/pending',
                headers={'Authorization': f'Bearer {test_edge_device["token"]}'}
            )
            
            assert response.status_code == 200
            data = response.get_json()
            
            assert '_deprecated' in data
            assert data['_deprecated'] is True
            assert '_deprecation_notice' in data
            assert '2026-06-01' in data['_deprecation_notice']
            assert 'commands' in data

    def test_legacy_pending_commands_returns_queued_commands(
            self, app, test_edge_device, queued_command):
        """Test /api/collector/commands/pending returns queued commands"""
        with app.app_context():
            client = app.test_client()
            
            response = client.get(
                '/api/collector/commands/pending',
                headers={'Authorization': f'Bearer {test_edge_device["token"]}'}
            )
            
            assert response.status_code == 200
            data = response.get_json()
            
            assert 'commands' in data
            command_ids = [c['command_id'] for c in data['commands']]
            assert queued_command['id'] in command_ids

    def test_legacy_requires_auth(self, app):
        """Test that legacy endpoints require authentication"""
        with app.app_context():
            client = app.test_client()
            
            response = client.get('/api/collector/commands/pending')
            
            assert response.status_code == 401
            assert '_deprecated' in response.get_json()

    def test_legacy_invalid_token(self, app):
        """Test that invalid token is rejected"""
        with app.app_context():
            client = app.test_client()
            
            response = client.get(
                '/api/collector/commands/pending',
                headers={'Authorization': 'Bearer invalid-token'}
            )
            
            assert response.status_code == 401
            assert '_deprecated' in response.get_json()

    def test_legacy_api_key_header(self, app, test_edge_device, queued_command):
        """Test legacy X-API-Key header authentication"""
        with app.app_context():
            client = app.test_client()
            
            response = client.get(
                '/api/collector/commands/pending',
                headers={'X-API-Key': test_edge_device["token"]}
            )
            
            assert response.status_code == 200
            data = response.get_json()
            assert '_deprecated' in data

    def test_legacy_command_not_found(self, app, test_edge_device):
        """Test 404 for non-existent command"""
        with app.app_context():
            client = app.test_client()
            
            response = client.post(
                '/api/collector/commands/non-existent-id/result',
                headers={'Authorization': f'Bearer {test_edge_device["token"]}'},
                json={
                    'miner_id': 1,
                    'status': 'SUCCEEDED'
                },
                content_type='application/json'
            )
            
            assert response.status_code == 404
            assert '_deprecated' in response.get_json()

    def test_legacy_access_denied_other_site(
            self, app, test_site, test_user, test_miner_asset, test_edge_device):
        """Test access denied for command from different site"""
        from db import db
        from models import HostingSite, UserAccess
        from models_device_encryption import EdgeDevice
        from models_remote_control import RemoteCommand
        from models_control_plane import CommandTarget
        
        with app.app_context():
            other_site = HostingSite(
                name='Other Site',
                slug=f'other-site-{uuid.uuid4().hex[:8]}',
                location='Other Location',
                capacity_mw=50.0,
                electricity_rate=0.06,
                operator_name='Other Operator'
            )
            db.session.add(other_site)
            db.session.commit()
            
            command_id = str(uuid.uuid4())
            command = RemoteCommand(
                id=command_id,
                tenant_id=test_user,
                site_id=other_site.id,
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
            db.session.commit()
            
            client = app.test_client()
            
            response = client.post(
                f'/api/collector/commands/{command_id}/result',
                headers={'Authorization': f'Bearer {test_edge_device["token"]}'},
                json={
                    'miner_id': test_miner_asset,
                    'status': 'SUCCEEDED'
                },
                content_type='application/json'
            )
            
            assert response.status_code == 403
            assert '_deprecated' in response.get_json()

    def test_legacy_health_endpoint(self, app):
        """Test legacy health check endpoint"""
        with app.app_context():
            client = app.test_client()
            
            response = client.get('/api/collector/health')
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['status'] == 'ok'
            assert '_deprecated' in data
            assert data['_deprecated'] is True
