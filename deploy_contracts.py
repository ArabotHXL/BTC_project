#!/usr/bin/env python3
"""
SLA Proof NFT Smart Contract Deployment Script
Deploys SLAProofNFT contract to Base L2 or other compatible networks

Usage:
    python deploy_contracts.py --network base-sepolia
    python deploy_contracts.py --network base-mainnet --verify
"""

import os
import json
import time
import logging
from typing import Dict, Any, Optional
from web3 import Web3
from web3.middleware import geth_poa_middleware
import argparse
from dataclasses import dataclass

# Configuration
@dataclass
class NetworkConfig:
    name: str
    rpc_url: str
    chain_id: int
    explorer_url: str
    is_testnet: bool

# Network configurations
NETWORKS = {
    'base-sepolia': NetworkConfig(
        name='Base Sepolia',
        rpc_url='https://sepolia.base.org',
        chain_id=84532,
        explorer_url='https://sepolia.basescan.org',
        is_testnet=True
    ),
    'base-mainnet': NetworkConfig(
        name='Base Mainnet',
        rpc_url='https://mainnet.base.org',
        chain_id=8453,
        explorer_url='https://basescan.org',
        is_testnet=False
    ),
    'localhost': NetworkConfig(
        name='Local Development',
        rpc_url='http://127.0.0.1:8545',
        chain_id=1337,
        explorer_url='http://localhost:8545',
        is_testnet=True
    )
}

class ContractDeployer:
    def __init__(self, network: str):
        self.network_config = NETWORKS.get(network)
        if not self.network_config:
            raise ValueError(f"Unsupported network: {network}")
        
        self.w3 = Web3(Web3.HTTPProvider(self.network_config.rpc_url))
        
        # Add POA middleware for networks that need it
        if network in ['base-sepolia', 'base-mainnet']:
            self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
        
        self.setup_logging()
        self.load_contract_artifacts()
        self.setup_account()
    
    def setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(f'deployment_{self.network_config.name.lower().replace(" ", "_")}.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def load_contract_artifacts(self):
        """Load compiled contract artifacts"""
        try:
            # This would typically load from a build directory
            # For now, we'll use simplified contract compilation
            self.contract_artifacts = {
                'SLAProofNFT': {
                    'abi': self._get_sla_nft_abi(),
                    'bytecode': '0x608060405234801561001057600080fd5b50...'  # Placeholder - would be actual bytecode
                }
            }
        except Exception as e:
            self.logger.error(f"Failed to load contract artifacts: {e}")
            raise
    
    def setup_account(self):
        """Setup deployment account from environment variables"""
        private_key = os.getenv('DEPLOYER_PRIVATE_KEY')
        if not private_key:
            raise ValueError("DEPLOYER_PRIVATE_KEY environment variable not set")
        
        self.account = self.w3.eth.account.from_key(private_key)
        self.deployer_address = self.account.address
        
        # Check balance
        balance = self.w3.eth.get_balance(self.deployer_address)
        balance_eth = self.w3.from_wei(balance, 'ether')
        
        self.logger.info(f"Deployer address: {self.deployer_address}")
        self.logger.info(f"Deployer balance: {balance_eth:.4f} ETH")
        
        if balance_eth < 0.01:  # Minimum balance check
            self.logger.warning(f"Low balance: {balance_eth:.4f} ETH")
    
    def deploy_sla_proof_nft(self, 
                           name: str = "SLA Proof Certificate", 
                           symbol: str = "SLAPROOF") -> Dict[str, Any]:
        """Deploy SLAProofNFT contract"""
        
        self.logger.info(f"Deploying SLAProofNFT contract...")
        self.logger.info(f"Network: {self.network_config.name}")
        self.logger.info(f"Name: {name}, Symbol: {symbol}")
        
        # Prepare contract
        contract_data = self.contract_artifacts['SLAProofNFT']
        contract = self.w3.eth.contract(
            abi=contract_data['abi'],
            bytecode=contract_data['bytecode']
        )
        
        # Estimate gas
        try:
            gas_estimate = contract.constructor(name, symbol).estimate_gas({
                'from': self.deployer_address
            })
            gas_limit = int(gas_estimate * 1.2)  # Add 20% buffer
        except Exception as e:
            self.logger.warning(f"Gas estimation failed: {e}")
            gas_limit = 3000000  # Fallback gas limit
        
        # Get current gas price
        gas_price = self.w3.eth.gas_price
        
        self.logger.info(f"Estimated gas: {gas_limit}")
        self.logger.info(f"Gas price: {self.w3.from_wei(gas_price, 'gwei')} gwei")
        
        # Build transaction
        constructor_txn = contract.constructor(name, symbol).build_transaction({
            'from': self.deployer_address,
            'gas': gas_limit,
            'gasPrice': gas_price,
            'nonce': self.w3.eth.get_transaction_count(self.deployer_address),
            'chainId': self.network_config.chain_id
        })
        
        # Sign and send transaction
        signed_txn = self.w3.eth.account.sign_transaction(constructor_txn, private_key=self.account.key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        
        self.logger.info(f"Transaction sent: {tx_hash.hex()}")
        self.logger.info("Waiting for transaction confirmation...")
        
        # Wait for transaction receipt
        tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
        
        if tx_receipt.status == 1:
            contract_address = tx_receipt.contractAddress
            self.logger.info(f"✅ Contract deployed successfully!")
            self.logger.info(f"Contract address: {contract_address}")
            self.logger.info(f"Transaction hash: {tx_hash.hex()}")
            self.logger.info(f"Gas used: {tx_receipt.gasUsed}")
            
            # Save deployment info
            deployment_info = {
                'contract_address': contract_address,
                'transaction_hash': tx_hash.hex(),
                'deployer_address': self.deployer_address,
                'network': self.network_config.name,
                'chain_id': self.network_config.chain_id,
                'gas_used': tx_receipt.gasUsed,
                'block_number': tx_receipt.blockNumber,
                'deployment_time': int(time.time()),
                'constructor_args': {
                    'name': name,
                    'symbol': symbol
                }
            }
            
            self.save_deployment_info(deployment_info)
            return deployment_info
            
        else:
            self.logger.error("❌ Contract deployment failed!")
            raise Exception(f"Deployment transaction failed: {tx_hash.hex()}")
    
    def save_deployment_info(self, deployment_info: Dict[str, Any]):
        """Save deployment information to file"""
        os.makedirs('deployments', exist_ok=True)
        
        filename = f"deployments/sla_proof_nft_{self.network_config.name.lower().replace(' ', '_')}.json"
        
        with open(filename, 'w') as f:
            json.dump(deployment_info, f, indent=2)
        
        self.logger.info(f"Deployment info saved to: {filename}")
        
        # Also update environment config
        self.update_env_config(deployment_info)
    
    def update_env_config(self, deployment_info: Dict[str, Any]):
        """Update environment configuration with deployed contract address"""
        env_file = '.env'
        env_lines = []
        
        # Read existing .env file
        if os.path.exists(env_file):
            with open(env_file, 'r') as f:
                env_lines = f.readlines()
        
        # Update or add contract address
        contract_var = f"SLA_PROOF_NFT_CONTRACT_ADDRESS"
        network_var = f"SLA_PROOF_NFT_NETWORK"
        
        updated_contract = False
        updated_network = False
        
        for i, line in enumerate(env_lines):
            if line.startswith(f"{contract_var}="):
                env_lines[i] = f"{contract_var}={deployment_info['contract_address']}\n"
                updated_contract = True
            elif line.startswith(f"{network_var}="):
                env_lines[i] = f"{network_var}={self.network_config.name}\n"
                updated_network = True
        
        # Add new variables if not found
        if not updated_contract:
            env_lines.append(f"{contract_var}={deployment_info['contract_address']}\n")
        if not updated_network:
            env_lines.append(f"{network_var}={self.network_config.name}\n")
        
        # Write updated .env file
        with open(env_file, 'w') as f:
            f.writelines(env_lines)
        
        self.logger.info(f"Environment variables updated in {env_file}")
    
    def verify_contract(self, contract_address: str, constructor_args: list):
        """Verify contract on block explorer (placeholder)"""
        self.logger.info(f"Contract verification on {self.network_config.explorer_url}")
        self.logger.info(f"Contract address: {contract_address}")
        self.logger.info("Note: Automated verification not implemented yet.")
        self.logger.info("Please verify manually on the block explorer.")
    
    def test_deployed_contract(self, contract_address: str):
        """Test basic functionality of deployed contract"""
        self.logger.info("Testing deployed contract...")
        
        contract_data = self.contract_artifacts['SLAProofNFT']
        contract = self.w3.eth.contract(
            address=contract_address,
            abi=contract_data['abi']
        )
        
        try:
            # Test read functions
            name = contract.functions.name().call()
            symbol = contract.functions.symbol().call()
            owner = contract.functions.owner().call()
            
            self.logger.info(f"Contract name: {name}")
            self.logger.info(f"Contract symbol: {symbol}")
            self.logger.info(f"Contract owner: {owner}")
            
            # Test contract info
            version, description = contract.functions.getContractInfo().call()
            self.logger.info(f"Contract version: {version}")
            self.logger.info(f"Contract description: {description}")
            
            self.logger.info("✅ Contract test passed!")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Contract test failed: {e}")
            return False
    
    def _get_sla_nft_abi(self) -> list:
        """Get SLA NFT contract ABI (simplified version)"""
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
                "name": "getContractInfo",
                "outputs": [
                    {"name": "version", "type": "string"},
                    {"name": "description", "type": "string"}
                ],
                "stateMutability": "pure",
                "type": "function"
            }
        ]

def main():
    parser = argparse.ArgumentParser(description='Deploy SLA Proof NFT contracts')
    parser.add_argument('--network', required=True, choices=list(NETWORKS.keys()),
                       help='Target network for deployment')
    parser.add_argument('--verify', action='store_true',
                       help='Verify contract on block explorer')
    parser.add_argument('--name', default='SLA Proof Certificate',
                       help='Contract name')
    parser.add_argument('--symbol', default='SLAPROOF',
                       help='Contract symbol')
    parser.add_argument('--test', action='store_true',
                       help='Test deployed contract functionality')
    
    args = parser.parse_args()
    
    try:
        # Initialize deployer
        deployer = ContractDeployer(args.network)
        
        # Deploy contract
        deployment_info = deployer.deploy_sla_proof_nft(
            name=args.name,
            symbol=args.symbol
        )
        
        # Test deployed contract
        if args.test:
            deployer.test_deployed_contract(deployment_info['contract_address'])
        
        # Verify contract
        if args.verify:
            deployer.verify_contract(
                deployment_info['contract_address'],
                [args.name, args.symbol]
            )
        
        print("\n" + "="*60)
        print("🎉 DEPLOYMENT SUCCESSFUL!")
        print("="*60)
        print(f"Network: {deployer.network_config.name}")
        print(f"Contract Address: {deployment_info['contract_address']}")
        print(f"Transaction Hash: {deployment_info['transaction_hash']}")
        print(f"Explorer URL: {deployer.network_config.explorer_url}/address/{deployment_info['contract_address']}")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ Deployment failed: {e}")
        exit(1)

if __name__ == '__main__':
    main()