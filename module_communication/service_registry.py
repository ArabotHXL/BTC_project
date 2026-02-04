"""
Service Discovery and Registry
服务发现和注册中心 - 管理模块服务注册、发现和健康检查
"""

import time
import threading
import logging
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from flask import Flask, request, jsonify

from .common.config import config
from .common.utils import health_checker, format_error_response, format_success_response

logger = logging.getLogger(__name__)

@dataclass
class ServiceInstance:
    """服务实例信息"""
    service_name: str
    instance_id: str
    host: str
    port: int
    health_endpoint: str
    status: str = 'unknown'  # unknown, healthy, unhealthy
    last_health_check: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    registered_at: datetime = field(default_factory=datetime.utcnow)
    last_heartbeat: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def base_url(self) -> str:
        """获取服务基础URL"""
        protocol = 'https' if self.metadata.get('use_https', False) else 'http'
        return f"{protocol}://{self.host}:{self.port}"
    
    @property
    def health_url(self) -> str:
        """获取健康检查URL"""
        return f"{self.base_url}{self.health_endpoint}"
    
    def is_expired(self, ttl_seconds: int = 300) -> bool:
        """检查服务实例是否过期"""
        if not self.last_heartbeat:
            return True
        return datetime.utcnow() - self.last_heartbeat > timedelta(seconds=ttl_seconds)

class ServiceRegistry:
    """服务注册中心"""
    
    def __init__(self, health_check_interval: int = 30, service_ttl: int = 300):
        self.services: Dict[str, Dict[str, ServiceInstance]] = {}
        self.health_check_interval = health_check_interval
        self.service_ttl = service_ttl
        self._lock = threading.RLock()
        self._health_check_thread = None
        self._running = False
        
        # 注册默认模块
        self._register_default_modules()
        
        logger.info("Service Registry initialized")
    
    def _register_default_modules(self):
        """注册默认模块"""
        default_modules = {
            'mining_core': {
                'host': config.modules['mining_core']['host'],
                'port': config.modules['mining_core']['port'],
                'health_endpoint': config.modules['mining_core']['health_endpoint']
            },
            'web3_integration': {
                'host': config.modules['web3_integration']['host'],
                'port': config.modules['web3_integration']['port'],
                'health_endpoint': config.modules['web3_integration']['health_endpoint']
            },
            'user_management': {
                'host': config.modules['user_management']['host'],
                'port': config.modules['user_management']['port'],
                'health_endpoint': config.modules['user_management']['health_endpoint']
            }
        }
        
        for service_name, service_config in default_modules.items():
            instance_id = f"{service_name}_default"
            self.register_service(
                service_name=service_name,
                instance_id=instance_id,
                host=service_config['host'],
                port=service_config['port'],
                health_endpoint=service_config['health_endpoint'],
                metadata={'default': True, 'auto_registered': True}
            )
    
    def register_service(self, 
                        service_name: str,
                        instance_id: str,
                        host: str,
                        port: int,
                        health_endpoint: str = '/health',
                        metadata: Dict[str, Any] = None) -> bool:
        """注册服务实例"""
        try:
            with self._lock:
                if service_name not in self.services:
                    self.services[service_name] = {}
                
                instance = ServiceInstance(
                    service_name=service_name,
                    instance_id=instance_id,
                    host=host,
                    port=port,
                    health_endpoint=health_endpoint,
                    metadata=metadata or {}
                )
                
                self.services[service_name][instance_id] = instance
                
                logger.info(f"Registered service instance: {service_name}/{instance_id} at {host}:{port}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to register service {service_name}/{instance_id}: {e}")
            return False
    
    def deregister_service(self, service_name: str, instance_id: str) -> bool:
        """注销服务实例"""
        try:
            with self._lock:
                if (service_name in self.services and 
                    instance_id in self.services[service_name]):
                    del self.services[service_name][instance_id]
                    
                    # 如果没有实例了，删除服务
                    if not self.services[service_name]:
                        del self.services[service_name]
                    
                    logger.info(f"Deregistered service instance: {service_name}/{instance_id}")
                    return True
                else:
                    logger.warning(f"Service instance not found: {service_name}/{instance_id}")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to deregister service {service_name}/{instance_id}: {e}")
            return False
    
    def heartbeat(self, service_name: str, instance_id: str) -> bool:
        """服务心跳"""
        try:
            with self._lock:
                if (service_name in self.services and 
                    instance_id in self.services[service_name]):
                    self.services[service_name][instance_id].last_heartbeat = datetime.utcnow()
                    return True
                else:
                    logger.warning(f"Service instance not found for heartbeat: {service_name}/{instance_id}")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to update heartbeat for {service_name}/{instance_id}: {e}")
            return False
    
    def discover_service(self, service_name: str, healthy_only: bool = True) -> List[ServiceInstance]:
        """发现服务实例"""
        try:
            with self._lock:
                if service_name not in self.services:
                    return []
                
                instances = list(self.services[service_name].values())
                
                # 过滤掉过期的实例
                active_instances = [
                    instance for instance in instances 
                    if not instance.is_expired(self.service_ttl)
                ]
                
                # 如果只要健康的实例
                if healthy_only:
                    active_instances = [
                        instance for instance in active_instances
                        if instance.status == 'healthy'
                    ]
                
                return active_instances
                
        except Exception as e:
            logger.error(f"Failed to discover service {service_name}: {e}")
            return []
    
    def get_service_instance(self, service_name: str, instance_id: str) -> Optional[ServiceInstance]:
        """获取特定服务实例"""
        try:
            with self._lock:
                if (service_name in self.services and 
                    instance_id in self.services[service_name]):
                    return self.services[service_name][instance_id]
                return None
                
        except Exception as e:
            logger.error(f"Failed to get service instance {service_name}/{instance_id}: {e}")
            return None
    
    def get_healthy_instance(self, service_name: str) -> Optional[ServiceInstance]:
        """获取一个健康的服务实例（负载均衡）"""
        instances = self.discover_service(service_name, healthy_only=True)
        if instances:
            # 简单的轮询负载均衡
            return min(instances, key=lambda x: x.last_health_check or datetime.min)
        return None
    
    def get_all_services(self) -> Dict[str, List[ServiceInstance]]:
        """获取所有服务实例"""
        try:
            with self._lock:
                result = {}
                for service_name, instances in self.services.items():
                    result[service_name] = [
                        instance for instance in instances.values()
                        if not instance.is_expired(self.service_ttl)
                    ]
                return result
                
        except Exception as e:
            logger.error(f"Failed to get all services: {e}")
            return {}
    
    def start_health_monitoring(self):
        """启动健康检查监控"""
        if self._running:
            logger.warning("Health monitoring is already running")
            return
        
        self._running = True
        self._health_check_thread = threading.Thread(
            target=self._health_check_loop,
            daemon=True
        )
        self._health_check_thread.start()
        logger.info("Started health monitoring")
    
    def stop_health_monitoring(self):
        """停止健康检查监控"""
        self._running = False
        if self._health_check_thread:
            self._health_check_thread.join(timeout=5)
        logger.info("Stopped health monitoring")
    
    def _health_check_loop(self):
        """健康检查循环"""
        while self._running:
            try:
                self._perform_health_checks()
                time.sleep(self.health_check_interval)
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
                time.sleep(5)  # 错误时短暂休息
    
    def _perform_health_checks(self):
        """执行健康检查"""
        with self._lock:
            for service_name, instances in self.services.items():
                for instance_id, instance in instances.items():
                    try:
                        # 检查是否过期
                        if instance.is_expired(self.service_ttl):
                            logger.warning(f"Service instance expired: {service_name}/{instance_id}")
                            instance.status = 'expired'
                            continue
                        
                        # 执行健康检查
                        health_result = health_checker.check_module_health({
                            'base_url': instance.base_url,
                            'health_endpoint': instance.health_endpoint
                        })
                        
                        # 更新状态
                        old_status = instance.status
                        instance.status = health_result['status']
                        instance.last_health_check = datetime.utcnow()
                        
                        # 记录状态变化
                        if old_status != instance.status:
                            logger.info(f"Service {service_name}/{instance_id} status changed: {old_status} -> {instance.status}")
                        
                    except Exception as e:
                        logger.error(f"Health check failed for {service_name}/{instance_id}: {e}")
                        instance.status = 'unhealthy'
                        instance.last_health_check = datetime.utcnow()

class LoadBalancer:
    """负载均衡器"""
    
    def __init__(self, service_registry: ServiceRegistry):
        self.service_registry = service_registry
        self._round_robin_counters = {}
    
    def get_instance(self, service_name: str, strategy: str = 'round_robin') -> Optional[ServiceInstance]:
        """根据负载均衡策略获取服务实例"""
        instances = self.service_registry.discover_service(service_name, healthy_only=True)
        
        if not instances:
            return None
        
        if strategy == 'round_robin':
            return self._round_robin(service_name, instances)
        elif strategy == 'least_connections':
            return self._least_connections(instances)
        elif strategy == 'random':
            import random
            return random.choice(instances)
        else:
            # 默认返回第一个
            return instances[0]
    
    def _round_robin(self, service_name: str, instances: List[ServiceInstance]) -> ServiceInstance:
        """轮询算法"""
        if service_name not in self._round_robin_counters:
            self._round_robin_counters[service_name] = 0
        
        index = self._round_robin_counters[service_name] % len(instances)
        self._round_robin_counters[service_name] += 1
        
        return instances[index]
    
    def _least_connections(self, instances: List[ServiceInstance]) -> ServiceInstance:
        """最少连接算法（简化版本，基于最近健康检查时间）"""
        return min(instances, key=lambda x: x.last_health_check or datetime.min)

def create_service_registry_app(registry: ServiceRegistry):
    """创建服务注册中心Flask应用"""
    app = Flask(__name__)
    
    @app.route('/health')
    def health():
        """健康检查"""
        return jsonify({
            'status': 'healthy',
            'service': 'service_registry',
            'timestamp': datetime.utcnow().isoformat(),
            'registered_services': len(registry.get_all_services())
        })
    
    @app.route('/services', methods=['GET'])
    def list_services():
        """列出所有服务"""
        services = registry.get_all_services()
        
        result = {}
        for service_name, instances in services.items():
            result[service_name] = []
            for instance in instances:
                result[service_name].append({
                    'instance_id': instance.instance_id,
                    'host': instance.host,
                    'port': instance.port,
                    'status': instance.status,
                    'last_health_check': instance.last_health_check.isoformat() if instance.last_health_check else None,
                    'registered_at': instance.registered_at.isoformat(),
                    'metadata': instance.metadata
                })
        
        return jsonify(format_success_response(result))
    
    @app.route('/services/<service_name>', methods=['GET'])
    def discover_service_instances(service_name: str):
        """发现特定服务的实例"""
        healthy_only = request.args.get('healthy_only', 'true').lower() == 'true'
        instances = registry.discover_service(service_name, healthy_only)
        
        result = []
        for instance in instances:
            result.append({
                'instance_id': instance.instance_id,
                'base_url': instance.base_url,
                'host': instance.host,
                'port': instance.port,
                'status': instance.status,
                'last_health_check': instance.last_health_check.isoformat() if instance.last_health_check else None,
                'metadata': instance.metadata
            })
        
        return jsonify(format_success_response(result))
    
    @app.route('/services/register', methods=['POST'])
    def register_service():
        """注册服务实例"""
        try:
            data = request.get_json()
            required_fields = ['service_name', 'instance_id', 'host', 'port']
            
            for field in required_fields:
                if field not in data:
                    return jsonify(format_error_response(
                        'MISSING_FIELD',
                        f'Required field missing: {field}'
                    )), 400
            
            success = registry.register_service(
                service_name=data['service_name'],
                instance_id=data['instance_id'],
                host=data['host'],
                port=data['port'],
                health_endpoint=data.get('health_endpoint', '/health'),
                metadata=data.get('metadata', {})
            )
            
            if success:
                return jsonify(format_success_response({
                    'message': 'Service registered successfully',
                    'service_name': data['service_name'],
                    'instance_id': data['instance_id']
                }))
            else:
                return jsonify(format_error_response(
                    'REGISTRATION_FAILED',
                    'Failed to register service'
                )), 500
                
        except Exception as e:
            logger.error(f"Service registration error: {e}")
            return jsonify(format_error_response(
                'REGISTRATION_ERROR',
                str(e)
            )), 500
    
    @app.route('/services/<service_name>/<instance_id>/heartbeat', methods=['POST'])
    def service_heartbeat(service_name: str, instance_id: str):
        """服务心跳"""
        success = registry.heartbeat(service_name, instance_id)
        
        if success:
            return jsonify(format_success_response({
                'message': 'Heartbeat received',
                'timestamp': datetime.utcnow().isoformat()
            }))
        else:
            return jsonify(format_error_response(
                'SERVICE_NOT_FOUND',
                'Service instance not found'
            )), 404
    
    @app.route('/services/<service_name>/<instance_id>', methods=['DELETE'])
    def deregister_service(service_name: str, instance_id: str):
        """注销服务实例"""
        success = registry.deregister_service(service_name, instance_id)
        
        if success:
            return jsonify(format_success_response({
                'message': 'Service deregistered successfully'
            }))
        else:
            return jsonify(format_error_response(
                'SERVICE_NOT_FOUND',
                'Service instance not found'
            )), 404
    
    return app

# 全局服务注册中心实例
service_registry = ServiceRegistry()
load_balancer = LoadBalancer(service_registry)

def start_service_registry_server(port: int = 5005):
    """启动服务注册中心服务器"""
    app = create_service_registry_app(service_registry)
    service_registry.start_health_monitoring()
    
    try:
        app.run(host='0.0.0.0', port=port, debug=False)
    except KeyboardInterrupt:
        logger.info("Shutting down service registry")
    finally:
        service_registry.stop_health_monitoring()

if __name__ == '__main__':
    import os
    port = int(os.environ.get('SERVICE_REGISTRY_PORT', 5005))
    start_service_registry_server(port)
