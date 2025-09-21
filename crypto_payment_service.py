"""
加密货币支付服务
为BTC Mining Calculator平台提供加密货币支付集成

支持的功能：
- 生成支付地址和二维码
- 监控链上交易状态
- 处理多种加密货币（BTC、ETH、USDC）
- 与现有Web3基础设施集成
- 安全和合规检查
"""

import os
import json
import logging
import hashlib
import qrcode
import io
import base64
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import requests
from web3 import Web3
from eth_account import Account

# 本地导入
from models_subscription import (
    Payment, UserSubscription, SubscriptionPlan, 
    PaymentStatus, PaymentMethodType, CryptoCurrency
)
from blockchain_integration import BlockchainIntegration
from compliance_service import compliance_service
from db import db

logger = logging.getLogger(__name__)

class CryptoPaymentService:
    """加密货币支付服务主类"""
    
    def __init__(self):
        """初始化加密货币支付服务"""
        self.blockchain_integration = BlockchainIntegration()
        self.w3 = self.blockchain_integration.w3
        
        # 支付配置
        self.payment_timeout_hours = 24  # 支付超时时间（小时）
        self.confirmation_requirements = {
            'BTC': 3,    # BTC需要3个确认
            'ETH': 12,   # ETH需要12个确认
            'USDC': 12   # USDC（基于ETH）需要12个确认
        }
        
        # API配置
        self.btc_api_url = "https://mempool.space/api"
        self.eth_api_url = "https://api.etherscan.io/api"
        self.etherscan_api_key = os.environ.get('ETHERSCAN_API_KEY')
        
        # 收款钱包地址（从环境变量获取）
        self.wallet_addresses = {
            'BTC': os.environ.get('BTC_WALLET_ADDRESS'),
            'ETH': os.environ.get('ETH_WALLET_ADDRESS'),
            'USDC': os.environ.get('USDC_WALLET_ADDRESS')  # USDC合约地址
        }
        
        # 🔧 CRITICAL FIX: 正确的USDC合约地址映射（防止资金损失）
        self.usdc_contract_addresses = {
            'base_mainnet': '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913',  # Base Mainnet USDC
            'base_sepolia': '0x036CbD53842c5426634e7929541eC2318f3dCF7e'   # Base Sepolia USDC
        }
        self.usdc_decimals = 6
        
        # 网络环境配置
        self.is_testnet = os.environ.get('NETWORK_ENV', 'testnet') == 'testnet'
        
        logger.info("CryptoPaymentService initialized")
    
    def create_payment(self, subscription_id: int, amount: float, currency: str, 
                      crypto_currency: str) -> Optional[Payment]:
        """
        创建新的加密货币支付记录
        
        Args:
            subscription_id: 订阅ID
            amount: 支付金额
            currency: 法币类型（USD等）
            crypto_currency: 加密货币类型（BTC、ETH、USDC）
            
        Returns:
            Payment对象或None
        """
        try:
            # 验证加密货币类型
            if crypto_currency not in ['BTC', 'ETH', 'USDC']:
                raise ValueError(f"不支持的加密货币: {crypto_currency}")
            
            # 获取当前汇率并计算加密货币金额
            crypto_amount = self._convert_to_crypto_amount(amount, currency, crypto_currency)
            if not crypto_amount:
                raise ValueError(f"无法获取{crypto_currency}汇率")
            
            # 生成支付地址
            payment_address = self._generate_payment_address(crypto_currency)
            if not payment_address:
                raise ValueError(f"无法生成{crypto_currency}支付地址")
            
            # 计算支付超时时间
            expires_at = datetime.utcnow() + timedelta(hours=self.payment_timeout_hours)
            
            # 创建支付记录
            payment = Payment(
                subscription_id=subscription_id,
                amount=crypto_amount,
                currency=crypto_currency,
                status=PaymentStatus.PENDING,
                payment_method_type=PaymentMethodType.CRYPTO,
                crypto_currency=CryptoCurrency[crypto_currency],
                wallet_address=self.wallet_addresses.get(crypto_currency),
                payment_address=payment_address,
                blockchain_network=self._get_blockchain_network(crypto_currency),
                confirmations=0,
                required_confirmations=self.confirmation_requirements.get(crypto_currency, 3),
                expires_at=expires_at,
                aml_status='pending',
                kyc_status='pending',
                compliance_score=None,
                compliance_checked_at=None,
                manual_review_required=False
            )
            
            # 保存到数据库
            db.session.add(payment)
            db.session.commit()
            
            logger.info(f"创建{crypto_currency}支付: {payment.id}, 金额: {crypto_amount}")
            return payment
            
        except Exception as e:
            logger.error(f"创建支付失败: {e}")
            db.session.rollback()
            return None
    
    def generate_payment_qr_code(self, payment: Payment) -> Optional[str]:
        """
        生成支付二维码
        
        Args:
            payment: 支付对象
            
        Returns:
            Base64编码的二维码图片字符串
        """
        try:
            if not payment.payment_address or not payment.amount:
                return None
            
            # 构建支付URI
            if payment.crypto_currency == CryptoCurrency.BTC:
                # BTC URI格式: bitcoin:address?amount=amount
                payment_uri = f"bitcoin:{payment.payment_address}?amount={payment.amount}"
            elif payment.crypto_currency == CryptoCurrency.ETH:
                # ETH URI格式: ethereum:address?value=amount
                wei_amount = int(payment.amount * 10**18)  # 转换为Wei
                payment_uri = f"ethereum:{payment.payment_address}?value={wei_amount}"
            elif payment.crypto_currency == CryptoCurrency.USDC:
                # 🔧 CRITICAL FIX: 使用正确的USDC合约地址
                network = self._get_blockchain_network('USDC')
                usdc_contract = self._get_usdc_contract_address(network)
                if not usdc_contract:
                    logger.error(f"无法获取{network}的USDC合约地址")
                    return None
                
                usdc_amount = int(payment.amount * 10**self.usdc_decimals)
                payment_uri = f"ethereum:{usdc_contract}/transfer?address={payment.payment_address}&uint256={usdc_amount}"
            else:
                return None
            
            # 生成二维码
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(payment_uri)
            qr.make(fit=True)
            
            # 转换为图片
            img = qr.make_image(fill_color="black", back_color="white")
            
            # 转换为Base64字符串
            img_buffer = io.BytesIO()
            img.save(img_buffer, format='PNG')
            img_buffer.seek(0)
            img_b64 = base64.b64encode(img_buffer.getvalue()).decode()
            
            return img_b64
            
        except Exception as e:
            logger.error(f"生成二维码失败: {e}")
            return None
    
    def check_payment_status(self, payment: Payment) -> bool:
        """
        检查支付状态
        
        Args:
            payment: 支付对象
            
        Returns:
            是否有状态更新
        """
        try:
            if payment.status in [PaymentStatus.COMPLETED, PaymentStatus.FAILED, PaymentStatus.CANCELLED]:
                return False
            
            # 检查是否过期
            if payment.is_expired:
                payment.status = PaymentStatus.EXPIRED
                db.session.commit()
                logger.info(f"支付已过期: {payment.id}")
                return True
            
            # 根据加密货币类型检查链上状态
            if payment.crypto_currency == CryptoCurrency.BTC:
                return self._check_btc_payment(payment)
            elif payment.crypto_currency in [CryptoCurrency.ETH, CryptoCurrency.USDC]:
                return self._check_eth_payment(payment)
            
            return False
            
        except Exception as e:
            logger.error(f"检查支付状态失败: {e}")
            return False
    
    def process_confirmed_payment(self, payment: Payment) -> bool:
        """
        处理已确认的支付
        
        Args:
            payment: 支付对象
            
        Returns:
            处理是否成功
        """
        try:
            if payment.status != PaymentStatus.CONFIRMING:
                return False
            
            # 更新支付状态
            payment.status = PaymentStatus.COMPLETED
            payment.confirmed_at = datetime.utcnow()
            payment.payment_date = datetime.utcnow()
            
            # 更新订阅状态
            subscription = payment.subscription
            if subscription:
                subscription.status = 'active'
                
                # 计算新的到期时间
                if subscription.plan:
                    if payment.currency == 'monthly':
                        new_expires_at = datetime.utcnow() + timedelta(days=30)
                    else:  # yearly
                        new_expires_at = datetime.utcnow() + timedelta(days=365)
                    
                    subscription.expires_at = new_expires_at
                    subscription.started_at = datetime.utcnow()
            
            # 记录审计日志
            self._log_payment_event(payment, "PAYMENT_CONFIRMED")
            
            db.session.commit()
            logger.info(f"支付确认完成: {payment.id}")
            
            return True
            
        except Exception as e:
            logger.error(f"处理确认支付失败: {e}")
            db.session.rollback()
            return False
    
    def _convert_to_crypto_amount(self, fiat_amount: float, fiat_currency: str, 
                                 crypto_currency: str) -> Optional[float]:
        """
        将法币金额转换为加密货币金额
        
        Args:
            fiat_amount: 法币金额
            fiat_currency: 法币类型
            crypto_currency: 加密货币类型
            
        Returns:
            加密货币金额
        """
        try:
            # 这里应该调用实时汇率API
            # 暂时使用模拟汇率（生产环境需要实际API）
            rates = {
                'BTC': 45000.0,  # 1 BTC = 45000 USD
                'ETH': 3000.0,   # 1 ETH = 3000 USD  
                'USDC': 1.0      # 1 USDC = 1 USD
            }
            
            if crypto_currency not in rates:
                return None
            
            crypto_amount = fiat_amount / rates[crypto_currency]
            return round(crypto_amount, 8)  # 精确到8位小数
            
        except Exception as e:
            logger.error(f"汇率转换失败: {e}")
            return None
    
    def _generate_payment_address(self, crypto_currency: str) -> Optional[str]:
        """
        生成支付地址
        
        Args:
            crypto_currency: 加密货币类型
            
        Returns:
            支付地址
        """
        try:
            # 生产环境中，这里应该：
            # 1. 为BTC生成新的HD钱包地址
            # 2. 为ETH生成新的合约地址或使用多重签名
            # 3. 确保私钥安全管理
            
            # 开发模式：返回配置的钱包地址
            return self.wallet_addresses.get(crypto_currency)
            
        except Exception as e:
            logger.error(f"生成支付地址失败: {e}")
            return None
    
    def _get_blockchain_network(self, crypto_currency: str) -> str:
        """获取区块链网络名称"""
        networks = {
            'BTC': 'bitcoin',
            'ETH': 'ethereum',
            'USDC': 'base_sepolia' if self.is_testnet else 'base_mainnet'  # 🔧 FIXED: 正确的Base网络
        }
        return networks.get(crypto_currency, 'unknown')
    
    def _get_usdc_contract_address(self, network: str = None) -> str:
        """获取正确的USDC合约地址"""
        if network is None:
            network = 'base_sepolia' if self.is_testnet else 'base_mainnet'
        
        return self.usdc_contract_addresses.get(network)
    
    def _validate_usdc_address(self, address: str, network: str) -> bool:
        """验证USDC合约地址是否正确"""
        expected_address = self.usdc_contract_addresses.get(network)
        return address.lower() == expected_address.lower() if expected_address else False
    
    def _check_btc_payment(self, payment: Payment) -> bool:
        """检查BTC支付状态"""
        try:
            if not payment.payment_address:
                return False
            
            # 调用Bitcoin API检查地址余额和交易
            url = f"{self.btc_api_url}/address/{payment.payment_address}"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # 检查是否有足够的资金
                received_amount = data.get('chain_stats', {}).get('funded_txo_sum', 0) / 100000000  # 转换为BTC
                
                if received_amount >= payment.amount:
                    # 检查确认数
                    confirmations = self._get_btc_confirmations(payment.payment_address)
                    payment.confirmations = confirmations
                    
                    if confirmations >= payment.required_confirmations:
                        payment.status = PaymentStatus.CONFIRMING
                    else:
                        payment.status = PaymentStatus.CONFIRMING
                    
                    db.session.commit()
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"检查BTC支付失败: {e}")
            return False
    
    def _check_eth_payment(self, payment: Payment) -> bool:
        """检查ETH/USDC支付状态"""
        try:
            if not payment.payment_address or not self.w3:
                return False
            
            # 检查ETH余额
            if payment.crypto_currency == CryptoCurrency.ETH:
                balance = self.w3.eth.get_balance(payment.payment_address)
                eth_amount = self.w3.from_wei(balance, 'ether')
                
                if float(eth_amount) >= payment.amount:
                    # 获取最新区块号检查确认数
                    latest_block = self.w3.eth.block_number
                    # 这里需要实现具体的交易查找逻辑
                    payment.confirmations = 12  # 模拟确认数
                    payment.status = PaymentStatus.CONFIRMING
                    db.session.commit()
                    return True
            
            # 检查USDC余额（需要ERC20合约调用）
            elif payment.crypto_currency == CryptoCurrency.USDC:
                # 这里需要实现USDC合约余额检查
                pass
            
            return False
            
        except Exception as e:
            logger.error(f"检查ETH支付失败: {e}")
            return False
    
    def _get_btc_confirmations(self, address: str) -> int:
        """获取BTC地址最新交易的确认数"""
        try:
            url = f"{self.btc_api_url}/address/{address}/txs"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                txs = response.json()
                if txs:
                    # 获取最新交易的确认数
                    latest_tx = txs[0]
                    return latest_tx.get('status', {}).get('confirmed', 0) and \
                           latest_tx.get('status', {}).get('block_height', 0)
            
            return 0
            
        except Exception as e:
            logger.error(f"获取BTC确认数失败: {e}")
            return 0
    
    def _log_payment_event(self, payment: Payment, event_type: str, details: str = None):
        """记录支付事件日志"""
        try:
            log_entry = {
                'payment_id': payment.id,
                'event_type': event_type,
                'timestamp': datetime.utcnow().isoformat(),
                'details': details or {},
                'payment_data': payment.to_dict()
            }
            
            logger.info(f"支付事件: {json.dumps(log_entry, ensure_ascii=False)}")
            
        except Exception as e:
            logger.error(f"记录支付事件失败: {e}")

# 全局服务实例
crypto_payment_service = CryptoPaymentService()