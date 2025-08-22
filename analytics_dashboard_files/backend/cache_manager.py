"""
缓存管理器 - 优化数据访问性能
"""
import json
import time
import logging
from functools import wraps
from typing import Any, Optional, Callable

logger = logging.getLogger(__name__)

class CacheManager:
    """简单的内存缓存管理器"""
    
    def __init__(self, default_ttl: int = 300):
        """
        初始化缓存管理器
        :param default_ttl: 默认缓存时间（秒）
        """
        self._cache = {}
        self._default_ttl = default_ttl
        self._stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0
        }
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        if key in self._cache:
            entry = self._cache[key]
            if entry['expires'] > time.time():
                self._stats['hits'] += 1
                logger.debug(f"Cache hit for key: {key}")
                return entry['value']
            else:
                # 过期，删除
                del self._cache[key]
        
        self._stats['misses'] += 1
        logger.debug(f"Cache miss for key: {key}")
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """设置缓存值"""
        ttl = ttl or self._default_ttl
        self._cache[key] = {
            'value': value,
            'expires': time.time() + ttl
        }
        self._stats['sets'] += 1
        logger.debug(f"Cache set for key: {key}, TTL: {ttl}s")
    
    def delete(self, key: str) -> bool:
        """删除缓存值"""
        if key in self._cache:
            del self._cache[key]
            self._stats['deletes'] += 1
            logger.debug(f"Cache deleted for key: {key}")
            return True
        return False
    
    def clear(self) -> None:
        """清空所有缓存"""
        count = len(self._cache)
        self._cache.clear()
        logger.info(f"Cache cleared, removed {count} entries")
    
    def cleanup(self) -> int:
        """清理过期缓存"""
        current_time = time.time()
        expired_keys = [
            key for key, entry in self._cache.items()
            if entry['expires'] <= current_time
        ]
        
        for key in expired_keys:
            del self._cache[key]
        
        if expired_keys:
            logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")
        
        return len(expired_keys)
    
    def get_stats(self) -> dict:
        """获取缓存统计信息"""
        total_requests = self._stats['hits'] + self._stats['misses']
        hit_rate = (self._stats['hits'] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            **self._stats,
            'total_requests': total_requests,
            'hit_rate': f"{hit_rate:.2f}%",
            'current_size': len(self._cache)
        }

# 全局缓存实例
cache = CacheManager()

def cached(ttl: int = 300, key_prefix: str = ''):
    """
    缓存装饰器
    :param ttl: 缓存时间（秒）
    :param key_prefix: 缓存键前缀
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = f"{key_prefix}:{func.__name__}:{str(args)}:{str(kwargs)}"
            
            # 尝试从缓存获取
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # 执行函数并缓存结果
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl)
            
            return result
        
        return wrapper
    return decorator

# 预定义的缓存键
class CacheKeys:
    """预定义的缓存键常量"""
    BTC_PRICE = 'market:btc_price'
    NETWORK_HASHRATE = 'market:network_hashrate'
    NETWORK_DIFFICULTY = 'market:network_difficulty'
    FEAR_GREED_INDEX = 'market:fear_greed'
    TECHNICAL_INDICATORS = 'analysis:technical_indicators'
    USER_PLAN = 'user:plan:{user_id}'
    MINER_SPECS = 'miners:specs'
    
    @staticmethod
    def user_plan(user_id: int) -> str:
        """生成用户计划缓存键"""
        return f'user:plan:{user_id}'
    
    @staticmethod
    def user_stats(user_id: int) -> str:
        """生成用户统计缓存键"""
        return f'user:stats:{user_id}'