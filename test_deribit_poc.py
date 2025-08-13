#!/usr/bin/env python3
"""
Deribit POC测试脚本
用于测试POC脚本的各项功能
"""

import json
from deribit_options_poc import DeribitOptionsAnalyzer

def create_mock_trade_data():
    """创建模拟交易数据用于测试"""
    mock_trades = [
        {
            "instrument_name": "BTC-30AUG24-60000-C",
            "price": 2.5,
            "amount": 10.0,
            "direction": "buy",
            "timestamp": 1692541200000
        },
        {
            "instrument_name": "BTC-30AUG24-60000-P", 
            "price": 1.8,
            "amount": 5.0,
            "direction": "sell",
            "timestamp": 1692541260000
        },
        {
            "instrument_name": "BTC-27SEP24-65000-C",
            "price": 7.2,
            "amount": 8.0,
            "direction": "buy", 
            "timestamp": 1692541320000
        },
        {
            "instrument_name": "BTC-27SEP24-70000-P",
            "price": 12.8,
            "amount": 3.0,
            "direction": "sell",
            "timestamp": 1692541380000
        },
        {
            "instrument_name": "BTC-25OCT24-55000-C",
            "price": 15.5,
            "amount": 2.0,
            "direction": "buy",
            "timestamp": 1692541440000
        }
    ]
    return mock_trades

def test_poc_functionality():
    """测试POC脚本功能"""
    print("=== Deribit期权POC功能测试 ===\n")
    
    analyzer = DeribitOptionsAnalyzer()
    mock_trades = create_mock_trade_data()
    
    print(f"模拟交易数据: {len(mock_trades)} 笔交易")
    
    # 测试数据聚合功能
    print("\n1. 按价格分组测试 (5美元区间):")
    buckets, type_buckets = analyzer.aggregate_trades(
        mock_trades, bucket_size=5.0, group_by="price", split_by_type=True
    )
    
    analyzer.print_summary_table(buckets, type_buckets, split_by_type=True)
    
    # 测试按行权价分组
    print("\n2. 按行权价分组测试 (5000美元区间):")
    strike_buckets, strike_type_buckets = analyzer.aggregate_trades(
        mock_trades, bucket_size=5000.0, group_by="strike", split_by_type=True
    )
    
    analyzer.print_summary_table(strike_buckets, strike_type_buckets, split_by_type=True)
    
    # 测试CSV导出
    print("\n3. CSV导出测试:")
    analyzer.export_to_csv("test_trades.csv", mock_trades)
    
    print("\n测试完成!")

if __name__ == "__main__":
    test_poc_functionality()