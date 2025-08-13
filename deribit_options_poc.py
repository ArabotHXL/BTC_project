#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deribit BTC期权交易数据POC脚本

功能说明:
- 获取最近15分钟的BTC期权交易数据
- 按期权价格进行分组统计
- 提供看涨/看跌期权的分类统计
- 支持CSV导出功能
- 使用Deribit公开API，无需认证

使用方法:
  # 默认15分钟窗口，5美元价格区间
  python deribit_options_poc.py --bucket 5

  # 包含看涨/看跌分类统计
  python deribit_options_poc.py --bucket 10 --by-type

  # 导出CSV文件
  python deribit_options_poc.py --csv deribit_trades_15m.csv

  # 自定义时间窗口（分钟）
  python deribit_options_poc.py --minutes 30

  # 按行权价分组（而非期权价格）
  python deribit_options_poc.py --by strike --bucket 1000
"""

import math
import time
import argparse
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Tuple, Optional
import requests
import csv
from collections import defaultdict

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Deribit API配置
BASE_URL = "https://www.deribit.com"
TRADES_ENDPOINT = f"{BASE_URL}/api/v2/public/get_last_trades_by_currency_and_time"

class DeribitOptionsAnalyzer:
    """Deribit期权数据分析器"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'BTC-Mining-Calculator-POC/1.0',
            'Accept': 'application/json'
        })
    
    def get_current_timestamp_ms(self) -> int:
        """获取当前UTC时间戳（毫秒）"""
        return int(datetime.now(timezone.utc).timestamp() * 1000)
    
    def parse_instrument_name(self, instrument_name: str) -> Tuple[str, float, str]:
        """
        解析期权合约名称
        格式: BTC-30AUG24-60000-C
        返回: (到期日, 行权价, 期权类型)
        """
        try:
            parts = instrument_name.split("-")
            if len(parts) >= 4:
                expiry_date = parts[1]
                strike_price = float(parts[2])
                option_type = "CALL" if parts[3].upper().startswith("C") else "PUT"
                return expiry_date, strike_price, option_type
        except (ValueError, IndexError) as e:
            logger.warning(f"无法解析合约名称 {instrument_name}: {e}")
        
        return "", float("nan"), "UNKNOWN"
    
    def create_bucket_label(self, value: float, bucket_size: float) -> str:
        """创建价格区间标签"""
        if math.isnan(value):
            return "N/A"
        
        lower_bound = math.floor(value / bucket_size) * bucket_size
        upper_bound = lower_bound + bucket_size
        
        # 避免负零显示
        lower_bound = 0.0 if abs(lower_bound) < 1e-12 else lower_bound
        upper_bound = 0.0 if abs(upper_bound) < 1e-12 else upper_bound
        
        return f"${lower_bound:.2f}–${upper_bound:.2f}"
    
    def fetch_option_trades(self, currency: str = "BTC", minutes: int = 15, 
                           kind: str = "option") -> List[Dict]:
        """
        获取期权交易数据
        
        Args:
            currency: 货币类型，默认BTC
            minutes: 时间窗口（分钟）
            kind: 合约类型，默认option
        
        Returns:
            交易数据列表
        """
        end_time = self.get_current_timestamp_ms()
        start_time = end_time - minutes * 60 * 1000
        
        all_trades = []
        params = {
            "currency": currency,
            "start_timestamp": start_time,
            "end_timestamp": end_time,
            "kind": kind,
            "count": 1000  # 每次请求最大数量
        }
        
        logger.info(f"开始获取{currency}期权交易数据，时间窗口：{minutes}分钟")
        
        while True:
            try:
                response = self.session.get(TRADES_ENDPOINT, params=params, timeout=30)
                response.raise_for_status()
                
                data = response.json()
                result = data.get("result", {})
                
                # 获取交易数据
                trades_batch = result.get("trades", [])
                if not trades_batch:
                    break
                
                all_trades.extend(trades_batch)
                logger.info(f"获取到 {len(trades_batch)} 笔交易，累计 {len(all_trades)} 笔")
                
                # 检查是否有更多数据
                has_more = result.get("has_more", False)
                continuation = result.get("continuation")
                
                if has_more and continuation:
                    params["continuation"] = continuation
                    time.sleep(0.1)  # 避免请求过快
                    continue
                else:
                    break
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"API请求失败: {e}")
                break
            except Exception as e:
                logger.error(f"数据处理错误: {e}")
                break
        
        logger.info(f"共获取到 {len(all_trades)} 笔交易数据")
        return all_trades
    
    def aggregate_trades(self, trades: List[Dict], bucket_size: float, 
                        group_by: str = "price", split_by_type: bool = False):
        """
        聚合交易数据
        
        Args:
            trades: 交易数据列表
            bucket_size: 分组区间大小
            group_by: 分组依据（'price' 或 'strike'）
            split_by_type: 是否按看涨/看跌分类
        
        Returns:
            (总体统计, 分类统计)
        """
        # 总体统计
        def create_bucket_stats():
            return {
                "trades_count": 0,
                "total_amount": 0.0,
                "avg_price": 0.0,
                "prices": []
            }
        
        buckets = defaultdict(create_bucket_stats)
        
        # 分类统计
        def create_type_stats():
            return {
                "CALL": {"trades_count": 0, "total_amount": 0.0},
                "PUT": {"trades_count": 0, "total_amount": 0.0}
            }
        
        type_buckets = defaultdict(create_type_stats)
        
        for trade in trades:
            instrument_name = trade.get("instrument_name", "")
            trade_price = float(trade.get("price", 0))
            trade_amount = float(trade.get("amount", 0))
            
            # 解析合约信息
            expiry, strike_price, option_type = self.parse_instrument_name(instrument_name)
            
            # 确定分组值
            if group_by == "price":
                group_value = trade_price
            elif group_by == "strike":
                group_value = strike_price
            else:
                continue
            
            if math.isnan(group_value) or group_value <= 0:
                continue
            
            bucket_label = self.create_bucket_label(group_value, bucket_size)
            
            # 更新总体统计
            buckets[bucket_label]["trades_count"] += 1
            buckets[bucket_label]["total_amount"] += trade_amount
            buckets[bucket_label]["prices"].append(trade_price)
            
            # 更新分类统计
            if split_by_type and option_type in ("CALL", "PUT"):
                type_buckets[bucket_label][option_type]["trades_count"] += 1
                type_buckets[bucket_label][option_type]["total_amount"] += trade_amount
        
        # 计算平均价格
        for bucket_data in buckets.values():
            if bucket_data["prices"]:
                bucket_data["avg_price"] = sum(bucket_data["prices"]) / len(bucket_data["prices"])
        
        # 按区间下限排序
        def sort_key(bucket_label: str) -> float:
            try:
                return float(bucket_label.split("$")[1].split("–")[0])
            except (IndexError, ValueError):
                return 0.0
        
        sorted_buckets = sorted(buckets.items(), key=lambda x: sort_key(x[0]))
        sorted_type_buckets = sorted(type_buckets.items(), key=lambda x: sort_key(x[0])) if split_by_type else []
        
        return sorted_buckets, sorted_type_buckets
    
    def print_summary_table(self, sorted_buckets, sorted_type_buckets, split_by_type: bool):
        """打印统计表格"""
        print("\n" + "="*60)
        print("BTC期权交易数据统计")
        print("="*60)
        
        # 总体统计表
        print(f"\n{'价格区间':>20} | {'交易笔数':>8} | {'总交易量':>12} | {'平均价格':>10}")
        print("-" * 65)
        
        total_trades = 0
        total_amount = 0.0
        
        for bucket_label, data in sorted_buckets:
            total_trades += data["trades_count"]
            total_amount += data["total_amount"]
            
            print(f"{bucket_label:>20} | {data['trades_count']:>8} | "
                  f"{data['total_amount']:>12.4f} | ${data['avg_price']:>9.2f}")
        
        print("-" * 65)
        print(f"{'总计':>20} | {total_trades:>8} | {total_amount:>12.4f} | {'':>10}")
        
        # 分类统计表
        if split_by_type and sorted_type_buckets:
            print(f"\n--- 看涨/看跌期权分类统计 ---")
            print(f"{'价格区间':>20} | {'看涨笔数':>8} | {'看涨量':>10} | {'看跌笔数':>8} | {'看跌量':>10}")
            print("-" * 70)
            
            for bucket_label, data in sorted_type_buckets:
                call_data = data['CALL']
                put_data = data['PUT']
                
                print(f"{bucket_label:>20} | {call_data['trades_count']:>8} | "
                      f"{call_data['total_amount']:>10.4f} | {put_data['trades_count']:>8} | "
                      f"{put_data['total_amount']:>10.4f}")
    
    def export_to_csv(self, filepath: str, trades: List[Dict]):
        """导出原始交易数据到CSV"""
        if not filepath or not trades:
            return
        
        fieldnames = [
            "timestamp", "instrument_name", "price", "amount", 
            "direction", "expiry", "strike_price", "option_type"
        ]
        
        try:
            with open(filepath, "w", newline="", encoding="utf-8") as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for trade in trades:
                    expiry, strike, opt_type = self.parse_instrument_name(
                        trade.get("instrument_name", "")
                    )
                    
                    row = {
                        "timestamp": trade.get("timestamp"),
                        "instrument_name": trade.get("instrument_name"),
                        "price": trade.get("price"),
                        "amount": trade.get("amount"),
                        "direction": trade.get("direction"),
                        "expiry": expiry,
                        "strike_price": strike if not math.isnan(strike) else "",
                        "option_type": opt_type
                    }
                    writer.writerow(row)
            
            logger.info(f"交易数据已导出到CSV文件: {filepath} (共{len(trades)}条记录)")
            
        except Exception as e:
            logger.error(f"CSV导出失败: {e}")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="Deribit BTC期权交易数据分析POC",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python deribit_options_poc.py --bucket 5 --minutes 15
  python deribit_options_poc.py --by-type --csv trades.csv
  python deribit_options_poc.py --by strike --bucket 1000
        """
    )
    
    parser.add_argument("--minutes", type=int, default=15,
                       help="时间窗口（分钟），默认15分钟")
    parser.add_argument("--bucket", type=float, default=5.0,
                       help="分组区间大小，默认5.0")
    parser.add_argument("--by", choices=["price", "strike"], default="price",
                       help="分组依据：价格(price)或行权价(strike)")
    parser.add_argument("--by-type", action="store_true",
                       help="是否按看涨/看跌期权分类统计")
    parser.add_argument("--csv", default="",
                       help="CSV导出文件路径（可选）")
    
    args = parser.parse_args()
    
    # 创建分析器实例
    analyzer = DeribitOptionsAnalyzer()
    
    try:
        # 获取交易数据
        trades = analyzer.fetch_option_trades(minutes=args.minutes)
        
        if not trades:
            print("未获取到交易数据，请检查网络连接或稍后重试")
            return
        
        print(f"\n成功获取 {len(trades)} 笔BTC期权交易数据")
        print(f"时间窗口: 最近 {args.minutes} 分钟")
        print(f"分组方式: 按{args.by}分组，区间大小: {args.bucket}")
        
        # 聚合分析
        buckets, type_buckets = analyzer.aggregate_trades(
            trades, args.bucket, args.by, args.by_type
        )
        
        # 显示统计结果
        analyzer.print_summary_table(buckets, type_buckets, args.by_type)
        
        # 导出CSV
        if args.csv:
            analyzer.export_to_csv(args.csv, trades)
            
    except KeyboardInterrupt:
        print("\n用户中断操作")
    except Exception as e:
        logger.error(f"程序执行错误: {e}")
        print(f"执行失败: {e}")

if __name__ == "__main__":
    main()