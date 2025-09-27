"""
NFT铸造服务
为Web3集成模块提供月度SLA证明NFT自动铸造功能
"""

import logging
import json
import time
import threading
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Tuple, Any
import os
import hashlib
import base64

# 本地导入
try:
    from ..models import SLACertificateRecord, NFTMintStatus, NFTMintingQueue
    from .blockchain import blockchain_integration
except ImportError:
    # Fallback for standalone execution
    from models import SLACertificateRecord, NFTMintStatus, NFTMintingQueue
    from services.blockchain import blockchain_integration

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SLANFTMintingSystem:
    """SLA NFT自动铸造系统主类"""
    
    def __init__(self):
        """初始化铸造系统"""
        self.is_running = False
        self.minting_thread = None
        
        # 系统组件
        self.blockchain_integration = blockchain_integration
        
        # SLA NFT合约配置（需要部署后更新）
        self.sla_nft_contract_address = os.environ.get('SLA_NFT_CONTRACT_ADDRESS')
        self.sla_nft_contract_abi = self._load_sla_nft_contract_abi()
        
        # 铸造配置
        self.minting_config = {
            'auto_mint_enabled': os.environ.get('SLA_AUTO_MINT_ENABLED', 'true').lower() == 'true',
            'mint_day': int(os.environ.get('SLA_MINT_DAY', '3')),  # 每月3号铸造
            'mint_hour': int(os.environ.get('SLA_MINT_HOUR', '8')),  # 上午8点铸造
            'retry_attempts': int(os.environ.get('SLA_MINT_RETRY_ATTEMPTS', '3')),
            'retry_interval': int(os.environ.get('SLA_MINT_RETRY_INTERVAL', '3600')),  # 1小时
            'batch_size': int(os.environ.get('SLA_MINT_BATCH_SIZE', '10')),  # 批量铸造大小
            'gas_limit': int(os.environ.get('SLA_MINT_GAS_LIMIT', '500000')),
            'gas_price_multiplier': float(os.environ.get('SLA_MINT_GAS_PRICE_MULTIPLIER', '1.2'))
        }
        
        logger.info("SLANFTMintingSystem initialized")
    
    def start_minting_service(self):
        """启动铸造服务"""
        if self.is_running:
            logger.warning("NFT铸造服务已在运行")
            return
        
        if not self.minting_config['auto_mint_enabled']:
            logger.info("自动铸造功能已禁用")
            return
        
        logger.info("正在启动NFT铸造服务...")
        self.is_running = True
        
        # 启动铸造线程
        self.minting_thread = threading.Thread(target=self._minting_loop, daemon=True)
        self.minting_thread.start()
        
        logger.info("NFT铸造服务已启动")
    
    def stop_minting_service(self):
        """停止铸造服务"""
        if not self.is_running:
            return
        
        logger.info("正在停止NFT铸造服务...")
        self.is_running = False
        
        # 等待铸造线程结束
        if self.minting_thread and self.minting_thread.is_alive():
            self.minting_thread.join(timeout=10)
        
        logger.info("NFT铸造服务已停止")
    
    def _minting_loop(self):
        """铸造主循环"""
        while self.is_running:
            try:
                # 检查是否应该执行月度铸造
                if self._should_perform_monthly_mint():
                    self._perform_monthly_mint()
                
                # 处理铸造队列
                self._process_minting_queue()
                
                # 等待下次检查
                time.sleep(300)  # 5分钟检查一次
                
            except Exception as e:
                logger.error(f"铸造循环出错: {e}")
                time.sleep(60)  # 出错后等待1分钟
    
    def _should_perform_monthly_mint(self) -> bool:
        """检查是否应该执行月度铸造"""
        try:
            now = datetime.utcnow()
            
            # 检查是否是铸造日期和时间
            if (now.day == self.minting_config['mint_day'] and
                now.hour == self.minting_config['mint_hour']):
                
                # 检查上个月是否已经铸造过
                last_month = now.replace(day=1) - timedelta(days=1)
                month_year = int(f"{last_month.year}{last_month.month:02d}")
                
                return not self._is_monthly_mint_completed(month_year)
            
            return False
            
        except Exception as e:
            logger.error(f"检查月度铸造时机失败: {e}")
            return False
    
    def _perform_monthly_mint(self):
        """执行月度铸造"""
        try:
            # 获取上个月的SLA数据
            last_month = datetime.utcnow().replace(day=1) - timedelta(days=1)
            month_year = int(f"{last_month.year}{last_month.month:02d}")
            
            logger.info(f"开始执行月度NFT铸造: {month_year}")
            
            # 获取需要铸造的SLA证书
            certificates_to_mint = self._get_certificates_for_minting(month_year)
            
            if not certificates_to_mint:
                logger.info(f"没有需要铸造的SLA证书: {month_year}")
                return
            
            # 批量添加到铸造队列
            for certificate in certificates_to_mint:
                self._add_to_minting_queue(certificate)
            
            logger.info(f"已添加 {len(certificates_to_mint)} 个证书到铸造队列")
            
        except Exception as e:
            logger.error(f"执行月度铸造失败: {e}")
    
    def _process_minting_queue(self):
        """处理铸造队列"""
        try:
            # 获取待处理的铸造任务
            pending_tasks = self._get_pending_minting_tasks()
            
            for task in pending_tasks[:self.minting_config['batch_size']]:
                try:
                    self._process_single_minting_task(task)
                except Exception as e:
                    logger.error(f"处理铸造任务 {task.task_id} 失败: {e}")
                    self._handle_minting_failure(task, str(e))
                    
        except Exception as e:
            logger.error(f"处理铸造队列失败: {e}")
    
    def _process_single_minting_task(self, task):
        """处理单个铸造任务"""
        try:
            # 更新任务状态为铸造中
            task.status = NFTMintStatus.MINTING
            task.started_at = datetime.utcnow()
            # 这里应该保存到数据库
            
            # 执行铸造
            result = self._mint_sla_nft(task)
            
            if result['success']:
                # 铸造成功
                task.status = NFTMintStatus.MINTED
                task.transaction_hash = result['transaction_hash']
                task.token_id = result.get('token_id')
                task.gas_used = result.get('gas_used')
                task.completed_at = datetime.utcnow()
                
                # 更新证书记录
                self._update_certificate_mint_status(task.certificate_id, result)
                
                logger.info(f"NFT铸造成功: {task.task_id}")
                
            else:
                # 铸造失败
                self._handle_minting_failure(task, result.get('error', '未知错误'))
                
        except Exception as e:
            logger.error(f"处理铸造任务失败: {e}")
            self._handle_minting_failure(task, str(e))
    
    def _mint_sla_nft(self, task) -> Dict[str, Any]:
        """铸造SLA NFT"""
        try:
            if not self.blockchain_integration.w3:
                return {'success': False, 'error': 'Web3连接不可用'}
            
            if not self.sla_nft_contract_address:
                return {'success': False, 'error': 'NFT合约地址未配置'}
            
            # 创建合约实例
            contract = self.blockchain_integration.w3.eth.contract(
                address=self.sla_nft_contract_address,
                abi=self.sla_nft_contract_abi
            )
            
            # 准备铸造参数
            recipient = task.recipient_address
            token_uri = task.token_uri
            metadata = task.metadata or {}
            
            # 构建交易
            account = self.blockchain_integration.account
            if not account:
                return {'success': False, 'error': '账户未配置'}
            
            # 估算Gas
            gas_estimate = contract.functions.mintSLACertificate(
                recipient,
                metadata.get('month_year', 0),
                self._build_sla_metrics(metadata),
                metadata.get('ipfs_cid', '')
            ).estimate_gas({'from': account.address})
            
            # 构建交易
            transaction = contract.functions.mintSLACertificate(
                recipient,
                metadata.get('month_year', 0),
                self._build_sla_metrics(metadata),
                metadata.get('ipfs_cid', '')
            ).build_transaction({
                'from': account.address,
                'gas': min(gas_estimate * 2, self.minting_config['gas_limit']),
                'gasPrice': int(self.blockchain_integration.w3.eth.gas_price * self.minting_config['gas_price_multiplier']),
                'nonce': self.blockchain_integration.w3.eth.get_transaction_count(account.address)
            })
            
            # 签名交易
            signed_tx = self.blockchain_integration.w3.eth.account.sign_transaction(
                transaction, private_key=account.key
            )
            
            # 发送交易
            tx_hash = self.blockchain_integration.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            
            # 等待交易确认
            receipt = self.blockchain_integration.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
            
            if receipt.status == 1:
                # 解析事件获取token_id
                token_id = self._extract_token_id_from_receipt(receipt, contract)
                
                return {
                    'success': True,
                    'transaction_hash': receipt.transactionHash.hex(),
                    'token_id': token_id,
                    'gas_used': receipt.gasUsed,
                    'block_number': receipt.blockNumber
                }
            else:
                return {'success': False, 'error': '交易执行失败'}
                
        except Exception as e:
            logger.error(f"铸造NFT失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def _build_sla_metrics(self, metadata: Dict[str, Any]) -> List[int]:
        """构建SLA指标数组"""
        return [
            int(metadata.get('uptime_percentage', 0) * 100),  # 转换为基点
            int(metadata.get('response_time_avg', 0)),
            int(metadata.get('accuracy_percentage', 0) * 100),
            int(metadata.get('availability_percentage', 0) * 100),
            int(metadata.get('transparency_score', 0) * 100),
            int(metadata.get('blockchain_verifications', 0)),
            int(metadata.get('sla_score', 0) * 100)
        ]
    
    def _extract_token_id_from_receipt(self, receipt, contract) -> Optional[int]:
        """从交易收据中提取token_id"""
        try:
            # 解析事件日志
            logs = contract.events.SLACertificateMinted().process_receipt(receipt)
            if logs:
                return logs[0]['args']['tokenId']
            return None
            
        except Exception as e:
            logger.error(f"提取token_id失败: {e}")
            return None
    
    def _handle_minting_failure(self, task, error_message: str):
        """处理铸造失败"""
        try:
            task.retry_count += 1
            task.last_error = error_message
            
            if task.retry_count >= task.max_retries:
                # 超过最大重试次数
                task.status = NFTMintStatus.FAILED
                task.completed_at = datetime.utcnow()
                logger.error(f"铸造任务失败，超过最大重试次数: {task.task_id}")
            else:
                # 设置下次重试时间
                task.status = NFTMintStatus.PENDING
                task.next_retry_at = datetime.utcnow() + timedelta(
                    seconds=self.minting_config['retry_interval']
                )
                logger.warning(f"铸造任务将重试: {task.task_id}, 重试次数: {task.retry_count}")
            
            # 这里应该保存到数据库
            
        except Exception as e:
            logger.error(f"处理铸造失败时出错: {e}")
    
    def _load_sla_nft_contract_abi(self) -> List[Dict]:
        """加载SLA NFT合约ABI"""
        # 这里应该加载实际的合约ABI
        # 暂时返回基本的ERC721 ABI
        return [
            {
                "inputs": [
                    {"name": "recipient", "type": "address"},
                    {"name": "monthYear", "type": "uint256"},
                    {"name": "metrics", "type": "tuple"},
                    {"name": "ipfsCid", "type": "string"}
                ],
                "name": "mintSLACertificate",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            }
        ]
    
    # 数据查询方法（在实际实现中应该查询数据库）
    def _is_monthly_mint_completed(self, month_year: int) -> bool:
        """检查月度铸造是否已完成"""
        # 在实际实现中查询数据库
        return False
    
    def _get_certificates_for_minting(self, month_year: int) -> List:
        """获取需要铸造的证书"""
        # 在实际实现中查询数据库
        return []
    
    def _get_pending_minting_tasks(self) -> List:
        """获取待处理的铸造任务"""
        # 在实际实现中查询数据库
        return []
    
    def _add_to_minting_queue(self, certificate):
        """添加到铸造队列"""
        # 在实际实现中插入数据库
        pass
    
    def _update_certificate_mint_status(self, certificate_id: int, result: Dict[str, Any]):
        """更新证书铸造状态"""
        # 在实际实现中更新数据库
        pass
    
    def get_minting_statistics(self) -> Dict[str, Any]:
        """获取铸造统计信息"""
        return {
            'is_running': self.is_running,
            'auto_mint_enabled': self.minting_config['auto_mint_enabled'],
            'contract_address': self.sla_nft_contract_address,
            'total_minted': 0,  # 从数据库查询
            'pending_tasks': 0,  # 从数据库查询
            'failed_tasks': 0,  # 从数据库查询
            'last_mint_time': None  # 从数据库查询
        }

# 全局实例
sla_nft_minting_system = SLANFTMintingSystem()

# 导出
__all__ = ['SLANFTMintingSystem', 'sla_nft_minting_system']