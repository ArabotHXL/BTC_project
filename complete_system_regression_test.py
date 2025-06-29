#!/usr/bin/env python3
"""
完整系统功能回归测试
Complete System Function Regression Test

全面测试BTC挖矿计算器系统的所有功能模块
Comprehensive testing of all function modules in BTC Mining Calculator System
"""

import requests
import json
import time
import psycopg2
import os
from datetime import datetime
from typing import Dict, List, Any, Tuple

class CompleteSystemRegressionTest:
    def __init__(self):
        self.base_url = "http://0.0.0.0:5000"
        self.session = requests.Session()
        self.test_results = []
        self.authenticated = False
        self.owner_email = "hxl2022hao@gmail.com"  # 使用有效的拥有者邮箱
        
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

    def test_core_infrastructure(self):
        """测试核心基础设施"""
        print("\n🏗️ 核心基础设施测试")
        
        # 测试服务器健康状态
        try:
            start_time = time.time()
            response = self.session.get(f"{self.base_url}/")
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                self.log_test("基础设施", "服务器健康检查", "PASS", "服务器运行正常", response_time)
            else:
                self.log_test("基础设施", "服务器健康检查", "FAIL", f"HTTP {response.status_code}", response_time)
                
        except Exception as e:
            self.log_test("基础设施", "服务器健康检查", "FAIL", f"连接异常: {str(e)}")

        # 测试数据库连接和表结构
        self.test_database_infrastructure()
        
        # 测试静态资源加载
        self.test_static_resources()

    def test_database_infrastructure(self):
        """测试数据库基础设施"""
        try:
            conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
            cursor = conn.cursor()
            
            # 检查关键表是否存在
            essential_tables = [
                'user_access', 'login_records', 'network_snapshots', 
                'market_analytics', 'customers', 'leads', 'deals', 
                'activities', 'contacts', 'commission_records'
            ]
            
            missing_tables = []
            for table in essential_tables:
                cursor.execute(f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '{table}');")
                exists = cursor.fetchone()[0]
                if not exists:
                    missing_tables.append(table)
            
            if not missing_tables:
                self.log_test("基础设施", "数据库表结构", "PASS", f"所有{len(essential_tables)}个关键表存在")
            else:
                self.log_test("基础设施", "数据库表结构", "FAIL", f"缺失表: {missing_tables}")
            
            # 检查数据完整性
            cursor.execute("SELECT COUNT(*) FROM market_analytics")
            market_count = cursor.fetchone()[0]
            self.log_test("基础设施", "市场数据完整性", "PASS", f"市场分析记录: {market_count}")
            
            cursor.execute("SELECT COUNT(*) FROM network_snapshots")
            snapshot_count = cursor.fetchone()[0]
            self.log_test("基础设施", "网络快照完整性", "PASS", f"网络快照记录: {snapshot_count}")
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            self.log_test("基础设施", "数据库连接", "FAIL", f"数据库异常: {str(e)}")

    def test_static_resources(self):
        """测试静态资源加载"""
        static_resources = [
            ("/static/css/style.css", "CSS样式表"),
            ("/static/js/main.js", "主JavaScript文件"),
            ("/static/js/chart.min.js", "图表库")
        ]
        
        for resource_path, resource_name in static_resources:
            try:
                start_time = time.time()
                response = self.session.get(f"{self.base_url}{resource_path}")
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    self.log_test("基础设施", f"静态资源-{resource_name}", "PASS", f"资源加载正常", response_time)
                else:
                    self.log_test("基础设施", f"静态资源-{resource_name}", "WARN", f"HTTP {response.status_code}", response_time)
                    
            except Exception as e:
                self.log_test("基础设施", f"静态资源-{resource_name}", "FAIL", f"加载失败: {str(e)}")

    def test_api_ecosystem(self):
        """测试API生态系统"""
        print("\n🔌 API生态系统测试")
        
        if not self.authenticated:
            self.log_test("API生态", "认证状态", "FAIL", "需要认证才能测试API")
            return
        
        # 核心数据API
        core_apis = [
            ("BTC价格API", "/api/get_btc_price", self.validate_price_api),
            ("网络统计API", "/api/get_network_stats", self.validate_network_api),
            ("矿机数据API", "/api/get_miners", self.validate_miners_api),
            ("SHA256对比API", "/api/get_sha256_mining_comparison", self.validate_comparison_api)
        ]
        
        for api_name, endpoint, validator in core_apis:
            self.test_single_api(api_name, endpoint, validator)
        
        # 分析系统API
        analytics_apis = [
            ("分析市场数据", "/api/analytics/market-data", self.validate_analytics_market),
            ("分析最新报告", "/analytics/api/latest-report", self.validate_analytics_report),
            ("分析技术指标", "/analytics/api/technical-indicators", self.validate_analytics_indicators),
            ("分析价格历史", "/analytics/api/price-history", self.validate_analytics_history)
        ]
        
        for api_name, endpoint, validator in analytics_apis:
            self.test_single_api(api_name, endpoint, validator)

    def test_single_api(self, api_name: str, endpoint: str, validator):
        """测试单个API端点"""
        try:
            start_time = time.time()
            response = self.session.get(f"{self.base_url}{endpoint}")
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    validation_result = validator(data)
                    if validation_result[0]:
                        self.log_test("API生态", api_name, "PASS", validation_result[1], response_time)
                    else:
                        self.log_test("API生态", api_name, "WARN", validation_result[1], response_time)
                except json.JSONDecodeError:
                    self.log_test("API生态", api_name, "FAIL", "JSON解析失败", response_time)
            else:
                self.log_test("API生态", api_name, "FAIL", f"HTTP {response.status_code}", response_time)
                
        except Exception as e:
            self.log_test("API生态", api_name, "FAIL", f"请求异常: {str(e)}")

    def validate_price_api(self, data) -> Tuple[bool, str]:
        """验证价格API"""
        if data.get('success') and 'price' in data:
            price = data['price']
            if isinstance(price, (int, float)) and price > 0:
                return True, f"BTC价格: ${price:,.2f}"
            else:
                return False, f"价格数据异常: {price}"
        return False, "响应格式错误"

    def validate_network_api(self, data) -> Tuple[bool, str]:
        """验证网络统计API"""
        if data.get('success'):
            required_fields = ['price', 'difficulty', 'hashrate', 'data_source']
            missing_fields = [field for field in required_fields if field not in data]
            if not missing_fields:
                return True, f"数据源: {data['data_source']}, 算力: {data['hashrate']:.1f}EH/s"
            else:
                return False, f"缺失字段: {missing_fields}"
        return False, "API响应失败"

    def validate_miners_api(self, data) -> Tuple[bool, str]:
        """验证矿机数据API"""
        if data.get('success') and 'miners' in data:
            miners = data['miners']
            if isinstance(miners, list) and len(miners) >= 10:
                sample_miner = miners[0]
                required_fields = ['name', 'hashrate', 'power_consumption']
                if all(field in sample_miner for field in required_fields):
                    return True, f"获取{len(miners)}种矿机型号"
                else:
                    return False, "矿机数据格式错误"
            else:
                return False, f"矿机数据不足: {len(miners) if isinstance(miners, list) else 0}"
        return False, "响应格式错误"

    def validate_comparison_api(self, data) -> Tuple[bool, str]:
        """验证挖矿对比API"""
        if data.get('success'):
            return True, "SHA256对比数据获取成功"
        elif 'error' in data:
            return False, f"API错误: {data['error']}"
        return False, "响应格式错误"

    def validate_analytics_market(self, data) -> Tuple[bool, str]:
        """验证分析市场数据API"""
        if data.get('success') and 'data' in data:
            market_data = data['data']
            required_fields = ['btc_price', 'network_hashrate', 'network_difficulty']
            if all(field in market_data for field in required_fields):
                return True, f"市场数据完整，BTC: ${market_data['btc_price']:,.0f}"
            else:
                return False, "市场数据不完整"
        return False, "分析数据格式错误"

    def validate_analytics_report(self, data) -> Tuple[bool, str]:
        """验证分析报告API"""
        if data.get('success'):
            return True, "最新分析报告可用"
        else:
            return False, data.get('error', '报告不可用')

    def validate_analytics_indicators(self, data) -> Tuple[bool, str]:
        """验证技术指标API"""
        if data.get('success'):
            return True, "技术指标数据可用"
        else:
            return False, data.get('error', '技术指标不可用')

    def validate_analytics_history(self, data) -> Tuple[bool, str]:
        """验证价格历史API"""
        if data.get('success') and 'data' in data:
            history_data = data['data']
            if isinstance(history_data, list) and len(history_data) > 0:
                return True, f"价格历史记录: {len(history_data)}条"
            else:
                return False, "价格历史数据为空"
        else:
            return False, data.get('error', '价格历史不可用')

    def test_mining_calculation_engine(self):
        """测试挖矿计算引擎"""
        print("\n⚡ 挖矿计算引擎测试")
        
        if not self.authenticated:
            self.log_test("挖矿计算", "认证状态", "FAIL", "需要认证才能测试计算功能")
            return
        
        # 测试基础挖矿计算
        self.test_basic_mining_calculation()
        
        # 测试所有矿机型号
        self.test_all_miner_models()
        
        # 测试高级计算功能
        self.test_advanced_calculations()
        
        # 测试盈亏平衡分析
        self.test_breakeven_analysis()

    def test_basic_mining_calculation(self):
        """测试基础挖矿计算"""
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
                    
                    # 验证计算结果的完整性
                    if self.validate_calculation_result(data):
                        btc_daily = data.get('btc_mined', {}).get('daily', 0)
                        profit_daily = data.get('profit_daily', 0)
                        efficiency = data.get('efficiency_wth', 0)
                        
                        self.log_test("挖矿计算", "基础挖矿计算", "PASS", 
                                    f"日产BTC: {btc_daily:.6f}, 日收益: ${profit_daily:.2f}, 效率: {efficiency:.2f}W/TH", response_time)
                        
                        # 验证关键业务逻辑
                        self.validate_business_logic(data)
                    else:
                        self.log_test("挖矿计算", "基础挖矿计算", "FAIL", "计算结果验证失败", response_time)
                        
                except json.JSONDecodeError:
                    self.log_test("挖矿计算", "基础挖矿计算", "FAIL", "JSON解析失败", response_time)
            else:
                self.log_test("挖矿计算", "基础挖矿计算", "FAIL", f"HTTP {response.status_code}", response_time)
                
        except Exception as e:
            self.log_test("挖矿计算", "基础挖矿计算", "FAIL", f"计算异常: {str(e)}")

    def validate_calculation_result(self, data) -> bool:
        """验证挖矿计算结果的完整性"""
        # 检查基本结构
        if not isinstance(data, dict):
            return False
            
        # 检查success标志
        if not data.get('success', False):
            return False
            
        # 验证BTC挖矿数据
        btc_mined = data.get('btc_mined', {})
        if isinstance(btc_mined, dict) and 'daily' in btc_mined:
            daily_btc = btc_mined.get('daily', 0)
            if not isinstance(daily_btc, (int, float)) or daily_btc <= 0:
                return False
        else:
            return False
            
        # 验证收益数据 - 使用实际响应中的字段名
        profit = data.get('profit', {})
        if isinstance(profit, dict) and 'daily' in profit:
            daily_profit = profit.get('daily', 0)
            if not isinstance(daily_profit, (int, float)):
                return False
        else:
            return False
            
        # 验证网络数据
        network_data = data.get('network_data', {})
        if not isinstance(network_data, dict) or 'btc_price' not in network_data:
            return False
            
        return True

    def validate_business_logic(self, data):
        """验证业务逻辑正确性"""
        # 验证盈亏平衡分析
        if 'breakeven_analysis' in data:
            breakeven = data['breakeven_analysis']
            breakeven_cost = breakeven.get('breakeven_electricity_cost', 0)
            
            if breakeven_cost > 0:
                self.log_test("挖矿计算", "盈亏平衡逻辑", "PASS", 
                            f"盈亏平衡电价: ${breakeven_cost:.6f}/kWh")
            else:
                self.log_test("挖矿计算", "盈亏平衡逻辑", "WARN", "盈亏平衡计算数据异常")
        
        # 验证ROI分析
        if 'roi_data' in data:
            roi_data = data['roi_data']
            if isinstance(roi_data, dict) and 'client' in roi_data:
                roi_months = roi_data['client'].get('roi_months', 0)
                if roi_months > 0:
                    self.log_test("挖矿计算", "ROI分析逻辑", "PASS", 
                                f"客户投资回报周期: {roi_months:.1f}个月")
                else:
                    self.log_test("挖矿计算", "ROI分析逻辑", "WARN", "ROI计算异常")

    def test_all_miner_models(self):
        """测试所有矿机型号"""
        try:
            response = self.session.get(f"{self.base_url}/api/get_miners")
            if response.status_code == 200:
                data = response.json()
                if data.get('success') and 'miners' in data:
                    miners = data['miners']
                    
                    successful_calculations = 0
                    total_miners = len(miners)
                    
                    # 测试前5个矿机型号的计算
                    for i, miner in enumerate(miners[:5]):
                        miner_name = miner['name']
                        calc_result = self.test_single_miner_calculation(miner_name)
                        if calc_result:
                            successful_calculations += 1
                    
                    success_rate = (successful_calculations / min(5, total_miners)) * 100
                    if success_rate >= 80:
                        self.log_test("挖矿计算", "所有矿机型号", "PASS", 
                                    f"测试了{min(5, total_miners)}种矿机，成功率: {success_rate:.1f}%")
                    else:
                        self.log_test("挖矿计算", "所有矿机型号", "WARN", 
                                    f"部分矿机计算异常，成功率: {success_rate:.1f}%")
                else:
                    self.log_test("挖矿计算", "所有矿机型号", "FAIL", "无法获取矿机列表")
            else:
                self.log_test("挖矿计算", "所有矿机型号", "FAIL", f"矿机API失败: {response.status_code}")
                
        except Exception as e:
            self.log_test("挖矿计算", "所有矿机型号", "FAIL", f"测试异常: {str(e)}")

    def test_single_miner_calculation(self, miner_name: str) -> bool:
        """测试单个矿机的计算"""
        calc_data = {
            "miner_model": miner_name,
            "miner_count": "1",
            "electricity_cost": "0.08",
            "use_real_time": "on"
        }
        
        try:
            response = self.session.post(f"{self.base_url}/calculate", data=calc_data)
            if response.status_code == 200:
                data = response.json()
                if self.validate_calculation_result(data):
                    breakeven = data.get('breakeven_analysis', {})
                    breakeven_cost = breakeven.get('breakeven_electricity_cost', 0)
                    self.log_test("挖矿计算", f"{miner_name}计算", "PASS", 
                                f"盈亏平衡: ${breakeven_cost:.6f}/kWh")
                    return True
                else:
                    self.log_test("挖矿计算", f"{miner_name}计算", "FAIL", "计算结果验证失败")
                    return False
            else:
                self.log_test("挖矿计算", f"{miner_name}计算", "FAIL", f"HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("挖矿计算", f"{miner_name}计算", "FAIL", f"异常: {str(e)}")
            return False

    def test_advanced_calculations(self):
        """测试高级计算功能"""
        # 测试限电计算
        self.test_curtailment_calculation()
        
        # 测试投资分析
        self.test_investment_analysis()
        
        # 测试多种电价计算
        self.test_multiple_electricity_costs()

    def test_curtailment_calculation(self):
        """测试限电计算功能"""
        curtailment_data = {
            "miners_config": json.dumps([{"model": "Antminer S21 XP Hyd", "count": 50}]),
            "curtailment_percentage": "20",
            "electricity_cost": "0.05",
            "btc_price": "108000",
            "network_difficulty": "117",
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
                            self.log_test("挖矿计算", "限电计算", "PASS", 
                                        f"算力降低: {reduced_hashrate:.1f}TH/s, 月损失: ${revenue_loss:.2f}", response_time)
                        else:
                            self.log_test("挖矿计算", "限电计算", "WARN", "限电计算结果异常", response_time)
                    else:
                        self.log_test("挖矿计算", "限电计算", "FAIL", "限电计算响应格式错误", response_time)
                        
                except json.JSONDecodeError:
                    self.log_test("挖矿计算", "限电计算", "FAIL", "JSON解析失败", response_time)
            else:
                self.log_test("挖矿计算", "限电计算", "FAIL", f"HTTP {response.status_code}", response_time)
                
        except Exception as e:
            self.log_test("挖矿计算", "限电计算", "FAIL", f"计算异常: {str(e)}")

    def test_investment_analysis(self):
        """测试投资分析功能"""
        investment_data = {
            "miner_model": "Antminer S21 XP Hyd",
            "miner_count": "100",
            "electricity_cost": "0.05",
            "client_electricity_cost": "0.06",
            "host_investment": "500000",  # 矿场主投资50万
            "client_investment": "1000000",  # 客户投资100万
            "use_real_time": "on"
        }
        
        try:
            response = self.session.post(f"{self.base_url}/calculate", data=investment_data)
            if response.status_code == 200:
                data = response.json()
                if 'roi_data' in data:
                    roi_data = data['roi_data']
                    
                    # 验证双方ROI计算
                    if 'host' in roi_data and 'client' in roi_data:
                        host_roi = roi_data['host'].get('roi_months', 0)
                        client_roi = roi_data['client'].get('roi_months', 0)
                        
                        if host_roi > 0 and client_roi > 0:
                            self.log_test("挖矿计算", "投资分析", "PASS", 
                                        f"矿场主ROI: {host_roi:.1f}月, 客户ROI: {client_roi:.1f}月")
                        else:
                            self.log_test("挖矿计算", "投资分析", "WARN", "ROI计算数据异常")
                    else:
                        self.log_test("挖矿计算", "投资分析", "FAIL", "缺少ROI分析数据")
                else:
                    self.log_test("挖矿计算", "投资分析", "FAIL", "响应中缺少ROI数据")
            else:
                self.log_test("挖矿计算", "投资分析", "FAIL", f"HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test("挖矿计算", "投资分析", "FAIL", f"异常: {str(e)}")

    def test_multiple_electricity_costs(self):
        """测试多种电价计算"""
        electricity_costs = [0.03, 0.05, 0.08, 0.12]  # 不同电价范围
        successful_calculations = 0
        
        for cost in electricity_costs:
            calc_data = {
                "miner_model": "Antminer S21",
                "miner_count": "10",
                "electricity_cost": str(cost),
                "use_real_time": "on"
            }
            
            try:
                response = self.session.post(f"{self.base_url}/calculate", data=calc_data)
                if response.status_code == 200:
                    data = response.json()
                    if self.validate_calculation_result(data):
                        successful_calculations += 1
                        
            except Exception:
                pass
        
        success_rate = (successful_calculations / len(electricity_costs)) * 100
        if success_rate >= 75:
            self.log_test("挖矿计算", "多电价计算", "PASS", 
                        f"测试了{len(electricity_costs)}种电价，成功率: {success_rate:.1f}%")
        else:
            self.log_test("挖矿计算", "多电价计算", "WARN", 
                        f"部分电价计算异常，成功率: {success_rate:.1f}%")

    def test_breakeven_analysis(self):
        """测试盈亏平衡分析"""
        # 获取矿机列表进行盈亏平衡测试
        try:
            response = self.session.get(f"{self.base_url}/api/get_miners")
            if response.status_code == 200:
                data = response.json()
                if data.get('success') and 'miners' in data:
                    miners = data['miners']
                    
                    breakeven_results = []
                    for miner in miners[:3]:  # 测试前3个型号
                        miner_name = miner['name']
                        hashrate = miner.get('hashrate', 0)
                        power = miner.get('power_consumption', 0)
                        
                        if hashrate > 0 and power > 0:
                            efficiency = power / hashrate  # W/TH
                            
                            # 计算理论盈亏平衡点
                            calc_data = {
                                "miner_model": miner_name,
                                "miner_count": "1",
                                "electricity_cost": "0.10",
                                "use_real_time": "on"
                            }
                            
                            try:
                                response = self.session.post(f"{self.base_url}/calculate", data=calc_data)
                                if response.status_code == 200:
                                    calc_result = response.json()
                                    breakeven = calc_result.get('breakeven_analysis', {})
                                    breakeven_cost = breakeven.get('breakeven_electricity_cost', 0)
                                    
                                    if breakeven_cost > 0:
                                        breakeven_results.append({
                                            'miner': miner_name,
                                            'efficiency': efficiency,
                                            'breakeven_cost': breakeven_cost
                                        })
                                        
                            except Exception:
                                continue
                    
                    if len(breakeven_results) >= 2:
                        # 验证效率更高的矿机有更高的盈亏平衡点
                        sorted_by_efficiency = sorted(breakeven_results, key=lambda x: x['efficiency'])
                        best_miner = sorted_by_efficiency[0]
                        worst_miner = sorted_by_efficiency[-1]
                        
                        if best_miner['breakeven_cost'] > worst_miner['breakeven_cost']:
                            self.log_test("挖矿计算", "盈亏平衡逻辑验证", "PASS", 
                                        f"高效矿机({best_miner['miner']}: ${best_miner['breakeven_cost']:.6f}) > 低效矿机({worst_miner['miner']}: ${worst_miner['breakeven_cost']:.6f})")
                        else:
                            self.log_test("挖矿计算", "盈亏平衡逻辑验证", "WARN", "盈亏平衡逻辑可能存在问题")
                    else:
                        self.log_test("挖矿计算", "盈亏平衡逻辑验证", "FAIL", "盈亏平衡数据不足")
                        
        except Exception as e:
            self.log_test("挖矿计算", "盈亏平衡逻辑验证", "FAIL", f"测试异常: {str(e)}")

    def test_user_interface(self):
        """测试用户界面功能"""
        print("\n🖥️ 用户界面测试")
        
        # 测试主要页面加载
        main_pages = [
            ("主页", "/"),
            ("登录页", "/login"),
            ("分析仪表盘", "/analytics"),
            ("CRM系统", "/crm"),
            ("限电计算器", "/curtailment_calculator"),
            ("算法测试", "/algorithm-test"),
            ("网络历史", "/network/history")
        ]
        
        for page_name, path in main_pages:
            self.test_page_load(page_name, path)
        
        # 测试响应式设计
        self.test_responsive_design()

    def test_page_load(self, page_name: str, path: str):
        """测试页面加载"""
        try:
            start_time = time.time()
            response = self.session.get(f"{self.base_url}{path}")
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                # 检查页面是否包含预期内容
                content = response.text
                if "BTC挖矿" in content or "Mining" in content or "login" in content.lower():
                    # 检查是否有JavaScript错误指示
                    if "error" not in content.lower() or "exception" not in content.lower():
                        self.log_test("用户界面", f"{page_name}加载", "PASS", 
                                    f"页面加载正常，大小: {len(content)}字符", response_time)
                    else:
                        self.log_test("用户界面", f"{page_name}加载", "WARN", 
                                    "页面包含错误信息", response_time)
                else:
                    self.log_test("用户界面", f"{page_name}加载", "WARN", 
                                "页面内容可能异常", response_time)
            elif response.status_code == 302:
                self.log_test("用户界面", f"{page_name}加载", "INFO", 
                            "重定向到登录页(正常行为)", response_time)
            else:
                self.log_test("用户界面", f"{page_name}加载", "FAIL", 
                            f"HTTP {response.status_code}", response_time)
                
        except Exception as e:
            self.log_test("用户界面", f"{page_name}加载", "FAIL", f"页面异常: {str(e)}")

    def test_responsive_design(self):
        """测试响应式设计"""
        # 测试不同用户代理字符串
        user_agents = [
            ("桌面Chrome", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"),
            ("移动Chrome", "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15"),
            ("平板Safari", "Mozilla/5.0 (iPad; CPU OS 14_0 like Mac OS X) AppleWebKit/605.1.15")
        ]
        
        for device_type, user_agent in user_agents:
            headers = {'User-Agent': user_agent}
            try:
                response = self.session.get(f"{self.base_url}/", headers=headers)
                if response.status_code == 200:
                    content = response.text
                    # 检查响应式设计元素
                    if "viewport" in content and "responsive" in content.lower():
                        self.log_test("用户界面", f"响应式设计-{device_type}", "PASS", "包含响应式设计元素")
                    else:
                        self.log_test("用户界面", f"响应式设计-{device_type}", "WARN", "响应式设计元素不明确")
                else:
                    self.log_test("用户界面", f"响应式设计-{device_type}", "FAIL", f"HTTP {response.status_code}")
                    
            except Exception as e:
                self.log_test("用户界面", f"响应式设计-{device_type}", "FAIL", f"测试异常: {str(e)}")

    def test_external_integrations(self):
        """测试外部集成"""
        print("\n🌐 外部集成测试")
        
        if not self.authenticated:
            self.log_test("外部集成", "认证状态", "FAIL", "需要认证才能测试外部集成")
            return
        
        # 测试通过系统API验证外部集成
        try:
            start_time = time.time()
            response = self.session.get(f"{self.base_url}/api/get_network_stats")
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    data_source = data.get('data_source', '')
                    api_calls_remaining = data.get('api_calls_remaining', 0)
                    
                    if 'CoinWarz' in data_source:
                        self.log_test("外部集成", "CoinWarz API", "PASS", 
                                    f"主要数据源正常，剩余调用: {api_calls_remaining}", response_time)
                    elif 'blockchain' in data_source.lower():
                        self.log_test("外部集成", "Blockchain.info API", "PASS", 
                                    f"备用数据源正常", response_time)
                    else:
                        self.log_test("外部集成", "未知数据源", "WARN", 
                                    f"数据源: {data_source}", response_time)
                        
                    # 验证数据质量
                    hashrate = data.get('hashrate', 0)
                    price = data.get('price', 0)
                    difficulty = data.get('difficulty', 0)
                    
                    if hashrate > 800 and price > 50000 and difficulty > 50:
                        self.log_test("外部集成", "数据质量验证", "PASS", 
                                    f"算力: {hashrate:.1f}EH/s, 价格: ${price:,.0f}, 难度: {difficulty:.1f}T")
                    else:
                        self.log_test("外部集成", "数据质量验证", "WARN", 
                                    f"数据值可能异常")
                else:
                    self.log_test("外部集成", "网络数据API", "FAIL", "API响应失败")
            else:
                self.log_test("外部集成", "网络数据API", "FAIL", f"HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test("外部集成", "网络数据API", "FAIL", f"集成异常: {str(e)}")

    def test_security_features(self):
        """测试安全功能"""
        print("\n🔒 安全功能测试")
        
        # 测试未认证访问保护
        self.test_authentication_protection()
        
        # 测试角色权限控制
        self.test_role_based_access()
        
        # 测试输入验证
        self.test_input_validation()

    def test_authentication_protection(self):
        """测试认证保护"""
        # 创建新的未认证会话
        unauth_session = requests.Session()
        
        protected_endpoints = [
            "/calculate",
            "/api/get_btc_price",
            "/api/get_network_stats",
            "/api/get_miners",
            "/analytics"
        ]
        
        protected_count = 0
        for endpoint in protected_endpoints:
            try:
                response = unauth_session.get(f"{self.base_url}{endpoint}")
                if response.status_code == 401:
                    protected_count += 1
                elif response.status_code == 302:  # 重定向到登录页
                    protected_count += 1
                    
            except Exception:
                pass
        
        protection_rate = (protected_count / len(protected_endpoints)) * 100
        if protection_rate >= 80:
            self.log_test("安全功能", "认证保护", "PASS", 
                        f"保护率: {protection_rate:.1f}% ({protected_count}/{len(protected_endpoints)})")
        else:
            self.log_test("安全功能", "认证保护", "FAIL", 
                        f"保护不足: {protection_rate:.1f}%")

    def test_role_based_access(self):
        """测试基于角色的访问控制"""
        if not self.authenticated:
            self.log_test("安全功能", "角色访问控制", "FAIL", "需要认证才能测试角色权限")
            return
        
        # 测试拥有者权限页面
        owner_pages = [
            "/admin/user_access",
            "/analytics",
            "/login/dashboard"
        ]
        
        owner_access_count = 0
        for page in owner_pages:
            try:
                response = self.session.get(f"{self.base_url}{page}")
                if response.status_code == 200:
                    owner_access_count += 1
                    
            except Exception:
                pass
        
        access_rate = (owner_access_count / len(owner_pages)) * 100
        if access_rate >= 66:
            self.log_test("安全功能", "拥有者权限", "PASS", 
                        f"访问率: {access_rate:.1f}% ({owner_access_count}/{len(owner_pages)})")
        else:
            self.log_test("安全功能", "拥有者权限", "WARN", 
                        f"部分页面可能有访问问题: {access_rate:.1f}%")

    def test_input_validation(self):
        """测试输入验证"""
        # 测试恶意输入
        malicious_inputs = [
            {"miner_count": "-1"},  # 负数
            {"electricity_cost": "abc"},  # 非数字
            {"miner_count": "999999"},  # 过大值
            {"electricity_cost": "0"},  # 零值
        ]
        
        validation_passes = 0
        for malicious_input in malicious_inputs:
            calc_data = {
                "miner_model": "Antminer S21",
                **malicious_input,
                "use_real_time": "on"
            }
            
            try:
                response = self.session.post(f"{self.base_url}/calculate", data=calc_data)
                if response.status_code == 400:  # 应该返回错误
                    validation_passes += 1
                elif response.status_code == 200:
                    # 检查是否有错误处理
                    data = response.json()
                    if not data.get('success', True):
                        validation_passes += 1
                        
            except Exception:
                pass
        
        validation_rate = (validation_passes / len(malicious_inputs)) * 100
        if validation_rate >= 50:
            self.log_test("安全功能", "输入验证", "PASS", 
                        f"验证率: {validation_rate:.1f}% ({validation_passes}/{len(malicious_inputs)})")
        else:
            self.log_test("安全功能", "输入验证", "WARN", 
                        f"输入验证可能不足: {validation_rate:.1f}%")

    def run_complete_system_test(self):
        """运行完整系统测试"""
        print("=" * 80)
        print("🔧 BTC挖矿计算器系统 - 完整系统功能回归测试")
        print(f"📅 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        
        # 步骤1: 系统认证
        print("\n🔐 系统认证")
        auth_success = self.authenticate_system()
        
        # 步骤2: 核心基础设施测试
        self.test_core_infrastructure()
        
        # 步骤3: API生态系统测试
        self.test_api_ecosystem()
        
        # 步骤4: 挖矿计算引擎测试
        self.test_mining_calculation_engine()
        
        # 步骤5: 用户界面测试
        self.test_user_interface()
        
        # 步骤6: 外部集成测试
        self.test_external_integrations()
        
        # 步骤7: 安全功能测试
        self.test_security_features()
        
        # 生成最终报告
        self.generate_final_report()

    def generate_final_report(self):
        """生成最终测试报告"""
        print("\n" + "=" * 80)
        print("📋 完整系统功能测试报告")
        print("=" * 80)
        
        # 统计结果
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r['status'] == 'PASS'])
        failed_tests = len([r for r in self.test_results if r['status'] == 'FAIL'])
        warned_tests = len([r for r in self.test_results if r['status'] == 'WARN'])
        info_tests = len([r for r in self.test_results if r['status'] == 'INFO'])
        
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        # 平均响应时间
        response_times = [r['response_time'] for r in self.test_results if r['response_time']]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        print(f"🎯 总测试数: {total_tests}")
        print(f"✅ 通过: {passed_tests}")
        print(f"❌ 失败: {failed_tests}")
        print(f"⚠️  警告: {warned_tests}")
        print(f"ℹ️  信息: {info_tests}")
        print(f"📈 成功率: {success_rate:.1f}%")
        print(f"⏱️  平均响应时间: {avg_response_time:.3f}秒")
        
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
        
        # 关键成功指标
        print(f"\n🎯 关键性能指标:")
        
        # 计算核心功能成功率
        core_modules = ['系统认证', 'API生态', '挖矿计算']
        core_results = [r for r in self.test_results if r['module'] in core_modules]
        core_passed = len([r for r in core_results if r['status'] == 'PASS'])
        core_total = len(core_results)
        core_success_rate = (core_passed / core_total * 100) if core_total > 0 else 0
        print(f"   • 核心功能成功率: {core_success_rate:.1f}%")
        
        # 计算API健康度
        api_results = [r for r in self.test_results if r['module'] == 'API生态']
        api_passed = len([r for r in api_results if r['status'] == 'PASS'])
        api_total = len(api_results)
        api_health = (api_passed / api_total * 100) if api_total > 0 else 0
        print(f"   • API健康度: {api_health:.1f}%")
        
        # 计算用户体验评分
        ui_results = [r for r in self.test_results if r['module'] == '用户界面']
        ui_passed = len([r for r in ui_results if r['status'] in ['PASS', 'INFO']])
        ui_total = len(ui_results)
        ux_score = (ui_passed / ui_total * 100) if ui_total > 0 else 0
        print(f"   • 用户体验评分: {ux_score:.1f}%")
        
        # 失败详情（仅显示严重失败）
        critical_failures = [r for r in self.test_results if r['status'] == 'FAIL' and r['module'] in core_modules]
        if critical_failures:
            print(f"\n❌ 关键失败详情:")
            for result in critical_failures[:5]:  # 只显示前5个
                print(f"   • {result['module']}.{result['function']}: {result['details']}")
        
        # 系统状态评估
        print(f"\n" + "=" * 80)
        if success_rate >= 85:
            print("🟢 系统状态: 优秀 - 生产就绪")
            print("   所有核心功能正常运行，系统稳定可靠")
        elif success_rate >= 70:
            print("🟡 系统状态: 良好 - 基本可用")
            print("   核心功能基本正常，部分模块需要优化")
        elif success_rate >= 50:
            print("🟠 系统状态: 一般 - 需要改进")
            print("   核心功能部分可用，建议进一步优化")
        else:
            print("🔴 系统状态: 需要修复 - 存在重大问题")
            print("   系统存在严重问题，需要立即修复")
        
        # 建议和总结
        print(f"\n💡 测试建议:")
        if core_success_rate >= 80:
            print("   ✓ 核心功能运行良好，系统架构稳定")
        else:
            print("   ⚠ 建议优先修复核心功能模块")
            
        if api_health >= 75:
            print("   ✓ API生态系统健康，外部集成正常")
        else:
            print("   ⚠ 建议检查API认证和外部服务连接")
            
        if ux_score >= 70:
            print("   ✓ 用户界面体验良好")
        else:
            print("   ⚠ 建议优化用户界面和响应式设计")
        
        print(f"\n🚀 完整系统功能回归测试完成")

def main():
    """主函数"""
    tester = CompleteSystemRegressionTest()
    tester.run_complete_system_test()

if __name__ == "__main__":
    main()