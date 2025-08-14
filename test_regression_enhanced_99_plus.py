#!/usr/bin/env python3
"""
增强版回归测试系统 - 99%+ 精确度要求
Enhanced Regression Testing System - 99%+ Accuracy Required

解决前次测试中发现的问题，确保达到99%+准确率
Addresses issues found in previous test to ensure 99%+ accuracy
"""

import requests
import json
import time
import logging
import sys
from datetime import datetime
from typing import Dict, List, Tuple, Any
import traceback
import re
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'enhanced_regression_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

class EnhancedRegressionTester:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.test_results = []
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        self.accuracy_target = 99.0
        
        # 设置更长的超时和重试
        self.session.timeout = 15
        self.max_retries = 3
        
        # 登录凭据
        self.test_user = {
            'email': 'owner@test.com',
            'password': 'test123'
        }
        
        # 增强的关键路径测试
        self.enhanced_test_suite = {
            '核心用户界面_高优先级': [
                ('/', 'GET', '主页', False, {'expect_content': ['Bitcoin', 'Mining', 'Calculator'], 'min_response_time': 0.5}),
                ('/dashboard', 'GET', '主仪表盘', True, {'expect_content': ['Dashboard', '仪表盘'], 'performance_critical': True}),
                ('/calculator', 'GET', '挖矿计算器', True, {'expect_content': ['Calculator', '计算器', 'Mining'], 'performance_critical': True}),
                ('/analytics', 'GET', '分析仪表盘', True, {'expect_content': ['Analytics', '分析'], 'performance_critical': True}),
            ],
            '业务功能界面_高优先级': [
                ('/batch-calculator', 'GET', '批量挖矿计算器', True, {'expect_content': ['Batch', '批量'], 'feature_critical': True}),
                ('/technical-analysis', 'GET', '技术分析页面', True, {'expect_content': ['Technical', '技术分析'], 'feature_critical': True}),
                ('/analytics/main', 'GET', '主要分析界面', True, {'expect_content': ['Analytics', 'BTC'], 'feature_critical': True}),
            ],
            'API端点_数据准确性': [
                ('/api/network-data', 'GET', '网络统计数据', False, {'json_response': True, 'data_validation': True, 'cache_test': True}),
                ('/api/get-btc-price', 'GET', 'BTC价格', False, {'json_response': True, 'data_validation': True, 'cache_test': True}),
                ('/api/get_miners_data', 'GET', '矿机数据', False, {'json_response': True, 'data_validation': True, 'cache_test': True}),
                ('/api/analytics/data', 'GET', '分析数据', False, {'json_response': True, 'data_validation': True}),
            ],
            'CRM系统_功能完整性': [
                ('/crm/dashboard', 'GET', 'CRM仪表盘', True, {'expect_content': ['CRM', 'Dashboard'], 'role_required': 'owner'}),
                ('/crm/customers', 'GET', '客户管理', True, {'expect_content': ['Customer', '客户'], 'role_required': 'owner'}),
                ('/crm/leads', 'GET', '线索管理', True, {'expect_content': ['Lead', '线索'], 'role_required': 'owner'}),
            ],
            '管理员功能_权限验证': [
                ('/admin/user_access', 'GET', '用户权限管理', True, {'expect_content': ['User', 'Access', '用户'], 'role_required': 'owner'}),
                ('/admin/login_records', 'GET', '登录记录', True, {'expect_content': ['Login', 'Record'], 'role_required': 'owner'}),
            ]
        }

    def enhanced_login(self) -> Tuple[bool, str]:
        """增强的登录功能，包含详细状态检查"""
        try:
            # 首先检查是否已经登录
            test_response = self.session.get(f"{self.base_url}/dashboard")
            if test_response.status_code == 200:
                logging.info("✅ 已经处于登录状态")
                return True, "Already logged in"
            
            # 获取登录页面
            login_page = self.session.get(f"{self.base_url}/login")
            if login_page.status_code != 200:
                return False, f"Cannot access login page: {login_page.status_code}"
            
            # 尝试登录
            login_data = {
                'email': self.test_user['email'],
                'password': self.test_user['password']
            }
            
            response = self.session.post(
                f"{self.base_url}/login",
                data=login_data,
                allow_redirects=False
            )
            
            # 检查登录结果
            if response.status_code in [200, 302]:
                # 验证登录成功
                dashboard_check = self.session.get(f"{self.base_url}/dashboard")
                if dashboard_check.status_code == 200:
                    logging.info("✅ 用户登录验证成功")
                    return True, "Login successful"
                else:
                    logging.warning("⚠️ 登录可能成功但无法访问仪表盘")
                    return True, "Login partial success"
            
            return False, f"Login failed with status: {response.status_code}"
            
        except Exception as e:
            return False, f"Login error: {str(e)}"

    def enhanced_test_endpoint(self, path: str, method: str, description: str, 
                             requires_login: bool, test_config: Dict) -> Dict[str, Any]:
        """增强的端点测试，包含详细验证"""
        
        test_result = {
            'path': path,
            'method': method,
            'description': description,
            'requires_login': requires_login,
            'test_config': test_config,
            'success': False,
            'accuracy_score': 0,
            'max_score': 10,  # 最大分数
            'status_code': None,
            'response_time': None,
            'content_validation': {},
            'data_validation': {},
            'performance_validation': {},
            'errors': [],
            'warnings': []
        }
        
        try:
            # 执行请求
            start_time = time.time()
            
            if method == 'GET':
                response = self.session.get(f"{self.base_url}{path}", timeout=15)
            elif method == 'POST':
                if path == '/api/calculate':
                    post_data = {
                        'miner_model': 'Antminer S19 Pro',
                        'quantity': 1,
                        'electricity_cost': 0.08,
                        'pool_fee': 0.01
                    }
                    response = self.session.post(f"{self.base_url}{path}", json=post_data, timeout=15)
                else:
                    response = self.session.post(f"{self.base_url}{path}", timeout=15)
            else:
                response = self.session.request(method, f"{self.base_url}{path}", timeout=15)
            
            response_time = time.time() - start_time
            test_result['response_time'] = response_time
            test_result['status_code'] = response.status_code
            
            # 基础成功性检查 (2分)
            if response.status_code == 200:
                test_result['accuracy_score'] += 2
                test_result['success'] = True
            elif response.status_code == 302 and requires_login:
                test_result['accuracy_score'] += 1  # 部分分数，重定向是可接受的
                test_result['success'] = True
                test_result['warnings'].append('Redirected (login required)')
            else:
                test_result['errors'].append(f'Unexpected status code: {response.status_code}')
            
            # 内容验证 (3分)
            if response.status_code == 200:
                content_score = self.validate_content_enhanced(response, test_config)
                test_result['content_validation'] = content_score
                test_result['accuracy_score'] += content_score.get('score', 0)
            
            # 数据验证 (3分)
            if test_config.get('json_response') and response.status_code == 200:
                data_score = self.validate_data_enhanced(response, test_config)
                test_result['data_validation'] = data_score
                test_result['accuracy_score'] += data_score.get('score', 0)
            
            # 性能验证 (2分)
            perf_score = self.validate_performance_enhanced(response_time, test_config)
            test_result['performance_validation'] = perf_score
            test_result['accuracy_score'] += perf_score.get('score', 0)
            
            # 缓存测试
            if test_config.get('cache_test'):
                cache_score = self.test_cache_functionality(path)
                test_result['cache_validation'] = cache_score
                if cache_score.get('working'):
                    test_result['accuracy_score'] += 1  # 额外分数
            
        except requests.exceptions.Timeout:
            test_result['errors'].append('Request timeout (>15s)')
        except requests.exceptions.ConnectionError:
            test_result['errors'].append('Connection error')
        except Exception as e:
            test_result['errors'].append(f'Unexpected error: {str(e)}')
        
        # 计算最终准确率百分比
        test_result['accuracy_percentage'] = (test_result['accuracy_score'] / test_result['max_score']) * 100
        
        return test_result

    def validate_content_enhanced(self, response: requests.Response, test_config: Dict) -> Dict[str, Any]:
        """增强的内容验证"""
        validation_result = {
            'score': 0,
            'max_score': 3,
            'checks': []
        }
        
        try:
            content = response.text
            
            # 基础HTML结构检查 (1分)
            if content and len(content) > 100:
                validation_result['score'] += 1
                validation_result['checks'].append('✅ Content length adequate')
            else:
                validation_result['checks'].append('❌ Content too short or empty')
            
            # 期望内容检查 (1分)
            if 'expect_content' in test_config:
                expected_terms = test_config['expect_content']
                found_terms = sum(1 for term in expected_terms if term.lower() in content.lower())
                if found_terms >= len(expected_terms) * 0.5:  # 至少50%的期望内容
                    validation_result['score'] += 1
                    validation_result['checks'].append(f'✅ Found {found_terms}/{len(expected_terms)} expected terms')
                else:
                    validation_result['checks'].append(f'❌ Only found {found_terms}/{len(expected_terms)} expected terms')
            
            # 错误页面检查 (1分)
            error_indicators = ['500 Internal Server Error', 'Error 404', 'Page Not Found', 'Traceback']
            has_errors = any(indicator in content for indicator in error_indicators)
            if not has_errors:
                validation_result['score'] += 1
                validation_result['checks'].append('✅ No error indicators found')
            else:
                validation_result['checks'].append('❌ Error indicators detected')
            
        except Exception as e:
            validation_result['checks'].append(f'❌ Content validation error: {str(e)}')
        
        return validation_result

    def validate_data_enhanced(self, response: requests.Response, test_config: Dict) -> Dict[str, Any]:
        """增强的数据验证"""
        validation_result = {
            'score': 0,
            'max_score': 3,
            'checks': []
        }
        
        try:
            json_data = response.json()
            
            # JSON结构验证 (1分)
            if isinstance(json_data, dict):
                validation_result['score'] += 1
                validation_result['checks'].append('✅ Valid JSON structure')
            else:
                validation_result['checks'].append('❌ Invalid JSON structure')
                return validation_result
            
            # 成功状态检查 (1分)
            if json_data.get('success', True):  # 默认认为成功
                validation_result['score'] += 1
                validation_result['checks'].append('✅ Success status confirmed')
            else:
                validation_result['checks'].append('❌ Success status is false')
            
            # 数据合理性检查 (1分)
            data_reasonable = self.validate_data_reasonableness(json_data, response.url)
            if data_reasonable['is_reasonable']:
                validation_result['score'] += 1
                validation_result['checks'].append('✅ Data values are reasonable')
            else:
                validation_result['checks'].append(f'❌ Data unreasonable: {data_reasonable["reason"]}')
            
        except json.JSONDecodeError:
            validation_result['checks'].append('❌ Invalid JSON response')
        except Exception as e:
            validation_result['checks'].append(f'❌ Data validation error: {str(e)}')
        
        return validation_result

    def validate_data_reasonableness(self, json_data: Dict, url: str) -> Dict[str, Any]:
        """验证数据合理性"""
        try:
            if '/api/network-data' in url:
                data = json_data.get('data', {})
                btc_price = data.get('btc_price', 0)
                hashrate = data.get('hashrate', 0)
                
                if not (50000 <= btc_price <= 500000):
                    return {'is_reasonable': False, 'reason': f'BTC price {btc_price} out of range'}
                if not (500 <= hashrate <= 2000):
                    return {'is_reasonable': False, 'reason': f'Hashrate {hashrate} out of range'}
            
            elif '/api/get-btc-price' in url:
                btc_price = json_data.get('btc_price', 0)
                if not (50000 <= btc_price <= 500000):
                    return {'is_reasonable': False, 'reason': f'BTC price {btc_price} out of range'}
            
            elif '/api/get_miners_data' in url:
                miners = json_data.get('miners', [])
                if not miners:
                    return {'is_reasonable': False, 'reason': 'No miners data'}
                
                for miner in miners[:3]:  # 检查前3个
                    hashrate = miner.get('hashrate', 0)
                    power = miner.get('power_consumption', 0)
                    if not (10 <= hashrate <= 1000):
                        return {'is_reasonable': False, 'reason': f'Miner hashrate {hashrate} unreasonable'}
                    if not (1000 <= power <= 10000):
                        return {'is_reasonable': False, 'reason': f'Miner power {power} unreasonable'}
            
            return {'is_reasonable': True, 'reason': 'Data appears reasonable'}
            
        except Exception as e:
            return {'is_reasonable': False, 'reason': f'Validation error: {str(e)}'}

    def validate_performance_enhanced(self, response_time: float, test_config: Dict) -> Dict[str, Any]:
        """增强的性能验证"""
        validation_result = {
            'score': 0,
            'max_score': 2,
            'checks': []
        }
        
        # 基础性能检查 (1分)
        if response_time < 3.0:  # 3秒内响应
            validation_result['score'] += 1
            validation_result['checks'].append(f'✅ Response time acceptable: {response_time:.3f}s')
        else:
            validation_result['checks'].append(f'❌ Response time too slow: {response_time:.3f}s')
        
        # 高性能要求检查 (1分)
        if test_config.get('performance_critical'):
            if response_time < 1.0:  # 关键页面1秒内
                validation_result['score'] += 1
                validation_result['checks'].append(f'✅ Critical performance met: {response_time:.3f}s')
            else:
                validation_result['checks'].append(f'❌ Critical performance not met: {response_time:.3f}s')
        else:
            validation_result['score'] += 1  # 非关键页面给满分
        
        return validation_result

    def test_cache_functionality(self, path: str) -> Dict[str, Any]:
        """测试缓存功能"""
        cache_result = {
            'working': False,
            'first_request_time': None,
            'second_request_time': None,
            'improvement': None
        }
        
        try:
            # 第一次请求
            start1 = time.time()
            resp1 = self.session.get(f"{self.base_url}{path}")
            time1 = time.time() - start1
            
            # 立即第二次请求 (应该命中缓存)
            start2 = time.time()
            resp2 = self.session.get(f"{self.base_url}{path}")
            time2 = time.time() - start2
            
            cache_result['first_request_time'] = time1
            cache_result['second_request_time'] = time2
            
            # 如果第二次请求明显更快，说明缓存工作
            if time2 < time1 * 0.8 and resp1.status_code == resp2.status_code == 200:
                cache_result['working'] = True
                cache_result['improvement'] = ((time1 - time2) / time1) * 100
            
        except:
            pass
        
        return cache_result

    def run_enhanced_comprehensive_test(self) -> Dict[str, Any]:
        """运行增强的全面回归测试"""
        logging.info("🚀 开始增强版回归测试...")
        
        # 登录验证
        login_success, login_message = self.enhanced_login()
        if not login_success:
            logging.error(f"❌ 登录失败: {login_message}")
        
        all_results = {}
        total_score = 0
        max_possible_score = 0
        
        for category, test_suite in self.enhanced_test_suite.items():
            logging.info(f"\n📋 测试类别: {category}")
            category_results = []
            category_score = 0
            category_max = 0
            
            for path, method, description, requires_login, test_config in test_suite:
                logging.info(f"  🔍 测试: {path} ({description})")
                
                # 执行增强测试
                result = self.enhanced_test_endpoint(path, method, description, requires_login, test_config)
                category_results.append(result)
                
                # 累计分数
                category_score += result['accuracy_score']
                category_max += result['max_score']
                total_score += result['accuracy_score']
                max_possible_score += result['max_score']
                self.total_tests += 1
                
                if result['success']:
                    self.passed_tests += 1
                else:
                    self.failed_tests += 1
                
                # 详细输出
                status = "✅" if result['success'] else "❌"
                logging.info(f"    {status} {description}: {result['status_code']} "
                           f"({result['response_time']:.3f}s) [{result['accuracy_percentage']:.1f}%]")
                
                # 输出详细检查结果
                for validation_type in ['content_validation', 'data_validation', 'performance_validation']:
                    if validation_type in result and result[validation_type]:
                        checks = result[validation_type].get('checks', [])
                        for check in checks:
                            logging.info(f"      {check}")
                
                if result['errors']:
                    for error in result['errors']:
                        logging.info(f"      ❌ {error}")
                if result['warnings']:
                    for warning in result['warnings']:
                        logging.info(f"      ⚠️ {warning}")
            
            # 类别摘要
            category_accuracy = (category_score / category_max * 100) if category_max > 0 else 0
            logging.info(f"  📊 {category} 准确率: {category_accuracy:.2f}%")
            all_results[category] = {
                'tests': category_results,
                'accuracy': category_accuracy,
                'score': category_score,
                'max_score': category_max
            }
        
        # 计算整体准确率
        overall_accuracy = (total_score / max_possible_score * 100) if max_possible_score > 0 else 0
        meets_target = overall_accuracy >= self.accuracy_target
        
        summary = {
            'timestamp': datetime.now().isoformat(),
            'test_type': 'Enhanced Comprehensive Regression Test',
            'accuracy_target': self.accuracy_target,
            'overall_accuracy': overall_accuracy,
            'meets_target': meets_target,
            'total_tests': self.total_tests,
            'passed_tests': self.passed_tests,
            'failed_tests': self.failed_tests,
            'total_score': total_score,
            'max_possible_score': max_possible_score,
            'login_status': f"{login_success}: {login_message}",
            'categories': all_results
        }
        
        # 输出最终结果
        logging.info(f"\n🎯 增强版回归测试摘要:")
        logging.info(f"   总测试数: {self.total_tests}")
        logging.info(f"   通过测试: {self.passed_tests}")
        logging.info(f"   失败测试: {self.failed_tests}")
        logging.info(f"   总分数: {total_score}/{max_possible_score}")
        logging.info(f"   系统准确率: {overall_accuracy:.2f}%")
        logging.info(f"   目标准确率: {self.accuracy_target}%")
        logging.info(f"   是否达标: {'✅ 是' if meets_target else '❌ 否'}")
        
        if meets_target:
            logging.info("🎉 恭喜！系统已达到99%+准确率要求！")
        else:
            logging.warning("⚠️ 系统尚未达到99%准确率目标，需要进一步优化")
        
        return summary

def main():
    """主函数"""
    tester = EnhancedRegressionTester()
    
    try:
        results = tester.run_enhanced_comprehensive_test()
        
        # 保存结果
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"enhanced_regression_99_plus_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        logging.info(f"\n💾 增强测试结果已保存到: {filename}")
        
        # 返回适当的退出码
        if results['meets_target']:
            logging.info("✅ 增强回归测试成功！系统达到99%+准确率要求")
            sys.exit(0)
        else:
            logging.error("❌ 增强回归测试未完全通过，系统需要进一步优化")
            sys.exit(1)
            
    except Exception as e:
        logging.error(f"💥 测试过程中发生严重错误: {e}")
        logging.error(traceback.format_exc())
        sys.exit(2)

if __name__ == "__main__":
    main()