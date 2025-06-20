#!/usr/bin/env python3
"""
前端信息显示完整模拟测试
Complete frontend information display simulation test
"""

import requests
import json
import re
from datetime import datetime

class FrontendSimulationTest:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.session = requests.Session()
        
    def authenticate(self):
        """用户认证"""
        response = self.session.post(f"{self.base_url}/login", 
                                   data={'email': 'user@example.com'})
        return response.status_code == 200
    
    def get_page_content(self):
        """获取页面内容"""
        response = self.session.get(self.base_url)
        return response.text if response.status_code == 200 else None
    
    def extract_initial_data(self, content):
        """提取页面初始数据"""
        # 提取初始数据
        start = content.find('window.initialData = {')
        if start == -1:
            return None
            
        # 找到完整的JavaScript对象
        brace_count = 0
        start_data = start + len('window.initialData = ')
        for i, char in enumerate(content[start_data:]):
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    end = start_data + i + 1
                    break
        else:
            return None
            
        data_str = content[start_data:end]
        try:
            return json.loads(data_str)
        except:
            return "数据解析失败，但存在"
    
    def check_html_elements(self, content):
        """检查关键HTML元素"""
        elements = {
            'miner_select': 'id="miner-model"',
            'site_power': 'id="site-power-mw"',
            'miner_count': 'id="miner-count"',
            'btc_price_input': 'id="btc-price-input"',
            'calculate_form': 'id="mining-calculator-form"',
            'results_card': 'id="results-card"',
            'client_profit_card': 'id="client-profit-card"',
            'btc_method1_card': 'id="btc-method1-daily-card"',
            'btc_method2_card': 'id="btc-method2-daily-card"',
            'total_hashrate_display': 'id="total-hashrate-display"',
            'total_power_display': 'id="total-power-display"'
        }
        
        found_elements = {}
        for name, element_id in elements.items():
            found_elements[name] = element_id in content
            
        return found_elements
    
    def submit_calculation(self):
        """提交计算请求"""
        calc_data = {
            'miner_model': 'Antminer S19 Pro',
            'site_power_mw': '4.0',
            'miner_count': '1230',
            'hashrate': '110',
            'power_consumption': '3250',
            'total_hashrate': '135300',
            'total_power': '3997500',
            'electricity_cost': '0.05',
            'client_electricity_cost': '0.06',
            'maintenance_fee': '5000',
            'host_investment': '800000',
            'client_investment': '0',
            'btc_price': '103500',
            'use_real_time': 'on'
        }
        
        response = self.session.post(f"{self.base_url}/calculate", data=calc_data)
        if response.status_code == 200:
            return response.json()
        return None
    
    def analyze_calculation_response(self, response_data):
        """分析计算响应数据"""
        analysis = {
            'success': response_data.get('success', False),
            'has_btc_mined': 'btc_mined' in response_data,
            'has_client_profit': 'client_profit' in response_data,
            'has_profitability': 'profitability' in response_data,
            'data_keys': list(response_data.keys())
        }
        
        # 提取关键数值
        if analysis['has_btc_mined']:
            btc_data = response_data['btc_mined']
            analysis['btc_daily'] = btc_data.get('daily', 0)
            analysis['btc_monthly'] = btc_data.get('monthly', 0)
            
        if analysis['has_client_profit']:
            profit_data = response_data['client_profit']
            analysis['client_daily'] = profit_data.get('daily', 0)
            analysis['client_monthly'] = profit_data.get('monthly', 0)
            
        # 检查设备信息
        analysis['miner_count'] = response_data.get('miner_count', 0)
        analysis['total_hashrate'] = response_data.get('total_hashrate_th', 0)
        analysis['total_power'] = response_data.get('total_power_w', 0)
        
        return analysis
    
    def run_complete_simulation(self):
        """运行完整模拟测试"""
        print("前端信息显示完整模拟测试")
        print("=" * 50)
        print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # 1. 用户认证
        print("1. 用户认证测试...")
        if not self.authenticate():
            print("✗ 认证失败")
            return False
        print("✓ 认证成功")
        
        # 2. 获取页面内容
        print("\n2. 页面内容获取...")
        content = self.get_page_content()
        if not content:
            print("✗ 页面获取失败")
            return False
        print(f"✓ 页面获取成功 (大小: {len(content):,} 字符)")
        
        # 3. 检查初始数据嵌入
        print("\n3. 初始数据检查...")
        initial_data = self.extract_initial_data(content)
        if initial_data:
            print("✓ 初始数据成功嵌入")
            if isinstance(initial_data, dict):
                print(f"  - 网络数据: {'✓' if 'network' in initial_data else '✗'}")
                print(f"  - 矿机数据: {'✓' if 'miners' in initial_data else '✗'}")
                if 'miners' in initial_data:
                    print(f"  - 矿机数量: {len(initial_data['miners'])}")
                if 'network' in initial_data:
                    network = initial_data['network']
                    print(f"  - BTC价格: ${network.get('btc_price', 0):,.0f}")
        else:
            print("✗ 初始数据缺失")
        
        # 4. 检查HTML元素
        print("\n4. HTML元素检查...")
        elements = self.check_html_elements(content)
        for element_name, found in elements.items():
            status = "✓" if found else "✗"
            print(f"  {element_name}: {status}")
        
        # 5. 提交计算测试
        print("\n5. 计算功能测试...")
        calc_result = self.submit_calculation()
        if calc_result:
            print("✓ 计算请求成功")
            
            # 分析响应数据
            analysis = self.analyze_calculation_response(calc_result)
            
            print(f"\n6. 响应数据分析:")
            print(f"  计算成功: {'✓' if analysis['success'] else '✗'}")
            print(f"  包含BTC挖矿数据: {'✓' if analysis['has_btc_mined'] else '✗'}")
            print(f"  包含客户收益数据: {'✓' if analysis['has_client_profit'] else '✗'}")
            print(f"  包含收益分析数据: {'✓' if analysis['has_profitability'] else '✗'}")
            
            if analysis['has_btc_mined']:
                print(f"\n  BTC挖矿收益:")
                print(f"    每日: {analysis.get('btc_daily', 0):.8f} BTC")
                print(f"    每月: {analysis.get('btc_monthly', 0):.6f} BTC")
                
            if analysis['has_client_profit']:
                print(f"\n  客户收益:")
                print(f"    每日: ${analysis.get('client_daily', 0):,.2f}")
                print(f"    每月: ${analysis.get('client_monthly', 0):,.2f}")
                
            print(f"\n  设备信息:")
            print(f"    矿机数量: {analysis.get('miner_count', 0):,}")
            print(f"    总算力: {analysis.get('total_hashrate', 0):,.0f} TH/s")
            print(f"    总功耗: {analysis.get('total_power', 0):,.0f} W")
            
            print(f"\n  数据结构键值: {analysis['data_keys']}")
            
        else:
            print("✗ 计算请求失败")
            
        # 7. 前端显示问题诊断
        print(f"\n7. 前端显示问题诊断:")
        if calc_result and analysis['success']:
            print("  后端计算: ✓ 正常工作")
            if analysis['has_client_profit'] and analysis.get('client_monthly', 0) > 0:
                print("  月收益数据: ✓ 存在且有效")
                print("  \n  可能的前端问题:")
                print("    1. JavaScript缓存问题 - 需要强制刷新")
                print("    2. DOM元素ID不匹配 - client-profit-card")
                print("    3. 数据映射错误 - client_profit.monthly路径")
                print("    4. CSS显示问题 - 元素被隐藏")
            else:
                print("  月收益数据: ✗ 缺失或无效")
        else:
            print("  后端计算: ✗ 存在问题")
            
        return True

def main():
    """主测试函数"""
    test = FrontendSimulationTest()
    test.run_complete_simulation()

if __name__ == "__main__":
    main()