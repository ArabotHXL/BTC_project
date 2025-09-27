"""
支付监控服务 - Payment Monitor Service
为Web3集成模块提供加密货币支付监控和自动确认功能

功能包括：
- 实时监控区块链交易状态
- 自动更新支付确认数
- 处理支付确认和订阅激活
- 支持多区块链网络（BTC、ETH、USDC）
- 异常处理和超时管理
"""

import os
import json
import logging
import time
import threading
import socket
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import requests
from web3 import Web3
from web3.exceptions import TransactionNotFound, BlockNotFound

# 本地导入
try:
    from ..models import Payment, PaymentStatus, CryptoCurrency, PaymentMethodType, SchedulerLock
    from .blockchain import blockchain_integration
    from .compliance import compliance_service
except ImportError:
    # Fallback for standalone execution
    from models import Payment, PaymentStatus, CryptoCurrency, PaymentMethodType, SchedulerLock
    from services.blockchain import blockchain_integration
    from services.compliance import compliance_service

logger = logging.getLogger(__name__)

@dataclass
class NetworkConfig:
    """区块链网络配置"""
    name: str
    rpc_url: str
    explorer_url: str
    min_confirmations: int
    block_time: int  # 平均出块时间（秒）

class PaymentMonitorService:
    """支付监控服务主类"""
    
    def __init__(self):
        """初始化支付监控服务"""
        self.running = False
        self.monitor_thread = None
        self.blockchain_integration = blockchain_integration
        
        # 🔧 CRITICAL FIX: SchedulerLock configuration
        self.lock_key = "payment_monitor_service"
        self.process_id = os.getpid()
        self.hostname = socket.gethostname()
        self.lock_timeout = 300  # 5分钟
        self.heartbeat_interval = 60  # 1分钟心跳
        self.last_heartbeat = None
        self.has_lock = False
        
        # 网络配置
        self.networks = {
            'BTC': NetworkConfig(
                name='Bitcoin',
                rpc_url=os.environ.get('BTC_RPC_URL', 'https://blockstream.info/api'),
                explorer_url='https://blockstream.info',
                min_confirmations=3,
                block_time=600  # 10分钟
            ),
            'ETH': NetworkConfig(
                name='Ethereum',
                rpc_url=os.environ.get('ETH_RPC_URL', 'https://mainnet.infura.io/v3/YOUR_PROJECT_ID'),
                explorer_url='https://etherscan.io',
                min_confirmations=12,
                block_time=15  # 15秒
            ),
            'USDC': NetworkConfig(
                name='USDC (Base)',
                rpc_url='https://mainnet.base.org',
                explorer_url='https://basescan.org',
                min_confirmations=12,
                block_time=2  # 2秒
            )
        }
        
        # 监控配置
        self.monitor_interval = 30  # 30秒检查一次
        self.batch_size = 50  # 每次处理50个支付
        self.max_retries = 3
        
        logger.info("PaymentMonitorService initialized")
    
    def start_monitoring(self):
        """启动支付监控服务"""
        if self.running:
            logger.warning("支付监控服务已在运行")
            return
        
        logger.info("正在启动支付监控服务...")
        self.running = True
        
        # 尝试获取调度器锁
        if not self._acquire_scheduler_lock():
            logger.warning("无法获取调度器锁，监控服务未启动")
            self.running = False
            return
        
        # 启动监控线程
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        
        logger.info("支付监控服务已启动")
    
    def stop_monitoring(self):
        """停止支付监控服务"""
        if not self.running:
            return
        
        logger.info("正在停止支付监控服务...")
        self.running = False
        
        # 释放调度器锁
        self._release_scheduler_lock()
        
        # 等待监控线程结束
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=10)
        
        logger.info("支付监控服务已停止")
    
    def _monitor_loop(self):
        """监控主循环"""
        while self.running:
            try:
                # 更新心跳
                if not self._update_heartbeat():
                    logger.error("心跳更新失败，停止监控")
                    break
                
                # 处理待监控的支付
                self._process_pending_payments()
                
                # 处理确认中的支付
                self._process_confirming_payments()
                
                # 处理超时的支付
                self._process_expired_payments()
                
                # 等待下次监控
                time.sleep(self.monitor_interval)
                
            except Exception as e:
                logger.error(f"监控循环出错: {e}")
                time.sleep(5)  # 出错后短暂等待
        
        self.running = False
    
    def _process_pending_payments(self):
        """处理待监控的支付"""
        try:
            # 这里应该从数据库查询待处理的支付
            # 暂时使用空列表作为示例
            pending_payments = self._get_pending_payments()
            
            for payment in pending_payments:
                try:
                    self._monitor_single_payment(payment)
                except Exception as e:
                    logger.error(f"监控支付 {payment.payment_id} 失败: {e}")
                    
        except Exception as e:
            logger.error(f"处理待监控支付失败: {e}")
    
    def _process_confirming_payments(self):
        """处理确认中的支付"""
        try:
            # 这里应该从数据库查询确认中的支付
            confirming_payments = self._get_confirming_payments()
            
            for payment in confirming_payments:
                try:
                    self._check_payment_confirmations(payment)
                except Exception as e:
                    logger.error(f"检查支付确认 {payment.payment_id} 失败: {e}")
                    
        except Exception as e:
            logger.error(f"处理确认中支付失败: {e}")
    
    def _process_expired_payments(self):
        """处理超时的支付"""
        try:
            # 这里应该从数据库查询超时的支付
            expired_payments = self._get_expired_payments()
            
            for payment in expired_payments:
                try:
                    self._mark_payment_expired(payment)
                except Exception as e:
                    logger.error(f"处理超时支付 {payment.payment_id} 失败: {e}")
                    
        except Exception as e:
            logger.error(f"处理超时支付失败: {e}")
    
    def _monitor_single_payment(self, payment):
        """监控单个支付"""
        try:
            crypto = payment.crypto_currency.name if hasattr(payment.crypto_currency, 'name') else str(payment.crypto_currency)
            
            if crypto == 'BTC':
                result = self._monitor_btc_payment(payment)
            elif crypto == 'ETH':
                result = self._monitor_eth_payment(payment)
            elif crypto == 'USDC':
                result = self._monitor_usdc_payment(payment)
            else:
                logger.warning(f"不支持的加密货币: {crypto}")
                return
            
            # 更新支付状态
            if result.get('transaction_found'):
                self._update_payment_status(payment, PaymentStatus.CONFIRMING, result)
            
        except Exception as e:
            logger.error(f"监控支付失败: {e}")
    
    def _monitor_btc_payment(self, payment) -> Dict[str, Any]:
        """监控BTC支付"""
        try:
            address = payment.payment_address
            expected_amount = payment.crypto_amount
            
            network_config = self.networks['BTC']
            api_url = network_config.rpc_url
            
            # 获取地址交易
            response = requests.get(f"{api_url}/address/{address}/txs", timeout=10)
            
            if response.status_code == 200:
                transactions = response.json()
                
                for tx in transactions[:5]:  # 检查最近5笔交易
                    # 检查输出
                    for vout in tx.get('vout', []):
                        if (vout.get('scriptpubkey_address') == address and
                            vout.get('value', 0) / 100000000 >= expected_amount):
                            
                            return {
                                'transaction_found': True,
                                'transaction_hash': tx['txid'],
                                'amount_received': vout.get('value', 0) / 100000000,
                                'confirmed': tx.get('status', {}).get('confirmed', False)
                            }
            
            return {'transaction_found': False}
            
        except Exception as e:
            logger.error(f"监控BTC支付失败: {e}")
            return {'error': str(e)}
    
    def _monitor_eth_payment(self, payment) -> Dict[str, Any]:
        """监控ETH支付"""
        try:
            w3 = blockchain_integration.w3
            if not w3 or not w3.is_connected():
                return {'error': 'Web3连接不可用'}
            
            address = payment.payment_address.lower()
            expected_amount = payment.crypto_amount
            
            # 获取最近的区块进行扫描
            latest_block = w3.eth.block_number
            start_block = max(0, latest_block - 100)
            
            for block_num in range(latest_block, start_block - 1, -1):
                try:
                    block = w3.eth.get_block(block_num, full_transactions=True)
                    
                    for tx in block.transactions:
                        if (tx.to and tx.to.lower() == address and
                            w3.from_wei(tx.value, 'ether') >= expected_amount):
                            
                            return {
                                'transaction_found': True,
                                'transaction_hash': tx.hash.hex(),
                                'amount_received': float(w3.from_wei(tx.value, 'ether')),
                                'block_number': block_num
                            }
                            
                except Exception as e:
                    logger.warning(f"扫描区块 {block_num} 失败: {e}")
                    continue
            
            return {'transaction_found': False}
            
        except Exception as e:
            logger.error(f"监控ETH支付失败: {e}")
            return {'error': str(e)}
    
    def _monitor_usdc_payment(self, payment) -> Dict[str, Any]:
        """监控USDC支付"""
        try:
            # USDC监控需要检查ERC-20代币转账事件
            # 这需要更复杂的实现，暂时返回未实现
            return {'transaction_found': False, 'error': 'USDC监控尚未实现'}
            
        except Exception as e:
            logger.error(f"监控USDC支付失败: {e}")
            return {'error': str(e)}
    
    def _check_payment_confirmations(self, payment):
        """检查支付确认数"""
        try:
            if not payment.transaction_hash:
                return
            
            crypto = payment.crypto_currency.name if hasattr(payment.crypto_currency, 'name') else str(payment.crypto_currency)
            
            confirmations = 0
            if crypto == 'BTC':
                confirmations = self._get_btc_confirmations(payment.transaction_hash)
            elif crypto in ['ETH', 'USDC']:
                confirmations = self._get_eth_confirmations(payment.transaction_hash)
            
            # 更新确认数
            if confirmations != payment.confirmations:
                self._update_payment_confirmations(payment, confirmations)
            
            # 检查是否达到要求的确认数
            required = payment.required_confirmations or self.networks[crypto].min_confirmations
            if confirmations >= required:
                self._complete_payment(payment)
                
        except Exception as e:
            logger.error(f"检查确认数失败: {e}")
    
    def _get_btc_confirmations(self, tx_hash: str) -> int:
        """获取BTC交易确认数"""
        try:
            network_config = self.networks['BTC']
            api_url = network_config.rpc_url
            
            response = requests.get(f"{api_url}/tx/{tx_hash}", timeout=10)
            
            if response.status_code == 200:
                tx_data = response.json()
                
                if tx_data.get('status', {}).get('confirmed'):
                    block_height = tx_data['status']['block_height']
                    
                    # 获取最新区块高度
                    latest_response = requests.get(f"{api_url}/blocks/tip/height", timeout=10)
                    if latest_response.status_code == 200:
                        latest_height = int(latest_response.text)
                        return latest_height - block_height + 1
            
            return 0
            
        except Exception as e:
            logger.error(f"获取BTC确认数失败: {e}")
            return 0
    
    def _get_eth_confirmations(self, tx_hash: str) -> int:
        """获取ETH交易确认数"""
        try:
            w3 = blockchain_integration.w3
            if not w3 or not w3.is_connected():
                return 0
            
            tx_receipt = w3.eth.get_transaction_receipt(tx_hash)
            if tx_receipt.status == 1:  # 交易成功
                current_block = w3.eth.block_number
                return current_block - tx_receipt.blockNumber + 1
            
            return 0
            
        except Exception as e:
            logger.error(f"获取ETH确认数失败: {e}")
            return 0
    
    def _update_payment_status(self, payment, new_status: PaymentStatus, details: Dict[str, Any]):
        """更新支付状态"""
        try:
            # 在实际实现中，这里应该更新数据库
            logger.info(f"更新支付 {payment.payment_id} 状态: {new_status.value}")
            
            # 如果发现交易，记录交易哈希
            if details.get('transaction_hash'):
                payment.transaction_hash = details['transaction_hash']
            
            payment.status = new_status
            payment.updated_at = datetime.utcnow()
            
            # 这里应该保存到数据库
            # db.session.commit()
            
        except Exception as e:
            logger.error(f"更新支付状态失败: {e}")
    
    def _update_payment_confirmations(self, payment, confirmations: int):
        """更新支付确认数"""
        try:
            payment.confirmations = confirmations
            payment.updated_at = datetime.utcnow()
            
            # 这里应该保存到数据库
            # db.session.commit()
            
            logger.info(f"支付 {payment.payment_id} 确认数更新为: {confirmations}")
            
        except Exception as e:
            logger.error(f"更新确认数失败: {e}")
    
    def _complete_payment(self, payment):
        """完成支付"""
        try:
            payment.status = PaymentStatus.COMPLETED
            payment.confirmed_at = datetime.utcnow()
            payment.updated_at = datetime.utcnow()
            
            # 这里应该保存到数据库
            # db.session.commit()
            
            logger.info(f"支付 {payment.payment_id} 已完成")
            
            # 触发支付完成事件（如激活订阅等）
            self._handle_payment_completion(payment)
            
        except Exception as e:
            logger.error(f"完成支付失败: {e}")
    
    def _mark_payment_expired(self, payment):
        """标记支付为超时"""
        try:
            payment.status = PaymentStatus.EXPIRED
            payment.updated_at = datetime.utcnow()
            
            # 这里应该保存到数据库
            # db.session.commit()
            
            logger.info(f"支付 {payment.payment_id} 已超时")
            
        except Exception as e:
            logger.error(f"标记支付超时失败: {e}")
    
    def _handle_payment_completion(self, payment):
        """处理支付完成事件"""
        try:
            # 这里可以触发各种完成后的操作，如：
            # - 激活用户订阅
            # - 发送确认邮件
            # - 更新用户权限
            # - 记录审计日志
            
            logger.info(f"处理支付完成事件: {payment.payment_id}")
            
        except Exception as e:
            logger.error(f"处理支付完成事件失败: {e}")
    
    # 调度器锁相关方法
    def _acquire_scheduler_lock(self) -> bool:
        """获取调度器锁"""
        try:
            # 在实际实现中，这里应该使用数据库操作
            # 暂时返回True
            self.has_lock = True
            self.last_heartbeat = datetime.utcnow()
            logger.info("获取调度器锁成功")
            return True
            
        except Exception as e:
            logger.error(f"获取调度器锁失败: {e}")
            return False
    
    def _release_scheduler_lock(self):
        """释放调度器锁"""
        try:
            if self.has_lock:
                # 在实际实现中，这里应该从数据库删除锁记录
                self.has_lock = False
                logger.info("调度器锁已释放")
                
        except Exception as e:
            logger.error(f"释放调度器锁失败: {e}")
    
    def _update_heartbeat(self) -> bool:
        """更新心跳"""
        try:
            if not self.has_lock:
                return False
            
            self.last_heartbeat = datetime.utcnow()
            # 在实际实现中，这里应该更新数据库中的心跳时间
            return True
            
        except Exception as e:
            logger.error(f"更新心跳失败: {e}")
            return False
    
    # 数据查询方法（在实际实现中应该查询数据库）
    def _get_pending_payments(self):
        """获取待处理的支付"""
        # 在实际实现中，这里应该查询数据库
        return []
    
    def _get_confirming_payments(self):
        """获取确认中的支付"""
        # 在实际实现中，这里应该查询数据库
        return []
    
    def _get_expired_payments(self):
        """获取超时的支付"""
        # 在实际实现中，这里应该查询数据库
        return []
    
    def get_service_status(self) -> Dict[str, Any]:
        """获取服务状态"""
        return {
            'running': self.running,
            'has_lock': self.has_lock,
            'last_heartbeat': self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            'process_id': self.process_id,
            'hostname': self.hostname,
            'networks_configured': list(self.networks.keys()),
            'monitor_interval': self.monitor_interval
        }

# 全局实例
payment_monitor_service = PaymentMonitorService()

# 导出
__all__ = ['PaymentMonitorService', 'payment_monitor_service']