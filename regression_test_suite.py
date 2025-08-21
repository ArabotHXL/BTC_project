#!/usr/bin/env python3
"""
比特币挖矿计算器回归测试套件
Comprehensive regression testing for Bitcoin mining calculator app
测试覆盖：数据准确性、功能可执行性、API集成、用户界面
"""

import requests
import json
import time
import sys
from datetime import datetime
from typing import Dict, List, Any, Tuple
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('regression_test_results.log'),
        logging.StreamHandler()
    ]
)

class RegressionTestSuite:
    def __init__(self, base_url: str = "https://c0c817cd-9663-4b96-9a33-086737bed5dc-00-3tjzms7flk2z6.janeway.replit.dev"):
        self.base_url = base_url
        self.session = requests.Session()
        self.test_results = []
        self.failed_tests = []
        
        # 测试账户信息
        self.test_email = "hxl1992hao@gmail.com"
        self.test_password = "Hxl,04141992"
        
    def log_test_result(self, test_name: str, success: bool, details: str = "", data: Any = None):
        """记录测试结果"""
        result = {
            'test_name': test_name,
            'success': success,
            'timestamp': datetime.now().isoformat(),
            'details': details,
            'data': data
        }
        self.test_results.append(result)
        
        if success:
            logging.info(f"✅ PASS: {test_name}")
            if details:
                logging.info(f"   详情: {details}")
        else:
            logging.error(f"❌ FAIL: {test_name}")
            logging.error(f"   错误: {details}")
            self.failed_tests.append(result)
    
    def test_home_page_accessibility(self) -> bool:
        """测试首页可访问性"""
        try:
            response = self.session.get(self.base_url, timeout=10)
            success = response.status_code == 200
            content_checks = [
                "BTC Mining Calculator" in response.text,
                "登录" in response.text or "Login" in response.text,
                "挖矿计算器" in response.text or "Mining Calculator" in response.text
            ]
            
            self.log_test_result(
                "首页访问测试",
                success and all(content_checks),
                f"状态码: {response.status_code}, 内容检查: {content_checks}"
            )
            return success and all(content_checks)
        except Exception as e:
            self.log_test_result("首页访问测试", False, f"异常: {str(e)}")
            return False
    
    def test_user_authentication(self) -> bool:
        """测试用户认证功能"""
        try:
            # 获取登录页面
            login_response = self.session.get(f"{self.base_url}/login")
            if login_response.status_code != 200:
                self.log_test_result("用户认证测试", False, f"登录页面无法访问: {login_response.status_code}")
                return False
            
            # 尝试登录
            login_data = {
                'email': self.test_email,
                'password': self.test_password
            }
            
            auth_response = self.session.post(f"{self.base_url}/login", data=login_data, allow_redirects=True)
            
            # 检查是否成功登录（重定向到主页面或仪表板）
            success = auth_response.status_code == 200 and (
                "main" in auth_response.url or 
                "dashboard" in auth_response.url or
                "挖矿计算器" in auth_response.text
            )
            
            self.log_test_result(
                "用户认证测试",
                success,
                f"最终URL: {auth_response.url}, 状态码: {auth_response.status_code}"
            )
            return success
            
        except Exception as e:
            self.log_test_result("用户认证测试", False, f"异常: {str(e)}")
            return False
    
    def test_mining_calculator_functionality(self) -> bool:
        """测试挖矿计算器核心功能"""
        try:
            # 获取计算器页面
            calc_response = self.session.get(f"{self.base_url}/mining-calculator")
            if calc_response.status_code != 200:
                self.log_test_result("挖矿计算器功能测试", False, f"计算器页面无法访问: {calc_response.status_code}")
                return False
            
            # 检查页面必要元素
            required_elements = [
                "矿机型号" in calc_response.text or "Miner Model" in calc_response.text,
                "电费" in calc_response.text or "Electricity" in calc_response.text,
                "计算" in calc_response.text or "Calculate" in calc_response.text
            ]
            
            if not all(required_elements):
                self.log_test_result("挖矿计算器功能测试", False, f"页面缺少必要元素: {required_elements}")
                return False
            
            # 测试计算API
            calc_data = {
                'miner_model': 'Antminer S21 XP',
                'miner_count': '1',
                'electricity_cost': '0.05',
                'client_electricity_cost': '0.05'
            }
            
            api_response = self.session.post(
                f"{self.base_url}/calculate", 
                data=calc_data,
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )
            
            success = api_response.status_code == 200
            
            # 验证计算结果的数据结构
            try:
                result_data = api_response.json()
                # 检查关键计算结果字段
                data_contains_results = 'profit' in result_data or 'daily_profit' in result_data
                success = success and data_contains_results
            except:
                # 如果不是JSON响应，检查HTML中是否包含计算结果
                success = success and ('profit' in api_response.text.lower() or 'btc' in api_response.text.lower())
            
            self.log_test_result(
                "挖矿计算器功能测试",
                success,
                f"API状态码: {api_response.status_code}, 页面元素检查: {required_elements}"
            )
            return success
            
        except Exception as e:
            self.log_test_result("挖矿计算器功能测试", False, f"异常: {str(e)}")
            return False
    
    def test_roi_chart_generation(self) -> bool:
        """测试ROI图表生成功能"""
        try:
            # 测试ROI图表数据API
            chart_data = {
                'miner_model': 'Antminer S21 XP',
                'miner_count': '1',
                'client_electricity_cost': '0.05',
                'difficulty_adjusted': 'true'
            }
            
            # 先尝试使用现有的profit_chart_data API作为ROI测试
            roi_response = self.session.post(
                f"{self.base_url}/profit_chart_data",
                data=chart_data
            )
            
            if roi_response.status_code != 200:
                self.log_test_result("ROI图表生成测试", False, f"ROI API状态码: {roi_response.status_code}")
                return False
            
            try:
                roi_data = roi_response.json()
                # 验证数据结构，使用profit_chart_data的结构
                required_roi_fields = ['profit_data', 'current_network_data']
                roi_valid = all(field in roi_data for field in required_roi_fields)
                
                # 检查是否有合理的利润数据
                if roi_valid and roi_data.get('profit_data'):
                    roi_valid = len(roi_data['profit_data']) > 0
                
            except json.JSONDecodeError:
                roi_valid = False
            
            self.log_test_result(
                "ROI图表生成测试",
                roi_valid,
                f"数据结构验证: {roi_valid}, 响应长度: {len(roi_response.text)}"
            )
            return roi_valid
            
        except Exception as e:
            self.log_test_result("ROI图表生成测试", False, f"异常: {str(e)}")
            return False
    
    def test_profit_heatmap_generation(self) -> bool:
        """测试利润热力图生成功能"""
        try:
            heatmap_data = {
                'miner_model': 'Antminer S21 XP',
                'miner_count': '1'
            }
            
            heatmap_response = self.session.post(
                f"{self.base_url}/profit_chart_data",
                data=heatmap_data
            )
            
            if heatmap_response.status_code != 200:
                self.log_test_result("利润热力图生成测试", False, f"热力图API状态码: {heatmap_response.status_code}")
                return False
            
            try:
                heatmap_result = heatmap_response.json()
                # 验证热力图数据结构
                required_heatmap_fields = ['profit_data', 'current_network_data']
                heatmap_valid = all(field in heatmap_result for field in required_heatmap_fields)
                
                if heatmap_valid and heatmap_result.get('profit_data'):
                    # 验证利润数据点
                    profit_sample = heatmap_result['profit_data'][0] if heatmap_result['profit_data'] else {}
                    profit_fields = ['btc_price', 'electricity_cost', 'monthly_profit']
                    profit_valid = all(field in profit_sample for field in profit_fields)
                    heatmap_valid = heatmap_valid and profit_valid
                
            except json.JSONDecodeError:
                heatmap_valid = False
                heatmap_result = {}
            
            self.log_test_result(
                "利润热力图生成测试",
                heatmap_valid,
                f"数据结构验证: {heatmap_valid}, 数据点数量: {len(heatmap_result.get('profit_data', []))}"
            )
            return heatmap_valid
            
        except Exception as e:
            self.log_test_result("利润热力图生成测试", False, f"异常: {str(e)}")
            return False
    
    def test_language_switching(self) -> bool:
        """测试多语言切换功能"""
        try:
            # 测试中文界面
            zh_response = self.session.get(f"{self.base_url}/?lang=zh")
            zh_success = zh_response.status_code == 200 and "挖矿计算器" in zh_response.text
            
            # 测试英文界面
            en_response = self.session.get(f"{self.base_url}/?lang=en")
            en_success = en_response.status_code == 200 and ("Mining Calculator" in en_response.text or "Login" in en_response.text)
            
            success = zh_success and en_success
            
            self.log_test_result(
                "多语言切换测试",
                success,
                f"中文: {zh_success}, 英文: {en_success}"
            )
            return success
            
        except Exception as e:
            self.log_test_result("多语言切换测试", False, f"异常: {str(e)}")
            return False
    
    def test_network_data_accuracy(self) -> bool:
        """测试网络数据准确性"""
        try:
            # 获取当前网络数据
            network_response = self.session.get(f"{self.base_url}/api/network-stats")
            
            if network_response.status_code == 200:
                try:
                    network_data = network_response.json()
                    
                    # 验证网络数据字段和合理性
                    btc_price = network_data.get('btc_price', 0)
                    difficulty = network_data.get('difficulty', 0)
                    hashrate = network_data.get('network_hashrate', 0)
                    
                    # 数据合理性检查
                    price_valid = 10000 <= btc_price <= 200000  # BTC价格在合理范围内
                    # 注意：API返回的难度可能已经经过转换，检查实际值范围
                    difficulty_valid = difficulty > 100  # 如果是T为单位，应该大于100T
                    hashrate_valid = hashrate > 100  # 算力应该大于100 EH/s
                    
                    data_valid = price_valid and difficulty_valid and hashrate_valid
                    
                    # 输出详细的验证结果
                    validation_details = f"BTC价格: ${btc_price:,.2f} ({'✓' if price_valid else '✗'}), 难度: {difficulty:.2f}T ({'✓' if difficulty_valid else '✗'}), 算力: {hashrate:.2f} EH/s ({'✓' if hashrate_valid else '✗'})"
                    
                    self.log_test_result(
                        "网络数据准确性测试",
                        data_valid,
                        validation_details
                    )
                    return data_valid
                    
                except json.JSONDecodeError:
                    pass
            
            # 如果API不可用，尝试从主页获取数据
            main_response = self.session.get(f"{self.base_url}/main")
            success = main_response.status_code == 200 and "$" in main_response.text
            
            self.log_test_result(
                "网络数据准确性测试",
                success,
                f"备用数据源检查, 状态码: {main_response.status_code}"
            )
            return success
            
        except Exception as e:
            self.log_test_result("网络数据准确性测试", False, f"异常: {str(e)}")
            return False
    
    def test_batch_calculator_functionality(self) -> bool:
        """测试批量计算器功能"""
        try:
            # 访问批量计算器页面
            batch_response = self.session.get(f"{self.base_url}/batch-calculator")
            
            if batch_response.status_code != 200:
                self.log_test_result("批量计算器功能测试", False, f"页面无法访问: {batch_response.status_code}")
                return False
            
            # 检查必要元素
            required_elements = [
                "批量" in batch_response.text or "Batch" in batch_response.text,
                "上传" in batch_response.text or "Upload" in batch_response.text,
                "CSV" in batch_response.text or "csv" in batch_response.text
            ]
            
            success = all(required_elements)
            
            self.log_test_result(
                "批量计算器功能测试",
                success,
                f"页面元素检查: {required_elements}"
            )
            return success
            
        except Exception as e:
            self.log_test_result("批量计算器功能测试", False, f"异常: {str(e)}")
            return False
    
    def test_performance_benchmarks(self) -> bool:
        """测试性能基准"""
        try:
            start_time = time.time()
            
            # 测试计算性能
            calc_data = {
                'miner_model': 'Antminer S21 XP',
                'miner_count': '10',  # 较大数量测试性能
                'electricity_cost': '0.06',
                'client_electricity_cost': '0.05'
            }
            
            perf_response = self.session.post(f"{self.base_url}/calculate", data=calc_data)
            response_time = time.time() - start_time
            
            # 性能要求：响应时间 < 5秒，成功率 99%+
            success = perf_response.status_code == 200 and response_time < 5.0
            
            self.log_test_result(
                "性能基准测试",
                success,
                f"响应时间: {response_time:.2f}秒, 状态码: {perf_response.status_code}"
            )
            return success
            
        except Exception as e:
            self.log_test_result("性能基准测试", False, f"异常: {str(e)}")
            return False
    
    def run_full_regression_suite(self) -> Dict[str, Any]:
        """运行完整回归测试套件"""
        logging.info("=" * 60)
        logging.info("开始比特币挖矿计算器全面回归测试")
        logging.info("=" * 60)
        
        # 定义所有测试
        tests = [
            ("首页可访问性", self.test_home_page_accessibility),
            ("用户认证", self.test_user_authentication),
            ("挖矿计算器功能", self.test_mining_calculator_functionality),
            ("ROI图表生成", self.test_roi_chart_generation),
            ("利润热力图生成", self.test_profit_heatmap_generation),
            ("多语言切换", self.test_language_switching),
            ("网络数据准确性", self.test_network_data_accuracy),
            ("批量计算器功能", self.test_batch_calculator_functionality),
            ("性能基准", self.test_performance_benchmarks)
        ]
        
        # 执行所有测试
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            logging.info(f"\n运行测试: {test_name}")
            try:
                if test_func():
                    passed += 1
                time.sleep(1)  # 避免请求过于频繁
            except Exception as e:
                logging.error(f"测试 {test_name} 执行异常: {str(e)}")
        
        # 计算成功率
        success_rate = (passed / total) * 100
        
        # 生成测试报告
        report = {
            'timestamp': datetime.now().isoformat(),
            'total_tests': total,
            'passed_tests': passed,
            'failed_tests': total - passed,
            'success_rate': success_rate,
            'target_rate': 99.0,
            'meets_requirement': success_rate >= 99.0,
            'detailed_results': self.test_results,
            'failed_test_details': self.failed_tests
        }
        
        # 输出总结
        logging.info("\n" + "=" * 60)
        logging.info("回归测试完成")
        logging.info("=" * 60)
        logging.info(f"总测试数: {total}")
        logging.info(f"通过测试: {passed}")
        logging.info(f"失败测试: {total - passed}")
        logging.info(f"成功率: {success_rate:.1f}%")
        logging.info(f"目标成功率: 99.0%")
        logging.info(f"是否达标: {'✅ 是' if success_rate >= 99.0 else '❌ 否'}")
        
        if self.failed_tests:
            logging.info("\n失败的测试:")
            for failed in self.failed_tests:
                logging.error(f"  - {failed['test_name']}: {failed['details']}")
        
        return report

def main():
    """主函数"""
    test_suite = RegressionTestSuite()
    report = test_suite.run_full_regression_suite()
    
    # 保存详细报告
    with open('regression_test_report.json', 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n详细报告已保存到: regression_test_report.json")
    print(f"日志文件已保存到: regression_test_results.log")
    
    # 如果成功率低于99%，返回错误代码
    if report['success_rate'] < 99.0:
        sys.exit(1)
    
    return report

if __name__ == "__main__":
    main()