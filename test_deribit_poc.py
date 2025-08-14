#!/usr/bin/env python3
"""
Deribit POC 测试脚本
测试API连接和基本功能
"""

import sys
import time
from deribit_options_poc import DeribitDataCollector, DataStorage, PriceRangeAnalyzer, DeribitAnalysisPOC

def test_api_connection():
    """测试API连接"""
    print("测试Deribit API连接...")
    
    collector = DeribitDataCollector()
    
    # 测试获取服务器时间
    result = collector.make_request("public/get_time")
    if result:
        print(f"✅ API连接成功！服务器时间: {result}")
    else:
        print("❌ API连接失败")
        return False
    
    return True

def test_get_instruments():
    """测试获取合约列表"""
    print("\n测试获取BTC期权合约...")
    
    collector = DeribitDataCollector()
    instruments = collector.get_instruments("BTC", "option")
    
    if instruments:
        print(f"✅ 成功获取 {len(instruments)} 个期权合约")
        print(f"示例合约: {instruments[0]['instrument_name']}")
        return instruments[0]['instrument_name']
    else:
        print("❌ 无法获取期权合约")
        return None

def test_get_trades(instrument_name):
    """测试获取交易数据"""
    print(f"\n测试获取交易数据: {instrument_name}")
    
    collector = DeribitDataCollector()
    trades = collector.get_last_trades(instrument_name, count=10)
    
    if trades:
        print(f"✅ 成功获取 {len(trades)} 条交易数据")
        print(f"最新交易: 价格${trades[0].price}, 数量{trades[0].amount}")
        return trades
    else:
        print("❌ 无法获取交易数据")
        return []

def test_data_storage():
    """测试数据存储"""
    print("\n测试数据存储...")
    
    storage = DataStorage("test_trades.db")
    print("✅ 数据库初始化完成")
    return True

def test_price_analysis(trades):
    """测试价格分析"""
    print(f"\n测试价格分析 ({len(trades)} 条交易)...")
    
    if not trades:
        print("❌ 没有交易数据进行分析")
        return
    
    analyzer = PriceRangeAnalyzer()
    analysis = analyzer.analyze_by_price_ranges(trades, num_ranges=5)
    
    if analysis:
        print(f"✅ 价格分析完成，生成 {len(analysis)} 个价格区间")
        for item in analysis:
            print(f"  {item.price_range}: {item.trade_count}笔, {item.percentage:.1f}%")
    else:
        print("❌ 价格分析失败")

def run_full_test():
    """运行完整测试"""
    print("🚀 开始Deribit POC完整测试\n")
    
    # 1. 测试API连接
    if not test_api_connection():
        return
    
    # 2. 测试获取合约
    instrument_name = test_get_instruments()
    if not instrument_name:
        return
    
    # 3. 测试获取交易数据
    trades = test_get_trades(instrument_name)
    
    # 4. 测试数据存储
    test_data_storage()
    
    # 5. 测试价格分析
    test_price_analysis(trades)
    
    print(f"\n✅ 所有测试完成！可以使用以下命令运行POC:")
    print(f"python deribit_options_poc.py --instrument {instrument_name}")
    print(f"python deribit_options_poc.py --list")
    print(f"python deribit_options_poc.py --schedule 15")

if __name__ == "__main__":
    run_full_test()