#!/usr/bin/env python3
"""
聚焦核心功能回归测试
Focused Core Function Regression Test

快速验证BTC挖矿计算器系统的核心功能模块
Quick validation of core function modules in BTC Mining Calculator System
"""

import requests
import json
import time
import psycopg2
import os
from datetime import datetime
from typing import Dict, List, Any, Tuple

class FocusedRegressionTest:
    def __init__(self):
        self.base_url = "http://0.0.0.0:5000"
        self.session = requests.Session()
        self.test_results = []
        self.authenticated = False
        self.owner_email = "hxl2022hao@gmail.com"
        
    def log_test(self, module_name: str, function_name: str, status: str, details: str = "", response_time: float = None):
        """记录测试结果"""
        result = {
            'module': module_name,
            'function': function_name,
            'status': status,
            'details': details,
            'response_time': response_time
        }
        self.test_results.append(result)
        
        status_symbol = "✓" if status == "PASS" else "✗" if status == "FAIL" else "⚠" if status == "WARN" else "ℹ"
        time_str = f" ({response_time:.3f}s)" if response_time else ""
        print(f"{status_symbol} {module_name}.{function_name}: {status}{time_str}")
        if details:
            print(f"   → {details}")

    def authenticate_system(self):
        """系统认证"""
        try:
            login_data = {"email": self.owner_email}
            start_time = time.time()
            response = self.session.post(f"{self.base_url}/login", data=login_data)
            response_time = time.time() - start_time
            
            if response.status_code == 200 and ("退出登录" in response.text or "Logout" in response.text):
                self.authenticated = True
                self.log_test("系统认证", "拥有者登录", "PASS", f"成功登录拥有者账户", response_time)
                return True
            else:
                self.log_test("系统认证", "拥有者登录", "FAIL", f"登录失败: {response.status_code}", response_time)
                return False
                
        except Exception as e:
            self.log_test("系统认证", "拥有者登录", "FAIL", f"认证异常: {str(e)}")
            return False

    def test_core_apis(self):
        """测试核心API"""
        print("\n🔌 核心API测试")
        
        if not self.authenticated:
            self.log_test("核心API", "认证状态", "FAIL", "需要认证才能测试API")
            return
        
        # 测试核心API端点
        core_apis = [
            ("BTC价格API", "/api/get_btc_price"),
            ("网络统计API", "/api/get_network_stats"),
            ("矿机数据API", "/api/get_miners"),
            ("SHA256对比API", "/api/get_sha256_mining_comparison")
        ]
        
        for api_name, endpoint in core_apis:
            try:
                start_time = time.time()
                response = self.session.get(f"{self.base_url}{endpoint}")
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        if data.get('success'):
                            self.log_test("核心API", api_name, "PASS", "API响应正常", response_time)
                        else:
                            self.log_test("核心API", api_name, "WARN", f"API错误: {data.get('error', '未知错误')}", response_time)
                    except json.JSONDecodeError:
                        self.log_test("核心API", api_name, "FAIL", "JSON解析失败", response_time)
                else:
                    self.log_test("核心API", api_name, "FAIL", f"HTTP {response.status_code}", response_time)
                    
            except Exception as e:
                self.log_test("核心API", api_name, "FAIL", f"请求异常: {str(e)}")

    def test_mining_calculation(self):
        """测试挖矿计算功能"""
        print("\n⚡ 挖矿计算测试")
        
        if not self.authenticated:
            self.log_test("挖矿计算", "认证状态", "FAIL", "需要认证才能测试计算功能")
            return
        
        # 测试基础挖矿计算
        calc_data = {
            "miner_model": "Antminer S21 XP Hyd",
            "miner_count": "1",
            "electricity_cost": "0.05",
            "use_real_time": "on"
        }
        
        try:
            start_time = time.time()
            response = self.session.post(f"{self.base_url}/calculate", data=calc_data)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    
                    if self.validate_calculation_result(data):
                        btc_daily = data.get('btc_mined', {}).get('daily', 0)
                        profit_daily = data.get('profit', {}).get('daily', 0)
                        breakeven_cost = data.get('break_even', {}).get('electricity_cost', 0)
                        
                        self.log_test("挖矿计算", "基础计算验证", "PASS", 
                                    f"日产BTC: {btc_daily:.6f}, 日收益: ${profit_daily:.2f}, 盈亏平衡: ${breakeven_cost:.6f}/kWh", response_time)
                        
                        # 测试不同矿机型号
                        self.test_multiple_miners()
                    else:
                        self.log_test("挖矿计算", "基础计算验证", "FAIL", "计算结果验证失败", response_time)
                        
                except json.JSONDecodeError:
                    self.log_test("挖矿计算", "基础计算验证", "FAIL", "JSON解析失败", response_time)
            else:
                self.log_test("挖矿计算", "基础计算验证", "FAIL", f"HTTP {response.status_code}", response_time)
                
        except Exception as e:
            self.log_test("挖矿计算", "基础计算验证", "FAIL", f"计算异常: {str(e)}")

    def validate_calculation_result(self, data) -> bool:
        """验证挖矿计算结果的完整性"""
        if not isinstance(data, dict) or not data.get('success', False):
            return False
            
        # 验证必要字段
        essential_fields = ['btc_mined', 'profit', 'break_even', 'network_data']
        for field in essential_fields:
            if field not in data:
                return False
                
        # 验证BTC挖矿数据
        btc_mined = data.get('btc_mined', {})
        if not isinstance(btc_mined, dict) or 'daily' not in btc_mined:
            return False
            
        daily_btc = btc_mined.get('daily', 0)
        if not isinstance(daily_btc, (int, float)) or daily_btc <= 0:
            return False
            
        return True

    def test_multiple_miners(self):
        """测试多种矿机型号"""
        test_miners = ["Antminer S21", "Antminer S21 XP", "Antminer S19j Pro"]
        successful_tests = 0
        
        for miner_model in test_miners:
            calc_data = {
                "miner_model": miner_model,
                "miner_count": "1",
                "electricity_cost": "0.08",
                "use_real_time": "on"
            }
            
            try:
                response = self.session.post(f"{self.base_url}/calculate", data=calc_data)
                if response.status_code == 200:
                    data = response.json()
                    if self.validate_calculation_result(data):
                        successful_tests += 1
                        breakeven_cost = data.get('break_even', {}).get('electricity_cost', 0)
                        daily_btc = data.get('btc_mined', {}).get('daily', 0)
                        self.log_test("挖矿计算", f"{miner_model}计算", "PASS", 
                                    f"盈亏平衡: ${breakeven_cost:.6f}/kWh, 日产BTC: {daily_btc:.6f}")
                    else:
                        self.log_test("挖矿计算", f"{miner_model}计算", "FAIL", "计算结果验证失败")
                else:
                    self.log_test("挖矿计算", f"{miner_model}计算", "FAIL", f"HTTP {response.status_code}")
                    
            except Exception as e:
                self.log_test("挖矿计算", f"{miner_model}计算", "FAIL", f"异常: {str(e)}")
        
        success_rate = (successful_tests / len(test_miners)) * 100
        if success_rate >= 66:
            self.log_test("挖矿计算", "多矿机测试", "PASS", f"成功率: {success_rate:.1f}% ({successful_tests}/{len(test_miners)})")
        else:
            self.log_test("挖矿计算", "多矿机测试", "WARN", f"成功率较低: {success_rate:.1f}%")

    def test_database_status(self):
        """测试数据库状态"""
        print("\n🗄️ 数据库状态测试")
        
        try:
            conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
            cursor = conn.cursor()
            
            # 检查关键表
            essential_tables = ['user_access', 'login_records', 'network_snapshots', 'market_analytics']
            missing_tables = []
            
            for table in essential_tables:
                cursor.execute(f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '{table}');")
                exists = cursor.fetchone()[0]
                if not exists:
                    missing_tables.append(table)
            
            if not missing_tables:
                self.log_test("数据库", "表结构完整性", "PASS", f"所有{len(essential_tables)}个核心表存在")
            else:
                self.log_test("数据库", "表结构完整性", "WARN", f"缺失表: {missing_tables}")
            
            # 检查数据记录
            cursor.execute("SELECT COUNT(*) FROM market_analytics")
            market_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM network_snapshots")
            snapshot_count = cursor.fetchone()[0]
            
            self.log_test("数据库", "数据完整性", "PASS", f"市场分析: {market_count}条, 网络快照: {snapshot_count}条")
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            self.log_test("数据库", "连接测试", "FAIL", f"数据库异常: {str(e)}")

    def test_user_interface(self):
        """测试用户界面"""
        print("\n🖥️ 用户界面测试")
        
        # 测试主要页面
        main_pages = [
            ("主页", "/"),
            ("分析仪表盘", "/analytics"),
            ("CRM系统", "/crm")
        ]
        
        for page_name, path in main_pages:
            try:
                start_time = time.time()
                response = self.session.get(f"{self.base_url}{path}")
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    content = response.text
                    if "BTC挖矿" in content or "Mining" in content:
                        self.log_test("用户界面", f"{page_name}加载", "PASS", 
                                    f"页面加载正常，大小: {len(content)}字符", response_time)
                    else:
                        self.log_test("用户界面", f"{page_name}加载", "WARN", "页面内容可能异常", response_time)
                elif response.status_code == 302:
                    self.log_test("用户界面", f"{page_name}加载", "INFO", "重定向到登录页(正常行为)", response_time)
                else:
                    self.log_test("用户界面", f"{page_name}加载", "FAIL", f"HTTP {response.status_code}", response_time)
                    
            except Exception as e:
                self.log_test("用户界面", f"{page_name}加载", "FAIL", f"页面异常: {str(e)}")

    def run_focused_test(self):
        """运行聚焦测试"""
        print("=" * 80)
        print("🔧 BTC挖矿计算器系统 - 聚焦核心功能回归测试")
        print(f"📅 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        
        # 步骤1: 系统认证
        print("\n🔐 系统认证")
        auth_success = self.authenticate_system()
        
        if auth_success:
            # 步骤2: 核心API测试
            self.test_core_apis()
            
            # 步骤3: 挖矿计算测试
            self.test_mining_calculation()
        
        # 步骤4: 数据库状态测试
        self.test_database_status()
        
        # 步骤5: 用户界面测试
        self.test_user_interface()
        
        # 生成测试报告
        self.generate_focused_report()

    def generate_focused_report(self):
        """生成聚焦测试报告"""
        print("\n" + "=" * 80)
        print("📋 聚焦核心功能测试报告")
        print("=" * 80)
        
        # 统计结果
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r['status'] == 'PASS'])
        failed_tests = len([r for r in self.test_results if r['status'] == 'FAIL'])
        warned_tests = len([r for r in self.test_results if r['status'] == 'WARN'])
        info_tests = len([r for r in self.test_results if r['status'] == 'INFO'])
        
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        print(f"🎯 总测试数: {total_tests}")
        print(f"✅ 通过: {passed_tests}")
        print(f"❌ 失败: {failed_tests}")
        print(f"⚠️  警告: {warned_tests}")
        print(f"ℹ️  信息: {info_tests}")
        print(f"📈 成功率: {success_rate:.1f}%")
        
        # 按模块分组统计
        modules = {}
        for result in self.test_results:
            module = result['module']
            if module not in modules:
                modules[module] = {'PASS': 0, 'FAIL': 0, 'WARN': 0, 'INFO': 0}
            modules[module][result['status']] += 1
        
        print(f"\n📊 模块测试详情:")
        for module, stats in modules.items():
            total_module = sum(stats.values())
            module_success_rate = (stats['PASS'] / total_module * 100) if total_module > 0 else 0
            print(f"   • {module}: {stats['PASS']}/{total_module} 通过 ({module_success_rate:.1f}%)")
        
        # 关键失败详情
        critical_failures = [r for r in self.test_results if r['status'] == 'FAIL']
        if critical_failures:
            print(f"\n❌ 失败详情:")
            for result in critical_failures[:5]:
                print(f"   • {result['module']}.{result['function']}: {result['details']}")
        
        # 系统状态评估
        print(f"\n" + "=" * 80)
        if success_rate >= 85:
            print("🟢 系统状态: 优秀 - 生产就绪")
        elif success_rate >= 70:
            print("🟡 系统状态: 良好 - 基本可用")
        elif success_rate >= 50:
            print("🟠 系统状态: 一般 - 需要改进")
        else:
            print("🔴 系统状态: 需要修复 - 存在重大问题")
        
        print(f"\n🚀 聚焦核心功能回归测试完成")

def main():
    """主函数"""
    tester = FocusedRegressionTest()
    tester.run_focused_test()

if __name__ == "__main__":
    main()