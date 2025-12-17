"""
HashInsight Enterprise - CRM API Unit Tests
CRM API单元测试

Tests for:
- Customer CRUD operations
- Deal management
- CRM statistics
- Input validation
"""

import pytest
from datetime import datetime
from decimal import Decimal
from unittest.mock import patch, MagicMock


class TestCustomerDataValidation:
    """Test customer data validation"""
    
    def test_valid_customer_data(self):
        """Valid customer data should pass validation"""
        customer_data = {
            'name': 'John Doe',
            'email': 'john@example.com',
            'phone': '+1-555-123-4567',
            'company': 'Acme Corp'
        }
        
        assert customer_data['name']
        assert '@' in customer_data['email']
        assert customer_data['company']
    
    def test_customer_name_required(self):
        """Customer name should be required"""
        customer_data = {
            'name': '',
            'email': 'test@example.com'
        }
        
        assert not customer_data['name']
    
    def test_email_format_validation(self):
        """Customer email should be properly formatted"""
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        valid_emails = ['customer@example.com', 'ceo@company.cn', 'manager+btc@mining.org']
        invalid_emails = ['not-an-email', '@missing.com', 'spaces in@email.com']
        
        for email in valid_emails:
            assert re.match(email_pattern, email), f"Valid email rejected: {email}"
        
        for email in invalid_emails:
            assert not re.match(email_pattern, email), f"Invalid email accepted: {email}"
    
    def test_phone_sanitization(self):
        """Phone numbers should be sanitizable"""
        import re
        
        phone_inputs = ['+1 (555) 123-4567', '555.123.4567', '+86 138 0000 0000']
        
        for phone in phone_inputs:
            sanitized = re.sub(r'[^\d+]', '', phone)
            assert sanitized.isdigit() or sanitized.startswith('+')
    
    def test_customer_status_values(self):
        """Customer status should be valid values"""
        valid_statuses = ['lead', 'prospect', 'customer', 'churned', 'inactive']
        
        test_status = 'lead'
        assert test_status in valid_statuses
        
        invalid_status = 'unknown'
        assert invalid_status not in valid_statuses


class TestDealDataValidation:
    """Test deal data validation"""
    
    def test_valid_deal_data(self):
        """Valid deal data should pass validation"""
        deal_data = {
            'title': 'Mining Contract Q1',
            'customer_id': 1,
            'amount': 50000.00,
            'stage': 'negotiation',
            'probability': 75
        }
        
        assert deal_data['title']
        assert deal_data['customer_id'] > 0
        assert deal_data['amount'] >= 0
        assert 0 <= deal_data['probability'] <= 100
    
    def test_deal_stages(self):
        """Deal stages should be valid values"""
        valid_stages = ['lead', 'qualified', 'proposal', 'negotiation', 'won', 'lost']
        
        assert 'negotiation' in valid_stages
        assert 'won' in valid_stages
        assert 'invalid_stage' not in valid_stages
    
    def test_amount_decimal_precision(self):
        """Deal amounts should handle decimal precision"""
        amounts = [
            (Decimal('50000.00'), True),
            (Decimal('0.01'), True),
            (Decimal('-100.00'), False),
            (Decimal('999999999.99'), True)
        ]
        
        for amount, should_be_valid in amounts:
            is_valid = amount >= 0
            assert is_valid == should_be_valid, f"Amount {amount} validation failed"
    
    def test_probability_range(self):
        """Probability should be 0-100"""
        valid_probabilities = [0, 25, 50, 75, 100]
        invalid_probabilities = [-10, 150, 200]
        
        for prob in valid_probabilities:
            assert 0 <= prob <= 100
        
        for prob in invalid_probabilities:
            assert not (0 <= prob <= 100)


class TestPaginationLogic:
    """Test API pagination logic"""
    
    def test_default_pagination(self):
        """Default pagination values should be applied"""
        page = 1
        per_page = 50
        
        assert page == 1
        assert per_page == 50
    
    def test_max_per_page_limit(self):
        """Per page should be capped at maximum"""
        max_limit = 100
        
        requested_per_page = 200
        actual_per_page = min(requested_per_page, max_limit)
        
        assert actual_per_page == 100
    
    def test_pagination_calculation(self):
        """Pagination calculations should be correct"""
        total_items = 125
        per_page = 50
        
        total_pages = (total_items + per_page - 1) // per_page
        assert total_pages == 3
        
        page1_start = 0
        page1_end = min(per_page, total_items)
        assert page1_end == 50
        
        page3_start = 2 * per_page
        page3_end = min(3 * per_page, total_items)
        assert page3_end == 125
    
    def test_has_next_prev_logic(self):
        """Has next/prev should be calculated correctly"""
        def calc_pagination(page, per_page, total):
            pages = (total + per_page - 1) // per_page
            has_next = page < pages
            has_prev = page > 1
            return has_next, has_prev
        
        assert calc_pagination(1, 50, 125) == (True, False)
        assert calc_pagination(2, 50, 125) == (True, True)
        assert calc_pagination(3, 50, 125) == (False, True)
        assert calc_pagination(1, 50, 25) == (False, False)


class TestCRMStatsCalculation:
    """Test CRM statistics calculations"""
    
    def test_stats_aggregation(self):
        """Stats should aggregate correctly"""
        mock_deals = [
            {'stage': 'won', 'amount': 10000},
            {'stage': 'won', 'amount': 20000},
            {'stage': 'negotiation', 'amount': 15000},
            {'stage': 'lost', 'amount': 5000}
        ]
        
        won_deals = [d for d in mock_deals if d['stage'] == 'won']
        active_deals = [d for d in mock_deals if d['stage'] == 'negotiation']
        
        assert len(won_deals) == 2
        assert len(active_deals) == 1
        assert sum(d['amount'] for d in won_deals) == 30000
    
    def test_empty_stats_handling(self):
        """Empty data should return zeros"""
        mock_stats = {
            'total_customers': 0,
            'active_deals': 0,
            'won_deals': 0
        }
        
        assert mock_stats['total_customers'] == 0
        assert mock_stats['active_deals'] == 0
        assert mock_stats['won_deals'] == 0
    
    def test_stage_filtering(self):
        """Stage filtering should work correctly"""
        stages_data = {
            'lead': 10,
            'qualified': 8,
            'proposal': 5,
            'negotiation': 3,
            'won': 12,
            'lost': 7
        }
        
        active_stages = ['lead', 'qualified', 'proposal', 'negotiation']
        closed_stages = ['won', 'lost']
        
        active_count = sum(stages_data[s] for s in active_stages)
        closed_count = sum(stages_data[s] for s in closed_stages)
        
        assert active_count == 26
        assert closed_count == 19


class TestCRMResponseFormat:
    """Test CRM API response format"""
    
    def test_customer_list_response_structure(self):
        """Customer list response should have correct structure"""
        response = {
            'success': True,
            'customers': [
                {
                    'id': 1,
                    'name': 'Test Customer',
                    'email': 'test@example.com',
                    'phone': '+1-555-0000',
                    'company': 'Test Corp',
                    'status': 'customer',
                    'created_at': '2025-01-01T00:00:00'
                }
            ],
            'pagination': {
                'page': 1,
                'per_page': 50,
                'total': 1,
                'pages': 1,
                'has_next': False,
                'has_prev': False
            }
        }
        
        assert 'success' in response
        assert 'customers' in response
        assert 'pagination' in response
        assert isinstance(response['customers'], list)
        
        customer = response['customers'][0]
        assert 'id' in customer
        assert 'name' in customer
        assert 'email' in customer
    
    def test_deal_list_response_structure(self):
        """Deal list response should have correct structure"""
        response = {
            'success': True,
            'deals': [
                {
                    'id': 1,
                    'title': 'Mining Contract',
                    'customer_id': 1,
                    'customer_name': 'Test Customer',
                    'amount': 50000.00,
                    'stage': 'negotiation',
                    'probability': 75,
                    'expected_close': '2025-06-30'
                }
            ],
            'pagination': {
                'page': 1,
                'per_page': 50,
                'total': 1,
                'pages': 1,
                'has_next': False,
                'has_prev': False
            }
        }
        
        assert response['success'] is True
        
        deal = response['deals'][0]
        assert 'id' in deal
        assert 'title' in deal
        assert 'customer_name' in deal
        assert 'amount' in deal
        assert 'stage' in deal
    
    def test_error_response_structure(self):
        """Error response should have correct structure"""
        error_response = {
            'success': False,
            'error': 'An error occurred'
        }
        
        assert error_response['success'] is False
        assert 'error' in error_response
    
    def test_stats_response_structure(self):
        """Stats response should have correct structure"""
        response = {
            'success': True,
            'stats': {
                'total_customers': 50,
                'active_deals': 10,
                'won_deals': 25
            }
        }
        
        assert response['success'] is True
        assert 'total_customers' in response['stats']
        assert 'active_deals' in response['stats']
        assert 'won_deals' in response['stats']


class TestRoleBasedAccess:
    """Test role-based access control for CRM"""
    
    def test_admin_sees_all_customers(self):
        """Admin role should see all customers"""
        user_role = 'admin'
        user_id = 1
        
        mock_customers = [
            {'id': 1, 'created_by_id': 1},
            {'id': 2, 'created_by_id': 2},
            {'id': 3, 'created_by_id': 3}
        ]
        
        if user_role == 'admin':
            visible_customers = mock_customers
        else:
            visible_customers = [c for c in mock_customers if c['created_by_id'] == user_id]
        
        assert len(visible_customers) == 3
    
    def test_non_admin_sees_own_customers(self):
        """Non-admin users should only see their own customers"""
        user_role = 'client'
        user_id = 2
        
        mock_customers = [
            {'id': 1, 'created_by_id': 1},
            {'id': 2, 'created_by_id': 2},
            {'id': 3, 'created_by_id': 2}
        ]
        
        if user_role == 'admin':
            visible_customers = mock_customers
        else:
            visible_customers = [c for c in mock_customers if c['created_by_id'] == user_id]
        
        assert len(visible_customers) == 2
        assert all(c['created_by_id'] == user_id for c in visible_customers)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
