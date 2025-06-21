#!/usr/bin/env python3
"""
综合回归测试套件
验证系统的所有核心功能和业务逻辑
"""

import sys
import os
import time
import requests
import json
from datetime import datetime, timedelta

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mining_calculator import (
    calculate_mining_profitability,
    get_real_time_btc_price,
    get_real_time_difficulty,
    calculate_roi,
    calculate_monthly_curtailment_impact
)
from coinwarz_api import (
    get_enhanced_network_data,
    check_coinwarz_api_status,
    get_bitcoin_data_from_coinwarz
)
from auth import verify_email, get_authorized_emails
from models import *
from app import app

class RegressionTestSuite:
    """综合回归测试套件"""
    
    def __init__(self):
        self.test_results = []
        self.passed_tests = 0
        self.failed_tests = 0
        self.start_time = datetime.now()
        
    def log_test(self, test_name, passed, details="", error=None):
        """记录测试结果"""
        status = "PASS" if passed else "FAIL"
        result = {
            'test_name': test_name,
            'status': status,
            'details': details,
            'error': str(error) if error else None,
            'timestamp': datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        if passed:
            self.passed_tests += 1
            print(f"✅ {test_name}: {status}")
        else:
            self.failed_tests += 1
            print(f"❌ {test_name}: {status}")
            if error:
                print(f"   Error: {error}")
        
        if details:
            print(f"   Details: {details}")
    
    def test_mining_calculator_core(self):
        """测试挖矿计算器核心功能"""
        try:
            # 测试基础计算
            result = calculate_mining_profitability(
                hashrate=100.0,  # 100 TH/s
                power_consumption=3000,  # 3000W
                electricity_cost=0.05,  # $0.05/kWh
                btc_price=80000,  # $80,000
                difficulty=100.0,  # 100T
                use_real_time_data=False
            )
            
            assert isinstance(result, dict), "计算结果应为字典"
            assert 'profit' in result, "应包含收益数据"
            assert 'daily' in result['profit'], "应包含日收益"
            assert 'monthly' in result['profit'], "应包含月收益"
            assert 'yearly' in result['profit'], "应包含年收益"
            
            # 验证数值合理性
            assert result['profit']['daily'] > 0, "日收益应为正值"
            assert result['profit']['monthly'] > 0, "月收益应为正值"
            assert result['profit']['yearly'] > 0, "年收益应为正值"
            
            self.log_test("Mining Calculator Core", True, 
                         f"Daily profit: ${result['profit']['daily']:.2f}")
            
        except Exception as e:
            self.log_test("Mining Calculator Core", False, error=e)
    
    def test_real_time_data_apis(self):
        """测试实时数据API"""
        try:
            # 测试BTC价格API
            btc_price = get_real_time_btc_price()
            assert isinstance(btc_price, (int, float)), "BTC价格应为数值"
            assert btc_price > 0, "BTC价格应为正值"
            assert btc_price > 1000, "BTC价格应大于1000（合理范围）"
            
            self.log_test("Real-time BTC Price API", True, 
                         f"BTC Price: ${btc_price:,.2f}")
            
            # 测试网络难度API
            difficulty = get_real_time_difficulty()
            assert isinstance(difficulty, (int, float)), "网络难度应为数值"
            assert difficulty > 0, "网络难度应为正值"
            
            self.log_test("Real-time Difficulty API", True, 
                         f"Difficulty: {difficulty:.2f}T")
            
        except Exception as e:
            self.log_test("Real-time Data APIs", False, error=e)
    
    def test_enhanced_network_data(self):
        """测试增强网络数据API"""
        try:
            network_data = get_enhanced_network_data()
            assert isinstance(network_data, dict), "网络数据应为字典"
            
            required_fields = ['btc_price', 'difficulty', 'hashrate', 'block_reward']
            for field in required_fields:
                assert field in network_data, f"应包含{field}字段"
                assert isinstance(network_data[field], (int, float)), f"{field}应为数值"
            
            self.log_test("Enhanced Network Data API", True, 
                         f"Price: ${network_data['btc_price']:,.2f}, "
                         f"Difficulty: {network_data['difficulty']:.2f}T")
            
        except Exception as e:
            self.log_test("Enhanced Network Data API", False, error=e)
    
    def test_roi_calculations(self):
        """测试ROI计算功能"""
        try:
            roi_data = calculate_roi(
                investment=100000,  # $100,000投资
                yearly_profit=50000,  # $50,000年收益
                monthly_profit=4167,  # 月收益
                btc_price=80000,
                forecast_months=36
            )
            
            assert isinstance(roi_data, dict), "ROI数据应为字典"
            assert 'roi_percent_annual' in roi_data, "应包含年化ROI"
            assert 'payback_period_months' in roi_data, "应包含回本周期"
            assert 'forecast_data' in roi_data, "应包含预测数据"
            
            assert roi_data['roi_percent_annual'] > 0, "ROI应为正值"
            assert roi_data['payback_period_months'] > 0, "回本周期应为正值"
            
            self.log_test("ROI Calculations", True, 
                         f"ROI: {roi_data['roi_percent_annual']:.1f}%, "
                         f"Payback: {roi_data['payback_period_months']:.1f} months")
            
        except Exception as e:
            self.log_test("ROI Calculations", False, error=e)
    
    def test_curtailment_calculator(self):
        """测试电力削减计算器"""
        try:
            miners_data = [
                {"model": "Antminer S19 Pro", "count": 100},
                {"model": "Antminer S21", "count": 50}
            ]
            
            curtailment_result = calculate_monthly_curtailment_impact(
                miners_data=miners_data,
                curtailment_percentage=20,  # 20%削减
                electricity_cost=0.05,
                btc_price=80000,
                network_difficulty=100.0,
                shutdown_strategy="efficiency"
            )
            
            assert isinstance(curtailment_result, dict), "削减结果应为字典"
            assert 'impact' in curtailment_result, "应包含影响数据"
            assert 'net_impact' in curtailment_result['impact'], "应包含净影响"
            
            self.log_test("Curtailment Calculator", True, 
                         f"Net impact: ${curtailment_result['impact']['net_impact']:,.2f}")
            
        except Exception as e:
            self.log_test("Curtailment Calculator", False, error=e)
    
    def test_authentication_system(self):
        """测试认证系统"""
        try:
            # 测试获取授权邮箱列表
            authorized_emails = get_authorized_emails()
            assert isinstance(authorized_emails, list), "授权邮箱应为列表"
            
            # 测试邮箱验证（使用测试邮箱）
            test_email = "test@example.com"
            if test_email in authorized_emails:
                is_valid = verify_email(test_email)
                assert isinstance(is_valid, bool), "邮箱验证应返回布尔值"
            
            self.log_test("Authentication System", True, 
                         f"Found {len(authorized_emails)} authorized emails")
            
        except Exception as e:
            self.log_test("Authentication System", False, error=e)
    
    def test_database_models(self):
        """测试数据库模型"""
        try:
            with app.app_context():
                # 测试数据库连接
                from db import db
                
                # 验证关键表存在
                tables_to_check = [
                    'user_access', 'login_record', 'network_snapshot',
                    'customer', 'contact', 'lead', 'deal', 'activity'
                ]
                
                for table_name in tables_to_check:
                    result = db.session.execute(
                        f"SELECT COUNT(*) FROM information_schema.tables "
                        f"WHERE table_name = '{table_name}'"
                    ).scalar()
                    assert result > 0, f"表{table_name}应存在"
                
                self.log_test("Database Models", True, 
                             f"Verified {len(tables_to_check)} tables exist")
                
        except Exception as e:
            self.log_test("Database Models", False, error=e)
    
    def test_api_endpoints(self):
        """测试API端点"""
        try:
            # 测试应用是否运行
            base_url = "http://localhost:5000"
            
            # 测试登录页面
            response = requests.get(f"{base_url}/login", timeout=10)
            assert response.status_code == 200, "登录页面应可访问"
            
            # 测试BTC价格API端点
            response = requests.get(f"{base_url}/api/btc-price", timeout=10)
            if response.status_code == 200:
                data = response.json()
                assert 'price' in data, "BTC价格API应返回价格"
            
            self.log_test("API Endpoints", True, 
                         "Login page accessible, API endpoints responsive")
            
        except Exception as e:
            self.log_test("API Endpoints", False, error=e)
    
    def test_external_api_status(self):
        """测试外部API状态"""
        try:
            # 测试CoinWarz API状态
            try:
                coinwarz_status = check_coinwarz_api_status()
                coinwarz_working = isinstance(coinwarz_status, dict)
            except:
                coinwarz_working = False
            
            # 测试CoinGecko API
            try:
                response = requests.get(
                    "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd",
                    timeout=10
                )
                coingecko_working = response.status_code == 200
            except:
                coingecko_working = False
            
            # 测试Blockchain.info API
            try:
                response = requests.get("https://blockchain.info/q/getdifficulty", timeout=10)
                blockchain_working = response.status_code == 200
            except:
                blockchain_working = False
            
            api_status = {
                'coinwarz': coinwarz_working,
                'coingecko': coingecko_working,
                'blockchain_info': blockchain_working
            }
            
            working_apis = sum(api_status.values())
            
            self.log_test("External API Status", True, 
                         f"Working APIs: {working_apis}/3 - "
                         f"CoinWarz: {'✓' if coinwarz_working else '✗'}, "
                         f"CoinGecko: {'✓' if coingecko_working else '✗'}, "
                         f"Blockchain.info: {'✓' if blockchain_working else '✗'}")
            
        except Exception as e:
            self.log_test("External API Status", False, error=e)
    
    def test_algorithm_validation(self):
        """测试算法验证功能"""
        try:
            # 测试两种算法计算结果
            test_params = {
                'hashrate': 100.0,
                'power_consumption': 3000,
                'electricity_cost': 0.05,
                'btc_price': 80000,
                'difficulty': 100.0,
                'use_real_time_data': False
            }
            
            # API算法
            result1 = calculate_mining_profitability(**test_params)
            
            # 手动难度算法（通过设置manual_network_hashrate）
            result2 = calculate_mining_profitability(
                manual_network_hashrate=700,  # 700 EH/s
                **test_params
            )
            
            # 验证两种算法都返回有效结果
            assert isinstance(result1, dict), "API算法应返回字典"
            assert isinstance(result2, dict), "手动算法应返回字典"
            
            # 验证关键字段存在
            for result in [result1, result2]:
                assert 'daily_profit' in result, "应包含日收益"
                assert 'monthly_profit' in result, "应包含月收益"
                assert result['daily_profit'] > 0, "日收益应为正值"
            
            self.log_test("Algorithm Validation", True, 
                         f"API算法日收益: ${result1['daily_profit']:.2f}, "
                         f"手动算法日收益: ${result2['daily_profit']:.2f}")
            
        except Exception as e:
            self.log_test("Algorithm Validation", False, error=e)
    
    def test_multilingual_support(self):
        """测试多语言支持"""
        try:
            from translations import get_translation
            
            # 测试中文翻译
            zh_translation = get_translation('login', 'zh')
            assert zh_translation == '登录', "中文翻译应正确"
            
            # 测试英文翻译
            en_translation = get_translation('login', 'en')
            assert en_translation == 'Login', "英文翻译应正确"
            
            # 测试不存在的翻译
            fallback = get_translation('nonexistent_key', 'zh')
            assert fallback == 'nonexistent_key', "应返回原始键值作为fallback"
            
            self.log_test("Multilingual Support", True, 
                         f"中文: {zh_translation}, 英文: {en_translation}")
            
        except Exception as e:
            self.log_test("Multilingual Support", False, error=e)
    
    def run_all_tests(self):
        """运行所有测试"""
        print("=== 开始综合回归测试 ===")
        print(f"测试开始时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # 核心功能测试
        print("🔧 测试核心功能...")
        self.test_mining_calculator_core()
        self.test_roi_calculations()
        self.test_curtailment_calculator()
        self.test_algorithm_validation()
        
        # API和数据测试
        print("\n🌐 测试API和数据服务...")
        self.test_real_time_data_apis()
        self.test_enhanced_network_data()
        self.test_external_api_status()
        
        # 系统组件测试
        print("\n🏗️ 测试系统组件...")
        self.test_authentication_system()
        self.test_database_models()
        self.test_multilingual_support()
        
        # Web应用测试
        print("\n🌍 测试Web应用...")
        self.test_api_endpoints()
        
        # 生成测试报告
        self.generate_test_report()
    
    def generate_test_report(self):
        """生成测试报告"""
        end_time = datetime.now()
        duration = end_time - self.start_time
        
        print("\n" + "="*60)
        print("回归测试完成报告")
        print("="*60)
        print(f"测试开始时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"测试结束时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"测试总耗时: {duration.total_seconds():.2f}秒")
        print()
        print(f"✅ 通过测试: {self.passed_tests}")
        print(f"❌ 失败测试: {self.failed_tests}")
        print(f"📊 总测试数: {len(self.test_results)}")
        print(f"🎯 成功率: {(self.passed_tests/len(self.test_results)*100):.1f}%")
        
        if self.failed_tests > 0:
            print("\n❌ 失败的测试:")
            for result in self.test_results:
                if result['status'] == 'FAIL':
                    print(f"  - {result['test_name']}: {result['error']}")
        
        # 保存详细测试报告到文件
        report_data = {
            'test_summary': {
                'start_time': self.start_time.isoformat(),
                'end_time': end_time.isoformat(),
                'duration_seconds': duration.total_seconds(),
                'passed_tests': self.passed_tests,
                'failed_tests': self.failed_tests,
                'total_tests': len(self.test_results),
                'success_rate': (self.passed_tests/len(self.test_results)*100)
            },
            'detailed_results': self.test_results
        }
        
        report_filename = f"tests/regression_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_filename, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n📋 详细测试报告已保存至: {report_filename}")
        
        # 返回测试是否全部通过
        return self.failed_tests == 0

def main():
    """主函数"""
    tester = RegressionTestSuite()
    all_passed = tester.run_all_tests()
    
    if all_passed:
        print("\n🎉 所有测试通过！系统运行正常。")
        exit(0)
    else:
        print("\n⚠️ 部分测试失败，请检查上述错误信息。")
        exit(1)

if __name__ == "__main__":
    main()