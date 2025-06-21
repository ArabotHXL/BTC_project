#!/usr/bin/env python3
"""
修正版综合回归测试套件
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
from coinwarz_api import get_enhanced_network_data
from auth import verify_email, get_authorized_emails
from app import app

class CorrectedRegressionTest:
    """修正版回归测试套件"""
    
    def __init__(self):
        self.results = []
        self.passed = 0
        self.failed = 0
        self.start_time = datetime.now()
        
    def test_result(self, name, success, details="", error=None):
        """记录测试结果"""
        status = "PASS" if success else "FAIL"
        result = {
            'name': name,
            'status': status,
            'details': details,
            'error': str(error) if error else None,
            'time': datetime.now().isoformat()
        }
        self.results.append(result)
        
        if success:
            self.passed += 1
            print(f"✅ {name}: {status}")
        else:
            self.failed += 1
            print(f"❌ {name}: {status}")
            if error:
                print(f"   错误: {error}")
        
        if details:
            print(f"   详情: {details}")
    
    def test_core_calculator(self):
        """测试核心计算器功能"""
        try:
            result = calculate_mining_profitability(
                hashrate=100.0,
                power_consumption=3000,
                electricity_cost=0.05,
                btc_price=80000,
                difficulty=100.0,
                use_real_time_data=False
            )
            
            # 检查返回结构
            assert isinstance(result, dict), "结果应为字典"
            assert 'profit' in result, "应包含收益数据"
            assert 'daily' in result['profit'], "应包含日收益"
            
            daily_profit = result['profit']['daily']
            assert daily_profit > 0, "日收益应为正值"
            
            self.test_result("Core Calculator", True, f"日收益: ${daily_profit:.2f}")
            
        except Exception as e:
            self.test_result("Core Calculator", False, error=e)
    
    def test_roi_calculation(self):
        """测试ROI计算"""
        try:
            roi_data = calculate_roi(
                investment=100000,
                yearly_profit=50000,
                monthly_profit=4167,
                btc_price=80000
            )
            
            assert isinstance(roi_data, dict), "ROI数据应为字典"
            assert 'roi_percent_annual' in roi_data, "应包含年化ROI"
            assert 'payback_period_months' in roi_data, "应包含回本周期"
            
            roi = roi_data['roi_percent_annual']
            payback = roi_data['payback_period_months']
            
            self.test_result("ROI Calculation", True, 
                           f"ROI: {roi:.1f}%, 回本: {payback:.1f}月")
            
        except Exception as e:
            self.test_result("ROI Calculation", False, error=e)
    
    def test_api_connectivity(self):
        """测试API连接性"""
        try:
            # 测试BTC价格API
            btc_price = get_real_time_btc_price()
            assert isinstance(btc_price, (int, float)), "BTC价格应为数值"
            assert btc_price > 1000, "BTC价格应在合理范围"
            
            self.test_result("API Connectivity", True, f"BTC价格: ${btc_price:,.2f}")
            
        except Exception as e:
            self.test_result("API Connectivity", False, error=e)
    
    def test_network_data(self):
        """测试网络数据获取"""
        try:
            network_data = get_enhanced_network_data()
            assert isinstance(network_data, dict), "网络数据应为字典"
            
            required_fields = ['btc_price', 'difficulty', 'hashrate']
            for field in required_fields:
                assert field in network_data, f"缺少{field}字段"
                assert isinstance(network_data[field], (int, float)), f"{field}应为数值"
            
            self.test_result("Network Data", True, 
                           f"价格: ${network_data['btc_price']:,.2f}, "
                           f"难度: {network_data['difficulty']:.2f}T")
            
        except Exception as e:
            self.test_result("Network Data", False, error=e)
    
    def test_authentication(self):
        """测试认证系统"""
        try:
            authorized_emails = get_authorized_emails()
            assert isinstance(authorized_emails, list), "授权邮箱应为列表"
            assert len(authorized_emails) > 0, "应有授权邮箱"
            
            self.test_result("Authentication", True, 
                           f"授权邮箱数量: {len(authorized_emails)}")
            
        except Exception as e:
            self.test_result("Authentication", False, error=e)
    
    def test_web_application(self):
        """测试Web应用"""
        try:
            base_url = "http://localhost:5000"
            response = requests.get(f"{base_url}/login", timeout=10)
            assert response.status_code == 200, "登录页面应可访问"
            
            self.test_result("Web Application", True, "登录页面可访问")
            
        except Exception as e:
            self.test_result("Web Application", False, error=e)
    
    def test_multilingual(self):
        """测试多语言支持"""
        try:
            from translations import get_translation
            
            zh_text = get_translation('login', 'zh')
            en_text = get_translation('login', 'en')
            
            assert zh_text == '登录', "中文翻译正确"
            assert en_text == 'Login', "英文翻译正确"
            
            self.test_result("Multilingual", True, f"中文: {zh_text}, 英文: {en_text}")
            
        except Exception as e:
            self.test_result("Multilingual", False, error=e)
    
    def test_database_connection(self):
        """测试数据库连接"""
        try:
            # 直接使用app中已初始化的数据库连接
            with app.app_context():
                # 使用app中已经初始化的数据库
                from app import db
                from sqlalchemy import text
                
                # 测试数据库连接
                result = db.session.execute(text("SELECT 1")).scalar()
                assert result == 1, "数据库连接应正常"
                
                # 测试一个简单的表查询
                table_count = db.session.execute(
                    text("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'")
                ).scalar()
                
                self.test_result("Database Connection", True, 
                               f"数据库连接正常，发现 {table_count} 个表")
                
        except Exception as e:
            self.test_result("Database Connection", False, error=e)
    
    def test_curtailment_calculator(self):
        """测试电力削减计算器"""
        try:
            miners_data = [
                {"model": "Antminer S19 Pro", "count": 10},
                {"model": "Antminer S21", "count": 5}
            ]
            
            result = calculate_monthly_curtailment_impact(
                miners_data=miners_data,
                curtailment_percentage=20,
                electricity_cost=0.05,
                btc_price=80000,
                network_difficulty=100.0
            )
            
            assert isinstance(result, dict), "削减结果应为字典"
            assert 'impact' in result, "应包含影响数据"
            
            self.test_result("Curtailment Calculator", True, "削减计算正常")
            
        except Exception as e:
            self.test_result("Curtailment Calculator", False, error=e)
    
    def run_all_tests(self):
        """运行所有测试"""
        print("=== 开始修正版回归测试 ===")
        print(f"开始时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # 运行所有测试
        tests = [
            self.test_core_calculator,
            self.test_roi_calculation,
            self.test_api_connectivity,
            self.test_network_data,
            self.test_authentication,
            self.test_database_connection,
            self.test_multilingual,
            self.test_curtailment_calculator,
            self.test_web_application
        ]
        
        for test in tests:
            try:
                test()
            except Exception as e:
                print(f"❌ 测试执行失败: {e}")
        
        # 生成报告
        self.generate_report()
    
    def generate_report(self):
        """生成测试报告"""
        end_time = datetime.now()
        duration = end_time - self.start_time
        
        print("\n" + "="*50)
        print("回归测试报告")
        print("="*50)
        print(f"开始时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"结束时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"总耗时: {duration.total_seconds():.2f}秒")
        print()
        print(f"✅ 通过: {self.passed}")
        print(f"❌ 失败: {self.failed}")
        print(f"📊 总计: {len(self.results)}")
        
        if len(self.results) > 0:
            success_rate = (self.passed / len(self.results)) * 100
            print(f"🎯 成功率: {success_rate:.1f}%")
        
        if self.failed > 0:
            print("\n失败的测试:")
            for result in self.results:
                if result['status'] == 'FAIL':
                    print(f"  - {result['name']}: {result['error']}")
        
        # 保存报告
        try:
            os.makedirs('tests/reports', exist_ok=True)
            report_file = f"tests/reports/regression_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            report_data = {
                'summary': {
                    'start_time': self.start_time.isoformat(),
                    'end_time': end_time.isoformat(),
                    'duration': duration.total_seconds(),
                    'passed': self.passed,
                    'failed': self.failed,
                    'total': len(self.results),
                    'success_rate': (self.passed / len(self.results)) * 100 if self.results else 0
                },
                'results': self.results
            }
            
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False)
            
            print(f"\n📋 详细报告已保存: {report_file}")
            
        except Exception as e:
            print(f"保存报告失败: {e}")
        
        return self.failed == 0

def main():
    """主函数"""
    tester = CorrectedRegressionTest()
    success = tester.run_all_tests()
    
    if success:
        print("\n🎉 所有测试通过！系统运行正常。")
        return 0
    else:
        print("\n⚠️ 部分测试失败，需要检查相关功能。")
        return 1

if __name__ == "__main__":
    exit(main())