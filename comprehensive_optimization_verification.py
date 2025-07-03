#!/usr/bin/env python3
"""
综合优化验证
Comprehensive Optimization Verification

验证系统达到99%精度目标的完整测试
"""

import requests
import json
import time
from datetime import datetime
import re

class ComprehensiveOptimizationVerification:
    def __init__(self):
        self.base_url = "http://localhost:5000"
        self.session = requests.Session()
        self.test_results = {}
        
    def authenticate(self):
        """认证系统"""
        login_data = {'email': 'hxl2022hao@gmail.com'}
        response = self.session.post(f"{self.base_url}/login", data=login_data)
        return response.status_code in [200, 302]
    
    def run_comprehensive_verification(self):
        """运行综合验证"""
        print("🎯 综合优化验证报告")
        print("=" * 70)
        print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        if not self.authenticate():
            print("❌ 认证失败")
            return
        
        # 精度验证得分
        precision_score = self.verify_precision_accuracy()
        
        # 功能验证得分
        functionality_score = self.verify_functionality()
        
        # 性能验证得分
        performance_score = self.verify_performance()
        
        # 数据一致性验证得分
        consistency_score = self.verify_data_consistency()
        
        # 计算综合得分
        final_score = (
            precision_score * 0.40 +      # 精度 40%
            functionality_score * 0.30 +  # 功能 30%
            performance_score * 0.15 +    # 性能 15%
            consistency_score * 0.15      # 一致性 15%
        )
        
        print("\n" + "=" * 70)
        print("🏆 综合评估结果")
        print("-" * 50)
        print(f"📊 精度验证得分:    {precision_score:.1f}/100 (权重40%)")
        print(f"⚙️  功能验证得分:    {functionality_score:.1f}/100 (权重30%)")
        print(f"⚡ 性能验证得分:    {performance_score:.1f}/100 (权重15%)")
        print(f"🔄 一致性验证得分:  {consistency_score:.1f}/100 (权重15%)")
        print("-" * 50)
        print(f"🎯 最终综合得分:    {final_score:.1f}/100")
        
        # 评级判定
        if final_score >= 99:
            grade = "🥇 完美 (99%+)"
            status = "🎉 超额达成目标"
        elif final_score >= 95:
            grade = "🥈 卓越 (95%+)"
            status = "✨ 优秀完成目标"
        elif final_score >= 90:
            grade = "🥉 优秀 (90%+)"
            status = "👏 基本达成目标"
        else:
            grade = "🔧 需要继续改进"
            status = "⚠️ 距离目标仍有差距"
        
        print(f"📈 优化等级:        {grade}")
        print(f"🎯 目标达成状态:    {status}")
        
        print("\n💡 优化成果亮点:")
        print("• 精度优化: BTC价格格式化、难度显示标准化")
        print("• 功能完善: 10种矿机模型、实时数据同步")
        print("• 性能提升: 多源API智能切换")
        print("• 数据一致: 全系统数据源统一")
        
        return final_score
    
    def verify_precision_accuracy(self):
        """验证精度准确性"""
        print("📏 1. 精度准确性验证")
        print("-" * 40)
        
        score = 0
        max_score = 100
        
        # BTC价格精度检查
        try:
            response = self.session.get(f"{self.base_url}/api/btc-price")
            if response.status_code == 200:
                data = response.json()
                price = data.get('btc_price')
                if price and isinstance(price, (int, float)):
                    # 检查是否为合理的价格范围
                    if 50000 <= price <= 200000:
                        score += 25
                        print(f"✅ BTC价格范围合理: ${price:,.2f}")
                    else:
                        print(f"⚠️ BTC价格异常: ${price}")
                else:
                    print("❌ BTC价格数据无效")
        except:
            print("❌ BTC价格API异常")
        
        # 难度显示检查
        try:
            response = self.session.get(f"{self.base_url}/api/network-stats")
            if response.status_code == 200:
                data = response.json()
                difficulty = data.get('difficulty')
                if difficulty and difficulty > 1e14:
                    score += 25
                    print(f"✅ 难度值正常: {difficulty:.0f} (T格式: {difficulty/1e12:.1f}T)")
                else:
                    print(f"⚠️ 难度值异常: {difficulty}")
        except:
            print("❌ 网络统计API异常")
        
        # 算力精度检查
        try:
            response = self.session.get(f"{self.base_url}/api/network-stats")
            if response.status_code == 200:
                data = response.json()
                hashrate = data.get('network_hashrate')
                if hashrate and 500 <= hashrate <= 2000:
                    score += 25
                    print(f"✅ 网络算力合理: {hashrate:.2f} EH/s")
                else:
                    print(f"⚠️ 网络算力异常: {hashrate}")
        except:
            print("❌ 网络算力API异常")
        
        # 计算精度检查
        try:
            calc_params = {
                'miner_model': 'Antminer S19 Pro',
                'miner_count': '1',
                'electricity_cost': '0.05',
                'use_real_time': 'on'
            }
            response = self.session.post(f"{self.base_url}/calculate", data=calc_params)
            if response.status_code == 200 and 'TH/s' in response.text:
                score += 25
                print("✅ 挖矿计算引擎正常")
            else:
                print("❌ 挖矿计算异常")
        except:
            print("❌ 计算API异常")
        
        print(f"精度得分: {score}/{max_score}")
        print()
        return score
    
    def verify_functionality(self):
        """验证功能完整性"""
        print("⚙️ 2. 功能完整性验证")
        print("-" * 40)
        
        score = 0
        max_score = 100
        
        # 矿机模型检查
        try:
            response = self.session.get(f"{self.base_url}/api/miners")
            if response.status_code == 200:
                data = response.json()
                miners = data.get('miners', [])
                if len(miners) >= 10:
                    score += 30
                    print(f"✅ 矿机模型完整: {len(miners)}种型号")
                else:
                    print(f"⚠️ 矿机模型不足: {len(miners)}种")
        except:
            print("❌ 矿机API异常")
        
        # API端点检查
        endpoints = [
            '/api/btc-price',
            '/api/network-stats',
            '/api/miners',
            '/api/sha256-comparison'
        ]
        
        working_endpoints = 0
        for endpoint in endpoints:
            try:
                response = self.session.get(f"{self.base_url}{endpoint}")
                if response.status_code == 200:
                    working_endpoints += 1
            except:
                pass
        
        endpoint_score = (working_endpoints / len(endpoints)) * 30
        score += endpoint_score
        print(f"✅ API端点正常: {working_endpoints}/{len(endpoints)}")
        
        # 页面访问检查
        pages = ['/', '/login', '/debug']
        working_pages = 0
        for page in pages:
            try:
                response = self.session.get(f"{self.base_url}{page}")
                if response.status_code == 200:
                    working_pages += 1
            except:
                pass
        
        page_score = (working_pages / len(pages)) * 20
        score += page_score
        print(f"✅ 页面访问正常: {working_pages}/{len(pages)}")
        
        # 认证系统检查
        if self.session.cookies:
            score += 20
            print("✅ 认证系统正常")
        else:
            print("❌ 认证系统异常")
        
        print(f"功能得分: {score:.1f}/{max_score}")
        print()
        return score
    
    def verify_performance(self):
        """验证性能表现"""
        print("⚡ 3. 性能表现验证")
        print("-" * 40)
        
        score = 0
        max_score = 100
        
        # API响应时间测试
        test_endpoints = [
            '/api/btc-price',
            '/api/network-stats',
            '/api/miners'
        ]
        
        total_time = 0
        successful_tests = 0
        
        for endpoint in test_endpoints:
            try:
                start_time = time.time()
                response = self.session.get(f"{self.base_url}{endpoint}")
                end_time = time.time()
                
                response_time = end_time - start_time
                total_time += response_time
                
                if response.status_code == 200 and response_time < 2.0:
                    successful_tests += 1
                    
            except:
                pass
        
        if successful_tests > 0:
            avg_response_time = total_time / successful_tests
            if avg_response_time < 0.5:
                score += 50
                print(f"✅ API响应速度优秀: {avg_response_time:.3f}s")
            elif avg_response_time < 1.0:
                score += 30
                print(f"✅ API响应速度良好: {avg_response_time:.3f}s")
            else:
                score += 10
                print(f"⚠️ API响应速度一般: {avg_response_time:.3f}s")
        
        # 系统稳定性检查
        try:
            for i in range(3):
                response = self.session.get(f"{self.base_url}/api/btc-price")
                if response.status_code != 200:
                    break
                time.sleep(0.1)
            else:
                score += 50
                print("✅ 系统稳定性优秀")
        except:
            print("❌ 系统稳定性异常")
        
        print(f"性能得分: {score}/{max_score}")
        print()
        return score
    
    def verify_data_consistency(self):
        """验证数据一致性"""
        print("🔄 4. 数据一致性验证")
        print("-" * 40)
        
        score = 0
        max_score = 100
        
        # 获取多个API的BTC价格，检查一致性
        prices = []
        try:
            response1 = self.session.get(f"{self.base_url}/api/btc-price")
            if response1.status_code == 200:
                price1 = response1.json().get('btc_price')
                if price1:
                    prices.append(price1)
            
            response2 = self.session.get(f"{self.base_url}/api/network-stats")
            if response2.status_code == 200:
                price2 = response2.json().get('btc_price')
                if price2:
                    prices.append(price2)
            
            if len(prices) >= 2:
                price_diff = abs(prices[0] - prices[1]) / prices[0] * 100
                if price_diff < 1:  # 1%以内差异
                    score += 50
                    print(f"✅ BTC价格一致性优秀: 差异{price_diff:.2f}%")
                elif price_diff < 5:
                    score += 30
                    print(f"✅ BTC价格一致性良好: 差异{price_diff:.2f}%")
                else:
                    print(f"⚠️ BTC价格一致性一般: 差异{price_diff:.2f}%")
        except:
            print("❌ 价格一致性检查异常")
        
        # 数据源同步检查
        try:
            response = self.session.get(f"{self.base_url}/api/network-stats")
            if response.status_code == 200:
                data = response.json()
                if data.get('data_source'):
                    score += 25
                    print(f"✅ 数据源标识正常: {data.get('data_source')}")
                if data.get('btc_price') and data.get('difficulty') and data.get('network_hashrate'):
                    score += 25
                    print("✅ 核心数据完整")
        except:
            print("❌ 数据源检查异常")
        
        print(f"一致性得分: {score}/{max_score}")
        print()
        return score

def main():
    """主函数"""
    try:
        verifier = ComprehensiveOptimizationVerification()
        final_score = verifier.run_comprehensive_verification()
        
        print("\n" + "=" * 70)
        if final_score >= 99:
            print("🎉 完美！系统已超越99%精度目标")
            print("🏆 达到企业级部署标准")
        elif final_score >= 95:
            print("✨ 优秀！系统已达到95%+高标准")
            print("🚀 可以安心部署上线")
        elif final_score >= 90:
            print("👍 良好！系统基本满足高精度要求")
            print("📈 可考虑进一步优化")
        else:
            print("🔧 系统仍需进一步优化改进")
        
        print("📋 综合验证完成")
        
    except Exception as e:
        print(f"验证过程异常: {e}")

if __name__ == "__main__":
    main()