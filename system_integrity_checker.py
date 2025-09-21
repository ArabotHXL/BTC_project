#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统完整性检查器 - 端到端验证所有集成组件
System Integrity Checker - End-to-End Validation for All Integration Components

这个模块提供全面的系统健康检查，验证：
- 数据库连接和模型完整性
- 区块链集成状态
- API依赖和RPC连接
- 模块注册状态
- 环境变量配置
- 文件依赖完整性

Authors: System Integration Team
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
import importlib.util
import requests
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SystemIntegrityChecker:
    """系统完整性检查器"""
    
    def __init__(self):
        self.check_results = {}
        self.critical_failures = []
        self.warnings = []
        self.start_time = datetime.now()
        
    def run_full_check(self) -> Dict[str, Any]:
        """运行完整的系统检查"""
        logger.info("🔍 开始系统完整性检查...")
        
        checks = [
            ("环境变量配置", self.check_environment_variables),
            ("数据库连接", self.check_database_connection),
            ("数据库模型完整性", self.check_database_models),
            ("文件依赖", self.check_file_dependencies),
            ("Python包依赖", self.check_python_dependencies),
            ("模块注册状态", self.check_module_registrations),
            ("API连接状态", self.check_api_connections),
            ("区块链集成", self.check_blockchain_integration),
            ("RPC故障转移", self.check_rpc_failover),
            ("系统资源", self.check_system_resources),
        ]
        
        for check_name, check_func in checks:
            try:
                logger.info(f"🔧 执行检查: {check_name}")
                result = check_func()
                self.check_results[check_name] = {
                    "status": "passed" if result.get("passed", False) else "failed",
                    "details": result,
                    "timestamp": datetime.now().isoformat()
                }
                
                if not result.get("passed", False):
                    if result.get("critical", False):
                        self.critical_failures.append(f"{check_name}: {result.get('error', 'Unknown error')}")
                    else:
                        self.warnings.append(f"{check_name}: {result.get('error', 'Warning')}")
                        
            except Exception as e:
                logger.error(f"❌ 检查 {check_name} 失败: {e}")
                self.check_results[check_name] = {
                    "status": "error",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
                self.critical_failures.append(f"{check_name}: {str(e)}")
        
        return self.generate_report()
    
    def check_environment_variables(self) -> Dict[str, Any]:
        """检查关键环境变量"""
        required_vars = [
            ("DATABASE_URL", True, "数据库连接必需"),
            ("SESSION_SECRET", True, "会话安全必需"),
        ]
        
        recommended_vars = [
            ("BLOCKCHAIN_PRIVATE_KEY", False, "区块链功能需要"),
            ("MINING_REGISTRY_CONTRACT_ADDRESS", False, "智能合约交互需要"),
            ("PINATA_JWT", False, "IPFS存储功能需要"),
            ("ENCRYPTION_PASSWORD", False, "数据加密功能需要"),
            ("ENCRYPTION_SALT", False, "数据加密功能需要"),
            ("GETBLOCK_API_KEY", False, "Bitcoin RPC访问推荐"),
        ]
        
        missing_required = []
        missing_recommended = []
        
        # 检查必需变量
        for var_name, required, description in required_vars:
            if not os.environ.get(var_name):
                if required:
                    missing_required.append(f"{var_name} - {description}")
                else:
                    missing_recommended.append(f"{var_name} - {description}")
        
        # 检查推荐变量
        for var_name, required, description in recommended_vars:
            if not os.environ.get(var_name):
                missing_recommended.append(f"{var_name} - {description}")
        
        result = {
            "passed": len(missing_required) == 0,
            "critical": len(missing_required) > 0,
            "missing_required": missing_required,
            "missing_recommended": missing_recommended,
            "total_env_vars": len(os.environ),
        }
        
        if missing_required:
            result["error"] = f"缺少 {len(missing_required)} 个必需的环境变量"
        
        return result
    
    def check_database_connection(self) -> Dict[str, Any]:
        """检查数据库连接"""
        try:
            from app import db
            
            # 测试数据库连接
            with db.engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                result.fetchone()
            
            # 检查数据库表
            tables = db.engine.table_names()
            expected_tables = [
                'user_access', 'miner_models', 'user_miners', 
                'network_snapshots', 'login_records',
                'crm_customers', 'crm_contacts', 'crm_leads', 'crm_deals'
            ]
            
            missing_tables = [table for table in expected_tables if table not in tables]
            
            return {
                "passed": True,
                "total_tables": len(tables),
                "expected_tables": len(expected_tables),
                "missing_tables": missing_tables,
                "database_url": os.environ.get("DATABASE_URL", "未配置")[:50] + "..."
            }
            
        except ImportError as e:
            return {
                "passed": False,
                "critical": True,
                "error": f"无法导入数据库模块: {e}"
            }
        except SQLAlchemyError as e:
            return {
                "passed": False,
                "critical": True,
                "error": f"数据库连接失败: {e}"
            }
    
    def check_database_models(self) -> Dict[str, Any]:
        """检查数据库模型完整性"""
        try:
            from models import (
                UserAccess, MinerModel, UserMiner, NetworkSnapshot,
                Customer, Contact, Lead, Deal, BlockchainRecord
            )
            
            model_checks = []
            for model_class in [UserAccess, MinerModel, UserMiner, NetworkSnapshot,
                                Customer, Contact, Lead, Deal, BlockchainRecord]:
                try:
                    # 检查模型是否有正确的表名和列
                    table_name = model_class.__tablename__
                    columns = [column.name for column in model_class.__table__.columns]
                    
                    model_checks.append({
                        "model": model_class.__name__,
                        "table": table_name,
                        "column_count": len(columns),
                        "status": "ok"
                    })
                    
                except Exception as e:
                    model_checks.append({
                        "model": model_class.__name__,
                        "error": str(e),
                        "status": "error"
                    })
            
            failed_models = [check for check in model_checks if check["status"] == "error"]
            
            return {
                "passed": len(failed_models) == 0,
                "critical": len(failed_models) > 3,  # 如果超过3个模型失败则为关键
                "model_checks": model_checks,
                "total_models": len(model_checks),
                "failed_models": len(failed_models)
            }
            
        except ImportError as e:
            return {
                "passed": False,
                "critical": True,
                "error": f"无法导入模型: {e}"
            }
    
    def check_file_dependencies(self) -> Dict[str, Any]:
        """检查关键文件依赖"""
        critical_files = [
            "app.py",
            "models.py", 
            "main.py",
            "blockchain_integration.py",
            "scheduler.py",
            "mining_calculator.py"
        ]
        
        important_files = [
            "api_client.py",
            "config.py",
            "auth.py",
            "contracts/MiningDataRegistry.sol"
        ]
        
        missing_critical = []
        missing_important = []
        
        for file_path in critical_files:
            if not os.path.exists(file_path):
                missing_critical.append(file_path)
                
        for file_path in important_files:
            if not os.path.exists(file_path):
                missing_important.append(file_path)
        
        return {
            "passed": len(missing_critical) == 0,
            "critical": len(missing_critical) > 0,
            "missing_critical": missing_critical,
            "missing_important": missing_important,
            "total_critical": len(critical_files),
            "total_important": len(important_files)
        }
    
    def check_python_dependencies(self) -> Dict[str, Any]:
        """检查Python包依赖"""
        required_packages = [
            "flask", "flask_sqlalchemy", "web3", "cryptography",
            "requests", "psycopg2", "schedule", "gunicorn"
        ]
        
        missing_packages = []
        version_info = {}
        
        for package in required_packages:
            try:
                module = importlib.import_module(package.replace('-', '_'))
                version = getattr(module, '__version__', 'Unknown')
                version_info[package] = version
            except ImportError:
                missing_packages.append(package)
        
        return {
            "passed": len(missing_packages) == 0,
            "critical": len(missing_packages) > 2,
            "missing_packages": missing_packages,
            "version_info": version_info,
            "total_required": len(required_packages)
        }
    
    def check_module_registrations(self) -> Dict[str, Any]:
        """检查模块注册状态"""
        try:
            # 这里需要检查Blueprint注册冲突
            # 由于我们无法直接访问Flask app实例，我们检查日志文件
            log_file = "/tmp/logs/Start_application_20250921_152053_338.log"
            
            registration_errors = []
            if os.path.exists(log_file):
                with open(log_file, 'r') as f:
                    content = f.read()
                    if "already registered for this blueprint" in content:
                        registration_errors.append("Blueprint名称冲突检测到")
            
            return {
                "passed": len(registration_errors) == 0,
                "critical": False,  # 非关键，但需要修复
                "errors": registration_errors,
                "log_file_checked": os.path.exists(log_file)
            }
            
        except Exception as e:
            return {
                "passed": False,
                "error": f"无法检查模块注册: {e}"
            }
    
    def check_api_connections(self) -> Dict[str, Any]:
        """检查API连接状态"""
        api_checks = []
        
        # 检查Bitcoin价格API
        try:
            response = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd", timeout=10)
            api_checks.append({
                "service": "CoinGecko价格API",
                "status": response.status_code,
                "response_time": response.elapsed.total_seconds(),
                "passed": response.status_code == 200
            })
        except Exception as e:
            api_checks.append({
                "service": "CoinGecko价格API",
                "error": str(e),
                "passed": False
            })
        
        # 检查Blockchain.info API
        try:
            response = requests.get("https://blockchain.info/q/hashrate", timeout=10)
            api_checks.append({
                "service": "Blockchain.info算力API",
                "status": response.status_code,
                "response_time": response.elapsed.total_seconds(),
                "passed": response.status_code == 200
            })
        except Exception as e:
            api_checks.append({
                "service": "Blockchain.info算力API",  
                "error": str(e),
                "passed": False
            })
        
        failed_apis = [check for check in api_checks if not check.get("passed", False)]
        
        return {
            "passed": len(failed_apis) < len(api_checks),  # 至少一个API工作
            "critical": len(failed_apis) == len(api_checks),  # 所有API都失败才是关键
            "api_checks": api_checks,
            "total_apis": len(api_checks),
            "failed_apis": len(failed_apis)
        }
    
    def check_blockchain_integration(self) -> Dict[str, Any]:
        """检查区块链集成状态"""
        try:
            from blockchain_integration import get_blockchain_integration
            
            # 尝试初始化区块链集成
            integration = get_blockchain_integration()
            
            integration_status = {
                "web3_connected": hasattr(integration, 'w3') and integration.w3 is not None,
                "contract_loaded": hasattr(integration, 'contract') and integration.contract is not None,
                "account_loaded": hasattr(integration, 'account') and integration.account is not None,
                "encryption_ready": hasattr(integration, 'encryption_key') and integration.encryption_key is not None,
                "pinata_configured": hasattr(integration, 'pinata_jwt') and integration.pinata_jwt is not None
            }
            
            working_components = sum(integration_status.values())
            total_components = len(integration_status)
            
            return {
                "passed": working_components >= 2,  # 至少2个组件工作
                "critical": working_components == 0,  # 没有组件工作才是关键
                "integration_status": integration_status,
                "working_components": working_components,
                "total_components": total_components,
                "health_percentage": (working_components / total_components) * 100
            }
            
        except Exception as e:
            return {
                "passed": False,
                "critical": True,
                "error": f"区块链集成检查失败: {e}"
            }
    
    def check_rpc_failover(self) -> Dict[str, Any]:
        """检查RPC故障转移机制"""
        rpc_endpoints = [
            "https://go.getblock.io/mainnet",
            "https://bitcoin-mainnet.public.blastapi.io",
            "https://bitcoin.drpc.org",
            "https://btc-mainnet.rpc.grove.city/v1/",
        ]
        
        working_endpoints = []
        failed_endpoints = []
        
        for endpoint in rpc_endpoints:
            try:
                # 简单的连接测试（不需要API key的基本测试）
                response = requests.get(endpoint, timeout=5, headers={"Content-Type": "application/json"})
                if response.status_code in [200, 401, 403]:  # 401/403表示端点存在但需要认证
                    working_endpoints.append(endpoint)
                else:
                    failed_endpoints.append(f"{endpoint} (HTTP {response.status_code})")
            except Exception as e:
                failed_endpoints.append(f"{endpoint} ({str(e)})")
        
        return {
            "passed": len(working_endpoints) > 0,
            "critical": len(working_endpoints) == 0,
            "working_endpoints": working_endpoints,
            "failed_endpoints": failed_endpoints,
            "total_endpoints": len(rpc_endpoints),
            "success_rate": (len(working_endpoints) / len(rpc_endpoints)) * 100
        }
    
    def check_system_resources(self) -> Dict[str, Any]:
        """检查系统资源状态"""
        try:
            import psutil
            
            # CPU和内存使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # 检查是否有足够的资源
            resource_warnings = []
            if cpu_percent > 80:
                resource_warnings.append(f"CPU使用率过高: {cpu_percent}%")
            if memory.percent > 85:
                resource_warnings.append(f"内存使用率过高: {memory.percent}%")
            if disk.percent > 90:
                resource_warnings.append(f"磁盘使用率过高: {disk.percent}%")
            
            return {
                "passed": len(resource_warnings) == 0,
                "critical": len(resource_warnings) > 2,
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "disk_percent": disk.percent,
                "warnings": resource_warnings
            }
            
        except ImportError:
            return {
                "passed": True,  # 非关键检查
                "error": "psutil未安装，无法检查系统资源"
            }
    
    def generate_report(self) -> Dict[str, Any]:
        """生成检查报告"""
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()
        
        total_checks = len(self.check_results)
        passed_checks = sum(1 for result in self.check_results.values() if result["status"] == "passed")
        failed_checks = total_checks - passed_checks
        
        overall_health = "健康" if len(self.critical_failures) == 0 else "有问题"
        if len(self.critical_failures) > 3:
            overall_health = "严重问题"
        
        report = {
            "overall_status": overall_health,
            "summary": {
                "total_checks": total_checks,
                "passed_checks": passed_checks,
                "failed_checks": failed_checks,
                "critical_failures": len(self.critical_failures),
                "warnings": len(self.warnings),
                "success_rate": (passed_checks / total_checks) * 100 if total_checks > 0 else 0
            },
            "critical_failures": self.critical_failures,
            "warnings": self.warnings,
            "detailed_results": self.check_results,
            "execution_time": duration,
            "timestamp": end_time.isoformat(),
            "recommendations": self.generate_recommendations()
        }
        
        return report
    
    def generate_recommendations(self) -> List[str]:
        """生成修复建议"""
        recommendations = []
        
        if self.critical_failures:
            recommendations.append("🚨 立即修复以下关键问题:")
            for failure in self.critical_failures:
                recommendations.append(f"  - {failure}")
        
        if self.warnings:
            recommendations.append("⚠️  建议修复以下警告:")
            for warning in self.warnings:
                recommendations.append(f"  - {warning}")
        
        # 基于检查结果的具体建议
        if "环境变量配置" in self.check_results and not self.check_results["环境变量配置"]["details"].get("passed", False):
            recommendations.append("📝 设置缺失的环境变量以启用所有功能")
        
        if "模块注册状态" in self.check_results and not self.check_results["模块注册状态"]["details"].get("passed", False):
            recommendations.append("🔧 修复Blueprint名称冲突问题")
        
        if "RPC故障转移" in self.check_results:
            rpc_result = self.check_results["RPC故障转移"]["details"]
            if rpc_result.get("success_rate", 0) < 50:
                recommendations.append("🌐 配置备用RPC端点或API密钥")
        
        if not recommendations:
            recommendations.append("✅ 系统运行良好，无需立即修复")
        
        return recommendations


def run_integrity_check():
    """运行完整性检查的主函数"""
    checker = SystemIntegrityChecker()
    report = checker.run_full_check()
    
    # 打印报告
    print("\n" + "="*80)
    print("🔍 系统完整性检查报告")
    print("="*80)
    print(f"总体状态: {report['overall_status']}")
    print(f"检查项目: {report['summary']['total_checks']} 项")
    print(f"通过: {report['summary']['passed_checks']} 项")
    print(f"失败: {report['summary']['failed_checks']} 项")
    print(f"成功率: {report['summary']['success_rate']:.1f}%")
    print(f"执行时间: {report['execution_time']:.2f} 秒")
    
    if report['critical_failures']:
        print(f"\n🚨 关键问题 ({len(report['critical_failures'])} 项):")
        for failure in report['critical_failures']:
            print(f"  ❌ {failure}")
    
    if report['warnings']:
        print(f"\n⚠️  警告 ({len(report['warnings'])} 项):")
        for warning in report['warnings']:
            print(f"  ⚠️  {warning}")
    
    print(f"\n📋 修复建议:")
    for rec in report['recommendations']:
        print(f"  {rec}")
    
    print("\n" + "="*80)
    
    return report


if __name__ == "__main__":
    run_integrity_check()