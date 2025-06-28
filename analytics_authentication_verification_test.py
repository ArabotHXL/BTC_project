#!/usr/bin/env python3
"""
Analytics Authentication Verification Test
验证修复后的分析系统认证问题是否解决
"""

import requests
import json
import time
from datetime import datetime

class AnalyticsAuthenticationTest:
    def __init__(self):
        self.base_url = "http://127.0.0.1:5000"
        self.session = requests.Session()
        self.test_results = []
        self.owner_email = "hxl2022hao@gmail.com"
        
    def log_test(self, test_name, status, details="", response_time=None):
        """记录测试结果"""
        result = {
            "test_name": test_name,
            "status": status,
            "details": details,
            "response_time": response_time,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        print(f"[{status.upper()}] {test_name}: {details}")
        
    def authenticate_as_owner(self):
        """使用拥有者邮箱进行认证"""
        try:
            start_time = time.time()
            response = self.session.post(f"{self.base_url}/login", 
                                       data={"email": self.owner_email},
                                       allow_redirects=False)
            response_time = time.time() - start_time
            
            if response.status_code in [302, 200]:
                self.log_test("Owner Authentication", "PASS", 
                            f"Successfully authenticated as owner ({self.owner_email})", 
                            response_time)
                return True
            else:
                self.log_test("Owner Authentication", "FAIL", 
                            f"Authentication failed: {response.status_code}", 
                            response_time)
                return False
                
        except Exception as e:
            self.log_test("Owner Authentication", "ERROR", f"Authentication error: {e}")
            return False
    
    def test_analytics_market_data_api(self):
        """测试分析系统市场数据API"""
        try:
            start_time = time.time()
            response = self.session.get(f"{self.base_url}/api/analytics/market-data")
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                if 'btc_price' in data or ('data' in data and 'btc_price' in data['data']):
                    self.log_test("Analytics Market Data API", "PASS", 
                                f"Market data retrieved successfully", response_time)
                    return True
                else:
                    self.log_test("Analytics Market Data API", "FAIL", 
                                "Invalid data format returned", response_time)
                    return False
            else:
                self.log_test("Analytics Market Data API", "FAIL", 
                            f"API returned status {response.status_code}", response_time)
                return False
                
        except Exception as e:
            self.log_test("Analytics Market Data API", "ERROR", f"API call failed: {e}")
            return False
    
    def test_analytics_price_history_api(self):
        """测试分析系统价格历史API"""
        try:
            start_time = time.time()
            response = self.session.get(f"{self.base_url}/api/analytics/price-history?hours=24")
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                if 'price_history' in data or 'error' in data:
                    if 'error' in data:
                        self.log_test("Analytics Price History API", "PASS", 
                                    f"API accessible, no data available: {data['error']}", response_time)
                    else:
                        self.log_test("Analytics Price History API", "PASS", 
                                    f"Price history retrieved successfully ({len(data['price_history'])} records)", 
                                    response_time)
                    return True
                else:
                    self.log_test("Analytics Price History API", "FAIL", 
                                "Invalid response format", response_time)
                    return False
            else:
                self.log_test("Analytics Price History API", "FAIL", 
                            f"API returned status {response.status_code}: {response.text}", response_time)
                return False
                
        except Exception as e:
            self.log_test("Analytics Price History API", "ERROR", f"API call failed: {e}")
            return False
    
    def test_analytics_technical_indicators_api(self):
        """测试分析系统技术指标API"""
        try:
            start_time = time.time()
            response = self.session.get(f"{self.base_url}/api/analytics/technical-indicators")
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                # 技术指标可能为空，只要API可访问即可
                self.log_test("Analytics Technical Indicators API", "PASS", 
                            "Technical indicators API accessible", response_time)
                return True
            else:
                self.log_test("Analytics Technical Indicators API", "FAIL", 
                            f"API returned status {response.status_code}", response_time)
                return False
                
        except Exception as e:
            self.log_test("Analytics Technical Indicators API", "ERROR", f"API call failed: {e}")
            return False
    
    def test_analytics_latest_report_api(self):
        """测试分析系统最新报告API"""
        try:
            start_time = time.time()
            response = self.session.get(f"{self.base_url}/api/analytics/latest-report")
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                # 报告可能为空，只要API可访问即可
                self.log_test("Analytics Latest Report API", "PASS", 
                            "Latest report API accessible", response_time)
                return True
            else:
                self.log_test("Analytics Latest Report API", "FAIL", 
                            f"API returned status {response.status_code}", response_time)
                return False
                
        except Exception as e:
            self.log_test("Analytics Latest Report API", "ERROR", f"API call failed: {e}")
            return False
    
    def test_analytics_dashboard_page(self):
        """测试分析仪表盘页面访问"""
        try:
            start_time = time.time()
            response = self.session.get(f"{self.base_url}/analytics")
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                if "分析数据仪表盘" in response.text or "Analytics Dashboard" in response.text:
                    self.log_test("Analytics Dashboard Page", "PASS", 
                                "Dashboard page loads successfully", response_time)
                    return True
                else:
                    self.log_test("Analytics Dashboard Page", "FAIL", 
                                "Dashboard content not found", response_time)
                    return False
            else:
                self.log_test("Analytics Dashboard Page", "FAIL", 
                            f"Page returned status {response.status_code}", response_time)
                return False
                
        except Exception as e:
            self.log_test("Analytics Dashboard Page", "ERROR", f"Page access failed: {e}")
            return False
    
    def test_guest_access_restriction(self):
        """测试游客访问限制"""
        guest_session = requests.Session()
        try:
            # 测试未认证用户访问分析API
            response = guest_session.get(f"{self.base_url}/api/analytics/market-data")
            
            if response.status_code == 302:  # 重定向到登录页面
                self.log_test("Guest Access Restriction", "PASS", 
                            "Unauthenticated users properly redirected to login")
                return True
            elif response.status_code == 403:  # 直接拒绝访问
                self.log_test("Guest Access Restriction", "PASS", 
                            "Unauthenticated users properly denied access")
                return True
            else:
                self.log_test("Guest Access Restriction", "FAIL", 
                            f"Unexpected response for unauthenticated access: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Guest Access Restriction", "ERROR", f"Access restriction test failed: {e}")
            return False
    
    def generate_test_report(self):
        """生成测试报告"""
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r['status'] == 'PASS'])
        failed_tests = len([r for r in self.test_results if r['status'] == 'FAIL'])
        error_tests = len([r for r in self.test_results if r['status'] == 'ERROR'])
        
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        report = {
            "test_suite": "Analytics Authentication Verification",
            "execution_time": datetime.now().isoformat(),
            "summary": {
                "total_tests": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "errors": error_tests,
                "success_rate": f"{success_rate:.1f}%"
            },
            "test_results": self.test_results,
            "recommendations": []
        }
        
        # 生成建议
        if failed_tests > 0:
            report["recommendations"].append("Some analytics API endpoints are still failing - check authentication implementation")
        if error_tests > 0:
            report["recommendations"].append("Technical errors encountered - review server logs for details")
        if success_rate == 100:
            report["recommendations"].append("All analytics authentication tests passed - system ready for production")
        
        return report
    
    def run_complete_authentication_test(self):
        """运行完整的认证验证测试"""
        print("=" * 80)
        print("Analytics Authentication Verification Test")
        print("分析系统认证验证测试")
        print("=" * 80)
        
        # 1. 认证测试
        if not self.authenticate_as_owner():
            print("认证失败，无法继续测试")
            return self.generate_test_report()
        
        # 2. API访问测试
        self.test_analytics_market_data_api()
        self.test_analytics_price_history_api()
        self.test_analytics_technical_indicators_api()
        self.test_analytics_latest_report_api()
        
        # 3. 页面访问测试
        self.test_analytics_dashboard_page()
        
        # 4. 访问控制测试
        self.test_guest_access_restriction()
        
        # 5. 生成报告
        report = self.generate_test_report()
        
        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("测试总结")
        print("=" * 80)
        print(f"总测试数: {report['summary']['total_tests']}")
        print(f"通过: {report['summary']['passed']}")
        print(f"失败: {report['summary']['failed']}")
        print(f"错误: {report['summary']['errors']}")
        print(f"成功率: {report['summary']['success_rate']}")
        
        if report['recommendations']:
            print("\n建议:")
            for rec in report['recommendations']:
                print(f"- {rec}")
        
        # 保存详细报告
        with open('analytics_authentication_test_report.json', 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n详细报告已保存到: analytics_authentication_test_report.json")
        return report

def main():
    """主函数"""
    tester = AnalyticsAuthenticationTest()
    tester.run_complete_authentication_test()

if __name__ == "__main__":
    main()