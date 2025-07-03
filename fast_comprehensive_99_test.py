#!/usr/bin/env python3
"""
快速全面99%准确率测试
Fast Comprehensive 99% Accuracy Test

优化版本，快速测试所有关键功能，确保99%准确率
"""

import requests
import json
import time
from datetime import datetime

class FastComprehensive99Test:
    def __init__(self):
        self.base_url = "http://0.0.0.0:5000"
        self.test_emails = [
            "hxl2022hao@gmail.com",  # 优先测试拥有者
            "testing123@example.com",
            "admin@example.com"
        ]
        self.test_results = []
        self.session = requests.Session()
        self.current_email = None
        self.start_time = datetime.now()
        
    def log_test(self, category: str, test_name: str, status: str, details: str = "", response_time: float = None):
        """记录测试结果"""
        result = {
            'category': category,
            'test_name': test_name,
            'status': status,
            'details': details,
            'response_time': round(response_time, 2) if response_time else None,
            'email': self.current_email
        }
        self.test_results.append(result)
        
        status_icon = "✅" if status == "成功" else "⚠️" if status == "警告" else "❌"
        print(f"{status_icon} [{category}] {test_name}: {status}")
        if details:
            print(f"   详情: {details}")

    def authenticate_with_email(self, email: str) -> bool:
        """快速认证"""
        try:
            start_time = time.time()
            self.session = requests.Session()
            login_data = {'email': email}
            response = self.session.post(f"{self.base_url}/login", data=login_data, timeout=5)
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code in [200, 302]:
                self.current_email = email
                self.log_test("AUTHENTICATION", f"邮箱认证", "成功", f"认证邮箱: {email}", response_time)
                return True
            else:
                self.log_test("AUTHENTICATION", f"邮箱认证", "失败", f"状态码: {response.status_code}", response_time)
                return False
        except Exception as e:
            self.log_test("AUTHENTICATION", f"邮箱认证", "失败", f"异常: {str(e)}")
            return False

    def test_core_apis(self):
        """测试核心API"""
        apis = [
            ("/api/btc-price", "BTC价格API"),
            ("/api/network-stats", "网络统计API"),
            ("/api/miners", "矿机列表API")
        ]
        
        for endpoint, name in apis:
            try:
                start_time = time.time()
                response = self.session.get(f"{self.base_url}{endpoint}", timeout=5)
                response_time = (time.time() - start_time) * 1000
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('success'):
                        # 验证关键数据
                        if 'btc-price' in endpoint and 'btc_price' in data:
                            btc_price = data['btc_price']
                            if 100000 <= btc_price <= 120000:
                                self.log_test("API_ENDPOINTS", name, "成功", f"BTC价格: ${btc_price:,.2f}", response_time)
                            else:
                                self.log_test("API_ENDPOINTS", name, "警告", f"价格异常: ${btc_price:,.2f}", response_time)
                        
                        elif 'network-stats' in endpoint:
                            hashrate = data.get('network_hashrate', 0)
                            difficulty = data.get('difficulty', 0)
                            if hashrate > 800 and difficulty > 1e14:
                                self.log_test("API_ENDPOINTS", name, "成功", f"算力: {hashrate:.1f}EH/s, 难度: {difficulty/1e12:.1f}T", response_time)
                            else:
                                self.log_test("API_ENDPOINTS", name, "警告", f"网络数据异常", response_time)
                        
                        elif 'miners' in endpoint and 'miners' in data:
                            miners_count = len(data['miners'])
                            if miners_count >= 10:
                                self.log_test("API_ENDPOINTS", name, "成功", f"矿机型号数: {miners_count}", response_time)
                            else:
                                self.log_test("API_ENDPOINTS", name, "警告", f"矿机数据不足: {miners_count}", response_time)
                        else:
                            self.log_test("API_ENDPOINTS", name, "成功", "数据格式正确", response_time)
                    else:
                        self.log_test("API_ENDPOINTS", name, "失败", f"API错误: {data.get('error')}", response_time)
                else:
                    self.log_test("API_ENDPOINTS", name, "失败", f"HTTP错误: {response.status_code}", response_time)
            except Exception as e:
                self.log_test("API_ENDPOINTS", name, "失败", f"请求异常: {str(e)}")

    def test_mining_calculations(self):
        """快速测试挖矿计算"""
        # 只测试3个代表性矿机
        test_miners = ["Antminer S19 Pro", "Antminer S21", "Antminer S21 XP"]
        successful = 0
        
        for miner in test_miners:
            try:
                start_time = time.time()
                calc_data = {
                    'miner_model': miner,
                    'miner_count': '50',
                    'site_power_mw': '5',
                    'electricity_cost': '0.06',
                    'use_real_time': 'true'
                }
                
                response = self.session.post(f"{self.base_url}/calculate", data=calc_data, timeout=10)
                response_time = (time.time() - start_time) * 1000
                
                if response.status_code == 200:
                    data = response.json()
                    if 'btc_mined' in data and 'revenue' in data:
                        btc_mined = data.get('btc_mined', {})
                        daily_btc = btc_mined.get('daily', 0) if isinstance(btc_mined, dict) else 0
                        
                        if daily_btc > 0:
                            successful += 1
                            self.log_test("MINING_CALCULATIONS", f"{miner}计算", "成功", 
                                        f"日产BTC: {daily_btc:.6f}", response_time)
                        else:
                            self.log_test("MINING_CALCULATIONS", f"{miner}计算", "失败", 
                                        "计算结果为0", response_time)
                    else:
                        self.log_test("MINING_CALCULATIONS", f"{miner}计算", "失败", 
                                    "缺少关键字段", response_time)
                else:
                    self.log_test("MINING_CALCULATIONS", f"{miner}计算", "失败", 
                                f"HTTP错误: {response.status_code}", response_time)
            except Exception as e:
                self.log_test("MINING_CALCULATIONS", f"{miner}计算", "失败", f"异常: {str(e)}")
        
        success_rate = (successful / len(test_miners)) * 100
        self.log_test("MINING_CALCULATIONS", "计算成功率", 
                     "成功" if success_rate >= 90 else "警告" if success_rate >= 70 else "失败",
                     f"成功率: {success_rate:.1f}% ({successful}/{len(test_miners)})")

    def test_ui_pages(self):
        """快速测试UI页面"""
        pages = [("/", "主页"), ("/analytics", "分析仪表盘")]
        
        for path, name in pages:
            try:
                start_time = time.time()
                response = self.session.get(f"{self.base_url}{path}", timeout=5)
                response_time = (time.time() - start_time) * 1000
                
                if response.status_code == 200:
                    content = response.text
                    if len(content) > 1000 and "<title>" in content:
                        self.log_test("USER_INTERFACE", f"{name}页面", "成功", 
                                    f"页面大小: {len(content)} 字符", response_time)
                    else:
                        self.log_test("USER_INTERFACE", f"{name}页面", "警告", 
                                    "页面内容可能不完整", response_time)
                else:
                    self.log_test("USER_INTERFACE", f"{name}页面", "失败", 
                                f"HTTP错误: {response.status_code}", response_time)
            except Exception as e:
                self.log_test("USER_INTERFACE", f"{name}页面", "失败", f"异常: {str(e)}")

    def test_data_consistency(self):
        """测试数据一致性"""
        try:
            # 获取多个价格源
            price_api = self.session.get(f"{self.base_url}/api/btc-price", timeout=3)
            network_api = self.session.get(f"{self.base_url}/api/network-stats", timeout=3)
            
            prices = []
            if price_api.status_code == 200:
                data = price_api.json()
                if data.get('success') and 'btc_price' in data:
                    prices.append(data['btc_price'])
            
            if network_api.status_code == 200:
                data = network_api.json()
                if data.get('success') and 'btc_price' in data:
                    prices.append(data['btc_price'])
            
            if len(prices) >= 2:
                variance = abs(prices[0] - prices[1]) / max(prices) * 100
                if variance <= 1.0:
                    self.log_test("DATA_CONSISTENCY", "价格一致性", "成功", 
                                f"价格差异: {variance:.3f}%")
                else:
                    self.log_test("DATA_CONSISTENCY", "价格一致性", "警告", 
                                f"价格差异过大: {variance:.3f}%")
            else:
                self.log_test("DATA_CONSISTENCY", "价格一致性", "失败", "无法获取足够数据")
                
        except Exception as e:
            self.log_test("DATA_CONSISTENCY", "价格一致性", "失败", f"异常: {str(e)}")

    def run_fast_99_test(self):
        """运行快速99%测试"""
        print("开始快速全面99%准确率测试")
        print(f"测试时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)
        
        # 使用拥有者邮箱进行完整测试
        owner_email = "hxl2022hao@gmail.com"
        print(f"\n🔐 使用拥有者邮箱测试: {owner_email}")
        
        if self.authenticate_with_email(owner_email):
            print(f"\n📊 测试核心API")
            self.test_core_apis()
            
            print(f"\n⛏️ 测试挖矿计算")
            self.test_mining_calculations()
            
            print(f"\n🖥️ 测试用户界面")
            self.test_ui_pages()
            
            print(f"\n📊 测试数据一致性")
            self.test_data_consistency()
        
        # 快速验证其他邮箱
        print(f"\n🔐 快速验证其他邮箱")
        for email in ["testing123@example.com", "admin@example.com"]:
            if self.authenticate_with_email(email):
                # 只测试一个简单API验证认证有效
                try:
                    response = self.session.get(f"{self.base_url}/api/btc-price", timeout=3)
                    if response.status_code == 200:
                        self.log_test("MULTI_USER", f"{email}访问验证", "成功", "API访问正常")
                    else:
                        self.log_test("MULTI_USER", f"{email}访问验证", "失败", f"API访问失败: {response.status_code}")
                except:
                    self.log_test("MULTI_USER", f"{email}访问验证", "失败", "API请求异常")
        
        self.generate_fast_report()

    def generate_fast_report(self):
        """生成快速测试报告"""
        end_time = datetime.now()
        total_time = (end_time - self.start_time).total_seconds()
        
        # 统计结果
        total_tests = len(self.test_results)
        successful_tests = len([r for r in self.test_results if r['status'] == '成功'])
        warning_tests = len([r for r in self.test_results if r['status'] == '警告'])
        failed_tests = len([r for r in self.test_results if r['status'] == '失败'])
        
        success_rate = (successful_tests / total_tests) * 100 if total_tests > 0 else 0
        functional_rate = ((successful_tests + warning_tests) / total_tests) * 100 if total_tests > 0 else 0
        
        print("\n" + "="*60)
        print("快速99%准确率测试报告")
        print("="*60)
        
        # 按类别统计
        categories = {}
        for result in self.test_results:
            category = result['category']
            if category not in categories:
                categories[category] = {'成功': 0, '警告': 0, '失败': 0}
            categories[category][result['status']] += 1
        
        for category, stats in categories.items():
            total_cat = sum(stats.values())
            success_cat = stats['成功']
            rate_cat = (success_cat / total_cat) * 100 if total_cat > 0 else 0
            
            print(f"\n[{category}] 测试结果:")
            for status, count in stats.items():
                icon = "✅" if status == "成功" else "⚠️" if status == "警告" else "❌"
                print(f"  {icon} {status}: {count}")
            print(f"     类别成功率: {rate_cat:.1f}%")
        
        print(f"\n🎯 总体统计:")
        print(f"   总测试数: {total_tests}")
        print(f"   成功: {successful_tests} ({success_rate:.1f}%)")
        print(f"   警告: {warning_tests} ({warning_tests/total_tests*100:.1f}%)")
        print(f"   失败: {failed_tests} ({failed_tests/total_tests*100:.1f}%)")
        print(f"   功能可用率: {functional_rate:.1f}%")
        print(f"   测试耗时: {total_time:.1f}秒")
        
        # 99%达成评估
        target_achieved = success_rate >= 99.0
        print(f"\n🎯 99%目标达成: {'是' if target_achieved else '否'}")
        if not target_achieved:
            gap = 99.0 - success_rate
            print(f"🎯 距离99%目标还需提升: {gap:.1f}%")
        
        # 准确率等级
        if success_rate >= 99:
            grade = "🥇 完美级别 (99%+)"
        elif success_rate >= 95:
            grade = "🥈 卓越级别 (95-99%)"
        elif success_rate >= 90:
            grade = "🥉 良好级别 (90-95%)"
        else:
            grade = "⚠️ 需要改进 (<90%)"
            
        print(f"📊 准确率等级: {grade}")
        
        # 保存报告
        report_filename = f"fast_99_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_filename, 'w', encoding='utf-8') as f:
            json.dump({
                'summary': {
                    'total_tests': total_tests,
                    'success_rate': success_rate,
                    'functional_rate': functional_rate,
                    'target_achieved': target_achieved,
                    'grade': grade,
                    'duration': total_time
                },
                'results': self.test_results
            }, f, ensure_ascii=False, indent=2)
        
        print(f"\n📋 报告已保存: {report_filename}")
        print(f"快速99%准确率测试完成！")

def main():
    test = FastComprehensive99Test()
    test.run_fast_99_test()

if __name__ == "__main__":
    main()