#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Multi-Exchange BTC Options Trading Data Collector
Integrates Deribit, OKX, and Binance options data collection
"""
import argparse
import math
import time
import requests
import logging
import sqlite3
import json
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from typing import List, Dict, Tuple, Any

logger = logging.getLogger(__name__)

class MultiExchangeCollector:
    """多交易所BTC期权数据收集器"""
    
    def __init__(self, db_path="deribit_trades.db"):
        self.db_path = db_path
        self.setup_database()
    
    def setup_database(self):
        """设置数据库表结构"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建多交易所交易表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS multi_exchange_trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                exchange TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                instrument TEXT NOT NULL,
                price REAL NOT NULL,
                amount REAL NOT NULL,
                side TEXT,
                expiry TEXT,
                strike REAL,
                option_type TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_exchange ON multi_exchange_trades(exchange)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON multi_exchange_trades(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_instrument ON multi_exchange_trades(instrument)')
        
        # 创建聚合分析表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bucket_analysis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bucket_range TEXT NOT NULL,
                bucket_type TEXT NOT NULL, -- 'price' or 'strike'
                bucket_width REAL NOT NULL,
                trades_count INTEGER NOT NULL,
                total_amount REAL NOT NULL,
                call_trades INTEGER DEFAULT 0,
                call_amount REAL DEFAULT 0,
                put_trades INTEGER DEFAULT 0,
                put_amount REAL DEFAULT 0,
                analysis_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                time_window_minutes INTEGER NOT NULL
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("多交易所数据库表创建完成")
    
    @staticmethod
    def now_ms():
        """获取当前时间戳（毫秒）"""
        return int(datetime.now(timezone.utc).timestamp() * 1000)
    
    @staticmethod
    def bucket_label(value, step):
        """生成分桶标签 - 高价在前，低价在后，带美元符号"""
        lo = math.floor(value / step) * step
        hi = lo + step
        return f"${int(hi)} - ${int(lo)}"
    
    @staticmethod
    def parse_generic(name):
        """解析期权合约名称，提取到期日、行权价、类型"""
        # BTC-30AUG24-60000-C / BTC-240829-60000-C
        parts = name.split("-")
        if len(parts) >= 4:
            strike = float(parts[2])
            typ = "CALL" if parts[3].upper().startswith("C") else "PUT"
            expiry = parts[1]
            return expiry, strike, typ
        return "", float("nan"), ""
    
    def fetch_deribit(self, minutes=15):
        """获取Deribit交易数据"""
        logger.info("开始获取Deribit数据...")
        url = "https://www.deribit.com/api/v2/public/get_last_trades_by_currency_and_time"
        end = self.now_ms()
        start = end - minutes * 60 * 1000
        
        try:
            response = requests.get(url, params={
                "currency": "BTC",
                "start_timestamp": start,
                "end_timestamp": end,
                "kind": "option"
            }, timeout=30)
            response.raise_for_status()
            
            trades = []
            for trade in response.json().get("result", {}).get("trades", []):
                expiry, strike, typ = self.parse_generic(trade["instrument_name"])
                trades.append({
                    "exchange": "Deribit",
                    "timestamp": trade["timestamp"],
                    "instrument": trade["instrument_name"],
                    "price": float(trade["price"]),
                    "amount": float(trade["amount"]),
                    "side": trade.get("direction", ""),
                    "expiry": expiry,
                    "strike": strike,
                    "option_type": typ
                })
            
            logger.info(f"Deribit获取到 {len(trades)} 笔交易")
            return trades
            
        except Exception as e:
            logger.error(f"Deribit数据获取失败: {e}")
            return []
    
    def fetch_okx(self, minutes=15, max_instruments=400):
        """获取OKX交易数据"""
        logger.info("开始获取OKX数据...")
        try:
            # 获取期权合约列表
            instruments_response = requests.get(
                "https://www.okx.com/api/v5/public/instruments",
                params={"instType": "OPTION", "uly": "BTC-USD"},
                timeout=30
            )
            instruments_response.raise_for_status()
            instruments = instruments_response.json().get("data", [])
            
            trades = []
            cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes)
            
            # 限制处理的合约数量
            for inst in instruments[:max_instruments]:
                inst_id = inst["instId"]
                
                try:
                    trades_response = requests.get(
                        "https://www.okx.com/api/v5/market/history-trades",
                        params={"instId": inst_id, "limit": "100"},
                        timeout=10  # 减少超时时间
                    )
                    trades_response.raise_for_status()
                    
                    trade_data = trades_response.json().get("data", [])
                    if not trade_data:
                        continue
                    
                    for trade in trade_data:
                        # 检查必需字段是否存在
                        if not all(key in trade for key in ["ts", "fillPx", "sz"]):
                            continue
                            
                        try:
                            ts = datetime.fromtimestamp(float(trade["ts"]) / 1000, tz=timezone.utc)
                            if ts < cutoff:
                                continue
                            
                            price = float(trade["fillPx"])
                            amount = float(trade["sz"])
                            
                            # 过滤无效价格数据
                            if price <= 0 or amount <= 0:
                                continue
                            
                            expiry, strike, typ = self.parse_generic(inst_id)
                            trades.append({
                                "exchange": "OKX",
                                "timestamp": int(float(trade["ts"])),
                                "instrument": inst_id,
                                "price": price,
                                "amount": amount,
                                "side": trade.get("side", ""),
                                "expiry": expiry,
                                "strike": strike,
                                "option_type": typ
                            })
                        except (ValueError, KeyError) as ve:
                            continue  # 跳过无效的交易数据
                    
                    time.sleep(0.1)  # 增加节流延迟
                    
                except (requests.exceptions.RequestException, requests.exceptions.Timeout) as e:
                    logger.warning(f"OKX合约 {inst_id} 网络请求失败: {e}")
                    continue
                except Exception as e:
                    logger.warning(f"OKX合约 {inst_id} 获取失败: {e}")
                    continue
            
            logger.info(f"OKX获取到 {len(trades)} 笔交易")
            return trades
            
        except Exception as e:
            logger.error(f"OKX数据获取失败: {e}")
            return []
    
    def fetch_binance(self, minutes=15, max_symbols=400):
        """获取Binance期权交易数据"""
        logger.info("开始获取Binance数据...")
        try:
            # 获取期权交易对信息
            info_response = requests.get("https://eapi.binance.com/eapi/v1/exchangeInfo", timeout=30)
            info_response.raise_for_status()
            info = info_response.json()
            symbols = info.get("optionSymbols", [])
            
            trades = []
            cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes)
            
            # 只处理BTC相关的期权
            btc_symbols = [s for s in symbols[:max_symbols] if s.get("underlying", "").startswith("BTC")]
            
            for symbol_info in btc_symbols:
                symbol = symbol_info["symbol"]
                
                try:
                    trades_response = requests.get(
                        "https://eapi.binance.com/eapi/v1/trades",
                        params={"symbol": symbol},
                        timeout=10
                    )
                    trades_response.raise_for_status()
                    
                    trade_data = trades_response.json()
                    if not isinstance(trade_data, list):
                        continue
                    
                    for trade in trade_data:
                        # 检查必需字段
                        if not all(key in trade for key in ["time", "price", "qty"]):
                            continue
                            
                        try:
                            ts = datetime.fromtimestamp(trade["time"] / 1000, tz=timezone.utc)
                            if ts < cutoff:
                                continue
                            
                            price = float(trade["price"])
                            amount = float(trade["qty"])
                            
                            # 过滤无效数据
                            if price <= 0 or amount <= 0:
                                continue
                            
                            expiry, strike, typ = self.parse_generic(symbol)
                            trades.append({
                                "exchange": "Binance",
                                "timestamp": trade["time"],
                                "instrument": symbol,
                                "price": price,
                                "amount": amount,
                                "side": "",  # Binance公共API不提供方向信息
                                "expiry": expiry,
                                "strike": strike,
                                "option_type": typ
                            })
                        except (ValueError, KeyError):
                            continue
                    
                    time.sleep(0.1)  # 增加节流延迟
                    
                except (requests.exceptions.RequestException, requests.exceptions.Timeout) as e:
                    logger.warning(f"Binance合约 {symbol} 网络请求失败: {e}")
                    continue
                except Exception as e:
                    logger.warning(f"Binance合约 {symbol} 获取失败: {e}")
                    continue
            
            logger.info(f"Binance获取到 {len(trades)} 笔交易")
            return trades
            
        except Exception as e:
            logger.error(f"Binance数据获取失败: {e}")
            return []
    
    def collect_all_exchanges(self, minutes=15, max_okx=400, max_binance=400):
        """收集所有交易所数据"""
        logger.info(f"开始收集最近 {minutes} 分钟的多交易所数据...")
        
        all_trades = []
        
        # 收集各交易所数据
        all_trades.extend(self.fetch_deribit(minutes))
        all_trades.extend(self.fetch_okx(minutes, max_okx))
        all_trades.extend(self.fetch_binance(minutes, max_binance))
        
        logger.info(f"总共收集到 {len(all_trades)} 笔交易")
        
        # 保存到数据库
        if all_trades:
            self.save_trades(all_trades)
        
        return all_trades
    
    def save_trades(self, trades):
        """保存交易数据到数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for trade in trades:
            cursor.execute('''
                INSERT INTO multi_exchange_trades 
                (exchange, timestamp, instrument, price, amount, side, expiry, strike, option_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                trade["exchange"],
                trade["timestamp"],
                trade["instrument"],
                trade["price"],
                trade["amount"],
                trade["side"],
                trade["expiry"],
                trade["strike"],
                trade["option_type"]
            ))
        
        conn.commit()
        conn.close()
        logger.info(f"已保存 {len(trades)} 笔交易到数据库")
    
    def aggregate_analysis(self, trades, bucket_width, by="price", by_type=False):
        """聚合分析交易数据"""
        agg = defaultdict(lambda: {"trades": 0, "amount": 0.0})
        cp = defaultdict(lambda: {"CALL": {"trades": 0, "amount": 0.0}, "PUT": {"trades": 0, "amount": 0.0}})
        
        for trade in trades:
            key_val = trade[by] if by in trade else trade.get("strike" if by == "strike" else "price", 0)
            if math.isnan(key_val):
                continue
            
            bucket = self.bucket_label(key_val, bucket_width)
            agg[bucket]["trades"] += 1
            agg[bucket]["amount"] += trade["amount"]
            
            if by_type and trade.get("option_type") in ("CALL", "PUT"):
                cp[bucket][trade["option_type"]]["trades"] += 1
                cp[bucket][trade["option_type"]]["amount"] += trade["amount"]
        
        # 排序 - 按高价排序（从高到低）
        def sort_key(k):
            try:
                # 提取高价部分（$符号后的第一个数字）
                high_price = k.split(" - ")[0].replace("$", "")
                return float(high_price)
            except:
                return 0.0
        
        agg_sorted = sorted(agg.items(), key=lambda kv: sort_key(kv[0]), reverse=True)
        cp_sorted = sorted(cp.items(), key=lambda kv: sort_key(kv[0]), reverse=True) if by_type else []
        
        return agg_sorted, cp_sorted
    
    def get_multi_exchange_stats(self):
        """获取多交易所统计数据"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 获取各交易所统计（最近24小时）
            cutoff_time = self.now_ms() - 24 * 60 * 60 * 1000
            cursor.execute('''
                SELECT exchange, COUNT(*), SUM(amount), AVG(price)
                FROM multi_exchange_trades
                WHERE timestamp > ?
                GROUP BY exchange
            ''', (cutoff_time,))
            
            exchange_stats = {}
            total_trades = 0
            total_volume = 0
            
            for row in cursor.fetchall():
                exchange, trades, volume, avg_price = row
                exchange_stats[exchange.lower() + '_stats'] = {
                    'trades': trades,
                    'volume': volume if volume else 0,
                    'avg_price': avg_price if avg_price else 0
                }
                total_trades += trades
                total_volume += volume if volume else 0
            
            # 计算总平均价格 - 确保使用合理的BTC价格范围
            cursor.execute('''
                SELECT AVG(price) FROM multi_exchange_trades
                WHERE timestamp > ? AND price > 50000 AND price < 200000
            ''', (cutoff_time,))
            
            avg_price_result = cursor.fetchone()
            avg_price = avg_price_result[0] if avg_price_result and avg_price_result[0] and avg_price_result[0] > 50000 else 0
            
            conn.close()
            
            return {
                'total_trades': total_trades,
                'total_volume': total_volume,
                'avg_price': avg_price,
                **exchange_stats
            }
            
        except Exception as e:
            logger.error(f"获取多交易所统计失败: {e}")
            return {
                'total_trades': 0,
                'total_volume': 0,
                'avg_price': 0,
                'okx_stats': {},
                'binance_stats': {}
            }
    
    def save_bucket_analysis(self, agg_data, cp_data, bucket_width, bucket_type, time_window_minutes):
        """保存分桶分析结果到数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 清除旧的分析数据
        cursor.execute('DELETE FROM bucket_analysis WHERE bucket_type = ? AND bucket_width = ?', 
                      (bucket_type, bucket_width))
        
        # 保存聚合数据
        for bucket_range, data in agg_data:
            call_data = cp_data.get(bucket_range, {}).get("CALL", {"trades": 0, "amount": 0.0}) if cp_data else {"trades": 0, "amount": 0.0}
            put_data = cp_data.get(bucket_range, {}).get("PUT", {"trades": 0, "amount": 0.0}) if cp_data else {"trades": 0, "amount": 0.0}
            
            cursor.execute('''
                INSERT INTO bucket_analysis 
                (bucket_range, bucket_type, bucket_width, trades_count, total_amount, 
                 call_trades, call_amount, put_trades, put_amount, time_window_minutes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                bucket_range,
                bucket_type,
                bucket_width,
                data["trades"],
                data["amount"],
                call_data["trades"],
                call_data["amount"],
                put_data["trades"],
                put_data["amount"],
                time_window_minutes
            ))
        
        conn.commit()
        conn.close()
        logger.info(f"已保存分桶分析结果: {len(agg_data)} 个分桶")
    
    def get_latest_analysis(self, limit=20):
        """获取最新的分析结果"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT bucket_range, trades_count, total_amount, call_trades, call_amount, 
                   put_trades, put_amount, analysis_time
            FROM bucket_analysis 
            ORDER BY analysis_time DESC, 
                     CAST(REPLACE(SUBSTR(bucket_range, 2, INSTR(bucket_range, ' - ')-2), '$', '') AS REAL) DESC
            LIMIT ?
        ''', (limit,))
        
        results = cursor.fetchall()
        conn.close()
        
        return [{
            "bucket_range": row[0],
            "trades_count": row[1],
            "total_amount": row[2],
            "call_trades": row[3],
            "call_amount": row[4],
            "put_trades": row[5],
            "put_amount": row[6],
            "analysis_time": row[7]
        } for row in results]
    
    def get_exchange_summary(self, minutes=15):
        """获取各交易所数据摘要"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff_time = self.now_ms() - minutes * 60 * 1000
        
        cursor.execute('''
            SELECT exchange, COUNT(*) as trades_count, SUM(amount) as total_amount,
                   AVG(price) as avg_price, MIN(price) as min_price, MAX(price) as max_price
            FROM multi_exchange_trades 
            WHERE timestamp > ?
            GROUP BY exchange
            ORDER BY trades_count DESC
        ''', (cutoff_time,))
        
        results = cursor.fetchall()
        conn.close()
        
        return [{
            "exchange": row[0],
            "trades_count": row[1],
            "total_amount": row[2],
            "avg_price": row[3],
            "min_price": row[4],
            "max_price": row[5]
        } for row in results]

def main():
    """命令行接口"""
    parser = argparse.ArgumentParser(description="Multi-exchange BTC options aggregator")
    parser.add_argument("--minutes", type=int, default=15, help="Time window in minutes")
    parser.add_argument("--bucket", type=float, default=5.0, help="Bucket width")
    parser.add_argument("--by", choices=["price", "strike"], default="price", help="Bucket by price or strike")
    parser.add_argument("--by-type", action="store_true", help="Separate CALL/PUT analysis")
    parser.add_argument("--max-okx", type=int, default=400, help="Max OKX instruments")
    parser.add_argument("--max-binance", type=int, default=400, help="Max Binance symbols")
    args = parser.parse_args()
    
    # 设置日志
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    collector = MultiExchangeCollector()
    
    # 收集数据
    all_trades = collector.collect_all_exchanges(args.minutes, args.max_okx, args.max_binance)
    
    if not all_trades:
        logger.warning("未收集到任何交易数据")
        return
    
    # 进行聚合分析
    agg_all, agg_cp = collector.aggregate_analysis(all_trades, args.bucket, by=args.by, by_type=args.by_type)
    
    # 保存分析结果
    cp_dict = dict(agg_cp) if agg_cp else {}
    collector.save_bucket_analysis(agg_all, cp_dict, args.bucket, args.by, args.minutes)
    
    # 显示结果
    print(f"\n总交易数: {len(all_trades)}")
    
    print("\n=== 分桶聚合分析 ===")
    print(f"{'分桶区间':>14} | {'交易数':>8} | {'总金额':>12}")
    print("-" * 40)
    for bucket, data in agg_all:
        print(f"{bucket:>14} | {data['trades']:>8} | {data['amount']:>12.4f}")
    
    if args.by_type and agg_cp:
        print("\n--- CALL/PUT 细分 ---")
        print(f"{'分桶区间':>14} | {'C_交易':>6} | {'C_金额':>8} | {'P_交易':>6} | {'P_金额':>8}")
        print("-" * 50)
        for bucket, data in agg_cp:
            c = data['CALL']
            p = data['PUT']
            print(f"{bucket:>14} | {c['trades']:>6} | {c['amount']:>8.4f} | {p['trades']:>6} | {p['amount']:>8.4f}")

if __name__ == "__main__":
    main()