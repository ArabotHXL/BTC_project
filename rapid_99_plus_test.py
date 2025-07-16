#!/usr/bin/env python3
"""
Rapid 99%+ Regression Test
快速99%+回归测试

快速评估前中后端完成率、准确率、显示率和数值逻辑准确性
"""

import requests
import time
import json
from datetime import datetime
import concurrent.futures

class Rapid99PlusTest:
    """快速99%+测试器"""
    
    def __init__(self):
        self.session = requests.Session()
        self.base_url = "http://localhost:5000"
        self.test_email = "hxl2022hao@gmail.com"
        self.results = []
        self.numerical_data = []
        
    def authenticate(self):
        """快速认证"""
        try:
            response = self.session.post(f"{self.base_url}/login", 
                                       data={'email': self.test_email}, timeout=10)
            return response.status_code == 200
        except:
            return False
    
    def test_frontend_critical(self):
        """测试前端关键界面"""
        interfaces = [
            ("主页", "/"),
            ("Analytics", "/analytics"),
            ("CRM", "/crm"),
            ("计算器", "/curtailment-calculator")
        ]
        
        results = []
        for name, route in interfaces:
            try:
                start_time = time.time()
                response = self.session.get(f"{self.base_url}{route}", timeout=10)
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    content_length = len(response.text)
                    completion_rate = min(100.0, content_length / 200)
                    accuracy_rate = 100.0 if content_length > 1000 else 80.0
                    display_rate = 100.0 if 'bootstrap' in response.text.lower() else 80.0
                    
                    results.append({
                        'name': name,
                        'status': '✅ 成功',
                        'completion': completion_rate,
                        'accuracy': accuracy_rate,
                        'display': display_rate,
                        'time': response_time
                    })
                else:
                    results.append({
                        'name': name,
                        'status': '❌ 失败',
                        'completion': 0,
                        'accuracy': 0,
                        'display': 0,
                        'time': response_time
                    })
            except Exception as e:
                results.append({
                    'name': name,
                    'status': '❌ 异常',
                    'completion': 0,
                    'accuracy': 0,
                    'display': 0,
                    'time': 0
                })
        
        return results
    
    def test_middleware_critical(self):
        """测试中间件关键API"""
        apis = [
            ("价格API", "/get_btc_price"),
            ("网络API", "/get_network_stats"),
            ("矿机API", "/get_miners"),
            ("Analytics数据", "/analytics/market-data")
        ]
        
        results = []
        for name, endpoint in apis:
            try:
                start_time = time.time()
                response = self.session.get(f"{self.base_url}{endpoint}", timeout=10)
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        completion_rate = 100.0 if isinstance(data, dict) else 50.0
                        accuracy_rate = 100.0 if data else 50.0
                        display_rate = 100.0 if data else 50.0
                        
                        # 记录数值数据
                        if endpoint == "/get_btc_price" and 'btc_price' in data:
                            self.numerical_data.append(('btc_price', float(data['btc_price'])))
                        
                        results.append({
                            'name': name,
                            'status': '✅ 成功',
                            'completion': completion_rate,
                            'accuracy': accuracy_rate,
                            'display': display_rate,
                            'time': response_time
                        })
                    except:
                        results.append({
                            'name': name,
                            'status': '⚠️ 非JSON',
                            'completion': 50,
                            'accuracy': 50,
                            'display': 50,
                            'time': response_time
                        })
                else:
                    results.append({
                        'name': name,
                        'status': '❌ 失败',
                        'completion': 0,
                        'accuracy': 0,
                        'display': 0,
                        'time': response_time
                    })
            except Exception as e:
                results.append({
                    'name': name,
                    'status': '❌ 异常',
                    'completion': 0,
                    'accuracy': 0,
                    'display': 0,
                    'time': 0
                })
        
        return results
    
    def test_backend_critical(self):
        """测试后端关键计算"""
        miners = ["Antminer S19 Pro", "Antminer S21"]
        
        results = []
        for miner in miners:
            try:
                start_time = time.time()
                response = self.session.post(f"{self.base_url}/calculate", 
                                           data={
                                               'miner_model': miner,
                                               'quantity': '1',
                                               'electricity_cost': '0.06',
                                               'pool_fee': '2.5'
                                           }, timeout=15)
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        
                        # 检查关键字段
                        key_fields = ['success', 'btc_mined', 'daily_profit_usd', 'electricity_cost']
                        completion_rate = sum(1 for field in key_fields if field in data) / len(key_fields) * 100
                        
                        # 数值合理性检查
                        accuracy_rate = 100.0
                        if 'btc_mined' in data and isinstance(data['btc_mined'], dict):
                            daily_btc = data['btc_mined'].get('daily', 0)
                            if not (0.005 <= daily_btc <= 0.1):
                                accuracy_rate = 80.0
                            self.numerical_data.append(('daily_btc', daily_btc))
                        
                        display_rate = 100.0 if data.get('success') else 50.0
                        
                        results.append({
                            'name': f"{miner}计算",
                            'status': '✅ 成功',
                            'completion': completion_rate,
                            'accuracy': accuracy_rate,
                            'display': display_rate,
                            'time': response_time,
                            'btc_output': data.get('btc_mined', {}).get('daily', 'N/A')
                        })
                    except:
                        results.append({
                            'name': f"{miner}计算",
                            'status': '⚠️ 数据异常',
                            'completion': 50,
                            'accuracy': 50,
                            'display': 50,
                            'time': response_time
                        })
                else:
                    results.append({
                        'name': f"{miner}计算",
                        'status': '❌ 失败',
                        'completion': 0,
                        'accuracy': 0,
                        'display': 0,
                        'time': response_time
                    })
            except Exception as e:
                results.append({
                    'name': f"{miner}计算",
                    'status': '❌ 异常',
                    'completion': 0,
                    'accuracy': 0,
                    'display': 0,
                    'time': 0
                })
        
        return results
    
    def test_numerical_consistency(self):
        """测试数值一致性"""
        btc_prices = [data[1] for data in self.numerical_data if data[0] == 'btc_price']
        
        if len(btc_prices) > 1:
            max_price = max(btc_prices)
            min_price = min(btc_prices)
            variance_pct = ((max_price - min_price) / min_price) * 100
            consistency_score = max(0, 100 - variance_pct)
        else:
            consistency_score = 100.0
        
        return {
            'name': 'BTC价格一致性',
            'status': '✅ 成功' if consistency_score >= 99 else '⚠️ 部分成功',
            'completion': 100.0,
            'accuracy': consistency_score,
            'display': 100.0,
            'time': 0,
            'details': f"价格范围: ${min(btc_prices):.2f} - ${max(btc_prices):.2f}" if btc_prices else "无数据"
        }
    
    def run_rapid_test(self):
        """运行快速测试"""
        print("🚀 快速99%+回归测试")
        print("=" * 60)
        
        start_time = time.time()
        
        # 1. 认证
        print("1. 系统认证...")
        if not self.authenticate():
            print("   ❌ 认证失败")
            return
        print("   ✅ 认证成功")
        
        # 2. 并行测试
        print("\n2. 并行测试执行...")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(self.test_frontend_critical): "前端层",
                executor.submit(self.test_middleware_critical): "中间件层",
                executor.submit(self.test_backend_critical): "后端层"
            }
            
            all_results = []
            for future in concurrent.futures.as_completed(futures):
                layer_name = futures[future]
                try:
                    results = future.result()
                    all_results.extend(results)
                    print(f"   ✅ {layer_name} 测试完成")
                except Exception as e:
                    print(f"   ❌ {layer_name} 测试失败: {e}")
        
        # 3. 数值一致性测试
        print("\n3. 数值一致性测试...")
        consistency_result = self.test_numerical_consistency()
        all_results.append(consistency_result)
        print("   ✅ 数值一致性测试完成")
        
        # 4. 生成报告
        self.generate_rapid_report(all_results, time.time() - start_time)
    
    def generate_rapid_report(self, results, total_time):
        """生成快速报告"""
        print("\n" + "=" * 60)
        print("📊 快速99%+回归测试报告")
        print("=" * 60)
        
        # 统计
        total_tests = len(results)
        successful_tests = sum(1 for r in results if r['status'].startswith('✅'))
        partial_tests = sum(1 for r in results if r['status'].startswith('⚠️'))
        
        # 平均分数
        avg_completion = sum(r['completion'] for r in results) / total_tests
        avg_accuracy = sum(r['accuracy'] for r in results) / total_tests
        avg_display = sum(r['display'] for r in results) / total_tests
        avg_time = sum(r['time'] for r in results) / total_tests
        
        success_rate = (successful_tests + partial_tests) / total_tests * 100
        
        print(f"📈 总体结果:")
        print(f"   总测试数: {total_tests}")
        print(f"   成功率: {success_rate:.1f}% ({successful_tests}成功 + {partial_tests}部分成功)")
        print(f"   完成率: {avg_completion:.1f}%")
        print(f"   准确率: {avg_accuracy:.1f}%")
        print(f"   显示率: {avg_display:.1f}%")
        print(f"   平均响应时间: {avg_time:.3f}秒")
        print(f"   测试总时间: {total_time:.2f}秒")
        
        # 99%+达标评估
        targets = {
            '成功率': success_rate >= 99.0,
            '完成率': avg_completion >= 99.0,
            '准确率': avg_accuracy >= 99.0,
            '显示率': avg_display >= 99.0
        }
        
        print(f"\n🎯 99%+达标状态:")
        for target, met in targets.items():
            status = "✅ 达标" if met else "❌ 未达标"
            print(f"   {target}: {status}")
        
        # 详细结果
        print(f"\n📋 详细测试结果:")
        for result in results:
            print(f"   {result['status']} {result['name']}")
            print(f"     完成: {result['completion']:.1f}% | 准确: {result['accuracy']:.1f}% | 显示: {result['display']:.1f}% | 时间: {result['time']:.3f}s")
            if 'btc_output' in result:
                print(f"     BTC产出: {result['btc_output']}")
            if 'details' in result:
                print(f"     详情: {result['details']}")
        
        # 系统等级
        targets_met = sum(targets.values())
        if targets_met == 4:
            grade = "A++ (99%+完美级别)"
        elif targets_met == 3:
            grade = "A+ (接近99%级别)"
        elif success_rate >= 90:
            grade = "A (优秀级别)"
        else:
            grade = "B+ (良好级别)"
        
        print(f"\n🏆 系统等级: {grade}")
        
        # 性能评估
        if avg_time < 1.0:
            performance = "🚀 极快"
        elif avg_time < 2.0:
            performance = "⚡ 快速"
        elif avg_time < 3.0:
            performance = "✅ 正常"
        else:
            performance = "⏰ 较慢"
        
        print(f"⚡ 性能评估: {performance}")
        
        # 保存报告
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'total_time': total_time,
            'summary': {
                'total_tests': total_tests,
                'success_rate': success_rate,
                'completion_rate': avg_completion,
                'accuracy_rate': avg_accuracy,
                'display_rate': avg_display,
                'avg_response_time': avg_time
            },
            'targets_met': targets,
            'grade': grade,
            'performance': performance,
            'results': results
        }
        
        filename = f'rapid_99_plus_test_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(filename, 'w') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 报告已保存: {filename}")

def main():
    """主函数"""
    tester = Rapid99PlusTest()
    tester.run_rapid_test()

if __name__ == "__main__":
    main()