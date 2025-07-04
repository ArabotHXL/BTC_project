#!/usr/bin/env python3
"""
统一测试框架
Unified Testing Framework

整合了所有测试功能的统一框架，避免代码重复
Unified framework that consolidates all testing functionality to avoid code duplication
"""

import json
import time
import requests
import psycopg2
from datetime import datetime
from typing import Dict, List, Any, Optional
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class UnifiedTestingFramework:
    """统一测试框架"""
    
    def __init__(self):
        self.base_url = "http://0.0.0.0:5000"
        self.session = requests.Session()
        self.db_url = os.environ.get('DATABASE_URL')
        self.test_results = []
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        self.warnings = 0
        
        # 标准测试邮箱
        self.standard_emails = [
            "testing123@example.com",
            "site@example.com", 
            "user@example.com",
            "hxl2022hao@gmail.com",
            "admin@example.com"
        ]
        
        # 收集数据用于一致性检查
        self.price_data = []
        self.hashrate_data = []
        self.calculation_results = []
    
    def log_test(self, category: str, test_name: str, status: str, details: str = "", 
                 response_time: Optional[float] = None, accuracy: Optional[float] = None,
                 email: Optional[str] = None):
        """记录测试结果"""
        result = {
            "timestamp": datetime.now().isoformat(),
            "category": category,
            "test_name": test_name,
            "status": status,
            "details": details,
            "response_time": response_time or 0.0,
            "accuracy": accuracy or 0.0,
            "email": email or "system"
        }
        self.test_results.append(result)
        
        self.total_tests += 1
        if status == "PASS":
            self.passed_tests += 1
        elif status == "FAIL":
            self.failed_tests += 1
        elif status == "WARNING":
            self.warnings += 1
        
        status_icon = "✅" if status == "PASS" else ("⚠️" if status == "WARNING" else "❌")
        logger.info(f"{status_icon} [{category}] {test_name} ({email}): {details}")
    
    def authenticate_email(self, email: str) -> bool:
        """认证指定邮箱"""
        try:
            start_time = time.time()
            response = self.session.get(f"{self.base_url}/")
            login_data = {"email": email}
            response = self.session.post(f"{self.base_url}/login", data=login_data, allow_redirects=True)
            response_time = time.time() - start_time
            
            if response.status_code == 200 and "logout" in response.text.lower():
                self.log_test("Authentication", "login", "PASS", 
                            f"认证成功", response_time, 100.0, email)
                return True
            else:
                self.log_test("Authentication", "login", "FAIL", 
                            f"认证失败: {response.status_code}", response_time, 0.0, email)
                return False
        except Exception as e:
            self.log_test("Authentication", "login", "FAIL", 
                        f"认证异常: {str(e)}", 0.0, 0.0, email)
            return False
    
    def test_btc_price_api(self, email: str = "system") -> None:
        """测试BTC价格API"""
        try:
            start_time = time.time()
            response = self.session.get(f"{self.base_url}/api/btc-price")
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success') and isinstance(data.get('btc_price'), (int, float)):
                    price = data['btc_price']
                    self.price_data.append(price)
                    
                    accuracy = 100.0
                    issues = []
                    
                    if not (80000 <= price <= 150000):
                        accuracy = 85.0
                        issues.append(f"价格${price}超出预期范围")
                    
                    status = "PASS" if accuracy >= 95 else "WARNING"
                    details = f"BTC价格${price:,.2f}"
                    if issues:
                        details += f" ({'; '.join(issues)})"
                    
                    self.log_test("Core_API", "btc_price", status, details, response_time, accuracy, email)
                else:
                    self.log_test("Core_API", "btc_price", "FAIL",
                                "价格API响应数据无效", response_time, 0.0, email)
            else:
                self.log_test("Core_API", "btc_price", "FAIL",
                            f"价格API响应错误: {response.status_code}", response_time, 0.0, email)
        except Exception as e:
            self.log_test("Core_API", "btc_price", "FAIL", f"价格API异常: {str(e)}", 0.0, 0.0, email)
    
    def test_network_stats_api(self, email: str = "system") -> None:
        """测试网络统计API"""
        try:
            start_time = time.time()
            response = self.session.get(f"{self.base_url}/api/network-stats")
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    hashrate = data.get('network_hashrate')
                    difficulty = data.get('difficulty')
                    
                    accuracy = 100.0
                    issues = []
                    
                    if isinstance(hashrate, (int, float)) and 600 <= hashrate <= 1200:
                        self.hashrate_data.append(hashrate)
                    else:
                        accuracy -= 40.0
                        issues.append(f"算力{hashrate}EH/s异常")
                    
                    if not (difficulty and isinstance(difficulty, (int, float))):
                        accuracy -= 30.0
                        issues.append("难度数据无效")
                    
                    status = "PASS" if accuracy >= 95 else ("WARNING" if accuracy >= 80 else "FAIL")
                    details = f"算力{hashrate}EH/s, 难度{difficulty}"
                    if issues:
                        details += f" ({'; '.join(issues)})"
                    
                    self.log_test("Core_API", "network_stats", status, details, response_time, accuracy, email)
                else:
                    self.log_test("Core_API", "network_stats", "FAIL",
                                "网络统计API响应数据无效", response_time, 0.0, email)
            else:
                self.log_test("Core_API", "network_stats", "FAIL",
                            f"网络统计API响应错误: {response.status_code}", response_time, 0.0, email)
        except Exception as e:
            self.log_test("Core_API", "network_stats", "FAIL", f"网络统计API异常: {str(e)}", 0.0, 0.0, email)
    
    def test_miners_api(self, email: str = "system") -> None:
        """测试矿机数据API"""
        try:
            start_time = time.time()
            response = self.session.get(f"{self.base_url}/api/miners")
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    miners = data.get('miners', [])
                    accuracy = 100.0
                    issues = []
                    
                    if len(miners) >= 10:
                        pass  # 优秀
                    elif len(miners) >= 8:
                        accuracy = 95.0
                        issues.append("矿机型号数量略少")
                    else:
                        accuracy = 70.0
                        issues.append("矿机型号严重不足")
                    
                    # 检查关键矿机型号
                    key_miners = ['Antminer S19 Pro', 'Antminer S21', 'Antminer S19']
                    found_key_miners = sum(1 for miner in miners if miner.get('name') in key_miners)
                    
                    if found_key_miners < 3:
                        accuracy -= 15.0
                        issues.append(f"关键矿机型号不足({found_key_miners}/3)")
                    
                    status = "PASS" if accuracy >= 95 else ("WARNING" if accuracy >= 85 else "FAIL")
                    details = f"矿机数据{len(miners)}个型号，{found_key_miners}个关键型号"
                    if issues:
                        details += f" ({'; '.join(issues)})"
                    
                    self.log_test("Core_API", "miners", status, details, response_time, accuracy, email)
                else:
                    self.log_test("Core_API", "miners", "FAIL",
                                "矿机API响应数据无效", response_time, 0.0, email)
            else:
                self.log_test("Core_API", "miners", "FAIL",
                            f"矿机API响应错误: {response.status_code}", response_time, 0.0, email)
        except Exception as e:
            self.log_test("Core_API", "miners", "FAIL", f"矿机API异常: {str(e)}", 0.0, 0.0, email)
    
    def test_mining_calculation(self, email: str = "system", miner_model: str = "Antminer S19 Pro") -> None:
        """测试挖矿计算功能"""
        params = {
            "miner_model": miner_model,
            "miner_count": "1",
            "electricity_cost": "0.06",
            "use_real_time_data": "true"
        }
        
        try:
            start_time = time.time()
            response = self.session.post(f"{self.base_url}/calculate", data=params)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    btc_output = result.get('site_daily_btc_output', 0)
                    revenue_data = result.get('revenue', {})
                    profit_data = result.get('profit', {})
                    
                    daily_revenue = revenue_data.get('daily', 0) if isinstance(revenue_data, dict) else 0
                    daily_profit = profit_data.get('daily', 0) if isinstance(profit_data, dict) else 0
                    
                    # 收集计算结果
                    calc_data = {
                        "miner_model": miner_model,
                        "btc_output": btc_output,
                        "daily_revenue": daily_revenue,
                        "daily_profit": daily_profit,
                        "email": email
                    }
                    self.calculation_results.append(calc_data)
                    
                    accuracy = 100.0
                    issues = []
                    
                    # 验证BTC产出
                    if not (isinstance(btc_output, (int, float)) and 0.001 <= btc_output <= 0.1):
                        accuracy -= 30.0
                        issues.append(f"BTC产出{btc_output}异常")
                    
                    # 验证收益
                    if not (isinstance(daily_revenue, (int, float)) and daily_revenue > 0):
                        accuracy -= 25.0
                        issues.append("收益数据无效")
                    
                    # 验证利润逻辑
                    if isinstance(daily_profit, (int, float)) and daily_profit > daily_revenue:
                        accuracy -= 30.0
                        issues.append("利润超过收入")
                    
                    status = "PASS" if accuracy >= 95 else ("WARNING" if accuracy >= 80 else "FAIL")
                    details = f"{miner_model}: BTC产出{btc_output:.6f}, 收益${daily_revenue:.2f}, 利润${daily_profit:.2f}"
                    if issues:
                        details += f" ({'; '.join(issues)})"
                    
                    self.log_test("Mining_Calc", "calculation", status, details, response_time, accuracy, email)
                else:
                    self.log_test("Mining_Calc", "calculation", "FAIL",
                                "计算返回success=false", response_time, 0.0, email)
            else:
                self.log_test("Mining_Calc", "calculation", "FAIL",
                            f"计算请求失败: {response.status_code}", response_time, 0.0, email)
        except Exception as e:
            self.log_test("Mining_Calc", "calculation", "FAIL", f"计算异常: {str(e)}", 0.0, 0.0, email)
    
    def test_system_pages(self) -> None:
        """测试系统页面"""
        pages = [
            ("/legal", "法律页面"),
            ("/", "主页")
        ]
        
        for path, name in pages:
            try:
                start_time = time.time()
                temp_session = requests.Session()
                response = temp_session.get(f"{self.base_url}{path}")
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    content_length = len(response.text)
                    accuracy = 100.0 if content_length > 10000 else 90.0
                    status = "PASS" if accuracy >= 95 else "WARNING"
                    
                    self.log_test("System_Pages", f"page_{path.replace('/', 'root')}", status,
                                f"{name}加载成功({content_length}字符)", response_time, accuracy)
                else:
                    self.log_test("System_Pages", f"page_{path.replace('/', 'root')}", "FAIL",
                                f"{name}加载失败: {response.status_code}", response_time, 0.0)
            except Exception as e:
                self.log_test("System_Pages", f"page_{path.replace('/', 'root')}", "FAIL",
                            f"{name}加载异常: {str(e)}", 0.0, 0.0)
    
    def test_data_consistency(self) -> None:
        """测试数据一致性"""
        # 价格数据一致性
        if len(self.price_data) >= 2:
            price_variance = (max(self.price_data) - min(self.price_data)) / max(self.price_data) * 100
            accuracy = 100.0 if price_variance <= 1.0 else (95.0 if price_variance <= 3.0 else 70.0)
            status = "PASS" if accuracy >= 95 else ("WARNING" if accuracy >= 85 else "FAIL")
            
            self.log_test("Data_Consistency", "price_variance", status,
                        f"价格差异{price_variance:.2f}% (样本{len(self.price_data)}个)",
                        0.0, accuracy)
        
        # 算力数据一致性
        if len(self.hashrate_data) >= 2:
            hashrate_variance = (max(self.hashrate_data) - min(self.hashrate_data)) / max(self.hashrate_data) * 100
            accuracy = 100.0 if hashrate_variance <= 2.0 else (90.0 if hashrate_variance <= 5.0 else 75.0)
            status = "PASS" if accuracy >= 95 else ("WARNING" if accuracy >= 85 else "FAIL")
            
            self.log_test("Data_Consistency", "hashrate_variance", status,
                        f"算力差异{hashrate_variance:.2f}% (样本{len(self.hashrate_data)}个)",
                        0.0, accuracy)
    
    def run_quick_test(self) -> Dict:
        """运行快速测试"""
        logger.info("开始快速系统测试...")
        
        # 单个邮箱快速测试
        test_email = self.standard_emails[0]
        if self.authenticate_email(test_email):
            self.test_btc_price_api(test_email)
            self.test_network_stats_api(test_email)
            self.test_miners_api(test_email)
            self.test_mining_calculation(test_email)
        
        self.test_system_pages()
        return self._generate_summary()
    
    def run_full_regression_test(self) -> Dict:
        """运行完整回归测试"""
        logger.info("开始完整回归测试...")
        
        # 对每个邮箱执行完整测试
        for email in self.standard_emails:
            logger.info(f"测试邮箱: {email}")
            
            if self.authenticate_email(email):
                self.test_btc_price_api(email)
                self.test_network_stats_api(email)
                self.test_miners_api(email)
                self.test_mining_calculation(email)
            
            time.sleep(0.3)  # 避免请求过快
        
        self.test_system_pages()
        self.test_data_consistency()
        
        return self._generate_summary()
    
    def _generate_summary(self) -> Dict:
        """生成测试摘要"""
        success_rate = (self.passed_tests / self.total_tests * 100) if self.total_tests > 0 else 0
        
        # 按类别统计
        categories = {}
        for result in self.test_results:
            cat = result['category']
            if cat not in categories:
                categories[cat] = {'total': 0, 'passed': 0}
            categories[cat]['total'] += 1
            if result['status'] == 'PASS':
                categories[cat]['passed'] += 1
        
        # 确定等级
        if success_rate >= 99:
            grade = "A+ (完美)"
        elif success_rate >= 95:
            grade = "A (优秀)"
        elif success_rate >= 90:
            grade = "B+ (良好)"
        else:
            grade = "B (需改进)"
        
        return {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_tests": self.total_tests,
                "passed_tests": self.passed_tests,
                "failed_tests": self.failed_tests,
                "warnings": self.warnings,
                "success_rate_percent": round(success_rate, 1),
                "system_grade": grade,
                "meets_99_percent_target": success_rate >= 99
            },
            "category_breakdown": categories,
            "detailed_results": self.test_results
        }

def main():
    """主函数"""
    framework = UnifiedTestingFramework()
    
    # 可以选择运行快速测试或完整测试
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--full":
        results = framework.run_full_regression_test()
        test_type = "完整回归测试"
    else:
        results = framework.run_quick_test()
        test_type = "快速系统测试"
    
    # 输出结果
    print(f"\n{'='*80}")
    print(f"{test_type}完成")
    print(f"{'='*80}")
    print(f"总测试数: {results['summary']['total_tests']}")
    print(f"通过: {results['summary']['passed_tests']}")
    print(f"失败: {results['summary']['failed_tests']}")
    print(f"警告: {results['summary']['warnings']}")
    print(f"成功率: {results['summary']['success_rate_percent']}%")
    print(f"系统等级: {results['summary']['system_grade']}")
    
    # 保存详细报告
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"test_report_{timestamp}.json"
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n详细报告: {filename}")

if __name__ == "__main__":
    main()