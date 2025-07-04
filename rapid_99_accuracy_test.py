#!/usr/bin/env python3
"""
快速99%准确率回归测试
Rapid 99% Accuracy Regression Test

使用多个邮箱快速验证核心功能和数值计算准确性
"""

import json
import time
import requests
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Rapid99AccuracyTest:
    def __init__(self):
        self.base_url = "http://0.0.0.0:5000"
        self.session = requests.Session()
        self.test_results = []
        
        # 测试邮箱
        self.test_emails = [
            "testing123@example.com",
            "site@example.com", 
            "user@example.com",
            "hxl2022hao@gmail.com",
            "admin@example.com"
        ]
        
        self.passed = 0
        self.total = 0
        
    def log_result(self, test_name: str, status: str, details: str, email: str = ""):
        """记录测试结果"""
        self.total += 1
        if status == "PASS":
            self.passed += 1
            icon = "✅"
        else:
            icon = "❌"
        
        result = {
            "test": test_name,
            "status": status,
            "details": details,
            "email": email,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        logger.info(f"{icon} {test_name} ({email}): {details}")
    
    def authenticate(self, email: str) -> bool:
        """认证指定邮箱"""
        try:
            response = self.session.get(f"{self.base_url}/")
            login_data = {"email": email}
            response = self.session.post(f"{self.base_url}/login", data=login_data, allow_redirects=True)
            
            if response.status_code == 200 and "logout" in response.text.lower():
                self.log_result("Authentication", "PASS", "登录成功", email)
                return True
            else:
                self.log_result("Authentication", "FAIL", f"登录失败: {response.status_code}", email)
                return False
        except Exception as e:
            self.log_result("Authentication", "FAIL", f"认证异常: {str(e)}", email)
            return False
    
    def test_apis(self, email: str):
        """测试核心API"""
        
        # BTC价格API
        try:
            response = self.session.get(f"{self.base_url}/api/btc-price")
            if response.status_code == 200:
                data = response.json()
                if data.get('success') and isinstance(data.get('btc_price'), (int, float)):
                    price = data['btc_price']
                    if 80000 <= price <= 150000:
                        self.log_result("BTC_Price_API", "PASS", f"价格${price:,.2f}正常", email)
                    else:
                        self.log_result("BTC_Price_API", "FAIL", f"价格${price:,.2f}异常", email)
                else:
                    self.log_result("BTC_Price_API", "FAIL", "价格数据无效", email)
            else:
                self.log_result("BTC_Price_API", "FAIL", f"API错误: {response.status_code}", email)
        except Exception as e:
            self.log_result("BTC_Price_API", "FAIL", f"异常: {str(e)}", email)
        
        # 网络统计API
        try:
            response = self.session.get(f"{self.base_url}/api/network-stats")
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    hashrate = data.get('network_hashrate')
                    if isinstance(hashrate, (int, float)) and 600 <= hashrate <= 1200:
                        self.log_result("Network_Stats_API", "PASS", f"算力{hashrate}EH/s正常", email)
                    else:
                        self.log_result("Network_Stats_API", "FAIL", f"算力{hashrate}异常", email)
                else:
                    self.log_result("Network_Stats_API", "FAIL", "网络数据无效", email)
            else:
                self.log_result("Network_Stats_API", "FAIL", f"API错误: {response.status_code}", email)
        except Exception as e:
            self.log_result("Network_Stats_API", "FAIL", f"异常: {str(e)}", email)
        
        # 矿机数据API
        try:
            response = self.session.get(f"{self.base_url}/api/miners")
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    miners = data.get('miners', [])
                    if len(miners) >= 8:
                        self.log_result("Miners_API", "PASS", f"矿机数据{len(miners)}个型号", email)
                    else:
                        self.log_result("Miners_API", "FAIL", f"矿机型号不足: {len(miners)}", email)
                else:
                    self.log_result("Miners_API", "FAIL", "矿机数据无效", email)
            else:
                self.log_result("Miners_API", "FAIL", f"API错误: {response.status_code}", email)
        except Exception as e:
            self.log_result("Miners_API", "FAIL", f"异常: {str(e)}", email)
    
    def test_calculation(self, email: str):
        """测试挖矿计算"""
        params = {
            "miner_model": "Antminer S19 Pro",
            "miner_count": "1",
            "electricity_cost": "0.06",
            "use_real_time_data": "true"
        }
        
        try:
            response = self.session.post(f"{self.base_url}/calculate", data=params)
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    btc_output = result.get('site_daily_btc_output', 0)
                    revenue_data = result.get('revenue', {})
                    profit_data = result.get('profit', {})
                    
                    daily_revenue = revenue_data.get('daily', 0) if isinstance(revenue_data, dict) else 0
                    daily_profit = profit_data.get('daily', 0) if isinstance(profit_data, dict) else 0
                    
                    # 验证计算结果合理性
                    if (isinstance(btc_output, (int, float)) and 0.001 <= btc_output <= 0.1 and
                        isinstance(daily_revenue, (int, float)) and daily_revenue > 0 and
                        isinstance(daily_profit, (int, float)) and daily_profit <= daily_revenue):
                        
                        self.log_result("Mining_Calculation", "PASS", 
                                      f"BTC产出{btc_output:.6f}, 收益${daily_revenue:.2f}, 利润${daily_profit:.2f}", email)
                    else:
                        self.log_result("Mining_Calculation", "FAIL", 
                                      f"计算结果异常: BTC={btc_output}, 收益=${daily_revenue}, 利润=${daily_profit}", email)
                else:
                    self.log_result("Mining_Calculation", "FAIL", "计算失败", email)
            else:
                self.log_result("Mining_Calculation", "FAIL", f"计算错误: {response.status_code}", email)
        except Exception as e:
            self.log_result("Mining_Calculation", "FAIL", f"异常: {str(e)}", email)
    
    def run_test(self):
        """运行测试"""
        logger.info("="*80)
        logger.info("开始快速99%准确率回归测试")
        logger.info(f"测试邮箱: {len(self.test_emails)}个")
        logger.info("="*80)
        
        start_time = time.time()
        
        for i, email in enumerate(self.test_emails, 1):
            logger.info(f"\n[{i}/{len(self.test_emails)}] 测试邮箱: {email}")
            
            if self.authenticate(email):
                self.test_apis(email)
                self.test_calculation(email)
            
            time.sleep(0.3)  # 避免请求过快
        
        # 系统级测试
        logger.info(f"\n[系统] 测试公开页面...")
        try:
            temp_session = requests.Session()
            response = temp_session.get(f"{self.base_url}/legal")
            if response.status_code == 200 and len(response.text) > 10000:
                self.log_result("Legal_Page", "PASS", f"法律页面加载成功({len(response.text)}字符)")
            else:
                self.log_result("Legal_Page", "FAIL", f"法律页面异常: {response.status_code}")
        except Exception as e:
            self.log_result("Legal_Page", "FAIL", f"异常: {str(e)}")
        
        # 生成报告
        total_time = time.time() - start_time
        self.generate_report(total_time)
    
    def generate_report(self, total_time: float):
        """生成测试报告"""
        success_rate = (self.passed / self.total * 100) if self.total > 0 else 0
        
        # 按邮箱统计
        email_stats = {}
        for result in self.test_results:
            email = result.get('email', 'system')
            if email not in email_stats:
                email_stats[email] = {'passed': 0, 'total': 0}
            email_stats[email]['total'] += 1
            if result['status'] == 'PASS':
                email_stats[email]['passed'] += 1
        
        # 确定等级
        if success_rate >= 99:
            grade = "A+ (完美)"
        elif success_rate >= 95:
            grade = "A (优秀)"
        elif success_rate >= 90:
            grade = "B+ (良好)"
        else:
            grade = "B (需改进)"
        
        # 生成报告文件
        report = {
            "test_metadata": {
                "test_name": "Rapid 99% Accuracy Regression Test",
                "timestamp": datetime.now().isoformat(),
                "duration_seconds": round(total_time, 2),
                "test_emails": self.test_emails
            },
            "summary": {
                "total_tests": self.total,
                "passed_tests": self.passed,
                "success_rate_percent": round(success_rate, 1),
                "system_grade": grade,
                "meets_99_percent_target": success_rate >= 99
            },
            "email_breakdown": {
                email: {
                    "passed": stats['passed'],
                    "total": stats['total'],
                    "success_rate": round(stats['passed'] / stats['total'] * 100, 1) if stats['total'] > 0 else 0
                }
                for email, stats in email_stats.items()
            },
            "detailed_results": self.test_results
        }
        
        filename = f"rapid_99_accuracy_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        # 输出结果
        logger.info(f"\n{'='*80}")
        logger.info(f"快速99%准确率回归测试完成")
        logger.info(f"{'='*80}")
        logger.info(f"总测试数: {self.total}")
        logger.info(f"通过测试: {self.passed}")
        logger.info(f"成功率: {success_rate:.1f}%")
        logger.info(f"系统等级: {grade}")
        logger.info(f"测试耗时: {total_time:.1f}秒")
        logger.info(f"")
        logger.info(f"邮箱测试结果:")
        for email, stats in email_stats.items():
            rate = stats['passed'] / stats['total'] * 100 if stats['total'] > 0 else 0
            logger.info(f"  {email}: {stats['passed']}/{stats['total']} ({rate:.1f}%)")
        logger.info(f"")
        if success_rate >= 99:
            logger.info(f"🎉 系统达到99%+准确率标准!")
        elif success_rate >= 95:
            logger.info(f"⭐ 系统表现优秀，接近99%标准")
        else:
            logger.info(f"⚠️ 系统需要优化以达到99%标准")
        logger.info(f"")
        logger.info(f"详细报告: {filename}")
        logger.info(f"{'='*80}")

def main():
    tester = Rapid99AccuracyTest()
    tester.run_test()

if __name__ == "__main__":
    main()