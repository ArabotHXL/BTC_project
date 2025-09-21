"""
Blockchain Configuration for SLA Proof NFT System
Manages Web3 connections, contract addresses, and network settings
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from web3 import Web3
from web3.middleware import geth_poa_middleware
from dataclasses import dataclass

@dataclass
class BlockchainNetwork:
    """Network configuration dataclass"""
    name: str
    rpc_url: str
    chain_id: int
    explorer_url: str
    is_testnet: bool
    gas_multiplier: float = 1.2
    max_gas_price_gwei: int = 100

class BlockchainConfig:
    """Blockchain configuration and Web3 connection manager"""
    
    # Network configurations
    NETWORKS = {
        'base-sepolia': BlockchainNetwork(
            name='Base Sepolia Testnet',
            rpc_url='https://sepolia.base.org',
            chain_id=84532,
            explorer_url='https://sepolia.basescan.org',
            is_testnet=True,
            gas_multiplier=1.3,
            max_gas_price_gwei=50
        ),
        'base-mainnet': BlockchainNetwork(
            name='Base Mainnet',
            rpc_url='https://mainnet.base.org',
            chain_id=8453,
            explorer_url='https://basescan.org',
            is_testnet=False,
            gas_multiplier=1.2,
            max_gas_price_gwei=100
        ),
        'localhost': BlockchainNetwork(
            name='Local Development',
            rpc_url='http://127.0.0.1:8545',
            chain_id=1337,
            explorer_url='http://localhost:8545',
            is_testnet=True,
            gas_multiplier=1.1,
            max_gas_price_gwei=20
        )
    }
    
    def __init__(self, network_name: str = None):
        """Initialize blockchain configuration"""
        self.logger = logging.getLogger(__name__)
        
        # Determine network from environment or parameter
        self.network_name = network_name or os.getenv('SLA_PROOF_NFT_NETWORK', 'base-sepolia')
        
        if self.network_name not in self.NETWORKS:
            raise ValueError(f"Unsupported network: {self.network_name}")
        
        self.network = self.NETWORKS[self.network_name]
        self.w3 = None
        self.contracts = {}
        
        # Initialize Web3 connection
        self._initialize_web3()
        
        # Load contract addresses
        self._load_contract_addresses()
        
        # Load contract ABIs
        self._load_contract_abis()
    
    def _initialize_web3(self):
        """Initialize Web3 connection with appropriate middleware"""
        try:
            self.w3 = Web3(Web3.HTTPProvider(self.network.rpc_url))
            
            # Add POA middleware for networks that need it
            if self.network_name in ['base-sepolia', 'base-mainnet']:
                self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
            
            # Test connection
            if not self.w3.is_connected():
                raise ConnectionError(f"Failed to connect to {self.network.name}")
            
            # Get chain ID to verify network
            chain_id = self.w3.eth.chain_id
            if chain_id != self.network.chain_id:
                self.logger.warning(f"Chain ID mismatch: expected {self.network.chain_id}, got {chain_id}")
            
            self.logger.info(f"Connected to {self.network.name} (Chain ID: {chain_id})")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Web3: {e}")
            raise
    
    def _load_contract_addresses(self):
        """Load deployed contract addresses"""
        self.contract_addresses = {}
        
        # Try to load from environment variables
        sla_nft_address = os.getenv('SLA_PROOF_NFT_CONTRACT_ADDRESS')
        if sla_nft_address:
            self.contract_addresses['SLAProofNFT'] = sla_nft_address
        
        # Try to load from deployment files
        deployment_file = f"deployments/sla_proof_nft_{self.network_name.replace('-', '_')}.json"
        if os.path.exists(deployment_file):
            try:
                with open(deployment_file, 'r') as f:
                    deployment_data = json.load(f)
                    self.contract_addresses['SLAProofNFT'] = deployment_data['contract_address']
                    self.logger.info(f"Loaded contract address from {deployment_file}")
            except Exception as e:
                self.logger.warning(f"Failed to load deployment file: {e}")
        
        # Log loaded addresses
        for contract_name, address in self.contract_addresses.items():
            self.logger.info(f"{contract_name}: {address}")
    
    def _load_contract_abis(self):
        """Load contract ABIs"""
        self.contract_abis = {
            'SLAProofNFT': self._get_sla_nft_abi()
        }
    
    def get_contract(self, contract_name: str):
        """Get Web3 contract instance"""
        if contract_name in self.contracts:
            return self.contracts[contract_name]
        
        if contract_name not in self.contract_addresses:
            raise ValueError(f"Contract address not found for {contract_name}")
        
        if contract_name not in self.contract_abis:
            raise ValueError(f"Contract ABI not found for {contract_name}")
        
        try:
            contract = self.w3.eth.contract(
                address=self.contract_addresses[contract_name],
                abi=self.contract_abis[contract_name]
            )
            
            # Cache the contract instance
            self.contracts[contract_name] = contract
            return contract
            
        except Exception as e:
            self.logger.error(f"Failed to create contract instance for {contract_name}: {e}")
            raise
    
    def get_gas_price(self) -> int:
        """Get current gas price with network-specific limits"""
        try:
            gas_price = self.w3.eth.gas_price
            max_gas_price = self.w3.to_wei(self.network.max_gas_price_gwei, 'gwei')
            
            # Cap gas price to network maximum
            if gas_price > max_gas_price:
                self.logger.warning(f"Gas price {self.w3.from_wei(gas_price, 'gwei')} gwei exceeds maximum, using {self.network.max_gas_price_gwei} gwei")
                gas_price = max_gas_price
            
            return gas_price
            
        except Exception as e:
            self.logger.error(f"Failed to get gas price: {e}")
            # Return fallback gas price
            return self.w3.to_wei(20, 'gwei')
    
    def estimate_gas_with_buffer(self, transaction: Dict[str, Any]) -> int:
        """Estimate gas usage with network-specific buffer"""
        try:
            gas_estimate = self.w3.eth.estimate_gas(transaction)
            return int(gas_estimate * self.network.gas_multiplier)
        except Exception as e:
            self.logger.warning(f"Gas estimation failed: {e}")
            return 500000  # Fallback gas limit
    
    def get_transaction_receipt(self, tx_hash: str, timeout: int = 300):
        """Get transaction receipt with timeout"""
        return self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=timeout)
    
    def get_block_explorer_url(self, tx_hash: str = None, address: str = None) -> str:
        """Get block explorer URL for transaction or address"""
        if tx_hash:
            return f"{self.network.explorer_url}/tx/{tx_hash}"
        elif address:
            return f"{self.network.explorer_url}/address/{address}"
        else:
            return self.network.explorer_url
    
    def is_contract_deployed(self, contract_name: str) -> bool:
        """Check if contract is deployed and accessible"""
        try:
            if contract_name not in self.contract_addresses:
                return False
            
            address = self.contract_addresses[contract_name]
            code = self.w3.eth.get_code(address)
            
            # Contract is deployed if it has bytecode
            return len(code) > 0
            
        except Exception as e:
            self.logger.error(f"Failed to check contract deployment: {e}")
            return False
    
    def get_network_info(self) -> Dict[str, Any]:
        """Get current network information"""
        try:
            latest_block = self.w3.eth.get_block('latest')
            gas_price = self.get_gas_price()
            
            return {
                'network_name': self.network.name,
                'chain_id': self.network.chain_id,
                'is_testnet': self.network.is_testnet,
                'latest_block_number': latest_block.number,
                'latest_block_timestamp': latest_block.timestamp,
                'gas_price_gwei': self.w3.from_wei(gas_price, 'gwei'),
                'explorer_url': self.network.explorer_url,
                'contracts_deployed': {
                    name: self.is_contract_deployed(name) 
                    for name in self.contract_addresses.keys()
                }
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get network info: {e}")
            return {}
    
    def _get_sla_nft_abi(self) -> list:
        """Get SLA NFT contract ABI"""
        return [
            {
                "inputs": [
                    {"name": "name", "type": "string"},
                    {"name": "symbol", "type": "string"}
                ],
                "stateMutability": "nonpayable",
                "type": "constructor"
            },
            {
                "inputs": [],
                "name": "name",
                "outputs": [{"name": "", "type": "string"}],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [],
                "name": "symbol",
                "outputs": [{"name": "", "type": "string"}],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [],
                "name": "owner",
                "outputs": [{"name": "", "type": "address"}],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [],
                "name": "totalCertificatesIssued",
                "outputs": [{"name": "", "type": "uint256"}],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [],
                "name": "totalVerifications",
                "outputs": [{"name": "", "type": "uint256"}],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [{"name": "user", "type": "address"}],
                "name": "getUserCertificates",
                "outputs": [{"name": "", "type": "uint256[]"}],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [{"name": "tokenId", "type": "uint256"}],
                "name": "getCertificate",
                "outputs": [
                    {
                        "components": [
                            {"name": "monthYear", "type": "uint256"},
                            {"name": "recipient", "type": "address"},
                            {"name": "mintedAt", "type": "uint256"},
                            {
                                "components": [
                                    {"name": "uptime", "type": "uint256"},
                                    {"name": "responseTime", "type": "uint256"},
                                    {"name": "accuracy", "type": "uint256"},
                                    {"name": "availability", "type": "uint256"},
                                    {"name": "transparencyScore", "type": "uint256"},
                                    {"name": "blockchainVerifications", "type": "uint256"},
                                    {"name": "composite", "type": "uint256"}
                                ],
                                "name": "metrics",
                                "type": "tuple"
                            },
                            {"name": "ipfsCid", "type": "string"},
                            {"name": "isVerified", "type": "bool"},
                            {"name": "verifier", "type": "address"},
                            {"name": "verificationNote", "type": "string"},
                            {"name": "verifiedAt", "type": "uint256"}
                        ],
                        "name": "",
                        "type": "tuple"
                    }
                ],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [{"name": "monthYear", "type": "uint256"}],
                "name": "getMonthlyStats",
                "outputs": [
                    {"name": "certificateCount", "type": "uint256"},
                    {"name": "averageSLA", "type": "uint256"},
                    {"name": "reportCid", "type": "string"}
                ],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [],
                "name": "getContractInfo",
                "outputs": [
                    {"name": "version", "type": "string"},
                    {"name": "description", "type": "string"}
                ],
                "stateMutability": "pure",
                "type": "function"
            },
            {
                "anonymous": False,
                "inputs": [
                    {"indexed": True, "name": "tokenId", "type": "uint256"},
                    {"indexed": True, "name": "recipient", "type": "address"},
                    {"indexed": True, "name": "monthYear", "type": "uint256"},
                    {"indexed": False, "name": "slaScore", "type": "uint256"},
                    {"indexed": False, "name": "ipfsCid", "type": "string"}
                ],
                "name": "SLACertificateMinted",
                "type": "event"
            },
            {
                "anonymous": False,
                "inputs": [
                    {"indexed": True, "name": "tokenId", "type": "uint256"},
                    {"indexed": True, "name": "verifier", "type": "address"},
                    {"indexed": False, "name": "isValid", "type": "bool"},
                    {"indexed": False, "name": "verificationNote", "type": "string"}
                ],
                "name": "CertificateVerified",
                "type": "event"
            }
        ]

# Global instance for easy access
_blockchain_config = None

def get_blockchain_config(network_name: str = None) -> BlockchainConfig:
    """Get or create blockchain configuration instance"""
    global _blockchain_config
    
    if _blockchain_config is None or (network_name and _blockchain_config.network_name != network_name):
        _blockchain_config = BlockchainConfig(network_name)
    
    return _blockchain_config

def get_web3() -> Web3:
    """Get Web3 instance"""
    return get_blockchain_config().w3

def get_sla_nft_contract():
    """Get SLA NFT contract instance"""
    return get_blockchain_config().get_contract('SLAProofNFT')

# Environment variable helpers
def set_contract_address(contract_name: str, address: str):
    """Set contract address in environment (for runtime configuration)"""
    config = get_blockchain_config()
    config.contract_addresses[contract_name] = address
    os.environ[f'{contract_name.upper()}_CONTRACT_ADDRESS'] = address

def get_contract_address(contract_name: str) -> Optional[str]:
    """Get contract address"""
    config = get_blockchain_config()
    return config.contract_addresses.get(contract_name)