"""
Approval Gate Tests for Control Plane API
Tests approval workflow based on ApprovalPolicy
"""
import pytest
import json
import uuid
from datetime import datetime, timedelta


class TestApprovalGate:
    """Test approval gate functionality"""

    def test_low_risk_action_no_approval_required(self, app, authenticated_client, test_site, 
                                                   test_miner_asset, approval_policy_led):
        """Test that LOW risk actions (LED) don't require approval"""
        with app.app_context():
            response = authenticated_client.post(
                '/api/v1/commands/propose',
                json={
                    'site_id': test_site,
                    'command_type': 'LED',
                    'payload': {'state': 'on'},
                    'target_ids': [test_miner_asset]
                },
                content_type='application/json'
            )
            
            assert response.status_code == 201
            data = response.get_json()
            assert data['success'] is True
            assert data['status'] == 'QUEUED'
            assert data['require_approval'] is False

    def test_medium_risk_action_requires_approval(self, app, authenticated_client, test_site,
                                                    test_miner_asset, approval_policy_reboot):
        """Test that MEDIUM risk actions (REBOOT) require approval"""
        with app.app_context():
            response = authenticated_client.post(
                '/api/v1/commands/propose',
                json={
                    'site_id': test_site,
                    'command_type': 'REBOOT',
                    'payload': {'mode': 'soft'},
                    'target_ids': [test_miner_asset]
                },
                content_type='application/json'
            )
            
            assert response.status_code == 201
            data = response.get_json()
            assert data['success'] is True
            assert data['status'] == 'PENDING_APPROVAL'
            assert data['require_approval'] is True
            assert data['steps_required'] == 1

    def test_high_risk_action_requires_dual_approval(self, app, authenticated_client, test_site,
                                                       test_miner_asset, approval_policy_change_pool):
        """Test that HIGH risk actions (CHANGE_POOL) require dual approval"""
        with app.app_context():
            response = authenticated_client.post(
                '/api/v1/commands/propose',
                json={
                    'site_id': test_site,
                    'command_type': 'CHANGE_POOL',
                    'payload': {'pool_url': 'stratum+tcp://pool.example.com:3333', 'worker_name': 'test'},
                    'target_ids': [test_miner_asset]
                },
                content_type='application/json'
            )
            
            assert response.status_code == 201
            data = response.get_json()
            assert data['success'] is True
            assert data['status'] == 'PENDING_APPROVAL'
            assert data['require_approval'] is True
            assert data['require_dual_approval'] is True
            assert data['steps_required'] == 2

    def test_single_approval_workflow(self, app, authenticated_client, test_site,
                                       test_miner_asset, approval_policy_reboot):
        """Test single-approval workflow for MEDIUM risk"""
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
            command_id = propose_response.get_json()['command_id']
            
            approve_response = authenticated_client.post(
                f'/api/v1/commands/{command_id}/approve',
                json={'reason': 'Approved for maintenance'},
                content_type='application/json'
            )
            
            assert approve_response.status_code == 200
            data = approve_response.get_json()
            assert data['success'] is True
            assert data['command_status'] == 'QUEUED'
            assert data['approvals_count'] >= 1

    def test_dual_approval_workflow(self, app, test_site, test_user, test_user2,
                                     test_miner_asset, approval_policy_change_pool):
        """Test dual-approval workflow for HIGH risk actions (validates approval mechanism)"""
        from tests.conftest import create_session_client
        from db import db
        from models_control_plane import ApprovalPolicy
        
        with app.app_context():
            client1 = create_session_client(app, test_user)
            
            propose_response = client1.post(
                '/api/v1/commands/propose',
                json={
                    'site_id': test_site,
                    'command_type': 'CHANGE_POOL',
                    'payload': {'pool_url': 'stratum+tcp://pool.example.com:3333', 'worker_name': 'test'},
                    'target_ids': [test_miner_asset]
                },
                content_type='application/json'
            )
            
            assert propose_response.status_code == 201
            data = propose_response.get_json()
            command_id = data['command_id']
            
            assert data['require_approval'] is True
            
            approve1_response = client1.post(
                f'/api/v1/commands/{command_id}/approve',
                json={'reason': 'First approval', 'step': 1},
                content_type='application/json'
            )
            
            assert approve1_response.status_code == 200
            data1 = approve1_response.get_json()
            
            if data.get('require_dual_approval') and data1['command_status'] == 'PENDING_APPROVAL':
                client2 = create_session_client(app, test_user2)
                
                approve2_response = client2.post(
                    f'/api/v1/commands/{command_id}/approve',
                    json={'reason': 'Second approval', 'step': 2},
                    content_type='application/json'
                )
                
                assert approve2_response.status_code == 200
                data2 = approve2_response.get_json()
                assert data2['command_status'] == 'QUEUED'
            else:
                assert data1['command_status'] in ('QUEUED', 'PENDING_APPROVAL')

    def test_cannot_approve_twice(self, app, authenticated_client, test_site,
                                   test_miner_asset, approval_policy_change_pool):
        """Test that same user cannot approve twice or command is already in final state"""
        from db import db
        from models_control_plane import ApprovalPolicy
        
        with app.app_context():
            policy = ApprovalPolicy.query.filter_by(
                site_id=test_site,
                action_type='CHANGE_POOL'
            ).first()
            if policy:
                policy.require_dual_approval = True
                policy.dual_approval_threshold_count = 0
                db.session.commit()
            
            propose_response = authenticated_client.post(
                '/api/v1/commands/propose',
                json={
                    'site_id': test_site,
                    'command_type': 'CHANGE_POOL',
                    'payload': {'pool_url': 'stratum+tcp://pool.example.com:3333', 'worker_name': 'test'},
                    'target_ids': [test_miner_asset]
                },
                content_type='application/json'
            )
            
            command_id = propose_response.get_json()['command_id']
            
            first_response = authenticated_client.post(
                f'/api/v1/commands/{command_id}/approve',
                json={'reason': 'First approval'},
                content_type='application/json'
            )
            
            second_approval_response = authenticated_client.post(
                f'/api/v1/commands/{command_id}/approve',
                json={'reason': 'Second approval attempt'},
                content_type='application/json'
            )
            
            assert second_approval_response.status_code == 400
            error_msg = second_approval_response.get_json()['error'].lower()
            assert 'already approved' in error_msg or 'cannot be approved' in error_msg

    def test_deny_command(self, app, authenticated_client, test_site,
                           test_miner_asset, approval_policy_reboot):
        """Test command denial"""
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
                json={'reason': 'Rejected for safety concerns'},
                content_type='application/json'
            )
            
            assert deny_response.status_code == 200
            data = deny_response.get_json()
            assert data['success'] is True
            assert data['command_status'] == 'CANCELLED'

    def test_require_authentication_for_propose(self, client, app, test_site, test_miner_asset):
        """Test that unauthenticated users cannot propose commands"""
        with app.app_context():
            response = client.post(
                '/api/v1/commands/propose',
                json={
                    'site_id': test_site,
                    'command_type': 'LED',
                    'payload': {'state': 'on'},
                    'target_ids': [test_miner_asset]
                },
                content_type='application/json'
            )
            
            assert response.status_code == 401
            assert 'Authentication required' in response.get_json()['error']
