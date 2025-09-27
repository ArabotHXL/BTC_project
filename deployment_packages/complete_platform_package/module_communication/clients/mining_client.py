"""
Mining Core Module API Client
挖矿核心模块API客户端
"""

import requests
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from ..common.config import config
from ..common.auth import jwt_manager
from ..common.utils import RetryMechanism, CircuitBreaker, format_error_response, request_logger

logger = logging.getLogger(__name__)

class MiningCoreClient:
    """挖矿核心模块API客户端"""
    
    def __init__(self, api_key: str = None, base_url: str = None):
        self.module_config = config.get_module_config('mining_core')
        self.base_url = base_url or self.module_config['base_url']
        self.api_key = api_key
        self.timeout = self.module_config['timeout']
        
        # 设置重试和熔断器
        self.retry = RetryMechanism(max_retries=self.module_config['max_retries'])
        self.circuit_breaker = CircuitBreaker()
        
        logger.info(f"Initialized Mining Core client for {self.base_url}")
    
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
        request_logger.log_request(method, url, headers, str(data) if data else None, 'mining_core')
        
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
                'mining_core'
            )
            
            # 处理响应
            if response.status_code >= 400:
                error_data = response.json() if response.headers.get('content-type') == 'application/json' else {}
                logger.error(f"Mining Core API error {response.status_code}: {error_data}")
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
            logger.error(f"Timeout calling Mining Core API: {url}")
            return {
                'success': False,
                'error': 'Request timeout',
                'status_code': 408
            }
        except requests.exceptions.ConnectionError:
            logger.error(f"Connection error calling Mining Core API: {url}")
            return {
                'success': False,
                'error': 'Connection failed',
                'status_code': 503
            }
        except Exception as e:
            logger.error(f"Unexpected error calling Mining Core API: {e}")
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
    def calculate_mining_profitability(self, 
                                     miner_data: Dict[str, Any],
                                     user_token: str = None) -> Dict[str, Any]:
        """计算挖矿盈利能力"""
        return self._make_request('POST', '/api/calculator/profitability', miner_data, user_token)
    
    @RetryMechanism(max_retries=3)
    def batch_calculate(self, 
                       miners_data: List[Dict[str, Any]],
                       user_token: str = None) -> Dict[str, Any]:
        """批量计算"""
        return self._make_request('POST', '/api/calculator/batch', {'miners': miners_data}, user_token)
    
    @RetryMechanism(max_retries=3)
    def get_market_analytics(self, 
                           timeframe: str = '24h',
                           indicators: List[str] = None,
                           user_token: str = None) -> Dict[str, Any]:
        """获取市场分析数据"""
        params = {'timeframe': timeframe}
        if indicators:
            params['indicators'] = ','.join(indicators)
        
        return self._make_request('GET', '/api/analytics/market', params, user_token)
    
    @RetryMechanism(max_retries=3)
    def generate_mining_report(self, 
                             report_config: Dict[str, Any],
                             user_token: str = None) -> Dict[str, Any]:
        """生成挖矿报告"""
        return self._make_request('POST', '/api/analytics/report', report_config, user_token)
    
    @RetryMechanism(max_retries=3)
    def get_network_metrics(self, user_token: str = None) -> Dict[str, Any]:
        """获取网络指标"""
        return self._make_request('GET', '/api/network/metrics', user_token=user_token)
    
    @RetryMechanism(max_retries=3)
    def get_historical_data(self, 
                          data_type: str,
                          start_date: str,
                          end_date: str,
                          user_token: str = None) -> Dict[str, Any]:
        """获取历史数据"""
        params = {
            'type': data_type,
            'start_date': start_date,
            'end_date': end_date
        }
        return self._make_request('GET', '/api/data/historical', params, user_token)
    
    def verify_user_subscription(self, 
                               user_id: str, 
                               required_level: str = 'basic') -> Dict[str, Any]:
        """验证用户订阅级别（与用户管理模块通信）"""
        # 这个方法实际上应该调用用户管理模块
        # 这里是Mining Core模块需要的接口定义
        logger.info(f"Mining Core requesting user subscription verification for user {user_id}")
        return {
            'success': True,
            'user_id': user_id,
            'subscription_verified': True,
            'subscription_level': required_level
        }
    
    def store_calculation_result(self, 
                               calculation_data: Dict[str, Any],
                               user_token: str = None) -> Dict[str, Any]:
        """存储计算结果（可选与Web3模块通信存储到区块链）"""
        return self._make_request('POST', '/api/results/store', calculation_data, user_token)
    
    def get_miner_models(self, 
                        manufacturer: str = None,
                        active_only: bool = True,
                        user_token: str = None) -> Dict[str, Any]:
        """获取矿机型号列表"""
        params = {'active_only': active_only}
        if manufacturer:
            params['manufacturer'] = manufacturer
        
        return self._make_request('GET', '/api/miners/models', params, user_token)
    
    def update_miner_specifications(self, 
                                  miner_id: str,
                                  specifications: Dict[str, Any],
                                  user_token: str = None) -> Dict[str, Any]:
        """更新矿机规格"""
        return self._make_request('PUT', f'/api/miners/{miner_id}/specs', specifications, user_token)
    
    def get_efficiency_analysis(self, 
                              miner_ids: List[str],
                              analysis_period: str = '30d',
                              user_token: str = None) -> Dict[str, Any]:
        """获取效率分析"""
        data = {
            'miner_ids': miner_ids,
            'period': analysis_period
        }
        return self._make_request('POST', '/api/analytics/efficiency', data, user_token)

# 辅助函数，用于获取默认的Mining Core客户端实例
def get_mining_client(api_key: str = None) -> MiningCoreClient:
    """获取Mining Core客户端实例"""
    return MiningCoreClient(api_key=api_key)