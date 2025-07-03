#!/usr/bin/env python3
"""
检查系统状态工具
Check System Status Tool
"""

import requests
import json
from datetime import datetime
import pytz

def check_system_status():
    """检查系统整体状态"""
    base_url = "http://localhost:5000"
    
    print("🔍 检查系统状态")
    print("=" * 50)
    
    # 创建会话并登录
    session = requests.Session()
    
    # 模拟登录（使用拥有者邮箱）
    login_data = {
        'email': 'bysj2025@qq.com'
    }
    
    try:
        login_response = session.post(f"{base_url}/login", data=login_data, timeout=5)
        if login_response.status_code == 302 or 'dashboard' in login_response.text.lower():
            print("✅ 认证: 登录成功")
        else:
            print("⚠️ 认证: 登录状态未知")
    except Exception as e:
        print(f"❌ 认证: 登录失败 - {e}")
        return
    
    # 1. 检查服务器响应
    try:
        response = requests.get(f"{base_url}/", timeout=5)
        if response.status_code == 200:
            print("✅ 服务器: 正常运行")
        else:
            print(f"⚠️ 服务器: 状态码 {response.status_code}")
    except Exception as e:
        print(f"❌ 服务器: 连接失败 - {e}")
    
    # 2. 检查Market Data API
    try:
        response = session.get(f"{base_url}/api/analytics/market-data", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                market_data = data.get('data', {})
                btc_price = market_data.get('btc_price', 0)
                hashrate = market_data.get('network_hashrate', 0)
                timestamp = market_data.get('timestamp', '')
                
                print("✅ Market Data API: 正常")
                print(f"   BTC价格: ${btc_price:,}")
                print(f"   网络算力: {hashrate:.2f} EH/s")
                print(f"   更新时间: {timestamp}")
            else:
                print("⚠️ Market Data API: 无数据")
        else:
            print(f"⚠️ Market Data API: 状态码 {response.status_code}")
    except Exception as e:
        print(f"❌ Market Data API: 异常 - {e}")
    
    # 3. 检查Price History API
    try:
        response = session.get(f"{base_url}/api/analytics/price-history", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                history = data.get('data', [])
                print(f"✅ Price History API: 正常 ({len(history)}条记录)")
                if history:
                    latest = history[-1]
                    print(f"   最新记录: {latest.get('timestamp', '')}")
            else:
                print("⚠️ Price History API: 无数据")
        else:
            print(f"⚠️ Price History API: 状态码 {response.status_code}")
    except Exception as e:
        print(f"❌ Price History API: 异常 - {e}")
    
    # 4. 检查Technical Indicators API
    try:
        response = session.get(f"{base_url}/api/analytics/technical-indicators", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                indicators = data.get('data', {})
                rsi = indicators.get('rsi_14', 0)
                sma_20 = indicators.get('sma_20', 0)
                timestamp = indicators.get('timestamp', '')
                
                print("✅ Technical Indicators API: 正常")
                print(f"   RSI(14): {rsi}")
                print(f"   SMA(20): ${sma_20:,.2f}")
                print(f"   更新时间: {timestamp}")
            else:
                print("⚠️ Technical Indicators API: 无数据")
        else:
            print(f"⚠️ Technical Indicators API: 状态码 {response.status_code}")
    except Exception as e:
        print(f"❌ Technical Indicators API: 异常 - {e}")
    
    # 5. 计算下次刷新时间
    now = datetime.now()
    current_minute = now.minute
    
    if current_minute < 30:
        next_refresh_minute = 30
        next_refresh_hour = now.hour
    else:
        next_refresh_minute = 0
        next_refresh_hour = now.hour + 1
        if next_refresh_hour >= 24:
            next_refresh_hour = 0
    
    print("\n⏰ 刷新时间安排:")
    print(f"   当前时间: {now.strftime('%H:%M:%S')}")
    print(f"   下次刷新: {next_refresh_hour:02d}:{next_refresh_minute:02d}:00")
    
    # 计算剩余时间
    if current_minute < 30:
        minutes_left = 30 - current_minute
    else:
        minutes_left = 60 - current_minute
    
    print(f"   剩余时间: {minutes_left}分钟")
    
    print("\n📊 30分钟刷新计划:")
    print("   执行时间: 每小时的00分钟和30分钟")
    print("   包含数据: BTC价格、网络算力、技术指标")
    print("   数据源: CoinGecko, Blockchain.info, Mempool.space")

if __name__ == "__main__":
    check_system_status()