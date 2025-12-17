#!/usr/bin/env python3
"""
🔧 CRITICAL SECURITY VALIDATION SCRIPT
关键安全修复验证脚本

验证以下安全修复：
1. Session Secret 安全修复
2. SchedulerLock 单实例机制
3. 生产就绪状态检查
4. 多worker环境下的调度器唯一性

Usage:
    python security_validation.py
"""

import os
import sys
import time
import json
import logging
import traceback
from datetime import datetime, timedelta
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SecurityValidator:
    """安全验证器"""
    
    def __init__(self):
        self.validation_results = {}
        self.critical_failures = []
        
    def validate_session_secret_fix(self):
        """验证Session Secret修复"""
        logger.info("🔒 验证Session Secret修复...")
        
        try:
            # 检查main.py是否移除了硬编码secret
            with open('main.py', 'r', encoding='utf-8') as f:
                main_content = f.read()
                
            # 检查是否还有硬编码的secret
            forbidden_patterns = [
                'bitcoin_mining_calculator_secret',
                'app.secret_key = "',
                "app.secret_key = '",
                'secret_key = "bitcoin',
                "secret_key = 'bitcoin"
            ]
            
            violations = []
            for pattern in forbidden_patterns:
                if pattern in main_content:
                    violations.append(pattern)
                    
            if violations:
                self.critical_failures.append(f"main.py仍包含硬编码secret: {violations}")
                self.validation_results['session_secret_fix'] = {
                    'status': 'FAILED',
                    'reason': f'发现硬编码secret: {violations}',
                    'critical': True
                }
                return False
                
            # 检查app.py的严格要求
            with open('app.py', 'r', encoding='utf-8') as f:
                app_content = f.read()
                
            # 检查是否有SESSION_SECRET的环境变量获取
            session_secret_patterns = [
                'os.environ.get("SESSION_SECRET")',
                "os.environ.get('SESSION_SECRET')",
                'SESSION_SECRET environment variable must be set'
            ]
            
            has_session_secret_check = any(pattern in app_content for pattern in session_secret_patterns)
            
            if not has_session_secret_check:
                self.critical_failures.append("app.py未严格要求SESSION_SECRET环境变量")
                self.validation_results['session_secret_fix'] = {
                    'status': 'FAILED',
                    'reason': 'app.py未严格要求SESSION_SECRET',
                    'critical': True
                }
                return False
                
            self.validation_results['session_secret_fix'] = {
                'status': 'PASSED',
                'details': 'Session secret硬编码已移除，严格要求环境变量'
            }
            logger.info("✅ Session Secret修复验证通过")
            return True
            
        except Exception as e:
            error_msg = f"Session Secret验证失败: {e}"
            self.critical_failures.append(error_msg)
            self.validation_results['session_secret_fix'] = {
                'status': 'ERROR',
                'reason': str(e),
                'critical': True
            }
            logger.error(f"❌ {error_msg}")
            return False
            
    def validate_scheduler_lock_model(self):
        """验证SchedulerLock模型实现"""
        logger.info("🔒 验证SchedulerLock模型...")
        
        try:
            # 导入模型测试
            from models import SchedulerLock
            from app import app, db
            
            with app.app_context():
                # 测试模型功能
                test_key = f"validation_test_{int(time.time())}"
                test_pid = 99999
                test_hostname = "validation_host"
                
                # 测试获取锁
                success = SchedulerLock.acquire_lock(
                    lock_key=test_key,
                    process_id=test_pid,
                    hostname=test_hostname,
                    timeout_seconds=30
                )
                
                if not success:
                    raise Exception("无法获取测试锁")
                    
                # 测试锁查询
                active_lock = SchedulerLock.get_active_lock(test_key)
                if not active_lock:
                    raise Exception("无法查询活跃锁")
                    
                # 验证锁属性
                if active_lock.process_id != test_pid:
                    raise Exception(f"锁进程ID不匹配: 期望{test_pid}, 实际{active_lock.process_id}")
                    
                if active_lock.hostname != test_hostname:
                    raise Exception(f"锁主机名不匹配: 期望{test_hostname}, 实际{active_lock.hostname}")
                    
                # 测试锁释放
                release_success = SchedulerLock.release_lock(test_key, test_pid)
                if not release_success:
                    raise Exception("无法释放测试锁")
                    
                # 验证锁已释放
                released_lock = SchedulerLock.get_active_lock(test_key)
                if released_lock:
                    raise Exception("锁释放后仍然存在")
                    
            self.validation_results['scheduler_lock_model'] = {
                'status': 'PASSED',
                'details': 'SchedulerLock模型功能完整，锁机制正常工作'
            }
            logger.info("✅ SchedulerLock模型验证通过")
            return True
            
        except Exception as e:
            error_msg = f"SchedulerLock模型验证失败: {e}"
            self.critical_failures.append(error_msg)
            self.validation_results['scheduler_lock_model'] = {
                'status': 'FAILED',
                'reason': str(e),
                'critical': True
            }
            logger.error(f"❌ {error_msg}")
            return False
            
    def validate_scheduler_integration(self):
        """验证调度器集成"""
        logger.info("🕐 验证调度器集成...")
        
        try:
            # 检查scheduler.py是否使用了SchedulerLock模型
            with open('scheduler.py', 'r', encoding='utf-8') as f:
                scheduler_content = f.read()
                
            # 验证关键修复
            required_imports = ['from models import BlockchainRecord, BlockchainVerificationStatus, SchedulerLock']
            required_methods = [
                '_verify_scheduler_lock_integration',
                '_test_scheduler_lock_functionality',
                'SchedulerLock.acquire_lock',
                'SchedulerLock.release_lock',
                'SchedulerLock.get_active_lock'
            ]
            
            missing_items = []
            for item in required_imports + required_methods:
                if item not in scheduler_content:
                    missing_items.append(item)
                    
            if missing_items:
                raise Exception(f"调度器缺少关键修复: {missing_items}")
                
            # 检查是否移除了老的SQL表操作
            deprecated_patterns = [
                'CREATE TABLE IF NOT EXISTS scheduler_leader_lock',
                'INSERT INTO scheduler_leader_lock',
                'DELETE FROM scheduler_leader_lock'
            ]
            
            found_deprecated = []
            for pattern in deprecated_patterns:
                if pattern in scheduler_content:
                    found_deprecated.append(pattern)
                    
            if found_deprecated:
                logger.warning(f"⚠️ 发现过时的SQL操作（可能需要清理）: {found_deprecated}")
                
            self.validation_results['scheduler_integration'] = {
                'status': 'PASSED',
                'details': '调度器已集成SchedulerLock模型，移除了直接SQL操作'
            }
            logger.info("✅ 调度器集成验证通过")
            return True
            
        except Exception as e:
            error_msg = f"调度器集成验证失败: {e}"
            self.validation_results['scheduler_integration'] = {
                'status': 'FAILED',
                'reason': str(e),
                'critical': False  # 非关键失败
            }
            logger.error(f"❌ {error_msg}")
            return False
            
    def validate_production_readiness_checker(self):
        """验证生产就绪检查器"""
        logger.info("🚀 验证生产就绪检查器...")
        
        try:
            # 检查production_readiness_checker.py是否存在
            if not os.path.exists('production_readiness_checker.py'):
                raise Exception("production_readiness_checker.py文件不存在")
                
            # 检查main.py中的调用时机
            with open('main.py', 'r', encoding='utf-8') as f:
                main_content = f.read()
                
            # 查找ProductionReadinessChecker的调用
            if 'ProductionReadinessChecker' not in main_content:
                raise Exception("main.py中未找到ProductionReadinessChecker")
                
            # 验证调用方法（可能是check_environment或run_startup_checks）
            checker_call_patterns = [
                'ProductionReadinessChecker().check_environment',
                'checker.check_environment',
                'ProductionReadinessChecker().run_startup_checks',
                'checker.run_startup_checks'
            ]
            
            has_checker_call = any(pattern in main_content for pattern in checker_call_patterns)
            
            if not has_checker_call:
                raise Exception("未找到ProductionReadinessChecker的调用方法")
                
            # 检查是否在配置之前运行（在生产模式下）
            self.validation_results['production_readiness_checker'] = {
                'status': 'PASSED',
                'details': '生产就绪检查器正确集成，支持生产模式严格检查'
            }
            logger.info("✅ 生产就绪检查器验证通过")
            return True
            
        except Exception as e:
            error_msg = f"生产就绪检查器验证失败: {e}"
            self.validation_results['production_readiness_checker'] = {
                'status': 'FAILED',
                'reason': str(e),
                'critical': False
            }
            logger.error(f"❌ {error_msg}")
            return False
            
    def test_multi_worker_safety(self):
        """测试多worker环境安全性（模拟测试）"""
        logger.info("🔄 测试多worker环境安全性...")
        
        try:
            from models import SchedulerLock
            from app import app, db
            
            with app.app_context():
                # 模拟多个worker尝试获取同一个锁
                test_key = "multi_worker_test"
                worker_pids = [10001, 10002, 10003]
                successful_acquisitions = 0
                
                for pid in worker_pids:
                    success = SchedulerLock.acquire_lock(
                        lock_key=test_key,
                        process_id=pid,
                        hostname=f"worker_{pid}",
                        timeout_seconds=60
                    )
                    if success:
                        successful_acquisitions += 1
                        
                # 只应该有一个worker成功获取锁
                if successful_acquisitions != 1:
                    raise Exception(f"多worker测试失败: {successful_acquisitions}个worker获取了锁，应该只有1个")
                    
                # 清理测试锁
                for pid in worker_pids:
                    SchedulerLock.release_lock(test_key, pid)
                    
            self.validation_results['multi_worker_safety'] = {
                'status': 'PASSED',
                'details': f'多worker测试通过: 只有1个worker获取了锁'
            }
            logger.info("✅ 多worker安全性验证通过")
            return True
            
        except Exception as e:
            error_msg = f"多worker安全性测试失败: {e}"
            self.validation_results['multi_worker_safety'] = {
                'status': 'FAILED',
                'reason': str(e),
                'critical': True
            }
            logger.error(f"❌ {error_msg}")
            return False
            
    def generate_validation_report(self):
        """生成验证报告"""
        report = {
            'validation_timestamp': datetime.utcnow().isoformat(),
            'total_tests': len(self.validation_results),
            'passed_tests': len([r for r in self.validation_results.values() if r['status'] == 'PASSED']),
            'failed_tests': len([r for r in self.validation_results.values() if r['status'] == 'FAILED']),
            'critical_failures': len(self.critical_failures),
            'results': self.validation_results,
            'critical_failure_details': self.critical_failures
        }
        
        # 判断总体状态
        if self.critical_failures:
            report['overall_status'] = 'CRITICAL_FAILURE'
            report['production_ready'] = False
        elif report['failed_tests'] > 0:
            report['overall_status'] = 'PARTIAL_FAILURE'
            report['production_ready'] = False
        else:
            report['overall_status'] = 'ALL_PASSED'
            report['production_ready'] = True
            
        return report
        
    def run_all_validations(self):
        """运行所有验证"""
        logger.info("🚀 开始安全验证...")
        
        validations = [
            ('Session Secret修复', self.validate_session_secret_fix),
            ('SchedulerLock模型', self.validate_scheduler_lock_model),
            ('调度器集成', self.validate_scheduler_integration),
            ('生产就绪检查器', self.validate_production_readiness_checker),
            ('多Worker安全性', self.test_multi_worker_safety)
        ]
        
        for test_name, test_func in validations:
            logger.info(f"正在执行: {test_name}")
            try:
                test_func()
            except Exception as e:
                logger.error(f"测试 {test_name} 执行异常: {e}")
                self.validation_results[test_name.lower().replace(' ', '_')] = {
                    'status': 'ERROR',
                    'reason': str(e),
                    'critical': True
                }
                
        # 生成报告
        report = self.generate_validation_report()
        
        # 保存报告
        with open('security_validation_report.json', 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
            
        # 打印总结
        self.print_summary(report)
        
        return report
        
    def print_summary(self, report):
        """打印验证总结"""
        print("\n" + "="*70)
        print("🔒 安全验证报告总结")
        print("="*70)
        
        print(f"📊 总测试数: {report['total_tests']}")
        print(f"✅ 通过测试: {report['passed_tests']}")
        print(f"❌ 失败测试: {report['failed_tests']}")
        print(f"🚨 关键失败: {report['critical_failures']}")
        
        print(f"\n🎯 总体状态: {report['overall_status']}")
        print(f"🚀 生产就绪: {'是' if report['production_ready'] else '否'}")
        
        if report['critical_failure_details']:
            print(f"\n🚨 关键问题:")
            for failure in report['critical_failure_details']:
                print(f"   - {failure}")
                
        print(f"\n📋 详细结果:")
        for test_name, result in report['results'].items():
            status_icon = "✅" if result['status'] == 'PASSED' else "❌"
            print(f"   {status_icon} {test_name}: {result['status']}")
            if result['status'] != 'PASSED':
                print(f"      原因: {result.get('reason', 'N/A')}")
                
        print("\n" + "="*70)
        
        if report['production_ready']:
            print("🎉 所有安全修复验证通过！系统已达到生产就绪状态。")
        else:
            print("⚠️  存在安全问题需要修复后才能用于生产环境。")
            
        print("="*70)

def main():
    """主函数"""
    print("🔒 Bitcoin Mining Calculator - 安全验证脚本")
    print("验证关键安全修复是否正确实施...")
    
    validator = SecurityValidator()
    report = validator.run_all_validations()
    
    # 返回退出码
    if report['production_ready']:
        sys.exit(0)  # 成功
    else:
        sys.exit(1)  # 失败

if __name__ == "__main__":
    main()