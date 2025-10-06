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
- optimize:{id}:{date}
"""

import logging
import os
import threading
import time
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Callable, Optional, Dict, List, Union
from flask_caching import Cache

logger = logging.getLogger(__name__)


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
    def optimize_key(optimization_id: int, date: str) -> str:
        """
        Generate cache key for optimization result
        
        Parameters:
        -----------
        optimization_id : int
            Optimization ID
        date : str
            Date string (YYYY-MM-DD format)
            
        Returns:
        --------
        str : Cache key in format optimize:{id}:{date}
        """
        return f"optimize:{optimization_id}:{date}"
    
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
    def user_optimizations_key(user_id: int) -> str:
        """
        Generate cache key for all user optimizations
        
        Parameters:
        -----------
        user_id : int
            User ID
            
        Returns:
        --------
        str : Cache key in format user_optimizations:{id}
        """
        return f"user_optimizations:{user_id}"
    
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
    
    def invalidate_user_optimizations(self, user_id: int) -> bool:
        """
        Invalidate all user optimization caches
        
        Parameters:
        -----------
        user_id : int
            User ID
            
        Returns:
        --------
        bool : True if successful
        """
        key = self.user_optimizations_key(user_id)
        logger.info(f"Invalidating user optimizations cache: user_id={user_id}")
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
    
    def invalidate_optimization(self, optimization_id: int, date: Optional[str] = None) -> bool:
        """
        Invalidate optimization cache
        
        Parameters:
        -----------
        optimization_id : int
            Optimization ID
        date : Optional[str]
            Specific date to invalidate (None invalidates all dates)
            
        Returns:
        --------
        bool : True if successful
        """
        if date:
            key = self.optimize_key(optimization_id, date)
            logger.info(f"Invalidating optimization cache: optimization_id={optimization_id}, date={date}")
            return self.delete(key)
        else:
            logger.info(f"Invalidating all optimization caches for optimization_id={optimization_id}")
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
            self.user_optimizations_key(user_id)
        ]
        
        return self.delete_many(*keys_to_delete)
    
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
