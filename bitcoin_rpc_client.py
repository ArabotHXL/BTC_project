"""
Bitcoin RPC Client
提供Bitcoin节点RPC连接和数据获取功能
"""

import logging
import requests
import json
from typing import Dict, Optional, Any
import time
from datetime import datetime

logger = logging.getLogger(__name__)

class BitcoinRPCClient:
    """Bitcoin RPC客户端"""
    
    def __init__(self, rpc_url: str = None, rpc_user: str = None, rpc_password: str = None):
        # 使用免费的RPC服务作为默认
        self.rpc_url = rpc_url or "https://go.getblock.io/mainnet"  # 免费RPC服务
        self.rpc_user = rpc_user
        self.rpc_password = rpc_password
        self.session = requests.Session()
        
        # 配置请求头
        if self.rpc_user and self.rpc_password:
            self.session.auth = (self.rpc_user, self.rpc_password)
        
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'Bitcoin-Mining-Analytics/1.0'
        })
        
        logger.info(f"Bitcoin RPC客户端初始化: {self.rpc_url}")
    
    def _make_request(self, method: str, params: list = None) -> Dict:
        """发送RPC请求"""
        try:
            payload = {
                'jsonrpc': '2.0',
                'method': method,
                'params': params or [],
                'id': int(time.time())
            }
            
            response = self.session.post(
                self.rpc_url,
                data=json.dumps(payload),
                timeout=30
            )
            
            response.raise_for_status()
            result = response.json()
            
            if 'error' in result and result['error']:
                error_msg = result['error']
                logger.error(f"RPC错误: {error_msg}")
                raise Exception(f"RPC Error: {error_msg}")
            
            return result.get('result', {})
            
        except requests.exceptions.RequestException as e:
            logger.error(f"RPC请求失败: {e}")
            raise Exception(f"RPC Request Failed: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"RPC响应解析失败: {e}")
            raise Exception(f"RPC Response Parse Error: {e}")
    
    def get_blockchain_info(self) -> Dict:
        """获取区块链信息"""
        try:
            info = self._make_request('getblockchaininfo')
            logger.info(f"Bitcoin RPC连接成功 - 当前区块: {info.get('blocks', 'Unknown')}")
            return info
        except Exception as e:
            logger.error(f"获取区块链信息失败: {e}")
            return {}
    
    def get_network_hashps(self, blocks: int = 120) -> float:
        """获取网络算力"""
        try:
            hashps = self._make_request('getnetworkhashps', [blocks])
            # 转换为EH/s
            hashps_eh = float(hashps) / 1e18
            logger.info(f"网络算力: {hashps_eh:.2f} EH/s")
            return hashps_eh
        except Exception as e:
            logger.error(f"获取网络算力失败: {e}")
            logger.info("RPC挖矿信息API受限，将使用备用数据源")
            return 0.0
    
    def get_difficulty(self) -> float:
        """获取挖矿难度"""
        try:
            difficulty = self._make_request('getdifficulty')
            logger.info(f"挖矿难度: {difficulty}")
            return float(difficulty)
        except Exception as e:
            logger.error(f"获取挖矿难度失败: {e}")
            return 0.0
    
    def get_block_count(self) -> int:
        """获取区块高度"""
        try:
            block_count = self._make_request('getblockcount')
            return int(block_count)
        except Exception as e:
            logger.error(f"获取区块高度失败: {e}")
            return 0
    
    def get_block_hash(self, height: int) -> str:
        """获取指定高度的区块哈希"""
        try:
            block_hash = self._make_request('getblockhash', [height])
            return str(block_hash)
        except Exception as e:
            logger.error(f"获取区块哈希失败: {e}")
            return ""
    
    def get_block(self, block_hash: str, verbosity: int = 1) -> Dict:
        """获取区块信息"""
        try:
            block = self._make_request('getblock', [block_hash, verbosity])
            return block
        except Exception as e:
            logger.error(f"获取区块信息失败: {e}")
            return {}
    
    def get_mempool_info(self) -> Dict:
        """获取内存池信息"""
        try:
            mempool_info = self._make_request('getmempoolinfo')
            return mempool_info
        except Exception as e:
            logger.error(f"获取内存池信息失败: {e}")
            return {}
    
    def get_mining_info(self) -> Dict:
        """获取挖矿信息"""
        try:
            mining_info = self._make_request('getmininginfo')
            return mining_info
        except Exception as e:
            logger.error(f"获取挖矿信息失败: {e}")
            logger.info("RPC挖矿信息API受限，将使用备用数据源")
            return {}
    
    def get_network_info(self) -> Dict:
        """获取网络信息"""
        try:
            network_info = self._make_request('getnetworkinfo')
            return network_info
        except Exception as e:
            logger.error(f"获取网络信息失败: {e}")
            return {}
    
    def estimate_smart_fee(self, conf_target: int = 6) -> Dict:
        """估算交易费用"""
        try:
            fee_estimate = self._make_request('estimatesmartfee', [conf_target])
            return fee_estimate
        except Exception as e:
            logger.error(f"估算交易费用失败: {e}")
            return {}
    
    def get_comprehensive_stats(self) -> Dict:
        """获取综合统计数据"""
        try:
            stats = {}
            
            # 获取基本信息
            blockchain_info = self.get_blockchain_info()
            if blockchain_info:
                stats.update({
                    'blocks': blockchain_info.get('blocks', 0),
                    'difficulty': blockchain_info.get('difficulty', 0),
                    'chain': blockchain_info.get('chain', 'unknown'),
                    'verification_progress': blockchain_info.get('verificationprogress', 0)
                })
            
            # 获取网络算力
            hashrate = self.get_network_hashps()
            if hashrate > 0:
                stats['network_hashrate_eh'] = hashrate
            
            # 获取内存池信息
            mempool_info = self.get_mempool_info()
            if mempool_info:
                stats.update({
                    'mempool_size': mempool_info.get('size', 0),
                    'mempool_bytes': mempool_info.get('bytes', 0),
                    'mempool_usage': mempool_info.get('usage', 0)
                })
            
            # 获取费用估算
            fee_estimate = self.estimate_smart_fee()
            if fee_estimate and 'feerate' in fee_estimate:
                stats['fee_rate_btc_kb'] = fee_estimate['feerate']
            
            stats['timestamp'] = datetime.now().isoformat()
            stats['source'] = 'bitcoin_rpc'
            
            return stats
            
        except Exception as e:
            logger.error(f"获取综合统计失败: {e}")
            return {}
    
    def test_connection(self) -> bool:
        """测试RPC连接"""
        try:
            info = self.get_blockchain_info()
            return bool(info)
        except Exception as e:
            logger.error(f"RPC连接测试失败: {e}")
            return False
    
    def is_rpc_available(self) -> bool:
        """检查RPC是否可用"""
        return self.test_connection()
    
    def get_comprehensive_mining_data(self) -> Optional[Dict]:
        """获取综合挖矿数据"""
        try:
            stats = self.get_comprehensive_stats()
            if not stats:
                return None
            
            # 添加一些额外的挖矿数据
            mining_info = self.get_mining_info()
            
            result = {
                'current_block_height': stats.get('blocks', 0),
                'difficulty': stats.get('difficulty', 0),
                'network_hashrate_eh': stats.get('network_hashrate_eh', 0),
                'mempool_size': stats.get('mempool_size', 0),
                'median_time': mining_info.get('mediantime', int(time.time())),
                'blocks_until_difficulty_adjustment': mining_info.get('blocks', 0) % 2016,
                'source': 'bitcoin_rpc',
                'timestamp': stats.get('timestamp', datetime.now().isoformat())
            }
            
            return result
            
        except Exception as e:
            logger.error(f"获取综合挖矿数据失败: {e}")
            return None

# 全局RPC客户端实例
bitcoin_rpc = BitcoinRPCClient()

def get_bitcoin_stats() -> Dict:
    """便捷的Bitcoin统计获取函数"""
    return bitcoin_rpc.get_comprehensive_stats()

def test_rpc_connection() -> bool:
    """便捷的RPC连接测试函数"""
    return bitcoin_rpc.test_connection()

# 兼容性导出
__all__ = ['BitcoinRPCClient', 'bitcoin_rpc', 'get_bitcoin_stats', 'test_rpc_connection']