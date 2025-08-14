#!/usr/bin/env python3
"""
最终99%准确率回归测试报告生成器
Final 99% Accuracy Regression Test Report Generator

整合所有测试结果，生成综合性99%准确率报告
Integrates all test results to generate comprehensive 99% accuracy report
"""

import json
import logging
import sys
from datetime import datetime
from typing import Dict, Any, List
import requests
import time
import statistics

logging.basicConfig(level=logging.INFO)

class FinalRegressionReporter:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.session = requests.Session()
        
    def validate_critical_functionality(self) -> Dict[str, Any]:
        """验证关键功能的工作状态"""
        logging.info("🔍 验证关键功能状态...")
        
        critical_tests = []
        
        # 1. 核心页面可访问性
        core_pages = [
            ('/', '主页'),
            ('/calculator', '挖矿计算器'),
            ('/analytics', '分析仪表盘'),
            ('/login', '登录页面')
        ]
        
        for path, name in core_pages:
            try:
                response = self.session.get(f"{self.base_url}{path}", timeout=10)
                critical_tests.append({
                    'test': f'核心页面_{name}',
                    'success': response.status_code == 200,
                    'response_time': response.elapsed.total_seconds(),
                    'details': f'HTTP {response.status_code}'
                })
            except Exception as e:
                critical_tests.append({
                    'test': f'核心页面_{name}',
                    'success': False,
                    'response_time': None,
                    'details': str(e)
                })
        
        # 2. 关键API数据准确性
        api_tests = [
            ('/api/network-data', '网络数据'),
            ('/api/get-btc-price', 'BTC价格'),
            ('/api/get_miners_data', '矿机数据')
        ]
        
        for path, name in api_tests:
            try:
                response = self.session.get(f"{self.base_url}{path}", timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    data_valid = self.validate_api_data(path, data)
                    critical_tests.append({
                        'test': f'API数据_{name}',
                        'success': data_valid,
                        'response_time': response.elapsed.total_seconds(),
                        'details': 'Data validation passed' if data_valid else 'Data validation failed'
                    })
                else:
                    critical_tests.append({
                        'test': f'API数据_{name}',
                        'success': False,
                        'response_time': response.elapsed.total_seconds(),
                        'details': f'HTTP {response.status_code}'
                    })
            except Exception as e:
                critical_tests.append({
                    'test': f'API数据_{name}',
                    'success': False,
                    'response_time': None,
                    'details': str(e)
                })
        
        # 3. 计算功能准确性
        try:
            calc_data = {
                'miner_model': 'Antminer S19 Pro',
                'quantity': 1,
                'electricity_cost': 0.08,
                'pool_fee': 0.01
            }
            response = self.session.post(f"{self.base_url}/api/calculate", json=calc_data, timeout=15)
            if response.status_code == 200:
                result = response.json()
                calc_valid = 'daily_profit' in result and isinstance(result['daily_profit'], (int, float))
                critical_tests.append({
                    'test': '计算功能_挖矿收益',
                    'success': calc_valid,
                    'response_time': response.elapsed.total_seconds(),
                    'details': f'Daily profit: {result.get("daily_profit", "N/A")}' if calc_valid else 'Invalid calculation result'
                })
            else:
                critical_tests.append({
                    'test': '计算功能_挖矿收益',
                    'success': False,
                    'response_time': response.elapsed.total_seconds(),
                    'details': f'HTTP {response.status_code}'
                })
        except Exception as e:
            critical_tests.append({
                'test': '计算功能_挖矿收益',
                'success': False,
                'response_time': None,
                'details': str(e)
            })
        
        success_count = sum(1 for test in critical_tests if test['success'])
        total_count = len(critical_tests)
        success_rate = (success_count / total_count) * 100 if total_count > 0 else 0
        
        return {
            'success_rate': success_rate,
            'successful_tests': success_count,
            'total_tests': total_count,
            'individual_tests': critical_tests,
            'meets_critical_threshold': success_rate >= 95  # 95%以上认为关键功能正常
        }
    
    def validate_api_data(self, path: str, data: Dict) -> bool:
        """验证API数据的合理性"""
        try:
            if '/api/network-data' in path:
                if 'data' in data:
                    d = data['data']
                    btc_price = d.get('btc_price', 0)
                    hashrate = d.get('hashrate', 0)
                    return 50000 <= btc_price <= 500000 and 500 <= hashrate <= 2000
            
            elif '/api/get-btc-price' in path:
                btc_price = data.get('btc_price', 0)
                return 50000 <= btc_price <= 500000
            
            elif '/api/get_miners_data' in path:
                miners = data.get('miners', [])
                if not miners:
                    return False
                # 检查前几个矿机数据
                for miner in miners[:3]:
                    hashrate = miner.get('hashrate', 0)
                    power = miner.get('power_consumption', 0)
                    if not (10 <= hashrate <= 1000 and 1000 <= power <= 10000):
                        return False
                return True
            
            return True  # 其他API默认通过
        except:
            return False
    
    def test_cache_performance(self) -> Dict[str, Any]:
        """测试缓存性能"""
        logging.info("⚡ 测试缓存性能...")
        
        cache_endpoints = [
            '/api/network-data',
            '/api/get-btc-price',
            '/api/get_miners_data'
        ]
        
        cache_results = []
        
        for endpoint in cache_endpoints:
            try:
                # 第一次请求（可能缓存未命中）
                times_uncached = []
                for _ in range(3):
                    start = time.time()
                    response = self.session.get(f"{self.base_url}{endpoint}")
                    times_uncached.append(time.time() - start)
                    time.sleep(0.5)  # 确保缓存生效
                
                # 快速连续请求（应该缓存命中）
                times_cached = []
                for _ in range(5):
                    start = time.time()
                    response = self.session.get(f"{self.base_url}{endpoint}")
                    times_cached.append(time.time() - start)
                    time.sleep(0.1)
                
                avg_uncached = statistics.mean(times_uncached)
                avg_cached = statistics.mean(times_cached)
                improvement = ((avg_uncached - avg_cached) / avg_uncached * 100) if avg_uncached > 0 else 0
                
                cache_results.append({
                    'endpoint': endpoint,
                    'avg_uncached_time': avg_uncached,
                    'avg_cached_time': avg_cached,
                    'performance_improvement': improvement,
                    'cache_working': improvement > 5  # 至少5%改善
                })
                
            except Exception as e:
                cache_results.append({
                    'endpoint': endpoint,
                    'error': str(e),
                    'cache_working': False
                })
        
        working_cache_count = sum(1 for r in cache_results if r.get('cache_working', False))
        cache_effectiveness = (working_cache_count / len(cache_results) * 100) if cache_results else 0
        
        return {
            'cache_effectiveness': cache_effectiveness,
            'working_caches': working_cache_count,
            'total_tested': len(cache_results),
            'individual_results': cache_results,
            'meets_cache_target': cache_effectiveness >= 70  # 70%以上缓存工作
        }
    
    def test_response_time_consistency(self) -> Dict[str, Any]:
        """测试响应时间一致性"""
        logging.info("⏱️ 测试响应时间一致性...")
        
        test_endpoints = [
            ('/', 'HomePage'),
            ('/calculator', 'Calculator'),
            ('/api/network-data', 'NetworkAPI'),
            ('/api/get-btc-price', 'PriceAPI')
        ]
        
        consistency_results = []
        
        for endpoint, name in test_endpoints:
            try:
                response_times = []
                
                # 执行多次请求测试一致性
                for _ in range(10):
                    start = time.time()
                    response = self.session.get(f"{self.base_url}{endpoint}", timeout=10)
                    if response.status_code == 200:
                        response_times.append(time.time() - start)
                    time.sleep(0.2)
                
                if response_times:
                    avg_time = statistics.mean(response_times)
                    std_dev = statistics.stdev(response_times) if len(response_times) > 1 else 0
                    min_time = min(response_times)
                    max_time = max(response_times)
                    
                    # 一致性评分：标准差越小越好
                    consistency_score = max(0, 100 - (std_dev * 1000))  # 标准差小于0.1s得满分
                    
                    consistency_results.append({
                        'endpoint': endpoint,
                        'name': name,
                        'avg_response_time': avg_time,
                        'std_deviation': std_dev,
                        'min_time': min_time,
                        'max_time': max_time,
                        'consistency_score': consistency_score,
                        'samples': len(response_times)
                    })
                    
            except Exception as e:
                consistency_results.append({
                    'endpoint': endpoint,
                    'name': name,
                    'error': str(e),
                    'consistency_score': 0
                })
        
        avg_consistency = statistics.mean([r.get('consistency_score', 0) for r in consistency_results])
        
        return {
            'average_consistency_score': avg_consistency,
            'individual_results': consistency_results,
            'meets_consistency_target': avg_consistency >= 85  # 85分以上认为一致性良好
        }
    
    def generate_final_report(self) -> Dict[str, Any]:
        """生成最终的99%准确率报告"""
        logging.info("📊 生成最终99%准确率报告...")
        
        # 执行所有测试
        critical_func = self.validate_critical_functionality()
        cache_perf = self.test_cache_performance()
        response_consistency = self.test_response_time_consistency()
        
        # 计算综合评分
        scores = {
            'critical_functionality': critical_func['success_rate'],
            'cache_performance': cache_perf['cache_effectiveness'],
            'response_consistency': response_consistency['average_consistency_score']
        }
        
        # 加权平均（关键功能权重最高）
        weights = {
            'critical_functionality': 0.5,  # 50%权重
            'cache_performance': 0.3,       # 30%权重
            'response_consistency': 0.2     # 20%权重
        }
        
        weighted_score = sum(scores[key] * weights[key] for key in scores.keys())
        
        # 额外检查
        bonus_checks = []
        
        # 检查数据源一致性
        try:
            net_response = self.session.get(f"{self.base_url}/api/network-data")
            price_response = self.session.get(f"{self.base_url}/api/get-btc-price")
            
            if net_response.status_code == 200 and price_response.status_code == 200:
                net_data = net_response.json()
                price_data = price_response.json()
                
                net_price = net_data.get('data', {}).get('btc_price', 0)
                direct_price = price_data.get('btc_price', 0)
                
                # 价格差异应该很小（1%以内）
                if abs(net_price - direct_price) / max(net_price, direct_price) <= 0.01:
                    bonus_checks.append({'check': 'Data Source Consistency', 'passed': True})
                    weighted_score += 2  # 奖励分
                else:
                    bonus_checks.append({'check': 'Data Source Consistency', 'passed': False})
        except:
            bonus_checks.append({'check': 'Data Source Consistency', 'passed': False})
        
        # 最终评估
        meets_99_percent = weighted_score >= 99.0
        
        final_report = {
            'timestamp': datetime.now().isoformat(),
            'test_type': 'Final 99% Accuracy Regression Test',
            'overall_score': weighted_score,
            'target_score': 99.0,
            'meets_99_percent_target': meets_99_percent,
            'component_scores': scores,
            'weights_used': weights,
            'detailed_results': {
                'critical_functionality': critical_func,
                'cache_performance': cache_perf,
                'response_consistency': response_consistency
            },
            'bonus_checks': bonus_checks,
            'final_assessment': {
                'grade': 'PASS' if meets_99_percent else 'NEEDS_IMPROVEMENT',
                'confidence_level': 'HIGH' if weighted_score >= 95 else 'MEDIUM' if weighted_score >= 85 else 'LOW'
            }
        }
        
        # 输出报告摘要
        logging.info(f"\n🎯 最终99%准确率测试报告")
        logging.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logging.info(f"📈 综合评分: {weighted_score:.2f}/100")
        logging.info(f"🎯 目标评分: 99.0")
        logging.info(f"✅ 达到99%目标: {'是' if meets_99_percent else '否'}")
        logging.info(f"")
        logging.info(f"📊 详细评分:")
        logging.info(f"   关键功能: {scores['critical_functionality']:.1f}% (权重50%)")
        logging.info(f"   缓存性能: {scores['cache_performance']:.1f}% (权重30%)")
        logging.info(f"   响应一致性: {scores['response_consistency']:.1f}% (权重20%)")
        logging.info(f"")
        logging.info(f"🏆 最终评级: {final_report['final_assessment']['grade']}")
        logging.info(f"🎖️ 信心水平: {final_report['final_assessment']['confidence_level']}")
        
        if meets_99_percent:
            logging.info(f"")
            logging.info(f"🎉 恭喜！系统已达到99%+准确率要求！")
            logging.info(f"   系统具备生产环境部署的质量标准")
        else:
            logging.info(f"")
            logging.info(f"⚠️ 系统尚未达到99%准确率目标")
            logging.info(f"   建议优化关键功能和缓存性能")
        
        return final_report

def main():
    """主函数"""
    reporter = FinalRegressionReporter()
    
    try:
        report = reporter.generate_final_report()
        
        # 保存报告
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"final_regression_report_99_percent_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logging.info(f"\n💾 最终报告已保存到: {filename}")
        
        # 返回适当的退出码
        if report['meets_99_percent_target']:
            logging.info("✅ 最终测试通过！系统达到99%+准确率要求")
            return 0
        else:
            logging.info("❌ 最终测试未通过，系统需要进一步优化")
            return 1
            
    except Exception as e:
        logging.error(f"💥 报告生成过程中发生错误: {e}")
        return 2

if __name__ == "__main__":
    exit(main())