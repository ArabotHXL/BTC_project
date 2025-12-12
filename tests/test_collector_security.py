"""
Tests for Collector Security Module
采集器安全模块测试
"""

import pytest
import time
from services.collector_security import (
    validate_single_miner,
    validate_telemetry_payload,
    RateLimiter,
    check_rate_limit,
    TelemetryValidationError,
    TELEMETRY_SCHEMA
)


class TestTelemetryValidation:
    """Test telemetry payload validation"""
    
    def test_validate_valid_payload(self):
        """Valid miner data should pass validation"""
        miner_data = {
            'miner_id': 'SN123456789',
            'ip_address': '192.168.1.100',
            'online': True,
            'hashrate_ghs': 110000.5,
            'temperature_avg': 65.5,
            'temperature_max': 72.0,
            'fan_speeds': [5200, 5300],
            'accepted_shares': 12500,
            'overall_health': 'healthy'
        }
        
        is_valid, error = validate_single_miner(miner_data)
        assert is_valid is True
        assert error is None
    
    def test_validate_missing_miner_id(self):
        """Missing required miner_id should fail"""
        miner_data = {
            'ip_address': '192.168.1.100',
            'online': True
        }
        
        is_valid, error = validate_single_miner(miner_data)
        assert is_valid is False
        assert error is not None and 'miner_id' in error
    
    def test_validate_invalid_type_string(self):
        """Invalid type for string field should fail"""
        miner_data = {
            'miner_id': 12345,  # Should be string
            'online': True
        }
        
        is_valid, error = validate_single_miner(miner_data)
        assert is_valid is False
        assert error is not None and 'type' in error.lower()
    
    def test_validate_invalid_type_number(self):
        """Invalid type for number field should fail"""
        miner_data = {
            'miner_id': 'SN123',
            'hashrate_ghs': 'not_a_number'
        }
        
        is_valid, error = validate_single_miner(miner_data)
        assert is_valid is False
        assert error is not None and 'type' in error.lower()
    
    def test_validate_string_max_length(self):
        """String exceeding max length should fail"""
        miner_data = {
            'miner_id': 'A' * 60  # Exceeds max 50
        }
        
        is_valid, error = validate_single_miner(miner_data)
        assert is_valid is False
        assert error is not None and 'length' in error.lower()
    
    def test_validate_numeric_min_range(self):
        """Number below minimum should fail"""
        miner_data = {
            'miner_id': 'SN123',
            'hashrate_ghs': -100  # Min is 0
        }
        
        is_valid, error = validate_single_miner(miner_data)
        assert is_valid is False
        assert error is not None and 'below minimum' in error.lower()
    
    def test_validate_numeric_max_range(self):
        """Number above maximum should fail"""
        miner_data = {
            'miner_id': 'SN123',
            'temperature_avg': 200  # Max is 150
        }
        
        is_valid, error = validate_single_miner(miner_data)
        assert is_valid is False
        assert error is not None and 'exceeds maximum' in error.lower()
    
    def test_validate_array_max_items(self):
        """Array exceeding max items should fail"""
        miner_data = {
            'miner_id': 'SN123',
            'temperature_chips': list(range(150))  # Max is 100
        }
        
        is_valid, error = validate_single_miner(miner_data)
        assert is_valid is False
        assert error is not None and 'max items' in error.lower()
    
    def test_validate_invalid_health_status(self):
        """Invalid health status should fail"""
        miner_data = {
            'miner_id': 'SN123',
            'overall_health': 'invalid_status'
        }
        
        is_valid, error = validate_single_miner(miner_data)
        assert is_valid is False
        assert error is not None and 'overall_health' in error
    
    def test_validate_valid_health_statuses(self):
        """All valid health statuses should pass"""
        valid_statuses = ['healthy', 'degraded', 'critical', 'offline', 'unknown']
        
        for status in valid_statuses:
            miner_data = {
                'miner_id': f'SN{status}',
                'overall_health': status
            }
            is_valid, error = validate_single_miner(miner_data)
            assert is_valid is True, f"Status {status} should be valid"
    
    def test_validate_optional_fields(self):
        """Optional fields missing should pass"""
        miner_data = {
            'miner_id': 'SN123'
        }
        
        is_valid, error = validate_single_miner(miner_data)
        assert is_valid is True


class TestPayloadValidation:
    """Test full payload validation"""
    
    def test_validate_payload_array(self):
        """Payload must be an array"""
        is_valid, error, data = validate_telemetry_payload({'miner_id': 'SN123'})
        assert is_valid is False
        assert error is not None and 'array' in error.lower()
    
    def test_validate_empty_payload(self):
        """Empty array should pass"""
        is_valid, error, data = validate_telemetry_payload([])
        assert is_valid is True
        assert data == []
    
    def test_validate_payload_max_miners(self):
        """Payload exceeding max miners should fail"""
        payload = [{'miner_id': f'SN{i}'} for i in range(5001)]
        
        is_valid, error, data = validate_telemetry_payload(payload)
        assert is_valid is False
        assert error is not None and '5000' in error
    
    def test_validate_payload_deduplication(self):
        """Duplicate miner_ids should be deduplicated"""
        payload = [
            {'miner_id': 'SN123', 'hashrate_ghs': 100},
            {'miner_id': 'SN123', 'hashrate_ghs': 200},  # Duplicate
            {'miner_id': 'SN456', 'hashrate_ghs': 300}
        ]
        
        is_valid, error, data = validate_telemetry_payload(payload)
        assert is_valid is True
        assert len(data) == 2  # Only 2 unique
    
    def test_validate_payload_sanitization(self):
        """Unknown fields should be stripped"""
        payload = [{
            'miner_id': 'SN123',
            'hashrate_ghs': 100,
            'malicious_field': 'should_be_removed',
            'another_unknown': 12345
        }]
        
        is_valid, error, data = validate_telemetry_payload(payload)
        assert is_valid is True
        assert 'malicious_field' not in data[0]
        assert 'another_unknown' not in data[0]
        assert data[0]['miner_id'] == 'SN123'
    
    def test_validate_mixed_valid_invalid(self):
        """Mixed valid/invalid miners: valid ones kept, invalid ones skipped"""
        payload = [
            {'miner_id': 'SN_VALID_1', 'hashrate_ghs': 100},
            {'miner_id': 12345, 'hashrate_ghs': 200},  # Invalid type
            {'miner_id': 'SN_VALID_2', 'hashrate_ghs': 300},
            {'hashrate_ghs': 400},  # Missing miner_id
        ]
        
        is_valid, error, data = validate_telemetry_payload(payload)
        assert is_valid is True  # Has valid miners
        assert len(data) == 2  # Only 2 valid
        assert data[0]['miner_id'] == 'SN_VALID_1'
        assert data[1]['miner_id'] == 'SN_VALID_2'
    
    def test_validate_all_invalid_miners(self):
        """All invalid miners should return error"""
        payload = [
            {'miner_id': 12345},  # Invalid type
            {'hashrate_ghs': 100},  # Missing miner_id
            {'miner_id': 'A' * 60},  # Too long
        ]
        
        is_valid, error, data = validate_telemetry_payload(payload)
        assert is_valid is False
        assert error is not None and 'No valid miners' in error
        assert len(data) == 0
    
    def test_validate_strict_mode(self):
        """Strict mode fails on first invalid miner"""
        payload = [
            {'miner_id': 'SN_VALID'},
            {'miner_id': 12345},  # Invalid type
            {'miner_id': 'SN_ALSO_VALID'},
        ]
        
        is_valid, error, data = validate_telemetry_payload(payload, strict=True)
        assert is_valid is False
        assert error is not None and 'type' in error.lower()
        assert len(data) == 0


class TestRateLimiter:
    """Test rate limiting functionality"""
    
    def test_rate_limiter_allows_under_limit(self):
        """Requests under limit should be allowed"""
        limiter = RateLimiter(max_requests=10, window_seconds=60)
        
        for i in range(10):
            allowed, remaining, reset = limiter.is_allowed('test_key')
            assert allowed is True
            assert remaining == 10 - i - 1
    
    def test_rate_limiter_blocks_over_limit(self):
        """Requests over limit should be blocked"""
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        
        for i in range(5):
            limiter.is_allowed('test_key')
        
        allowed, remaining, reset = limiter.is_allowed('test_key')
        assert allowed is False
        assert remaining == 0
    
    def test_rate_limiter_different_keys(self):
        """Different keys should have separate limits"""
        limiter = RateLimiter(max_requests=3, window_seconds=60)
        
        for i in range(3):
            limiter.is_allowed('key1')
        
        allowed, remaining, reset = limiter.is_allowed('key1')
        assert allowed is False
        
        allowed, remaining, reset = limiter.is_allowed('key2')
        assert allowed is True
    
    def test_rate_limiter_window_expiry(self):
        """Requests should be allowed after window expires"""
        limiter = RateLimiter(max_requests=2, window_seconds=1)
        
        limiter.is_allowed('test_key')
        limiter.is_allowed('test_key')
        
        allowed, _, _ = limiter.is_allowed('test_key')
        assert allowed is False
        
        time.sleep(1.1)
        
        allowed, remaining, _ = limiter.is_allowed('test_key')
        assert allowed is True
    
    def test_rate_limiter_stats(self):
        """Stats should reflect current state"""
        limiter = RateLimiter(max_requests=10, window_seconds=60)
        
        for i in range(5):
            limiter.is_allowed('test_key')
        
        stats = limiter.get_stats('test_key')
        assert stats['current_count'] == 5
        assert stats['max_requests'] == 10
        assert stats['remaining'] == 5
    
    def test_rate_limiter_unknown_key_stats(self):
        """Stats for unknown key should show full capacity"""
        limiter = RateLimiter(max_requests=10, window_seconds=60)
        
        stats = limiter.get_stats('unknown_key')
        assert stats['current_count'] == 0
        assert stats['remaining'] == 10


class TestSchemaCompleteness:
    """Test that schema covers all expected fields"""
    
    def test_schema_has_required_fields(self):
        """Schema should have required miner_id"""
        assert 'miner_id' in TELEMETRY_SCHEMA
        assert TELEMETRY_SCHEMA['miner_id']['required'] is True
    
    def test_schema_numeric_fields_have_ranges(self):
        """Numeric fields should have min/max ranges"""
        numeric_fields = [
            'hashrate_ghs', 'temperature_avg', 'temperature_max',
            'frequency_avg', 'power_consumption'
        ]
        
        for field in numeric_fields:
            assert field in TELEMETRY_SCHEMA
            assert 'min' in TELEMETRY_SCHEMA[field] or 'max' in TELEMETRY_SCHEMA[field]
    
    def test_schema_string_fields_have_lengths(self):
        """String fields should have max_length"""
        string_fields = ['miner_id', 'ip_address', 'pool_url', 'worker_name', 'model']
        
        for field in string_fields:
            assert field in TELEMETRY_SCHEMA
            assert 'max_length' in TELEMETRY_SCHEMA[field]
    
    def test_schema_array_fields_have_limits(self):
        """Array fields should have max_items"""
        array_fields = ['temperature_chips', 'fan_speeds', 'boards']
        
        for field in array_fields:
            assert field in TELEMETRY_SCHEMA
            assert 'max_items' in TELEMETRY_SCHEMA[field]


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
