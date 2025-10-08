"""
HashInsight CDC Platform - Redis Client
Redis客户端和缓存工具
"""
import os
import json
import logging
from typing import Any, Optional
from datetime import timedelta
import redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)

class RedisClient:
    """Redis客户端封装，提供缓存和分布式锁功能"""
    
    def __init__(self):
        """初始化Redis连接"""
        self.redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        self.client = None
        self._connect()
    
    def _connect(self):
        """建立Redis连接"""
        try:
            self.client = redis.from_url(
                self.redis_url,
                decode_responses=True,  # 自动解码为字符串
                socket_timeout=5,
                socket_connect_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )
            
            # 测试连接
            self.client.ping()
            logger.info(f"✅ Redis connected: {self.redis_url}")
        except RedisError as e:
            logger.error(f"❌ Redis connection failed: {e}")
            logger.warning("⚠️ Running without Redis - caching disabled")
            self.client = None
    
    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值
        
        参数:
            key: 缓存键
        
        返回:
            缓存值（JSON解析后）或None
        """
        if not self.client:
            return None
        
        try:
            value = self.client.get(key)
            if value:
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value
            return None
        except RedisError as e:
            logger.error(f"Redis GET error for key '{key}': {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """
        设置缓存值
        
        参数:
            key: 缓存键
            value: 缓存值（自动JSON序列化）
            ttl: 过期时间（秒），默认1小时
        
        返回:
            是否成功
        """
        if not self.client:
            return False
        
        try:
            # 如果value不是字符串，则JSON序列化
            if not isinstance(value, str):
                value = json.dumps(value, ensure_ascii=False)
            
            self.client.setex(key, ttl, value)
            return True
        except RedisError as e:
            logger.error(f"Redis SET error for key '{key}': {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """
        删除缓存
        
        参数:
            key: 缓存键
        
        返回:
            是否成功
        """
        if not self.client:
            return False
        
        try:
            self.client.delete(key)
            return True
        except RedisError as e:
            logger.error(f"Redis DELETE error for key '{key}': {e}")
            return False
    
    def incr(self, key: str) -> int:
        """
        自增计数器（用于速率限制）
        
        参数:
            key: 计数器键
        
        返回:
            自增后的值
        """
        if not self.client:
            return 0
        
        try:
            return self.client.incr(key)
        except RedisError as e:
            logger.error(f"Redis INCR error for key '{key}': {e}")
            return 0
    
    def expire(self, key: str, seconds: int) -> bool:
        """
        设置键的过期时间
        
        参数:
            key: 缓存键
            seconds: 过期秒数
        
        返回:
            是否成功
        """
        if not self.client:
            return False
        
        try:
            return self.client.expire(key, seconds)
        except RedisError as e:
            logger.error(f"Redis EXPIRE error for key '{key}': {e}")
            return False
    
    def acquire_lock(self, lock_name: str, timeout: int = 10, blocking_timeout: int = 5) -> Optional[Any]:
        """
        获取分布式锁（用于防止并发写入）
        
        参数:
            lock_name: 锁名称
            timeout: 锁超时时间（秒）
            blocking_timeout: 等待锁的超时时间（秒）
        
        返回:
            锁对象或None
        """
        if not self.client:
            return None
        
        try:
            lock = self.client.lock(
                f"lock:{lock_name}",
                timeout=timeout,
                blocking_timeout=blocking_timeout
            )
            
            if lock.acquire():
                return lock
            
            logger.warning(f"Failed to acquire lock: {lock_name}")
            return None
        except RedisError as e:
            logger.error(f"Redis LOCK error for '{lock_name}': {e}")
            return None
    
    def release_lock(self, lock) -> bool:
        """
        释放分布式锁
        
        参数:
            lock: 锁对象
        
        返回:
            是否成功
        """
        if not lock:
            return False
        
        try:
            lock.release()
            return True
        except RedisError as e:
            logger.error(f"Redis UNLOCK error: {e}")
            return False
    
    def cache_decorator(self, key_prefix: str, ttl: int = 3600):
        """
        缓存装饰器
        
        参数:
            key_prefix: 缓存键前缀
            ttl: 过期时间（秒）
        
        用法:
            @redis_client.cache_decorator('user', ttl=1800)
            def get_user(user_id):
                return fetch_user_from_db(user_id)
        """
        def decorator(func):
            def wrapper(*args, **kwargs):
                # 生成缓存键
                cache_key = f"{key_prefix}:{':'.join(map(str, args))}"
                
                # 尝试从缓存获取
                cached = self.get(cache_key)
                if cached is not None:
                    logger.debug(f"Cache hit: {cache_key}")
                    return cached
                
                # 缓存未命中，执行函数
                result = func(*args, **kwargs)
                
                # 写入缓存
                self.set(cache_key, result, ttl)
                logger.debug(f"Cache set: {cache_key}")
                
                return result
            
            return wrapper
        return decorator
    
    def flush_pattern(self, pattern: str) -> int:
        """
        删除匹配模式的所有键
        
        参数:
            pattern: Redis键模式（如 'user:*'）
        
        返回:
            删除的键数量
        """
        if not self.client:
            return 0
        
        try:
            keys = self.client.keys(pattern)
            if keys:
                return self.client.delete(*keys)
            return 0
        except RedisError as e:
            logger.error(f"Redis FLUSH error for pattern '{pattern}': {e}")
            return 0
    
    def health_check(self) -> dict:
        """
        健康检查
        
        返回:
            健康状态字典
        """
        if not self.client:
            return {'status': 'disconnected', 'error': 'Redis client not initialized'}
        
        try:
            info = self.client.info('server')
            return {
                'status': 'healthy',
                'version': info.get('redis_version'),
                'uptime_seconds': info.get('uptime_in_seconds'),
                'connected_clients': info.get('connected_clients')
            }
        except RedisError as e:
            return {'status': 'unhealthy', 'error': str(e)}


# 创建全局Redis客户端实例
redis_client = RedisClient()
