"""
Module Communication Configuration
模块间通信配置管理
"""

import os
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class ModuleCommunicationConfig:
    """模块间通信配置类"""
    
    # 模块默认配置
    DEFAULT_MODULES = {
        'mining_core': {
            'host': os.environ.get('MINING_CORE_HOST', 'localhost'),
            'port': int(os.environ.get('MINING_CORE_PORT', 5001)),
            'base_url': None,  # 将在初始化时构建
            'timeout': 30,
            'max_retries': 3,
            'health_endpoint': '/health'
        },
        'web3_integration': {
            'host': os.environ.get('WEB3_INTEGRATION_HOST', 'localhost'),
            'port': int(os.environ.get('WEB3_INTEGRATION_PORT', 5002)),
            'base_url': None,
            'timeout': 30,
            'max_retries': 3,
            'health_endpoint': '/health'
        },
        'user_management': {
            'host': os.environ.get('USER_MANAGEMENT_HOST', 'localhost'),
            'port': int(os.environ.get('USER_MANAGEMENT_PORT', 5003)),
            'base_url': None,
            'timeout': 30,
            'max_retries': 3,
            'health_endpoint': '/health'
        }
    }
    
    def __init__(self):
        """初始化配置"""
        self.modules = self._load_module_config()
        self.jwt_config = self._load_jwt_config()
        self.security_config = self._load_security_config()
        self.api_gateway_config = self._load_api_gateway_config()
        
        # 构建模块base_url
        for module_name, config in self.modules.items():
            if config['base_url'] is None:
                protocol = 'https' if os.environ.get('USE_HTTPS', 'false').lower() == 'true' else 'http'
                config['base_url'] = f"{protocol}://{config['host']}:{config['port']}"
        
        logger.info("Module communication configuration loaded")
    
    def _load_module_config(self) -> Dict:
        """加载模块配置"""
        config = self.DEFAULT_MODULES.copy()
        
        # 允许从环境变量覆盖配置
        for module_name in config.keys():
            env_prefix = f"{module_name.upper()}_"
            
            # 检查自定义base_url
            base_url_key = f"{env_prefix}BASE_URL"
            if os.environ.get(base_url_key):
                config[module_name]['base_url'] = os.environ[base_url_key]
            
            # 检查超时配置
            timeout_key = f"{env_prefix}TIMEOUT"
            if os.environ.get(timeout_key):
                config[module_name]['timeout'] = int(os.environ[timeout_key])
        
        return config
    
    def _load_jwt_config(self) -> Dict:
        """加载JWT配置"""
        return {
            'secret_key': os.environ.get('JWT_SECRET_KEY') or os.environ.get('SESSION_SECRET'),
            'algorithm': os.environ.get('JWT_ALGORITHM', 'HS256'),
            'expiration_delta': int(os.environ.get('JWT_EXPIRATION_HOURS', 24)) * 3600,
            'issuer': os.environ.get('JWT_ISSUER', 'module_communication'),
            'audience': os.environ.get('JWT_AUDIENCE', 'hashinsight_modules')
        }
    
    def _load_security_config(self) -> Dict:
        """加载安全配置"""
        return {
            'api_key_header': 'X-API-Key',
            'jwt_header': 'Authorization',
            'jwt_prefix': 'Bearer ',
            'rate_limit_enabled': os.environ.get('RATE_LIMIT_ENABLED', 'true').lower() == 'true',
            'rate_limit_per_minute': int(os.environ.get('RATE_LIMIT_PER_MINUTE', 100)),
            'request_signing_enabled': os.environ.get('REQUEST_SIGNING_ENABLED', 'false').lower() == 'true',
            'signature_header': 'X-Signature',
            'timestamp_header': 'X-Timestamp',
            'signature_tolerance': int(os.environ.get('SIGNATURE_TOLERANCE', 300))  # 5分钟
        }
    
    def _load_api_gateway_config(self) -> Dict:
        """加载API网关配置"""
        return {
            'enabled': os.environ.get('API_GATEWAY_ENABLED', 'false').lower() == 'true',
            'host': os.environ.get('API_GATEWAY_HOST', 'localhost'),
            'port': int(os.environ.get('API_GATEWAY_PORT', 5000)),
            'load_balancing': os.environ.get('LOAD_BALANCING_ENABLED', 'false').lower() == 'true',
            'circuit_breaker_enabled': os.environ.get('CIRCUIT_BREAKER_ENABLED', 'true').lower() == 'true',
            'circuit_breaker_threshold': int(os.environ.get('CIRCUIT_BREAKER_THRESHOLD', 5)),
            'circuit_breaker_timeout': int(os.environ.get('CIRCUIT_BREAKER_TIMEOUT', 60))
        }
    
    def get_module_config(self, module_name: str) -> Optional[Dict]:
        """获取指定模块配置"""
        return self.modules.get(module_name)
    
    def get_module_url(self, module_name: str, endpoint: str = '') -> Optional[str]:
        """获取模块完整URL"""
        config = self.get_module_config(module_name)
        if not config:
            return None
        
        base_url = config['base_url'].rstrip('/')
        endpoint = endpoint.lstrip('/')
        
        return f"{base_url}/{endpoint}" if endpoint else base_url
    
    def validate_configuration(self) -> bool:
        """验证配置有效性"""
        errors = []
        
        # 验证JWT配置
        if not self.jwt_config['secret_key']:
            errors.append("JWT secret key is required")
        
        # 验证模块配置
        for module_name, config in self.modules.items():
            if not config['host'] or not config['port']:
                errors.append(f"Invalid configuration for module {module_name}")
        
        if errors:
            logger.error(f"Configuration validation failed: {errors}")
            return False
        
        logger.info("Configuration validation passed")
        return True

# 全局配置实例
config = ModuleCommunicationConfig()