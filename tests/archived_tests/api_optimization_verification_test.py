#!/usr/bin/env python3
"""
API优化验证测试 (API Optimization Verification Test)
验证修复后的API端点是否正常工作
"""
import requests
import time
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class APIOptimizationVerificationTest:
    def __init__(self):
        self.base_url = "http://127.0.0.1:5000"
        self.session = requests.Session()
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

    def test_optimized_api_endpoints(self):
        """测试优化后的API端点"""
        logging.info("=== 测试优化后的API端点 ===")
        
        # 测试所有API路径变体
        api_tests = [
            # BTC价格API - 多路径测试
            {'name': 'BTC价格API - /get_btc_price', 'url': '/get_btc_price'},
            {'name': 'BTC价格API - /api/btc_price', 'url': '/api/btc_price'},
            {'name': 'BTC价格API - /api/btc-price', 'url': '/api/btc-price'},
            
            # 网络统计API - 多路径测试
            {'name': '网络统计API - /get_network_stats', 'url': '/get_network_stats'},
            {'name': '网络统计API - /api/network_stats', 'url': '/api/network_stats'},
            {'name': '网络统计API - /api/network-stats', 'url': '/api/network-stats'},
            
            # 矿机列表API - 多路径测试
            {'name': '矿机列表API - /get_miners', 'url': '/get_miners'},
            {'name': '矿机列表API - /api/miners', 'url': '/api/miners'},
            
            # 分析系统API - 验证仍正常工作
            {'name': '分析系统API - /api/analytics/market-data', 'url': '/api/analytics/market-data'},
        ]
        
        for test in api_tests:
            try:
                start_time = time.time()
                response = self.session.get(f"{self.base_url}{test['url']}")
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        
                        # 基本数据完整性检查
                        has_data = bool(data)
                        has_success = data.get('success', True)  # 某些API可能没有success字段
                        
                        # 特定数据验证
                        valid_data = True
                        key_metric = None
                        
                        if 'btc' in test['url'] or 'price' in test['url']:
                            price = data.get('price', 0)
                            valid_data = 50000 <= price <= 150000
                            key_metric = f"价格: ${price:,.0f}"
                        elif 'network' in test['url']:
                            hashrate = data.get('hashrate', 0)
                            valid_data = 500 <= hashrate <= 1200
                            key_metric = f"算力: {hashrate:.1f}EH/s"
                        elif 'miners' in test['url']:
                            miners = data.get('miners', [])
                            valid_data = len(miners) >= 8
                            key_metric = f"矿机数量: {len(miners)}"
                        elif 'analytics' in test['url']:
                            analytics_data = data.get('data', {})
                            btc_price = analytics_data.get('btc_price', 0)
                            valid_data = btc_price > 50000
                            key_metric = f"分析价格: ${btc_price:,.0f}"
                        
                        if has_data and has_success and valid_data:
                            logging.info(f"✅ {test['name']}: 正常工作 - {key_metric}, 响应时间: {response_time:.3f}s")
                        else:
                            logging.warning(f"⚠️ {test['name']}: 数据异常 - {key_metric}")
                    except json.JSONDecodeError:
                        logging.error(f"❌ {test['name']}: JSON解析失败")
                else:
                    logging.error(f"❌ {test['name']}: HTTP {response.status_code}")
                    
            except Exception as e:
                logging.error(f"❌ {test['name']}: 异常 - {str(e)}")

    def test_database_query_optimization(self):
        """测试数据库查询优化"""
        logging.info("=== 测试数据库查询优化 ===")
        
        # 测试原来有问题的查询是否已修复
        try:
            import psycopg2
            import os
            
            conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
            cursor = conn.cursor()
            
            # 测试修复后的网络快照查询
            start_time = time.time()
            cursor.execute("""
                SELECT COUNT(*), AVG(btc_price), AVG(network_difficulty)
                FROM (
                    SELECT btc_price, network_difficulty
                    FROM network_snapshots 
                    WHERE btc_price > 0 AND network_difficulty > 0
                    ORDER BY recorded_at DESC LIMIT 100
                ) recent_snapshots
            """)
            query_time = time.time() - start_time
            result = cursor.fetchone()
            
            if result and result[0] > 0:
                count = int(result[0])
                avg_price = float(result[1]) if result[1] else 0
                avg_difficulty = float(result[2]) if result[2] else 0
                
                logging.info(f"✅ 网络快照查询优化: 成功 - {count}条记录, 平均价格: ${avg_price:,.0f}, "
                           f"平均难度: {avg_difficulty/1e12:.2f}T, 查询时间: {query_time:.3f}s")
            else:
                logging.warning("⚠️ 网络快照查询: 无数据返回")
            
            # 测试市场分析查询性能
            start_time = time.time()
            cursor.execute("""
                SELECT COUNT(*), AVG(btc_price), MAX(recorded_at)
                FROM market_analytics 
                WHERE btc_price IS NOT NULL AND btc_price > 0
            """)
            query_time = time.time() - start_time
            result = cursor.fetchone()
            
            if result and result[0] > 0:
                count = int(result[0])
                avg_price = float(result[1]) if result[1] else 0
                latest_time = result[2]
                
                logging.info(f"✅ 市场分析查询: 成功 - {count}条记录, 平均价格: ${avg_price:,.0f}, "
                           f"最新时间: {latest_time}, 查询时间: {query_time:.3f}s")
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            logging.error(f"❌ 数据库查询测试失败: {str(e)}")

    def test_performance_improvements(self):
        """测试性能改进"""
        logging.info("=== 测试性能改进 ===")
        
        # 批量测试API响应时间
        performance_tests = [
            {'url': '/get_btc_price', 'max_time': 1.0},
            {'url': '/get_network_stats', 'max_time': 2.0},
            {'url': '/get_miners', 'max_time': 0.5},
            {'url': '/api/analytics/market-data', 'max_time': 1.0},
        ]
        
        total_time = 0
        passed_count = 0
        
        for test in performance_tests:
            try:
                start_time = time.time()
                response = self.session.get(f"{self.base_url}{test['url']}")
                response_time = time.time() - start_time
                total_time += response_time
                
                if response.status_code == 200 and response_time <= test['max_time']:
                    logging.info(f"✅ 性能测试 {test['url']}: {response_time:.3f}s (限制: {test['max_time']}s)")
                    passed_count += 1
                else:
                    logging.warning(f"⚠️ 性能测试 {test['url']}: {response_time:.3f}s (超出限制: {test['max_time']}s)")
                    
            except Exception as e:
                logging.error(f"❌ 性能测试 {test['url']}: 异常 - {str(e)}")
        
        avg_response_time = total_time / len(performance_tests) if performance_tests else 0
        performance_rate = (passed_count / len(performance_tests) * 100) if performance_tests else 0
        
        logging.info(f"📊 性能测试总结: {passed_count}/{len(performance_tests)} 通过 ({performance_rate:.1f}%)")
        logging.info(f"📊 平均响应时间: {avg_response_time:.3f}s")

    def run_verification_test(self):
        """运行API优化验证测试"""
        logging.info("🚀 开始API优化验证测试")
        
        if not self.authenticate():
            logging.error("用户认证失败，测试终止")
            return
        
        self.test_optimized_api_endpoints()
        self.test_database_query_optimization()
        self.test_performance_improvements()
        
        logging.info("🎯 API优化验证测试完成")

def main():
    """主函数"""
    tester = APIOptimizationVerificationTest()
    tester.run_verification_test()

if __name__ == "__main__":
    main()