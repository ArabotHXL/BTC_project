"""
Price Plan Upload Tests for Control Plane API
Tests price plan upload functionality including JSON, CSV, and versioning
"""
import pytest
import json
import io
from datetime import datetime


class TestPricePlanUpload:
    """Test price plan upload functionality"""

    def test_json_upload(self, app, authenticated_client, test_site):
        """Test JSON price plan upload"""
        with app.app_context():
            response = authenticated_client.post(
                '/api/v1/price-plans/upload',
                json={
                    'site_id': test_site,
                    'plan_name': 'Test JSON Plan',
                    'rates': [
                        {'hour': 0, 'rate': 0.05},
                        {'hour': 1, 'rate': 0.05},
                        {'hour': 12, 'rate': 0.08},
                        {'hour': 18, 'rate': 0.10}
                    ]
                },
                query_string={'site_id': test_site, 'plan_name': 'Test JSON Plan'},
                content_type='application/json'
            )
            
            assert response.status_code == 201
            data = response.get_json()
            assert data['success'] is True
            assert 'price_plan_id' in data
            assert 'version_id' in data
            assert data['version_number'] == 1

    def test_csv_upload(self, app, authenticated_client, test_site):
        """Test CSV price plan upload"""
        with app.app_context():
            csv_content = "hour,rate\n0,0.05\n1,0.05\n12,0.08\n18,0.10\n"
            
            response = authenticated_client.post(
                '/api/v1/price-plans/upload',
                data={
                    'site_id': str(test_site),
                    'plan_name': 'Test CSV Plan',
                    'file': (io.BytesIO(csv_content.encode('utf-8')), 'rates.csv')
                },
                content_type='multipart/form-data'
            )
            
            assert response.status_code == 201
            data = response.get_json()
            assert data['success'] is True
            assert data['version_number'] == 1

    def test_version_numbering(self, app, authenticated_client, test_site):
        """Test that version numbers increment properly"""
        with app.app_context():
            response1 = authenticated_client.post(
                '/api/v1/price-plans/upload',
                json={
                    'site_id': test_site,
                    'plan_name': 'Versioned Plan',
                    'rates': [{'hour': 0, 'rate': 0.05}]
                },
                query_string={'site_id': test_site, 'plan_name': 'Versioned Plan'},
                content_type='application/json'
            )
            
            assert response1.status_code == 201
            assert response1.get_json()['version_number'] == 1
            
            response2 = authenticated_client.post(
                '/api/v1/price-plans/upload',
                json={
                    'site_id': test_site,
                    'plan_name': 'Versioned Plan',
                    'rates': [{'hour': 0, 'rate': 0.06}]
                },
                query_string={'site_id': test_site, 'plan_name': 'Versioned Plan'},
                content_type='application/json'
            )
            
            assert response2.status_code == 201
            assert response2.get_json()['version_number'] == 2
            
            response3 = authenticated_client.post(
                '/api/v1/price-plans/upload',
                json={
                    'site_id': test_site,
                    'plan_name': 'Versioned Plan',
                    'rates': [{'hour': 0, 'rate': 0.07}]
                },
                query_string={'site_id': test_site, 'plan_name': 'Versioned Plan'},
                content_type='application/json'
            )
            
            assert response3.status_code == 201
            assert response3.get_json()['version_number'] == 3

    def test_missing_data_policy_carry_forward(self, app, authenticated_client, test_site):
        """Test missing_data_policy = carry_forward"""
        with app.app_context():
            response = authenticated_client.post(
                '/api/v1/price-plans/upload',
                data={
                    'site_id': str(test_site),
                    'plan_name': 'Carry Forward Plan',
                    'missing_data_policy': 'carry_forward',
                    'file': (io.BytesIO(b"hour,rate\n0,0.05\n"), 'rates.csv')
                },
                content_type='multipart/form-data'
            )
            
            assert response.status_code == 201
            
            from models_control_plane import PricePlanVersion
            version = PricePlanVersion.query.filter_by(
                version_id=response.get_json()['version_id']
            ).first()
            assert version.missing_data_policy == 'carry_forward'

    def test_missing_data_policy_interpolate(self, app, authenticated_client, test_site):
        """Test missing_data_policy = interpolate"""
        with app.app_context():
            response = authenticated_client.post(
                '/api/v1/price-plans/upload',
                data={
                    'site_id': str(test_site),
                    'plan_name': 'Interpolate Plan',
                    'missing_data_policy': 'interpolate',
                    'file': (io.BytesIO(b"hour,rate\n0,0.05\n12,0.10\n"), 'rates.csv')
                },
                content_type='multipart/form-data'
            )
            
            assert response.status_code == 201
            
            from models_control_plane import PricePlanVersion
            version = PricePlanVersion.query.filter_by(
                version_id=response.get_json()['version_id']
            ).first()
            assert version.missing_data_policy == 'interpolate'

    def test_missing_data_policy_mark_missing(self, app, authenticated_client, test_site):
        """Test missing_data_policy = mark_missing"""
        with app.app_context():
            response = authenticated_client.post(
                '/api/v1/price-plans/upload',
                data={
                    'site_id': str(test_site),
                    'plan_name': 'Mark Missing Plan',
                    'missing_data_policy': 'mark_missing',
                    'file': (io.BytesIO(b"hour,rate\n0,0.05\n"), 'rates.csv')
                },
                content_type='multipart/form-data'
            )
            
            assert response.status_code == 201
            
            from models_control_plane import PricePlanVersion
            version = PricePlanVersion.query.filter_by(
                version_id=response.get_json()['version_id']
            ).first()
            assert version.missing_data_policy == 'mark_missing'

    def test_upload_requires_site_id(self, app, authenticated_client):
        """Test that site_id is required"""
        with app.app_context():
            response = authenticated_client.post(
                '/api/v1/price-plans/upload',
                json={
                    'plan_name': 'No Site Plan',
                    'rates': [{'hour': 0, 'rate': 0.05}]
                },
                content_type='application/json'
            )
            
            assert response.status_code == 400
            assert 'site_id' in response.get_json()['error'].lower()

    def test_upload_invalid_site(self, app, authenticated_client):
        """Test upload with invalid site_id"""
        with app.app_context():
            response = authenticated_client.post(
                '/api/v1/price-plans/upload',
                json={
                    'site_id': 99999,
                    'plan_name': 'Invalid Site Plan',
                    'rates': [{'hour': 0, 'rate': 0.05}]
                },
                query_string={'site_id': 99999, 'plan_name': 'Invalid Site Plan'},
                content_type='application/json'
            )
            
            assert response.status_code == 404
            assert 'not found' in response.get_json()['error'].lower()

    def test_upload_requires_file_or_json(self, app, authenticated_client, test_site):
        """Test that either file or JSON data is required"""
        with app.app_context():
            response = authenticated_client.post(
                '/api/v1/price-plans/upload',
                data={
                    'site_id': str(test_site),
                    'plan_name': 'Empty Plan'
                },
                content_type='multipart/form-data'
            )
            
            assert response.status_code == 400
            assert 'required' in response.get_json()['error'].lower()

    def test_upload_requires_authentication(self, client, app, test_site):
        """Test that upload requires authentication"""
        with app.app_context():
            response = client.post(
                '/api/v1/price-plans/upload',
                json={
                    'site_id': test_site,
                    'plan_name': 'Unauth Plan',
                    'rates': [{'hour': 0, 'rate': 0.05}]
                },
                query_string={'site_id': test_site},
                content_type='application/json'
            )
            
            assert response.status_code == 401

    def test_effective_from_date(self, app, authenticated_client, test_site):
        """Test setting effective_from date"""
        with app.app_context():
            effective_date = '2025-02-01T00:00:00'
            
            response = authenticated_client.post(
                '/api/v1/price-plans/upload',
                data={
                    'site_id': str(test_site),
                    'plan_name': 'Future Plan',
                    'effective_from': effective_date,
                    'file': (io.BytesIO(b"hour,rate\n0,0.05\n"), 'rates.csv')
                },
                content_type='multipart/form-data'
            )
            
            assert response.status_code == 201
            
            from models_control_plane import PricePlanVersion
            version = PricePlanVersion.query.filter_by(
                version_id=response.get_json()['version_id']
            ).first()
            assert version.effective_from.year == 2025
            assert version.effective_from.month == 2
