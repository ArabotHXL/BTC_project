"""
Service Integration Module
服务集成模块 - 将应用注册到服务发现系统并提供心跳检测
"""

import os
import time
import logging
import threading
import requests
from datetime import datetime
from typing import Dict, Optional, Any
from flask import Flask

logger = logging.getLogger(__name__)

class ServiceRegistration:
    """服务注册管理器"""
    
    def __init__(self, app: Flask = None):
        self.app = app
        self.service_name = None
        self.instance_id = None
        self.host = None
        self.port = None
        self.service_registry_url = None
        self.heartbeat_interval = 30  # 30秒心跳间隔
        self.heartbeat_thread = None
        self.running = False
        
        if app:
            self.init_app(app)
    
    def init_app(self, app: Flask):
        """初始化Flask应用"""
        self.app = app
        
        # 配置服务参数
        self.service_name = os.environ.get('SERVICE_NAME', 'main_application')
        self.instance_id = f"{self.service_name}_{int(time.time())}"
        self.host = os.environ.get('SERVICE_HOST', '0.0.0.0')
        self.port = int(os.environ.get('SERVICE_PORT', 5000))
        
        # 服务注册中心配置
        registry_host = os.environ.get('SERVICE_REGISTRY_HOST', 'localhost')
        registry_port = int(os.environ.get('SERVICE_REGISTRY_PORT', 8500))
        self.service_registry_url = f"http://{registry_host}:{registry_port}"
        
        # 服务元数据
        self.metadata = {
            'version': '1.0.0',
            'environment': os.environ.get('FLASK_ENV', 'development'),
            'capabilities': ['calculation', 'analytics', 'treasury', 'mining'],
            'api_version': 'v1',
            'auth_required': True,
            'health_check_interval': 30
        }
        
        # 添加健康检查端点（如果不存在）
        self._add_health_endpoint()
        
        logger.info(f"Service registration initialized for {self.service_name}")
    
    def _add_health_endpoint(self):
        """添加健康检查端点"""
        if self.app:
            @self.app.route('/health', methods=['GET'])
            def service_health():
                return {
                    'status': 'healthy',
                    'service': self.service_name,
                    'instance_id': self.instance_id,
                    'timestamp': datetime.utcnow().isoformat(),
                    'uptime': time.time() - self.app.start_time if hasattr(self.app, 'start_time') else 0,
                    'version': self.metadata.get('version', '1.0.0'),
                    'capabilities': self.metadata.get('capabilities', [])
                }
    
    def register_service(self) -> bool:
        """注册服务到服务发现系统"""
        if not self.service_registry_url:
            logger.warning("Service registry URL not configured, skipping registration")
            return False
        
        registration_data = {
            'service_name': self.service_name,
            'instance_id': self.instance_id,
            'host': self.host,
            'port': self.port,
            'health_endpoint': '/health',
            'metadata': self.metadata
        }
        
        try:
            response = requests.post(
                f"{self.service_registry_url}/api/registry/register",
                json=registration_data,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"Service {self.service_name} registered successfully")
                return True
            else:
                logger.error(f"Service registration failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Service registration failed: {e}")
            return False
    
    def deregister_service(self) -> bool:
        """从服务发现系统注销服务"""
        if not self.service_registry_url or not self.instance_id:
            return False
        
        try:
            response = requests.delete(
                f"{self.service_registry_url}/api/registry/deregister/{self.instance_id}",
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"Service {self.service_name} deregistered successfully")
                return True
            else:
                logger.warning(f"Service deregistration failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.warning(f"Service deregistration failed: {e}")
            return False
    
    def send_heartbeat(self) -> bool:
        """发送心跳到服务注册中心"""
        if not self.service_registry_url or not self.instance_id:
            return False
        
        heartbeat_data = {
            'instance_id': self.instance_id,
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'metadata': self.metadata
        }
        
        try:
            response = requests.post(
                f"{self.service_registry_url}/api/registry/heartbeat",
                json=heartbeat_data,
                timeout=5
            )
            
            if response.status_code == 200:
                logger.debug(f"Heartbeat sent successfully for {self.service_name}")
                return True
            else:
                logger.warning(f"Heartbeat failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.warning(f"Heartbeat failed: {e}")
            return False
    
    def _heartbeat_worker(self):
        """心跳工作线程"""
        logger.info(f"Heartbeat worker started for {self.service_name}")
        
        while self.running:
            try:
                self.send_heartbeat()
                time.sleep(self.heartbeat_interval)
            except Exception as e:
                logger.error(f"Heartbeat worker error: {e}")
                time.sleep(self.heartbeat_interval)
        
        logger.info(f"Heartbeat worker stopped for {self.service_name}")
    
    def start_heartbeat(self):
        """启动心跳线程"""
        if self.heartbeat_thread and self.heartbeat_thread.is_alive():
            logger.warning("Heartbeat already running")
            return
        
        self.running = True
        self.heartbeat_thread = threading.Thread(
            target=self._heartbeat_worker,
            daemon=True,
            name=f"Heartbeat-{self.service_name}"
        )
        self.heartbeat_thread.start()
        logger.info(f"Heartbeat started for {self.service_name}")
    
    def stop_heartbeat(self):
        """停止心跳线程"""
        self.running = False
        if self.heartbeat_thread:
            self.heartbeat_thread.join(timeout=5)
        logger.info(f"Heartbeat stopped for {self.service_name}")
    
    def discover_service(self, service_name: str) -> Optional[Dict[str, Any]]:
        """发现其他服务"""
        if not self.service_registry_url:
            return None
        
        try:
            response = requests.get(
                f"{self.service_registry_url}/api/registry/discover/{service_name}",
                timeout=10
            )
            
            if response.status_code == 200:
                services = response.json().get('services', [])
                return services[0] if services else None
            else:
                logger.warning(f"Service discovery failed for {service_name}: {response.status_code}")
                return None
                
        except Exception as e:
            logger.warning(f"Service discovery failed for {service_name}: {e}")
            return None
    
    def get_service_url(self, service_name: str) -> Optional[str]:
        """获取服务URL"""
        service = self.discover_service(service_name)
        if service:
            protocol = 'https' if service.get('metadata', {}).get('use_https', False) else 'http'
            return f"{protocol}://{service['host']}:{service['port']}"
        return None

class GatewayRouter:
    """网关路由器"""
    
    def __init__(self, service_registration: ServiceRegistration):
        self.service_registration = service_registration
        self.route_mapping = {
            '/api/mining': 'mining_core',
            '/api/web3': 'web3_integration',
            '/api/users': 'user_management',
            '/api/auth': 'user_management',
            '/api/billing': 'user_management',
            '/api/crm': 'user_management'
        }
    
    def route_request(self, path: str, method: str = 'GET', **kwargs) -> Optional[str]:
        """将请求路由到相应的服务"""
        for prefix, service_name in self.route_mapping.items():
            if path.startswith(prefix):
                service_url = self.service_registration.get_service_url(service_name)
                if service_url:
                    # 构建完整的目标URL
                    target_path = path[len(prefix):] if path != prefix else ''
                    return f"{service_url}{prefix}{target_path}"
        
        return None

# 全局实例
service_registration = ServiceRegistration()
gateway_router = GatewayRouter(service_registration)

def init_service_integration(app: Flask, enable_registration: bool = True, enable_heartbeat: bool = True):
    """初始化服务集成"""
    # 记录应用启动时间
    app.start_time = time.time()
    
    # 初始化服务注册
    service_registration.init_app(app)
    
    # 注册服务（如果启用）
    if enable_registration:
        deployment_mode = os.environ.get('DEPLOYMENT_MODE', 'standalone')
        
        if deployment_mode in ['combined', 'gateway']:
            # 只在组合或网关模式下注册服务
            if service_registration.register_service():
                logger.info(f"Service registered in {deployment_mode} mode")
                
                # 启动心跳（如果启用）
                if enable_heartbeat:
                    service_registration.start_heartbeat()
            else:
                logger.warning(f"Service registration failed in {deployment_mode} mode")
        else:
            logger.info(f"Service registration skipped in {deployment_mode} mode")
    
    # 添加关闭处理器
    @app.teardown_appcontext
    def cleanup_service(error):
        if error:
            logger.error(f"Application error during cleanup: {error}")
    
    # 注册关闭处理
    import atexit
    
    def shutdown_handler():
        logger.info("Shutting down service integration")
        service_registration.stop_heartbeat()
        service_registration.deregister_service()
    
    atexit.register(shutdown_handler)
    
    logger.info("Service integration initialized successfully")
    return service_registration, gateway_router

# 导出主要组件
__all__ = [
    'ServiceRegistration',
    'GatewayRouter', 
    'service_registration',
    'gateway_router',
    'init_service_integration'
]