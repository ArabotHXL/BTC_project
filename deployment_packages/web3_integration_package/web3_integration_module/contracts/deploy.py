"""
智能合约部署脚本
Smart Contract Deployment Script for Web3 Integration Module
"""

import os
import json
import time
from web3 import Web3
from eth_account import Account
from solcx import compile_source, install_solc, set_solc_version
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ContractDeployer:
    """智能合约部署器"""
    
    def __init__(self):
        """初始化部署器"""
        self.w3 = None
        self.account = None
        self.is_mainnet = False
        self._initialize_web3()
        self._initialize_account()
    
    def _initialize_web3(self):
        """初始化Web3连接"""
        # 检查是否启用主网
        self.is_mainnet = os.environ.get('BLOCKCHAIN_ENABLE_MAINNET_WRITES', '').lower() == 'true'
        
        if self.is_mainnet:
            rpc_url = "https://mainnet.base.org"
            logger.warning("🚨 主网部署模式 - 将部署到Base L2主网")
        else:
            rpc_url = "https://sepolia.base.org"
            logger.info("🛡️ 测试网部署模式 - 将部署到Base Sepolia测试网")
        
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        
        if not self.w3.is_connected():
            raise Exception(f"无法连接到网络: {rpc_url}")
        
        logger.info(f"已连接到 {'主网' if self.is_mainnet else '测试网'}")
    
    def _initialize_account(self):
        """初始化部署账户"""
        private_key = os.environ.get('BLOCKCHAIN_PRIVATE_KEY')
        if not private_key:
            raise Exception("未设置BLOCKCHAIN_PRIVATE_KEY环境变量")
        
        self.account = Account.from_key(private_key)
        logger.info(f"部署账户: {self.account.address}")
        
        # 检查账户余额
        balance = self.w3.eth.get_balance(self.account.address)
        balance_eth = self.w3.from_wei(balance, 'ether')
        logger.info(f"账户余额: {balance_eth:.6f} ETH")
        
        if balance_eth < 0.01:
            logger.warning("⚠️ 账户余额较低，可能无法完成部署")
    
    def compile_contract(self, contract_file: str) -> dict:
        """编译智能合约"""
        try:
            # 安装并设置Solidity编译器版本
            install_solc('0.8.19')
            set_solc_version('0.8.19')
            
            # 读取合约源代码
            contract_path = os.path.join(os.path.dirname(__file__), contract_file)
            with open(contract_path, 'r', encoding='utf-8') as f:
                contract_source = f.read()
            
            # 编译合约
            logger.info(f"正在编译合约: {contract_file}")
            compiled_sol = compile_source(
                contract_source,
                output_values=['abi', 'bin'],
                import_remappings=['@openzeppelin/contracts=node_modules/@openzeppelin/contracts']
            )
            
            # 获取主合约
            contract_name = os.path.splitext(contract_file)[0]
            contract_interface = None
            
            for key in compiled_sol.keys():
                if contract_name in key:
                    contract_interface = compiled_sol[key]
                    break
            
            if not contract_interface:
                raise Exception(f"未找到合约: {contract_name}")
            
            logger.info(f"合约编译完成: {contract_name}")
            return contract_interface
            
        except Exception as e:
            logger.error(f"合约编译失败: {e}")
            raise
    
    def deploy_contract(self, contract_interface: dict, constructor_args: list = None, gas_limit: int = 3000000) -> dict:
        """部署智能合约"""
        try:
            # 创建合约实例
            contract = self.w3.eth.contract(
                abi=contract_interface['abi'],
                bytecode=contract_interface['bin']
            )
            
            # 构建部署交易
            constructor_args = constructor_args or []
            
            # 估算Gas
            try:
                gas_estimate = contract.constructor(*constructor_args).estimate_gas({'from': self.account.address})
                gas_limit = min(gas_estimate * 2, gas_limit)  # 使用估算值的2倍，但不超过限制
            except Exception as e:
                logger.warning(f"Gas估算失败，使用默认值: {e}")
            
            # 获取Gas价格
            gas_price = self.w3.eth.gas_price
            
            # 构建交易
            transaction = contract.constructor(*constructor_args).build_transaction({
                'from': self.account.address,
                'gas': gas_limit,
                'gasPrice': gas_price,
                'nonce': self.w3.eth.get_transaction_count(self.account.address)
            })
            
            logger.info(f"准备部署合约，Gas限制: {gas_limit}, Gas价格: {gas_price}")
            
            # 签名交易
            signed_txn = self.w3.eth.account.sign_transaction(transaction, private_key=self.account.key)
            
            # 发送交易
            logger.info("发送部署交易...")
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            
            logger.info(f"部署交易已发送: {tx_hash.hex()}")
            logger.info("等待交易确认...")
            
            # 等待交易确认
            tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
            
            if tx_receipt.status == 1:
                logger.info(f"✅ 合约部署成功!")
                logger.info(f"合约地址: {tx_receipt.contractAddress}")
                logger.info(f"区块号: {tx_receipt.blockNumber}")
                logger.info(f"Gas使用: {tx_receipt.gasUsed}")
                
                return {
                    'success': True,
                    'contract_address': tx_receipt.contractAddress,
                    'transaction_hash': tx_hash.hex(),
                    'block_number': tx_receipt.blockNumber,
                    'gas_used': tx_receipt.gasUsed,
                    'abi': contract_interface['abi']
                }
            else:
                raise Exception("合约部署失败")
                
        except Exception as e:
            logger.error(f"合约部署失败: {e}")
            raise
    
    def deploy_mining_registry(self) -> dict:
        """部署挖矿数据注册合约"""
        logger.info("部署MiningDataRegistry合约...")
        
        # 编译合约
        contract_interface = self.compile_contract('MiningDataRegistry.sol')
        
        # 部署合约
        result = self.deploy_contract(contract_interface)
        
        if result['success']:
            # 保存合约信息
            self._save_contract_info('MiningDataRegistry', result)
        
        return result
    
    def deploy_sla_nft(self, name: str = "SLA Proof NFT", symbol: str = "SLANFT") -> dict:
        """部署SLA NFT合约"""
        logger.info(f"部署SLAProofNFT合约: {name} ({symbol})")
        
        # 编译合约
        contract_interface = self.compile_contract('SLAProofNFT.sol')
        
        # 构造函数参数
        constructor_args = [name, symbol]
        
        # 部署合约
        result = self.deploy_contract(contract_interface, constructor_args)
        
        if result['success']:
            # 保存合约信息
            self._save_contract_info('SLAProofNFT', result)
        
        return result
    
    def _save_contract_info(self, contract_name: str, deploy_result: dict):
        """保存合约信息到文件"""
        try:
            # 创建contracts/deployed目录
            deployed_dir = os.path.join(os.path.dirname(__file__), 'deployed')
            os.makedirs(deployed_dir, exist_ok=True)
            
            # 保存合约信息
            network = 'mainnet' if self.is_mainnet else 'testnet'
            contract_info = {
                'name': contract_name,
                'address': deploy_result['contract_address'],
                'transaction_hash': deploy_result['transaction_hash'],
                'block_number': deploy_result['block_number'],
                'gas_used': deploy_result['gas_used'],
                'abi': deploy_result['abi'],
                'network': network,
                'deployed_at': time.time(),
                'deployed_by': self.account.address
            }
            
            # 保存到JSON文件
            filename = f"{contract_name}_{network}.json"
            filepath = os.path.join(deployed_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(contract_info, f, indent=2, ensure_ascii=False)
            
            logger.info(f"合约信息已保存到: {filepath}")
            
            # 输出环境变量建议
            env_var_name = f"{contract_name.upper()}_CONTRACT_ADDRESS"
            logger.info(f"建议设置环境变量: {env_var_name}={deploy_result['contract_address']}")
            
        except Exception as e:
            logger.error(f"保存合约信息失败: {e}")
    
    def verify_deployment(self, contract_address: str, abi: list) -> bool:
        """验证合约部署"""
        try:
            # 创建合约实例
            contract = self.w3.eth.contract(address=contract_address, abi=abi)
            
            # 调用一个只读函数来验证合约
            # 不同合约可能有不同的只读函数
            try:
                # 尝试调用常见的只读函数
                if hasattr(contract.functions, 'owner'):
                    owner = contract.functions.owner().call()
                    logger.info(f"合约验证成功，所有者: {owner}")
                elif hasattr(contract.functions, 'name'):
                    name = contract.functions.name().call()
                    logger.info(f"合约验证成功，名称: {name}")
                else:
                    # 检查合约代码
                    code = self.w3.eth.get_code(contract_address)
                    if code != b'':
                        logger.info("合约验证成功，包含字节码")
                    else:
                        return False
                
                return True
                
            except Exception as e:
                logger.error(f"合约函数调用失败: {e}")
                return False
                
        except Exception as e:
            logger.error(f"合约验证失败: {e}")
            return False

def main():
    """主函数"""
    try:
        # 创建部署器
        deployer = ContractDeployer()
        
        # 部署选择
        print("\n=== Web3集成模块合约部署工具 ===")
        print("1. 部署MiningDataRegistry合约")
        print("2. 部署SLAProofNFT合约")
        print("3. 部署所有合约")
        print("0. 退出")
        
        choice = input("\n请选择部署选项 (0-3): ").strip()
        
        if choice == '1':
            result = deployer.deploy_mining_registry()
            print(f"\nMiningDataRegistry部署结果: {result}")
            
        elif choice == '2':
            name = input("请输入NFT名称 (默认: SLA Proof NFT): ").strip() or "SLA Proof NFT"
            symbol = input("请输入NFT符号 (默认: SLANFT): ").strip() or "SLANFT"
            result = deployer.deploy_sla_nft(name, symbol)
            print(f"\nSLAProofNFT部署结果: {result}")
            
        elif choice == '3':
            print("\n开始部署所有合约...")
            
            # 部署MiningDataRegistry
            registry_result = deployer.deploy_mining_registry()
            print(f"\n1/2 MiningDataRegistry: {'✅ 成功' if registry_result['success'] else '❌ 失败'}")
            
            # 部署SLAProofNFT
            nft_result = deployer.deploy_sla_nft()
            print(f"2/2 SLAProofNFT: {'✅ 成功' if nft_result['success'] else '❌ 失败'}")
            
            print(f"\n部署完成! 成功: {sum([registry_result['success'], nft_result['success']])}/2")
            
        elif choice == '0':
            print("退出部署工具")
            
        else:
            print("无效选择")
    
    except KeyboardInterrupt:
        print("\n\n部署被用户中断")
    except Exception as e:
        logger.error(f"部署失败: {e}")
        print(f"\n❌ 部署失败: {e}")

if __name__ == '__main__':
    main()