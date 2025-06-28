#!/usr/bin/env python3
"""
最终数值回归测试 (Final Numerical Regression Test)
专注数值准确性，全面覆盖前端、中端API、后端数据库
"""
import requests
import time
import json
import logging
import psycopg2
import os
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class FinalNumericalRegressionTest:
    def __init__(self):
        self.base_url = "http://127.0.0.1:5000"
        self.session = requests.Session()
        self.test_results = []
        self.test_start_time = time.time()
        self.test_user_email = "hxl2022hao@gmail.com"

    def authenticate(self):
        """用户认证"""
        try:
            login_data = {'email': self.test_user_email}
            response = self.session.post(f"{self.base_url}/login", data=login_data)
            if response.status_code == 200 and "logout" in response.text.lower():
                logging.info("✅ 用户认证成功")
                return True
            else:
                logging.error(f"❌ 用户认证失败: {response.status_code}")
                return False
        except Exception as e:
            logging.error(f"认证异常: {e}")
            return False

    def log_test(self, test_name: str, status: str, details: str = "", numerical_result=None, test_type: str = "general"):
        """记录测试结果，处理Decimal序列化问题"""
        # 转换Decimal为float以避免JSON序列化错误
        if numerical_result is not None:
            if isinstance(numerical_result, dict):
                numerical_result = {k: float(v) if hasattr(v, '__float__') else v for k, v in numerical_result.items()}
            elif hasattr(numerical_result, '__float__'):
                numerical_result = float(numerical_result)
        
        result = {
            'test_name': test_name,
            'status': status,
            'details': details,
            'numerical_result': numerical_result,
            'test_type': test_type,
            'timestamp': datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        status_icon = "✅" if status == "PASS" else "❌"
        msg = f"{status_icon} {test_name}"
        if details:
            msg += f": {details}"
        if numerical_result is not None:
            msg += f" (数值: {numerical_result})"
        logging.info(msg)

    def test_backend_database_numerical_integrity(self):
        """测试后端数据库数值完整性"""
        logging.info("=== 测试后端数据库数值完整性 ===")
        
        try:
            conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
            cursor = conn.cursor()
            
            # 测试市场数据数值范围
            cursor.execute("""
                SELECT COUNT(*), AVG(btc_price), MIN(btc_price), MAX(btc_price),
                       AVG(network_hashrate), MIN(network_hashrate), MAX(network_hashrate)
                FROM market_analytics 
                WHERE btc_price IS NOT NULL AND btc_price > 0
            """)
            market_stats = cursor.fetchone()
            
            if market_stats and market_stats[0] > 0:
                count = int(market_stats[0])
                avg_price = float(market_stats[1]) if market_stats[1] else 0
                avg_hashrate = float(market_stats[4]) if market_stats[4] else 0
                
                price_valid = 50000 <= avg_price <= 150000
                hashrate_valid = 500 <= avg_hashrate <= 1200 if avg_hashrate > 0 else True
                
                if price_valid and hashrate_valid:
                    self.log_test("后端数值完整性-市场数据", "PASS", 
                                f"记录数: {count}, 平均价格: ${avg_price:,.0f}, 平均算力: {avg_hashrate:.1f}EH/s",
                                {'count': count, 'avg_price': avg_price, 'avg_hashrate': avg_hashrate}, "backend")
                else:
                    self.log_test("后端数值完整性-市场数据", "FAIL", 
                                f"数值异常 - 价格: ${avg_price:,.0f}, 算力: {avg_hashrate}EH/s", None, "backend")
            
            # 修复SQL查询：网络快照统计
            cursor.execute("""
                SELECT COUNT(*), AVG(btc_price), AVG(network_difficulty)
                FROM (
                    SELECT btc_price, network_difficulty
                    FROM network_snapshots 
                    WHERE btc_price > 0 AND network_difficulty > 0
                    ORDER BY recorded_at DESC LIMIT 100
                ) recent_snapshots
            """)
            snapshot_stats = cursor.fetchone()
            
            if snapshot_stats and snapshot_stats[0] > 0:
                count = int(snapshot_stats[0])
                avg_price = float(snapshot_stats[1]) if snapshot_stats[1] else 0
                avg_difficulty = float(snapshot_stats[2]) if snapshot_stats[2] else 0
                difficulty_valid = avg_difficulty > 100000000000000  # 100T minimum
                
                if difficulty_valid:
                    self.log_test("后端数值完整性-网络快照", "PASS", 
                                f"近期记录: {count}, 平均难度: {avg_difficulty/1e12:.2f}T",
                                {'count': count, 'avg_difficulty': avg_difficulty}, "backend")
                else:
                    self.log_test("后端数值完整性-网络快照", "FAIL", 
                                f"难度数值异常: {avg_difficulty}", None, "backend")
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            self.log_test("后端数值完整性-数据库连接", "FAIL", f"数据库操作失败: {str(e)}", None, "backend")

    def test_mining_calculation_numerical_precision(self):
        """测试挖矿计算数值精度 - 基于实际系统逻辑"""
        logging.info("=== 测试挖矿计算数值精度 ===")
        
        # 基于系统实际计算逻辑的测试用例
        test_cases = [
            {
                'name': 'S19 Pro单台基准测试',
                'data': {
                    'miner_model': 'Antminer S19 Pro',
                    'miner_count': '1',
                    'electricity_cost': '0.06'
                },
                'validation': lambda result: (
                    result.get('inputs', {}).get('hashrate', 0) > 0 and
                    result.get('inputs', {}).get('power_consumption', 0) > 0 and
                    result.get('btc_mined', {}).get('daily', 0) > 0
                )
            },
            {
                'name': 'S21高效能测试',
                'data': {
                    'miner_model': 'Antminer S21',
                    'miner_count': '1',
                    'electricity_cost': '0.05'
                },
                'validation': lambda result: (
                    result.get('inputs', {}).get('hashrate', 0) > 0 and
                    result.get('btc_mined', {}).get('daily', 0) > 0
                )
            },
            {
                'name': '多台矿机缩放测试',
                'data': {
                    'miner_model': 'Antminer S19 Pro',
                    'miner_count': '5',
                    'electricity_cost': '0.04'
                },
                'validation': lambda result: (
                    result.get('inputs', {}).get('hashrate', 0) > 500 and  # 5台矿机总算力
                    result.get('btc_mined', {}).get('monthly', 0) > result.get('btc_mined', {}).get('daily', 0) * 25  # 月产>日产*25天
                )
            }
        ]
        
        for test_case in test_cases:
            try:
                start_time = time.time()
                response = self.session.post(f"{self.base_url}/calculate", data=test_case['data'])
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    result = response.json()
                    
                    if result.get('success') and test_case['validation'](result):
                        inputs = result.get('inputs', {})
                        btc_mined = result.get('btc_mined', {})
                        
                        self.log_test(f"数值精度-{test_case['name']}", "PASS", 
                                    f"算力: {inputs.get('hashrate', 0)}TH/s, "
                                    f"功耗: {inputs.get('power_consumption', 0)}W, "
                                    f"日产: {btc_mined.get('daily', 0):.6f}BTC, "
                                    f"响应时间: {response_time:.3f}s",
                                    {
                                        'hashrate': inputs.get('hashrate', 0),
                                        'power': inputs.get('power_consumption', 0),
                                        'daily_btc': btc_mined.get('daily', 0),
                                        'response_time': response_time
                                    }, "numerical")
                    else:
                        error_msg = result.get('error', 'Unknown error') if not result.get('success') else 'Validation failed'
                        self.log_test(f"数值精度-{test_case['name']}", "FAIL", 
                                    f"计算验证失败: {error_msg}", None, "numerical")
                else:
                    self.log_test(f"数值精度-{test_case['name']}", "FAIL", 
                                f"HTTP错误: {response.status_code}", None, "numerical")
                    
            except Exception as e:
                self.log_test(f"数值精度-{test_case['name']}", "FAIL", 
                            f"测试异常: {str(e)}", None, "numerical")

    def test_api_numerical_endpoints(self):
        """测试API数值端点"""
        logging.info("=== 测试API数值端点 ===")
        
        # 核心数值API测试 - 使用正确的端点路径
        api_tests = [
            {
                'name': 'BTC价格API数值验证',
                'url': '/get_btc_price',
                'validation': lambda data: 50000 <= data.get('price', 0) <= 150000
            },
            {
                'name': '网络统计API数值验证',
                'url': '/get_network_stats',
                'validation': lambda data: 500 <= data.get('hashrate', 0) <= 1200 and data.get('difficulty', 0) > 100
            },
            {
                'name': '矿机规格API数值验证',
                'url': '/get_miners',
                'validation': lambda data: len(data.get('miners', [])) >= 8
            },
            {
                'name': '分析市场数据API数值验证',
                'url': '/api/analytics/market-data',
                'validation': lambda data: (data.get('success') == True and 
                                          data.get('data', {}).get('btc_price', 0) > 50000)
            }
        ]
        
        for api_test in api_tests:
            try:
                start_time = time.time()
                response = self.session.get(f"{self.base_url}{api_test['url']}")
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        numerical_valid = api_test['validation'](data)
                        
                        if numerical_valid:
                            # 提取关键数值
                            key_value = None
                            if 'price' in data:
                                key_value = data['price']
                            elif 'hashrate' in data:
                                key_value = data['hashrate']
                            elif 'miners' in data:
                                key_value = len(data['miners'])
                            elif api_test['name'] == '分析市场数据API数值验证':
                                key_value = data.get('data', {}).get('btc_price')
                            
                            self.log_test(f"API数值验证-{api_test['name']}", "PASS", 
                                        f"响应时间: {response_time:.3f}s, 数值验证通过",
                                        key_value, "middleware")
                        else:
                            self.log_test(f"API数值验证-{api_test['name']}", "FAIL", 
                                        "数值验证失败", None, "middleware")
                    except json.JSONDecodeError:
                        self.log_test(f"API数值验证-{api_test['name']}", "FAIL", 
                                    "JSON解析失败", None, "middleware")
                else:
                    self.log_test(f"API数值验证-{api_test['name']}", "FAIL", 
                                f"HTTP状态码: {response.status_code}", None, "middleware")
                    
            except Exception as e:
                self.log_test(f"API数值验证-{api_test['name']}", "FAIL", 
                            f"请求异常: {str(e)}", None, "middleware")

    def test_frontend_numerical_integration(self):
        """测试前端数值集成"""
        logging.info("=== 测试前端数值集成 ===")
        
        # 前端页面数值功能测试
        frontend_tests = [
            {
                'name': '主页计算器数值功能',
                'url': '/',
                'elements': ['矿机型号', '计算', 'BTC', 'TH/s', 'W'],
                'forms': ['<form', '<input', '<select', '<button']
            },
            {
                'name': '电力削减计算器数值功能',
                'url': '/curtailment_calculator',
                'elements': ['削减', '电力', '%', 'MW', '月度'],
                'forms': ['<form', '<input']
            },
            {
                'name': 'CRM客户管理界面',
                'url': '/crm/dashboard',
                'elements': ['客户管理', '仪表盘'],
                'forms': ['<a', '<button']
            },
            {
                'name': '算法差异测试工具',
                'url': '/algorithm_test',
                'elements': ['算法', '测试', '差异'],
                'forms': ['<form', '<input']
            }
        ]
        
        for test in frontend_tests:
            try:
                start_time = time.time()
                response = self.session.get(f"{self.base_url}{test['url']}")
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    page_content = response.text.lower()
                    
                    # 检查页面元素
                    elements_found = sum(1 for element in test['elements'] 
                                       if element.lower() in page_content)
                    
                    # 检查表单元素
                    forms_found = sum(1 for form in test['forms'] 
                                    if form.lower() in page_content)
                    
                    element_coverage = elements_found / len(test['elements'])
                    form_coverage = forms_found / len(test['forms'])
                    
                    if element_coverage >= 0.6 and form_coverage >= 0.5:
                        self.log_test(f"前端数值集成-{test['name']}", "PASS", 
                                    f"元素覆盖: {element_coverage:.1%}, 表单覆盖: {form_coverage:.1%}, "
                                    f"响应时间: {response_time:.3f}s",
                                    {
                                        'element_coverage': element_coverage,
                                        'form_coverage': form_coverage,
                                        'response_time': response_time
                                    }, "frontend")
                    else:
                        self.log_test(f"前端数值集成-{test['name']}", "FAIL", 
                                    f"覆盖不足 - 元素: {element_coverage:.1%}, 表单: {form_coverage:.1%}",
                                    None, "frontend")
                else:
                    self.log_test(f"前端数值集成-{test['name']}", "FAIL", 
                                f"页面无法访问: {response.status_code}", None, "frontend")
                    
            except Exception as e:
                self.log_test(f"前端数值集成-{test['name']}", "FAIL", 
                            f"页面测试异常: {str(e)}", None, "frontend")

    def test_end_to_end_numerical_flow(self):
        """测试端到端数值流程"""
        logging.info("=== 测试端到端数值流程 ===")
        
        # 完整数值流程测试
        try:
            calculation_data = {
                'miner_model': 'Antminer S19 Pro',
                'miner_count': '3',
                'electricity_cost': '0.06'
            }
            
            start_time = time.time()
            response = self.session.post(f"{self.base_url}/calculate", data=calculation_data)
            end_to_end_time = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('success'):
                    inputs = result.get('inputs', {})
                    btc_mined = result.get('btc_mined', {})
                    
                    # 验证数值流程完整性
                    hashrate = inputs.get('hashrate', 0)
                    power = inputs.get('power_consumption', 0)
                    daily_btc = btc_mined.get('daily', 0)
                    monthly_btc = btc_mined.get('monthly', 0)
                    yearly_btc = btc_mined.get('yearly', 0)
                    
                    # 数值逻辑一致性检查
                    daily_monthly_ratio = monthly_btc / daily_btc if daily_btc > 0 else 0
                    monthly_yearly_ratio = yearly_btc / monthly_btc if monthly_btc > 0 else 0
                    
                    data_complete = all([hashrate > 0, power > 0, daily_btc > 0, monthly_btc > 0, yearly_btc > 0])
                    ratios_reasonable = (25 <= daily_monthly_ratio <= 35 and 
                                       10 <= monthly_yearly_ratio <= 15)
                    performance_good = end_to_end_time < 2.0
                    
                    if data_complete and ratios_reasonable and performance_good:
                        self.log_test("端到端数值流程-完整性验证", "PASS", 
                                    f"3台S19 Pro: 算力={hashrate}TH/s, 功耗={power}W, "
                                    f"日产={daily_btc:.6f}BTC, 月产={monthly_btc:.6f}BTC, "
                                    f"年产={yearly_btc:.6f}BTC, 处理时间={end_to_end_time:.3f}s",
                                    {
                                        'hashrate': hashrate,
                                        'power': power,
                                        'daily_btc': daily_btc,
                                        'monthly_btc': monthly_btc,
                                        'yearly_btc': yearly_btc,
                                        'processing_time': end_to_end_time,
                                        'daily_monthly_ratio': daily_monthly_ratio,
                                        'monthly_yearly_ratio': monthly_yearly_ratio
                                    }, "numerical")
                    else:
                        self.log_test("端到端数值流程-完整性验证", "FAIL", 
                                    f"数值流程验证失败 - 数据完整: {data_complete}, "
                                    f"比例合理: {ratios_reasonable}, 性能良好: {performance_good}",
                                    None, "numerical")
                else:
                    self.log_test("端到端数值流程-完整性验证", "FAIL", 
                                f"计算处理失败: {result.get('error')}", None, "numerical")
            else:
                self.log_test("端到端数值流程-完整性验证", "FAIL", 
                            f"HTTP请求失败: {response.status_code}", None, "numerical")
                
        except Exception as e:
            self.log_test("端到端数值流程-完整性验证", "FAIL", 
                        f"流程测试异常: {str(e)}", None, "numerical")

    def generate_final_report(self):
        """生成最终测试报告"""
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r['status'] == 'PASS'])
        failed_tests = total_tests - passed_tests
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        test_duration = time.time() - self.test_start_time
        
        # 按测试类型统计
        type_stats = {}
        for test_type in ['backend', 'middleware', 'frontend', 'numerical']:
            type_results = [r for r in self.test_results if r['test_type'] == test_type]
            type_passed = len([r for r in type_results if r['status'] == 'PASS'])
            type_stats[test_type] = {
                'total': len(type_results),
                'passed': type_passed,
                'success_rate': (type_passed / len(type_results) * 100) if type_results else 0
            }
        
        # 数值测试统计
        numerical_results = [r for r in self.test_results 
                           if r['test_type'] == 'numerical' and r['numerical_result'] is not None]
        
        report = {
            'test_summary': {
                'total_tests': total_tests,
                'passed_tests': passed_tests,
                'failed_tests': failed_tests,
                'success_rate': round(success_rate, 1),
                'test_duration': round(test_duration, 2),
                'test_timestamp': datetime.now().isoformat()
            },
            'layer_performance': type_stats,
            'numerical_test_count': len(numerical_results),
            'test_results': self.test_results,
            'recommendations': self.generate_recommendations()
        }
        
        # 保存详细报告
        with open('final_numerical_regression_report.json', 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        logging.info("=== 最终数值回归测试报告 ===")
        logging.info(f"📊 总测试: {total_tests}")
        logging.info(f"✅ 通过: {passed_tests}")
        logging.info(f"❌ 失败: {failed_tests}")
        logging.info(f"📈 成功率: {success_rate:.1f}%")
        logging.info(f"⏱️ 测试耗时: {test_duration:.2f}秒")
        logging.info(f"🔢 数值测试: {len(numerical_results)} 项")
        
        for test_type, stats in type_stats.items():
            if stats['total'] > 0:
                logging.info(f"🏗️ {test_type}: {stats['passed']}/{stats['total']} ({stats['success_rate']:.1f}%)")
                
        logging.info(f"📄 详细报告已保存: final_numerical_regression_report.json")
        
        return report

    def generate_recommendations(self):
        """生成改进建议"""
        failed_tests = [r for r in self.test_results if r['status'] == 'FAIL']
        recommendations = []
        
        # 按失败类型分析
        backend_failures = len([r for r in failed_tests if r['test_type'] == 'backend'])
        middleware_failures = len([r for r in failed_tests if r['test_type'] == 'middleware'])
        frontend_failures = len([r for r in failed_tests if r['test_type'] == 'frontend'])
        numerical_failures = len([r for r in failed_tests if r['test_type'] == 'numerical'])
        
        if backend_failures > 0:
            recommendations.append("后端数据库: 优化SQL查询和数据完整性验证")
        
        if middleware_failures > 0:
            recommendations.append("中端API: 检查API端点路径和响应格式")
        
        if frontend_failures > 0:
            recommendations.append("前端界面: 确保页面元素加载和路由访问")
        
        if numerical_failures > 0:
            recommendations.append("数值计算: 验证计算逻辑和数值精度")
        
        return recommendations

    def run_final_numerical_test(self):
        """运行最终数值测试"""
        logging.info("🚀 开始最终数值回归测试")
        logging.info("🎯 专注数值精度和前端中端后端功能验证")
        
        # 用户认证
        if not self.authenticate():
            logging.error("用户认证失败，测试终止")
            return
        
        # 执行测试
        self.test_backend_database_numerical_integrity()
        self.test_mining_calculation_numerical_precision()
        self.test_api_numerical_endpoints()
        self.test_frontend_numerical_integration()
        self.test_end_to_end_numerical_flow()
        
        # 生成报告
        report = self.generate_final_report()
        return report

def main():
    """主函数"""
    tester = FinalNumericalRegressionTest()
    report = tester.run_final_numerical_test()
    
    print("\n" + "="*50)
    print("最终数值回归测试报告")
    print("="*50)
    print(f"总测试: {report['test_summary']['total_tests']}")
    print(f"通过: {report['test_summary']['passed_tests']}")
    print(f"失败: {report['test_summary']['failed_tests']}")
    print(f"成功率: {report['test_summary']['success_rate']}%")
    print(f"测试耗时: {report['test_summary']['test_duration']}秒")
    print(f"数值精度测试: {report['numerical_test_count']} 项")
    
    for layer, stats in report['layer_performance'].items():
        if stats['total'] > 0:
            print(f"{layer}: {stats['passed']}/{stats['total']} ({stats['success_rate']:.1f}%)")
    
    print("="*50)

if __name__ == "__main__":
    main()