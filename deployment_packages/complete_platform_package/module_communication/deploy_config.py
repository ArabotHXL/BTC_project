"""
Deployment Configuration for Module Communication
模块通信部署配置 - 支持独立运行和组合部署
"""

import os
import json
from typing import Dict, Any, List, Optional

class DeploymentConfig:
    """部署配置管理器"""
    
    def __init__(self):
        self.deployment_mode = os.environ.get('DEPLOYMENT_MODE', 'standalone')  # standalone, combined, gateway
        self.environment = os.environ.get('ENVIRONMENT', 'development')  # development, staging, production
        
        # 基础配置
        self.base_config = {
            'security': {
                'use_https': self.environment != 'development',
                'api_key_rotation_hours': 24,
                'jwt_expiration_hours': 24,
                'rate_limit_per_minute': 100
            },
            'monitoring': {
                'health_check_interval': 30,
                'metrics_collection': True,
                'log_level': 'INFO' if self.environment == 'production' else 'DEBUG'
            },
            'communication': {
                'timeout_seconds': 30,
                'retry_attempts': 3,
                'retry_delay_seconds': 1.0,
                'circuit_breaker_threshold': 5
            }
        }
        
        # 模块端口配置
        self.module_ports = {
            'mining_core': int(os.environ.get('MINING_CORE_PORT', 5001)),
            'web3_integration': int(os.environ.get('WEB3_INTEGRATION_PORT', 5002)),
            'user_management': int(os.environ.get('USER_MANAGEMENT_PORT', 5003)),
            'api_gateway': int(os.environ.get('API_GATEWAY_PORT', 5000)),
            'service_registry': int(os.environ.get('SERVICE_REGISTRY_PORT', 5005))
        }
        
        # 模块主机配置
        self.module_hosts = {
            'mining_core': os.environ.get('MINING_CORE_HOST', 'localhost'),
            'web3_integration': os.environ.get('WEB3_INTEGRATION_HOST', 'localhost'),
            'user_management': os.environ.get('USER_MANAGEMENT_HOST', 'localhost'),
            'api_gateway': os.environ.get('API_GATEWAY_HOST', '0.0.0.0'),
            'service_registry': os.environ.get('SERVICE_REGISTRY_HOST', 'localhost')
        }
    
    def get_module_config(self, module_name: str) -> Dict[str, Any]:
        """获取特定模块的配置"""
        base_url = f"{'https' if self.base_config['security']['use_https'] else 'http'}://{self.module_hosts.get(module_name, 'localhost')}:{self.module_ports.get(module_name, 5000)}"
        
        config = {
            'module_name': module_name,
            'host': self.module_hosts.get(module_name, 'localhost'),
            'port': self.module_ports.get(module_name, 5000),
            'base_url': base_url,
            'health_endpoint': '/health',
            'deployment_mode': self.deployment_mode,
            'environment': self.environment,
            **self.base_config
        }
        
        # 模块特定配置
        if module_name == 'mining_core':
            config.update({
                'features': [
                    'profitability_calculation',
                    'market_analysis',
                    'technical_indicators',
                    'batch_processing'
                ],
                'dependencies': ['user_management'],
                'optional_dependencies': ['web3_integration']
            })
        
        elif module_name == 'web3_integration':
            config.update({
                'features': [
                    'wallet_authentication',
                    'cryptocurrency_payments',
                    'nft_minting',
                    'ipfs_storage',
                    'kyc_compliance'
                ],
                'dependencies': ['user_management'],
                'blockchain_networks': ['ethereum', 'polygon', 'bitcoin']
            })
        
        elif module_name == 'user_management':
            config.update({
                'features': [
                    'user_authentication',
                    'subscription_management',
                    'crm_system',
                    'billing_management',
                    'admin_panel'
                ],
                'dependencies': [],
                'database_required': True
            })
        
        elif module_name == 'api_gateway':
            config.update({
                'enabled': self.deployment_mode in ['combined', 'gateway'],
                'features': [
                    'request_routing',
                    'load_balancing',
                    'rate_limiting',
                    'authentication_proxy'
                ],
                'route_mappings': {
                    '/api/mining': 'mining_core',
                    '/api/web3': 'web3_integration',
                    '/api/users': 'user_management',
                    '/api/auth': 'user_management'
                }
            })
        
        return config
    
    def get_all_configs(self) -> Dict[str, Any]:
        """获取所有模块配置"""
        modules = ['mining_core', 'web3_integration', 'user_management', 'api_gateway', 'service_registry']
        
        configs = {}
        for module in modules:
            configs[module] = self.get_module_config(module)
        
        return configs
    
    def generate_docker_compose(self) -> str:
        """生成Docker Compose配置"""
        compose_config = {
            'version': '3.8',
            'services': {},
            'networks': {
                'hashinsight_network': {
                    'driver': 'bridge'
                }
            },
            'volumes': {
                'postgres_data': {}
            }
        }
        
        # PostgreSQL服务
        if self.deployment_mode in ['combined', 'standalone']:
            compose_config['services']['postgres'] = {
                'image': 'postgres:15',
                'environment': {
                    'POSTGRES_DB': 'hashinsight',
                    'POSTGRES_USER': 'hashinsight',
                    'POSTGRES_PASSWORD': 'hashinsight_password'
                },
                'volumes': ['postgres_data:/var/lib/postgresql/data'],
                'ports': ['5432:5432'],
                'networks': ['hashinsight_network']
            }
        
        # 服务注册中心
        if self.deployment_mode in ['combined', 'gateway']:
            compose_config['services']['service_registry'] = {
                'build': '.',
                'command': 'python -m module_communication.service_registry',
                'ports': [f"{self.module_ports['service_registry']}:{self.module_ports['service_registry']}"],
                'networks': ['hashinsight_network'],
                'environment': {
                    'SERVICE_REGISTRY_PORT': self.module_ports['service_registry']
                }
            }
        
        # API网关
        if self.deployment_mode in ['combined', 'gateway']:
            compose_config['services']['api_gateway'] = {
                'build': '.',
                'command': 'python -m module_communication.api_gateway',
                'ports': [f"{self.module_ports['api_gateway']}:{self.module_ports['api_gateway']}"],
                'networks': ['hashinsight_network'],
                'depends_on': ['service_registry'],
                'environment': {
                    'API_GATEWAY_PORT': self.module_ports['api_gateway'],
                    'DEPLOYMENT_MODE': self.deployment_mode
                }
            }
        
        # 各个模块服务
        modules = ['user_management', 'mining_core', 'web3_integration']
        
        for module in modules:
            service_config = {
                'build': '.',
                'command': f'python -m {module}_module.app',
                'ports': [f"{self.module_ports[module]}:{self.module_ports[module]}"],
                'networks': ['hashinsight_network'],
                'environment': {
                    f'{module.upper()}_PORT': self.module_ports[module],
                    'DEPLOYMENT_MODE': self.deployment_mode,
                    'ENVIRONMENT': self.environment
                }
            }
            
            # 用户管理模块需要数据库
            if module == 'user_management':
                service_config['depends_on'] = ['postgres']
                service_config['environment']['DATABASE_URL'] = 'postgresql://hashinsight:hashinsight_password@postgres:5432/hashinsight'
            
            # 如果是组合部署，依赖服务注册中心
            if self.deployment_mode in ['combined', 'gateway']:
                service_config.setdefault('depends_on', []).append('service_registry')
            
            compose_config['services'][module.replace('_', '-')] = service_config
        
        return json.dumps(compose_config, indent=2)
    
    def generate_kubernetes_manifests(self) -> Dict[str, str]:
        """生成Kubernetes清单文件"""
        manifests = {}
        
        # 命名空间
        manifests['namespace.yaml'] = """
apiVersion: v1
kind: Namespace
metadata:
  name: hashinsight
"""
        
        # ConfigMap
        manifests['configmap.yaml'] = f"""
apiVersion: v1
kind: ConfigMap
metadata:
  name: hashinsight-config
  namespace: hashinsight
data:
  DEPLOYMENT_MODE: "{self.deployment_mode}"
  ENVIRONMENT: "{self.environment}"
  MINING_CORE_PORT: "{self.module_ports['mining_core']}"
  WEB3_INTEGRATION_PORT: "{self.module_ports['web3_integration']}"
  USER_MANAGEMENT_PORT: "{self.module_ports['user_management']}"
  API_GATEWAY_PORT: "{self.module_ports['api_gateway']}"
"""
        
        # 为每个模块生成Deployment和Service
        modules = ['user_management', 'mining_core', 'web3_integration']
        
        for module in modules:
            module_name = module.replace('_', '-')
            port = self.module_ports[module]
            
            manifests[f'{module_name}-deployment.yaml'] = f"""
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {module_name}
  namespace: hashinsight
spec:
  replicas: 2
  selector:
    matchLabels:
      app: {module_name}
  template:
    metadata:
      labels:
        app: {module_name}
    spec:
      containers:
      - name: {module_name}
        image: hashinsight/{module_name}:latest
        ports:
        - containerPort: {port}
        envFrom:
        - configMapRef:
            name: hashinsight-config
        livenessProbe:
          httpGet:
            path: /health
            port: {port}
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: {port}
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: {module_name}-service
  namespace: hashinsight
spec:
  selector:
    app: {module_name}
  ports:
  - port: {port}
    targetPort: {port}
  type: ClusterIP
"""
        
        # API网关
        if self.deployment_mode in ['combined', 'gateway']:
            manifests['api-gateway-deployment.yaml'] = f"""
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-gateway
  namespace: hashinsight
spec:
  replicas: 2
  selector:
    matchLabels:
      app: api-gateway
  template:
    metadata:
      labels:
        app: api-gateway
    spec:
      containers:
      - name: api-gateway
        image: hashinsight/api-gateway:latest
        ports:
        - containerPort: {self.module_ports['api_gateway']}
        envFrom:
        - configMapRef:
            name: hashinsight-config
---
apiVersion: v1
kind: Service
metadata:
  name: api-gateway-service
  namespace: hashinsight
spec:
  selector:
    app: api-gateway
  ports:
  - port: {self.module_ports['api_gateway']}
    targetPort: {self.module_ports['api_gateway']}
  type: LoadBalancer
"""
        
        return manifests
    
    def save_configs_to_files(self, output_dir: str = 'deployment_configs'):
        """保存配置到文件"""
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        # 保存Docker Compose
        with open(f'{output_dir}/docker-compose.yml', 'w') as f:
            f.write(self.generate_docker_compose())
        
        # 保存Kubernetes manifests
        k8s_manifests = self.generate_kubernetes_manifests()
        k8s_dir = f'{output_dir}/kubernetes'
        os.makedirs(k8s_dir, exist_ok=True)
        
        for filename, content in k8s_manifests.items():
            with open(f'{k8s_dir}/{filename}', 'w') as f:
                f.write(content)
        
        # 保存模块配置
        configs = self.get_all_configs()
        with open(f'{output_dir}/module_configs.json', 'w') as f:
            json.dump(configs, f, indent=2)
        
        print(f"Configuration files saved to {output_dir}/")

# 全局部署配置实例
deployment_config = DeploymentConfig()

if __name__ == '__main__':
    # 生成配置文件
    deployment_config.save_configs_to_files()
    
    # 打印当前配置
    print("Current deployment configuration:")
    configs = deployment_config.get_all_configs()
    for module, config in configs.items():
        print(f"\n{module}:")
        print(f"  Host: {config['host']}")
        print(f"  Port: {config['port']}")
        print(f"  Base URL: {config['base_url']}")
        if 'features' in config:
            print(f"  Features: {', '.join(config['features'])}")