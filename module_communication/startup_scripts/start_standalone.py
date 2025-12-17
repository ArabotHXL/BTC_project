"""
Standalone Module Startup Script
独立模块启动脚本 - 启动单个模块进行独立运行
"""

import os
import sys
import subprocess
import argparse
import time
import logging
from typing import List

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from module_communication.common.config import config
from module_communication.deploy_config import deployment_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StandaloneModuleStarter:
    """独立模块启动器"""
    
    def __init__(self):
        self.processes = {}
        self.module_configs = {
            'mining_core': {
                'module_path': 'mining_core_module.app',
                'port': deployment_config.module_ports['mining_core'],
                'dependencies': ['user_management']
            },
            'web3_integration': {
                'module_path': 'web3_integration_module.app',
                'port': deployment_config.module_ports['web3_integration'],
                'dependencies': ['user_management']
            },
            'user_management': {
                'module_path': 'user_management_module.app',
                'port': deployment_config.module_ports['user_management'],
                'dependencies': []
            }
        }
    
    def check_dependencies(self, module_name: str) -> bool:
        """检查模块依赖是否可用"""
        module_config = self.module_configs.get(module_name, {})
        dependencies = module_config.get('dependencies', [])
        
        for dep in dependencies:
            dep_port = self.module_configs[dep]['port']
            
            # 检查依赖服务是否运行
            try:
                import requests
                response = requests.get(
                    f"http://localhost:{dep_port}/health", 
                    timeout=5
                )
                if response.status_code != 200:
                    logger.warning(f"Dependency {dep} is not healthy")
                    return False
            except Exception as e:
                logger.warning(f"Cannot connect to dependency {dep}: {e}")
                return False
        
        return True
    
    def start_module(self, module_name: str, check_deps: bool = True) -> bool:
        """启动单个模块"""
        if module_name not in self.module_configs:
            logger.error(f"Unknown module: {module_name}")
            return False
        
        if module_name in self.processes:
            logger.warning(f"Module {module_name} is already running")
            return True
        
        # 检查依赖
        if check_deps and not self.check_dependencies(module_name):
            logger.error(f"Dependencies not available for {module_name}")
            return False
        
        module_config = self.module_configs[module_name]
        port = module_config['port']
        
        # 设置环境变量
        env = os.environ.copy()
        env.update({
            'DEPLOYMENT_MODE': 'standalone',
            'ENVIRONMENT': 'development',
            f'{module_name.upper()}_PORT': str(port),
            'PYTHONPATH': project_root
        })
        
        # 如果是用户管理模块，确保数据库连接
        if module_name == 'user_management':
            if not os.environ.get('DATABASE_URL'):
                env['DATABASE_URL'] = 'postgresql://localhost:5432/hashinsight'
        
        try:
            # 启动模块
            cmd = [sys.executable, '-m', module_config['module_path']]
            
            logger.info(f"Starting {module_name} on port {port}...")
            process = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=project_root
            )
            
            # 等待服务启动
            time.sleep(3)
            
            # 检查进程是否还在运行
            if process.poll() is None:
                self.processes[module_name] = process
                logger.info(f"Module {module_name} started successfully (PID: {process.pid})")
                
                # 验证健康检查
                time.sleep(2)
                if self.check_module_health(module_name):
                    logger.info(f"Module {module_name} health check passed")
                    return True
                else:
                    logger.warning(f"Module {module_name} health check failed")
                    return True  # 仍然认为启动成功，可能需要时间初始化
            else:
                stdout, stderr = process.communicate()
                logger.error(f"Module {module_name} failed to start:")
                logger.error(f"STDOUT: {stdout.decode()}")
                logger.error(f"STDERR: {stderr.decode()}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to start module {module_name}: {e}")
            return False
    
    def check_module_health(self, module_name: str) -> bool:
        """检查模块健康状态"""
        if module_name not in self.module_configs:
            return False
        
        port = self.module_configs[module_name]['port']
        
        try:
            import requests
            response = requests.get(f"http://localhost:{port}/health", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def stop_module(self, module_name: str) -> bool:
        """停止单个模块"""
        if module_name not in self.processes:
            logger.warning(f"Module {module_name} is not running")
            return True
        
        try:
            process = self.processes[module_name]
            process.terminate()
            
            # 等待进程结束
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                logger.warning(f"Force killing module {module_name}")
                process.kill()
                process.wait()
            
            del self.processes[module_name]
            logger.info(f"Module {module_name} stopped")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop module {module_name}: {e}")
            return False
    
    def start_with_dependencies(self, module_name: str) -> bool:
        """启动模块及其依赖"""
        if module_name not in self.module_configs:
            logger.error(f"Unknown module: {module_name}")
            return False
        
        # 递归启动依赖
        dependencies = self.module_configs[module_name].get('dependencies', [])
        for dep in dependencies:
            if dep not in self.processes:
                logger.info(f"Starting dependency: {dep}")
                if not self.start_with_dependencies(dep):
                    logger.error(f"Failed to start dependency {dep}")
                    return False
        
        # 启动目标模块
        return self.start_module(module_name, check_deps=False)
    
    def stop_all(self):
        """停止所有模块"""
        logger.info("Stopping all modules...")
        
        for module_name in list(self.processes.keys()):
            self.stop_module(module_name)
        
        logger.info("All modules stopped")
    
    def status(self):
        """显示所有模块状态"""
        logger.info("Module Status:")
        logger.info("-" * 50)
        
        for module_name, config in self.module_configs.items():
            port = config['port']
            
            if module_name in self.processes:
                process = self.processes[module_name]
                if process.poll() is None:
                    health = "✓" if self.check_module_health(module_name) else "✗"
                    logger.info(f"{module_name:20} Running (:{port}) {health}")
                else:
                    logger.info(f"{module_name:20} Dead (:{port}) ✗")
                    del self.processes[module_name]
            else:
                logger.info(f"{module_name:20} Stopped (:{port}) -")

def main():
    parser = argparse.ArgumentParser(description='HashInsight Standalone Module Starter')
    parser.add_argument('action', choices=['start', 'stop', 'restart', 'status'], 
                       help='Action to perform')
    parser.add_argument('module', nargs='?', 
                       choices=['mining_core', 'web3_integration', 'user_management', 'all'],
                       default='all', help='Module to manage')
    parser.add_argument('--with-deps', action='store_true', 
                       help='Start module with its dependencies')
    
    args = parser.parse_args()
    
    starter = StandaloneModuleStarter()
    
    try:
        if args.action == 'start':
            if args.module == 'all':
                # 按依赖顺序启动所有模块
                modules = ['user_management', 'mining_core', 'web3_integration']
                for module in modules:
                    starter.start_module(module, check_deps=False)
                    time.sleep(2)  # 给每个模块启动时间
            else:
                if args.with_deps:
                    starter.start_with_dependencies(args.module)
                else:
                    starter.start_module(args.module)
        
        elif args.action == 'stop':
            if args.module == 'all':
                starter.stop_all()
            else:
                starter.stop_module(args.module)
        
        elif args.action == 'restart':
            if args.module == 'all':
                starter.stop_all()
                time.sleep(2)
                modules = ['user_management', 'mining_core', 'web3_integration']
                for module in modules:
                    starter.start_module(module, check_deps=False)
                    time.sleep(2)
            else:
                starter.stop_module(args.module)
                time.sleep(1)
                if args.with_deps:
                    starter.start_with_dependencies(args.module)
                else:
                    starter.start_module(args.module)
        
        elif args.action == 'status':
            starter.status()
        
        # 如果启动了模块，保持运行
        if args.action in ['start', 'restart'] and starter.processes:
            logger.info("Modules running. Press Ctrl+C to stop all.")
            try:
                while True:
                    time.sleep(10)
                    # 定期检查进程状态
                    for module_name in list(starter.processes.keys()):
                        process = starter.processes[module_name]
                        if process.poll() is not None:
                            logger.warning(f"Module {module_name} died unexpectedly")
                            del starter.processes[module_name]
            except KeyboardInterrupt:
                logger.info("Received interrupt signal")
                starter.stop_all()
    
    except Exception as e:
        logger.error(f"Startup script error: {e}")
        starter.stop_all()
        sys.exit(1)

if __name__ == '__main__':
    main()