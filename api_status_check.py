#!/usr/bin/env python3
"""
API状态检查工具
检查所有API端点的运行状态
"""

import requests
import json
from datetime import datetime

def check_api_status():
    """检查API状态"""
    print("=" * 80)
    print("🔧 BTC挖矿计算器系统 - API状态检查")
    print(f"📅 检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # 模拟登录认证
    session = requests.Session()
    login_data = {'email': 'hxl2022hao@gmail.com'}
    
    try:
        login_response = session.post('http://localhost:5000/login', data=login_data, timeout=5)
        print(f"\n🔐 认证状态: {login_response.status_code}")
        
        if login_response.status_code == 200:
            print("✅ 认证成功")
        else:
            print("❌ 认证失败")
            return
            
    except Exception as e:
        print(f"❌ 认证连接失败: {e}")
        return
    
    # 定义要测试的API端点
    apis = [
        ('/api/btc_price', 'BTC价格API'),
        ('/api/network_stats', '网络统计API'), 
        ('/api/miners', '矿机数据API'),
        ('/api/sha256_mining_comparison', 'SHA256对比API'),
        ('/api/analytics/market-data', '分析市场数据API'),
        ('/api/analytics/latest-report', '分析报告API'),
        ('/api/analytics/technical-indicators', '技术指标API'),
        ('/api/analytics/price-history', '价格历史API')
    ]
    
    print("\n🔌 API端点状态检查:")
    print("-" * 60)
    
    success_count = 0
    total_count = len(apis)
    
    for endpoint, name in apis:
        try:
            response = session.get(f'http://localhost:5000{endpoint}', timeout=10)
            
            if response.status_code == 200:
                print(f"✅ {name}: 正常运行")
                success_count += 1
                
                # 显示关键数据
                try:
                    data = response.json()
                    if endpoint == '/api/btc_price':
                        price = data.get('btc_price', 'N/A')
                        print(f"   → BTC价格: ${price:,.2f}" if isinstance(price, (int, float)) else f"   → BTC价格: {price}")
                        
                    elif endpoint == '/api/network_stats':
                        hashrate = data.get('network_hashrate_eh', 'N/A')
                        difficulty = data.get('network_difficulty', 'N/A')
                        print(f"   → 算力: {hashrate}EH/s, 难度: {difficulty}")
                        
                    elif endpoint == '/api/miners':
                        miners = data.get('miners', [])
                        print(f"   → 矿机型号数量: {len(miners)}")
                        if len(miners) > 0:
                            print(f"   → 示例: {miners[0].get('name', 'Unknown')}")
                            
                    elif endpoint == '/api/sha256_mining_comparison':
                        comparison = data.get('comparison_data', [])
                        print(f"   → 币种对比数量: {len(comparison)}")
                        
                    elif endpoint == '/api/analytics/market-data':
                        market_data = data.get('data', {})
                        btc_price = market_data.get('btc_price', 'N/A')
                        hashrate = market_data.get('network_hashrate', 'N/A')
                        print(f"   → 市场数据: BTC=${btc_price}, 算力={hashrate}EH/s")
                        
                    elif endpoint == '/api/analytics/latest-report':
                        report = data.get('latest_report')
                        if report:
                            print(f"   → 最新报告: {report.get('date', 'N/A')}")
                        else:
                            print("   → 暂无报告数据")
                            
                    elif endpoint == '/api/analytics/technical-indicators':
                        indicators = data.get('indicators', [])
                        print(f"   → 技术指标数量: {len(indicators)}")
                        
                    elif endpoint == '/api/analytics/price-history':
                        history_data = data.get('price_history', [])
                        print(f"   → 历史数据点: {len(history_data)}")
                        
                except json.JSONDecodeError:
                    print("   → 响应格式非JSON")
                except Exception as e:
                    print(f"   → 数据解析错误: {e}")
                    
            else:
                print(f"❌ {name}: 状态码 {response.status_code}")
                
        except requests.exceptions.Timeout:
            print(f"⏰ {name}: 请求超时")
        except requests.exceptions.ConnectionError:
            print(f"🔌 {name}: 连接失败")
        except Exception as e:
            print(f"❌ {name}: 错误 - {str(e)}")
    
    print("-" * 60)
    print(f"\n📊 总结:")
    print(f"   • 总API数量: {total_count}")
    print(f"   • 正常运行: {success_count}")
    print(f"   • 故障数量: {total_count - success_count}")
    print(f"   • 成功率: {success_count/total_count*100:.1f}%")
    
    if success_count == total_count:
        print("\n🎉 所有API端点运行正常!")
    elif success_count >= total_count * 0.8:
        print("\n🟡 大部分API端点运行正常")
    else:
        print("\n🔴 多个API端点存在问题，需要检查")
    
    print("=" * 80)

if __name__ == "__main__":
    check_api_status()