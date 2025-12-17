#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RPC故障转移管理器
RPC Failover Manager - Robust Bitcoin RPC Client with Automatic Failover

提供高可用的Bitcoin RPC连接，支持多个端点自动故障转移：
- 智能端点选择和负载均衡
- 自动错误检测和恢复
- API密钥轮换和管理
- 连接健康监控
- 缓存机制减少API调用

Authors: System Integration Team
Date: 2025-09-21
Version: 1.0.0
"""

import os
import time
import random
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import json
import requests
from dataclasses import dataclass, field
import threading
from contextlib import contextmanager

# 配置日志
logger = logging.getLogger(__name__)

@dataclass
class RPCEndpoint:
    """RPC端点配置"""
    url: str
    name: str
    api_key: Optional[str] = None
    headers: Dict[str, str] = field(default_factory=dict)
    priority: int = 1  # 1=最高优先级, 5=最低优先级
    timeout: int = 10
    max_retries: int = 3
    
    # 运行时状态
    is_healthy: bool = True
    last_used: Optional[datetime] = None
    consecutive_failures: int = 0
    total_requests: int = 0
    total_failures: int = 0
    avg_response_time: float = 0.0

    def __post_init__(self):
        """初始化后处理"""
        if self.api_key:
            if 'getblock.io' in self.url:
                # GetBlock需要在URL中添加API key
                if '?' not in self.url:
                    self.url += f"/?api_key={self.api_key}"
                else:
                    self.url += f"&api_key={self.api_key}"
            else:
                # 其他服务使用Header认证
                self.headers['Authorization'] = f'Bearer {self.api_key}'
        
        # 设置通用headers
        self.headers.setdefault('Content-Type', 'application/json')
        self.headers.setdefault('User-Agent', 'Bitcoin-Mining-Calculator/1.0')

class RPCFailoverManager:
    """RPC故障转移管理器"""
    
    def __init__(self):
        self.endpoints: List[RPCEndpoint] = []
        self.current_endpoint_index = 0
        self.health_check_interval = 60  # 秒
        self.last_health_check = datetime.now()
        self.cache = {}
        self.cache_ttl = 300  # 5分钟缓存
        self.lock = threading.RLock()
        
        self._initialize_endpoints()
        
    def _initialize_endpoints(self):
        """初始化RPC端点"""
        # 获取API密钥
        getblock_key = os.environ.get('GETBLOCK_API_KEY')
        blast_key = os.environ.get('BLAST_API_KEY')
        drpc_key = os.environ.get('DRPC_API_KEY')
        grove_key = os.environ.get('GROVE_API_KEY')
        
        # 定义端点配置（按优先级排序）
        endpoint_configs = [
            # 优先级1：付费API服务（最可靠）
            {
                'url': 'https://go.getblock.io/mainnet',
                'name': 'GetBlock',
                'api_key': getblock_key,
                'priority': 1,
                'timeout': 15
            },
            {
                'url': 'https://bitcoin-mainnet.public.blastapi.io',
                'name': 'Blast API',
                'api_key': blast_key,
                'priority': 1,
                'timeout': 12
            },
            
            # 优先级2：免费公共端点
            {
                'url': 'https://bitcoin.drpc.org',
                'name': 'dRPC',
                'api_key': drpc_key,
                'priority': 2,
                'timeout': 10
            },
            {
                'url': 'https://btc-mainnet.rpc.grove.city/v1/',
                'name': 'Grove',
                'api_key': grove_key,
                'priority': 2,
                'timeout': 10
            },
            
            # 优先级3：备用端点
            {
                'url': 'https://bitcoin-rpc.publicnode.com',
                'name': 'PublicNode',
                'priority': 3,
                'timeout': 8
            },
            {
                'url': 'https://btc-mainnet.nodereal.io/v1/public',
                'name': 'NodeReal',
                'priority': 3,
                'timeout': 8
            }
        ]
        
        # 创建端点实例
        for config in endpoint_configs:
            # 只添加有API密钥的付费服务或免费服务
            if config.get('api_key') or config['priority'] >= 2:
                endpoint = RPCEndpoint(**config)
                self.endpoints.append(endpoint)
                logger.info(f"已添加RPC端点: {endpoint.name} (优先级: {endpoint.priority})")
        
        if not self.endpoints:
            logger.warning("没有可用的RPC端点，添加默认端点")
            # 添加一个不需要API key的备用端点
            self.endpoints.append(RPCEndpoint(
                url='https://bitcoin.drpc.org',
                name='dRPC (无认证)',
                priority=4,
                timeout=8
            ))
        
        # 按优先级排序
        self.endpoints.sort(key=lambda x: (x.priority, x.name))
        logger.info(f"初始化完成，共 {len(self.endpoints)} 个RPC端点")
    
    def get_healthy_endpoint(self) -> Optional[RPCEndpoint]:
        """获取健康的端点"""
        with self.lock:
            # 定期健康检查
            if (datetime.now() - self.last_health_check).seconds > self.health_check_interval:
                self._health_check()
            
            # 按优先级查找健康的端点
            healthy_endpoints = [ep for ep in self.endpoints if ep.is_healthy]
            
            if not healthy_endpoints:
                logger.warning("没有健康的RPC端点，尝试重新检查")
                self._reset_health_status()
                healthy_endpoints = self.endpoints[:2]  # 使用前两个端点作为备用
            
            # 在同优先级中进行负载均衡
            if healthy_endpoints:
                # 按优先级分组
                priority_groups = {}
                for ep in healthy_endpoints:
                    if ep.priority not in priority_groups:
                        priority_groups[ep.priority] = []
                    priority_groups[ep.priority].append(ep)
                
                # 选择最高优先级组
                highest_priority = min(priority_groups.keys())
                candidates = priority_groups[highest_priority]
                
                # 在候选者中选择最少使用的或随机选择
                if len(candidates) == 1:
                    return candidates[0]
                else:
                    # 选择最少使用的端点
                    return min(candidates, key=lambda x: (x.total_requests, x.consecutive_failures))
            
            return None
    
    def _health_check(self):
        """健康检查所有端点"""
        logger.debug("执行RPC端点健康检查")
        
        for endpoint in self.endpoints:
            try:
                # 简单的连接测试
                response = requests.get(
                    endpoint.url,
                    headers=endpoint.headers,
                    timeout=5
                )
                
                # 检查响应
                if response.status_code in [200, 401, 403, 405]:
                    # 这些状态码表示端点可达（即使可能需要认证或不支持GET）
                    if not endpoint.is_healthy:
                        logger.info(f"端点 {endpoint.name} 恢复健康")
                    endpoint.is_healthy = True
                    endpoint.consecutive_failures = 0
                else:
                    endpoint.is_healthy = False
                    endpoint.consecutive_failures += 1
                    logger.warning(f"端点 {endpoint.name} 健康检查失败: HTTP {response.status_code}")
                    
            except Exception as e:
                endpoint.is_healthy = False
                endpoint.consecutive_failures += 1
                logger.warning(f"端点 {endpoint.name} 连接失败: {e}")
        
        self.last_health_check = datetime.now()
    
    def _reset_health_status(self):
        """重置所有端点的健康状态"""
        for endpoint in self.endpoints:
            if endpoint.consecutive_failures < 5:  # 不要重置失败太多次的端点
                endpoint.is_healthy = True
                logger.debug(f"重置端点 {endpoint.name} 的健康状态")
    
    def make_rpc_call(self, method: str, params: Optional[List] = None, use_cache: bool = True) -> Dict[str, Any]:
        """
        执行RPC调用，支持自动故障转移
        
        Args:
            method: RPC方法名
            params: 参数列表
            use_cache: 是否使用缓存
            
        Returns:
            RPC响应数据
        """
        params = params or []
        
        # 检查缓存
        if use_cache:
            cache_key = f"{method}:{json.dumps(params)}"
            cached_result = self._get_cached_result(cache_key)
            if cached_result:
                logger.debug(f"使用缓存结果: {method}")
                return cached_result
        
        # 尝试所有端点
        last_error = None
        
        for attempt in range(len(self.endpoints) + 1):  # +1 for retry
            endpoint = self.get_healthy_endpoint()
            
            if not endpoint:
                logger.error("没有可用的RPC端点")
                break
                
            try:
                start_time = time.time()
                
                # 构建RPC请求
                rpc_request = {
                    "jsonrpc": "2.0",
                    "method": method,
                    "params": params,
                    "id": int(time.time() * 1000)
                }
                
                # 发送请求
                response = requests.post(
                    endpoint.url,
                    json=rpc_request,
                    headers=endpoint.headers,
                    timeout=endpoint.timeout
                )
                
                response_time = time.time() - start_time
                
                # 更新统计
                endpoint.total_requests += 1
                endpoint.last_used = datetime.now()
                endpoint.avg_response_time = (
                    endpoint.avg_response_time * (endpoint.total_requests - 1) + response_time
                ) / endpoint.total_requests
                
                if response.status_code == 200:
                    result = response.json()
                    
                    if 'result' in result:
                        # 成功 - 重置失败计数
                        endpoint.consecutive_failures = 0
                        
                        # 缓存结果
                        if use_cache:
                            self._cache_result(cache_key, result['result'])
                        
                        logger.debug(f"RPC调用成功: {method} via {endpoint.name} ({response_time:.2f}s)")
                        return result['result']
                    
                    elif 'error' in result:
                        error_msg = result['error'].get('message', 'Unknown RPC error')
                        logger.warning(f"RPC错误 via {endpoint.name}: {error_msg}")
                        last_error = Exception(f"RPC Error: {error_msg}")
                        
                        # RPC级别错误不算连接失败
                        if 'authentication' in error_msg.lower() or 'unauthorized' in error_msg.lower():
                            endpoint.is_healthy = False  # 认证问题需要标记为不健康
                
                else:
                    # HTTP错误
                    error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
                    logger.warning(f"HTTP错误 via {endpoint.name}: {error_msg}")
                    last_error = Exception(error_msg)
                    
                    endpoint.consecutive_failures += 1
                    endpoint.total_failures += 1
                    
                    # 连续失败3次标记为不健康
                    if endpoint.consecutive_failures >= 3:
                        endpoint.is_healthy = False
                        logger.warning(f"端点 {endpoint.name} 连续失败{endpoint.consecutive_failures}次，标记为不健康")
                
            except requests.exceptions.Timeout:
                logger.warning(f"RPC调用超时: {method} via {endpoint.name}")
                endpoint.consecutive_failures += 1
                endpoint.total_failures += 1
                endpoint.is_healthy = False
                last_error = Exception(f"Timeout calling {endpoint.name}")
                
            except Exception as e:
                logger.warning(f"RPC调用异常 via {endpoint.name}: {e}")
                endpoint.consecutive_failures += 1
                endpoint.total_failures += 1
                last_error = e
                
                # 网络异常标记为不健康
                if isinstance(e, (requests.exceptions.ConnectionError, requests.exceptions.RequestException)):
                    endpoint.is_healthy = False
            
            # 短暂延迟后重试
            time.sleep(0.5)
        
        # 所有端点都失败了
        error_msg = f"所有RPC端点都失败了，最后错误: {last_error}"
        logger.error(error_msg)
        raise Exception(error_msg)
    
    def _get_cached_result(self, cache_key: str) -> Optional[Any]:
        """获取缓存结果"""
        if cache_key in self.cache:
            cached_data, timestamp = self.cache[cache_key]
            if (datetime.now() - timestamp).seconds < self.cache_ttl:
                return cached_data
            else:
                # 缓存过期
                del self.cache[cache_key]
        return None
    
    def _cache_result(self, cache_key: str, result: Any):
        """缓存结果"""
        self.cache[cache_key] = (result, datetime.now())
        
        # 清理过期缓存
        if len(self.cache) > 100:  # 避免缓存过大
            expired_keys = []
            now = datetime.now()
            for key, (_, timestamp) in self.cache.items():
                if (now - timestamp).seconds > self.cache_ttl:
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self.cache[key]
    
    # Bitcoin特定的便捷方法
    
    def get_blockchain_info(self) -> Dict[str, Any]:
        """获取区块链信息"""
        return self.make_rpc_call('getblockchaininfo')
    
    def get_network_hashrate(self, blocks: int = 144) -> float:
        """获取网络算力（EH/s）"""
        try:
            result = self.make_rpc_call('getnetworkhashps', [blocks])
            # 转换为EH/s (1 EH/s = 10^18 H/s)
            return result / 1e18
        except Exception:
            # 如果RPC失败，尝试其他数据源
            return self._get_hashrate_from_alternative_sources()
    
    def get_difficulty(self) -> float:
        """获取挖矿难度"""
        return self.make_rpc_call('getdifficulty')
    
    def get_block_count(self) -> int:
        """获取区块高度"""
        return self.make_rpc_call('getblockcount')
    
    def get_block(self, block_hash: str, verbosity: int = 1) -> Dict[str, Any]:
        """获取区块信息"""
        return self.make_rpc_call('getblock', [block_hash, verbosity])
    
    def get_block_hash(self, height: int) -> str:
        """根据高度获取区块哈希"""
        return self.make_rpc_call('getblockhash', [height])
    
    def _get_hashrate_from_alternative_sources(self) -> float:
        """从备用数据源获取算力"""
        try:
            # 尝试blockchain.info API
            response = requests.get('https://blockchain.info/q/hashrate', timeout=10)
            if response.status_code == 200:
                # blockchain.info返回的是TH/s，需要转换为EH/s
                hashrate_th = float(response.text.strip())
                return hashrate_th / 1000  # TH/s to EH/s
        except Exception as e:
            logger.warning(f"备用算力数据源失败: {e}")
        
        # 返回默认估计值
        return 500.0  # 默认500 EH/s
    
    def get_status_report(self) -> Dict[str, Any]:
        """获取故障转移状态报告"""
        with self.lock:
            healthy_count = sum(1 for ep in self.endpoints if ep.is_healthy)
            
            endpoint_status = []
            for ep in self.endpoints:
                status = {
                    'name': ep.name,
                    'url': ep.url[:50] + '...' if len(ep.url) > 50 else ep.url,
                    'priority': ep.priority,
                    'is_healthy': ep.is_healthy,
                    'consecutive_failures': ep.consecutive_failures,
                    'total_requests': ep.total_requests,
                    'total_failures': ep.total_failures,
                    'success_rate': ((ep.total_requests - ep.total_failures) / ep.total_requests * 100) if ep.total_requests > 0 else 0,
                    'avg_response_time': ep.avg_response_time,
                    'last_used': ep.last_used.isoformat() if ep.last_used else None
                }
                endpoint_status.append(status)
            
            return {
                'total_endpoints': len(self.endpoints),
                'healthy_endpoints': healthy_count,
                'unhealthy_endpoints': len(self.endpoints) - healthy_count,
                'last_health_check': self.last_health_check.isoformat(),
                'cache_size': len(self.cache),
                'endpoints': endpoint_status
            }


# 全局实例
_rpc_manager = None

def get_rpc_manager() -> RPCFailoverManager:
    """获取RPC管理器实例（单例模式）"""
    global _rpc_manager
    if _rpc_manager is None:
        _rpc_manager = RPCFailoverManager()
    return _rpc_manager

# 便捷函数
def get_btc_network_info() -> Dict[str, Any]:
    """获取Bitcoin网络信息"""
    manager = get_rpc_manager()
    return {
        'blockchain_info': manager.get_blockchain_info(),
        'network_hashrate': manager.get_network_hashrate(),
        'difficulty': manager.get_difficulty(),
        'block_count': manager.get_block_count()
    }

if __name__ == "__main__":
    # 测试RPC故障转移
    manager = RPCFailoverManager()
    
    print("🔍 RPC故障转移管理器测试")
    print("="*50)
    
    try:
        # 测试基本连接
        info = manager.get_blockchain_info()
        print(f"✅ 区块链信息获取成功")
        print(f"   区块数量: {info.get('blocks', 'N/A')}")
        print(f"   链: {info.get('chain', 'N/A')}")
        
        # 测试算力获取
        hashrate = manager.get_network_hashrate()
        print(f"✅ 网络算力: {hashrate:.2f} EH/s")
        
        # 测试难度获取
        difficulty = manager.get_difficulty()
        print(f"✅ 挖矿难度: {difficulty:,.0f}")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
    
    # 显示状态报告
    print(f"\n📊 RPC端点状态:")
    report = manager.get_status_report()
    print(f"   总端点: {report['total_endpoints']}")
    print(f"   健康端点: {report['healthy_endpoints']}")
    print(f"   不健康端点: {report['unhealthy_endpoints']}")
    
    for ep in report['endpoints']:
        status_icon = "✅" if ep['is_healthy'] else "❌"
        print(f"   {status_icon} {ep['name']}: 成功率{ep['success_rate']:.1f}%, 平均响应{ep['avg_response_time']:.2f}s")