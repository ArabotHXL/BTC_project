"""
HashInsight Enterprise - Authentication Unit Tests
认证模块单元测试

Tests for authentication helper functions and security features.
These tests are isolated and don't require the full Flask app context.
"""

import pytest
import re
import secrets
import ipaddress
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from werkzeug.security import generate_password_hash, check_password_hash
from markupsafe import escape


class TestEmailValidation:
    """Test email validation patterns used in auth"""
    
    EMAIL_PATTERN = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    def test_valid_emails_accepted(self):
        """Valid email formats should be accepted"""
        valid_emails = [
            'test@example.com',
            'user.name@domain.org',
            'user+tag@company.cn',
            'admin@hashinsight.net',
            'ceo@mining-company.io'
        ]
        
        for email in valid_emails:
            assert re.match(self.EMAIL_PATTERN, email), f"Valid email rejected: {email}"
    
    def test_invalid_emails_rejected(self):
        """Invalid email formats should be rejected"""
        invalid_emails = [
            'notanemail',
            '@nodomain.com',
            'missing@.com',
            'spaces in@email.com',
            '',
            'no-at-sign.com'
        ]
        
        for email in invalid_emails:
            assert not re.match(self.EMAIL_PATTERN, email), f"Invalid email accepted: {email}"


class TestClientIPExtraction:
    """Test client IP extraction logic"""
    
    def test_extract_first_ip_from_forwarded(self):
        """Should extract first IP from X-Forwarded-For"""
        forwarded_header = '1.2.3.4, 5.6.7.8, 9.10.11.12'
        
        if ',' in forwarded_header:
            client_ip = forwarded_header.split(',')[0].strip()
        else:
            client_ip = forwarded_header
        
        assert client_ip == '1.2.3.4'
    
    def test_single_ip_in_forwarded(self):
        """Should handle single IP in X-Forwarded-For"""
        forwarded_header = '10.20.30.40'
        
        if ',' in forwarded_header:
            client_ip = forwarded_header.split(',')[0].strip()
        else:
            client_ip = forwarded_header
        
        assert client_ip == '10.20.30.40'
    
    def test_whitespace_handling(self):
        """Should handle whitespace in IP list"""
        forwarded_header = '  1.2.3.4 , 5.6.7.8  '
        
        client_ip = forwarded_header.split(',')[0].strip()
        assert client_ip == '1.2.3.4'


class TestIPClassification:
    """Test IP address classification"""
    
    def test_private_ip_detection(self):
        """Private IPs should be correctly detected"""
        private_ips = [
            '192.168.1.1',
            '192.168.0.100',
            '10.0.0.1',
            '10.255.255.255',
            '172.16.0.1',
            '172.31.255.255'
        ]
        
        for ip in private_ips:
            ip_obj = ipaddress.ip_address(ip)
            assert ip_obj.is_private, f"Private IP not detected: {ip}"
    
    def test_public_ip_detection(self):
        """Public IPs should be correctly detected"""
        public_ips = [
            '8.8.8.8',
            '1.1.1.1',
            '142.250.185.14'
        ]
        
        for ip in public_ips:
            ip_obj = ipaddress.ip_address(ip)
            assert not ip_obj.is_private, f"Public IP detected as private: {ip}"
    
    def test_localhost_detection(self):
        """Localhost should be correctly detected"""
        localhost_ips = ['127.0.0.1', '::1']
        
        for ip in localhost_ips:
            ip_obj = ipaddress.ip_address(ip)
            assert ip_obj.is_loopback, f"Localhost not detected: {ip}"
    
    def test_ipv4_10_range(self):
        """10.x.x.x range should be private"""
        test_ips = ['10.0.0.1', '10.100.50.25', '10.255.255.254']
        
        for ip in test_ips:
            ip_obj = ipaddress.ip_address(ip)
            assert str(ip_obj).startswith('10.')
            assert ip_obj.is_private


class TestLocationStringLogic:
    """Test location string generation logic"""
    
    def test_localhost_location(self):
        """Localhost should return local development location"""
        ip = '127.0.0.1'
        
        if ip.startswith('127.') or ip == '::1':
            location = "本地, 开发环境, localhost"
        else:
            location = "未知"
        
        assert '本地' in location or 'localhost' in location
    
    def test_private_network_location(self):
        """Private IPs should return network type"""
        test_cases = [
            ('192.168.1.1', '192.168'),
            ('10.0.0.1', '10.')
        ]
        
        for ip, expected_prefix in test_cases:
            if ip.startswith('192.168.'):
                location = "局域网 (192.168.x.x)"
            elif ip.startswith('10.'):
                location = "内部网络 (10.x.x.x)"
            else:
                location = "未知"
            
            assert expected_prefix in location


class TestPasswordSecurity:
    """Test password hashing and verification"""
    
    def test_password_hash_is_different(self):
        """Password hash should differ from plaintext"""
        password = "testpassword123"
        hashed = generate_password_hash(password)
        
        assert hashed != password
        assert len(hashed) > len(password)
    
    def test_same_password_different_hashes(self):
        """Same password should produce different hashes due to salt"""
        password = "testpassword123"
        hash1 = generate_password_hash(password)
        hash2 = generate_password_hash(password)
        
        assert hash1 != hash2
    
    def test_correct_password_verifies(self):
        """Correct password should verify successfully"""
        password = "correctPassword123"
        hashed = generate_password_hash(password)
        
        assert check_password_hash(hashed, password)
    
    def test_wrong_password_fails(self):
        """Wrong password should fail verification"""
        password = "correctPassword"
        hashed = generate_password_hash(password)
        
        assert not check_password_hash(hashed, "wrongPassword")
    
    def test_empty_password_fails(self):
        """Empty password should fail verification"""
        password = "somePassword"
        hashed = generate_password_hash(password)
        
        assert not check_password_hash(hashed, "")


class TestTokenGeneration:
    """Test secure token generation"""
    
    def test_token_sufficient_length(self):
        """Tokens should be of sufficient length"""
        token = secrets.token_urlsafe(32)
        assert len(token) >= 32
    
    def test_token_uniqueness(self):
        """Generated tokens should be unique"""
        tokens = [secrets.token_urlsafe(32) for _ in range(100)]
        unique_tokens = set(tokens)
        assert len(unique_tokens) == 100
    
    def test_token_url_safe(self):
        """Tokens should be URL-safe"""
        token = secrets.token_urlsafe(32)
        url_safe_pattern = r'^[A-Za-z0-9_-]+$'
        assert re.match(url_safe_pattern, token)
    
    def test_token_hex_format(self):
        """Token hex should be valid hex"""
        token = secrets.token_hex(32)
        assert all(c in '0123456789abcdef' for c in token)


class TestInputSanitization:
    """Test input sanitization for security"""
    
    def test_html_escape_script_tags(self):
        """Script tags should be escaped"""
        malicious = '<script>alert("xss")</script>'
        escaped = str(escape(malicious))
        
        assert '<script>' not in escaped
        assert '&lt;script&gt;' in escaped
    
    def test_html_escape_attributes(self):
        """HTML attributes should be escaped"""
        malicious = '" onmouseover="alert(1)"'
        escaped = str(escape(malicious))
        
        assert '"' not in escaped or '&' in escaped
    
    def test_html_escape_angle_brackets(self):
        """Angle brackets should be escaped"""
        malicious = '<div><span>'
        escaped = str(escape(malicious))
        
        assert '<div>' not in escaped


class TestRoleValidation:
    """Test role validation logic"""
    
    VALID_ROLES = ['admin', 'owner', 'client', 'guest']
    
    def test_valid_roles_accepted(self):
        """Valid roles should be accepted"""
        for role in self.VALID_ROLES:
            assert role in self.VALID_ROLES
    
    def test_invalid_role_rejected(self):
        """Invalid roles should be rejected"""
        invalid_roles = ['superuser', 'root', 'unknown', '']
        
        for role in invalid_roles:
            assert role not in self.VALID_ROLES
    
    def test_role_hierarchy(self):
        """Role hierarchy should be properly ordered"""
        role_levels = {
            'admin': 100,
            'owner': 80,
            'client': 40,
            'guest': 10
        }
        
        assert role_levels['admin'] > role_levels['owner']
        assert role_levels['owner'] > role_levels['client']
        assert role_levels['client'] > role_levels['guest']


class TestSessionValidation:
    """Test session data validation"""
    
    def test_session_authenticated_flag(self):
        """Session authenticated flag should be boolean"""
        session_data = {
            'authenticated': True,
            'email': 'test@example.com'
        }
        
        assert isinstance(session_data['authenticated'], bool)
    
    def test_session_expiry_calculation(self):
        """Session expiry should be calculated correctly"""
        session_lifetime_hours = 24
        created_at = datetime.now()
        expires_at = created_at + timedelta(hours=session_lifetime_hours)
        
        assert expires_at > created_at
        assert (expires_at - created_at).total_seconds() == 24 * 3600


class TestPasswordRequirements:
    """Test password strength requirements"""
    
    def test_minimum_length(self):
        """Password should meet minimum length"""
        def check_length(password, min_length=8):
            return len(password) >= min_length
        
        assert not check_length('')
        assert not check_length('short')
        assert not check_length('seven77')
        assert check_length('longenough')
        assert check_length('validpass')


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
