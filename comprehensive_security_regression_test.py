#!/usr/bin/env python3
"""
综合安全回归测试
Comprehensive Security Regression Test

全面验证系统功能性和安全性特性
Complete validation of system functionality and security features
"""

import requests
import json
import time
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('security_regression_test.log'),
        logging.StreamHandler()
    ]
)

class ComprehensiveSecurityRegressionTest:
    """综合安全回归测试器"""
    
    def __init__(self):
        self.base_url = "http://localhost:5000"
        self.session = requests.Session()
        self.test_results = []
        self.test_emails = [
            "testing123@example.com",
            "site@example.com", 
            "user@example.com",
            "hxl2022hao@gmail.com",
            "admin@example.com"
        ]
        
    def log_test(self, category: str, test_name: str, status: str, details: str = "", 
                 security_score: Optional[float] = None, response_time: Optional[float] = None,
                 email: Optional[str] = None):
        """记录测试结果"""
        result = {
            "category": category,
            "test_name": test_name,
            "status": status,
            "details": details,
            "security_score": security_score,
            "response_time": response_time,
            "email": email,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        status_icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        logging.info(f"{status_icon} [{category}] {test_name} ({email or 'N/A'}): {details}")
        
    def test_authentication_security(self, email: str) -> bool:
        """测试认证系统安全性"""
        try:
            # 测试正常登录
            start_time = time.time()
            response = self.session.post(f"{self.base_url}/login", 
                                       data={"email": email},
                                       allow_redirects=False)
            response_time = time.time() - start_time
            
            if response.status_code == 302:
                self.log_test("Authentication_Security", "valid_login", "PASS", 
                            f"正常登录成功 - 状态码: {response.status_code}", 
                            security_score=100.0, response_time=response_time, email=email)
                return True
            else:
                self.log_test("Authentication_Security", "valid_login", "FAIL", 
                            f"登录失败 - 状态码: {response.status_code}", 
                            security_score=0.0, response_time=response_time, email=email)
                return False
                
        except Exception as e:
            self.log_test("Authentication_Security", "valid_login", "FAIL", 
                        f"登录异常: {str(e)}", security_score=0.0, email=email)
            return False
            
    def test_unauthorized_access_protection(self) -> bool:
        """测试未授权访问保护"""
        try:
            # 测试未登录访问受保护页面
            start_time = time.time()
            response = self.session.get(f"{self.base_url}/", allow_redirects=False)
            response_time = time.time() - start_time
            
            if response.status_code == 302:
                self.log_test("Access_Control", "unauthorized_protection", "PASS", 
                            f"未授权访问正确重定向 - 状态码: {response.status_code}", 
                            security_score=100.0, response_time=response_time)
                return True
            else:
                self.log_test("Access_Control", "unauthorized_protection", "FAIL", 
                            f"未授权访问保护失败 - 状态码: {response.status_code}", 
                            security_score=0.0, response_time=response_time)
                return False
                
        except Exception as e:
            self.log_test("Access_Control", "unauthorized_protection", "FAIL", 
                        f"访问控制测试异常: {str(e)}", security_score=0.0)
            return False
            
    def test_invalid_email_rejection(self) -> bool:
        """测试无效邮箱拒绝"""
        invalid_emails = [
            "invalid@example.com",
            "hacker@evil.com",
            "test@malicious.org",
            "unauthorized@bad.com"
        ]
        
        passed_tests = 0
        total_tests = len(invalid_emails)
        
        for invalid_email in invalid_emails:
            try:
                start_time = time.time()
                response = self.session.post(f"{self.base_url}/login", 
                                           data={"email": invalid_email},
                                           allow_redirects=False)
                response_time = time.time() - start_time
                
                if response.status_code != 302:
                    self.log_test("Email_Validation", "invalid_email_rejection", "PASS", 
                                f"无效邮箱正确拒绝: {invalid_email}", 
                                security_score=100.0, response_time=response_time, email=invalid_email)
                    passed_tests += 1
                else:
                    self.log_test("Email_Validation", "invalid_email_rejection", "FAIL", 
                                f"无效邮箱未被拒绝: {invalid_email}", 
                                security_score=0.0, response_time=response_time, email=invalid_email)
                    
            except Exception as e:
                self.log_test("Email_Validation", "invalid_email_rejection", "FAIL", 
                            f"邮箱验证测试异常: {str(e)}", security_score=0.0, email=invalid_email)
                
        success_rate = (passed_tests / total_tests) * 100
        return success_rate >= 75  # 75%以上通过率为合格
        
    def test_session_management(self, email: str) -> bool:
        """测试会话管理安全"""
        try:
            # 先登录
            login_response = self.session.post(f"{self.base_url}/login", 
                                             data={"email": email},
                                             allow_redirects=True)
            
            if login_response.status_code != 200:
                self.log_test("Session_Management", "session_creation", "FAIL", 
                            f"无法创建会话 - 状态码: {login_response.status_code}", 
                            security_score=0.0, email=email)
                return False
                
            # 测试会话有效性
            start_time = time.time()
            response = self.session.get(f"{self.base_url}/")
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                self.log_test("Session_Management", "session_validation", "PASS", 
                            f"会话管理正常 - 页面大小: {len(response.content)} bytes", 
                            security_score=100.0, response_time=response_time, email=email)
                return True
            else:
                self.log_test("Session_Management", "session_validation", "FAIL", 
                            f"会话验证失败 - 状态码: {response.status_code}", 
                            security_score=0.0, response_time=response_time, email=email)
                return False
                
        except Exception as e:
            self.log_test("Session_Management", "session_validation", "FAIL", 
                        f"会话管理测试异常: {str(e)}", security_score=0.0, email=email)
            return False
            
    def test_api_authentication(self, email: str) -> bool:
        """测试API认证安全"""
        try:
            # 确保已登录
            self.session.post(f"{self.base_url}/login", 
                            data={"email": email}, allow_redirects=True)
            
            # 测试API端点
            api_endpoints = [
                "/api/btc-price",
                "/api/network-stats", 
                "/api/miners",
                "/api/calculate"
            ]
            
            passed_tests = 0
            total_tests = len(api_endpoints)
            
            for endpoint in api_endpoints:
                start_time = time.time()
                response = self.session.get(f"{self.base_url}{endpoint}")
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        if isinstance(data, dict):
                            self.log_test("API_Authentication", f"api_access_{endpoint.replace('/', '_')}", 
                                        "PASS", f"API端点正常访问", 
                                        security_score=100.0, response_time=response_time, email=email)
                            passed_tests += 1
                        else:
                            self.log_test("API_Authentication", f"api_access_{endpoint.replace('/', '_')}", 
                                        "FAIL", f"API响应格式错误", 
                                        security_score=50.0, response_time=response_time, email=email)
                    except:
                        self.log_test("API_Authentication", f"api_access_{endpoint.replace('/', '_')}", 
                                    "FAIL", f"API响应非JSON格式", 
                                    security_score=25.0, response_time=response_time, email=email)
                else:
                    self.log_test("API_Authentication", f"api_access_{endpoint.replace('/', '_')}", 
                                "FAIL", f"API访问失败 - 状态码: {response.status_code}", 
                                security_score=0.0, response_time=response_time, email=email)
                    
            success_rate = (passed_tests / total_tests) * 100
            return success_rate >= 75
            
        except Exception as e:
            self.log_test("API_Authentication", "api_access_test", "FAIL", 
                        f"API认证测试异常: {str(e)}", security_score=0.0, email=email)
            return False
            
    def test_legal_compliance_access(self) -> bool:
        """测试法律合规页面访问"""
        try:
            start_time = time.time()
            response = self.session.get(f"{self.base_url}/legal-terms")
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                content_length = len(response.content)
                if content_length > 5000:  # 期望法律页面内容丰富
                    self.log_test("Legal_Compliance", "legal_page_access", "PASS", 
                                f"法律页面公开访问正常 - 内容长度: {content_length} bytes", 
                                security_score=100.0, response_time=response_time)
                    return True
                else:
                    self.log_test("Legal_Compliance", "legal_page_access", "WARN", 
                                f"法律页面内容较少 - 内容长度: {content_length} bytes", 
                                security_score=70.0, response_time=response_time)
                    return True
            else:
                self.log_test("Legal_Compliance", "legal_page_access", "FAIL", 
                            f"法律页面访问失败 - 状态码: {response.status_code}", 
                            security_score=0.0, response_time=response_time)
                return False
                
        except Exception as e:
            self.log_test("Legal_Compliance", "legal_page_access", "FAIL", 
                        f"法律页面访问异常: {str(e)}", security_score=0.0)
            return False
            
    def test_data_consistency_security(self) -> bool:
        """测试数据一致性安全"""
        try:
            # 使用第一个邮箱获取基准数据
            baseline_email = self.test_emails[0]
            self.session.post(f"{self.base_url}/login", 
                            data={"email": baseline_email}, allow_redirects=True)
            
            # 获取基准数据
            baseline_data = {}
            start_time = time.time()
            
            price_response = self.session.get(f"{self.base_url}/api/btc-price")
            if price_response.status_code == 200:
                baseline_data['btc_price'] = price_response.json()
                
            network_response = self.session.get(f"{self.base_url}/api/network-stats")
            if network_response.status_code == 200:
                baseline_data['network_stats'] = network_response.json()
                
            response_time = time.time() - start_time
            
            # 测试其他邮箱是否获得相同数据
            consistent_results = 0
            total_comparisons = 0
            
            for email in self.test_emails[1:]:
                # 切换用户
                self.session.post(f"{self.base_url}/login", 
                                data={"email": email}, allow_redirects=True)
                
                # 比较BTC价格
                price_response = self.session.get(f"{self.base_url}/api/btc-price")
                if price_response.status_code == 200:
                    current_price = price_response.json()
                    if current_price == baseline_data.get('btc_price'):
                        consistent_results += 1
                    total_comparisons += 1
                    
                # 比较网络统计
                network_response = self.session.get(f"{self.base_url}/api/network-stats")
                if network_response.status_code == 200:
                    current_network = network_response.json()
                    if current_network == baseline_data.get('network_stats'):
                        consistent_results += 1
                    total_comparisons += 1
                    
            consistency_rate = (consistent_results / total_comparisons * 100) if total_comparisons > 0 else 0
            
            if consistency_rate >= 95:
                self.log_test("Data_Consistency", "cross_user_data_consistency", "PASS", 
                            f"数据一致性excellent - 一致率: {consistency_rate:.1f}%", 
                            security_score=100.0, response_time=response_time)
                return True
            elif consistency_rate >= 80:
                self.log_test("Data_Consistency", "cross_user_data_consistency", "WARN", 
                            f"数据一致性良好 - 一致率: {consistency_rate:.1f}%", 
                            security_score=80.0, response_time=response_time)
                return True
            else:
                self.log_test("Data_Consistency", "cross_user_data_consistency", "FAIL", 
                            f"数据一致性差 - 一致率: {consistency_rate:.1f}%", 
                            security_score=50.0, response_time=response_time)
                return False
                
        except Exception as e:
            self.log_test("Data_Consistency", "cross_user_data_consistency", "FAIL", 
                        f"数据一致性测试异常: {str(e)}", security_score=0.0)
            return False
            
    def test_calculation_accuracy_security(self) -> bool:
        """测试计算精确度安全"""
        try:
            # 登录测试用户
            test_email = self.test_emails[0]
            self.session.post(f"{self.base_url}/login", 
                            data={"email": test_email}, allow_redirects=True)
            
            # 测试挖矿计算
            calculation_data = {
                "miner_model": "Antminer S19 Pro",
                "miner_count": 1,
                "site_power_mw": 3.25,
                "use_real_time": True
            }
            
            start_time = time.time()
            response = self.session.post(f"{self.base_url}/calculate", 
                                       data=calculation_data)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    
                    # 验证关键计算字段
                    required_fields = ['btc_mined_daily', 'daily_revenue_usd', 'daily_profit_usd']
                    missing_fields = [field for field in required_fields if field not in result]
                    
                    if not missing_fields:
                        # 验证数值合理性
                        btc_mined = float(result.get('btc_mined_daily', 0))
                        daily_revenue = float(result.get('daily_revenue_usd', 0))
                        daily_profit = float(result.get('daily_profit_usd', 0))
                        
                        if 0.001 <= btc_mined <= 1.0 and daily_revenue > 0 and daily_profit < daily_revenue:
                            self.log_test("Calculation_Security", "mining_calculation_accuracy", "PASS", 
                                        f"计算精确度正常 - BTC: {btc_mined:.6f}, 收益: ${daily_revenue:.2f}, 利润: ${daily_profit:.2f}", 
                                        security_score=100.0, response_time=response_time, email=test_email)
                            return True
                        else:
                            self.log_test("Calculation_Security", "mining_calculation_accuracy", "FAIL", 
                                        f"计算结果不合理 - BTC: {btc_mined}, 收益: ${daily_revenue}, 利润: ${daily_profit}", 
                                        security_score=30.0, response_time=response_time, email=test_email)
                            return False
                    else:
                        self.log_test("Calculation_Security", "mining_calculation_accuracy", "FAIL", 
                                    f"计算结果缺少关键字段: {missing_fields}", 
                                    security_score=20.0, response_time=response_time, email=test_email)
                        return False
                        
                except Exception as e:
                    self.log_test("Calculation_Security", "mining_calculation_accuracy", "FAIL", 
                                f"计算结果解析错误: {str(e)}", 
                                security_score=0.0, response_time=response_time, email=test_email)
                    return False
            else:
                self.log_test("Calculation_Security", "mining_calculation_accuracy", "FAIL", 
                            f"计算请求失败 - 状态码: {response.status_code}", 
                            security_score=0.0, response_time=response_time, email=test_email)
                return False
                
        except Exception as e:
            self.log_test("Calculation_Security", "mining_calculation_accuracy", "FAIL", 
                        f"计算精确度测试异常: {str(e)}", security_score=0.0)
            return False
            
    def run_comprehensive_security_test(self) -> Dict[str, Any]:
        """运行综合安全测试"""
        logging.info("=" * 80)
        logging.info("开始综合安全回归测试")
        logging.info("Starting Comprehensive Security Regression Test")
        logging.info("=" * 80)
        
        start_time = time.time()
        
        # 测试未授权访问保护
        self.test_unauthorized_access_protection()
        
        # 测试无效邮箱拒绝
        self.test_invalid_email_rejection()
        
        # 测试法律合规页面
        self.test_legal_compliance_access()
        
        # 对每个测试邮箱进行全面测试
        for email in self.test_emails:
            logging.info(f"\n测试邮箱: {email}")
            
            # 认证安全测试
            self.test_authentication_security(email)
            
            # 会话管理测试
            self.test_session_management(email)
            
            # API认证测试
            self.test_api_authentication(email)
            
        # 数据一致性安全测试
        self.test_data_consistency_security()
        
        # 计算精确度安全测试
        self.test_calculation_accuracy_security()
        
        total_time = time.time() - start_time
        
        # 生成综合报告
        return self.generate_security_report(total_time)
        
    def generate_security_report(self, total_time: float) -> Dict[str, Any]:
        """生成安全测试报告"""
        # 统计测试结果
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r['status'] == 'PASS'])
        failed_tests = len([r for r in self.test_results if r['status'] == 'FAIL'])
        warning_tests = len([r for r in self.test_results if r['status'] == 'WARN'])
        
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        # 计算平均安全评分
        security_scores = [r['security_score'] for r in self.test_results if r['security_score'] is not None]
        avg_security_score = sum(security_scores) / len(security_scores) if security_scores else 0
        
        # 按类别统计
        categories = {}
        for result in self.test_results:
            category = result['category']
            if category not in categories:
                categories[category] = {'total': 0, 'passed': 0, 'failed': 0, 'warned': 0}
            categories[category]['total'] += 1
            if result['status'] == 'PASS':
                categories[category]['passed'] += 1
            elif result['status'] == 'FAIL':
                categories[category]['failed'] += 1
            elif result['status'] == 'WARN':
                categories[category]['warned'] += 1
                
        # 生成报告
        report = {
            "test_metadata": {
                "test_name": "Comprehensive Security Regression Test",
                "timestamp": datetime.now().isoformat(),
                "total_time_seconds": total_time,
                "test_emails": self.test_emails
            },
            "summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": failed_tests,
                "warning_tests": warning_tests,
                "success_rate_percent": success_rate,
                "average_security_score": avg_security_score,
                "system_grade": self.get_system_grade(success_rate, avg_security_score)
            },
            "category_breakdown": categories,
            "detailed_results": self.test_results,
            "security_assessment": self.assess_security_posture(success_rate, avg_security_score),
            "recommendations": self.generate_security_recommendations(categories)
        }
        
        # 保存报告
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"comprehensive_security_regression_test_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
            
        # 输出控制台报告
        self.print_security_report(report, filename)
        
        return report
        
    def get_system_grade(self, success_rate: float, security_score: float) -> str:
        """获取系统等级"""
        if success_rate >= 95 and security_score >= 95:
            return "A+ (完美级别)"
        elif success_rate >= 90 and security_score >= 90:
            return "A (优秀级别)"
        elif success_rate >= 80 and security_score >= 80:
            return "B+ (良好级别)"
        elif success_rate >= 70 and security_score >= 70:
            return "B (合格级别)"
        elif success_rate >= 60 and security_score >= 60:
            return "C+ (需改进)"
        else:
            return "C (有待改进)"
            
    def assess_security_posture(self, success_rate: float, security_score: float) -> Dict[str, Any]:
        """评估安全态势"""
        if success_rate >= 95 and security_score >= 95:
            risk_level = "极低风险"
            readiness = "生产就绪"
            confidence = "完全信任"
        elif success_rate >= 90 and security_score >= 90:
            risk_level = "低风险"
            readiness = "生产就绪"
            confidence = "高度信任"
        elif success_rate >= 80 and security_score >= 80:
            risk_level = "中等风险"
            readiness = "基本就绪"
            confidence = "较高信任"
        elif success_rate >= 70 and security_score >= 70:
            risk_level = "中高风险"
            readiness = "需要改进"
            confidence = "谨慎信任"
        else:
            risk_level = "高风险"
            readiness = "不建议生产"
            confidence = "需要修复"
            
        return {
            "risk_level": risk_level,
            "production_readiness": readiness,
            "confidence_level": confidence,
            "security_score": security_score,
            "success_rate": success_rate
        }
        
    def generate_security_recommendations(self, categories: Dict[str, Dict]) -> List[str]:
        """生成安全建议"""
        recommendations = []
        
        for category, stats in categories.items():
            pass_rate = (stats['passed'] / stats['total'] * 100) if stats['total'] > 0 else 0
            
            if pass_rate < 70:
                if category == "Authentication_Security":
                    recommendations.append(f"加强{category}：考虑添加多因素认证或更严格的邮箱验证")
                elif category == "Access_Control":
                    recommendations.append(f"改进{category}：增强访问控制机制和权限管理")
                elif category == "API_Authentication":
                    recommendations.append(f"优化{category}：添加API速率限制和更严格的认证")
                elif category == "Data_Consistency":
                    recommendations.append(f"修复{category}：确保数据在所有用户间保持一致")
                else:
                    recommendations.append(f"修复{category}：通过率仅{pass_rate:.1f}%，需要重点关注")
                    
        if len(recommendations) == 0:
            recommendations.append("安全测试表现excellent，系统安全性良好")
            
        return recommendations
        
    def print_security_report(self, report: Dict[str, Any], filename: str):
        """打印安全报告"""
        print("\n" + "=" * 100)
        print("综合安全回归测试报告")
        print("Comprehensive Security Regression Test Report")
        print("=" * 100)
        
        summary = report['summary']
        print(f"📊 测试概况:")
        print(f"   总测试数: {summary['total_tests']}")
        print(f"   通过测试: {summary['passed_tests']}")
        print(f"   失败测试: {summary['failed_tests']}")
        print(f"   警告测试: {summary['warning_tests']}")
        print(f"   成功率: {summary['success_rate_percent']:.1f}%")
        print(f"   平均安全评分: {summary['average_security_score']:.1f}/100")
        print(f"   系统等级: {summary['system_grade']}")
        
        print(f"\n📧 测试邮箱: {len(report['test_metadata']['test_emails'])}个")
        for email in report['test_metadata']['test_emails']:
            print(f"   ✅ {email}")
            
        print(f"\n🔍 安全模块测试:")
        for category, stats in report['category_breakdown'].items():
            pass_rate = (stats['passed'] / stats['total'] * 100) if stats['total'] > 0 else 0
            status_icon = "✅" if pass_rate >= 80 else "⚠️" if pass_rate >= 60 else "❌"
            print(f"   {status_icon} {category}: {stats['passed']}/{stats['total']} ({pass_rate:.1f}%)")
            
        print(f"\n🛡️ 安全态势评估:")
        security_assessment = report['security_assessment']
        print(f"   风险等级: {security_assessment['risk_level']}")
        print(f"   生产就绪度: {security_assessment['production_readiness']}")
        print(f"   信任程度: {security_assessment['confidence_level']}")
        
        print(f"\n💡 安全建议:")
        for i, recommendation in enumerate(report['recommendations'], 1):
            print(f"   {i}. {recommendation}")
            
        print(f"\n📄 详细报告已保存: {filename}")
        print(f"⏱️ 总测试时间: {report['test_metadata']['total_time_seconds']:.2f}秒")
        print("=" * 100)
        
def main():
    """主函数"""
    tester = ComprehensiveSecurityRegressionTest()
    report = tester.run_comprehensive_security_test()
    return report

if __name__ == "__main__":
    main()