#!/usr/bin/env python3
"""
全面功能回归测试 - BTC挖矿计算器系统
Comprehensive Function Regression Test - BTC Mining Calculator System

测试所有核心功能模块的完整性和可用性
Tests completeness and availability of all core function modules
"""

import requests
import json
import time
import psycopg2
import os
from datetime import datetime
from typing import Dict, List, Any

class ComprehensiveFunctionTest:
    def __init__(self):
        self.base_url = "http://0.0.0.0:5000"
        self.session = requests.Session()
        self.test_results = []
        self.authenticated = False
        self.owner_email = "admin@btcmining.com"  # 拥有者邮箱用于测试
        
    def log_test(self, module_name: str, function_name: str, status: str, details: str = "", response_time: float = None):
        """记录测试结果"""
        result = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'module': module_name,
            'function': function_name,
            'status': status,
            'details': details,
            'response_time': response_time
        }
        self.test_results.append(result)
        
        status_symbol = "✓" if status == "PASS" else "✗" if status == "FAIL" else "⚠"
        time_str = f" ({response_time:.3f}s)" if response_time else ""
        print(f"{status_symbol} {module_name}.{function_name}: {status}{time_str}")
        if details:
            print(f"   → {details}")

    def authenticate_as_owner(self):
        """使用拥有者邮箱进行认证"""
        try:
            login_data = {"email": self.owner_email}
            start_time = time.time()
            response = self.session.post(f"{self.base_url}/login", data=login_data)
            response_time = time.time() - start_time
            
            if response.status_code == 200 and "退出登录" in response.text:
                self.authenticated = True
                self.log_test("认证系统", "拥有者登录", "PASS", f"成功登录为拥有者", response_time)
                return True
            else:
                self.log_test("认证系统", "拥有者登录", "FAIL", f"登录失败: {response.status_code}", response_time)
                return False
                
        except Exception as e:
            self.log_test("认证系统", "拥有者登录", "FAIL", f"认证异常: {str(e)}")
            return False

    def test_core_apis(self):
        """测试核心API功能"""
        print("\n🔌 核心API功能测试")
        
        apis = [
            ("BTC价格API", "/api/get_btc_price"),
            ("网络统计API", "/api/get_network_stats"), 
            ("矿机数据API", "/api/get_miners"),
            ("SHA256挖矿对比API", "/api/get_sha256_mining_comparison"),
            ("收益图表数据API", "/api/get_profit_chart_data")
        ]
        
        for api_name, endpoint in apis:
            try:
                start_time = time.time()
                response = self.session.get(f"{self.base_url}{endpoint}")
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        if isinstance(data, dict) and data:
                            self.log_test("核心API", api_name, "PASS", f"数据完整性验证通过", response_time)
                        else:
                            self.log_test("核心API", api_name, "WARN", f"数据格式异常", response_time)
                    except json.JSONDecodeError:
                        self.log_test("核心API", api_name, "FAIL", f"JSON解析失败", response_time)
                else:
                    self.log_test("核心API", api_name, "FAIL", f"HTTP {response.status_code}", response_time)
                    
            except Exception as e:
                self.log_test("核心API", api_name, "FAIL", f"请求异常: {str(e)}")

    def test_mining_calculation_engine(self):
        """测试挖矿计算引擎"""
        print("\n⚡ 挖矿计算引擎测试")
        
        # 测试标准挖矿计算
        calc_data = {
            "miner_model": "Antminer S21 XP Hyd",
            "miner_count": "10",
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
                    
                    # 验证关键计算结果
                    required_fields = ['btc_mined', 'electricity_cost_daily', 'profit_daily', 'roi_data']
                    missing_fields = [field for field in required_fields if field not in data]
                    
                    if not missing_fields:
                        btc_daily = data.get('btc_mined', {}).get('daily', 0)
                        profit_daily = data.get('profit_daily', 0)
                        
                        if btc_daily > 0 and profit_daily != 0:
                            self.log_test("挖矿计算", "标准计算", "PASS", 
                                        f"BTC日产出: {btc_daily:.6f}, 日收益: ${profit_daily:.2f}", response_time)
                        else:
                            self.log_test("挖矿计算", "标准计算", "WARN", 
                                        f"计算结果异常: BTC={btc_daily}, 收益={profit_daily}", response_time)
                    else:
                        self.log_test("挖矿计算", "标准计算", "FAIL", 
                                    f"缺失字段: {missing_fields}", response_time)
                        
                except json.JSONDecodeError:
                    self.log_test("挖矿计算", "标准计算", "FAIL", "JSON解析失败", response_time)
            else:
                self.log_test("挖矿计算", "标准计算", "FAIL", f"HTTP {response.status_code}", response_time)
                
        except Exception as e:
            self.log_test("挖矿计算", "标准计算", "FAIL", f"计算异常: {str(e)}")

        # 测试盈亏平衡分析
        self.test_breakeven_analysis()
        
        # 测试限电计算
        self.test_curtailment_calculation()

    def test_breakeven_analysis(self):
        """测试盈亏平衡分析"""
        try:
            # 获取所有矿机型号的盈亏平衡电价
            start_time = time.time()
            response = self.session.get(f"{self.base_url}/api/get_miners")
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                miners_data = response.json()
                if isinstance(miners_data, list) and len(miners_data) >= 10:
                    self.log_test("盈亏平衡分析", "矿机数据获取", "PASS", 
                                f"获取到{len(miners_data)}种矿机型号", response_time)
                    
                    # 验证盈亏平衡计算
                    breakeven_tests = 0
                    breakeven_success = 0
                    
                    for miner in miners_data[:3]:  # 测试前3个型号
                        miner_model = miner.get('name', '')
                        if miner_model:
                            breakeven_cost = self.calculate_breakeven_for_miner(miner_model)
                            if breakeven_cost and breakeven_cost > 0:
                                breakeven_success += 1
                                self.log_test("盈亏平衡分析", f"{miner_model}盈亏平衡", "PASS", 
                                            f"盈亏平衡电价: ${breakeven_cost:.6f}/kWh")
                            else:
                                self.log_test("盈亏平衡分析", f"{miner_model}盈亏平衡", "FAIL", "计算失败")
                            breakeven_tests += 1
                    
                    if breakeven_success == breakeven_tests:
                        self.log_test("盈亏平衡分析", "综合评估", "PASS", 
                                    f"所有测试矿机({breakeven_success}/{breakeven_tests})盈亏平衡计算正常")
                    else:
                        self.log_test("盈亏平衡分析", "综合评估", "WARN", 
                                    f"部分矿机盈亏平衡计算异常({breakeven_success}/{breakeven_tests})")
                        
                else:
                    self.log_test("盈亏平衡分析", "矿机数据获取", "FAIL", f"矿机数据不完整", response_time)
            else:
                self.log_test("盈亏平衡分析", "矿机数据获取", "FAIL", f"HTTP {response.status_code}", response_time)
                
        except Exception as e:
            self.log_test("盈亏平衡分析", "数据获取", "FAIL", f"异常: {str(e)}")

    def calculate_breakeven_for_miner(self, miner_model: str) -> float:
        """计算特定矿机的盈亏平衡电价"""
        try:
            calc_data = {
                "miner_model": miner_model,
                "miner_count": "1",
                "electricity_cost": "0.10",  # 使用中等电价测试
                "use_real_time": "on"
            }
            
            response = self.session.post(f"{self.base_url}/calculate", data=calc_data)
            if response.status_code == 200:
                data = response.json()
                breakeven_data = data.get('breakeven_analysis', {})
                return breakeven_data.get('breakeven_electricity_cost', 0)
            return 0
            
        except Exception:
            return 0

    def test_curtailment_calculation(self):
        """测试限电计算功能"""
        curtailment_data = {
            "miners_config": json.dumps([{"model": "Antminer S21 XP Hyd", "count": 50}]),
            "curtailment_percentage": "20",
            "electricity_cost": "0.05",
            "btc_price": "100000",
            "network_difficulty": "120",
            "shutdown_strategy": "efficiency"
        }
        
        try:
            start_time = time.time()
            response = self.session.post(f"{self.base_url}/calculate_curtailment", data=curtailment_data)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    if data.get('success') and 'curtailment_impact' in data:
                        impact = data['curtailment_impact']
                        reduced_hashrate = impact.get('reduced_hashrate', 0)
                        revenue_loss = impact.get('monthly_revenue_loss', 0)
                        
                        if reduced_hashrate > 0 and revenue_loss > 0:
                            self.log_test("限电计算", "限电影响分析", "PASS", 
                                        f"算力降低: {reduced_hashrate:.1f}TH/s, 月损失: ${revenue_loss:.2f}", response_time)
                        else:
                            self.log_test("限电计算", "限电影响分析", "WARN", "计算结果异常", response_time)
                    else:
                        self.log_test("限电计算", "限电影响分析", "FAIL", "响应数据不完整", response_time)
                        
                except json.JSONDecodeError:
                    self.log_test("限电计算", "限电影响分析", "FAIL", "JSON解析失败", response_time)
            else:
                self.log_test("限电计算", "限电影响分析", "FAIL", f"HTTP {response.status_code}", response_time)
                
        except Exception as e:
            self.log_test("限电计算", "限电影响分析", "FAIL", f"计算异常: {str(e)}")

    def test_analytics_system(self):
        """测试分析系统功能"""
        print("\n📊 分析系统功能测试")
        
        if not self.authenticated:
            self.log_test("分析系统", "权限验证", "FAIL", "需要拥有者权限")
            return
            
        analytics_apis = [
            ("市场数据API", "/api/analytics/market-data"),
            ("最新报告API", "/analytics/api/latest-report"),
            ("技术指标API", "/analytics/api/technical-indicators"),
            ("价格历史API", "/analytics/api/price-history")
        ]
        
        for api_name, endpoint in analytics_apis:
            try:
                start_time = time.time()
                response = self.session.get(f"{self.base_url}{endpoint}")
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        if data.get('success'):
                            self.log_test("分析系统", api_name, "PASS", "数据获取成功", response_time)
                        else:
                            error_msg = data.get('error', '未知错误')
                            self.log_test("分析系统", api_name, "WARN", f"API返回错误: {error_msg}", response_time)
                    except json.JSONDecodeError:
                        self.log_test("分析系统", api_name, "FAIL", "JSON解析失败", response_time)
                else:
                    self.log_test("分析系统", api_name, "FAIL", f"HTTP {response.status_code}", response_time)
                    
            except Exception as e:
                self.log_test("分析系统", api_name, "FAIL", f"请求异常: {str(e)}")

    def test_database_connectivity(self):
        """测试数据库连接和功能"""
        print("\n🗄️ 数据库功能测试")
        
        try:
            # 测试基本数据库连接
            conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
            cursor = conn.cursor()
            
            # 测试市场分析数据表
            cursor.execute("SELECT COUNT(*) FROM market_analytics")
            market_count = cursor.fetchone()[0]
            self.log_test("数据库", "市场分析数据", "PASS", f"记录数量: {market_count}")
            
            # 测试网络快照数据表
            cursor.execute("SELECT COUNT(*) FROM network_snapshots")
            snapshot_count = cursor.fetchone()[0]
            self.log_test("数据库", "网络快照数据", "PASS", f"记录数量: {snapshot_count}")
            
            # 测试用户访问权限表
            cursor.execute("SELECT COUNT(*) FROM user_access")
            access_count = cursor.fetchone()[0]
            self.log_test("数据库", "用户访问权限", "PASS", f"用户数量: {access_count}")
            
            # 测试登录记录表
            cursor.execute("SELECT COUNT(*) FROM login_records")
            login_count = cursor.fetchone()[0]
            self.log_test("数据库", "登录记录", "PASS", f"登录记录数: {login_count}")
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            self.log_test("数据库", "连接测试", "FAIL", f"数据库异常: {str(e)}")

    def test_page_functionality(self):
        """测试页面功能"""
        print("\n🌐 页面功能测试")
        
        pages = [
            ("主页", "/"),
            ("登录页", "/login"),
            ("分析仪表盘", "/analytics"),
            ("CRM系统", "/crm"),
            ("限电计算器", "/curtailment_calculator"),
            ("算法测试", "/algorithm-test"),
            ("网络历史", "/network/history")
        ]
        
        for page_name, path in pages:
            try:
                start_time = time.time()
                response = self.session.get(f"{self.base_url}{path}")
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    # 检查页面是否包含预期内容
                    if "BTC挖矿" in response.text or "Mining" in response.text:
                        self.log_test("页面功能", page_name, "PASS", "页面加载正常", response_time)
                    else:
                        self.log_test("页面功能", page_name, "WARN", "页面内容异常", response_time)
                elif response.status_code == 302:
                    self.log_test("页面功能", page_name, "WARN", "重定向到登录页(需要权限)", response_time)
                else:
                    self.log_test("页面功能", page_name, "FAIL", f"HTTP {response.status_code}", response_time)
                    
            except Exception as e:
                self.log_test("页面功能", page_name, "FAIL", f"页面异常: {str(e)}")

    def test_external_integrations(self):
        """测试外部API集成"""
        print("\n🌍 外部API集成测试")
        
        try:
            # 通过系统API测试外部集成
            start_time = time.time()
            response = self.session.get(f"{self.base_url}/api/get_network_stats")
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    data_source = data.get('data_source', '')
                    if 'CoinWarz' in data_source or 'blockchain' in data_source:
                        hashrate = data.get('network_hashrate', 0)
                        difficulty = data.get('difficulty', 0)
                        
                        if hashrate > 0 and difficulty > 0:
                            self.log_test("外部集成", "网络数据API", "PASS", 
                                        f"数据源: {data_source}, 算力: {hashrate}EH/s", response_time)
                        else:
                            self.log_test("外部集成", "网络数据API", "WARN", "数据值异常", response_time)
                    else:
                        self.log_test("外部集成", "网络数据API", "FAIL", "数据源未知", response_time)
                        
                except json.JSONDecodeError:
                    self.log_test("外部集成", "网络数据API", "FAIL", "JSON解析失败", response_time)
            else:
                self.log_test("外部集成", "网络数据API", "FAIL", f"HTTP {response.status_code}", response_time)
                
        except Exception as e:
            self.log_test("外部集成", "网络数据API", "FAIL", f"集成异常: {str(e)}")

    def run_comprehensive_test(self):
        """运行全面的功能回归测试"""
        print("=" * 80)
        print("🔧 BTC挖矿计算器系统 - 全面功能回归测试")
        print(f"📅 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        
        # 首先进行认证
        print("\n🔐 系统认证")
        self.authenticate_as_owner()
        
        # 按模块进行测试
        self.test_core_apis()
        self.test_mining_calculation_engine()
        self.test_analytics_system()
        self.test_database_connectivity()
        self.test_page_functionality()
        self.test_external_integrations()
        
        # 生成测试报告
        self.generate_comprehensive_report()

    def generate_comprehensive_report(self):
        """生成全面的测试报告"""
        print("\n" + "=" * 80)
        print("📋 全面功能测试报告")
        print("=" * 80)
        
        # 统计结果
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r['status'] == 'PASS'])
        failed_tests = len([r for r in self.test_results if r['status'] == 'FAIL'])
        warned_tests = len([r for r in self.test_results if r['status'] == 'WARN'])
        
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        # 平均响应时间
        response_times = [r['response_time'] for r in self.test_results if r['response_time']]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        print(f"🎯 总测试数: {total_tests}")
        print(f"✅ 通过: {passed_tests}")
        print(f"❌ 失败: {failed_tests}")
        print(f"⚠️  警告: {warned_tests}")
        print(f"📈 成功率: {success_rate:.1f}%")
        print(f"⏱️  平均响应时间: {avg_response_time:.3f}秒")
        
        # 按模块分组统计
        modules = {}
        for result in self.test_results:
            module = result['module']
            if module not in modules:
                modules[module] = {'PASS': 0, 'FAIL': 0, 'WARN': 0}
            modules[module][result['status']] += 1
        
        print(f"\n📊 模块测试详情:")
        for module, stats in modules.items():
            total_module = sum(stats.values())
            module_success_rate = (stats['PASS'] / total_module * 100) if total_module > 0 else 0
            print(f"   • {module}: {stats['PASS']}/{total_module} 通过 ({module_success_rate:.1f}%)")
        
        # 失败详情
        failed_results = [r for r in self.test_results if r['status'] == 'FAIL']
        if failed_results:
            print(f"\n❌ 失败测试详情:")
            for result in failed_results:
                print(f"   • {result['module']}.{result['function']}: {result['details']}")
        
        # 警告详情
        warned_results = [r for r in self.test_results if r['status'] == 'WARN']
        if warned_results:
            print(f"\n⚠️  警告测试详情:")
            for result in warned_results:
                print(f"   • {result['module']}.{result['function']}: {result['details']}")
        
        # 系统状态评估
        print(f"\n" + "=" * 80)
        if success_rate >= 80:
            print("🟢 系统状态: 良好 - 大部分功能正常运行")
        elif success_rate >= 60:
            print("🟡 系统状态: 一般 - 部分功能需要优化")
        else:
            print("🔴 系统状态: 需要改进 - 多个功能存在问题")
        
        print(f"\n🚀 全面功能回归测试完成")

def main():
    """主函数"""
    tester = ComprehensiveFunctionTest()
    tester.run_comprehensive_test()

if __name__ == "__main__":
    main()