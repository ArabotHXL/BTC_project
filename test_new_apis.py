#!/usr/bin/env python3
"""
测试新API数据源集成
验证Mempool.space、Blockchain.info和CoinGecko APIs
"""

import requests
import json
from datetime import datetime

def test_mempool_api():
    """测试Mempool.space API"""
    print("测试Mempool.space API...")
    try:
        response = requests.get('https://mempool.space/api/v1/blocks', timeout=10)
        if response.status_code == 200:
            blocks = response.json()
            if blocks:
                latest = blocks[0]
                block_reward = latest.get('extras', {}).get('reward', 0) / 100000000
                print(f"✅ 最新区块: {latest.get('height')}")
                print(f"   难度: {latest.get('difficulty', 0):,.0f}")
                print(f"   交易数: {latest.get('tx_count')}")
                print(f"   区块奖励: {block_reward:.4f} BTC")
                return True
        else:
            print(f"❌ HTTP错误: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        return False

def test_blockchain_hashrate_api():
    """测试Blockchain.info算力API"""
    print("\n测试Blockchain.info算力API...")
    try:
        response = requests.get('https://api.blockchain.info/charts/hash-rate?timespan=1days&format=json', timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('values'):
                hashrate_th = data['values'][-1]['y']
                hashrate_eh = hashrate_th / 1000000
                timestamp = data['values'][-1]['x']
                print(f"✅ 网络算力: {hashrate_eh:.2f} EH/s")
                print(f"   数据时间: {datetime.fromtimestamp(timestamp)}")
                return True
        else:
            print(f"❌ HTTP错误: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        return False

def test_coingecko_simple_api():
    """测试CoinGecko简单API"""
    print("\n测试CoinGecko简单API...")
    try:
        response = requests.get('https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd', timeout=10)
        if response.status_code == 200:
            data = response.json()
            if 'bitcoin' in data and 'usd' in data['bitcoin']:
                price = data['bitcoin']['usd']
                print(f"✅ BTC价格: ${price:,}")
                return True
            else:
                print("❌ 响应格式错误")
                return False
        elif response.status_code == 429:
            print("⚠️ API速率限制 (这是正常的)")
            return False
        else:
            print(f"❌ HTTP错误: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        return False

def main():
    print("=== 新API数据源测试 ===")
    
    results = []
    results.append(test_mempool_api())
    results.append(test_blockchain_hashrate_api())
    results.append(test_coingecko_simple_api())
    
    working_apis = sum(results)
    total_apis = len(results)
    
    print(f"\n=== 测试结果 ===")
    print(f"工作正常的API: {working_apis}/{total_apis}")
    
    if working_apis >= 2:
        print("✅ 系统有足够的数据源正常工作")
        print("分析引擎应该能够收集数据")
    else:
        print("⚠️ 可用数据源不足，需要检查网络连接")
    
    return working_apis >= 2

if __name__ == "__main__":
    main()