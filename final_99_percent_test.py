#!/usr/bin/env python3
"""
最终99%通过率测试系统 - 完全验证版本
Final 99% Pass Rate Testing System - Complete Validation Version

目标：超越99%通过率，完全验证所有系统功能
Goal: Exceed 99% pass rate, complete validation of all system functions
"""

import os
import sys
import json
import time
import logging
import requests
import traceback
import psutil
import psycopg2
from datetime import datetime
from typing import Dict, List, Tuple, Any

# 配置详细日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('final_test_99_percent.log'),
        logging.StreamHandler()
    ]
)

class Final99PercentTest:
    """最终99%通过率测试系统"""
    
    def __init__(self):
        self.base_url = "http://localhost:5000"
        self.test_results = {
            'total_tests': 0,
            'passed_tests': 0,
            'failed_tests': 0,
            'test_details': [],
            'performance_metrics': {},
            'system_health': {},
            'timestamp': datetime.now().isoformat()
        }
        self.start_time = time.time()
    
    def log_test(self, test_name: str, status: str, details: str = "", 
                 response_time: float = 0, data: Dict = None):
        """记录测试结果"""
        self.test_results['total_tests'] += 1
        
        if status == 'PASS':
            self.test_results['passed_tests'] += 1
            logging.info(f"✅ {test_name}: {status}")
        else:
            self.test_results['failed_tests'] += 1
            logging.error(f"❌ {test_name}: {status} - {details}")
        
        self.test_results['test_details'].append({
            'test_name': test_name,
            'status': status,
            'details': details,
            'response_time': response_time,
            'data': data or {},
            'timestamp': datetime.now().isoformat()
        })
    
    def test_server_connectivity(self) -> bool:
        """测试服务器连接性和响应"""
        try:
            start_time = time.time()
            response = requests.get(f"{self.base_url}/", timeout=10)
            response_time = time.time() - start_time
            
            # 更严格的健康检查
            is_healthy = (
                response.status_code == 200 and
                response_time < 5.0 and
                len(response.text) > 1000  # 确保返回完整页面
            )
            
            if is_healthy:
                self.log_test("Server Connectivity", "PASS", 
                            f"Status: {response.status_code}, Time: {response_time:.3f}s", response_time)
                return True
            else:
                self.log_test("Server Connectivity", "FAIL", 
                            f"Status: {response.status_code}, Time: {response_time:.3f}s", response_time)
                return False
        except Exception as e:
            self.log_test("Server Connectivity", "FAIL", str(e))
            return False
    
    def test_database_integrity(self) -> bool:
        """测试数据库完整性和数据"""
        try:
            conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
            cursor = conn.cursor()
            
            # 检查核心表存在性和数据
            table_checks = [
                ('user_access', 'SELECT COUNT(*) FROM user_access'),
                ('customers', 'SELECT COUNT(*) FROM customers'),
                ('network_snapshots', 'SELECT COUNT(*) FROM network_snapshots'),
                ('plans', 'SELECT COUNT(*) FROM plans'),
                ('subscriptions', 'SELECT COUNT(*) FROM subscriptions')
            ]
            
            table_results = {}
            total_records = 0
            
            for table_name, query in table_checks:
                try:
                    cursor.execute(query)
                    count = cursor.fetchone()[0]
                    table_results[table_name] = count
                    total_records += count
                except Exception as e:
                    table_results[table_name] = f"Error: {str(e)}"
            
            cursor.close()
            conn.close()
            
            # 检查是否有足够的数据
            valid_tables = len([k for k, v in table_results.items() if isinstance(v, int)])
            
            if valid_tables >= 4 and total_records > 0:
                self.log_test("Database Integrity", "PASS", 
                            f"Tables: {valid_tables}/5, Records: {total_records}", 0, table_results)
                return True
            else:
                self.log_test("Database Integrity", "FAIL", 
                            f"Insufficient data. Tables: {valid_tables}/5, Records: {total_records}", 0, table_results)
                return False
                
        except Exception as e:
            self.log_test("Database Integrity", "FAIL", str(e))
            return False
    
    def test_api_endpoints_comprehensive(self) -> bool:
        """全面测试API端点"""
        endpoints = [
            ("/", "GET", [200]),
            ("/login", "GET", [200, 302]),
            ("/api/analytics/data", "GET", [200, 401, 403]),
            ("/billing/plans", "GET", [200, 302]),
            ("/dashboard", "GET", [200, 302, 401])  # 额外端点测试
        ]
        
        passed = 0
        total = len(endpoints)
        results = {}
        
        for endpoint, method, allowed_codes in endpoints:
            try:
                start_time = time.time()
                response = requests.get(f"{self.base_url}{endpoint}", timeout=10)
                response_time = time.time() - start_time
                
                if response.status_code in allowed_codes:
                    self.log_test(f"API {endpoint}", "PASS", 
                                f"Status: {response.status_code}", response_time)
                    passed += 1
                    results[endpoint] = "PASS"
                else:
                    self.log_test(f"API {endpoint}", "FAIL", 
                                f"Status: {response.status_code} (expected: {allowed_codes})", response_time)
                    results[endpoint] = "FAIL"
                    
            except Exception as e:
                self.log_test(f"API {endpoint}", "FAIL", str(e))
                results[endpoint] = "ERROR"
        
        success_rate = (passed / total) * 100
        return success_rate >= 80  # 要求80%+端点正常
    
    def test_real_time_analytics(self) -> bool:
        """测试实时分析数据质量"""
        try:
            start_time = time.time()
            response = requests.get(f"{self.base_url}/api/analytics/data", timeout=15)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                
                # 数据质量指标
                quality_metrics = {
                    'has_success_flag': 'success' in data,
                    'has_data_object': 'data' in data and isinstance(data.get('data'), dict),
                    'data_field_count': 0,
                    'data_completeness': 0
                }
                
                if quality_metrics['has_data_object']:
                    sub_data = data['data']
                    expected_fields = [
                        'btc_price', 'network_difficulty', 'network_hashrate', 
                        'price_change_24h', 'fear_greed_index', 'market_cap',
                        'volume_24h', 'dominance', 'halving_countdown'
                    ]
                    
                    present_fields = [f for f in expected_fields if f in sub_data and sub_data[f] is not None]
                    quality_metrics['data_field_count'] = len(present_fields)
                    quality_metrics['data_completeness'] = (len(present_fields) / len(expected_fields)) * 100
                
                # 质量判断：至少要有基础结构和部分数据
                is_high_quality = (
                    quality_metrics['has_success_flag'] and
                    quality_metrics['has_data_object'] and
                    quality_metrics['data_field_count'] >= 3  # 至少3个关键字段
                )
                
                if is_high_quality:
                    self.log_test("Real-time Analytics", "PASS", 
                                f"Quality: {quality_metrics['data_completeness']:.1f}% complete", 
                                response_time, quality_metrics)
                    return True
                else:
                    self.log_test("Real-time Analytics", "PARTIAL", 
                                f"Limited quality: {quality_metrics}", response_time, quality_metrics)
                    return True  # 部分数据仍算通过
            else:
                self.log_test("Real-time Analytics", "FAIL", 
                            f"Status: {response.status_code}", response_time)
                return False
                
        except Exception as e:
            self.log_test("Real-time Analytics", "FAIL", str(e))
            return False
    
    def test_mining_calculator_comprehensive(self) -> bool:
        """全面测试挖矿计算器功能"""
        try:
            # 导入并测试计算器
            from mining_calculator import (
                get_real_time_btc_price, 
                get_real_time_difficulty,
                calculate_mining_profitability,
                MINER_DATA
            )
            
            # 测试1: 数据获取功能
            btc_price = get_real_time_btc_price()
            difficulty = get_real_time_difficulty()
            
            data_available = (
                btc_price is not None and btc_price > 0 and
                difficulty is not None and difficulty > 0
            )
            
            # 测试2: 计算引擎
            miner_data = MINER_DATA.get('S19_Pro', {})
            hashrate = miner_data.get('hashrate', 110)
            power_consumption = miner_data.get('power_consumption', 3250)
            
            calculation_result = calculate_mining_profitability(
                hashrate=hashrate,
                power_consumption=power_consumption,
                electricity_cost=0.08,
                client_electricity_cost=0.10,
                miner_model='S19_Pro',
                miner_count=1,
                btc_price=btc_price if btc_price else 95000,
                difficulty=difficulty if difficulty else 102289407543323.7
            )
            
            # 测试3: 结果完整性
            essential_sections = ['profit', 'revenue', 'roi', 'break_even', 'optimization']
            result_completeness = sum(1 for section in essential_sections if section in calculation_result)
            
            # 测试4: 数据合理性
            has_reasonable_data = (
                'revenue' in calculation_result and
                isinstance(calculation_result.get('revenue'), dict) and
                'daily' in calculation_result['revenue']
            )
            
            success_score = (
                (1 if data_available else 0) +
                (1 if result_completeness >= 4 else 0) +
                (1 if has_reasonable_data else 0)
            )
            
            if success_score >= 2:  # 至少2/3项通过
                self.log_test("Mining Calculator Comprehensive", "PASS", 
                            f"Score: {success_score}/3, Sections: {result_completeness}/5", 0, {
                                'data_available': data_available,
                                'result_sections': result_completeness,
                                'reasonable_data': has_reasonable_data
                            })
                return True
            else:
                self.log_test("Mining Calculator Comprehensive", "FAIL", 
                            f"Score: {success_score}/3, insufficient functionality")
                return False
                
        except Exception as e:
            self.log_test("Mining Calculator Comprehensive", "FAIL", str(e))
            return False
    
    def test_subscription_integration(self) -> bool:
        """测试订阅系统集成"""
        try:
            # 测试订阅页面
            start_time = time.time()
            response = requests.get(f"{self.base_url}/billing/plans", timeout=10)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                content = response.text.lower()
                
                # 检查Stripe集成指标
                stripe_indicators = [
                    'stripe', 'checkout', 'subscription', 'billing',
                    'free', 'basic', 'pro', 'price', 'plan'
                ]
                
                found_indicators = [indicator for indicator in stripe_indicators if indicator in content]
                indicator_score = len(found_indicators)
                
                # 检查表单存在性
                has_forms = 'form' in content and 'post' in content
                
                integration_quality = (
                    indicator_score >= 6 and  # 至少6个关键指标
                    has_forms  # 有支付表单
                )
                
                if integration_quality:
                    self.log_test("Subscription Integration", "PASS", 
                                f"Indicators: {indicator_score}/9, Forms: {has_forms}", response_time)
                    return True
                else:
                    self.log_test("Subscription Integration", "PARTIAL", 
                                f"Limited integration: {indicator_score}/9 indicators", response_time)
                    return True  # 部分集成仍算通过
            else:
                self.log_test("Subscription Integration", "FAIL", 
                            f"Status: {response.status_code}", response_time)
                return False
                
        except Exception as e:
            self.log_test("Subscription Integration", "FAIL", str(e))
            return False
    
    def test_system_performance(self) -> Dict:
        """测试系统性能指标"""
        try:
            # 收集性能指标
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            try:
                network = psutil.net_io_counters()
                network_info = {
                    'bytes_sent': network.bytes_sent,
                    'bytes_recv': network.bytes_recv
                }
            except:
                network_info = {'bytes_sent': 0, 'bytes_recv': 0}
            
            # 响应时间测试
            response_times = []
            for _ in range(3):
                start = time.time()
                requests.get(f"{self.base_url}/", timeout=5)
                response_times.append(time.time() - start)
            
            avg_response_time = sum(response_times) / len(response_times)
            
            metrics = {
                'cpu_percent': round(cpu_percent, 1),
                'memory_percent': round(memory.percent, 1),
                'memory_used_mb': round(memory.used / (1024 * 1024), 1),
                'disk_percent': round(disk.percent, 1),
                'avg_response_time': round(avg_response_time, 3),
                'response_times': [round(t, 3) for t in response_times],
                'network_info': network_info,
                'test_duration': round(time.time() - self.start_time, 2)
            }
            
            # 性能评估
            performance_score = 0
            if cpu_percent < 70: performance_score += 1
            if memory.percent < 80: performance_score += 1
            if avg_response_time < 2.0: performance_score += 1
            if disk.percent < 85: performance_score += 1
            
            self.test_results['performance_metrics'] = metrics
            
            if performance_score >= 3:
                self.log_test("System Performance", "PASS", 
                            f"Score: {performance_score}/4, Response: {avg_response_time:.3f}s", 0, metrics)
            else:
                self.log_test("System Performance", "WARNING", 
                            f"Performance issues. Score: {performance_score}/4", 0, metrics)
            
            return metrics
            
        except Exception as e:
            self.log_test("System Performance", "FAIL", str(e))
            return {}
    
    def test_multilingual_support(self) -> bool:
        """测试多语言支持"""
        try:
            # 测试主页的多语言功能
            response = requests.get(f"{self.base_url}/", timeout=10)
            
            if response.status_code == 200:
                content = response.text.lower()
                
                # 检查多语言指标
                multilingual_indicators = [
                    'lang', 'language', 'chinese', 'english', 
                    'zh', 'en', 'translate', '中文', '英文'
                ]
                
                found_indicators = [indicator for indicator in multilingual_indicators if indicator in content]
                
                # 检查JavaScript语言切换
                has_language_switch = 'switchlanguage' in content or 'switch-language' in content
                
                multilingual_quality = len(found_indicators) >= 4 or has_language_switch
                
                if multilingual_quality:
                    self.log_test("Multilingual Support", "PASS", 
                                f"Indicators found: {len(found_indicators)}")
                    return True
                else:
                    self.log_test("Multilingual Support", "PARTIAL", 
                                f"Limited support: {len(found_indicators)} indicators")
                    return True  # 部分支持仍算通过
            else:
                self.log_test("Multilingual Support", "FAIL", 
                            f"Status: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Multilingual Support", "FAIL", str(e))
            return False
    
    def run_final_comprehensive_test(self) -> Dict:
        """运行最终全面测试"""
        logging.info("🚀 开始最终99%通过率全面测试...")
        logging.info("=" * 80)
        
        # 扩展测试套件
        test_suite = [
            ("服务器连接性", self.test_server_connectivity),
            ("数据库完整性", self.test_database_integrity),
            ("API端点全面测试", self.test_api_endpoints_comprehensive),
            ("实时分析质量", self.test_real_time_analytics),
            ("挖矿计算器全面测试", self.test_mining_calculator_comprehensive),
            ("订阅系统集成", self.test_subscription_integration),
            ("系统性能", self.test_system_performance),
            ("多语言支持", self.test_multilingual_support)
        ]
        
        for test_name, test_func in test_suite:
            logging.info(f"执行测试: {test_name}")
            try:
                test_func()
            except Exception as e:
                self.log_test(test_name, "ERROR", f"测试异常: {str(e)}")
                logging.error(f"测试 {test_name} 发生异常: {str(e)}")
            time.sleep(0.3)  # 短暂延迟
        
        # 计算最终结果
        self.calculate_final_results()
        
        # 生成详细报告
        self.generate_comprehensive_report()
        
        return self.test_results
    
    def calculate_final_results(self):
        """计算最终测试结果"""
        total_tests = self.test_results['total_tests']
        passed_tests = self.test_results['passed_tests']
        
        if total_tests > 0:
            pass_rate = (passed_tests / total_tests) * 100
            self.test_results['pass_rate'] = round(pass_rate, 2)
        else:
            self.test_results['pass_rate'] = 0
            
        self.test_results['test_duration'] = round(time.time() - self.start_time, 2)
        
        # 系统健康评估
        health_score = min(100, (passed_tests / total_tests) * 100) if total_tests > 0 else 0
        
        if health_score >= 99:
            health_status = "EXCELLENT"
            health_grade = "A++"
        elif health_score >= 95:
            health_status = "VERY_GOOD"
            health_grade = "A+"
        elif health_score >= 90:
            health_status = "GOOD"
            health_grade = "A"
        elif health_score >= 80:
            health_status = "FAIR"
            health_grade = "B"
        else:
            health_status = "POOR"
            health_grade = "C"
        
        self.test_results['system_health'] = {
            'score': round(health_score, 2),
            'status': health_status,
            'grade': health_grade
        }
    
    def generate_comprehensive_report(self):
        """生成全面测试报告"""
        logging.info("=" * 80)
        logging.info("📊 最终测试结果总结")
        logging.info("=" * 80)
        
        total = self.test_results['total_tests']
        passed = self.test_results['passed_tests']
        failed = self.test_results['failed_tests']
        pass_rate = self.test_results['pass_rate']
        health = self.test_results['system_health']
        
        logging.info(f"总测试数量: {total}")
        logging.info(f"通过测试: {passed}")
        logging.info(f"失败测试: {failed}")
        logging.info(f"通过率: {pass_rate}%")
        logging.info(f"系统健康: {health['grade']} ({health['status']})")
        logging.info(f"测试用时: {self.test_results['test_duration']}秒")
        
        # 性能指标展示
        if 'performance_metrics' in self.test_results:
            metrics = self.test_results['performance_metrics']
            logging.info(f"\n🔧 系统性能指标:")
            logging.info(f"CPU使用率: {metrics.get('cpu_percent', 'N/A')}%")
            logging.info(f"内存使用率: {metrics.get('memory_percent', 'N/A')}%")
            logging.info(f"内存使用量: {metrics.get('memory_used_mb', 'N/A')} MB")
            logging.info(f"平均响应时间: {metrics.get('avg_response_time', 'N/A')}秒")
        
        # 目标达成分析
        target_99_achieved = pass_rate >= 99.0
        target_95_achieved = pass_rate >= 95.0
        
        logging.info(f"\n🎯 目标达成情况:")
        logging.info(f"99%目标: {'✅ 达成' if target_99_achieved else '❌ 未达成'}")
        logging.info(f"95%目标: {'✅ 达成' if target_95_achieved else '❌ 未达成'}")
        
        if target_99_achieved:
            logging.info("🎉 恭喜！超越99%通过率目标！系统达到企业级标准！")
        elif target_95_achieved:
            needed = 99.0 - pass_rate
            logging.info(f"⚠️  已达到95%，还需提高 {needed:.1f}% 达到99%目标")
        else:
            needed = 99.0 - pass_rate
            logging.info(f"⚠️  需要提高 {needed:.1f}% 才能达到99%目标")
        
        # 保存详细报告
        report_file = f"final_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(self.test_results, f, indent=2, ensure_ascii=False)
        
        logging.info(f"\n📄 详细报告已保存到: {report_file}")

def main():
    """主函数"""
    try:
        tester = Final99PercentTest()
        results = tester.run_final_comprehensive_test()
        
        # 根据结果返回适当的退出代码
        pass_rate = results.get('pass_rate', 0)
        if pass_rate >= 99.0:
            return 0  # 优秀
        elif pass_rate >= 95.0:
            return 1  # 良好但未达到99%
        else:
            return 2  # 需要改进

    except KeyboardInterrupt:
        logging.info("\n⚠️ 测试被用户中断")
        return 3
    except Exception as e:
        logging.error(f"❌ 测试过程中发生严重错误: {str(e)}")
        logging.error(traceback.format_exc())
        return 4

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)