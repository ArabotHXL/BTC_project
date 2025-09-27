"""
区块链数据验证和IPFS存储服务
为Web3集成模块提供透明度证明能力

技术栈：
- Base L2网络 (低gas费用，机构友好)
- IPFS + Pinata服务
- Web3.py 用于智能合约交互
- 加密存储保护数据隐私
"""

import os
import json
import hashlib
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import requests
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

from web3 import Web3
from eth_account import Account

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BlockchainIntegration:
    """区块链集成主类"""
    
    def __init__(self):
        """初始化区块链集成组件"""
        self.w3 = None
        self.contract = None
        self.account = None
        self.encryption_key = None
        self.pinata_jwt = None
        self.pinata_api_url = "https://api.pinata.cloud"
        
        # 🔧 CRITICAL FIX: 默认使用测试网，只有明确启用主网时才使用主网
        self._initialize_network_config()
        
        # 智能合约信息 (部署后需要更新)
        self.contract_address = os.environ.get('MINING_REGISTRY_CONTRACT_ADDRESS')
        self.contract_abi = self._load_contract_abi()
        
        self._initialize_web3()
        self._initialize_encryption()
        self._initialize_pinata()
    
    def _initialize_network_config(self):
        """
        初始化网络配置 - 安全优先方法
        
        🔧 CRITICAL FIX: 默认使用测试网，防止意外的主网写入
        """
        try:
            # 🔒 SECURITY: 检查是否明确启用主网写入
            mainnet_writes_enabled = os.environ.get('BLOCKCHAIN_ENABLE_MAINNET_WRITES', '').lower() == 'true'
            
            if mainnet_writes_enabled:
                # 主网写入已启用，验证所有必需的安全配置
                required_mainnet_vars = [
                    'BLOCKCHAIN_PRIVATE_KEY',
                    'MINING_REGISTRY_CONTRACT_ADDRESS',
                    'ENCRYPTION_PASSWORD',
                    'ENCRYPTION_SALT',
                    'PINATA_JWT'
                ]
                
                missing_vars = [var for var in required_mainnet_vars if not os.environ.get(var)]
                
                if missing_vars:
                    raise ValueError(
                        f"主网写入已启用但缺少必需的安全配置：{', '.join(missing_vars)}\n"
                        "主网模式需要所有安全配置完整。请设置所有必需的环境变量。"
                    )
                
                self.base_rpc_url = "https://mainnet.base.org"  # Base L2 主网RPC
                self.is_mainnet_mode = True
                logger.warning("🚨 主网写入模式已启用 - 将连接到Base L2主网")
                
            else:
                # 🔧 CRITICAL FIX: 默认使用Base Sepolia测试网 - 安全模式
                self.base_rpc_url = "https://sepolia.base.org"  # Base Sepolia测试网RPC
                self.is_mainnet_mode = False
                logger.info("🛡️ 默认安全模式：使用Base Sepolia测试网")
                
                # 在测试网模式下，允许部分配置缺失（用于开发测试）
                if not os.environ.get('BLOCKCHAIN_PRIVATE_KEY'):
                    logger.warning("⚠️ 测试网模式：BLOCKCHAIN_PRIVATE_KEY未设置，区块链功能将受限")
                
        except Exception as e:
            logger.error(f"网络配置初始化失败: {e}")
            # 🔧 CRITICAL FIX: 在配置失败时，强制使用最安全的Base Sepolia设置
            self.base_rpc_url = "https://sepolia.base.org"
            self.is_mainnet_mode = False
            logger.info("🛡️ 配置失败，强制使用安全的Base Sepolia测试网模式")
            raise
    
    def _initialize_web3(self):
        """初始化Web3连接到Base L2"""
        try:
            # 初始化Web3连接
            self.w3 = Web3(Web3.HTTPProvider(self.base_rpc_url))
            
            if not self.w3.is_connected():
                logger.error("无法连接到Base L2网络")
                return
            
            # 加载私钥
            private_key = os.environ.get('BLOCKCHAIN_PRIVATE_KEY')
            if private_key:
                self.account = Account.from_key(private_key)
                logger.info(f"区块链账户已加载: {self.account.address}")
            
            # 初始化合约实例
            if self.contract_address and self.contract_abi:
                self.contract = self.w3.eth.contract(
                    address=self.contract_address,
                    abi=self.contract_abi
                )
                logger.info("智能合约实例已初始化")
            
            logger.info("Web3连接已建立到Base L2网络")
            
        except Exception as e:
            logger.error(f"Web3初始化失败: {e}")
    
    def _initialize_encryption(self):
        """初始化数据加密 - 支持开发/测试环境的灵活配置"""
        try:
            password = os.environ.get('ENCRYPTION_PASSWORD')
            salt = os.environ.get('ENCRYPTION_SALT')
            
            # 🔧 CRITICAL FIX: 根据环境提供不同的安全策略
            if self.is_mainnet_mode:
                # 主网模式：严格验证所有安全配置
                if not password:
                    raise ValueError(
                        "主网模式下ENCRYPTION_PASSWORD环境变量必须设置。"
                        "请设置强密码（建议32位以上随机字符串）"
                    )
                
                if not salt:
                    raise ValueError(
                        "主网模式下ENCRYPTION_SALT环境变量必须设置。"
                        "请设置唯一盐值（建议16位以上随机字符串）"
                    )
                
                # 验证密码强度
                if len(password) < 16:
                    raise ValueError("主网模式下ENCRYPTION_PASSWORD长度至少16个字符")
                
                if len(salt) < 8:
                    raise ValueError("主网模式下ENCRYPTION_SALT长度至少8个字符")
                    
                logger.info("🔒 主网模式：使用生产级加密配置")
            else:
                # 🔧 开发/测试模式：使用安全默认值
                if not password:
                    password = "dev_encryption_password_32_chars_long_secure"
                    logger.warning("⚠️ 开发模式：使用默认加密密码（仅限开发/测试）")
                
                if not salt:
                    salt = "dev_salt_16chars"
                    logger.warning("⚠️ 开发模式：使用默认加密盐值（仅限开发/测试）")
                    
                logger.info("🛡️ 开发/测试模式：使用安全默认值")
            
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt.encode(),
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
            self.encryption_key = Fernet(key)
            
            logger.info("数据加密已初始化")
            
        except ValueError as e:
            logger.error(f"加密配置错误: {e}")
            raise
        except Exception as e:
            logger.error(f"加密初始化失败: {e}")
            raise
    
    def _initialize_pinata(self):
        """初始化Pinata IPFS客户端 - 支持开发/测试环境的灵活配置"""
        try:
            self.pinata_jwt = os.environ.get('PINATA_JWT')
            
            # 检查是否明确禁用IPFS
            if os.environ.get('BLOCKCHAIN_DISABLE_IPFS', '').lower() == 'true':
                logger.warning("IPFS功能已禁用 (BLOCKCHAIN_DISABLE_IPFS=true)")
                self.pinata_jwt = None
                return
            
            # 🔧 CRITICAL FIX: 根据环境提供不同的IPFS策略
            if self.is_mainnet_mode:
                # 主网模式：严格验证Pinata JWT
                if not self.pinata_jwt:
                    raise ValueError(
                        "主网模式下PINATA_JWT环境变量必须设置。区块链透明度功能需要IPFS存储。"
                        "请从Pinata.cloud获取JWT令牌并设置环境变量。"
                    )
                
                # 验证JWT格式
                if not self.pinata_jwt.startswith('eyJ'):
                    raise ValueError("主网模式下PINATA_JWT格式不正确，请确认是有效的JWT令牌")
                
                # 测试Pinata连接
                headers = {
                    'Authorization': f'Bearer {self.pinata_jwt}',
                    'Content-Type': 'application/json'
                }
                
                try:
                    response = requests.get(
                        f"{self.pinata_api_url}/data/testAuthentication", 
                        headers=headers, 
                        timeout=10
                    )
                    
                    if response.status_code == 200:
                        logger.info("🔒 主网模式：Pinata IPFS连接已建立并验证")
                    elif response.status_code == 401:
                        raise ValueError("Pinata JWT令牌无效或已过期，请更新PINATA_JWT环境变量")
                    else:
                        raise ValueError(f"Pinata连接失败: HTTP {response.status_code}")
                        
                except requests.exceptions.RequestException as e:
                    raise ValueError(f"无法连接到Pinata服务: {e}")
            else:
                # 🔧 开发/测试模式：允许没有IPFS功能正常启动
                if not self.pinata_jwt:
                    logger.warning("⚠️ 开发/测试模式：PINATA_JWT未设置，IPFS功能将受限（仅影响数据上传到IPFS）")
                    self.pinata_jwt = None
                    return
                
                # 如果设置了JWT，尝试验证但不要求严格通过
                try:
                    headers = {
                        'Authorization': f'Bearer {self.pinata_jwt}',
                        'Content-Type': 'application/json'
                    }
                    
                    response = requests.get(
                        f"{self.pinata_api_url}/data/testAuthentication", 
                        headers=headers, 
                        timeout=5
                    )
                    
                    if response.status_code == 200:
                        logger.info("🛡️ 开发/测试模式：Pinata IPFS连接已验证")
                    else:
                        logger.warning(f"⚠️ 开发/测试模式：Pinata连接失败 (HTTP {response.status_code})，但允许继续启动")
                        self.pinata_jwt = None
                        
                except requests.exceptions.RequestException as e:
                    logger.warning(f"⚠️ 开发/测试模式：无法连接到Pinata服务 ({e})，但允许继续启动")
                    self.pinata_jwt = None
                
        except ValueError as e:
            # 主网模式下的配置错误需要抛出异常
            if self.is_mainnet_mode:
                logger.error(f"主网模式Pinata配置错误: {e}")
                raise
            else:
                # 开发/测试模式下降级处理
                logger.warning(f"开发/测试模式Pinata配置警告: {e}")
                self.pinata_jwt = None
        except Exception as e:
            logger.error(f"Pinata初始化失败: {e}")
            if self.is_mainnet_mode:
                raise
            else:
                logger.warning("开发/测试模式：Pinata初始化失败，但允许继续启动")
                self.pinata_jwt = None
    
    def _load_contract_abi(self) -> List[Dict]:
        """加载智能合约ABI - 完整匹配MiningDataRegistry.sol"""
        return [
            # Events
            {
                "anonymous": False,
                "inputs": [
                    {"indexed": True, "name": "dataHash", "type": "bytes32"},
                    {"indexed": True, "name": "siteId", "type": "string"},
                    {"indexed": True, "name": "timestamp", "type": "uint256"},
                    {"indexed": False, "name": "ipfsCid", "type": "string"},
                    {"indexed": False, "name": "registrar", "type": "address"}
                ],
                "name": "DataRegistered",
                "type": "event"
            },
            {
                "anonymous": False,
                "inputs": [
                    {"indexed": True, "name": "dataHash", "type": "bytes32"},
                    {"indexed": True, "name": "siteId", "type": "string"},
                    {"indexed": False, "name": "verifier", "type": "address"},
                    {"indexed": False, "name": "isValid", "type": "bool"}
                ],
                "name": "DataVerified",
                "type": "event"
            },
            # Constructor
            {
                "inputs": [],
                "stateMutability": "nonpayable",
                "type": "constructor"
            },
            # Main Functions
            {
                "inputs": [
                    {"name": "_dataHash", "type": "bytes32"},
                    {"name": "_siteId", "type": "string"},
                    {"name": "_ipfsCid", "type": "string"}
                ],
                "name": "registerMiningData",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [{"name": "_dataHash", "type": "bytes32"}],
                "name": "verifyData",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [{"name": "_dataHash", "type": "bytes32"}],
                "name": "getRecord",
                "outputs": [
                    {
                        "components": [
                            {"name": "dataHash", "type": "bytes32"},
                            {"name": "siteId", "type": "string"},
                            {"name": "timestamp", "type": "uint256"},
                            {"name": "ipfsCid", "type": "string"},
                            {"name": "registrar", "type": "address"},
                            {"name": "blockNumber", "type": "uint256"},
                            {"name": "isVerified", "type": "bool"},
                            {"name": "verificationCount", "type": "uint256"}
                        ],
                        "name": "",
                        "type": "tuple"
                    }
                ],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [{"name": "_siteId", "type": "string"}],
                "name": "getSiteRecords",
                "outputs": [{"name": "", "type": "bytes32[]"}],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [{"name": "_registrar", "type": "address"}],
                "name": "getRegistrarRecords",
                "outputs": [{"name": "", "type": "bytes32[]"}],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [
                    {"name": "_siteId", "type": "string"},
                    {"name": "_count", "type": "uint256"}
                ],
                "name": "getLatestSiteRecords",
                "outputs": [{"name": "", "type": "bytes32[]"}],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [{"name": "_dataHash", "type": "bytes32"}],
                "name": "checkDataStatus",
                "outputs": [
                    {"name": "exists", "type": "bool"},
                    {"name": "verified", "type": "bool"}
                ],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [
                    {"name": "_dataHashes", "type": "bytes32[]"},
                    {"name": "_siteIds", "type": "string[]"},
                    {"name": "_ipfsCids", "type": "string[]"}
                ],
                "name": "batchRegisterMiningData",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            # Access Control Functions
            {
                "inputs": [{"name": "_registrar", "type": "address"}],
                "name": "addAuthorizedRegistrar",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [{"name": "_registrar", "type": "address"}],
                "name": "removeAuthorizedRegistrar",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [{"name": "_newOwner", "type": "address"}],
                "name": "transferOwnership",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            # Utility Functions
            {
                "inputs": [],
                "name": "getContractStats",
                "outputs": [
                    {"name": "", "type": "uint256"},
                    {"name": "", "type": "uint256"}
                ],
                "stateMutability": "view",
                "type": "function"
            },
            # Public State Variables
            {
                "inputs": [],
                "name": "owner",
                "outputs": [{"name": "", "type": "address"}],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [],
                "name": "totalRecords",
                "outputs": [{"name": "", "type": "uint256"}],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [],
                "name": "MAX_RECORDS_PER_SITE",
                "outputs": [{"name": "", "type": "uint256"}],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [{"name": "", "type": "address"}],
                "name": "authorizedRegistrars",
                "outputs": [{"name": "", "type": "bool"}],
                "stateMutability": "view",
                "type": "function"
            }
        ]
    
    def standardize_mining_data(self, mining_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        标准化挖矿数据格式
        
        Args:
            mining_data: 原始挖矿数据
            
        Returns:
            标准化后的数据字典
        """
        try:
            # 标准化数据结构
            standardized = {
                "version": "1.0",
                "timestamp": mining_data.get("timestamp", datetime.utcnow().isoformat()),
                "site_id": mining_data.get("site_id", "default_site"),
                "mining_metrics": {
                    "hashrate_th": float(mining_data.get("hashrate", 0)),
                    "power_consumption_w": float(mining_data.get("power_consumption", 0)),
                    "efficiency_wth": float(mining_data.get("efficiency", 0)),
                    "daily_btc_production": float(mining_data.get("daily_btc", 0)),
                    "daily_revenue_usd": float(mining_data.get("daily_revenue", 0)),
                    "daily_profit_usd": float(mining_data.get("daily_profit", 0))
                },
                "network_data": {
                    "btc_price_usd": float(mining_data.get("btc_price", 0)),
                    "network_hashrate_eh": float(mining_data.get("network_hashrate", 0)),
                    "network_difficulty": float(mining_data.get("network_difficulty", 0)),
                    "block_reward": float(mining_data.get("block_reward", 3.125))
                },
                "operational_data": {
                    "electricity_cost_kwh": float(mining_data.get("electricity_cost", 0.06)),
                    "pool_fee_rate": float(mining_data.get("pool_fee", 0.025)),
                    "miner_model": mining_data.get("miner_model", "Unknown"),
                    "miner_count": int(mining_data.get("miner_count", 1))
                },
                "metadata": {
                    "calculation_method": mining_data.get("calculation_method", "standard"),
                    "data_source": mining_data.get("data_source", "internal"),
                    "recorded_by": mining_data.get("recorded_by", "system"),
                    "verification_level": mining_data.get("verification_level", "basic")
                }
            }
            
            # 添加数据完整性检查
            standardized["data_integrity"] = {
                "checksum": self._calculate_data_checksum(standardized["mining_metrics"]),
                "field_count": len(standardized),
                "required_fields_present": self._check_required_fields(standardized)
            }
            
            logger.info(f"数据标准化完成，站点ID: {standardized['site_id']}")
            return standardized
            
        except Exception as e:
            logger.error(f"数据标准化失败: {e}")
            raise
    
    def calculate_data_hash(self, data: Dict[str, Any]) -> str:
        """
        计算数据的Keccak256哈希值
        
        Args:
            data: 要哈希的数据
            
        Returns:
            十六进制哈希字符串
        """
        try:
            # 将数据转换为规范化的JSON字符串
            data_str = json.dumps(data, sort_keys=True, separators=(',', ':'))
            
            # 计算Keccak256哈希 (与以太坊兼容)
            data_bytes = data_str.encode('utf-8')
            hash_object = Web3.keccak(data_bytes)
            
            return hash_object.hex()
            
        except Exception as e:
            logger.error(f"数据哈希计算失败: {e}")
            raise
    
    def encrypt_data(self, data: Dict[str, Any]) -> bytes:
        """
        加密敏感数据
        
        Args:
            data: 要加密的数据
            
        Returns:
            加密后的字节数据
        """
        try:
            if not self.encryption_key:
                raise ValueError("加密密钥未初始化")
            
            data_str = json.dumps(data)
            encrypted_data = self.encryption_key.encrypt(data_str.encode())
            
            logger.info("数据加密完成")
            return encrypted_data
            
        except Exception as e:
            logger.error(f"数据加密失败: {e}")
            raise
    
    def decrypt_data(self, encrypted_data: bytes) -> Dict[str, Any]:
        """
        解密数据
        
        Args:
            encrypted_data: 加密的数据
            
        Returns:
            解密后的数据字典
        """
        try:
            if not self.encryption_key:
                raise ValueError("加密密钥未初始化")
            
            decrypted_bytes = self.encryption_key.decrypt(encrypted_data)
            data_str = decrypted_bytes.decode()
            
            return json.loads(data_str)
            
        except Exception as e:
            logger.error(f"数据解密失败: {e}")
            raise
    
    def upload_to_ipfs(self, data: Dict[str, Any], encrypt: bool = True) -> str:
        """
        上传数据到IPFS (通过Pinata)
        
        Args:
            data: 要上传的数据
            encrypt: 是否加密数据
            
        Returns:
            IPFS CID
        """
        try:
            if not self.pinata_jwt:
                raise ValueError("Pinata JWT未配置")
            
            # 准备数据
            if encrypt:
                # 分离敏感数据和公开数据
                public_data = self._extract_public_data(data)
                sensitive_data = self._extract_sensitive_data(data)
                
                upload_data = {
                    "public": public_data,
                    "encrypted": base64.b64encode(self.encrypt_data(sensitive_data)).decode(),
                    "metadata": {
                        "encrypted": True,
                        "upload_time": datetime.utcnow().isoformat(),
                        "data_type": "mining_audit_package"
                    }
                }
            else:
                upload_data = data
            
            # 上传到Pinata
            headers = {
                'Authorization': f'Bearer {self.pinata_jwt}',
                'Content-Type': 'application/json'
            }
            
            pinata_data = {
                'pinataContent': upload_data,
                'pinataOptions': {
                    'cidVersion': 1,
                },
                'pinataMetadata': {
                    'name': f"mining_data_{int(time.time())}",
                    'keyvalues': {
                        'site_id': data.get('site_id', 'unknown'),
                        'data_type': 'mining_verification',
                        'timestamp': str(int(time.time()))
                    }
                }
            }
            
            response = requests.post(
                f"{self.pinata_api_url}/pinning/pinJSONToIPFS",
                headers=headers,
                json=pinata_data,
                timeout=30
            )
            
            if response.status_code == 200:
                ipfs_hash = response.json()['IpfsHash']
                logger.info(f"数据已上传到IPFS: {ipfs_hash}")
                return ipfs_hash
            else:
                raise Exception(f"IPFS上传失败: {response.status_code} - {response.text}")
                
        except Exception as e:
            logger.error(f"IPFS上传失败: {e}")
            raise
    
    def _extract_public_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """提取公开数据"""
        public_fields = [
            "version", "timestamp", "site_id",
            "network_data", "metadata"
        ]
        
        return {k: v for k, v in data.items() if k in public_fields}
    
    def _extract_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """提取敏感数据"""
        sensitive_fields = [
            "mining_metrics", "operational_data"
        ]
        
        return {k: v for k, v in data.items() if k in sensitive_fields}
    
    def _calculate_data_checksum(self, data: Dict[str, Any]) -> str:
        """计算数据校验和"""
        data_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(data_str.encode()).hexdigest()
    
    def _check_required_fields(self, data: Dict[str, Any]) -> bool:
        """检查必需字段是否存在"""
        required_fields = ["version", "timestamp", "site_id", "mining_metrics"]
        return all(field in data for field in required_fields)

# 全局实例
blockchain_integration = BlockchainIntegration()

# 导出
__all__ = ['BlockchainIntegration', 'blockchain_integration']