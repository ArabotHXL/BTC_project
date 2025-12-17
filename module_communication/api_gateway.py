"""
API Gateway for Module Communication
API网关 - 提供统一的入口点和路由，支持可选的组合部署
"""

import logging
import time
from typing import Dict, Any, Optional, List
from urllib.parse import urljoin, urlparse
from flask import Flask, request, jsonify, Response
import requests

from common.config import config
from common.auth import auth_middleware, require_auth
from common.utils import format_error_response, format_success_response, rate_limiter, CircuitBreaker
from service_registry import service_registry, load_balancer

logger = logging.getLogger(__name__)

class APIGateway:
    """API网关类"""
    
    def __init__(self):
        self.service_registry = service_registry
        self.load_balancer = load_balancer
        self.auth_middleware = auth_middleware
        
        # 路由映射配置
        self.route_mappings = {
            '/api/mining': 'mining_core',
            '/api/web3': 'web3_integration', 
            '/api/users': 'user_management',
            '/api/auth': 'user_management',
            '/api/billing': 'user_management',
            '/api/crm': 'user_management'
        }
        
        # 熔断器配置
        self.circuit_breakers = {}
        for service_name in self.route_mappings.values():
            self.circuit_breakers[service_name] = CircuitBreaker(
                failure_threshold=config.api_gateway_config.get('circuit_breaker_threshold', 5),
                recovery_timeout=config.api_gateway_config.get('circuit_breaker_timeout', 60)
            )
        
        logger.info("API Gateway initialized")
    
    def route_request(self, path: str, method: str, **kwargs) -> Dict[str, Any]:
        """路由请求到相应的服务"""
        try:
            # 确定目标服务
            service_name = self._determine_service(path)
            if not service_name:
                return {
                    'success': False,
                    'error': 'Service not found for path',
                    'status_code': 404
                }
            
            # 获取服务实例
            if config.api_gateway_config.get('load_balancing', False):
                instance = self.load_balancer.get_instance(service_name)
            else:
                instances = self.service_registry.discover_service(service_name, healthy_only=True)
                instance = instances[0] if instances else None
            
            if not instance:
                return {
                    'success': False,
                    'error': f'No healthy instances available for service {service_name}',
                    'status_code': 503
                }
            
            # 构建目标URL
            target_url = self._build_target_url(instance.base_url, path, service_name)
            
            # 应用熔断器
            circuit_breaker = self.circuit_breakers.get(service_name)
            if circuit_breaker:
                return self._make_request_with_circuit_breaker(
                    circuit_breaker, target_url, method, **kwargs
                )
            else:
                return self._make_request(target_url, method, **kwargs)
                
        except Exception as e:
            logger.error(f"Error routing request to {path}: {e}")
            return {
                'success': False,
                'error': str(e),
                'status_code': 500
            }
    
    def _determine_service(self, path: str) -> Optional[str]:
        """确定路径对应的服务"""
        for route_prefix, service_name in self.route_mappings.items():
            if path.startswith(route_prefix):
                return service_name
        return None
    
    def _build_target_url(self, base_url: str, original_path: str, service_name: str) -> str:
        """构建目标URL"""
        # 移除API网关前缀
        for route_prefix, mapped_service in self.route_mappings.items():
            if mapped_service == service_name and original_path.startswith(route_prefix):
                # 移除网关前缀，保留服务内部路径
                service_path = original_path[len(route_prefix):]
                if not service_path.startswith('/'):
                    service_path = '/' + service_path
                return urljoin(base_url, service_path.lstrip('/'))
        
        # 如果没有匹配的前缀，直接使用原路径
        return urljoin(base_url, original_path.lstrip('/'))
    
    def _make_request_with_circuit_breaker(self, 
                                         circuit_breaker: CircuitBreaker,
                                         url: str, 
                                         method: str, 
                                         **kwargs) -> Dict[str, Any]:
        """使用熔断器发起请求"""
        @circuit_breaker
        def make_request():
            return self._make_request(url, method, **kwargs)
        
        try:
            return make_request()
        except Exception as e:
            logger.error(f"Circuit breaker triggered for {url}: {e}")
            return {
                'success': False,
                'error': 'Service temporarily unavailable',
                'status_code': 503
            }
    
    def _make_request(self, url: str, method: str, **kwargs) -> Dict[str, Any]:
        """发起HTTP请求"""
        try:
            timeout = kwargs.pop('timeout', 30)
            
            # 准备请求头
            headers = kwargs.get('headers', {})
            headers['User-Agent'] = 'APIGateway/1.0'
            
            start_time = time.time()
            
            # 发起请求
            if method.upper() == 'GET':
                response = requests.get(url, timeout=timeout, **kwargs)
            elif method.upper() == 'POST':
                response = requests.post(url, timeout=timeout, **kwargs)
            elif method.upper() == 'PUT':
                response = requests.put(url, timeout=timeout, **kwargs)
            elif method.upper() == 'DELETE':
                response = requests.delete(url, timeout=timeout, **kwargs)
            elif method.upper() == 'PATCH':
                response = requests.patch(url, timeout=timeout, **kwargs)
            else:
                return {
                    'success': False,
                    'error': f'Unsupported HTTP method: {method}',
                    'status_code': 405
                }
            
            response_time = time.time() - start_time
            
            # 处理响应
            result = {
                'success': response.status_code < 400,
                'status_code': response.status_code,
                'headers': dict(response.headers),
                'response_time': response_time
            }
            
            # 尝试解析JSON响应
            try:
                result['data'] = response.json()
            except:
                result['data'] = response.text
            
            return result
            
        except requests.exceptions.Timeout:
            return {
                'success': False,
                'error': 'Request timeout',
                'status_code': 408
            }
        except requests.exceptions.ConnectionError:
            return {
                'success': False,
                'error': 'Connection failed',
                'status_code': 503
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'status_code': 500
            }

def create_api_gateway_app():
    """创建API网关Flask应用"""
    app = Flask(__name__)
    app.secret_key = config.jwt_config['secret_key']
    
    gateway = APIGateway()
    
    @app.before_request
    def before_request():
        """请求前处理"""
        # 速率限制
        if config.security_config['rate_limit_enabled']:
            client_ip = request.remote_addr
            if not rate_limiter.is_allowed(client_ip):
                return jsonify(format_error_response(
                    'RATE_LIMIT_EXCEEDED',
                    'Too many requests'
                )), 429
        
        # 记录请求
        logger.info(f"Gateway request: {request.method} {request.path} from {request.remote_addr}")
    
    @app.route('/health')
    def health():
        """网关健康检查"""
        services_status = {}
        
        # 检查所有注册的服务
        for service_name in gateway.route_mappings.values():
            instances = service_registry.discover_service(service_name, healthy_only=False)
            healthy_count = len([i for i in instances if i.status == 'healthy'])
            total_count = len(instances)
            
            services_status[service_name] = {
                'healthy_instances': healthy_count,
                'total_instances': total_count,
                'status': 'healthy' if healthy_count > 0 else 'unhealthy'
            }
        
        overall_status = 'healthy' if any(
            s['status'] == 'healthy' for s in services_status.values()
        ) else 'unhealthy'
        
        return jsonify({
            'status': overall_status,
            'service': 'api_gateway',
            'timestamp': time.time(),
            'services': services_status
        }), 200 if overall_status == 'healthy' else 503
    
    @app.route('/gateway/info')
    def gateway_info():
        """网关信息"""
        return jsonify(format_success_response({
            'name': 'HashInsight Module Communication Gateway',
            'version': '1.0.0',
            'services': list(set(gateway.route_mappings.values())),
            'routes': gateway.route_mappings,
            'features': [
                'Load Balancing',
                'Circuit Breaker',
                'Rate Limiting',
                'Authentication',
                'Request Routing',
                'Health Monitoring'
            ]
        }))
    
    @app.route('/gateway/services')
    def list_gateway_services():
        """列出网关管理的服务"""
        services = service_registry.get_all_services()
        
        result = {}
        for service_name, instances in services.items():
            if service_name in gateway.route_mappings.values():
                result[service_name] = {
                    'instances': len(instances),
                    'healthy_instances': len([i for i in instances if i.status == 'healthy']),
                    'route_prefix': next(
                        (prefix for prefix, svc in gateway.route_mappings.items() if svc == service_name),
                        None
                    )
                }
        
        return jsonify(format_success_response(result))
    
    # 通用路由处理器
    @app.route('/api/<path:subpath>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
    def proxy_request(subpath):
        """代理请求到相应的服务"""
        full_path = f"/api/{subpath}"
        
        # 准备请求参数
        request_kwargs = {
            'headers': dict(request.headers),
            'params': dict(request.args)
        }
        
        # 添加请求体（如果有）
        if request.is_json:
            request_kwargs['json'] = request.get_json()
        elif request.form:
            request_kwargs['data'] = dict(request.form)
        elif request.data:
            request_kwargs['data'] = request.data
        
        # 路由请求
        result = gateway.route_request(full_path, request.method, **request_kwargs)
        
        if not result['success']:
            error_response = format_error_response(
                'GATEWAY_ERROR',
                result['error']
            )
            return jsonify(error_response), result['status_code']
        
        # 构建响应
        response_data = result['data']
        status_code = result['status_code']
        
        # 创建响应对象
        response = Response(
            response_data if isinstance(response_data, str) else jsonify(response_data).data,
            status=status_code,
            content_type='application/json' if isinstance(response_data, dict) else 'text/plain'
        )
        
        # 添加响应头
        for header_name, header_value in result.get('headers', {}).items():
            if header_name.lower() not in ['content-length', 'content-encoding', 'transfer-encoding']:
                response.headers[header_name] = header_value
        
        # 添加网关头
        response.headers['X-Gateway-Response-Time'] = str(result.get('response_time', 0))
        response.headers['X-Powered-By'] = 'HashInsight-Gateway'
        
        return response
    
    # 特殊的认证保护路由
    @app.route('/api/admin/<path:subpath>', methods=['GET', 'POST', 'PUT', 'DELETE'])
    @require_auth(['admin', 'owner'])
    def admin_proxy_request(subpath):
        """管理员API代理（需要认证）"""
        return proxy_request(f"admin/{subpath}")
    
    @app.route('/api/protected/<path:subpath>', methods=['GET', 'POST', 'PUT', 'DELETE'])
    @require_auth()
    def protected_proxy_request(subpath):
        """受保护的API代理（需要认证）"""
        return proxy_request(f"protected/{subpath}")
    
    # 错误处理
    @app.errorhandler(404)
    def not_found(error):
        return jsonify(format_error_response(
            'NOT_FOUND',
            'Endpoint not found'
        )), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Gateway internal error: {error}")
        return jsonify(format_error_response(
            'INTERNAL_ERROR',
            'Gateway internal error'
        )), 500
    
    return app

def start_api_gateway(port: int = 5000):
    """启动API网关"""
    if not config.api_gateway_config.get('enabled', False):
        logger.warning("API Gateway is disabled in configuration")
        return
    
    app = create_api_gateway_app()
    
    # 启动服务注册中心监控
    service_registry.start_health_monitoring()
    
    logger.info(f"Starting API Gateway on port {port}")
    
    try:
        app.run(
            host=config.api_gateway_config.get('host', '0.0.0.0'),
            port=port,
            debug=False,
            threaded=True
        )
    except KeyboardInterrupt:
        logger.info("Shutting down API Gateway")
    finally:
        service_registry.stop_health_monitoring()

if __name__ == '__main__':
    import os
    port = int(os.environ.get('API_GATEWAY_PORT', 5000))
    start_api_gateway(port)