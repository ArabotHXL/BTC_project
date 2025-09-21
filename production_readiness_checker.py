#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生产就绪度检查器
Production Readiness Checker - Comprehensive System Health and Configuration Validator

确保系统满足生产环境要求：
- 启动前配置验证
- 关键服务健康检查  
- 故障转移机制验证
- 安全配置审查
- 性能监控就绪度

Authors: Production Engineering Team
Date: 2025-09-21
Version: 1.0.0
"""

import os
import sys
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import json
import requests
import psutil
from pathlib import Path

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ProductionReadinessChecker:
    """生产就绪度检查器"""
    
    def __init__(self):
        self.check_results = {}
        self.critical_issues = []
        self.warnings = []
        self.production_ready = False
        
    def run_startup_checks(self, fail_fast: bool = True) -> Dict[str, Any]:
        """
        运行启动前检查
        
        Args:
            fail_fast: 遇到关键问题时是否立即失败
            
        Returns:
            检查结果字典
        """
        logger.info("🚀 开始生产就绪度检查...")
        
        checks = [
            ("关键环境变量", self.check_critical_env_vars),
            ("数据库连接", self.check_database_readiness),
            ("外部服务连接", self.check_external_services),
            ("安全配置", self.check_security_configuration),
            ("区块链集成", self.check_blockchain_readiness),
            ("RPC故障转移", self.check_rpc_failover_readiness),
            ("系统资源", self.check_system_resources),
            ("监控配置", self.check_monitoring_readiness),
        ]
        
        for check_name, check_func in checks:
            try:
                logger.info(f"🔍 检查: {check_name}")
                result = check_func()
                
                self.check_results[check_name] = result
                
                if not result.get('passed', False):
                    if result.get('critical', False):
                        issue = f"{check_name}: {result.get('error', '未知错误')}"
                        self.critical_issues.append(issue)
                        logger.error(f"❌ 关键问题: {issue}")
                        
                        if fail_fast:
                            logger.error("🛑 检测到关键问题，停止启动")
                            raise SystemExit(f"启动失败: {issue}")
                    else:
                        warning = f"{check_name}: {result.get('error', '警告')}"
                        self.warnings.append(warning)
                        logger.warning(f"⚠️  警告: {warning}")
                else:
                    logger.info(f"✅ {check_name}: 通过")
                    
            except Exception as e:
                error_msg = f"{check_name}: 检查失败 - {e}"
                self.critical_issues.append(error_msg)
                logger.error(f"❌ {error_msg}")
                
                if fail_fast:
                    raise SystemExit(f"启动失败: {error_msg}")
        
        # 评估总体就绪度
        self.production_ready = len(self.critical_issues) == 0
        
        return self.generate_readiness_report()
    
    def check_critical_env_vars(self) -> Dict[str, Any]:
        """检查关键环境变量"""
        required_vars = {
            'DATABASE_URL': '数据库连接字符串',
            'SESSION_SECRET': 'Flask会话密钥',
        }
        
        # 生产环境推荐配置
        production_vars = {
            'ENCRYPTION_PASSWORD': '数据加密密钥（生产必须）',
            'ENCRYPTION_SALT': '加密盐值（生产必须）',
            'BLOCKCHAIN_PRIVATE_KEY': '区块链私钥（功能启用必需）',
            'PINATA_JWT': 'IPFS存储令牌（透明度功能必需）',
            'MINING_REGISTRY_CONTRACT_ADDRESS': '智能合约地址',
        }
        
        missing_required = []
        missing_production = []
        weak_configs = []
        
        # 检查必需变量
        for var, description in required_vars.items():
            value = os.environ.get(var)
            if not value:
                missing_required.append(f"{var} - {description}")
            elif var == 'SESSION_SECRET' and len(value) < 32:
                weak_configs.append(f"{var} - 密钥长度不足32位")
        
        # 检查生产环境变量
        for var, description in production_vars.items():
            if not os.environ.get(var):
                missing_production.append(f"{var} - {description}")
        
        # 检查环境类型
        env_type = os.environ.get('FLASK_ENV', os.environ.get('ENV', 'development'))
        is_production = env_type.lower() in ['production', 'prod']
        
        if is_production and missing_production:
            # 生产环境缺少推荐配置视为关键问题
            return {
                'passed': False,
                'critical': True,
                'error': f'生产环境缺少 {len(missing_production)} 个重要配置',
                'missing_required': missing_required,
                'missing_production': missing_production,
                'weak_configs': weak_configs,
                'environment': env_type
            }
        
        return {
            'passed': len(missing_required) == 0,
            'critical': len(missing_required) > 0,
            'error': f'缺少 {len(missing_required)} 个必需配置' if missing_required else None,
            'missing_required': missing_required,
            'missing_production': missing_production,
            'weak_configs': weak_configs,
            'environment': env_type,
            'production_mode': is_production
        }
    
    def check_database_readiness(self) -> Dict[str, Any]:
        """检查数据库就绪度"""
        try:
            from app import db
            from models import UserAccess, MinerModel  # 测试导入关键模型
            
            # 测试数据库连接
            with db.engine.connect() as conn:
                result = conn.execute(db.text("SELECT 1"))
                result.fetchone()
            
            # 检查关键表是否存在
            inspector = db.inspect(db.engine)
            existing_tables = inspector.get_table_names()
            
            critical_tables = ['user_access', 'miner_models', 'network_snapshots']
            missing_critical = [table for table in critical_tables if table not in existing_tables]
            
            if missing_critical:
                return {
                    'passed': False,
                    'critical': True,
                    'error': f'缺少关键数据表: {", ".join(missing_critical)}',
                    'existing_tables': len(existing_tables),
                    'missing_tables': missing_critical
                }
            
            # 测试写入权限
            try:
                test_user = UserAccess.query.first()  # 简单查询测试
            except Exception as e:
                return {
                    'passed': False,
                    'critical': True,
                    'error': f'数据库查询失败: {e}'
                }
            
            return {
                'passed': True,
                'table_count': len(existing_tables),
                'critical_tables_ok': True
            }
            
        except ImportError as e:
            return {
                'passed': False,
                'critical': True,
                'error': f'数据库模块导入失败: {e}'
            }
        except Exception as e:
            return {
                'passed': False,
                'critical': True,
                'error': f'数据库连接失败: {e}'
            }
    
    def check_external_services(self) -> Dict[str, Any]:
        """检查外部服务连接"""
        services = [
            {
                'name': 'CoinGecko API',
                'url': 'https://api.coingecko.com/api/v3/ping',
                'timeout': 10,
                'critical': False
            },
            {
                'name': 'Blockchain.info',
                'url': 'https://blockchain.info/q/hashrate',
                'timeout': 10,
                'critical': False
            }
        ]
        
        # 检查Pinata服务（如果配置了JWT）
        pinata_jwt = os.environ.get('PINATA_JWT')
        if pinata_jwt:
            services.append({
                'name': 'Pinata IPFS',
                'url': 'https://api.pinata.cloud/data/testAuthentication',
                'timeout': 10,
                'critical': False,
                'headers': {'Authorization': f'Bearer {pinata_jwt}'}
            })
        
        failed_critical = []
        failed_optional = []
        successful = []
        
        for service in services:
            try:
                headers = service.get('headers', {})
                response = requests.get(
                    service['url'], 
                    timeout=service['timeout'],
                    headers=headers
                )
                
                if response.status_code in [200, 401]:  # 401 for auth-required services
                    successful.append(service['name'])
                else:
                    if service['critical']:
                        failed_critical.append(f"{service['name']} (HTTP {response.status_code})")
                    else:
                        failed_optional.append(f"{service['name']} (HTTP {response.status_code})")
                        
            except Exception as e:
                if service['critical']:
                    failed_critical.append(f"{service['name']} ({str(e)})")
                else:
                    failed_optional.append(f"{service['name']} ({str(e)})")
        
        return {
            'passed': len(failed_critical) == 0,
            'critical': len(failed_critical) > 0,
            'error': f'{len(failed_critical)} 个关键服务失败' if failed_critical else None,
            'successful': successful,
            'failed_critical': failed_critical,
            'failed_optional': failed_optional,
            'total_tested': len(services)
        }
    
    def check_security_configuration(self) -> Dict[str, Any]:
        """检查安全配置"""
        security_issues = []
        warnings = []
        
        # 检查默认密码/密钥
        session_secret = os.environ.get('SESSION_SECRET', '')
        if session_secret in ['dev', 'development', 'secret', '123456']:
            security_issues.append('SESSION_SECRET使用弱默认值')
        
        # 检查加密配置
        encryption_password = os.environ.get('ENCRYPTION_PASSWORD')
        if encryption_password:
            if len(encryption_password) < 16:
                security_issues.append('ENCRYPTION_PASSWORD长度不足16位')
        else:
            warnings.append('未设置ENCRYPTION_PASSWORD，数据加密功能不可用')
        
        # 检查区块链安全配置
        private_key = os.environ.get('BLOCKCHAIN_PRIVATE_KEY')
        if private_key:
            if private_key.startswith('0x'):
                private_key = private_key[2:]
            if len(private_key) != 64:
                security_issues.append('BLOCKCHAIN_PRIVATE_KEY格式不正确')
        
        # 检查主网保护
        mainnet_writes = os.environ.get('BLOCKCHAIN_ENABLE_MAINNET_WRITES')
        if mainnet_writes and mainnet_writes.lower() == 'true':
            warnings.append('主网写入已启用，请确认这是预期配置')
        
        # 检查Flask配置
        flask_env = os.environ.get('FLASK_ENV', 'development')
        if flask_env == 'development':
            warnings.append('Flask运行在开发模式，生产环境应设置为production')
        
        return {
            'passed': len(security_issues) == 0,
            'critical': len(security_issues) > 2,
            'error': f'{len(security_issues)} 个安全问题' if security_issues else None,
            'security_issues': security_issues,
            'warnings': warnings,
            'flask_env': flask_env
        }
    
    def check_blockchain_readiness(self) -> Dict[str, Any]:
        """检查区块链集成就绪度"""
        try:
            # 尝试导入区块链集成
            from blockchain_integration import get_blockchain_integration
            
            integration = get_blockchain_integration()
            
            # 检查组件状态
            components = {
                'web3_connection': hasattr(integration, 'w3') and integration.w3 is not None,
                'contract_loaded': hasattr(integration, 'contract'),
                'account_ready': hasattr(integration, 'account'),
                'encryption_ready': hasattr(integration, 'encryption_key'),
                'pinata_configured': hasattr(integration, 'pinata_jwt')
            }
            
            working = sum(components.values())
            total = len(components)
            
            # 如果没有基本配置，不算关键错误
            if working == 0 and not os.environ.get('BLOCKCHAIN_PRIVATE_KEY'):
                return {
                    'passed': True,
                    'components': components,
                    'status': 'disabled',
                    'message': '区块链功能未配置（可选功能）'
                }
            
            # 如果有配置但组件失败，算作错误
            if working < 2:
                return {
                    'passed': False,
                    'critical': False,  # 非关键，但需要修复
                    'error': f'区块链组件就绪度不足: {working}/{total}',
                    'components': components
                }
            
            return {
                'passed': True,
                'components': components,
                'readiness': f'{working}/{total}',
                'status': 'ready'
            }
            
        except Exception as e:
            return {
                'passed': False,
                'critical': False,
                'error': f'区块链集成检查失败: {e}'
            }
    
    def check_rpc_failover_readiness(self) -> Dict[str, Any]:
        """检查RPC故障转移就绪度"""
        try:
            from rpc_failover import get_rpc_manager
            
            rpc_manager = get_rpc_manager()
            
            # 获取端点状态
            status_report = rpc_manager.get_status_report()
            
            healthy_endpoints = status_report['healthy_endpoints']
            total_endpoints = status_report['total_endpoints']
            
            if healthy_endpoints == 0:
                return {
                    'passed': False,
                    'critical': False,  # RPC是可选功能
                    'error': '没有健康的RPC端点',
                    'healthy_count': healthy_endpoints,
                    'total_count': total_endpoints
                }
            
            return {
                'passed': True,
                'healthy_count': healthy_endpoints,
                'total_count': total_endpoints,
                'success_rate': (healthy_endpoints / total_endpoints) * 100 if total_endpoints > 0 else 0
            }
            
        except Exception as e:
            return {
                'passed': False,
                'critical': False,
                'error': f'RPC故障转移检查失败: {e}'
            }
    
    def check_system_resources(self) -> Dict[str, Any]:
        """检查系统资源"""
        try:
            # CPU和内存
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # 资源阈值
            resource_issues = []
            if cpu_percent > 90:
                resource_issues.append(f'CPU使用率过高: {cpu_percent}%')
            if memory.percent > 90:
                resource_issues.append(f'内存使用率过高: {memory.percent}%')
            if disk.percent > 95:
                resource_issues.append(f'磁盘使用率过高: {disk.percent}%')
            
            # 检查可用内存
            available_gb = memory.available / (1024**3)
            if available_gb < 0.5:
                resource_issues.append(f'可用内存不足: {available_gb:.1f}GB')
            
            return {
                'passed': len(resource_issues) == 0,
                'critical': len(resource_issues) > 2,
                'error': f'{len(resource_issues)} 个资源问题' if resource_issues else None,
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'disk_percent': disk.percent,
                'available_memory_gb': available_gb,
                'issues': resource_issues
            }
            
        except Exception as e:
            return {
                'passed': False,
                'critical': False,
                'error': f'系统资源检查失败: {e}'
            }
    
    def check_monitoring_readiness(self) -> Dict[str, Any]:
        """检查监控配置就绪度"""
        monitoring_configs = []
        missing_configs = []
        
        # 检查日志配置
        log_level = os.environ.get('LOG_LEVEL', 'INFO')
        if log_level in ['DEBUG', 'INFO', 'WARNING', 'ERROR']:
            monitoring_configs.append('日志级别配置')
        else:
            missing_configs.append('有效的日志级别')
        
        # 检查监控端点
        monitoring_path = os.path.exists('/tmp/logs')
        if monitoring_path:
            monitoring_configs.append('日志目录')
        else:
            missing_configs.append('日志存储目录')
        
        return {
            'passed': len(missing_configs) == 0,
            'critical': False,  # 监控配置非关键
            'monitoring_configs': monitoring_configs,
            'missing_configs': missing_configs,
            'log_level': log_level
        }
    
    def generate_readiness_report(self) -> Dict[str, Any]:
        """生成就绪度报告"""
        total_checks = len(self.check_results)
        passed_checks = sum(1 for result in self.check_results.values() if result.get('passed', False))
        
        readiness_score = (passed_checks / total_checks) * 100 if total_checks > 0 else 0
        
        # 确定就绪度状态
        if len(self.critical_issues) == 0 and readiness_score >= 80:
            status = "生产就绪"
        elif len(self.critical_issues) == 0:
            status = "基本就绪"
        else:
            status = "未就绪"
        
        report = {
            'production_ready': self.production_ready,
            'status': status,
            'readiness_score': readiness_score,
            'summary': {
                'total_checks': total_checks,
                'passed_checks': passed_checks,
                'failed_checks': total_checks - passed_checks,
                'critical_issues': len(self.critical_issues),
                'warnings': len(self.warnings)
            },
            'critical_issues': self.critical_issues,
            'warnings': self.warnings,
            'detailed_results': self.check_results,
            'timestamp': datetime.now().isoformat(),
            'recommendations': self.generate_recommendations()
        }
        
        return report
    
    def generate_recommendations(self) -> List[str]:
        """生成修复建议"""
        recommendations = []
        
        if self.critical_issues:
            recommendations.append("🚨 立即修复关键问题以启用生产部署:")
            for issue in self.critical_issues:
                recommendations.append(f"  • {issue}")
        
        if self.warnings:
            recommendations.append("⚠️  建议修复以下警告:")
            for warning in self.warnings:
                recommendations.append(f"  • {warning}")
        
        # 基于检查结果的建议
        env_result = self.check_results.get('关键环境变量', {})
        if env_result.get('missing_production'):
            recommendations.append("📝 设置生产环境配置以启用完整功能")
        
        security_result = self.check_results.get('安全配置', {})
        if security_result.get('security_issues'):
            recommendations.append("🔒 修复安全配置问题")
        
        if not recommendations:
            recommendations.append("✅ 系统已就绪，可以部署到生产环境")
        
        return recommendations


def run_production_readiness_check(fail_fast: bool = False):
    """运行生产就绪度检查"""
    checker = ProductionReadinessChecker()
    
    try:
        report = checker.run_startup_checks(fail_fast=fail_fast)
        
        # 打印报告
        print("\n" + "="*80)
        print("🚀 生产就绪度检查报告")
        print("="*80)
        print(f"状态: {report['status']}")
        print(f"就绪度评分: {report['readiness_score']:.1f}%")
        print(f"检查项目: {report['summary']['total_checks']} 项")
        print(f"通过: {report['summary']['passed_checks']} 项")
        print(f"失败: {report['summary']['failed_checks']} 项")
        
        if report['critical_issues']:
            print(f"\n🚨 关键问题 ({len(report['critical_issues'])} 项):")
            for issue in report['critical_issues']:
                print(f"  ❌ {issue}")
        
        if report['warnings']:
            print(f"\n⚠️  警告 ({len(report['warnings'])} 项):")
            for warning in report['warnings']:
                print(f"  ⚠️  {warning}")
        
        print(f"\n💡 建议:")
        for rec in report['recommendations']:
            print(f"  {rec}")
        
        print("\n" + "="*80)
        
        return report
        
    except SystemExit:
        # fail_fast导致的退出
        print("\n❌ 生产就绪度检查失败，应用启动被阻止")
        return None


if __name__ == "__main__":
    import sys
    fail_fast = "--fail-fast" in sys.argv
    run_production_readiness_check(fail_fast=fail_fast)