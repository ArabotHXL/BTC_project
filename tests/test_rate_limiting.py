"""
Unit tests for rate_limiting.py

Tests the Redis-backed sliding window rate limiting with thread-safe fallback.
"""
import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from flask import Flask


@pytest.fixture
def app():
    """Create test Flask application"""
    flask_app = Flask(__name__)
    flask_app.config['TESTING'] = True
    flask_app.config['SECRET_KEY'] = 'test-secret-key'
    return flask_app


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


class TestRateLimitMemory:
    """Test in-memory rate limiting fallback"""
    
    def test_memory_rate_limit_allows_requests_under_limit(self, app):
        """Requests under the limit should be allowed"""
        with app.app_context():
            from rate_limiting import _check_rate_limit_memory, _rate_limit_store
            _rate_limit_store.clear()
            
            allowed, remaining, reset_time = _check_rate_limit_memory(
                client_id="test-user",
                max_requests=5,
                window_seconds=60,
                feature_name="test"
            )
            
            assert allowed is True
            assert remaining == 4
            assert reset_time > int(datetime.now().timestamp())
    
    def test_memory_rate_limit_blocks_after_limit(self, app):
        """Requests over the limit should be blocked"""
        with app.app_context():
            from rate_limiting import _check_rate_limit_memory, _rate_limit_store
            _rate_limit_store.clear()
            
            for i in range(5):
                allowed, _, _ = _check_rate_limit_memory(
                    client_id="test-user",
                    max_requests=5,
                    window_seconds=60,
                    feature_name="test"
                )
                assert allowed is True
            
            allowed, remaining, _ = _check_rate_limit_memory(
                client_id="test-user",
                max_requests=5,
                window_seconds=60,
                feature_name="test"
            )
            
            assert allowed is False
            assert remaining == 0
    
    def test_memory_rate_limit_resets_after_window(self, app):
        """Rate limit should reset after window expires"""
        with app.app_context():
            from rate_limiting import _check_rate_limit_memory, _rate_limit_store
            _rate_limit_store.clear()
            
            old_time = datetime.now() - timedelta(seconds=120)
            _rate_limit_store["test:test-user"] = [old_time] * 5
            
            allowed, remaining, _ = _check_rate_limit_memory(
                client_id="test-user",
                max_requests=5,
                window_seconds=60,
                feature_name="test"
            )
            
            assert allowed is True
            assert remaining == 4
    
    def test_memory_reset_time_uses_oldest_timestamp(self, app):
        """Reset time should be based on oldest surviving request"""
        with app.app_context():
            from rate_limiting import _check_rate_limit_memory, _rate_limit_store
            _rate_limit_store.clear()
            
            now = datetime.now()
            oldest = now - timedelta(seconds=30)
            _rate_limit_store["test:test-user"] = [oldest, now - timedelta(seconds=10), now]
            
            _, _, reset_time = _check_rate_limit_memory(
                client_id="test-user",
                max_requests=5,
                window_seconds=60,
                feature_name="test"
            )
            
            expected_reset = int((oldest + timedelta(seconds=60)).timestamp())
            assert abs(reset_time - expected_reset) <= 1


class TestRateLimitRedis:
    """Test Redis-backed rate limiting"""
    
    def test_redis_fallback_when_unavailable(self, app):
        """Should fall back to memory when Redis is unavailable"""
        with app.app_context():
            with patch('rate_limiting.get_redis_client', return_value=None):
                from rate_limiting import _check_rate_limit_redis, _rate_limit_store
                _rate_limit_store.clear()
                
                allowed, remaining, _ = _check_rate_limit_redis(
                    client_id="test-user",
                    max_requests=5,
                    window_seconds=60,
                    feature_name="test"
                )
                
                assert allowed is True
                assert remaining == 4
    
    def test_redis_rate_limit_allows_under_limit(self, app):
        """Redis rate limit should allow requests under limit"""
        mock_redis = MagicMock()
        mock_pipe = MagicMock()
        
        now = time.time()
        mock_pipe.execute.return_value = [
            None,
            1,
            1,
            [(str(now), now)],
            True
        ]
        mock_redis.pipeline.return_value = mock_pipe
        mock_redis.zrem = MagicMock()
        
        with app.app_context():
            with patch('rate_limiting.get_redis_client', return_value=mock_redis):
                from rate_limiting import _check_rate_limit_redis
                
                allowed, remaining, reset_time = _check_rate_limit_redis(
                    client_id="test-user",
                    max_requests=5,
                    window_seconds=60,
                    feature_name="test"
                )
                
                assert allowed is True
                assert remaining == 4
                assert reset_time == int(now + 60)
    
    def test_redis_rate_limit_blocks_over_limit(self, app):
        """Redis rate limit should block requests over limit"""
        mock_redis = MagicMock()
        mock_pipe = MagicMock()
        
        now = time.time()
        oldest = now - 30
        mock_pipe.execute.return_value = [
            None,
            6,
            6,
            [(str(oldest), oldest)],
            True
        ]
        mock_redis.pipeline.return_value = mock_pipe
        mock_redis.zrem = MagicMock()
        
        with app.app_context():
            with patch('rate_limiting.get_redis_client', return_value=mock_redis):
                from rate_limiting import _check_rate_limit_redis
                
                allowed, remaining, reset_time = _check_rate_limit_redis(
                    client_id="test-user",
                    max_requests=5,
                    window_seconds=60,
                    feature_name="test"
                )
                
                assert allowed is False
                assert remaining == 0
                assert reset_time == int(oldest + 60)


class TestRateLimitDecorators:
    """Test rate limiting decorators"""
    
    def test_rate_limit_decorator_adds_headers(self, app):
        """Rate limit decorator should add X-RateLimit headers to response"""
        from rate_limiting import rate_limit
        
        @app.route('/test')
        @rate_limit(max_requests=10, window_minutes=1, feature_name="test_endpoint")
        def test_route():
            return "OK"
        
        with app.test_client() as client:
            with patch('rate_limiting._check_rate_limit_redis') as mock_check:
                mock_check.return_value = (True, 9, int(time.time() + 60))
                response = client.get('/test')
                
                assert response.status_code == 200
                assert 'X-RateLimit-Limit' in response.headers
                assert response.headers['X-RateLimit-Limit'] == '10'
                assert 'X-RateLimit-Remaining' in response.headers
                assert 'X-RateLimit-Reset' in response.headers
    
    def test_rate_limit_decorator_returns_429_when_exceeded(self, app):
        """Rate limit decorator should return 429 when limit exceeded"""
        from rate_limiting import rate_limit
        
        @app.route('/test2')
        @rate_limit(max_requests=5, window_minutes=1, feature_name="test_endpoint2")
        def test_route2():
            return "OK"
        
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess['authenticated'] = True
                sess['email'] = 'test@example.com'
            
            with patch('rate_limiting._check_rate_limit_redis') as mock_check:
                mock_check.return_value = (False, 0, int(time.time() + 60))
                response = client.get('/test2')
                
                assert response.status_code == 429
                assert 'X-RateLimit-Limit' in response.headers
                assert 'X-RateLimit-Remaining' in response.headers
                assert response.headers['X-RateLimit-Remaining'] == '0'
                assert 'Retry-After' in response.headers
    
    def test_rate_limit_api_decorator_returns_json(self, app):
        """API rate limit decorator should return JSON response"""
        from rate_limiting import rate_limit_api
        
        @app.route('/api/test')
        @rate_limit_api(max_requests=100, window_minutes=1, feature_name="api_test")
        def api_route():
            return {"status": "ok"}
        
        with app.test_client() as client:
            with patch('rate_limiting._check_rate_limit_redis') as mock_check:
                mock_check.return_value = (False, 0, int(time.time() + 60))
                response = client.get('/api/test')
                
                assert response.status_code == 429
                data = response.get_json()
                assert data['success'] is False
                assert data['error'] == 'rate_limit_exceeded'
                assert 'retry_after_seconds' in data
    
    def test_rate_limit_api_decorator_adds_headers_on_success(self, app):
        """API rate limit decorator should add headers on successful response"""
        from rate_limiting import rate_limit_api
        
        @app.route('/api/test_success')
        @rate_limit_api(max_requests=100, window_minutes=1, feature_name="api_test_success")
        def api_route_success():
            return {"status": "ok"}
        
        with app.test_client() as client:
            with patch('rate_limiting._check_rate_limit_redis') as mock_check:
                mock_check.return_value = (True, 99, int(time.time() + 60))
                response = client.get('/api/test_success')
                
                assert response.status_code == 200
                assert 'X-RateLimit-Limit' in response.headers
                assert response.headers['X-RateLimit-Limit'] == '100'
                assert 'X-RateLimit-Remaining' in response.headers
                assert response.headers['X-RateLimit-Remaining'] == '99'
                assert 'X-RateLimit-Reset' in response.headers


class TestGetRateLimitInfo:
    """Test get_rate_limit_info function"""
    
    def test_get_rate_limit_info_parameterized(self, app):
        """get_rate_limit_info should use provided parameters"""
        with app.app_context():
            from rate_limiting import get_rate_limit_info, _rate_limit_store
            _rate_limit_store.clear()
            
            with patch('rate_limiting.get_redis_client', return_value=None):
                info = get_rate_limit_info(
                    client_id="test-user",
                    feature_name="custom",
                    max_requests=20,
                    window_seconds=120
                )
                
                assert info['remaining'] == 20
                assert info['backend'] == 'memory'


class TestGetRateLimiterStatus:
    """Test rate limiter status function"""
    
    def test_status_returns_memory_fallback(self, app):
        """Status should indicate memory fallback when Redis unavailable"""
        with app.app_context():
            with patch('rate_limiting.get_redis_client', return_value=None):
                from rate_limiting import get_rate_limiter_status
                
                status = get_rate_limiter_status()
                
                assert status['backend'] == 'memory'
                assert status['status'] == 'fallback'
                assert status['distributed'] is False
    
    def test_status_returns_redis_healthy(self, app):
        """Status should indicate healthy when Redis connected"""
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        
        with app.app_context():
            with patch('rate_limiting.get_redis_client', return_value=mock_redis):
                from rate_limiting import get_rate_limiter_status
                
                status = get_rate_limiter_status()
                
                assert status['backend'] == 'redis'
                assert status['status'] == 'healthy'
                assert status['distributed'] is True
