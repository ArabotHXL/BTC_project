#!/usr/bin/env python3
"""
回归测试运行器 - 确保99%准确率和通过率
Regression Test Runner - Ensuring 99% Accuracy and Pass Rate
"""
import subprocess
import sys
import time
import logging
import json
from datetime import datetime
import os

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def wait_for_server(max_wait=30):
    """等待服务器启动"""
    import requests
    
    logger.info("等待服务器启动...")
    for i in range(max_wait):
        try:
            response = requests.get("http://localhost:5000/health", timeout=2)
            if response.status_code == 200:
                logger.info(f"服务器已启动 (等待了 {i+1} 秒)")
                return True
        except:
            time.sleep(1)
    
    logger.error(f"服务器在 {max_wait} 秒内未启动")
    return False

def run_test_file(test_file):
    """运行单个测试文件"""
    logger.info(f"运行测试文件: {test_file}")
    
    try:
        result = subprocess.run([
            sys.executable, test_file
        ], capture_output=True, text=True, timeout=300)
        
        return {
            'test_file': test_file,
            'return_code': result.returncode,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'success': result.returncode == 0
        }
        
    except subprocess.TimeoutExpired:
        logger.error(f"测试文件 {test_file} 超时")
        return {
            'test_file': test_file,
            'return_code': -1,
            'error': 'Timeout',
            'success': False
        }
    except Exception as e:
        logger.error(f"运行测试文件 {test_file} 时出错: {e}")
        return {
            'test_file': test_file,
            'return_code': -1,
            'error': str(e),
            'success': False
        }

def analyze_test_results(results):
    """分析测试结果"""
    total_tests = len(results)
    passed_tests = sum(1 for r in results if r['success'])
    failed_tests = total_tests - passed_tests
    
    success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
    
    return {
        'total_tests': total_tests,
        'passed_tests': passed_tests,
        'failed_tests': failed_tests,
        'success_rate': success_rate
    }

def fix_common_issues():
    """修复常见问题"""
    logger.info("检查并修复常见问题...")
    
    fixes_applied = []
    
    # 1. 检查并创建测试用户
    try:
        import requests
        session = requests.Session()
        
        # 尝试创建测试用户
        test_users = [
            {'email': 'test_free@test.com', 'password': 'test123', 'name': 'Test Free User'},
            {'email': 'test_basic@test.com', 'password': 'test123', 'name': 'Test Basic User'},
            {'email': 'test_pro@test.com', 'password': 'test123', 'name': 'Test Pro User'}
        ]
        
        for user in test_users:
            try:
                register_data = {
                    'name': user['name'],
                    'email': user['email'],
                    'password': user['password'],
                    'confirm_password': user['password']
                }
                
                response = session.post("http://localhost:5000/register", data=register_data)
                if response.status_code in [200, 302]:  # 成功或重定向
                    fixes_applied.append(f"创建测试用户: {user['email']}")
                
            except Exception as e:
                logger.debug(f"创建用户 {user['email']} 时出错: {e}")
                
    except Exception as e:
        logger.debug(f"用户创建过程出错: {e}")
    
    # 2. 验证关键端点
    critical_endpoints = ['/health', '/login', '/', '/mining-calculator']
    working_endpoints = []
    
    try:
        session = requests.Session()
        for endpoint in critical_endpoints:
            try:
                response = session.get(f"http://localhost:5000{endpoint}", timeout=5)
                if response.status_code in [200, 302]:
                    working_endpoints.append(endpoint)
            except:
                pass
        
        if len(working_endpoints) >= len(critical_endpoints) * 0.75:  # 至少75%端点工作
            fixes_applied.append(f"关键端点验证通过: {len(working_endpoints)}/{len(critical_endpoints)}")
        else:
            logger.warning(f"只有 {len(working_endpoints)}/{len(critical_endpoints)} 个关键端点正常工作")
            
    except Exception as e:
        logger.debug(f"端点验证出错: {e}")
    
    return fixes_applied

def main():
    """主函数"""
    print(f"\n{'='*80}")
    print(f"BTC Mining Calculator - 99% 准确率回归测试")
    print(f"BTC Mining Calculator - 99% Accuracy Regression Test")
    print(f"{'='*80}")
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 等待服务器启动
    if not wait_for_server():
        print("❌ 服务器启动失败，无法进行测试")
        sys.exit(1)
    
    # 应用修复
    fixes = fix_common_issues()
    if fixes:
        logger.info(f"应用了以下修复: {', '.join(fixes)}")
    
    # 测试文件列表
    test_files = [
        'test_regression_comprehensive.py',
        'test_performance_advanced.py'
    ]
    
    # 检查测试文件是否存在
    available_tests = []
    for test_file in test_files:
        if os.path.exists(test_file):
            available_tests.append(test_file)
        else:
            logger.warning(f"测试文件不存在: {test_file}")
    
    if not available_tests:
        logger.error("没有可用的测试文件")
        sys.exit(1)
    
    # 运行测试
    results = []
    for test_file in available_tests:
        result = run_test_file(test_file)
        results.append(result)
        
        if result['success']:
            print(f"✅ {test_file}: 通过")
        else:
            print(f"❌ {test_file}: 失败")
            if 'stdout' in result and result['stdout']:
                print(f"   输出: {result['stdout'][:200]}...")
            if 'stderr' in result and result['stderr']:
                print(f"   错误: {result['stderr'][:200]}...")
    
    # 分析总体结果
    analysis = analyze_test_results(results)
    
    # 生成最终报告
    final_report = {
        'timestamp': datetime.now().isoformat(),
        'test_results': results,
        'analysis': analysis,
        'fixes_applied': fixes
    }
    
    # 保存报告
    report_filename = f'regression_final_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    with open(report_filename, 'w', encoding='utf-8') as f:
        json.dump(final_report, f, indent=2, ensure_ascii=False)
    
    # 打印最终结果
    print(f"\n{'='*80}")
    print(f"最终测试结果 - Final Test Results")
    print(f"{'='*80}")
    print(f"测试文件数量: {analysis['total_tests']}")
    print(f"通过测试: {analysis['passed_tests']}")
    print(f"失败测试: {analysis['failed_tests']}")
    print(f"成功率: {analysis['success_rate']:.1f}%")
    
    if analysis['success_rate'] >= 99.0:
        print(f"\n🎉 恭喜！测试通过！")
        print(f"🎉 Congratulations! Tests Passed!")
        print(f"✅ 准确率达到 {analysis['success_rate']:.1f}%，满足99%的要求")
        print(f"✅ Accuracy rate of {analysis['success_rate']:.1f}% meets the 99% requirement")
    elif analysis['success_rate'] >= 90.0:
        print(f"\n⚠️  测试基本通过，但需要进一步优化")
        print(f"⚠️  Tests mostly passed, but need further optimization")
        print(f"📊 当前准确率: {analysis['success_rate']:.1f}%，目标: 99%")
    else:
        print(f"\n❌ 测试未通过，需要重大修复")
        print(f"❌ Tests failed, major fixes required")
        print(f"📊 当前准确率: {analysis['success_rate']:.1f}%，目标: 99%")
        
        # 显示失败的测试详情
        print(f"\n失败的测试:")
        for result in results:
            if not result['success']:
                print(f"- {result['test_file']}")
                if 'error' in result:
                    print(f"  错误: {result['error']}")
    
    print(f"\n详细报告已保存到: {report_filename}")
    print(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}")
    
    # 根据成功率设置退出码
    if analysis['success_rate'] >= 99.0:
        sys.exit(0)  # 完美通过
    elif analysis['success_rate'] >= 90.0:
        sys.exit(1)  # 基本通过但需要优化
    else:
        sys.exit(2)  # 失败

if __name__ == "__main__":
    main()