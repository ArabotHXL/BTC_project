"""
Intelligence Layer Cache Manager
=================================

Flask-Caching based caching system for the intelligence layer with:
- Redis backend support
- Structured cache key naming
- Cache invalidation functions
- Stale-while-revalidate pattern implementation

Cache Key Patterns:
- user_portfolio:{id}
- forecast:{id}
- ops_schedule:{id}:{date}
- user_forecasts:{id}
- user_ops_schedules:{id}
"""

import logging
import os
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Callable, Optional, Dict, List, Union
try:
    from flask_caching import Cache
except ImportError:  # pragma: no cover - fallback for environments without flask_caching
    Cache = None


class SimpleCache:
    """Minimal in-memory cache fallback when Flask-Caching isn't available."""

    def __init__(self, app=None):
        self._store: Dict[str, Any] = {}

    def get(self, key: str) -> Optional[Any]:
        return self._store.get(key)

    def set(self, key: str, value: Any, timeout: Optional[int] = None) -> bool:
        self._store[key] = value
        return True

    def delete(self, key: str) -> bool:
        self._store.pop(key, None)
        return True

    def delete_many(self, *keys: str) -> bool:
        for key in keys:
            self._store.pop(key, None)
        return True

    def clear(self) -> bool:
        self._store.clear()
        return True

logger = logging.getLogger(__name__)


@dataclass
class CachedValue:
    """
    Structured cache entry with expiration and stale-while-revalidate support
    
    Attributes:
    -----------
    value : Any
        The cached value
    expires_at : datetime
        When the cache entry becomes stale
    stale_until : datetime
        When the cache entry should be completely removed (beyond this, return None)
    """
    value: Any
    expires_at: datetime
    stale_until: datetime
    
    def is_expired(self) -> bool:
        """Check if cache entry has expired (is stale)"""
        return datetime.utcnow() > self.expires_at
    
    def is_stale(self) -> bool:
        """Check if cache entry is stale but still usable (within stale window)"""
        now = datetime.utcnow()
        return self.expires_at < now <= self.stale_until
    
    def is_completely_expired(self) -> bool:
        """Check if cache entry is beyond stale window (should return None)"""
        return datetime.utcnow() > self.stale_until


class IntelligenceCacheManager:
    """
    Cache Manager for Intelligence Layer
    
    Uses Flask-Caching with Redis backend for distributed caching
    with support for cache invalidation and stale-while-revalidate patterns.
    """
    
    def __init__(self, app=None):
        """
        Initialize the Intelligence Cache Manager
        
        Parameters:
        -----------
        app : Flask application instance
            Flask app to configure caching for
        """
        self.cache: Optional[Cache] = None
        self._revalidate_locks: Dict[str, bool] = {}
        self._revalidate_lock = threading.Lock()
        self._process_locks: Dict[str, threading.Lock] = {}
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """
        Initialize Flask-Caching with Redis backend
        
        Parameters:
        -----------
        app : Flask
            Flask application instance
        """
        if Cache is None:
            # Keep cache-backed code paths usable in constrained test environments.
            logger.warning("flask_caching not installed; using SimpleCache fallback")
            self.cache = SimpleCache(app)
            return

        redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
        
        cache_config = {
            'CACHE_TYPE': 'redis',
            'CACHE_REDIS_URL': redis_url,
            'CACHE_KEY_PREFIX': 'intelligence:',
            'CACHE_DEFAULT_TIMEOUT': 300,
        }
        
        app.config.update(cache_config)
        
        try:
            self.cache = Cache(app)
            logger.info(f"Intelligence cache initialized with Redis: {redis_url}")
        except Exception as e:
            logger.error(f"Failed to initialize Redis cache: {e}")
            logger.warning("Falling back to simple cache")
            app.config['CACHE_TYPE'] = 'simple'
            self.cache = Cache(app)
    
    # ========================================================================
    # Cache Key Naming Functions
    # ========================================================================
    
    @staticmethod
    def user_portfolio_key(user_id: int) -> str:
        """
        Generate cache key for user portfolio
        
        Parameters:
        -----------
        user_id : int
            User ID
            
        Returns:
        --------
        str : Cache key in format user_portfolio:{id}
        """
        return f"user_portfolio:{user_id}"
    
    @staticmethod
    def forecast_key(forecast_id: int) -> str:
        """
        Generate cache key for forecast
        
        Parameters:
        -----------
        forecast_id : int
            Forecast ID
            
        Returns:
        --------
        str : Cache key in format forecast:{id}
        """
        return f"forecast:{forecast_id}"
    
    @staticmethod
    def ops_schedule_key(ops_schedule_id: int, date: str) -> str:
        """
        Generate cache key for ops schedule
        
        Parameters:
        -----------
        ops_schedule_id : int
            Operations Schedule ID
        date : str
            Date string (YYYY-MM-DD format)
            
        Returns:
        --------
        str : Cache key in format ops_schedule:{id}:{date}
        """
        return f"ops_schedule:{ops_schedule_id}:{date}"
    
    @staticmethod
    def user_forecasts_key(user_id: int) -> str:
        """
        Generate cache key for all user forecasts
        
        Parameters:
        -----------
        user_id : int
            User ID
            
        Returns:
        --------
        str : Cache key in format user_forecasts:{id}
        """
        return f"user_forecasts:{user_id}"
    
    @staticmethod
    def user_ops_schedules_key(user_id: int) -> str:
        """
        Generate cache key for all user ops schedules
        
        Parameters:
        -----------
        user_id : int
            User ID
            
        Returns:
        --------
        str : Cache key in format user_ops_schedules:{id}
        """
        return f"user_ops_schedules:{user_id}"
    
    # ========================================================================
    # Cache Operations
    # ========================================================================
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache
        
        Parameters:
        -----------
        key : str
            Cache key
            
        Returns:
        --------
        Optional[Any] : Cached value or None if not found
        """
        if not self.cache:
            logger.warning("Cache not initialized")
            return None
        
        try:
            value = self.cache.get(key)
            if value is not None:
                logger.debug(f"Cache hit: {key}")
            else:
                logger.debug(f"Cache miss: {key}")
            return value
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            return None
    
    def set(self, key: str, value: Any, timeout: Optional[int] = None) -> bool:
        """
        Set value in cache
        
        Parameters:
        -----------
        key : str
            Cache key
        value : Any
            Value to cache
        timeout : Optional[int]
            Timeout in seconds (None uses default)
            
        Returns:
        --------
        bool : True if successful, False otherwise
        """
        if not self.cache:
            logger.warning("Cache not initialized")
            return False
        
        try:
            self.cache.set(key, value, timeout=timeout)
            logger.debug(f"Cache set: {key}, timeout={timeout}s")
            return True
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """
        Delete value from cache
        
        Parameters:
        -----------
        key : str
            Cache key
            
        Returns:
        --------
        bool : True if successful, False otherwise
        """
        if not self.cache:
            logger.warning("Cache not initialized")
            return False
        
        try:
            self.cache.delete(key)
            logger.debug(f"Cache deleted: {key}")
            return True
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            return False
    
    def delete_many(self, *keys: str) -> bool:
        """
        Delete multiple values from cache
        
        Parameters:
        -----------
        *keys : str
            Cache keys to delete
            
        Returns:
        --------
        bool : True if successful, False otherwise
        """
        if not self.cache:
            logger.warning("Cache not initialized")
            return False
        
        try:
            self.cache.delete_many(*keys)
            logger.debug(f"Cache deleted {len(keys)} keys")
            return True
        except Exception as e:
            logger.error(f"Cache delete_many error: {e}")
            return False
    
    def clear(self) -> bool:
        """
        Clear all cache entries
        
        Returns:
        --------
        bool : True if successful, False otherwise
        """
        if not self.cache:
            logger.warning("Cache not initialized")
            return False
        
        try:
            self.cache.clear()
            logger.info("Cache cleared")
            return True
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            return False
    
    # ========================================================================
    # Cache Invalidation Functions
    # ========================================================================
    
    def invalidate_user_portfolio(self, user_id: int) -> bool:
        """
        Invalidate user portfolio cache
        
        Parameters:
        -----------
        user_id : int
            User ID
            
        Returns:
        --------
        bool : True if successful
        """
        key = self.user_portfolio_key(user_id)
        logger.info(f"Invalidating user portfolio cache: user_id={user_id}")
        return self.delete(key)
    
    def invalidate_user_forecasts(self, user_id: int) -> bool:
        """
        Invalidate all user forecast caches
        
        Parameters:
        -----------
        user_id : int
            User ID
            
        Returns:
        --------
        bool : True if successful
        """
        key = self.user_forecasts_key(user_id)
        logger.info(f"Invalidating user forecasts cache: user_id={user_id}")
        return self.delete(key)
    
    def invalidate_user_ops_schedules(self, user_id: int) -> bool:
        """
        Invalidate all user ops schedules caches
        
        Parameters:
        -----------
        user_id : int
            User ID
            
        Returns:
        --------
        bool : True if successful
        """
        key = self.user_ops_schedules_key(user_id)
        logger.info(f"Invalidating user ops schedules cache: user_id={user_id}")
        return self.delete(key)
    
    def invalidate_forecast(self, forecast_id: int) -> bool:
        """
        Invalidate specific forecast cache
        
        Parameters:
        -----------
        forecast_id : int
            Forecast ID
            
        Returns:
        --------
        bool : True if successful
        """
        key = self.forecast_key(forecast_id)
        logger.info(f"Invalidating forecast cache: forecast_id={forecast_id}")
        return self.delete(key)
    
    def invalidate_ops_schedule(self, ops_schedule_id: int, date: Optional[str] = None) -> bool:
        """
        Invalidate ops schedule cache
        
        Parameters:
        -----------
        ops_schedule_id : int
            Operations Schedule ID
        date : Optional[str]
            Specific date to invalidate (None invalidates all dates)
            
        Returns:
        --------
        bool : True if successful
        """
        if date:
            key = self.ops_schedule_key(ops_schedule_id, date)
            logger.info(f"Invalidating ops schedule cache: ops_schedule_id={ops_schedule_id}, date={date}")
            return self.delete(key)
        else:
            logger.info(f"Invalidating all ops schedule caches for ops_schedule_id={ops_schedule_id}")
            return True
    
    def invalidate_all_user_data(self, user_id: int) -> bool:
        """
        Invalidate all user-related caches
        
        Parameters:
        -----------
        user_id : int
            User ID
            
        Returns:
        --------
        bool : True if all invalidations successful
        """
        logger.info(f"Invalidating all user data: user_id={user_id}")
        
        keys_to_delete = [
            self.user_portfolio_key(user_id),
            self.user_forecasts_key(user_id),
            self.user_ops_schedules_key(user_id)
        ]
        
        return self.delete_many(*keys_to_delete)
    
    # ========================================================================
    # Enhanced SWR Pattern with CachedValue and RQ Integration
    # ========================================================================
    
    def _get_redis_lock(self, lock_key: str, timeout: int = 60) -> bool:
        """
        Acquire a distributed lock using Redis to prevent duplicate refresh operations
        
        Parameters:
        -----------
        lock_key : str
            Lock key
        timeout : int
            Lock timeout in seconds
            
        Returns:
        --------
        bool : True if lock acquired, False otherwise
        """
        if not self.cache:
            return False
        
        try:
            cache_backend = getattr(self.cache, 'cache', None)
            if not cache_backend:
                return False
            
            redis_client = getattr(cache_backend, '_write_client', None)
            if not redis_client:
                return False
            
            lock_key_full = f"lock:{lock_key}"
            result = redis_client.set(lock_key_full, '1', nx=True, ex=timeout)
            return bool(result)
        except Exception as e:
            logger.debug(f"Failed to acquire Redis lock for {lock_key}: {e}")
            return False
    
    def _release_redis_lock(self, lock_key: str) -> bool:
        """
        Release a distributed lock
        
        Parameters:
        -----------
        lock_key : str
            Lock key
            
        Returns:
        --------
        bool : True if lock released, False otherwise
        """
        if not self.cache:
            return False
        
        try:
            cache_backend = getattr(self.cache, 'cache', None)
            if not cache_backend:
                return False
            
            redis_client = getattr(cache_backend, '_write_client', None)
            if not redis_client:
                return False
            
            lock_key_full = f"lock:{lock_key}"
            redis_client.delete(lock_key_full)
            return True
        except Exception as e:
            logger.debug(f"Failed to release Redis lock for {lock_key}: {e}")
            return False
    
    def get_with_swr(
        self,
        key: str,
        refresh_callback: Optional[Callable[..., Any]] = None,
        refresh_args: tuple = (),
        refresh_kwargs: Optional[dict] = None,
        ttl: int = 300,
        stale_window: int = 300,
        use_rq: bool = True
    ) -> Optional[Any]:
        """
        Get cached value with Stale-While-Revalidate pattern using CachedValue dataclass
        
        This method implements the SWR pattern:
        1. If cache is fresh (not expired): return immediately
        2. If cache is stale (expired but within stale_window): 
           - Return stale value immediately
           - Trigger background refresh
        3. If cache is completely expired (beyond stale_window) or missing:
           - Synchronously fetch fresh data if refresh_callback provided
           - Update cache and return fresh value
        
        Parameters:
        -----------
        key : str
            Cache key
        refresh_callback : Optional[Callable]
            Function to call to refresh the cache
        refresh_args : tuple
            Positional arguments to pass to refresh_callback
        refresh_kwargs : dict
            Keyword arguments to pass to refresh_callback
        ttl : int
            Time-to-live (fresh period) in seconds
        stale_window : int
            How long (in seconds) to serve stale content while revalidating
        use_rq : bool
            Whether to use RQ for background refresh (falls back to threading if unavailable)
            
        Returns:
        --------
        Optional[Any] : Cached value or None if no refresh_callback and cache miss
        
        Example:
        --------
        def fetch_user_data(user_id):
            # Expensive operation
            return calculate_user_portfolio(user_id)
        
        data = cache.get_with_swr(
            key='portfolio:123',
            refresh_callback=fetch_user_data,
            refresh_args=(123,),
            ttl=300,
            stale_window=300
        )
        """
        if refresh_kwargs is None:
            refresh_kwargs = {}
        
        if not self.cache:
            logger.warning("Cache not initialized")
            if refresh_callback:
                return refresh_callback(*refresh_args, **refresh_kwargs)
            return None
        
        try:
            cached_entry = self.cache.get(key)
            
            if cached_entry is None:
                logger.info(f"Cache miss: {key}, fetching fresh data synchronously")
                if refresh_callback:
                    fresh_value = refresh_callback(*refresh_args, **refresh_kwargs)
                    self.set_with_swr(key, fresh_value, ttl=ttl, stale_window=stale_window)
                    return fresh_value
                return None
            
            if isinstance(cached_entry, CachedValue):
                if not cached_entry.is_expired():
                    logger.debug(f"Cache fresh: {key}")
                    return cached_entry.value
                
                elif cached_entry.is_stale():
                    logger.info(f"Serving stale content and triggering refresh: {key}")
                    
                    if refresh_callback:
                        self._trigger_background_refresh(
                            key=key,
                            refresh_callback=refresh_callback,
                            refresh_args=refresh_args,
                            refresh_kwargs=refresh_kwargs,
                            ttl=ttl,
                            stale_window=stale_window,
                            use_rq=use_rq
                        )
                    
                    return cached_entry.value
                
                else:
                    logger.info(f"Cache completely expired: {key}, fetching fresh data synchronously")
                    if refresh_callback:
                        fresh_value = refresh_callback(*refresh_args, **refresh_kwargs)
                        self.set_with_swr(key, fresh_value, ttl=ttl, stale_window=stale_window)
                        return fresh_value
                    return None
            
            else:
                logger.debug(f"Cache entry is not CachedValue type: {key}")
                return cached_entry
                
        except Exception as e:
            logger.error(f"Error in get_with_swr for key {key}: {e}")
            return None
    
    def set_with_swr(
        self,
        key: str,
        value: Any,
        ttl: int = 300,
        stale_window: int = 300
    ) -> bool:
        """
        Set cache value with SWR support using CachedValue dataclass
        
        Parameters:
        -----------
        key : str
            Cache key
        value : Any
            Value to cache
        ttl : int
            Time-to-live (fresh period) in seconds
        stale_window : int
            Additional time to serve stale content (in seconds)
            
        Returns:
        --------
        bool : True if successful, False otherwise
        """
        if not self.cache:
            logger.warning("Cache not initialized")
            return False
        
        try:
            now = datetime.utcnow()
            cached_value = CachedValue(
                value=value,
                expires_at=now + timedelta(seconds=ttl),
                stale_until=now + timedelta(seconds=ttl + stale_window)
            )
            
            total_timeout = ttl + stale_window
            self.cache.set(key, cached_value, timeout=total_timeout)
            logger.debug(f"Cache set with SWR: {key}, ttl={ttl}s, stale_window={stale_window}s")
            return True
            
        except Exception as e:
            logger.error(f"Error in set_with_swr for key {key}: {e}")
            return False
    
    def _check_cache_freshness(self, key: str) -> bool:
        """
        Check if cache entry is still fresh (not expired)
        
        Parameters:
        -----------
        key : str
            Cache key
            
        Returns:
        --------
        bool : True if cache is fresh, False otherwise
        """
        if not self.cache:
            return False
        
        try:
            cached_entry = self.cache.get(key)
            if cached_entry and isinstance(cached_entry, CachedValue):
                return not cached_entry.is_expired()
            return False
        except Exception as e:
            logger.error(f"Error checking cache freshness for {key}: {e}")
            return False
    
    def _trigger_background_refresh(
        self,
        key: str,
        refresh_callback: Callable[[], Any],
        refresh_args: tuple = (),
        refresh_kwargs: Optional[dict] = None,
        ttl: int = 300,
        stale_window: int = 300,
        use_rq: bool = True
    ):
        """
        Trigger background refresh using RQ (with fallback to threading)
        
        Parameters:
        -----------
        key : str
            Cache key
        refresh_callback : Callable
            Function to fetch fresh data
        refresh_args : tuple
            Positional arguments to pass to refresh_callback
        refresh_kwargs : dict
            Keyword arguments to pass to refresh_callback
        ttl : int
            Time-to-live (fresh period) in seconds
        stale_window : int
            Stale window duration
        use_rq : bool
            Whether to use RQ (falls back to threading if unavailable)
        """
        if refresh_kwargs is None:
            refresh_kwargs = {}
        
        lock_key = f"refresh:{key}"
        
        redis_lock_acquired = self._get_redis_lock(lock_key, timeout=60)
        
        if redis_lock_acquired:
            if use_rq:
                try:
                    from intelligence.workers.worker import enqueue_task
                    from intelligence.workers.tasks import refresh_cache_entry
                    
                    if not hasattr(refresh_callback, '__module__') or not hasattr(refresh_callback, '__name__'):
                        raise ValueError(
                            f"Callback must be a module-level function with __module__ and __name__ attributes. "
                            f"Lambda functions and closures are not supported for RQ tasks."
                        )
                    
                    callback_path = f"{refresh_callback.__module__}.{refresh_callback.__name__}"
                    
                    enqueue_task(
                        'default',
                        refresh_cache_entry,
                        key=key,
                        callback_path=callback_path,
                        callback_args=refresh_args,
                        callback_kwargs=refresh_kwargs,
                        ttl=ttl,
                        stale_window=stale_window,
                        lock_key=lock_key,
                        timeout=ttl
                    )
                    logger.info(f"Enqueued RQ refresh task for key: {key}, callback: {callback_path}, args: {refresh_args}")
                    return
                    
                except Exception as e:
                    logger.warning(f"Failed to enqueue RQ task, falling back to threading: {e}")
                    self._release_redis_lock(lock_key)
                    redis_lock_acquired = False
            
            if redis_lock_acquired:
                def refresh_with_threading():
                    try:
                        if self._check_cache_freshness(key):
                            logger.debug(f"Cache already fresh, skipping refresh: {key}")
                            return
                        
                        logger.debug(f"Starting background refresh (threading): {key}")
                        fresh_value = refresh_callback(*refresh_args, **refresh_kwargs)
                        
                        now = datetime.utcnow()
                        cached_value = CachedValue(
                            value=fresh_value,
                            expires_at=now + timedelta(seconds=ttl),
                            stale_until=now + timedelta(seconds=ttl + stale_window)
                        )
                        
                        if self.cache:
                            self.cache.set(key, cached_value, timeout=ttl + stale_window)
                        
                        logger.info(f"Background refresh complete (threading): {key}")
                        
                    except Exception as e:
                        logger.error(f"Background refresh failed for {key}: {e}")
                    finally:
                        self._release_redis_lock(lock_key)
                
                thread = threading.Thread(target=refresh_with_threading, daemon=True)
                thread.start()
                return
        
        logger.debug(f"Redis lock not available, using process-level threading lock for key: {key}")
        
        with self._process_locks.setdefault(key, threading.Lock()):
            if self._check_cache_freshness(key):
                logger.debug(f"Cache already fresh after acquiring lock, skipping refresh: {key}")
                return
            
            try:
                logger.debug(f"Starting background refresh with threading lock: {key}")
                fresh_value = refresh_callback(*refresh_args, **refresh_kwargs)
                
                now = datetime.utcnow()
                cached_value = CachedValue(
                    value=fresh_value,
                    expires_at=now + timedelta(seconds=ttl),
                    stale_until=now + timedelta(seconds=ttl + stale_window)
                )
                
                if self.cache:
                    self.cache.set(key, cached_value, timeout=ttl + stale_window)
                
                logger.info(f"Background refresh complete (threading lock): {key}")
                
            except Exception as e:
                logger.error(f"Background refresh failed for {key}: {e}")
    
    # ========================================================================
    # Stale-While-Revalidate Pattern Implementation
    # ========================================================================
    
    def get_or_set_with_revalidate(
        self,
        key: str,
        fetch_func: Callable[[], Any],
        timeout: int = 300,
        stale_timeout: int = 600,
        revalidate_callback: Optional[Callable[[Any], None]] = None
    ) -> Optional[Any]:
        """
        Stale-While-Revalidate pattern implementation
        
        This pattern serves stale content while asynchronously revalidating
        the cache in the background, ensuring fast response times.
        
        Parameters:
        -----------
        key : str
            Cache key
        fetch_func : Callable
            Function to fetch fresh data
        timeout : int
            Fresh cache timeout in seconds
        stale_timeout : int
            Stale cache timeout in seconds (should be > timeout)
        revalidate_callback : Optional[Callable]
            Callback to execute after revalidation
            
        Returns:
        --------
        Optional[Any] : Cached or fresh value
        """
        if not self.cache:
            logger.warning("Cache not initialized, fetching fresh data")
            return fetch_func()
        
        try:
            cache_entry = self.cache.get(key)
            
            if cache_entry is not None:
                cached_time = cache_entry.get('timestamp', 0)
                cached_value = cache_entry.get('value')
                age = time.time() - cached_time
                
                if age < timeout:
                    logger.debug(f"Cache fresh: {key}, age={age:.1f}s")
                    return cached_value
                
                elif age < stale_timeout:
                    logger.info(f"Serving stale content and revalidating: {key}, age={age:.1f}s")
                    
                    self._async_revalidate(key, fetch_func, timeout, stale_timeout, revalidate_callback)
                    
                    return cached_value
                
                else:
                    logger.info(f"Cache expired: {key}, age={age:.1f}s")
            
            logger.debug(f"Cache miss, fetching fresh data: {key}")
            fresh_value = fetch_func()
            
            cache_entry = {
                'value': fresh_value,
                'timestamp': time.time()
            }
            self.cache.set(key, cache_entry, timeout=stale_timeout)
            
            return fresh_value
            
        except Exception as e:
            logger.error(f"Stale-while-revalidate error for key {key}: {e}")
            try:
                return fetch_func()
            except Exception as fetch_error:
                logger.error(f"Fetch function failed for key {key}: {fetch_error}")
                return None
    
    def _async_revalidate(
        self,
        key: str,
        fetch_func: Callable[[], Any],
        timeout: int,
        stale_timeout: int,
        callback: Optional[Callable[[Any], None]] = None
    ):
        """
        Asynchronously revalidate cache in background
        
        Parameters:
        -----------
        key : str
            Cache key
        fetch_func : Callable
            Function to fetch fresh data
        timeout : int
            Fresh cache timeout
        stale_timeout : int
            Stale cache timeout
        callback : Optional[Callable]
            Callback to execute after revalidation
        """
        with self._revalidate_lock:
            if key in self._revalidate_locks:
                logger.debug(f"Revalidation already in progress for key: {key}")
                return
            
            self._revalidate_locks[key] = True
        
        def revalidate():
            try:
                logger.debug(f"Starting background revalidation: {key}")
                fresh_value = fetch_func()
                
                cache_entry = {
                    'value': fresh_value,
                    'timestamp': time.time()
                }
                if self.cache:
                    self.cache.set(key, cache_entry, timeout=stale_timeout)
                
                logger.info(f"Background revalidation complete: {key}")
                
                if callback:
                    try:
                        callback(fresh_value)
                    except Exception as cb_error:
                        logger.error(f"Revalidation callback error: {cb_error}")
                
            except Exception as e:
                logger.error(f"Background revalidation failed for {key}: {e}")
            finally:
                with self._revalidate_lock:
                    if key in self._revalidate_locks:
                        del self._revalidate_locks[key]
        
        thread = threading.Thread(target=revalidate, daemon=True)
        thread.start()
    
    # ========================================================================
    # Decorators
    # ========================================================================
    
    def cached(self, timeout: int = 300, key_func: Optional[Callable] = None):
        """
        Decorator for caching function results
        
        Parameters:
        -----------
        timeout : int
            Cache timeout in seconds
        key_func : Optional[Callable]
            Function to generate cache key from function arguments
            
        Usage:
        ------
        @cache_manager.cached(timeout=600, key_func=lambda user_id: f"user:{user_id}")
        def get_user_data(user_id):
            return expensive_operation(user_id)
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                if not self.cache:
                    return func(*args, **kwargs)
                
                if key_func:
                    cache_key = key_func(*args, **kwargs)
                else:
                    cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
                
                cached_value = self.get(cache_key)
                if cached_value is not None:
                    return cached_value
                
                result = func(*args, **kwargs)
                self.set(cache_key, result, timeout=timeout)
                
                return result
            
            return wrapper
        return decorator
    
    def stale_while_revalidate(
        self,
        timeout: int = 300,
        stale_timeout: int = 600,
        key_func: Optional[Callable] = None
    ):
        """
        Decorator for stale-while-revalidate pattern
        
        Parameters:
        -----------
        timeout : int
            Fresh cache timeout in seconds
        stale_timeout : int
            Stale cache timeout in seconds
        key_func : Optional[Callable]
            Function to generate cache key from function arguments
            
        Usage:
        ------
        @cache_manager.stale_while_revalidate(timeout=300, stale_timeout=600)
        def get_forecast(forecast_id):
            return expensive_forecast_calculation(forecast_id)
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                if not self.cache:
                    return func(*args, **kwargs)
                
                if key_func:
                    cache_key = key_func(*args, **kwargs)
                else:
                    cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
                
                return self.get_or_set_with_revalidate(
                    key=cache_key,
                    fetch_func=lambda: func(*args, **kwargs),
                    timeout=timeout,
                    stale_timeout=stale_timeout
                )
            
            return wrapper
        return decorator


# ============================================================================
# Global Instance
# ============================================================================

intelligence_cache = IntelligenceCacheManager()


def init_intelligence_cache(app):
    """
    Initialize intelligence cache with Flask app
    
    Parameters:
    -----------
    app : Flask
        Flask application instance
        
    Usage:
    ------
    from intelligence.cache_manager import init_intelligence_cache
    
    app = Flask(__name__)
    init_intelligence_cache(app)
    """
    intelligence_cache.init_app(app)
    logger.info("Intelligence cache manager initialized")
