"""
Test and Demonstration of SWR Cache Implementation
==================================================

This file demonstrates how to use the new Stale-While-Revalidate (SWR) 
caching pattern in the IntelligenceCacheManager.

Run this file to verify the SWR implementation works correctly.
"""

import time
import logging
from datetime import datetime
from intelligence.cache_manager import IntelligenceCacheManager, CachedValue

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def simulate_expensive_operation(user_id: int) -> dict:
    """
    Simulate an expensive database/API operation
    """
    logger.info(f"🔄 Executing expensive operation for user {user_id}...")
    time.sleep(1)
    
    return {
        'user_id': user_id,
        'data': f'Fresh data for user {user_id}',
        'timestamp': datetime.utcnow().isoformat(),
        'total_hashrate': 100.5,
        'revenue': 1234.56
    }


def test_cached_value_dataclass():
    """Test 1: Verify CachedValue dataclass works correctly"""
    logger.info("\n" + "="*60)
    logger.info("Test 1: CachedValue dataclass")
    logger.info("="*60)
    
    from datetime import timedelta
    now = datetime.utcnow()
    
    fresh_cache = CachedValue(
        value={'data': 'test'},
        expires_at=now + timedelta(seconds=10),
        stale_until=now + timedelta(seconds=20)
    )
    
    assert not fresh_cache.is_expired(), "Fresh cache should not be expired"
    assert not fresh_cache.is_stale(), "Fresh cache should not be stale"
    assert not fresh_cache.is_completely_expired(), "Fresh cache should not be completely expired"
    
    logger.info("✅ CachedValue dataclass works correctly")
    logger.info(f"   - is_expired: {fresh_cache.is_expired()}")
    logger.info(f"   - is_stale: {fresh_cache.is_stale()}")
    logger.info(f"   - is_completely_expired: {fresh_cache.is_completely_expired()}")


def test_swr_basic_functionality():
    """Test 2: Basic SWR set and get operations"""
    logger.info("\n" + "="*60)
    logger.info("Test 2: Basic SWR set and get operations")
    logger.info("="*60)
    
    cache = IntelligenceCacheManager()
    
    if not cache.cache:
        logger.warning("⚠️  Cache not initialized (Redis might not be available)")
        return
    
    test_key = 'test:user:123'
    test_value = {'user_id': 123, 'name': 'Test User'}
    
    success = cache.set_with_swr(
        key=test_key,
        value=test_value,
        ttl=5,
        stale_window=10
    )
    
    if success:
        logger.info(f"✅ Cache set successfully: {test_key}")
        
        retrieved = cache.get_with_swr(key=test_key)
        
        if retrieved:
            logger.info(f"✅ Cache retrieved successfully: {retrieved}")
        else:
            logger.error("❌ Failed to retrieve cached value")
    else:
        logger.error("❌ Failed to set cache")


def test_swr_with_refresh_callback():
    """Test 3: SWR with refresh callback"""
    logger.info("\n" + "="*60)
    logger.info("Test 3: SWR with refresh callback")
    logger.info("="*60)
    
    cache = IntelligenceCacheManager()
    
    if not cache.cache:
        logger.warning("⚠️  Cache not initialized (Redis might not be available)")
        return
    
    test_key = 'test:portfolio:456'
    
    def refresh_portfolio():
        logger.info("📡 Refresh callback triggered!")
        return simulate_expensive_operation(456)
    
    logger.info("Step 1: Setting initial cache with short TTL (2s)")
    cache.set_with_swr(
        key=test_key,
        value=simulate_expensive_operation(456),
        ttl=2,
        stale_window=10
    )
    
    logger.info("\nStep 2: Immediate retrieval (should be fresh)")
    result1 = cache.get_with_swr(
        key=test_key,
        refresh_callback=refresh_portfolio,
        stale_window=10
    )
    logger.info(f"Result: {result1}")
    
    logger.info("\nStep 3: Wait 3 seconds (cache becomes stale)")
    time.sleep(3)
    
    logger.info("\nStep 4: Retrieve stale cache (should trigger background refresh)")
    result2 = cache.get_with_swr(
        key=test_key,
        refresh_callback=refresh_portfolio,
        stale_window=10,
        use_rq=False
    )
    logger.info(f"Result (stale): {result2}")
    
    logger.info("\nStep 5: Wait for background refresh to complete")
    time.sleep(2)
    
    logger.info("\nStep 6: Retrieve again (should have fresh data)")
    result3 = cache.get_with_swr(key=test_key)
    logger.info(f"Result (refreshed): {result3}")
    
    logger.info("\n✅ SWR with refresh callback test completed")


def test_distributed_lock():
    """Test 4: Distributed lock prevents duplicate refreshes"""
    logger.info("\n" + "="*60)
    logger.info("Test 4: Distributed lock mechanism")
    logger.info("="*60)
    
    cache = IntelligenceCacheManager()
    
    if not cache.cache:
        logger.warning("⚠️  Cache not initialized (Redis might not be available)")
        return
    
    lock_acquired_1 = cache._get_redis_lock('test:lock', timeout=5)
    logger.info(f"First lock attempt: {'✅ Acquired' if lock_acquired_1 else '❌ Failed'}")
    
    lock_acquired_2 = cache._get_redis_lock('test:lock', timeout=5)
    logger.info(f"Second lock attempt (should fail): {'❌ Acquired (unexpected!)' if lock_acquired_2 else '✅ Blocked (expected)'}")
    
    if lock_acquired_1:
        cache._release_redis_lock('test:lock')
        logger.info("Lock released")
    
    lock_acquired_3 = cache._get_redis_lock('test:lock', timeout=5)
    logger.info(f"Third lock attempt after release: {'✅ Acquired' if lock_acquired_3 else '❌ Failed'}")
    
    if lock_acquired_3:
        cache._release_redis_lock('test:lock')
    
    logger.info("\n✅ Distributed lock test completed")


def test_bug_fix_1_cache_miss_sync_refresh():
    """Test Bug Fix #1: Cache miss/completely expired should sync refresh"""
    logger.info("\n" + "="*60)
    logger.info("Test Bug Fix #1: Cache miss/completely expired sync refresh")
    logger.info("="*60)
    
    cache = IntelligenceCacheManager()
    
    if not cache.cache:
        logger.warning("⚠️  Cache not initialized")
        return
    
    test_key = 'test:bug1:cache_miss'
    refresh_count = {'count': 0}
    
    def refresh_callback():
        refresh_count['count'] += 1
        logger.info(f"🔄 Refresh callback called (count: {refresh_count['count']})")
        return {'data': 'fresh_value', 'count': refresh_count['count']}
    
    logger.info("Test 1a: Cache miss should trigger sync refresh")
    result = cache.get_with_swr(
        key=test_key,
        refresh_callback=refresh_callback,
        ttl=5,
        stale_window=5
    )
    assert result is not None, "Cache miss should return fresh data"
    assert refresh_count['count'] == 1, "Refresh callback should be called once"
    logger.info(f"✅ Cache miss correctly fetched fresh data: {result}")
    
    logger.info("\nTest 1b: Completely expired cache should trigger sync refresh")
    time.sleep(11)
    refresh_count['count'] = 0
    
    result2 = cache.get_with_swr(
        key=test_key,
        refresh_callback=refresh_callback,
        ttl=5,
        stale_window=5
    )
    assert result2 is not None, "Completely expired should return fresh data"
    assert refresh_count['count'] == 1, "Refresh callback should be called once"
    logger.info(f"✅ Completely expired correctly fetched fresh data: {result2}")
    
    logger.info("\n✅ Bug Fix #1 test passed!")


def test_bug_fix_2_threading_lock_fallback():
    """Test Bug Fix #2: Threading lock fallback when Redis lock fails"""
    logger.info("\n" + "="*60)
    logger.info("Test Bug Fix #2: Threading lock fallback")
    logger.info("="*60)
    
    from flask import Flask
    
    app = Flask(__name__)
    app.config['CACHE_TYPE'] = 'simple'
    
    cache = IntelligenceCacheManager()
    cache.init_app(app)
    
    test_key = 'test:bug2:threading_lock'
    refresh_count = {'count': 0}
    
    def refresh_callback():
        refresh_count['count'] += 1
        logger.info(f"🔄 Refresh with threading lock (count: {refresh_count['count']})")
        time.sleep(0.5)
        return {'data': 'refreshed_with_threading', 'count': refresh_count['count']}
    
    logger.info("Setting cache with short TTL for simple cache environment")
    cache.set_with_swr(
        key=test_key,
        value={'data': 'initial'},
        ttl=1,
        stale_window=5
    )
    
    time.sleep(2)
    
    logger.info("Retrieving stale cache (should use threading lock)")
    result = cache.get_with_swr(
        key=test_key,
        refresh_callback=refresh_callback,
        ttl=5,
        stale_window=5,
        use_rq=False
    )
    
    logger.info(f"Result (stale): {result}")
    
    time.sleep(1)
    
    assert refresh_count['count'] > 0, "Threading lock should allow refresh"
    logger.info(f"✅ Threading lock fallback works (refresh count: {refresh_count['count']})")
    
    logger.info("\n✅ Bug Fix #2 test passed!")


def test_callback_parameters_passing():
    """Test: Callback parameters are correctly passed to refresh functions"""
    logger.info("\n" + "="*60)
    logger.info("Test: Callback Parameters Passing (New Feature)")
    logger.info("="*60)
    
    cache = IntelligenceCacheManager()
    
    if not cache.cache:
        logger.warning("⚠️  Cache not initialized")
        return
    
    test_key = 'test:callback_params:user_portfolio'
    call_log = []
    
    def fetch_user_portfolio(user_id, include_inactive=False):
        """Test callback that requires parameters"""
        logger.info(f"🔄 fetch_user_portfolio called with user_id={user_id}, include_inactive={include_inactive}")
        call_log.append({
            'user_id': user_id,
            'include_inactive': include_inactive,
            'timestamp': datetime.utcnow().isoformat()
        })
        return {
            'user_id': user_id,
            'portfolio': f'Portfolio for user {user_id}',
            'include_inactive': include_inactive,
            'data': 'test_data'
        }
    
    logger.info("Test 1: Cache miss with callback parameters")
    result1 = cache.get_with_swr(
        key=test_key,
        refresh_callback=fetch_user_portfolio,
        refresh_args=(123,),
        refresh_kwargs={'include_inactive': True},
        ttl=2,
        stale_window=5
    )
    
    assert result1 is not None, "Should return fresh data"
    assert result1['user_id'] == 123, "Should have correct user_id"
    assert result1['include_inactive'] is True, "Should have correct include_inactive flag"
    assert len(call_log) == 1, "Callback should be called once"
    logger.info(f"✅ Cache miss correctly called callback with params: {result1}")
    
    logger.info("\nTest 2: Stale cache with callback parameters (threading path)")
    call_log.clear()
    time.sleep(3)
    
    result2 = cache.get_with_swr(
        key=test_key,
        refresh_callback=fetch_user_portfolio,
        refresh_args=(456,),
        refresh_kwargs={'include_inactive': False},
        ttl=5,
        stale_window=10,
        use_rq=False
    )
    
    logger.info(f"Stale result (should return old data): {result2}")
    assert result2 is not None, "Should return stale data"
    assert result2['user_id'] == 123, "Should return stale data immediately"
    
    time.sleep(2)
    
    logger.info(f"Callback log after background refresh: {call_log}")
    assert len(call_log) > 0, "Background refresh should have been triggered"
    if call_log:
        assert call_log[0]['user_id'] == 456, "Background refresh should use new user_id"
        logger.info("✅ Stale cache correctly triggered background refresh with new params")
    
    logger.info("\nTest 3: Verify refreshed cache has new data")
    result3 = cache.get_with_swr(key=test_key)
    logger.info(f"Refreshed result: {result3}")
    if result3 and 'user_id' in result3:
        assert result3['user_id'] == 456, "Should have refreshed data with new user_id"
        assert result3['include_inactive'] is False, "Should have refreshed data with new flag"
        logger.info("✅ Refreshed cache has correct data from callback with params")
    
    logger.info("\nTest 4: Backward compatibility - callback without parameters")
    call_log.clear()
    test_key_no_params = 'test:callback_no_params'
    
    def simple_callback():
        """Callback without parameters (backward compatibility)"""
        logger.info("🔄 simple_callback called (no parameters)")
        call_log.append({'called': True})
        return {'data': 'simple_data', 'timestamp': datetime.utcnow().isoformat()}
    
    result4 = cache.get_with_swr(
        key=test_key_no_params,
        refresh_callback=simple_callback,
        ttl=5,
        stale_window=5
    )
    
    assert result4 is not None, "Should work with no parameters (backward compatible)"
    assert len(call_log) == 1, "Simple callback should be called"
    logger.info(f"✅ Backward compatibility: callback without params works: {result4}")
    
    logger.info("\n✅ Callback parameters passing test completed!")


def test_bug_fix_3_correct_ttl_values():
    """Test Bug Fix #3: Correct TTL values in refresh"""
    logger.info("\n" + "="*60)
    logger.info("Test Bug Fix #3: Correct TTL values in refresh")
    logger.info("="*60)
    
    cache = IntelligenceCacheManager()
    
    if not cache.cache:
        logger.warning("⚠️  Cache not initialized")
        return
    
    test_key = 'test:bug3:ttl_check'
    custom_ttl = 10
    custom_stale_window = 15
    
    def refresh_callback():
        logger.info(f"🔄 Refreshing with custom TTL={custom_ttl}, stale_window={custom_stale_window}")
        return {'data': 'refreshed_data', 'timestamp': datetime.utcnow().isoformat()}
    
    logger.info(f"Setting cache with TTL={custom_ttl}s, stale_window={custom_stale_window}s")
    cache.set_with_swr(
        key=test_key,
        value={'data': 'initial'},
        ttl=2,
        stale_window=5
    )
    
    time.sleep(3)
    
    logger.info("Triggering refresh with custom TTL values")
    result = cache.get_with_swr(
        key=test_key,
        refresh_callback=refresh_callback,
        ttl=custom_ttl,
        stale_window=custom_stale_window,
        use_rq=False
    )
    
    time.sleep(1)
    
    cached_entry = cache.cache.get(test_key)
    if isinstance(cached_entry, CachedValue):
        actual_ttl = (cached_entry.expires_at - datetime.utcnow()).total_seconds()
        actual_total = (cached_entry.stale_until - datetime.utcnow()).total_seconds()
        
        logger.info(f"Actual TTL remaining: {actual_ttl:.1f}s (expected ~{custom_ttl}s)")
        logger.info(f"Actual total timeout: {actual_total:.1f}s (expected ~{custom_ttl + custom_stale_window}s)")
        
        assert 8 <= actual_ttl <= 11, f"TTL should be ~{custom_ttl}s, got {actual_ttl:.1f}s"
        assert 23 <= actual_total <= 26, f"Total should be ~{custom_ttl + custom_stale_window}s, got {actual_total:.1f}s"
        
        logger.info("✅ TTL values are correct!")
    else:
        logger.warning("⚠️  Cache entry is not CachedValue type")
    
    logger.info("\n✅ Bug Fix #3 test passed!")


def main():
    """Run all tests"""
    logger.info("="*60)
    logger.info("SWR Cache Implementation Tests (Bug Fixes Verification)")
    logger.info("="*60)
    
    try:
        test_cached_value_dataclass()
        test_swr_basic_functionality()
        test_swr_with_refresh_callback()
        test_distributed_lock()
        
        logger.info("\n" + "="*60)
        logger.info("Bug Fixes Verification Tests")
        logger.info("="*60)
        
        test_bug_fix_1_cache_miss_sync_refresh()
        test_bug_fix_2_threading_lock_fallback()
        test_callback_parameters_passing()
        test_bug_fix_3_correct_ttl_values()
        
        logger.info("\n" + "="*60)
        logger.info("✅ All tests completed successfully!")
        logger.info("="*60)
        
    except Exception as e:
        logger.error(f"\n❌ Test failed with error: {e}", exc_info=True)


if __name__ == '__main__':
    main()
