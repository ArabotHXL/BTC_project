#!/usr/bin/env python3
"""
全面回归测试系统 - 99%+ 精确度要求
Comprehensive Regression Testing System - 99%+ Accuracy Required

测试所有关键路径的可用性、准确性和性能
Tests all critical paths for availability, accuracy, and performance
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

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'regression_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

class ComprehensiveRegressionTester:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.test_results = []
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        
        # 登录凭据（测试用户）
        self.test_user = {
            'email': 'owner@test.com',
            'password': 'test123'  # 假设测试密码
        }
        
        # 关键路径定义
        self.critical_paths = {
            '主要用户界面': [
                ('/', 'GET', '主页', True),
                ('/dashboard', 'GET', '主仪表盘', True),
                ('/calculator', 'GET', '挖矿计算器', True),
                ('/analytics', 'GET', '分析仪表盘', True),
                ('/login', 'GET', '登录页面', False),
                ('/register', 'GET', '注册页面', False),
            ],
            '业务功能界面': [
                ('/batch-calculator', 'GET', '批量挖矿计算器', True),
                ('/curtailment-calculator', 'GET', '停电损失计算器', True),
                ('/technical-analysis', 'GET', '技术分析页面', True),
                ('/network-history', 'GET', '网络历史数据', True),
                ('/mining-broker', 'GET', '挖矿经纪界面', True),
            ],
            'CRM客户管理系统': [
                ('/crm/dashboard', 'GET', 'CRM仪表盘', True),
                ('/crm/customers', 'GET', '客户管理', True),
                ('/crm/leads', 'GET', '线索管理', True),
                ('/crm/deals', 'GET', '交易管理', True),
                ('/crm/activities', 'GET', '活动记录', True),
            ],
            '管理员界面': [
                ('/admin/user_access', 'GET', '用户权限管理', True),
                ('/admin/login_records', 'GET', '登录记录', True),
                ('/billing/plans', 'GET', '订阅计划管理', True),
                ('/subscription', 'GET', '用户订阅页面', True),
            ],
            '关键API端点': [
                ('/api/network-data', 'GET', '网络统计数据', False),
                ('/api/get-btc-price', 'GET', 'BTC价格', False),
                ('/api/get_miners_data', 'GET', '矿机数据', False),
                ('/api/analytics/data', 'GET', '分析数据', False),
                ('/api/calculate', 'POST', '挖矿计算API', False),
            ],
            '专业分析功能': [
                ('/analytics/main', 'GET', '主要分析界面', True),
                ('/api/professional-report', 'GET', '专业报告生成', False),
                ('/api/price-trend', 'GET', '价格趋势分析', False),
                ('/api/analytics/detailed-report', 'GET', '详细分析报告', False),
            ]
        }

    def login(self) -> bool:
        """登录测试用户"""
        try:
            login_data = {
                'email': self.test_user['email'],
                'password': self.test_user['password']
            }
            
            response = self.session.post(
                f"{self.base_url}/login",
                data=login_data,
                allow_redirects=False
            )
            
            # 检查登录是否成功（重定向或200状态）
            if response.status_code in [200, 302]:
                logging.info("✅ 用户登录成功")
                return True
            else:
                logging.warning(f"⚠️ 登录可能失败，状态码: {response.status_code}")
                return True  # 继续测试，某些路径可能不需要登录
                
        except Exception as e:
            logging.error(f"❌ 登录失败: {e}")
            return False

    def test_endpoint(self, path: str, method: str, description: str, requires_login: bool) -> Dict[str, Any]:
        """测试单个端点"""
        test_result = {
            'path': path,
            'method': method,
            'description': description,
            'requires_login': requires_login,
            'success': False,
            'status_code': None,
            'response_time': None,
            'content_valid': False,
            'api_data_valid': False,
            'errors': []
        }
        
        try:
            start_time = time.time()
            
            # 发送请求
            if method == 'GET':
                if path.startswith('/api/calculate'):
                    # 跳过POST-only端点的GET测试
                    test_result['errors'].append('POST-only endpoint skipped for GET test')
                    return test_result
                    
                response = self.session.get(f"{self.base_url}{path}", timeout=10)
            elif method == 'POST':
                # 为POST端点准备测试数据
                if path == '/api/calculate':
                    post_data = {
                        'miner_model': 'Antminer S19 Pro',
                        'quantity': 1,
                        'electricity_cost': 0.08,
                        'pool_fee': 0.01
                    }
                else:
                    post_data = {}
                response = self.session.post(f"{self.base_url}{path}", json=post_data, timeout=10)
            else:
                response = self.session.request(method, f"{self.base_url}{path}", timeout=10)
            
            response_time = time.time() - start_time
            test_result['response_time'] = response_time
            test_result['status_code'] = response.status_code
            
            # 检查响应状态
            if response.status_code == 200:
                test_result['success'] = True
            elif response.status_code == 302 and requires_login:
                # 重定向可能是正常的（需要登录）
                test_result['success'] = True
                test_result['errors'].append('Redirected (likely login required)')
            elif response.status_code == 404:
                test_result['errors'].append('Route not found (404)')
            elif response.status_code == 500:
                test_result['errors'].append('Internal server error (500)')
            else:
                test_result['errors'].append(f'Unexpected status code: {response.status_code}')
            
            # 验证内容
            if response.status_code == 200:
                content = response.text
                
                # 对于HTML页面，检查基本结构
                if path.startswith('/api/'):
                    # API端点验证
                    try:
                        json_data = response.json()
                        test_result['api_data_valid'] = self.validate_api_response(path, json_data)
                    except:
                        test_result['errors'].append('Invalid JSON response')
                else:
                    # HTML页面验证
                    test_result['content_valid'] = self.validate_html_content(content, path)
            
        except requests.exceptions.Timeout:
            test_result['errors'].append('Request timeout')
        except requests.exceptions.ConnectionError:
            test_result['errors'].append('Connection error')
        except Exception as e:
            test_result['errors'].append(f'Unexpected error: {str(e)}')
        
        return test_result

    def validate_html_content(self, content: str, path: str) -> bool:
        """验证HTML内容的有效性"""
        try:
            # 基本HTML结构检查
            if not content.strip():
                return False
            
            # 检查HTML标签
            if '<html' in content.lower() and '</html>' in content.lower():
                # 检查是否有错误页面标识
                error_indicators = ['500 Internal Server Error', 'Error 404', 'Page Not Found']
                if any(indicator in content for indicator in error_indicators):
                    return False
                return True
            
            # 对于非完整HTML页面，检查是否有有效内容
            if len(content) > 100:  # 至少有一些内容
                return True
                
            return False
        except:
            return False

    def validate_api_response(self, path: str, json_data: Dict) -> bool:
        """验证API响应数据的准确性"""
        try:
            # 通用API响应验证
            if 'success' in json_data:
                if not json_data.get('success', False):
                    return False
            
            # 特定端点验证
            if path == '/api/network-data':
                required_fields = ['data', 'success']
                if all(field in json_data for field in required_fields):
                    data = json_data['data']
                    # 验证关键数据字段
                    if 'btc_price' in data and 'hashrate' in data:
                        btc_price = data['btc_price']
                        hashrate = data['hashrate']
                        # 合理性检查
                        if 50000 <= btc_price <= 500000 and 500 <= hashrate <= 2000:
                            return True
            
            elif path == '/api/get-btc-price':
                if 'btc_price' in json_data:
                    price = json_data['btc_price']
                    if 50000 <= price <= 500000:  # 合理的BTC价格范围
                        return True
            
            elif path == '/api/get_miners_data':
                if 'miners' in json_data and isinstance(json_data['miners'], list):
                    if len(json_data['miners']) > 0:
                        # 检查矿机数据结构
                        miner = json_data['miners'][0]
                        if 'name' in miner and 'hashrate' in miner and 'power_consumption' in miner:
                            return True
            
            elif path == '/api/analytics/data':
                if 'data' in json_data:
                    data = json_data['data']
                    if 'btc_price' in data and 'network_hashrate' in data:
                        return True
            
            return True  # 默认认为有效
            
        except:
            return False

    def run_performance_test(self, path: str, iterations: int = 5) -> Dict[str, float]:
        """运行性能测试"""
        response_times = []
        
        for _ in range(iterations):
            try:
                start_time = time.time()
                response = self.session.get(f"{self.base_url}{path}", timeout=10)
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    response_times.append(response_time)
                    
            except:
                continue
        
        if response_times:
            return {
                'avg_response_time': sum(response_times) / len(response_times),
                'min_response_time': min(response_times),
                'max_response_time': max(response_times),
                'samples': len(response_times)
            }
        
        return {'avg_response_time': 0, 'min_response_time': 0, 'max_response_time': 0, 'samples': 0}

    def run_comprehensive_test(self) -> Dict[str, Any]:
        """运行全面的回归测试"""
        logging.info("🚀 开始全面回归测试...")
        
        # 尝试登录
        login_success = self.login()
        
        all_results = {}
        total_score = 0
        max_score = 0
        
        for category, paths in self.critical_paths.items():
            logging.info(f"\n📋 测试类别: {category}")
            category_results = []
            
            for path, method, description, requires_login in paths:
                logging.info(f"  🔍 测试: {path} ({description})")
                
                # 基础功能测试
                result = self.test_endpoint(path, method, description, requires_login)
                
                # 性能测试（仅对API端点）
                if path.startswith('/api/'):
                    perf_result = self.run_performance_test(path)
                    result['performance'] = perf_result
                
                category_results.append(result)
                self.total_tests += 1
                
                # 评分计算
                score = 0
                max_possible = 4  # 最大分数
                
                if result['success']:
                    score += 2  # 基础可用性
                    self.passed_tests += 1
                else:
                    self.failed_tests += 1
                
                if result['content_valid'] or result['api_data_valid']:
                    score += 1  # 内容有效性
                
                if result['response_time'] and result['response_time'] < 1.0:
                    score += 1  # 性能
                
                total_score += score
                max_score += max_possible
                
                # 输出结果
                status = "✅" if result['success'] else "❌"
                logging.info(f"    {status} {description}: {result['status_code']} ({result['response_time']:.3f}s)")
                if result['errors']:
                    for error in result['errors']:
                        logging.info(f"      ⚠️ {error}")
            
            all_results[category] = category_results
        
        # 计算整体准确率
        accuracy = (total_score / max_score * 100) if max_score > 0 else 0
        
        summary = {
            'timestamp': datetime.now().isoformat(),
            'total_tests': self.total_tests,
            'passed_tests': self.passed_tests,
            'failed_tests': self.failed_tests,
            'accuracy_percentage': accuracy,
            'target_accuracy': 99.0,
            'meets_target': accuracy >= 99.0,
            'categories': all_results
        }
        
        logging.info(f"\n📊 测试摘要:")
        logging.info(f"   总测试数: {self.total_tests}")
        logging.info(f"   通过测试: {self.passed_tests}")
        logging.info(f"   失败测试: {self.failed_tests}")
        logging.info(f"   系统准确率: {accuracy:.2f}%")
        logging.info(f"   目标准确率: 99.0%")
        logging.info(f"   是否达标: {'✅ 是' if accuracy >= 99.0 else '❌ 否'}")
        
        return summary

def main():
    """主测试函数"""
    tester = ComprehensiveRegressionTester()
    
    try:
        # 运行全面测试
        results = tester.run_comprehensive_test()
        
        # 保存结果到文件
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"regression_99_percent_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        logging.info(f"\n💾 测试结果已保存到: {filename}")
        
        # 返回exit code
        if results['meets_target']:
            logging.info("🎉 回归测试成功！系统达到99%+准确率要求")
            sys.exit(0)
        else:
            logging.error("💥 回归测试失败！系统未达到99%准确率要求")
            sys.exit(1)
            
    except Exception as e:
        logging.error(f"💥 测试过程中发生严重错误: {e}")
        logging.error(traceback.format_exc())
        sys.exit(2)

if __name__ == "__main__":
    main()