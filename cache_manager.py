"""
缓存管理器 - 优化数据访问性能
Enhanced Cache Manager with Redis Support

支持多种缓存策略：
- 内存缓存（开发环境）
- Redis缓存（生产环境）
- 多级缓存（内存+Redis）

目标：API响应时间p95 ≤250ms
Target: API response time p95 ≤250ms
"""
import json
import time
import logging
import os
import pickle
import hashlib
from functools import wraps
from typing import Any, Optional, Callable, Dict, List
from datetime import datetime, timedelta
try:
    import yaml
except ImportError:
    yaml = None

logger = logging.getLogger(__name__)

# ============================================================================
# Redis缓存后端支持
# Redis Cache Backend Support
# ============================================================================

class RedisCacheBackend:
    """Redis缓存后端"""
    
    def __init__(self, host='localhost', port=6379, db=0, password=None, 
                 key_prefix='hashinsight:', decode_responses=True):
        """
        初始化Redis缓存后端
        
        Parameters:
        -----------
        host : str
            Redis服务器地址
        port : int
            Redis端口
        db : int
            数据库编号
        password : str
            Redis密码
        key_prefix : str
            键前缀
        decode_responses : bool
            是否自动解码响应
        """
        try:
            import redis
            self.redis = redis.Redis(
                host=host,
                port=port,
                db=db,
                password=password,
                decode_responses=decode_responses
            )
            self.key_prefix = key_prefix
            self.enabled = True
            logger.info(f"Redis缓存后端已启用: {host}:{port}/{db}")
        except ImportError:
            logger.warning("redis库未安装，Redis缓存功能不可用")
            self.enabled = False
        except Exception as e:
            logger.error(f"Redis连接失败: {e}")
            self.enabled = False
    
    def _make_key(self, key: str) -> str:
        """生成带前缀的键"""
        return f"{self.key_prefix}{key}"
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        if not self.enabled:
            return None
        
        try:
            full_key = self._make_key(key)
            value = self.redis.get(full_key)
            if value:
                # 尝试反序列化
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value
            return None
        except Exception as e:
            logger.error(f"Redis get错误: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存值"""
        if not self.enabled:
            return False
        
        try:
            full_key = self._make_key(key)
            # 序列化值
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            
            if ttl:
                self.redis.setex(full_key, ttl, value)
            else:
                self.redis.set(full_key, value)
            return True
        except Exception as e:
            logger.error(f"Redis set错误: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """删除缓存值"""
        if not self.enabled:
            return False
        
        try:
            full_key = self._make_key(key)
            self.redis.delete(full_key)
            return True
        except Exception as e:
            logger.error(f"Redis delete错误: {e}")
            return False
    
    def clear(self, pattern: str = '*') -> int:
        """清空匹配的缓存"""
        if not self.enabled:
            return 0
        
        try:
            full_pattern = self._make_key(pattern)
            keys = self.redis.keys(full_pattern)
            if keys:
                return self.redis.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Redis clear错误: {e}")
            return 0
    
    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        if not self.enabled:
            return False
        
        try:
            full_key = self._make_key(key)
            return self.redis.exists(full_key) > 0
        except Exception as e:
            logger.error(f"Redis exists错误: {e}")
            return False
    
    def ttl(self, key: str) -> int:
        """获取键的TTL"""
        if not self.enabled:
            return -1
        
        try:
            full_key = self._make_key(key)
            return self.redis.ttl(full_key)
        except Exception as e:
            logger.error(f"Redis ttl错误: {e}")
            return -1


# ============================================================================
# 内存缓存后端（开发环境 Fallback）
# Memory Cache Backend (Development Fallback)
# ============================================================================

class MemoryCacheBackend:
    """内存缓存后端"""
    
    def __init__(self, default_ttl: int = 300):
        """
        初始化内存缓存后端
        :param default_ttl: 默认缓存时间（秒）
        """
        self._cache = {}
        self._default_ttl = default_ttl
        self.enabled = True
        logger.info("内存缓存后端已启用")
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        if key in self._cache:
            entry = self._cache[key]
            if entry['expires'] > time.time():
                return entry['value']
            else:
                # 过期，删除
                del self._cache[key]
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存值"""
        ttl = ttl or self._default_ttl
        self._cache[key] = {
            'value': value,
            'expires': time.time() + ttl
        }
        return True
    
    def delete(self, key: str) -> bool:
        """删除缓存值"""
        if key in self._cache:
            del self._cache[key]
            return True
        return False
    
    def clear(self, pattern: str = '*') -> int:
        """清空匹配的缓存"""
        if pattern == '*':
            count = len(self._cache)
            self._cache.clear()
            return count
        
        # 简单的模式匹配
        keys_to_delete = [k for k in self._cache.keys() if pattern.replace('*', '') in k]
        for key in keys_to_delete:
            del self._cache[key]
        return len(keys_to_delete)
    
    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        if key in self._cache:
            if self._cache[key]['expires'] > time.time():
                return True
            else:
                del self._cache[key]
        return False
    
    def ttl(self, key: str) -> int:
        """获取键的TTL"""
        if key in self._cache:
            ttl = int(self._cache[key]['expires'] - time.time())
            return max(ttl, -1)
        return -2
    
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
            logger.info(f"清理了 {len(expired_keys)} 个过期缓存条目")
        
        return len(expired_keys)


# ============================================================================
# 多级缓存管理器
# Multi-Level Cache Manager
# ============================================================================

class EnhancedCacheManager:
    """
    增强型缓存管理器
    Enhanced Cache Manager with Redis and Multi-level Support
    
    支持：
    - 内存缓存（L1）
    - Redis缓存（L2）
    - 缓存预热
    - 缓存失效策略
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化缓存管理器
        
        Parameters:
        -----------
        config_path : str
            配置文件路径
        """
        self.config = self._load_config(config_path)
        self._stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0,
            'l1_hits': 0,
            'l2_hits': 0
        }
        
        # 初始化缓存后端
        self._init_backends()
    
    def _load_config(self, config_path: Optional[str]) -> Dict:
        """加载配置"""
        default_config = {
            'backend': os.getenv('CACHE_BACKEND', 'memory'),  # memory, redis, multi
            'redis': {
                'host': os.getenv('REDIS_HOST', 'localhost'),
                'port': int(os.getenv('REDIS_PORT', 6379)),
                'db': int(os.getenv('REDIS_DB', 0)),
                'password': os.getenv('REDIS_PASSWORD'),
                'key_prefix': 'hashinsight:'
            },
            'memory': {
                'default_ttl': 300
            },
            'ttl_strategy': {
                'btc_price': 5,  # 5秒
                'network_difficulty': 600,  # 10分钟
                'network_hashrate': 600,  # 10分钟
                'miner_specs': 3600,  # 1小时
                'calculation_results': 300,  # 5分钟
                'user_plan': 1800,  # 30分钟
                'default': 300  # 5分钟
            }
        }
        
        # 如果提供了配置文件，尝试加载
        if config_path and os.path.exists(config_path) and yaml:
            try:
                with open(config_path, 'r') as f:
                    file_config = yaml.safe_load(f)
                    default_config.update(file_config)
                    logger.info(f"从{config_path}加载缓存配置")
            except Exception as e:
                logger.warning(f"加载配置文件失败: {e}, 使用默认配置")
        
        return default_config
    
    def _init_backends(self):
        """初始化缓存后端"""
        backend_type = self.config['backend']
        
        if backend_type == 'redis':
            # 仅使用Redis
            self.l1_cache = None
            self.l2_cache = RedisCacheBackend(**self.config['redis'])
            self.primary_backend = self.l2_cache
            logger.info("使用Redis缓存后端")
        
        elif backend_type == 'multi':
            # 多级缓存：内存(L1) + Redis(L2)
            self.l1_cache = MemoryCacheBackend(**self.config['memory'])
            self.l2_cache = RedisCacheBackend(**self.config['redis'])
            self.primary_backend = self.l1_cache
            logger.info("使用多级缓存：内存(L1) + Redis(L2)")
        
        else:
            # 默认使用内存缓存
            self.l1_cache = MemoryCacheBackend(**self.config['memory'])
            self.l2_cache = None
            self.primary_backend = self.l1_cache
            logger.info("使用内存缓存后端")
    
    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值（支持多级缓存）
        
        查找顺序：
        1. L1缓存（内存）
        2. L2缓存（Redis）
        3. 如果从L2找到，回填到L1
        """
        # 先查L1缓存
        if self.l1_cache and self.l1_cache.enabled:
            value = self.l1_cache.get(key)
            if value is not None:
                self._stats['hits'] += 1
                self._stats['l1_hits'] += 1
                logger.debug(f"L1缓存命中: {key}")
                return value
        
        # 再查L2缓存
        if self.l2_cache and self.l2_cache.enabled:
            value = self.l2_cache.get(key)
            if value is not None:
                self._stats['hits'] += 1
                self._stats['l2_hits'] += 1
                logger.debug(f"L2缓存命中: {key}")
                
                # 回填到L1缓存
                if self.l1_cache and self.l1_cache.enabled:
                    ttl = self._get_ttl_for_key(key)
                    self.l1_cache.set(key, value, ttl)
                    logger.debug(f"L2->L1回填: {key}")
                
                return value
        
        # 缓存未命中
        self._stats['misses'] += 1
        logger.debug(f"缓存未命中: {key}")
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        设置缓存值（同时写入所有级别）
        
        写入策略：
        - 如果是多级缓存，同时写入L1和L2
        - 如果单级缓存，只写入对应后端
        """
        if ttl is None:
            ttl = self._get_ttl_for_key(key)
        
        success = True
        
        # 写入L1缓存
        if self.l1_cache and self.l1_cache.enabled:
            success = self.l1_cache.set(key, value, ttl) and success
        
        # 写入L2缓存
        if self.l2_cache and self.l2_cache.enabled:
            success = self.l2_cache.set(key, value, ttl) and success
        
        if success:
            self._stats['sets'] += 1
            logger.debug(f"缓存已设置: {key}, TTL={ttl}s")
        
        return success
    
    def delete(self, key: str) -> bool:
        """删除缓存值（从所有级别删除）"""
        success = True
        
        # 从L1删除
        if self.l1_cache and self.l1_cache.enabled:
            success = self.l1_cache.delete(key) and success
        
        # 从L2删除
        if self.l2_cache and self.l2_cache.enabled:
            success = self.l2_cache.delete(key) and success
        
        if success:
            self._stats['deletes'] += 1
            logger.debug(f"缓存已删除: {key}")
        
        return success
    
    def clear(self, pattern: str = '*') -> int:
        """清空匹配的缓存"""
        count = 0
        
        if self.l1_cache and self.l1_cache.enabled:
            count += self.l1_cache.clear(pattern)
        
        if self.l2_cache and self.l2_cache.enabled:
            count += self.l2_cache.clear(pattern)
        
        logger.info(f"清空缓存，模式={pattern}, 删除={count}条")
        return count
    
    def _get_ttl_for_key(self, key: str) -> int:
        """根据键获取TTL"""
        ttl_strategy = self.config['ttl_strategy']
        
        # 检查键是否匹配预定义的策略
        for pattern, ttl in ttl_strategy.items():
            if pattern in key:
                return ttl
        
        # 返回默认TTL
        return ttl_strategy.get('default', 300)
    
    def get_stats(self) -> dict:
        """获取缓存统计信息"""
        total_requests = self._stats['hits'] + self._stats['misses']
        hit_rate = (self._stats['hits'] / total_requests * 100) if total_requests > 0 else 0
        
        l1_hit_rate = (self._stats['l1_hits'] / total_requests * 100) if total_requests > 0 else 0
        l2_hit_rate = (self._stats['l2_hits'] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            **self._stats,
            'total_requests': total_requests,
            'hit_rate': f"{hit_rate:.2f}%",
            'l1_hit_rate': f"{l1_hit_rate:.2f}%",
            'l2_hit_rate': f"{l2_hit_rate:.2f}%",
            'backend': self.config['backend']
        }
    
    def warmup(self, warmup_data: List[Dict[str, Any]]) -> int:
        """
        缓存预热
        Cache Warmup
        
        Parameters:
        -----------
        warmup_data : List[Dict]
            预热数据列表，格式：[{'key': 'xxx', 'value': xxx, 'ttl': xxx}, ...]
            
        Returns:
        --------
        int : 成功预热的条目数
        """
        success_count = 0
        
        for item in warmup_data:
            key = item.get('key')
            value = item.get('value')
            ttl = item.get('ttl')
            
            if key and value is not None:
                if self.set(key, value, ttl):
                    success_count += 1
        
        logger.info(f"缓存预热完成：{success_count}/{len(warmup_data)} 条")
        return success_count
    
    def export_metrics(self) -> Dict:
        """
        导出监控指标
        Export monitoring metrics for Prometheus/CloudWatch
        """
        stats = self.get_stats()
        
        return {
            'cache_hits_total': self._stats['hits'],
            'cache_misses_total': self._stats['misses'],
            'cache_sets_total': self._stats['sets'],
            'cache_deletes_total': self._stats['deletes'],
            'cache_hit_rate': float(stats['hit_rate'].rstrip('%')),
            'cache_l1_hits_total': self._stats['l1_hits'],
            'cache_l2_hits_total': self._stats['l2_hits'],
            'cache_backend': self.config['backend']
        }


# ============================================================================
# 全局缓存实例和装饰器
# Global Cache Instance and Decorators
# ============================================================================

# 初始化缓存管理器
config_file = os.getenv('CACHE_CONFIG', 'cache_config.yaml')
cache = EnhancedCacheManager(config_file if os.path.exists(config_file) else None)

def cached(ttl: Optional[int] = None, key_prefix: str = '', cache_backend=None):
    """
    缓存装饰器
    Cache Decorator
    
    Parameters:
    -----------
    ttl : int
        缓存时间（秒），None则使用配置中的TTL策略
    key_prefix : str
        缓存键前缀
    cache_backend : CacheManager
        缓存后端，None则使用全局cache
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 使用全局cache或指定的backend
            cache_instance = cache_backend or cache
            
            # 生成缓存键（使用哈希避免过长）
            args_str = str(args) + str(kwargs)
            args_hash = hashlib.md5(args_str.encode()).hexdigest()[:8]
            cache_key = f"{key_prefix}:{func.__name__}:{args_hash}"
            
            # 尝试从缓存获取
            cached_value = cache_instance.get(cache_key)
            if cached_value is not None:
                logger.debug(f"缓存装饰器命中: {func.__name__}")
                return cached_value
            
            # 执行函数并缓存结果
            result = func(*args, **kwargs)
            cache_instance.set(cache_key, result, ttl)
            logger.debug(f"缓存装饰器存储: {func.__name__}")
            
            return result
        
        return wrapper
    return decorator


# ============================================================================
# 预定义的缓存键和TTL策略
# Predefined Cache Keys and TTL Strategies
# ============================================================================

class CacheKeys:
    """预定义的缓存键常量"""
    
    # 市场数据（实时性要求高）
    BTC_PRICE = 'market:btc_price'  # TTL: 5s
    NETWORK_HASHRATE = 'market:network_hashrate'  # TTL: 10m
    NETWORK_DIFFICULTY = 'market:network_difficulty'  # TTL: 10m
    BLOCK_REWARD = 'market:block_reward'  # TTL: 1h
    
    # 分析数据
    FEAR_GREED_INDEX = 'market:fear_greed'  # TTL: 1h
    TECHNICAL_INDICATORS = 'analysis:technical_indicators'  # TTL: 5m
    
    # 矿机数据（相对稳定）
    MINER_SPECS = 'miners:specs'  # TTL: 1h
    MINER_MODELS = 'miners:models'  # TTL: 1h
    
    # 计算结果（基于参数哈希）
    CALCULATION_RESULT = 'calc:result'  # TTL: 5m
    
    # 用户数据
    USER_PLAN = 'user:plan:{user_id}'  # TTL: 30m
    USER_STATS = 'user:stats:{user_id}'  # TTL: 5m
    
    @staticmethod
    def user_plan(user_id: int) -> str:
        """生成用户计划缓存键"""
        return f'user:plan:{user_id}'
    
    @staticmethod
    def user_stats(user_id: int) -> str:
        """生成用户统计缓存键"""
        return f'user:stats:{user_id}'
    
    @staticmethod
    def calculation_result(params_hash: str) -> str:
        """生成计算结果缓存键"""
        return f'calc:result:{params_hash}'


# 向后兼容：保留原有的CacheManager类（别名）
CacheManager = MemoryCacheBackend
