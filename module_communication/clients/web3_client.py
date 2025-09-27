"""
Web3 Integration Module API Client
Web3集成模块API客户端
"""

import requests
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from ..common.config import config
from ..common.auth import jwt_manager
from ..common.utils import RetryMechanism, CircuitBreaker, format_error_response, request_logger

logger = logging.getLogger(__name__)

class Web3IntegrationClient:
    """Web3集成模块API客户端"""
    
    def __init__(self, api_key: str = None, base_url: str = None):
        self.module_config = config.get_module_config('web3_integration')
        self.base_url = base_url or self.module_config['base_url']
        self.api_key = api_key
        self.timeout = self.module_config['timeout']
        
        # 设置重试和熔断器
        self.retry = RetryMechanism(max_retries=self.module_config['max_retries'])
        self.circuit_breaker = CircuitBreaker()
        
        logger.info(f"Initialized Web3 Integration client for {self.base_url}")
    
    def _make_request(self, 
                     method: str, 
                     endpoint: str, 
                     data: Dict[str, Any] = None,
                     user_token: str = None,
                     **kwargs) -> Dict[str, Any]:
        """发起API请求"""
        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'ModuleCommunication/1.0'
        }
        
        # 添加认证头
        if self.api_key:
            headers[config.security_config['api_key_header']] = self.api_key
        
        if user_token:
            headers[config.security_config['jwt_header']] = f"{config.security_config['jwt_prefix']}{user_token}"
        
        # 记录请求
        request_logger.log_request(method, url, headers, str(data) if data else None, 'web3_integration')
        
        try:
            start_time = datetime.now()
            
            if method.upper() == 'GET':
                response = requests.get(url, headers=headers, timeout=self.timeout, **kwargs)
            elif method.upper() == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=self.timeout, **kwargs)
            elif method.upper() == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=self.timeout, **kwargs)
            elif method.upper() == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=self.timeout, **kwargs)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response_time = (datetime.now() - start_time).total_seconds()
            
            # 记录响应
            request_logger.log_response(
                response.status_code, 
                response_time, 
                response.text[:1000] if len(response.text) < 1000 else None,
                'web3_integration'
            )
            
            # 处理响应
            if response.status_code >= 400:
                error_data = response.json() if response.headers.get('content-type') == 'application/json' else {}
                logger.error(f"Web3 Integration API error {response.status_code}: {error_data}")
                return {
                    'success': False,
                    'error': error_data.get('error', f'HTTP {response.status_code}'),
                    'status_code': response.status_code
                }
            
            result = response.json() if response.headers.get('content-type') == 'application/json' else {'data': response.text}
            return {
                'success': True,
                'data': result,
                'response_time': response_time
            }
            
        except requests.exceptions.Timeout:
            logger.error(f"Timeout calling Web3 Integration API: {url}")
            return {
                'success': False,
                'error': 'Request timeout',
                'status_code': 408
            }
        except requests.exceptions.ConnectionError:
            logger.error(f"Connection error calling Web3 Integration API: {url}")
            return {
                'success': False,
                'error': 'Connection failed',
                'status_code': 503
            }
        except Exception as e:
            logger.error(f"Unexpected error calling Web3 Integration API: {e}")
            return {
                'success': False,
                'error': str(e),
                'status_code': 500
            }
    
    @RetryMechanism(max_retries=3)
    @CircuitBreaker(failure_threshold=5)
    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        return self._make_request('GET', '/health')
    
    @RetryMechanism(max_retries=3)
    def authenticate_wallet(self, 
                          wallet_address: str,
                          signature: str,
                          message: str,
                          wallet_type: str = 'metamask') -> Dict[str, Any]:
        """钱包认证"""
        data = {
            'wallet_address': wallet_address,
            'signature': signature,
            'message': message,
            'wallet_type': wallet_type
        }
        return self._make_request('POST', '/api/auth/wallet', data)
    
    @RetryMechanism(max_retries=3)
    def create_payment_order(self, 
                           payment_data: Dict[str, Any],
                           user_token: str = None) -> Dict[str, Any]:
        """创建加密货币支付订单"""
        return self._make_request('POST', '/api/payments/create', payment_data, user_token)
    
    @RetryMechanism(max_retries=3)
    def check_payment_status(self, 
                           payment_id: str,
                           user_token: str = None) -> Dict[str, Any]:
        """检查支付状态"""
        return self._make_request('GET', f'/api/payments/{payment_id}/status', user_token=user_token)
    
    @RetryMechanism(max_retries=3)
    def confirm_payment(self, 
                       payment_id: str,
                       transaction_hash: str,
                       user_token: str = None) -> Dict[str, Any]:
        """确认支付"""
        data = {
            'payment_id': payment_id,
            'transaction_hash': transaction_hash
        }
        return self._make_request('POST', '/api/payments/confirm', data, user_token)
    
    @RetryMechanism(max_retries=3)
    def mint_sla_nft(self, 
                    nft_data: Dict[str, Any],
                    user_token: str = None) -> Dict[str, Any]:
        """铸造SLA NFT证书"""
        return self._make_request('POST', '/api/nft/sla/mint', nft_data, user_token)
    
    @RetryMechanism(max_retries=3)
    def store_data_ipfs(self, 
                       data: Dict[str, Any],
                       metadata: Dict[str, Any] = None,
                       user_token: str = None) -> Dict[str, Any]:
        """存储数据到IPFS"""
        payload = {
            'data': data,
            'metadata': metadata or {}
        }
        return self._make_request('POST', '/api/storage/ipfs', payload, user_token)
    
    @RetryMechanism(max_retries=3)
    def retrieve_ipfs_data(self, 
                          ipfs_hash: str,
                          user_token: str = None) -> Dict[str, Any]:
        """从IPFS检索数据"""
        return self._make_request('GET', f'/api/storage/ipfs/{ipfs_hash}', user_token=user_token)
    
    @RetryMechanism(max_retries=3)
    def store_blockchain_proof(self, 
                             proof_data: Dict[str, Any],
                             blockchain: str = 'ethereum',
                             user_token: str = None) -> Dict[str, Any]:
        """存储区块链验证证明"""
        data = {
            'proof_data': proof_data,
            'blockchain': blockchain
        }
        return self._make_request('POST', '/api/blockchain/proof', data, user_token)
    
    @RetryMechanism(max_retries=3)
    def verify_blockchain_proof(self, 
                               proof_id: str,
                               user_token: str = None) -> Dict[str, Any]:
        """验证区块链证明"""
        return self._make_request('GET', f'/api/blockchain/proof/{proof_id}/verify', user_token=user_token)
    
    @RetryMechanism(max_retries=3)
    def get_wallet_balance(self, 
                          wallet_address: str,
                          token_symbols: List[str] = None,
                          user_token: str = None) -> Dict[str, Any]:
        """获取钱包余额"""
        params = {'wallet_address': wallet_address}
        if token_symbols:
            params['tokens'] = ','.join(token_symbols)
        
        return self._make_request('GET', '/api/wallet/balance', params, user_token)
    
    @RetryMechanism(max_retries=3)
    def perform_kyc_check(self, 
                         user_data: Dict[str, Any],
                         user_token: str = None) -> Dict[str, Any]:
        """执行KYC检查"""
        return self._make_request('POST', '/api/compliance/kyc', user_data, user_token)
    
    @RetryMechanism(max_retries=3)
    def perform_aml_check(self, 
                         transaction_data: Dict[str, Any],
                         user_token: str = None) -> Dict[str, Any]:
        """执行AML检查"""
        return self._make_request('POST', '/api/compliance/aml', transaction_data, user_token)
    
    @RetryMechanism(max_retries=3)
    def get_supported_cryptocurrencies(self, user_token: str = None) -> Dict[str, Any]:
        """获取支持的加密货币列表"""
        return self._make_request('GET', '/api/payments/currencies', user_token=user_token)
    
    @RetryMechanism(max_retries=3)
    def get_network_status(self, 
                          blockchain: str = 'ethereum',
                          user_token: str = None) -> Dict[str, Any]:
        """获取区块链网络状态"""
        params = {'blockchain': blockchain}
        return self._make_request('GET', '/api/blockchain/status', params, user_token)
    
    @RetryMechanism(max_retries=3)
    def estimate_gas_fees(self, 
                         transaction_type: str,
                         blockchain: str = 'ethereum',
                         user_token: str = None) -> Dict[str, Any]:
        """估算Gas费用"""
        data = {
            'transaction_type': transaction_type,
            'blockchain': blockchain
        }
        return self._make_request('POST', '/api/blockchain/gas/estimate', data, user_token)
    
    def update_user_kyc_status(self, 
                             user_id: str,
                             kyc_status: str,
                             kyc_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """更新用户KYC状态（与用户管理模块通信）"""
        # 这个方法实际上应该调用用户管理模块
        # 这里是Web3模块需要的接口定义
        logger.info(f"Web3 Integration requesting KYC status update for user {user_id}")
        return {
            'success': True,
            'user_id': user_id,
            'kyc_status': kyc_status,
            'updated_at': datetime.utcnow().isoformat()
        }
    
    def notify_payment_completion(self, 
                                user_id: str,
                                payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """通知支付完成（与用户管理模块通信）"""
        # 这个方法实际上应该调用用户管理模块
        # 这里是Web3模块需要的接口定义
        logger.info(f"Web3 Integration notifying payment completion for user {user_id}")
        return {
            'success': True,
            'user_id': user_id,
            'payment_id': payment_data.get('payment_id'),
            'notified_at': datetime.utcnow().isoformat()
        }

# 辅助函数，用于获取默认的Web3 Integration客户端实例
def get_web3_client(api_key: str = None) -> Web3IntegrationClient:
    """获取Web3 Integration客户端实例"""
    return Web3IntegrationClient(api_key=api_key)