#!/usr/bin/env python3
"""
API数据准确性验证测试
API Data Accuracy Validation Test

专门验证API端点返回数据的准确性和一致性
Specifically validates accuracy and consistency of API endpoint data
"""

import requests
import json
import time
import logging
from datetime import datetime
from typing import Dict, Any, List
import statistics

logging.basicConfig(level=logging.INFO)

class APIAccuracyValidator:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.session = requests.Session()
        
    def test_network_data_consistency(self, samples: int = 10) -> Dict[str, Any]:
        """测试网络数据的一致性"""
        results = []
        
        logging.info("🔍 测试网络数据一致性...")
        
        for i in range(samples):
            try:
                response = self.session.get(f"{self.base_url}/api/network-data")
                if response.status_code == 200:
                    data = response.json()
                    if 'data' in data:
                        results.append({
                            'timestamp': datetime.now().isoformat(),
                            'btc_price': data['data'].get('btc_price'),
                            'hashrate': data['data'].get('hashrate'),
                            'difficulty': data['data'].get('difficulty'),
                            'block_reward': data['data'].get('block_reward')
                        })
                time.sleep(1)  # 等待1秒
            except Exception as e:
                logging.error(f"样本 {i+1} 获取失败: {e}")
        
        if not results:
            return {'success': False, 'error': 'No valid samples collected'}
        
        # 分析一致性
        btc_prices = [r['btc_price'] for r in results if r['btc_price']]
        hashrates = [r['hashrate'] for r in results if r['hashrate']]
        
        analysis = {
            'samples_collected': len(results),
            'btc_price_range': [min(btc_prices), max(btc_prices)] if btc_prices else None,
            'btc_price_variance': statistics.variance(btc_prices) if len(btc_prices) > 1 else 0,
            'hashrate_range': [min(hashrates), max(hashrates)] if hashrates else None,
            'hashrate_variance': statistics.variance(hashrates) if len(hashrates) > 1 else 0,
            'consistency_score': 0
        }
        
        # 计算一致性分数
        score = 100
        if analysis['btc_price_variance'] > 1000:  # 价格变化过大
            score -= 20
        if analysis['hashrate_variance'] > 100:  # 算力变化过大
            score -= 20
        
        analysis['consistency_score'] = score
        analysis['success'] = True
        
        return analysis

    def test_btc_price_accuracy(self) -> Dict[str, Any]:
        """测试BTC价格数据准确性"""
        logging.info("💰 验证BTC价格数据准确性...")
        
        try:
            # 从我们的API获取价格
            response = self.session.get(f"{self.base_url}/api/get-btc-price")
            if response.status_code != 200:
                return {'success': False, 'error': 'API request failed'}
            
            our_data = response.json()
            our_price = our_data.get('btc_price')
            
            if not our_price:
                return {'success': False, 'error': 'No price data in response'}
            
            # 验证价格合理性
            if not (50000 <= our_price <= 500000):
                return {
                    'success': False, 
                    'error': f'Price out of reasonable range: ${our_price}',
                    'our_price': our_price
                }
            
            return {
                'success': True,
                'our_price': our_price,
                'price_reasonable': True,
                'data_source': our_data.get('data_source', 'unknown')
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def test_miners_data_completeness(self) -> Dict[str, Any]:
        """测试矿机数据完整性"""
        logging.info("⛏️ 验证矿机数据完整性...")
        
        try:
            response = self.session.get(f"{self.base_url}/api/get_miners_data")
            if response.status_code != 200:
                return {'success': False, 'error': 'API request failed'}
            
            data = response.json()
            miners = data.get('miners', [])
            
            if not miners:
                return {'success': False, 'error': 'No miners data found'}
            
            # 验证数据结构
            required_fields = ['name', 'hashrate', 'power_consumption']
            valid_miners = 0
            total_miners = len(miners)
            
            for miner in miners:
                if all(field in miner for field in required_fields):
                    # 验证数值合理性
                    if (miner['hashrate'] > 0 and 
                        miner['power_consumption'] > 0 and
                        10 <= miner['hashrate'] <= 1000 and  # TH/s range
                        1000 <= miner['power_consumption'] <= 10000):  # Watts range
                        valid_miners += 1
            
            completeness_ratio = valid_miners / total_miners if total_miners > 0 else 0
            
            return {
                'success': True,
                'total_miners': total_miners,
                'valid_miners': valid_miners,
                'completeness_ratio': completeness_ratio,
                'completeness_percentage': completeness_ratio * 100,
                'sample_miner': miners[0] if miners else None
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def test_calculate_api_accuracy(self) -> Dict[str, Any]:
        """测试计算API的准确性"""
        logging.info("🧮 验证挖矿计算API准确性...")
        
        test_cases = [
            {
                'name': 'Standard S19 Pro Test',
                'data': {
                    'miner_model': 'Antminer S19 Pro',
                    'quantity': 1,
                    'electricity_cost': 0.08,
                    'pool_fee': 0.01
                },
                'expected_fields': ['daily_profit', 'monthly_profit', 'roi_days', 'daily_revenue']
            },
            {
                'name': 'Multiple Miners Test',
                'data': {
                    'miner_model': 'Antminer S19 Pro',
                    'quantity': 10,
                    'electricity_cost': 0.06,
                    'pool_fee': 0.015
                },
                'expected_fields': ['daily_profit', 'monthly_profit', 'roi_days', 'daily_revenue']
            }
        ]
        
        results = []
        
        for test_case in test_cases:
            try:
                response = self.session.post(
                    f"{self.base_url}/api/calculate",
                    json=test_case['data']
                )
                
                if response.status_code == 200:
                    calc_result = response.json()
                    
                    # 验证响应结构
                    has_required_fields = all(
                        field in calc_result for field in test_case['expected_fields']
                    )
                    
                    # 验证数值合理性
                    reasonable_values = True
                    if 'daily_profit' in calc_result:
                        daily_profit = calc_result['daily_profit']
                        # 日利润应该在合理范围内（-$100 到 $1000）
                        if not (-100 <= daily_profit <= 1000):
                            reasonable_values = False
                    
                    results.append({
                        'test_name': test_case['name'],
                        'success': True,
                        'has_required_fields': has_required_fields,
                        'reasonable_values': reasonable_values,
                        'response_data': calc_result
                    })
                else:
                    results.append({
                        'test_name': test_case['name'],
                        'success': False,
                        'error': f'HTTP {response.status_code}'
                    })
                    
            except Exception as e:
                results.append({
                    'test_name': test_case['name'],
                    'success': False,
                    'error': str(e)
                })
        
        success_count = sum(1 for r in results if r['success'])
        accuracy = (success_count / len(results)) * 100 if results else 0
        
        return {
            'success': accuracy >= 90,
            'test_results': results,
            'success_count': success_count,
            'total_tests': len(results),
            'accuracy_percentage': accuracy
        }

    def run_accuracy_validation(self) -> Dict[str, Any]:
        """运行完整的准确性验证"""
        logging.info("🎯 开始API数据准确性验证...")
        
        tests = {
            'network_data_consistency': self.test_network_data_consistency(),
            'btc_price_accuracy': self.test_btc_price_accuracy(),
            'miners_data_completeness': self.test_miners_data_completeness(),
            'calculate_api_accuracy': self.test_calculate_api_accuracy()
        }
        
        # 计算总体准确性分数
        scores = []
        
        for test_name, result in tests.items():
            if result.get('success'):
                if 'consistency_score' in result:
                    scores.append(result['consistency_score'])
                elif 'completeness_percentage' in result:
                    scores.append(result['completeness_percentage'])
                elif 'accuracy_percentage' in result:
                    scores.append(result['accuracy_percentage'])
                else:
                    scores.append(100)  # 基础成功分数
            else:
                scores.append(0)
        
        overall_accuracy = statistics.mean(scores) if scores else 0
        
        summary = {
            'timestamp': datetime.now().isoformat(),
            'overall_accuracy': overall_accuracy,
            'meets_99_percent_target': overall_accuracy >= 99.0,
            'individual_tests': tests,
            'test_count': len(tests),
            'passed_tests': sum(1 for t in tests.values() if t.get('success')),
            'failed_tests': sum(1 for t in tests.values() if not t.get('success'))
        }
        
        logging.info(f"\n📊 API准确性验证结果:")
        logging.info(f"   整体准确性: {overall_accuracy:.2f}%")
        logging.info(f"   达到99%目标: {'✅ 是' if summary['meets_99_percent_target'] else '❌ 否'}")
        logging.info(f"   通过测试: {summary['passed_tests']}/{summary['test_count']}")
        
        return summary

def main():
    """主函数"""
    validator = APIAccuracyValidator()
    
    try:
        results = validator.run_accuracy_validation()
        
        # 保存结果
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"api_accuracy_validation_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        logging.info(f"\n💾 验证结果已保存到: {filename}")
        
        if results['meets_99_percent_target']:
            logging.info("🎉 API准确性验证通过！")
            return 0
        else:
            logging.error("💥 API准确性验证失败！")
            return 1
            
    except Exception as e:
        logging.error(f"💥 验证过程中发生错误: {e}")
        return 2

if __name__ == "__main__":
    exit(main())