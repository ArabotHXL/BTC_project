#!/usr/bin/env python3
"""
系统回归测试总结 (System Regression Test Summary)
基于已执行的测试结果生成完整系统状态报告
"""
import requests
import time
import json
import logging
import psycopg2
import os
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class SystemRegressionSummary:
    def __init__(self):
        self.base_url = "http://127.0.0.1:5000"
        self.session = requests.Session()
        self.test_user_email = "hxl2022hao@gmail.com"
        
    def authenticate(self):
        """用户认证"""
        try:
            login_data = {'email': self.test_user_email}
            response = self.session.post(f"{self.base_url}/login", data=login_data)
            return response.status_code == 200 and "logout" in response.text.lower()
        except:
            return False

    def quick_system_validation(self):
        """快速系统验证"""
        logging.info("=== 快速系统验证 ===")
        
        results = {
            'database': {'tested': 0, 'passed': 0},
            'api': {'tested': 0, 'passed': 0},
            'frontend': {'tested': 0, 'passed': 0},
            'calculations': {'tested': 0, 'passed': 0},
            'analytics': {'tested': 0, 'passed': 0}
        }
        
        # 数据库验证
        try:
            conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
            cursor = conn.cursor()
            
            # 核心表验证
            core_tables = ['market_analytics', 'network_snapshots', 'user_access', 'crm_customers']
            for table in core_tables:
                results['database']['tested'] += 1
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    if count >= 0:
                        results['database']['passed'] += 1
                        logging.info(f"✅ 数据库表 {table}: {count} 记录")
                except:
                    logging.error(f"❌ 数据库表 {table}: 查询失败")
            
            cursor.close()
            conn.close()
        except Exception as e:
            logging.error(f"数据库连接失败: {e}")
        
        # API端点验证
        core_apis = [
            '/get_btc_price',
            '/get_network_stats', 
            '/get_miners',
            '/api/analytics/market-data'
        ]
        
        for api in core_apis:
            results['api']['tested'] += 1
            try:
                response = self.session.get(f"{self.base_url}{api}")
                if response.status_code == 200:
                    data = response.json()
                    if data:
                        results['api']['passed'] += 1
                        logging.info(f"✅ API端点 {api}: 正常")
                    else:
                        logging.warning(f"⚠️ API端点 {api}: 无数据")
                else:
                    logging.error(f"❌ API端点 {api}: HTTP {response.status_code}")
            except Exception as e:
                logging.error(f"❌ API端点 {api}: {str(e)}")
        
        # 前端页面验证
        core_pages = ['/', '/crm/dashboard', '/network_history', '/analytics_dashboard']
        
        for page in core_pages:
            results['frontend']['tested'] += 1
            try:
                response = self.session.get(f"{self.base_url}{page}")
                if response.status_code == 200:
                    content = response.text.lower()
                    if any(keyword in content for keyword in ['计算', 'dashboard', '分析', 'crm']):
                        results['frontend']['passed'] += 1
                        logging.info(f"✅ 前端页面 {page}: 加载正常")
                    else:
                        logging.warning(f"⚠️ 前端页面 {page}: 内容异常")
                else:
                    logging.error(f"❌ 前端页面 {page}: HTTP {response.status_code}")
            except Exception as e:
                logging.error(f"❌ 前端页面 {page}: {str(e)}")
        
        # 挖矿计算验证
        calculation_tests = [
            {'miner_model': 'Antminer S19 Pro', 'miner_count': '1'},
            {'miner_model': 'Antminer S21', 'miner_count': '1'}
        ]
        
        for test in calculation_tests:
            results['calculations']['tested'] += 1
            try:
                response = self.session.post(f"{self.base_url}/calculate", data=test)
                if response.status_code == 200:
                    result = response.json()
                    if result.get('success') and result.get('btc_mined', {}).get('daily', 0) > 0:
                        results['calculations']['passed'] += 1
                        daily_btc = result['btc_mined']['daily']
                        logging.info(f"✅ 挖矿计算 {test['miner_model']}: {daily_btc:.6f} BTC/日")
                    else:
                        logging.warning(f"⚠️ 挖矿计算 {test['miner_model']}: 计算异常")
                else:
                    logging.error(f"❌ 挖矿计算 {test['miner_model']}: HTTP {response.status_code}")
            except Exception as e:
                logging.error(f"❌ 挖矿计算 {test['miner_model']}: {str(e)}")
        
        # 分析系统验证
        analytics_apis = [
            '/api/analytics/market-data',
            '/api/analytics/technical-indicators'
        ]
        
        for api in analytics_apis:
            results['analytics']['tested'] += 1
            try:
                response = self.session.get(f"{self.base_url}{api}")
                if response.status_code == 200:
                    data = response.json()
                    if data:
                        results['analytics']['passed'] += 1
                        logging.info(f"✅ 分析系统 {api}: 数据正常")
                    else:
                        logging.warning(f"⚠️ 分析系统 {api}: 无数据")
                else:
                    logging.error(f"❌ 分析系统 {api}: HTTP {response.status_code}")
            except Exception as e:
                logging.error(f"❌ 分析系统 {api}: {str(e)}")
        
        return results

    def generate_system_health_report(self, results):
        """生成系统健康报告"""
        total_tested = sum(cat['tested'] for cat in results.values())
        total_passed = sum(cat['passed'] for cat in results.values())
        overall_success_rate = (total_passed / total_tested * 100) if total_tested > 0 else 0
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'overall_health': {
                'total_tests': total_tested,
                'passed_tests': total_passed,
                'success_rate': round(overall_success_rate, 1),
                'status': 'HEALTHY' if overall_success_rate >= 85 else 'DEGRADED' if overall_success_rate >= 70 else 'CRITICAL'
            },
            'component_health': {}
        }
        
        # 组件健康状态
        for component, stats in results.items():
            success_rate = (stats['passed'] / stats['tested'] * 100) if stats['tested'] > 0 else 0
            status = 'HEALTHY' if success_rate >= 85 else 'DEGRADED' if success_rate >= 70 else 'CRITICAL'
            
            report['component_health'][component] = {
                'tested': stats['tested'],
                'passed': stats['passed'],
                'success_rate': round(success_rate, 1),
                'status': status
            }
        
        # 保存报告
        with open('system_health_report.json', 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        # 生成总结
        logging.info("=== 系统健康报告 ===")
        logging.info(f"📊 整体状态: {report['overall_health']['status']}")
        logging.info(f"📈 总体成功率: {overall_success_rate:.1f}%")
        logging.info(f"✅ 通过测试: {total_passed}/{total_tested}")
        logging.info("")
        logging.info("📋 组件状态:")
        
        for component, health in report['component_health'].items():
            status_icon = "🟢" if health['status'] == 'HEALTHY' else "🟡" if health['status'] == 'DEGRADED' else "🔴"
            logging.info(f"  {status_icon} {component}: {health['passed']}/{health['tested']} ({health['success_rate']}%) - {health['status']}")
        
        logging.info(f"📄 详细报告已保存: system_health_report.json")
        return report

    def run_summary_test(self):
        """运行总结测试"""
        logging.info("🚀 开始系统回归测试总结")
        
        if not self.authenticate():
            logging.error("用户认证失败")
            return None
        
        results = self.quick_system_validation()
        report = self.generate_system_health_report(results)
        
        return report

def main():
    """主函数"""
    tester = SystemRegressionSummary()
    report = tester.run_summary_test()
    
    if report:
        print("\n" + "="*50)
        print("系统回归测试总结")
        print("="*50)
        print(f"整体状态: {report['overall_health']['status']}")
        print(f"成功率: {report['overall_health']['success_rate']}%")
        print(f"测试总数: {report['overall_health']['total_tests']}")
        print(f"通过测试: {report['overall_health']['passed_tests']}")
        print("="*50)

if __name__ == "__main__":
    main()