#!/usr/bin/env python3
"""
BTC Price Monitor
实时监控BTC价格和网络数据
"""

import requests
import json
from datetime import datetime

def get_current_btc_data():
    """获取当前BTC价格和网络数据"""
    print("💰 Bitcoin Market Data")
    print("=" * 40)
    
    try:
        # CoinGecko价格数据
        price_response = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd", timeout=10)
        if price_response.status_code == 200:
            price_data = price_response.json()
            btc_price = price_data['bitcoin']['usd']
            print(f"BTC Price: ${btc_price:,}")
        
        # 网络难度数据
        difficulty_response = requests.get("https://blockchain.info/q/getdifficulty", timeout=10)
        if difficulty_response.status_code == 200:
            difficulty = float(difficulty_response.text)
            print(f"Network Difficulty: {difficulty/1e12:.2f}T")
            
            # 计算网络算力
            hashrate_eh = difficulty * 2**32 / (600 * 1e18)
            print(f"Network Hashrate: {hashrate_eh:.1f} EH/s")
        
        # 区块计数
        blocks_response = requests.get("https://blockchain.info/q/getblockcount", timeout=10)
        if blocks_response.status_code == 200:
            block_count = int(blocks_response.text)
            print(f"Current Block: #{block_count:,}")
        
        print(f"Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 价格分析
        print("\n📈 Price Analysis:")
        if btc_price > 100000:
            print("Status: Above $100K milestone")
        else:
            print(f"Distance to $100K: ${100000 - btc_price:,}")
            
        # 挖矿收益估算 (1 TH/s)
        daily_btc_per_th = (1e12 / hashrate_eh / 1e18) * 144 * 3.125
        daily_usd_per_th = daily_btc_per_th * btc_price
        
        print(f"\n⚡ Mining Profitability (per TH/s):")
        print(f"Daily BTC: {daily_btc_per_th:.8f}")
        print(f"Daily USD: ${daily_usd_per_th:.4f}")
        
    except Exception as e:
        print(f"Error fetching data: {str(e)}")

if __name__ == "__main__":
    get_current_btc_data()