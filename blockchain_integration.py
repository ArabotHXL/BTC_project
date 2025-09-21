"""
区块链数据验证和IPFS存储模块
为BTC Mining Calculator平台提供透明度证明能力

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
from flask import current_app

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
        self.base_rpc_url = "https://mainnet.base.org"  # Base L2 主网RPC
        
        # 智能合约信息 (部署后需要更新)
        self.contract_address = os.environ.get('MINING_REGISTRY_CONTRACT_ADDRESS')
        self.contract_abi = self._load_contract_abi()
        
        self._initialize_web3()
        self._initialize_encryption()
        self._initialize_pinata()
    
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
        """初始化数据加密 - 生产安全版本"""
        try:
            # SECURITY FIX: 生产环境必须设置加密密码和盐值
            password = os.environ.get('ENCRYPTION_PASSWORD')
            salt = os.environ.get('ENCRYPTION_SALT')
            
            if not password:
                raise ValueError(
                    "ENCRYPTION_PASSWORD环境变量必须设置。生产环境不允许使用默认密码。"
                    "请设置强密码（建议32位以上随机字符串）"
                )
            
            if not salt:
                raise ValueError(
                    "ENCRYPTION_SALT环境变量必须设置。生产环境不允许使用默认盐值。"
                    "请设置唯一盐值（建议16位以上随机字符串）"
                )
            
            # 验证密码强度
            if len(password) < 16:
                raise ValueError("ENCRYPTION_PASSWORD长度至少16个字符")
            
            if len(salt) < 8:
                raise ValueError("ENCRYPTION_SALT长度至少8个字符")
            
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt.encode(),
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
            self.encryption_key = Fernet(key)
            
            logger.info("数据加密已初始化（使用强加密配置）")
            
        except ValueError as e:
            logger.error(f"加密配置错误: {e}")
            raise
        except Exception as e:
            logger.error(f"加密初始化失败: {e}")
            raise
    
    def _initialize_pinata(self):
        """初始化Pinata IPFS客户端 - 生产安全版本"""
        try:
            self.pinata_jwt = os.environ.get('PINATA_JWT')
            
            # SECURITY FIX: 生产环境不允许静默降级，必须提供JWT
            if not self.pinata_jwt:
                raise ValueError(
                    "PINATA_JWT环境变量必须设置。区块链透明度功能需要IPFS存储。"
                    "请从Pinata.cloud获取JWT令牌并设置环境变量。"
                    "如果确实不需要IPFS功能，请设置BLOCKCHAIN_DISABLE_IPFS=true"
                )
            
            # 验证JWT格式
            if not self.pinata_jwt.startswith('eyJ'):
                logger.warning("PINATA_JWT格式可能不正确，请确认是有效的JWT令牌")
            
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
                    logger.info("Pinata IPFS连接已建立并验证")
                elif response.status_code == 401:
                    raise ValueError("Pinata JWT令牌无效或已过期，请更新PINATA_JWT环境变量")
                else:
                    raise ValueError(f"Pinata连接失败: HTTP {response.status_code}")
                    
            except requests.exceptions.RequestException as e:
                raise ValueError(f"无法连接到Pinata服务: {e}")
                
        except ValueError as e:
            logger.error(f"Pinata配置错误: {e}")
            # 检查是否明确禁用IPFS
            if os.environ.get('BLOCKCHAIN_DISABLE_IPFS', '').lower() == 'true':
                logger.warning("IPFS功能已禁用 (BLOCKCHAIN_DISABLE_IPFS=true)")
                self.pinata_jwt = None
                return
            else:
                raise
        except Exception as e:
            logger.error(f"Pinata初始化失败: {e}")
            raise
    
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
                        'timestamp': data.get('timestamp', ''),
                        'type': 'mining_verification_data'
                    }
                }
            }
            
            response = requests.post(
                f"{self.pinata_api_url}/pinning/pinJSONToIPFS",
                headers=headers,
                json=pinata_data
            )
            
            if response.status_code == 200:
                result = response.json()
                ipfs_cid = result['IpfsHash']
                logger.info(f"数据已上传到IPFS，CID: {ipfs_cid}")
                return ipfs_cid
            else:
                raise Exception(f"IPFS上传失败: {response.status_code} - {response.text}")
                
        except Exception as e:
            logger.error(f"IPFS上传失败: {e}")
            raise
    
    def retrieve_from_ipfs(self, cid: str, decrypt: bool = True) -> Dict[str, Any]:
        """
        从IPFS检索数据
        
        Args:
            cid: IPFS内容标识符
            decrypt: 是否解密数据
            
        Returns:
            检索到的数据
        """
        try:
            # 从IPFS网关获取数据
            ipfs_gateway_url = f"https://gateway.pinata.cloud/ipfs/{cid}"
            response = requests.get(ipfs_gateway_url, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                if decrypt and data.get('metadata', {}).get('encrypted'):
                    # 解密敏感数据
                    encrypted_data = base64.b64decode(data['encrypted'])
                    sensitive_data = self.decrypt_data(encrypted_data)
                    
                    # 合并公开数据和解密的敏感数据
                    combined_data = {**data['public'], **sensitive_data}
                    return combined_data
                else:
                    return data
            else:
                raise Exception(f"IPFS检索失败: {response.status_code}")
                
        except Exception as e:
            logger.error(f"IPFS数据检索失败: {e}")
            raise
    
    def register_on_blockchain(self, data_hash: str, site_id: str, ipfs_cid: str) -> str:
        """
        在区块链上注册数据 - 包含主网写入保护
        
        Args:
            data_hash: 数据哈希
            site_id: 站点ID
            ipfs_cid: IPFS内容标识符
            
        Returns:
            交易哈希
        """
        try:
            if not self.contract or not self.account:
                raise ValueError("智能合约或账户未初始化")
            
            # SECURITY PROTECTION: 主网写入保护
            self._validate_mainnet_write_permissions()
            
            # 构建交易
            nonce = self.w3.eth.get_transaction_count(self.account.address)
            
            # 估算gas费用
            gas_estimate = self.contract.functions.registerMiningData(
                Web3.to_bytes(hexstr=data_hash),
                site_id,
                ipfs_cid
            ).estimate_gas({'from': self.account.address})
            
            # 构建交易
            transaction = self.contract.functions.registerMiningData(
                Web3.to_bytes(hexstr=data_hash),
                site_id,
                ipfs_cid
            ).build_transaction({
                'from': self.account.address,
                'gas': gas_estimate + 10000,  # 添加gas缓冲
                'gasPrice': self.w3.eth.gas_price,
                'nonce': nonce,
            })
            
            # 签名交易
            signed_txn = self.w3.eth.account.sign_transaction(transaction, self.account.key)
            
            # 发送交易
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            
            # 等待交易确认
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
            
            if receipt.status == 1:
                logger.info(f"区块链注册成功，交易哈希: {tx_hash.hex()}")
                return tx_hash.hex()
            else:
                raise Exception(f"交易失败，状态: {receipt.status}")
                
        except Exception as e:
            logger.error(f"区块链注册失败: {e}")
            raise
    
    def verify_on_blockchain(self, data_hash: str) -> Dict[str, Any]:
        """
        在区块链上验证数据
        
        Args:
            data_hash: 数据哈希
            
        Returns:
            验证结果
        """
        try:
            if not self.contract:
                raise ValueError("智能合约未初始化")
            
            # 查询区块链记录
            record = self.contract.functions.getRecord(
                Web3.to_bytes(hexstr=data_hash)
            ).call()
            
            return {
                "exists": True,
                "data_hash": record[0].hex(),
                "site_id": record[1],
                "timestamp": record[2],
                "ipfs_cid": record[3],
                "registrar": record[4],
                "verified": True
            }
            
        except Exception as e:
            logger.error(f"区块链验证失败: {e}")
            return {"exists": False, "error": str(e)}
    
    def create_audit_package(self, mining_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        创建完整的审计数据包
        
        Args:
            mining_data: 挖矿数据
            
        Returns:
            审计数据包信息
        """
        try:
            # 1. 标准化数据
            standardized_data = self.standardize_mining_data(mining_data)
            
            # 2. 计算数据哈希
            data_hash = self.calculate_data_hash(standardized_data)
            
            # 3. 上传到IPFS
            ipfs_cid = self.upload_to_ipfs(standardized_data, encrypt=True)
            
            # 4. 注册到区块链
            site_id = standardized_data.get('site_id', 'default_site')
            tx_hash = self.register_on_blockchain(data_hash, site_id, ipfs_cid)
            
            # 5. 创建审计记录
            audit_package = {
                "data_hash": data_hash,
                "ipfs_cid": ipfs_cid,
                "blockchain_tx_hash": tx_hash,
                "site_id": site_id,
                "timestamp": standardized_data['timestamp'],
                "verification_status": "registered",
                "audit_trail": {
                    "created_at": datetime.utcnow().isoformat(),
                    "standardization_version": "1.0",
                    "encryption_enabled": True,
                    "blockchain_network": "Base L2",
                    "ipfs_gateway": "Pinata"
                }
            }
            
            logger.info(f"审计数据包创建成功，数据哈希: {data_hash[:16]}...")
            return audit_package
            
        except Exception as e:
            logger.error(f"审计数据包创建失败: {e}")
            raise
    
    def verify_audit_package(self, data_hash: str) -> Dict[str, Any]:
        """
        验证审计数据包
        
        Args:
            data_hash: 数据哈希
            
        Returns:
            验证结果
        """
        try:
            # 1. 区块链验证
            blockchain_result = self.verify_on_blockchain(data_hash)
            
            if not blockchain_result.get("exists"):
                return {
                    "valid": False,
                    "error": "数据未在区块链上找到",
                    "blockchain_result": blockchain_result
                }
            
            # 2. IPFS数据验证
            ipfs_cid = blockchain_result.get("ipfs_cid")
            if ipfs_cid:
                try:
                    ipfs_data = self.retrieve_from_ipfs(ipfs_cid, decrypt=True)
                    retrieved_hash = self.calculate_data_hash(ipfs_data)
                    
                    hash_match = retrieved_hash == data_hash
                except Exception as e:
                    logger.warning(f"IPFS数据检索失败: {e}")
                    hash_match = False
                    ipfs_data = None
            else:
                hash_match = False
                ipfs_data = None
            
            return {
                "valid": hash_match,
                "blockchain_result": blockchain_result,
                "ipfs_data_available": ipfs_data is not None,
                "data_integrity_verified": hash_match,
                "verification_timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"审计数据包验证失败: {e}")
            return {
                "valid": False,
                "error": str(e)
            }
    
    def _extract_public_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """提取可公开的数据部分"""
        return {
            "version": data.get("version"),
            "timestamp": data.get("timestamp"),
            "site_id": data.get("site_id"),
            "mining_metrics": {
                "hashrate_th": data.get("mining_metrics", {}).get("hashrate_th"),
                "efficiency_wth": data.get("mining_metrics", {}).get("efficiency_wth")
            },
            "network_data": data.get("network_data", {}),
            "metadata": data.get("metadata", {})
        }
    
    def _extract_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """提取敏感数据部分"""
        return {
            "mining_metrics": {
                "daily_btc_production": data.get("mining_metrics", {}).get("daily_btc_production"),
                "daily_revenue_usd": data.get("mining_metrics", {}).get("daily_revenue_usd"),
                "daily_profit_usd": data.get("mining_metrics", {}).get("daily_profit_usd")
            },
            "operational_data": data.get("operational_data", {}),
            "data_integrity": data.get("data_integrity", {})
        }
    
    def _calculate_data_checksum(self, data: Dict[str, Any]) -> str:
        """计算数据校验和"""
        data_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(data_str.encode()).hexdigest()
    
    def _check_required_fields(self, data: Dict[str, Any]) -> bool:
        """检查必要字段是否存在"""
        required = ['timestamp', 'site_id', 'mining_metrics', 'network_data']
        return all(field in data for field in required)
    
    def _validate_mainnet_write_permissions(self):
        """
        验证主网写入权限 - 安全保护机制
        
        防止意外的主网交易，确保只有明确授权的操作才能写入主网
        """
        try:
            # 检查当前网络ID
            network_id = self.w3.eth.chain_id
            
            # Base L2 主网的Chain ID是8453
            BASE_MAINNET_CHAIN_ID = 8453
            BASE_TESTNET_CHAIN_ID = 84531  # Base Goerli测试网
            
            logger.info(f"当前连接的网络Chain ID: {network_id}")
            
            # 如果是主网，需要额外验证
            if network_id == BASE_MAINNET_CHAIN_ID:
                # SECURITY CHECK: 主网写入必须明确启用
                mainnet_enabled = os.environ.get('BLOCKCHAIN_ENABLE_MAINNET_WRITES')
                
                if not mainnet_enabled or mainnet_enabled.lower() != 'true':
                    raise ValueError(
                        "主网写入被禁止。这是一个安全保护机制。\n"
                        "如果您确实需要在Base L2主网上写入数据，请设置环境变量：\n"
                        "BLOCKCHAIN_ENABLE_MAINNET_WRITES=true\n"
                        "警告：主网交易将消耗真实的ETH作为gas费用。"
                    )
                
                # 验证账户余额是否足够支付gas费用
                balance = self.w3.eth.get_balance(self.account.address)
                min_balance_wei = self.w3.to_wei(0.001, 'ether')  # 至少0.001 ETH
                
                if balance < min_balance_wei:
                    raise ValueError(
                        f"账户余额不足以支付主网gas费用。\n"
                        f"当前余额: {self.w3.from_wei(balance, 'ether'):.6f} ETH\n"
                        f"建议最小余额: {self.w3.from_wei(min_balance_wei, 'ether'):.6f} ETH"
                    )
                
                # 检查智能合约地址是否已配置
                if not self.contract_address:
                    raise ValueError(
                        "主网合约地址未配置。请设置 MINING_REGISTRY_CONTRACT_ADDRESS 环境变量。"
                    )
                
                # 验证私钥是否为生产环境密钥（基本检查）
                if not os.environ.get('BLOCKCHAIN_PRIVATE_KEY'):
                    raise ValueError(
                        "主网私钥未配置。请设置 BLOCKCHAIN_PRIVATE_KEY 环境变量。"
                        "确保使用正确的主网账户私钥。"
                    )
                
                logger.warning(
                    "⚠️  准备在Base L2主网执行交易！\n"
                    f"   账户地址: {self.account.address}\n"
                    f"   余额: {self.w3.from_wei(balance, 'ether'):.6f} ETH\n"
                    f"   合约地址: {self.contract_address}"
                )
            
            elif network_id == BASE_TESTNET_CHAIN_ID:
                logger.info("✅ 连接到Base测试网络，允许写入操作")
                
            else:
                # 未知网络 - 根据配置决定是否允许
                unknown_networks_allowed = os.environ.get('BLOCKCHAIN_ALLOW_UNKNOWN_NETWORKS', 'false')
                
                if unknown_networks_allowed.lower() != 'true':
                    raise ValueError(
                        f"未知网络Chain ID: {network_id}\n"
                        "出于安全考虑，不允许在未知网络上执行交易。\n"
                        "如果这是预期的网络，请设置 BLOCKCHAIN_ALLOW_UNKNOWN_NETWORKS=true"
                    )
                else:
                    logger.warning(f"⚠️  允许在未知网络上执行交易 (Chain ID: {network_id})")
            
        except ValueError:
            # ValueError 是配置错误，应该重新抛出
            raise
        except Exception as e:
            logger.error(f"主网权限验证失败: {e}")
            raise ValueError(f"无法验证网络权限: {e}")


# 全局实例
blockchain_integration = None

def get_blockchain_integration() -> BlockchainIntegration:
    """获取区块链集成实例（单例模式）"""
    global blockchain_integration
    if blockchain_integration is None:
        blockchain_integration = BlockchainIntegration()
    return blockchain_integration


def quick_register_mining_data(mining_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    快速注册挖矿数据到区块链和IPFS
    
    Args:
        mining_data: 挖矿数据
        
    Returns:
        注册结果或None（如果失败）
    """
    try:
        integration = get_blockchain_integration()
        return integration.create_audit_package(mining_data)
    except Exception as e:
        logger.error(f"快速注册失败: {e}")
        return None


def quick_verify_mining_data(data_hash: str) -> Dict[str, Any]:
    """
    快速验证挖矿数据
    
    Args:
        data_hash: 数据哈希
        
    Returns:
        验证结果
    """
    try:
        integration = get_blockchain_integration()
        return integration.verify_audit_package(data_hash)
    except Exception as e:
        logger.error(f"快速验证失败: {e}")
        return {"valid": False, "error": str(e)}