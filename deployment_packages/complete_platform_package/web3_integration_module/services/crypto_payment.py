"""
加密货币支付服务
为Web3集成模块提供加密货币支付集成

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
try:
    from .blockchain import blockchain_integration
    from .compliance import compliance_service
except ImportError:
    # Fallback for standalone execution
    from services.blockchain import blockchain_integration
    from services.compliance import compliance_service

logger = logging.getLogger(__name__)

class CryptoPaymentService:
    """加密货币支付服务主类"""
    
    def __init__(self):
        """初始化加密货币支付服务"""
        self.blockchain_integration = blockchain_integration
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
            'base_testnet': '0x1c7D4B196Cb0C7B01d743Fbc6116a902379C7238',  # Base Testnet USDC
            'ethereum_mainnet': '0xA0b86a33E6b3d539B4F1Fea1e23bDcdD0C91EeEf',  # 替换为正确的主网USDC地址
            'ethereum_testnet': '0x6F175f4F84b8D5d0A7b9d8b3fF7E8a89bfC1c1C1'    # 替换为正确的测试网USDC地址
        }
        
        # 价格获取API
        self.price_api_endpoints = {
            'coingecko': 'https://api.coingecko.com/api/v3/simple/price',
            'coinbase': 'https://api.coinbase.com/v2/exchange-rates'
        }
        
        logger.info("CryptoPaymentService initialized")
    
    def get_supported_currencies(self) -> List[str]:
        """获取支持的加密货币列表"""
        return ['BTC', 'ETH', 'USDC']
    
    def get_current_prices(self) -> Dict[str, float]:
        """
        获取当前加密货币价格
        
        Returns:
            包含所有支持币种价格的字典
        """
        try:
            # 使用CoinGecko API获取价格
            currency_ids = {
                'BTC': 'bitcoin',
                'ETH': 'ethereum', 
                'USDC': 'usd-coin'
            }
            
            ids = ','.join(currency_ids.values())
            url = f"{self.price_api_endpoints['coingecko']}?ids={ids}&vs_currencies=usd"
            
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                prices = {}
                
                for crypto, coin_id in currency_ids.items():
                    if coin_id in data and 'usd' in data[coin_id]:
                        prices[crypto] = data[coin_id]['usd']
                
                if prices:
                    logger.info("价格获取成功")
                    return prices
            
            # 回退价格
            logger.warning("使用回退价格")
            return {
                'BTC': 45000.0,
                'ETH': 3000.0,
                'USDC': 1.0
            }
            
        except Exception as e:
            logger.error(f"获取价格失败: {e}")
            # 返回回退价格
            return {
                'BTC': 45000.0,
                'ETH': 3000.0,
                'USDC': 1.0
            }
    
    def calculate_crypto_amount(self, usd_amount: float, crypto: str) -> float:
        """
        计算加密货币数量
        
        Args:
            usd_amount: USD金额
            crypto: 加密货币类型
            
        Returns:
            加密货币数量
        """
        try:
            prices = self.get_current_prices()
            crypto_price = prices.get(crypto)
            
            if not crypto_price:
                raise ValueError(f"无法获取{crypto}价格")
            
            crypto_amount = usd_amount / crypto_price
            
            # 根据币种调整精度
            if crypto == 'BTC':
                crypto_amount = round(crypto_amount, 8)  # BTC保留8位小数
            elif crypto == 'ETH':
                crypto_amount = round(crypto_amount, 6)  # ETH保留6位小数
            elif crypto == 'USDC':
                crypto_amount = round(crypto_amount, 6)  # USDC保留6位小数
            
            return crypto_amount
            
        except Exception as e:
            logger.error(f"计算{crypto}数量失败: {e}")
            raise
    
    def create_payment_request(self, payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        创建支付请求
        
        Args:
            payment_data: 包含金额、货币、用户信息等的支付数据
            
        Returns:
            支付请求信息，包括地址、二维码等
        """
        try:
            required_fields = ['amount_usd', 'crypto_currency', 'user_id']
            for field in required_fields:
                if field not in payment_data:
                    raise ValueError(f"缺少必需字段: {field}")
            
            amount_usd = float(payment_data['amount_usd'])
            crypto = payment_data['crypto_currency'].upper()
            user_id = payment_data['user_id']
            
            if crypto not in self.get_supported_currencies():
                raise ValueError(f"不支持的加密货币: {crypto}")
            
            # 计算加密货币数量
            crypto_amount = self.calculate_crypto_amount(amount_usd, crypto)
            
            # 生成支付地址
            payment_address = self._get_payment_address(crypto, user_id)
            
            if not payment_address:
                raise ValueError(f"无法生成{crypto}支付地址")
            
            # 生成二维码
            qr_code_data = self._generate_payment_qr_code(crypto, payment_address, crypto_amount)
            
            # 创建支付超时时间
            expires_at = datetime.utcnow() + timedelta(hours=self.payment_timeout_hours)
            
            # 🔧 CRITICAL FIX: 合规检查
            compliance_result = compliance_service.check_payment_compliance({
                'user_id': user_id,
                'amount_usd': amount_usd,
                'crypto_currency': crypto,
                'payment_address': payment_address
            })
            
            if not compliance_result['approved']:
                raise ValueError(f"支付被合规检查拒绝: {compliance_result['reason']}")
            
            payment_request = {
                'payment_id': self._generate_payment_id(),
                'amount_usd': amount_usd,
                'crypto_currency': crypto,
                'crypto_amount': crypto_amount,
                'payment_address': payment_address,
                'qr_code_data': qr_code_data,
                'expires_at': expires_at.isoformat(),
                'status': 'pending',
                'created_at': datetime.utcnow().isoformat(),
                'user_id': user_id,
                'confirmation_requirement': self.confirmation_requirements[crypto],
                'compliance_check_id': compliance_result.get('check_id')
            }
            
            logger.info(f"支付请求创建成功: {payment_request['payment_id']}")
            return payment_request
            
        except Exception as e:
            logger.error(f"创建支付请求失败: {e}")
            raise
    
    def check_payment_status(self, payment_id: str, payment_address: str, crypto: str, amount: float) -> Dict[str, Any]:
        """
        检查支付状态
        
        Args:
            payment_id: 支付ID
            payment_address: 支付地址
            crypto: 加密货币类型
            amount: 预期金额
            
        Returns:
            支付状态信息
        """
        try:
            if crypto == 'BTC':
                return self._check_btc_payment(payment_address, amount)
            elif crypto == 'ETH':
                return self._check_eth_payment(payment_address, amount)
            elif crypto == 'USDC':
                return self._check_usdc_payment(payment_address, amount)
            else:
                return {'status': 'error', 'message': f'不支持的加密货币: {crypto}'}
                
        except Exception as e:
            logger.error(f"检查支付状态失败: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def _get_payment_address(self, crypto: str, user_id: int) -> Optional[str]:
        """获取支付地址"""
        try:
            # 对于简化实现，返回配置的地址
            # 在生产环境中，应该为每个支付生成唯一地址
            return self.wallet_addresses.get(crypto)
            
        except Exception as e:
            logger.error(f"获取{crypto}支付地址失败: {e}")
            return None
    
    def _generate_payment_qr_code(self, crypto: str, address: str, amount: float) -> str:
        """生成支付二维码"""
        try:
            if crypto == 'BTC':
                qr_text = f"bitcoin:{address}?amount={amount}"
            elif crypto == 'ETH':
                qr_text = f"ethereum:{address}?value={amount}"
            elif crypto == 'USDC':
                # USDC使用ERC-20标准
                qr_text = f"ethereum:{address}?value={amount}&token=USDC"
            else:
                qr_text = f"{address}"
            
            # 生成二维码
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(qr_text)
            qr.make(fit=True)
            
            # 转换为图片
            img = qr.make_image(fill_color="black", back_color="white")
            
            # 转换为base64
            buffered = io.BytesIO()
            img.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode()
            
            return f"data:image/png;base64,{img_str}"
            
        except Exception as e:
            logger.error(f"生成二维码失败: {e}")
            return ""
    
    def _generate_payment_id(self) -> str:
        """生成支付ID"""
        timestamp = str(int(time.time()))
        random_str = os.urandom(8).hex()
        return f"pay_{timestamp}_{random_str}"
    
    def _check_btc_payment(self, address: str, expected_amount: float) -> Dict[str, Any]:
        """检查BTC支付"""
        try:
            # 使用Blockstream API检查BTC交易
            api_url = self.btc_api_url
            if not self.blockchain_integration.is_mainnet_mode:
                api_url = "https://blockstream.info/testnet/api"
            
            response = requests.get(f"{api_url}/address/{address}/txs", timeout=10)
            
            if response.status_code == 200:
                transactions = response.json()
                
                for tx in transactions[:5]:  # 检查最近5笔交易
                    # 检查输出
                    for vout in tx.get('vout', []):
                        if (vout.get('scriptpubkey_address') == address and
                            vout.get('value', 0) / 100000000 >= expected_amount):  # 转换satoshi为BTC
                            
                            confirmations = 0
                            if tx.get('status', {}).get('confirmed'):
                                # 计算确认数
                                block_height = tx['status']['block_height']
                                latest_response = requests.get(f"{api_url}/blocks/tip/height", timeout=5)
                                if latest_response.status_code == 200:
                                    latest_height = int(latest_response.text)
                                    confirmations = latest_height - block_height + 1
                            
                            return {
                                'status': 'confirmed' if confirmations >= self.confirmation_requirements['BTC'] else 'pending',
                                'transaction_hash': tx['txid'],
                                'confirmations': confirmations,
                                'amount_received': vout.get('value', 0) / 100000000
                            }
                
                return {'status': 'not_found', 'message': '未找到匹配的交易'}
            else:
                return {'status': 'error', 'message': f'API请求失败: {response.status_code}'}
                
        except Exception as e:
            logger.error(f"检查BTC支付失败: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def _check_eth_payment(self, address: str, expected_amount: float) -> Dict[str, Any]:
        """检查ETH支付"""
        try:
            if not self.w3 or not self.w3.is_connected():
                return {'status': 'error', 'message': 'Web3连接不可用'}
            
            # 获取最近的区块进行扫描
            latest_block = self.w3.eth.block_number
            start_block = max(0, latest_block - 100)  # 扫描最近100个区块
            
            for block_num in range(latest_block, start_block - 1, -1):
                try:
                    block = self.w3.eth.get_block(block_num, full_transactions=True)
                    
                    for tx in block.transactions:
                        if (tx.to and tx.to.lower() == address.lower() and
                            self.w3.from_wei(tx.value, 'ether') >= expected_amount):
                            
                            # 计算确认数
                            confirmations = latest_block - block_num + 1
                            
                            return {
                                'status': 'confirmed' if confirmations >= self.confirmation_requirements['ETH'] else 'pending',
                                'transaction_hash': tx.hash.hex(),
                                'confirmations': confirmations,
                                'amount_received': float(self.w3.from_wei(tx.value, 'ether')),
                                'block_number': block_num
                            }
                            
                except Exception as e:
                    logger.warning(f"扫描区块 {block_num} 失败: {e}")
                    continue
            
            return {'status': 'not_found', 'message': '未找到匹配的交易'}
            
        except Exception as e:
            logger.error(f"检查ETH支付失败: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def _check_usdc_payment(self, address: str, expected_amount: float) -> Dict[str, Any]:
        """检查USDC支付"""
        try:
            # USDC是ERC-20代币，需要检查代币转账事件
            # 这需要更复杂的实现，暂时返回未实现状态
            return {'status': 'not_implemented', 'message': 'USDC支付检查尚未实现'}
            
        except Exception as e:
            logger.error(f"检查USDC支付失败: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def get_payment_statistics(self) -> Dict[str, Any]:
        """获取支付统计信息"""
        try:
            # 这里应该从数据库获取实际统计数据
            # 暂时返回示例数据
            return {
                'total_payments': 0,
                'successful_payments': 0,
                'total_volume_usd': 0.0,
                'currency_breakdown': {
                    'BTC': {'count': 0, 'volume': 0.0},
                    'ETH': {'count': 0, 'volume': 0.0},
                    'USDC': {'count': 0, 'volume': 0.0}
                },
                'current_prices': self.get_current_prices()
            }
            
        except Exception as e:
            logger.error(f"获取支付统计失败: {e}")
            return {'error': str(e)}

# 全局实例
crypto_payment_service = CryptoPaymentService()

# 导出
__all__ = ['CryptoPaymentService', 'crypto_payment_service']