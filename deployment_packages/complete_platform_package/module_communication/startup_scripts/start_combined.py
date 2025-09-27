"""
Combined Deployment Startup Script
组合部署启动脚本 - 启动所有模块和API网关
"""

import os
import sys
import subprocess
import time
import logging
from typing import Dict, List

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from module_communication.deploy_config import deployment_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CombinedDeploymentStarter:
    """组合部署启动器"""
    
    def __init__(self):
        self.processes = {}
        
        # 启动顺序：服务注册中心 -> 各模块 -> API网关
        self.startup_order = [
            'service_registry',
            'user_management',
            'mining_core',
            'web3_integration',
            'api_gateway'
        ]
        
        self.service_configs = {
            'service_registry': {
                'module_path': 'module_communication.service_registry',
                'port': deployment_config.module_ports['service_registry'],
                'startup_delay': 2
            },
            'user_management': {
                'module_path': 'user_management_module.app',
                'port': deployment_config.module_ports['user_management'],
                'startup_delay': 3
            },
            'mining_core': {
                'module_path': 'mining_core_module.app',
                'port': deployment_config.module_ports['mining_core'],
                'startup_delay': 2
            },
            'web3_integration': {
                'module_path': 'web3_integration_module.app',
                'port': deployment_config.module_ports['web3_integration'],
                'startup_delay': 2
            },
            'api_gateway': {
                'module_path': 'module_communication.api_gateway',
                'port': deployment_config.module_ports['api_gateway'],
                'startup_delay': 3
            }
        }
    
    def setup_environment(self):
        """设置环境变量"""
        env_vars = {
            'DEPLOYMENT_MODE': 'combined',
            'ENVIRONMENT': 'development',
            'PYTHONPATH': project_root,
            
            # 模块端口
            'MINING_CORE_PORT': str(deployment_config.module_ports['mining_core']),
            'WEB3_INTEGRATION_PORT': str(deployment_config.module_ports['web3_integration']),
            'USER_MANAGEMENT_PORT': str(deployment_config.module_ports['user_management']),
            'API_GATEWAY_PORT': str(deployment_config.module_ports['api_gateway']),
            'SERVICE_REGISTRY_PORT': str(deployment_config.module_ports['service_registry']),
            
            # 模块主机
            'MINING_CORE_HOST': deployment_config.module_hosts['mining_core'],
            'WEB3_INTEGRATION_HOST': deployment_config.module_hosts['web3_integration'],
            'USER_MANAGEMENT_HOST': deployment_config.module_hosts['user_management'],
            'API_GATEWAY_HOST': deployment_config.module_hosts['api_gateway'],
            'SERVICE_REGISTRY_HOST': deployment_config.module_hosts['service_registry'],
            
            # 数据库
            'DATABASE_URL': os.environ.get('DATABASE_URL', 'postgresql://localhost:5432/hashinsight'),
            
            # 安全配置
            'JWT_SECRET_KEY': os.environ.get('JWT_SECRET_KEY', 'dev_secret_key_change_in_production'),
            'SESSION_SECRET': os.environ.get('SESSION_SECRET', 'dev_session_secret_change_in_production'),
            
            # API Keys
            'API_KEY': os.environ.get('API_KEY', 'dev_api_key_change_in_production')
        }
        
        # 更新当前环境
        os.environ.update(env_vars)
        
        return env_vars
    
    def start_service(self, service_name: str) -> bool:
        """启动单个服务"""
        if service_name not in self.service_configs:
            logger.error(f"Unknown service: {service_name}")
            return False
        
        if service_name in self.processes:
            logger.warning(f"Service {service_name} is already running")
            return True
        
        config = self.service_configs[service_name]
        port = config['port']
        
        # 准备环境变量
        env = os.environ.copy()
        
        try:
            # 启动服务
            cmd = [sys.executable, '-m', config['module_path']]
            
            logger.info(f"Starting {service_name} on port {port}...")
            
            process = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=project_root
            )
            
            # 等待服务启动
            startup_delay = config.get('startup_delay', 2)
            time.sleep(startup_delay)
            
            # 检查进程是否还在运行
            if process.poll() is None:
                self.processes[service_name] = process
                logger.info(f"Service {service_name} started successfully (PID: {process.pid})")
                
                # 验证健康检查
                time.sleep(1)
                if self.check_service_health(service_name):
                    logger.info(f"Service {service_name} health check passed")
                else:
                    logger.warning(f"Service {service_name} health check failed (may need more time)")
                
                return True
            else:
                stdout, stderr = process.communicate()
                logger.error(f"Service {service_name} failed to start:")
                logger.error(f"STDOUT: {stdout.decode()}")
                logger.error(f"STDERR: {stderr.decode()}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to start service {service_name}: {e}")
            return False
    
    def check_service_health(self, service_name: str) -> bool:
        """检查服务健康状态"""
        if service_name not in self.service_configs:
            return False
        
        port = self.service_configs[service_name]['port']
        
        try:
            import requests
            response = requests.get(f"http://localhost:{port}/health", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def stop_service(self, service_name: str) -> bool:
        """停止单个服务"""
        if service_name not in self.processes:
            logger.warning(f"Service {service_name} is not running")
            return True
        
        try:
            process = self.processes[service_name]
            process.terminate()
            
            # 等待进程结束
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                logger.warning(f"Force killing service {service_name}")
                process.kill()
                process.wait()
            
            del self.processes[service_name]
            logger.info(f"Service {service_name} stopped")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop service {service_name}: {e}")
            return False
    
    def start_all(self) -> bool:
        """按顺序启动所有服务"""
        logger.info("Starting HashInsight Combined Deployment...")
        
        # 设置环境变量
        self.setup_environment()
        
        # 按顺序启动服务
        for service_name in self.startup_order:
            logger.info(f"Starting {service_name}...")
            
            if not self.start_service(service_name):
                logger.error(f"Failed to start {service_name}, stopping deployment")
                self.stop_all()
                return False
            
            # 给服务时间完全启动
            time.sleep(1)
        
        logger.info("All services started successfully!")
        logger.info("-" * 50)
        self.show_status()
        logger.info("-" * 50)
        
        return True
    
    def stop_all(self):
        """按相反顺序停止所有服务"""
        logger.info("Stopping all services...")
        
        # 按相反顺序停止
        for service_name in reversed(self.startup_order):
            if service_name in self.processes:
                self.stop_service(service_name)
        
        logger.info("All services stopped")
    
    def show_status(self):
        """显示所有服务状态"""
        logger.info("Service Status:")
        
        for service_name in self.startup_order:
            config = self.service_configs[service_name]
            port = config['port']
            
            if service_name in self.processes:
                process = self.processes[service_name]
                if process.poll() is None:
                    health = "✓" if self.check_service_health(service_name) else "✗"
                    logger.info(f"  {service_name:20} Running (:{port}) {health}")
                else:
                    logger.info(f"  {service_name:20} Dead (:{port}) ✗")
                    del self.processes[service_name]
            else:
                logger.info(f"  {service_name:20} Stopped (:{port}) -")
    
    def wait_for_interrupt(self):
        """等待中断信号"""
        logger.info("Combined deployment is running. Press Ctrl+C to stop all services.")
        logger.info(f"API Gateway available at: http://localhost:{deployment_config.module_ports['api_gateway']}")
        logger.info("Available endpoints:")
        logger.info(f"  - Mining API: http://localhost:{deployment_config.module_ports['api_gateway']}/api/mining")
        logger.info(f"  - Web3 API: http://localhost:{deployment_config.module_ports['api_gateway']}/api/web3")
        logger.info(f"  - User API: http://localhost:{deployment_config.module_ports['api_gateway']}/api/users")
        
        try:
            while True:
                time.sleep(10)
                
                # 定期检查进程状态
                for service_name in list(self.processes.keys()):
                    process = self.processes[service_name]
                    if process.poll() is not None:
                        logger.warning(f"Service {service_name} died unexpectedly")
                        del self.processes[service_name]
                
                # 如果没有运行的进程，退出
                if not self.processes:
                    logger.warning("All services have stopped")
                    break
                    
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
            self.stop_all()

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='HashInsight Combined Deployment Starter')
    parser.add_argument('action', choices=['start', 'stop', 'restart', 'status'], 
                       help='Action to perform')
    
    args = parser.parse_args()
    
    starter = CombinedDeploymentStarter()
    
    try:
        if args.action == 'start':
            if starter.start_all():
                starter.wait_for_interrupt()
        
        elif args.action == 'stop':
            starter.stop_all()
        
        elif args.action == 'restart':
            starter.stop_all()
            time.sleep(2)
            if starter.start_all():
                starter.wait_for_interrupt()
        
        elif args.action == 'status':
            starter.show_status()
    
    except Exception as e:
        logger.error(f"Deployment error: {e}")
        starter.stop_all()
        sys.exit(1)

if __name__ == '__main__':
    main()