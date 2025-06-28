#!/usr/bin/env python3
"""
聚焦数值回归测试 (Focused Numerical Regression Test)
专注数值准确性，覆盖前端、中端API、后端数据库
"""
import requests
import time
import json
import logging
import psycopg2
import os
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class FocusedNumericalRegressionTest:
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
        """记录测试结果"""
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
                count, avg_price, min_price, max_price, avg_hashrate, min_hashrate, max_hashrate = market_stats
                
                # 验证价格数值合理性
                price_valid = 50000 <= avg_price <= 150000 and min_price > 0 and max_price < 200000
                hashrate_valid = 500 <= avg_hashrate <= 1200 if avg_hashrate else True
                
                if price_valid and hashrate_valid:
                    self.log_test("后端数值完整性-市场数据", "PASS", 
                                f"记录数: {count}, 平均价格: ${avg_price:,.0f}, 平均算力: {avg_hashrate:.1f}EH/s",
                                {'count': count, 'avg_price': avg_price, 'avg_hashrate': avg_hashrate}, "backend")
                else:
                    self.log_test("后端数值完整性-市场数据", "FAIL", 
                                f"数值异常 - 价格: ${avg_price:,.0f}, 算力: {avg_hashrate}EH/s", None, "backend")
            
            # 测试网络快照数值一致性
            cursor.execute("""
                SELECT COUNT(*), AVG(btc_price), AVG(network_difficulty)
                FROM network_snapshots 
                WHERE btc_price > 0 AND network_difficulty > 0
                ORDER BY recorded_at DESC LIMIT 100
            """)
            snapshot_stats = cursor.fetchone()
            
            if snapshot_stats and snapshot_stats[0] > 0:
                count, avg_price, avg_difficulty = snapshot_stats
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
            self.log_test("后端数值完整性-数据库连接", "FAIL", f"数据库连接失败: {str(e)}", None, "backend")

    def test_mining_calculation_numerical_precision(self):
        """测试挖矿计算数值精度"""
        logging.info("=== 测试挖矿计算数值精度 ===")
        
        # 精确数值测试用例
        test_cases = [
            {
                'name': 'S19 Pro单台精度测试',
                'data': {
                    'miner_model': 'Antminer S19 Pro',
                    'miner_count': '1',
                    'electricity_cost': '0.06'
                },
                'expected_hashrate': 110,  # TH/s
                'expected_power': 3250,    # W
                'tolerance': 0.1  # 10%容差
            },
            {
                'name': 'S21单台精度测试',
                'data': {
                    'miner_model': 'Antminer S21',
                    'miner_count': '1',
                    'electricity_cost': '0.05'
                },
                'expected_hashrate': 200,  # TH/s
                'expected_power': 3550,    # W
                'tolerance': 0.1
            },
            {
                'name': '多台矿机规模测试',
                'data': {
                    'miner_model': 'Antminer S19 Pro',
                    'miner_count': '10',
                    'electricity_cost': '0.04'
                },
                'expected_hashrate': 1100,  # TH/s
                'expected_power': 32500,     # W
                'tolerance': 0.1
            }
        ]
        
        for test_case in test_cases:
            try:
                start_time = time.time()
                response = self.session.post(f"{self.base_url}/calculate", data=test_case['data'])
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    result = response.json()
                    
                    if result.get('success'):
                        inputs = result.get('inputs', {})
                        btc_mined = result.get('btc_mined', {})
                        
                        actual_hashrate = inputs.get('hashrate', 0)
                        actual_power = inputs.get('power_consumption', 0)
                        daily_btc = btc_mined.get('daily', 0)
                        
                        # 数值精度验证
                        hashrate_error = abs(actual_hashrate - test_case['expected_hashrate']) / test_case['expected_hashrate']
                        power_error = abs(actual_power - test_case['expected_power']) / test_case['expected_power']
                        
                        precision_ok = (hashrate_error <= test_case['tolerance'] and 
                                      power_error <= test_case['tolerance'] and
                                      daily_btc > 0)
                        
                        if precision_ok:
                            self.log_test(f"数值精度-{test_case['name']}", "PASS", 
                                        f"算力: {actual_hashrate}TH/s (误差: {hashrate_error:.1%}), "
                                        f"功耗: {actual_power}W (误差: {power_error:.1%}), "
                                        f"日产BTC: {daily_btc:.6f}, 响应时间: {response_time:.3f}s",
                                        {
                                            'hashrate': actual_hashrate,
                                            'power': actual_power,
                                            'daily_btc': daily_btc,
                                            'hashrate_error': hashrate_error,
                                            'power_error': power_error,
                                            'response_time': response_time
                                        }, "numerical")
                        else:
                            self.log_test(f"数值精度-{test_case['name']}", "FAIL", 
                                        f"精度超出容差 - 算力误差: {hashrate_error:.1%}, 功耗误差: {power_error:.1%}",
                                        None, "numerical")
                    else:
                        self.log_test(f"数值精度-{test_case['name']}", "FAIL", 
                                    f"计算失败: {result.get('error', 'Unknown error')}", None, "numerical")
                else:
                    self.log_test(f"数值精度-{test_case['name']}", "FAIL", 
                                f"HTTP错误: {response.status_code}", None, "numerical")
                    
            except Exception as e:
                self.log_test(f"数值精度-{test_case['name']}", "FAIL", 
                            f"测试异常: {str(e)}", None, "numerical")

    def test_api_numerical_endpoints(self):
        """测试API数值端点"""
        logging.info("=== 测试API数值端点 ===")
        
        # 核心数值API测试
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
                'validation': lambda data: len(data.get('miners', [])) >= 8 and all(
                    miner.get('hashrate', 0) > 50 and miner.get('power', 0) > 1000 
                    for miner in data.get('miners', [])[:3]  # 检查前3个
                )
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
                'form_elements': ['矿机型号', '计算', 'BTC'],
                'numerical_indicators': ['TH/s', 'W', '0.']  # 算力、功耗、BTC数值
            },
            {
                'name': '电力削减计算器数值功能',
                'url': '/curtailment_calculator',
                'form_elements': ['削减', '电力', '%'],
                'numerical_indicators': ['MW', '月度', '收益']
            },
            {
                'name': '分析仪表盘数值显示',
                'url': '/analytics_dashboard',
                'form_elements': ['分析', '市场'],
                'numerical_indicators': ['$', 'EH/s', '%']
            }
        ]
        
        for test in frontend_tests:
            try:
                start_time = time.time()
                response = self.session.get(f"{self.base_url}{test['url']}")
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    page_content = response.text
                    
                    # 检查表单元素
                    form_elements_found = sum(1 for element in test['form_elements'] 
                                            if element in page_content)
                    
                    # 检查数值指示器
                    numerical_indicators_found = sum(1 for indicator in test['numerical_indicators'] 
                                                   if indicator in page_content)
                    
                    form_coverage = form_elements_found / len(test['form_elements'])
                    numerical_coverage = numerical_indicators_found / len(test['numerical_indicators'])
                    
                    if form_coverage >= 0.7 and numerical_coverage >= 0.5:
                        self.log_test(f"前端数值集成-{test['name']}", "PASS", 
                                    f"表单覆盖: {form_coverage:.1%}, 数值覆盖: {numerical_coverage:.1%}, "
                                    f"响应时间: {response_time:.3f}s",
                                    {
                                        'form_coverage': form_coverage,
                                        'numerical_coverage': numerical_coverage,
                                        'response_time': response_time
                                    }, "frontend")
                    else:
                        self.log_test(f"前端数值集成-{test['name']}", "FAIL", 
                                    f"覆盖不足 - 表单: {form_coverage:.1%}, 数值: {numerical_coverage:.1%}",
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
        
        # 完整数值流程测试：前端表单 -> API处理 -> 后端计算 -> 数值返回
        try:
            calculation_data = {
                'miner_model': 'Antminer S19 Pro',
                'miner_count': '5',
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
                    
                    # 数值逻辑一致性检查
                    expected_hashrate = 110 * 5  # 5台S19 Pro
                    expected_power = 3250 * 5
                    monthly_daily_ratio = monthly_btc / daily_btc if daily_btc > 0 else 0
                    
                    hashrate_accurate = abs(hashrate - expected_hashrate) / expected_hashrate < 0.1
                    power_accurate = abs(power - expected_power) / expected_power < 0.1
                    ratio_reasonable = 28 <= monthly_daily_ratio <= 32  # 约30天
                    
                    if hashrate_accurate and power_accurate and ratio_reasonable:
                        self.log_test("端到端数值流程-完整性验证", "PASS", 
                                    f"5台S19 Pro: 算力={hashrate}TH/s, 功耗={power}W, "
                                    f"日产={daily_btc:.6f}BTC, 月产={monthly_btc:.6f}BTC, "
                                    f"处理时间={end_to_end_time:.3f}s",
                                    {
                                        'hashrate': hashrate,
                                        'power': power,
                                        'daily_btc': daily_btc,
                                        'monthly_btc': monthly_btc,
                                        'processing_time': end_to_end_time,
                                        'monthly_daily_ratio': monthly_daily_ratio
                                    }, "numerical")
                    else:
                        self.log_test("端到端数值流程-完整性验证", "FAIL", 
                                    f"数值逻辑不一致 - 算力准确: {hashrate_accurate}, "
                                    f"功耗准确: {power_accurate}, 比例合理: {ratio_reasonable}",
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

    def generate_focused_report(self):
        """生成聚焦测试报告"""
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r['status'] == 'PASS'])
        failed_tests = total_tests - passed_tests
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        test_duration = time.time() - self.test_start_time
        
        # 按测试类型统计
        type_stats = {}
        for test_type in ['backend', 'middleware', 'frontend', 'numerical']:
            type_count = len([r for r in self.test_results if r['test_type'] == test_type])
            type_passed = len([r for r in self.test_results if r['test_type'] == test_type and r['status'] == 'PASS'])
            type_stats[test_type] = {'total': type_count, 'passed': type_passed}
        
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
            'test_results': self.test_results
        }
        
        # 保存详细报告
        with open('focused_numerical_regression_report.json', 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        logging.info("=== 聚焦数值回归测试报告 ===")
        logging.info(f"📊 总测试: {total_tests}")
        logging.info(f"✅ 通过: {passed_tests}")
        logging.info(f"❌ 失败: {failed_tests}")
        logging.info(f"📈 成功率: {success_rate:.1f}%")
        logging.info(f"⏱️ 测试耗时: {test_duration:.2f}秒")
        logging.info(f"🔢 数值测试: {len(numerical_results)} 项")
        for test_type, stats in type_stats.items():
            if stats['total'] > 0:
                layer_rate = (stats['passed'] / stats['total'] * 100)
                logging.info(f"🏗️ {test_type}: {stats['passed']}/{stats['total']} ({layer_rate:.1f}%)")
        logging.info(f"📄 详细报告已保存: focused_numerical_regression_report.json")
        
        return report

    def run_focused_numerical_test(self):
        """运行聚焦数值测试"""
        logging.info("🚀 开始聚焦数值回归测试")
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
        report = self.generate_focused_report()
        return report

def main():
    """主函数"""
    tester = FocusedNumericalRegressionTest()
    report = tester.run_focused_numerical_test()
    
    print("\n" + "="*50)
    print("聚焦数值回归测试报告")
    print("="*50)
    print(f"总测试: {report['test_summary']['total_tests']}")
    print(f"通过: {report['test_summary']['passed_tests']}")
    print(f"失败: {report['test_summary']['failed_tests']}")
    print(f"成功率: {report['test_summary']['success_rate']}%")
    print(f"测试耗时: {report['test_summary']['test_duration']}秒")
    print(f"数值精度测试: {report['numerical_test_count']} 项")
    print("="*50)

if __name__ == "__main__":
    main()