"""
支付监控服务 - Payment Monitor Service
为BTC Mining Calculator平台提供加密货币支付监控和自动确认功能

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
import asyncio
import socket
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import requests
from flask import current_app

# 区块链相关导入
from web3 import Web3
from web3.exceptions import TransactionNotFound, BlockNotFound
import bitcoinlib
from bitcoinlib.services.services import ServiceError

# 本地导入
from models_subscription import (
    Payment, PaymentStatus, CryptoCurrency, PaymentMethodType,
    UserSubscription, SubscriptionStatus
)
from models import SchedulerLock
from compliance_service import compliance_service
from db import db
from blockchain_integration import BlockchainIntegration

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
        self.blockchain_integration = None
        
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
                name='USDC (Base Sepolia)',
                rpc_url=os.environ.get('BASE_RPC_URL', 'https://sepolia.base.org'),
                explorer_url='https://sepolia-explorer.base.org',
                min_confirmations=3,
                block_time=2  # Base网络约2秒出块
            )
        }
        
        # 监控配置
        self.check_interval = int(os.environ.get('PAYMENT_CHECK_INTERVAL', '30'))  # 30秒
        self.max_retries = 3
        self.retry_delay = 5
        
        # Web3连接缓存
        self.web3_connections = {}
        
        # 初始化区块链集成
        try:
            self.blockchain_integration = BlockchainIntegration()
        except Exception as e:
            logger.warning(f"区块链集成初始化失败，将使用外部API: {e}")
    
    def start_monitoring(self):
        """启动支付监控服务 - 使用SchedulerLock确保单实例"""
        if self.running:
            logger.warning("支付监控服务已在运行")
            return
        
        # 🔧 CRITICAL FIX: 尝试获取SchedulerLock
        if not self._acquire_scheduler_lock():
            logger.info(f"无法获取调度器锁，其他实例正在运行。PID={self.process_id}@{self.hostname}")
            return
        
        self.running = True
        self.has_lock = True
        self.last_heartbeat = datetime.utcnow()
        
        # 启动监控线程
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        
        # 启动心跳线程
        self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self.heartbeat_thread.start()
        
        logger.info(f"🚀 支付监控服务已启动 (PID={self.process_id}@{self.hostname})")
    
    def stop_monitoring(self):
        """停止支付监控服务 - 释放SchedulerLock"""
        self.running = False
        
        # 等待线程结束
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=10)
        
        if hasattr(self, 'heartbeat_thread') and self.heartbeat_thread.is_alive():
            self.heartbeat_thread.join(timeout=5)
        
        # 🔧 CRITICAL FIX: 释放SchedulerLock
        if self.has_lock:
            self._release_scheduler_lock()
            self.has_lock = False
        
        logger.info(f"🛑 支付监控服务已停止 (PID={self.process_id}@{self.hostname})")
    
    def _monitor_loop(self):
        """主监控循环 - 增强版本带生命周期管理"""
        logger.info(f"📊 开始支付监控循环 (PID={self.process_id})")
        
        while self.running:
            try:
                # 🔧 CRITICAL FIX: 检查锁状态
                if not self.has_lock:
                    logger.warning("失去调度器锁，停止监控")
                    break
                
                # 执行支付检查
                self._check_pending_payments()
                
                # 检查服务健康状态
                self._health_check()
                
                time.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"监控循环异常: {e}")
                time.sleep(self.check_interval)
        
        logger.info(f"📊 支付监控循环结束 (PID={self.process_id})")
    
    def _check_pending_payments(self):
        """检查待确认的支付"""
        try:
            # 🔧 CRITICAL FIX: 修复is_crypto_payment字段引用
            # is_crypto_payment是property，不是数据库字段
            pending_payments = Payment.query.filter(
                Payment.status.in_([PaymentStatus.PENDING, PaymentStatus.CONFIRMING]),
                Payment.payment_method_type == PaymentMethodType.CRYPTO
            ).all()
            
            logger.info(f"检查 {len(pending_payments)} 个待确认支付")
            
            for payment in pending_payments:
                try:
                    self._process_payment(payment)
                except Exception as e:
                    logger.error(f"处理支付 {payment.id} 时出错: {e}")
                    
        except Exception as e:
            logger.error(f"获取待确认支付失败: {e}")
    
    def _process_payment(self, payment: Payment):
        """处理单个支付"""
        crypto = payment.crypto_currency
        if not crypto or crypto not in self.networks:
            logger.warning(f"不支持的加密货币: {crypto}")
            return
        
        # 检查支付是否过期
        if payment.expires_at and datetime.utcnow() > payment.expires_at:
            self._handle_expired_payment(payment)
            return
        
        # 根据加密货币类型检查交易状态
        if crypto == 'BTC':
            self._check_btc_payment(payment)
        elif crypto in ['ETH', 'USDC']:
            self._check_eth_payment(payment)
        else:
            logger.warning(f"暂不支持的加密货币监控: {crypto}")
    
    def _check_btc_payment(self, payment: Payment):
        """检查BTC支付状态"""
        try:
            if not payment.transaction_hash:
                # 没有交易哈希，检查地址是否收到支付
                tx_hash = self._find_btc_transaction(payment)
                if tx_hash:
                    payment.transaction_hash = tx_hash
                    payment.status = PaymentStatus.CONFIRMING
                    db.session.commit()
                    logger.info(f"发现BTC交易: {tx_hash}")
                return
            
            # 已有交易哈希，检查确认数
            confirmations = self._get_btc_confirmations(payment.transaction_hash)
            if confirmations is not None:
                payment.confirmations = confirmations
                
                if confirmations >= payment.required_confirmations:
                    self._confirm_payment(payment)
                else:
                    payment.status = PaymentStatus.CONFIRMING
                
                db.session.commit()
                logger.info(f"BTC支付 {payment.id} 确认数: {confirmations}/{payment.required_confirmations}")
                
        except Exception as e:
            logger.error(f"检查BTC支付失败: {e}")
    
    def _check_eth_payment(self, payment: Payment):
        """检查ETH/USDC支付状态"""
        try:
            w3 = self._get_web3_connection('ETH')
            if not w3:
                logger.error("无法连接到以太坊网络")
                return
            
            if not payment.transaction_hash:
                # 检查地址是否收到支付
                if payment.crypto_currency == 'ETH':
                    tx_hash = self._find_eth_transaction(payment, w3)
                else:  # USDC
                    tx_hash = self._find_usdc_transaction(payment, w3)
                
                if tx_hash:
                    payment.transaction_hash = tx_hash
                    payment.status = PaymentStatus.CONFIRMING
                    db.session.commit()
                    logger.info(f"发现{payment.crypto_currency}交易: {tx_hash}")
                return
            
            # 检查交易确认数
            try:
                tx = w3.eth.get_transaction(payment.transaction_hash)
                tx_receipt = w3.eth.get_transaction_receipt(payment.transaction_hash)
                
                if tx_receipt.status == 1:  # 交易成功
                    current_block = w3.eth.block_number
                    confirmations = current_block - tx_receipt.blockNumber + 1
                    
                    payment.confirmations = confirmations
                    payment.block_number = tx_receipt.blockNumber
                    
                    if confirmations >= payment.required_confirmations:
                        self._confirm_payment(payment)
                    else:
                        payment.status = PaymentStatus.CONFIRMING
                    
                    db.session.commit()
                    logger.info(f"{payment.crypto_currency}支付 {payment.id} 确认数: {confirmations}/{payment.required_confirmations}")
                else:
                    # 交易失败
                    payment.status = PaymentStatus.FAILED
                    db.session.commit()
                    logger.warning(f"交易失败: {payment.transaction_hash}")
                    
            except (TransactionNotFound, BlockNotFound):
                logger.warning(f"交易未找到: {payment.transaction_hash}")
                
        except Exception as e:
            logger.error(f"检查{payment.crypto_currency}支付失败: {e}")
    
    def _find_btc_transaction(self, payment: Payment) -> Optional[str]:
        """查找BTC交易"""
        try:
            # 使用BlockStream API查找交易
            address = payment.payment_address
            url = f"https://blockstream.info/api/address/{address}/txs"
            
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                transactions = response.json()
                
                for tx in transactions:
                    # 检查输出是否包含目标地址和金额
                    for output in tx.get('vout', []):
                        if (output.get('scriptpubkey_address') == address and
                            output.get('value', 0) >= payment.amount * 100000000):  # 转换为satoshi
                            return tx['txid']
            
        except Exception as e:
            logger.error(f"查找BTC交易失败: {e}")
        
        return None
    
    def _get_btc_confirmations(self, tx_hash: str) -> Optional[int]:
        """获取BTC交易确认数"""
        try:
            url = f"https://blockstream.info/api/tx/{tx_hash}"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                tx_data = response.json()
                if tx_data.get('status', {}).get('confirmed'):
                    # 获取当前最新区块高度
                    latest_url = "https://blockstream.info/api/blocks/tip/height"
                    latest_response = requests.get(latest_url, timeout=10)
                    
                    if latest_response.status_code == 200:
                        latest_height = int(latest_response.text)
                        tx_height = tx_data['status']['block_height']
                        return latest_height - tx_height + 1
                else:
                    return 0  # 未确认
            
        except Exception as e:
            logger.error(f"获取BTC确认数失败: {e}")
        
        return None
    
    def _get_web3_connection(self, network: str) -> Optional[Web3]:
        """获取Web3连接"""
        if network in self.web3_connections:
            return self.web3_connections[network]
        
        try:
            if self.blockchain_integration and self.blockchain_integration.w3:
                # 使用现有的区块链集成
                self.web3_connections[network] = self.blockchain_integration.w3
                return self.blockchain_integration.w3
            else:
                # 创建新连接
                rpc_url = self.networks[network].rpc_url
                w3 = Web3(Web3.HTTPProvider(rpc_url))
                
                if w3.is_connected():
                    self.web3_connections[network] = w3
                    return w3
                else:
                    logger.error(f"无法连接到{network}网络: {rpc_url}")
                    
        except Exception as e:
            logger.error(f"创建{network}连接失败: {e}")
        
        return None
    
    def _find_eth_transaction(self, payment: Payment, w3: Web3) -> Optional[str]:
        """查找ETH交易"""
        try:
            # 获取最近的区块
            latest_block = w3.eth.block_number
            start_block = max(0, latest_block - 100)  # 检查最近100个区块
            
            for block_num in range(latest_block, start_block - 1, -1):
                block = w3.eth.get_block(block_num, full_transactions=True)
                
                for tx in block.transactions:
                    if (tx.to and tx.to.lower() == payment.payment_address.lower() and
                        w3.from_wei(tx.value, 'ether') >= payment.amount):
                        return tx.hash.hex()
                        
        except Exception as e:
            logger.error(f"查找ETH交易失败: {e}")
        
        return None
    
    def _find_usdc_transaction(self, payment: Payment, w3: Web3) -> Optional[str]:
        """查找USDC交易"""
        try:
            # USDC合约地址 (主网)
            usdc_contract_address = "0xA0b86a33E6417c0C85c5A67eB0B1dD15e2119c67"  # 示例地址，需要替换为实际地址
            
            # 这里需要实现ERC-20代币转账监控
            # 由于复杂性，暂时返回None，实际实现需要解析合约事件
            logger.info("USDC交易监控需要进一步实现")
            
        except Exception as e:
            logger.error(f"查找USDC交易失败: {e}")
        
        return None
    
    def _confirm_payment(self, payment: Payment):
        """确认支付并激活订阅 - 🔧 CRITICAL FIX: 添加合规检查"""
        try:
            # 🔧 CRITICAL FIX: 执行合规检查在激活订阅前
            logger.info(f"开始合规检查: 支付={payment.id}")
            compliance_passed, compliance_details = compliance_service.validate_payment_compliance(payment)
            
            if not compliance_passed:
                # 合规检查未通过，标记为需要审核
                payment.status = PaymentStatus.FAILED
                payment.compliance_notes = f"合规检查失败: {compliance_details.get('error', 'Unknown error')}"
                payment.manual_review_required = True
                
                if compliance_details.get('requires_manual_review'):
                    logger.warning(f"支付 {payment.id} 需要人工审核: {compliance_details}")
                else:
                    logger.error(f"支付 {payment.id} 合规检查失败: {compliance_details}")
                
                db.session.commit()
                return
            
            # 更新支付状态
            payment.status = PaymentStatus.COMPLETED
            payment.confirmed_at = datetime.utcnow()
            payment.payment_date = payment.confirmed_at
            
            # 激活用户订阅（仅在合规检查通过后）
            subscription = payment.subscription
            if subscription:
                subscription.status = SubscriptionStatus.ACTIVE
                subscription.confirmed_at = payment.confirmed_at
                
                # 设置订阅期限
                if subscription.plan:
                    if hasattr(subscription, 'billing_cycle') and subscription.billing_cycle == 'yearly':
                        subscription.expires_at = subscription.started_at + timedelta(days=365)
                    else:
                        subscription.expires_at = subscription.started_at + timedelta(days=30)
                
                subscription.auto_renew = True
            
            db.session.commit()
            
            logger.info(f"✅ 支付 {payment.id} 已确认并通过合规检查，订阅 {subscription.id if subscription else 'N/A'} 已激活")
            
            # 发送确认通知（可选）
            self._send_payment_confirmation(payment)
            
        except Exception as e:
            logger.error(f"确认支付失败: {e}")
            db.session.rollback()
            raise
    
    def _handle_expired_payment(self, payment: Payment):
        """处理过期支付"""
        try:
            payment.status = PaymentStatus.EXPIRED
            
            # 取消相关订阅
            subscription = payment.subscription
            if subscription and subscription.status == SubscriptionStatus.PENDING:
                subscription.status = SubscriptionStatus.CANCELLED
                subscription.cancelled_at = datetime.utcnow()
            
            db.session.commit()
            
            logger.info(f"支付 {payment.id} 已过期")
            
        except Exception as e:
            logger.error(f"处理过期支付失败: {e}")
            db.session.rollback()
    
    def _send_payment_confirmation(self, payment: Payment):
        """发送支付确认通知（可选实现）"""
        try:
            # 这里可以集成邮件服务或其他通知方式
            logger.info(f"应发送支付确认通知给用户，支付ID: {payment.id}")
            
        except Exception as e:
            logger.error(f"发送支付确认通知失败: {e}")
    
    def check_payment_status(self, payment_id: int) -> Dict[str, Any]:
        """手动检查单个支付状态"""
        try:
            payment = Payment.query.get(payment_id)
            if not payment:
                return {'success': False, 'error': '支付记录不存在'}
            
            if payment.status in [PaymentStatus.PENDING, PaymentStatus.CONFIRMING]:
                old_status = payment.status
                old_confirmations = payment.confirmations
                
                self._process_payment(payment)
                
                # 检查是否有更新
                updated = (payment.status != old_status or 
                          payment.confirmations != old_confirmations)
                
                return {
                    'success': True,
                    'payment': payment.to_dict(),
                    'status_updated': updated
                }
            else:
                return {
                    'success': True,
                    'payment': payment.to_dict(),
                    'status_updated': False
                }
                
        except Exception as e:
            logger.error(f"检查支付状态失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_network_status(self) -> Dict[str, Any]:
        """获取网络状态信息"""
        status = {}
        
        for crypto, config in self.networks.items():
            try:
                if crypto == 'BTC':
                    # 检查BTC网络状态
                    response = requests.get("https://blockstream.info/api/blocks/tip/height", timeout=5)
                    if response.status_code == 200:
                        status[crypto] = {
                            'connected': True,
                            'latest_block': int(response.text),
                            'network': config.name
                        }
                    else:
                        status[crypto] = {'connected': False, 'error': '无法获取区块高度'}
                        
                elif crypto in ['ETH', 'USDC']:
                    w3 = self._get_web3_connection(crypto)
                    if w3 and w3.is_connected():
                        status[crypto] = {
                            'connected': True,
                            'latest_block': w3.eth.block_number,
                            'network': config.name
                        }
                    else:
                        status[crypto] = {'connected': False, 'error': '无法连接Web3'}
                        
            except Exception as e:
                status[crypto] = {'connected': False, 'error': str(e)}
        
        return {
            'service_running': self.running,
            'networks': status,
            'check_interval': self.check_interval
        }
    
    # 🔧 CRITICAL FIX: SchedulerLock methods for single instance enforcement
    def _acquire_scheduler_lock(self) -> bool:
        """获取调度器锁"""
        try:
            worker_info = json.dumps({
                'process_id': self.process_id,
                'hostname': self.hostname,
                'start_time': datetime.utcnow().isoformat(),
                'service_type': 'payment_monitor'
            })
            
            return SchedulerLock.acquire_lock(
                lock_key=self.lock_key,
                process_id=self.process_id,
                hostname=self.hostname,
                timeout_seconds=self.lock_timeout,
                worker_info=worker_info
            )
        except Exception as e:
            logger.error(f"获取调度器锁失败: {e}")
            return False
    
    def _release_scheduler_lock(self) -> bool:
        """释放调度器锁"""
        try:
            return SchedulerLock.release_lock(self.lock_key, self.process_id)
        except Exception as e:
            logger.error(f"释放调度器锁失败: {e}")
            return False
    
    def _heartbeat_loop(self):
        """心跳循环 - 维持锁的有效性"""
        logger.info(f"💓 启动心跳循环 (PID={self.process_id})")
        
        while self.running and self.has_lock:
            try:
                time.sleep(self.heartbeat_interval)
                
                if not self.running:
                    break
                
                # 更新心跳
                current_time = datetime.utcnow()
                self.last_heartbeat = current_time
                
                # 刷新锁
                try:
                    active_lock = SchedulerLock.get_active_lock(self.lock_key)
                    if active_lock and active_lock.process_id == self.process_id:
                        active_lock.refresh_lock(self.lock_timeout)
                        db.session.commit()
                        logger.debug(f"💓 心跳更新成功 (PID={self.process_id})")
                    else:
                        logger.warning("失去调度器锁，停止心跳")
                        self.has_lock = False
                        break
                except Exception as e:
                    logger.error(f"心跳更新失败: {e}")
                    self.has_lock = False
                    break
                    
            except Exception as e:
                logger.error(f"心跳循环异常: {e}")
                time.sleep(5)  # 等待5秒后重试
        
        logger.info(f"💓 心跳循环结束 (PID={self.process_id})")
    
    def _health_check(self):
        """健康检查"""
        try:
            # 检查数据库连接
            db.session.execute('SELECT 1')
            
            # 检查锁状态
            if self.has_lock:
                active_lock = SchedulerLock.get_active_lock(self.lock_key)
                if not active_lock or active_lock.process_id != self.process_id:
                    logger.warning("检测到锁状态异常，停止监控")
                    self.has_lock = False
                    self.running = False
            
            # 记录服务状态
            if hasattr(self, '_last_health_check'):
                elapsed = datetime.utcnow() - self._last_health_check
                if elapsed.total_seconds() > 300:  # 每5分钟记录一次
                    logger.info(f"🏥 服务健康检查: PID={self.process_id}, 锁状态={self.has_lock}")
                    self._last_health_check = datetime.utcnow()
            else:
                self._last_health_check = datetime.utcnow()
                
        except Exception as e:
            logger.error(f"健康检查失败: {e}")

# 全局服务实例
payment_monitor = PaymentMonitorService()

def start_payment_monitor():
    """启动支付监控服务"""
    try:
        payment_monitor.start_monitoring()
        logger.info("支付监控服务启动成功")
    except Exception as e:
        logger.error(f"启动支付监控服务失败: {e}")

def stop_payment_monitor():
    """停止支付监控服务"""
    try:
        payment_monitor.stop_monitoring()
        logger.info("支付监控服务停止成功")
    except Exception as e:
        logger.error(f"停止支付监控服务失败: {e}")

# 导出
__all__ = ['PaymentMonitorService', 'payment_monitor', 'start_payment_monitor', 'stop_payment_monitor']