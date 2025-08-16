"""
Bitcoin RPC 客户端 - 获取链上实时数据
通过本地Bitcoin节点获取准确的区块链信息
"""
import requests
import json
import logging
from datetime import datetime
from typing import Dict, Optional
import os

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BitcoinRPCClient:
    """Bitcoin RPC客户端 - 连接本地或远程Bitcoin节点"""

    def __init__(self, 
                 rpc_host="127.0.0.1", 
                 rpc_port=8332, 
                 rpc_user=None, 
                 rpc_password=None,
                 rpc_url=None):
        """
        初始化RPC客户端

        Args:
            rpc_host: Bitcoin节点主机地址
            rpc_port: RPC端口 (主网:8332, 测试网:18332)
            rpc_user: RPC用户名
            rpc_password: RPC密码
            rpc_url: 直接指定RPC URL (如Ankr等云服务)
        """
        # 优先使用Ankr免费RPC服务
        self.ankr_url = "https://rpc.ankr.com/btc/3c1e57e178ff7195c7fc9c6d31b8d21d58fca3b0960067febe0026b2348d5f45"

        if rpc_url:
            self.rpc_url = rpc_url
            self.use_ankr = False
        elif os.environ.get('BITCOIN_RPC_URL'):
            self.rpc_url = os.environ.get('BITCOIN_RPC_URL')
            self.use_ankr = False
        else:
            # 默认使用Ankr免费服务
            self.rpc_url = self.ankr_url
            self.use_ankr = True

        self.rpc_host = rpc_host
        self.rpc_port = rpc_port
        self.rpc_user = rpc_user or os.environ.get('BITCOIN_RPC_USER')
        self.rpc_password = rpc_password or os.environ.get('BITCOIN_RPC_PASSWORD')

        # 如果使用本地节点才需要用户名密码
        if not self.use_ankr and (not self.rpc_url.startswith('http')):
            self.rpc_url = f"http://{rpc_host}:{rpc_port}/"
            if not self.rpc_user or not self.rpc_password:
                logger.warning("本地Bitcoin RPC凭据未配置，将尝试使用Ankr服务")
                self.rpc_url = self.ankr_url
                self.use_ankr = True

    def make_rpc_call(self, method: str, params: list = None) -> Optional[Dict]:
        """
        执行RPC调用

        Args:
            method: RPC方法名
            params: 参数列表

        Returns:
            RPC响应数据或None
        """
        payload = {
            "jsonrpc": "2.0",
            "id": "mining_calculator",
            "method": method,
            "params": params or []
        }

        try:
            headers = {'content-type': 'application/json'}

            # 根据是否使用Ankr服务选择不同的请求方式
            if self.use_ankr or self.rpc_url.startswith('https://rpc.ankr.com'):
                # Ankr服务不需要认证
                response = requests.post(
                    self.rpc_url,
                    data=json.dumps(payload),
                    headers=headers,
                    timeout=30
                )
            else:
                # 本地或其他需要认证的服务
                if not self.rpc_user or not self.rpc_password:
                    logger.error("本地Bitcoin RPC凭据未配置")
                    return None

                response = requests.post(
                    self.rpc_url,
                    data=json.dumps(payload),
                    headers=headers,
                    auth=(self.rpc_user, self.rpc_password),
                    timeout=30
                )

            response.raise_for_status()

            result = response.json()
            if 'error' in result and result['error']:
                logger.error(f"RPC错误: {result['error']}")
                return None

            return result.get('result')

        except requests.exceptions.RequestException as e:
            logger.error(f"RPC请求失败: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"RPC响应解析失败: {e}")
            return None

    def get_blockchain_info(self) -> Optional[Dict]:
        """
        获取区块链信息 - 核心方法

        Returns:
            包含以下关键信息的字典:
            - chain: 网络类型 (main/test/regtest)
            - blocks: 当前区块高度
            - difficulty: 当前挖矿难度
            - mediantime: 中位时间
            - chainwork: 总工作量
            - verificationprogress: 同步进度
        """
        return self.make_rpc_call("getblockchaininfo")

    def get_mining_info(self) -> Optional[Dict]:
        """获取挖矿相关信息"""
        return self.make_rpc_call("getmininginfo")

    def get_network_hashps(self, blocks: int = 120) -> Optional[float]:
        """
        获取网络算力 (基于最近N个区块)
        注意: Ankr免费服务不支持此方法，会返回None
        此方法也可能因RPC服务限制而失败。

        Args:
            blocks: 计算算力的区块数量 (默认120个区块)

        Returns:
            网络算力 (H/s) 或 None
        """
        try:
            result = self.make_rpc_call("getnetworkhashps", [blocks])
            if result is None and self.use_ankr:
                logger.debug("Ankr服务不支持网络算力查询，这是正常的限制")
                return None
            # Explicitly handle the restricted method error
            if isinstance(result, dict) and 'error' in result and result['error']:
                error_msg = str(result['error'])
                if "Method disabled" in error_msg or "restricted by blockchain schema" in error_msg:
                    logger.error(f"RPC method restricted: {result['error']['message']}")
                    return None
            
            return float(result) if result is not None else None
        except Exception as e:
            error_msg = str(e)
            if "Method disabled" in error_msg or "restricted by blockchain schema" in error_msg:
                logger.warning(f"RPC method restricted, using fallback: {e}")
                return None
            else:
                logger.error(f"RPC错误: {e}")
                return None

    def get_block_count(self) -> Optional[int]:
        """获取当前区块数量"""
        result = self.make_rpc_call("getblockcount")
        return int(result) if result else None

    def get_difficulty(self) -> Optional[float]:
        """获取当前挖矿难度"""
        result = self.make_rpc_call("getdifficulty")
        return float(result) if result else None

    def get_comprehensive_mining_data(self) -> Dict:
        """
        获取综合挖矿数据 - 整合多个RPC调用

        Returns:
            综合挖矿数据字典
        """
        blockchain_info = self.get_blockchain_info()
        mining_info = self.get_mining_info()
        network_hashrate = self.get_network_hashps(120)  # 基于最近120个区块

        if not blockchain_info:
            logger.warning("无法获取区块链信息，可能是RPC连接问题")
            return {}

        # 计算下次难度调整预估
        blocks_until_adjustment = 2016 - (blockchain_info.get('blocks', 0) % 2016)

        # 估算到下次调整的时间 (假设10分钟一个区块)
        time_to_adjustment_hours = (blocks_until_adjustment * 10) / 60

        # 确定数据源标识
        source_name = 'ankr_rpc' if self.use_ankr else 'bitcoin_rpc'

        comprehensive_data = {
            'timestamp': datetime.now().isoformat(),
            'source': source_name,

            # 基础网络信息
            'network': blockchain_info.get('chain', 'unknown'),
            'current_block_height': blockchain_info.get('blocks', 0),
            'sync_progress': blockchain_info.get('verificationprogress', 0) * 100,

            # 挖矿核心数据
            'difficulty': blockchain_info.get('difficulty', 0),
            'network_hashrate_hs': network_hashrate,
            'network_hashrate_eh': network_hashrate / 1e18 if network_hashrate else None,

            # 时间相关
            'median_time': blockchain_info.get('mediantime', 0),
            'blocks_until_difficulty_adjustment': blocks_until_adjustment,
            'estimated_hours_to_difficulty_adjustment': time_to_adjustment_hours,

            # 网络状态
            'total_work': blockchain_info.get('chainwork', ''),
            'warnings': blockchain_info.get('warnings', ''),

            # 挖矿额外信息
            'mining_info': mining_info if mining_info else {}
        }

        logger.info(f"RPC数据获取成功: 区块{comprehensive_data['current_block_height']}, "
                   f"难度{comprehensive_data['difficulty']:.2e}, "
                   f"算力{comprehensive_data['network_hashrate_eh']:.2f}EH/s")

        return comprehensive_data

    def is_rpc_available(self) -> bool:
        """检查RPC服务是否可用"""
        try:
            result = self.get_block_count()
            if result is not None:
                logger.info(f"Bitcoin RPC连接成功 - 当前区块: {result}")
                return True
            return False
        except Exception as e:
            logger.debug(f"RPC连接检查失败: {e}")
            return False

# 示例用法和测试函数
def test_bitcoin_rpc():
    """测试Bitcoin RPC连接和数据获取"""
    client = BitcoinRPCClient()

    if not client.is_rpc_available():
        logger.info("Bitcoin RPC不可用 - 需要配置本地Bitcoin节点")
        return None

    # 获取综合数据
    data = client.get_comprehensive_mining_data()

    if data:
        print(f"网络: {data['network']}")
        print(f"当前区块: {data['current_block_height']}")
        print(f"难度: {data['difficulty']:.2e}")
        print(f"算力: {data['network_hashrate_eh']:.2f} EH/s")
        print(f"下次调整还需: {data['blocks_until_difficulty_adjustment']} 个区块")
        print(f"预计时间: {data['estimated_hours_to_difficulty_adjustment']:.1f} 小时")

    return data

if __name__ == "__main__":
    test_bitcoin_rpc()