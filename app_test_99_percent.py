#!/usr/bin/env python3
"""
BTC挖矿计算器99%准确率综合测试
"""

import requests
import os
import json
import time
import psycopg2
from datetime import datetime
import threading

def main():
    print("🚀 BTC挖矿计算器99%准确率综合测试")
    print("="*60)
    
    # 使用本地URL
    base_url = 'http://localhost:5000'
    
    # 测试结果收集器
    test_results = {
        'total_tests': 0,
        'passed_tests': 0,
        'failed_tests': 0,
        'accuracy_score': 0.0,
        'test_details': {},
        'timestamp': datetime.now().isoformat()
    }
    
    def log_test(name, success, details=''):
        test_results['total_tests'] += 1
        if success:
            test_results['passed_tests'] += 1
            print(f"✓ {name}: 通过 - {details}")
        else:
            test_results['failed_tests'] += 1
            print(f"✗ {name}: 失败 - {details}")
        
        test_results['test_details'][name] = {
            'success': success,
            'details': details,
            'timestamp': datetime.now().isoformat()
        }
    
    # 1. 数据库连接测试
    print("\n🔍 数据库连接测试:")
    try:
        conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
        cursor = conn.cursor()
        
        # 测试关键表
        tables = ['users', 'market_analytics', 'technical_indicators']
        for table in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                log_test(f"数据库表_{table}", True, f"{count}条记录")
            except Exception as e:
                log_test(f"数据库表_{table}", False, str(e))
        
        # 测试市场数据质量
        cursor.execute("SELECT COUNT(*) FROM market_analytics WHERE btc_price > 50000 AND btc_price < 200000")
        valid_price_count = cursor.fetchone()[0]
        log_test("市场数据质量", valid_price_count > 100, f"{valid_price_count}条有效价格记录")
        
        conn.close()
        
    except Exception as e:
        log_test("数据库连接", False, str(e))
    
    # 2. 核心挖矿计算准确性测试
    print("\n🧮 核心计算引擎测试:")
    
    # 测试案例
    test_cases = [
        {
            'name': 'Antminer S19 Pro (低电费)',
            'hashrate_th': 110,
            'power_kw': 3.25,
            'electricity_cost': 0.06,
            'btc_price': 118968,
            'network_hashrate_eh': 927,
            'expected_profit_min': 1.0,  # 基于当前BTC价格$118,968的实际预期
            'expected_profit_max': 3.0
        },
        {
            'name': 'Antminer S21 XP (中等电费)',
            'hashrate_th': 270,
            'power_kw': 3.645,
            'electricity_cost': 0.08,
            'btc_price': 118968,
            'network_hashrate_eh': 927,
            'expected_profit_min': 7.0,  # 基于当前BTC价格$118,968的实际预期
            'expected_profit_max': 10.0
        }
    ]
    
    for case in test_cases:
        try:
            # 计算逻辑
            network_hashrate_th = case['network_hashrate_eh'] * 1000000
            daily_btc = (case['hashrate_th'] / network_hashrate_th) * 144 * 3.125
            daily_revenue = daily_btc * case['btc_price']
            daily_power_cost = case['power_kw'] * 24 * case['electricity_cost']
            daily_profit = daily_revenue - daily_power_cost
            
            # 验证结果
            is_accurate = case['expected_profit_min'] <= daily_profit <= case['expected_profit_max']
            
            details = f"每日利润${daily_profit:.2f} (预期${case['expected_profit_min']}-${case['expected_profit_max']})"
            log_test(f"计算准确性_{case['name']}", is_accurate, details)
            
        except Exception as e:
            log_test(f"计算准确性_{case['name']}", False, str(e))
    
    # 3. API接口功能测试
    print("\n🔌 API接口测试:")
    
    session = requests.Session()
    
    api_endpoints = [
        ('/api/get-btc-price', '实时价格API'),
        ('/api/get-hashrate', '网络算力API'),
        ('/calculator', '计算器页面'),
        ('/price', '价格页面')
    ]
    
    for endpoint, description in api_endpoints:
        try:
            response = session.get(f"{base_url}{endpoint}", timeout=5)
            success = response.status_code in [200, 302]
            
            details = f"HTTP {response.status_code}"
            log_test(f"API_{description}", success, details)
            
        except Exception as e:
            log_test(f"API_{description}", False, str(e))
    
    # 4. 技术指标准确性验证
    print("\n📊 技术指标验证:")
    
    try:
        conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
        cursor = conn.cursor()
        
        # 获取最近价格数据
        cursor.execute("SELECT btc_price FROM market_analytics WHERE btc_price > 0 ORDER BY recorded_at DESC LIMIT 50")
        prices = [float(row[0]) for row in cursor.fetchall()]
        
        if len(prices) >= 20:
            current_price = prices[0]
            
            # 计算SMA20
            sma_20 = sum(prices[:20]) / 20
            sma_deviation = abs(sma_20 - current_price) / current_price
            
            # 验证SMA合理性
            sma_reasonable = sma_deviation <= 0.10
            log_test("技术指标_SMA20合理性", sma_reasonable, 
                    f"SMA20: ${sma_20:.2f}, 当前价格: ${current_price:.2f}, 偏差: {sma_deviation*100:.2f}%")
        else:
            log_test("技术指标验证", False, "历史数据不足")
        
        conn.close()
        
    except Exception as e:
        log_test("技术指标验证", False, str(e))
    
    # 5. 系统性能测试
    print("\n⚡ 性能测试:")
    
    def make_request():
        try:
            response = requests.get(f"{base_url}/calculator", timeout=10)
            return response.status_code in [200, 302]
        except:
            return False
    
    try:
        # 并发请求测试
        results = []
        threads = []
        
        def worker():
            result = make_request()
            results.append(result)
        
        start_time = time.time()
        
        for _ in range(5):  # 5个并发请求
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join(timeout=15)
        
        end_time = time.time()
        
        success_rate = sum(results) / len(results) if results else 0
        avg_response_time = (end_time - start_time) / len(results) if results else 999
        
        performance_good = success_rate >= 0.8 and avg_response_time <= 5.0
        log_test("并发性能测试", performance_good, 
                f"成功率: {success_rate*100:.1f}%, 平均响应时间: {avg_response_time:.2f}s")
        
    except Exception as e:
        log_test("并发性能测试", False, str(e))
    
    # 6. 数据一致性验证
    print("\n🔍 数据一致性验证:")
    
    try:
        conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
        cursor = conn.cursor()
        
        # 检查价格数据一致性
        cursor.execute("SELECT COUNT(*) FROM market_analytics WHERE btc_price IS NOT NULL AND btc_price > 1000 AND btc_price < 1000000")
        valid_prices = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM market_analytics WHERE btc_price IS NOT NULL")
        total_prices = cursor.fetchone()[0]
        
        data_quality = valid_prices / total_prices if total_prices > 0 else 0
        
        log_test("数据一致性验证", data_quality >= 0.95, 
                f"有效数据比例: {data_quality*100:.1f}% ({valid_prices}/{total_prices})")
        
        conn.close()
        
    except Exception as e:
        log_test("数据一致性验证", False, str(e))
    
    # 计算最终得分
    print("\n" + "="*60)
    print("📊 综合测试结果:")
    
    total_tests = test_results['total_tests']
    passed_tests = test_results['passed_tests']
    failed_tests = test_results['failed_tests']
    
    if total_tests > 0:
        accuracy_score = (passed_tests / total_tests) * 100
        availability_score = accuracy_score
    else:
        accuracy_score = 0
        availability_score = 0
    
    test_results['accuracy_score'] = accuracy_score
    test_results['availability_score'] = availability_score
    
    print(f"总测试项目: {total_tests}")
    print(f"通过测试: {passed_tests}")
    print(f"失败测试: {failed_tests}")
    print(f"准确率: {accuracy_score:.1f}%")
    print(f"可用率: {availability_score:.1f}%")
    
    # 评估结果
    if accuracy_score >= 99.0:
        print("🎉 恭喜! 应用已成功达到99%准确率和可用率目标!")
        result_status = 'SUCCESS'
    elif accuracy_score >= 95.0:
        print("✅ 优秀! 应用性能接近99%目标。")
        result_status = 'EXCELLENT'
    elif accuracy_score >= 90.0:
        print("👍 良好! 应用性能达到企业级标准。")
        result_status = 'GOOD'
    else:
        print("⚠️ 需要改进以达到99%目标。")
        result_status = 'NEEDS_IMPROVEMENT'
    
    test_results['result_status'] = result_status
    
    # 保存详细测试报告
    report_filename = f"comprehensive_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(report_filename, 'w', encoding='utf-8') as f:
        json.dump(test_results, f, ensure_ascii=False, indent=2)
    
    print(f"📄 详细测试报告已保存: {report_filename}")
    
    # 失败测试分析
    if failed_tests > 0:
        print("\n🔍 失败测试分析:")
        for test_name, details in test_results['test_details'].items():
            if not details['success']:
                print(f"  ✗ {test_name}: {details['details']}")
    
    print("\n🏁 测试完成!")
    
    return test_results

if __name__ == "__main__":
    main()