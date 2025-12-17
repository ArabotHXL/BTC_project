#!/usr/bin/env python3
"""
Deribit Trading Data Analysis POC
从Deribit Public API采集期权交易数据，分析价格区间的交易量分布

功能：
1. 采集最近的期权交易数据
2. 按价格区间统计交易量
3. 生成分析报告
4. 支持定时数据采集

作者：BTC Mining Calculator System
日期：2025-08-14
"""

import requests
import time
import json
import pandas as pd
from datetime import datetime, timedelta
import sqlite3
import schedule
import logging
from typing import List, Dict, Optional, Tuple
import argparse
from dataclasses import dataclass, asdict

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('deribit_analysis.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class TradeData:
    """交易数据结构"""
    trade_id: str
    timestamp: int
    price: float
    amount: float
    direction: str
    instrument_name: str
    index_price: float
    mark_price: float

@dataclass
class PriceRangeAnalysis:
    """价格区间分析结果"""
    price_range: str
    trade_count: int
    total_volume: float
    avg_price: float
    percentage: float

class DeribitDataCollector:
    """Deribit数据采集器"""
    
    def __init__(self, base_url="https://www.deribit.com/api/v2"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'DeribitAnalysisPOC/1.0'
        })
        
    def make_request(self, method: str, params: Optional[Dict] = None) -> Dict:
        """发送API请求"""
        if params is None:
            params = {}
            
        payload = {
            "jsonrpc": "2.0",
            "id": int(time.time()),
            "method": method,
            "params": params
        }
        
        try:
            response = self.session.post(self.base_url, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if 'error' in data:
                logger.error(f"API错误: {data['error']}")
                return {}
                
            return data.get('result', {})
            
        except requests.exceptions.RequestException as e:
            logger.error(f"请求失败: {e}")
            return {}
    
    def get_instruments(self, currency: str = "BTC", kind: str = "option") -> List[Dict]:
        """获取可用的期权合约"""
        params = {
            "currency": currency,
            "kind": kind,
            "expired": False
        }
        
        result = self.make_request("public/get_instruments", params)
        return result if isinstance(result, list) else []
    
    def get_last_trades(self, instrument_name: str, count: int = 100) -> List[TradeData]:
        """获取最近的交易数据"""
        params = {
            "instrument_name": instrument_name,
            "count": count
        }
        
        result = self.make_request("public/get_last_trades_by_instrument", params)
        trades = result.get('trades', []) if isinstance(result, dict) else []
        
        trade_data = []
        for trade in trades:
            try:
                trade_obj = TradeData(
                    trade_id=trade['trade_id'],
                    timestamp=trade['timestamp'],
                    price=float(trade['price']),
                    amount=float(trade['amount']),
                    direction=trade['direction'],
                    instrument_name=trade['instrument_name'],
                    index_price=float(trade.get('index_price', 0)),
                    mark_price=float(trade.get('mark_price', 0))
                )
                trade_data.append(trade_obj)
            except (KeyError, ValueError) as e:
                logger.warning(f"解析交易数据失败: {e}")
                continue
                
        return trade_data
    
    def get_ticker(self, instrument_name: str) -> Dict:
        """获取合约行情数据"""
        params = {"instrument_name": instrument_name}
        return self.make_request("public/ticker", params)

class DataStorage:
    """数据存储管理"""
    
    def __init__(self, db_path: str = "deribit_trades.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                trade_id TEXT PRIMARY KEY,
                timestamp INTEGER,
                price REAL,
                amount REAL,
                direction TEXT,
                instrument_name TEXT,
                index_price REAL,
                mark_price REAL,
                collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS price_range_analysis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                instrument_name TEXT,
                analysis_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                price_range TEXT,
                trade_count INTEGER,
                total_volume REAL,
                avg_price REAL,
                percentage REAL
            )
        ''')
        
        conn.commit()
        conn.close()
        
    def save_trades(self, trades: List[TradeData]):
        """保存交易数据"""
        if not trades:
            return
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for trade in trades:
            cursor.execute('''
                INSERT OR REPLACE INTO trades 
                (trade_id, timestamp, price, amount, direction, instrument_name, index_price, mark_price)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                trade.trade_id, trade.timestamp, trade.price, trade.amount,
                trade.direction, trade.instrument_name, trade.index_price, trade.mark_price
            ))
        
        conn.commit()
        conn.close()
        logger.info(f"保存了 {len(trades)} 条交易数据")
    
    def get_trades_by_instrument(self, instrument_name: str, hours: int = 24) -> List[TradeData]:
        """获取指定时间范围内的交易数据"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        since_timestamp = int((datetime.now() - timedelta(hours=hours)).timestamp() * 1000)
        
        cursor.execute('''
            SELECT trade_id, timestamp, price, amount, direction, instrument_name, index_price, mark_price
            FROM trades 
            WHERE instrument_name = ? AND timestamp > ?
            ORDER BY timestamp DESC
        ''', (instrument_name, since_timestamp))
        
        trades = []
        for row in cursor.fetchall():
            trade = TradeData(
                trade_id=row[0], timestamp=row[1], price=row[2], amount=row[3],
                direction=row[4], instrument_name=row[5], index_price=row[6], mark_price=row[7]
            )
            trades.append(trade)
        
        conn.close()
        return trades
    
    def save_price_analysis(self, instrument_name: str, analysis: List[PriceRangeAnalysis]):
        """保存价格区间分析结果"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for item in analysis:
            cursor.execute('''
                INSERT INTO price_range_analysis 
                (instrument_name, price_range, trade_count, total_volume, avg_price, percentage)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                instrument_name, item.price_range, item.trade_count,
                item.total_volume, item.avg_price, item.percentage
            ))
        
        conn.commit()
        conn.close()

class PriceRangeAnalyzer:
    """价格区间分析器"""
    
    @staticmethod
    def analyze_by_price_ranges(trades: List[TradeData], num_ranges: int = 10) -> List[PriceRangeAnalysis]:
        """按价格区间分析交易数据"""
        if not trades:
            return []
        
        df = pd.DataFrame([asdict(trade) for trade in trades])
        
        # 计算价格区间
        min_price = df['price'].min()
        max_price = df['price'].max()
        range_size = (max_price - min_price) / num_ranges
        
        analysis_results = []
        total_volume = df['amount'].sum()
        
        for i in range(num_ranges):
            range_start = min_price + i * range_size
            range_end = min_price + (i + 1) * range_size
            
            # 筛选该价格区间的交易
            mask = (df['price'] >= range_start) & (df['price'] < range_end)
            range_trades = df[mask]
            
            if len(range_trades) > 0:
                analysis = PriceRangeAnalysis(
                    price_range=f"${int(range_end)} - ${int(range_start)}",
                    trade_count=len(range_trades),
                    total_volume=float(range_trades['amount'].sum()),
                    avg_price=float(range_trades['price'].mean()),
                    percentage=float((range_trades['amount'].sum() / total_volume * 100) if total_volume > 0 else 0)
                )
                analysis_results.append(analysis)
        
        # 按价格区间排序（从高到低）
        def price_sort_key(x):
            try:
                # 提取高价部分（$符号后的第一个数字）
                high_price = x.price_range.split(" - ")[0].replace("$", "")
                return float(high_price)
            except:
                return 0.0
        
        return sorted(analysis_results, key=price_sort_key, reverse=True)

class DeribitAnalysisPOC:
    """Deribit分析POC主类"""
    
    def __init__(self):
        self.collector = DeribitDataCollector()
        self.storage = DataStorage()
        self.analyzer = PriceRangeAnalyzer()
        
    def collect_and_analyze(self, instrument_name: Optional[str] = None):
        """采集并分析数据"""
        logger.info("开始数据采集和分析...")
        
        # 如果没有指定合约，获取活跃的BTC期权合约
        if not instrument_name:
            instruments = self.collector.get_instruments("BTC", "option")
            if not instruments:
                logger.error("无法获取期权合约列表")
                return
            
            # 选择第一个活跃合约
            instrument_name = instruments[0]['instrument_name']
            logger.info(f"选择分析合约: {instrument_name}")
        
        # 确保instrument_name不为None
        if not instrument_name:
            logger.error("无法确定分析合约")
            return
        
        # 采集交易数据
        trades = self.collector.get_last_trades(instrument_name, count=500)
        if not trades:
            logger.warning(f"未获取到 {instrument_name} 的交易数据")
            return
        
        # 保存数据
        self.storage.save_trades(trades)
        
        # 分析价格区间
        analysis = self.analyzer.analyze_by_price_ranges(trades, num_ranges=10)
        self.storage.save_price_analysis(instrument_name, analysis)
        
        # 生成报告
        self.generate_report(instrument_name, trades, analysis)
        
    def generate_report(self, instrument_name: str, trades: List[TradeData], analysis: List[PriceRangeAnalysis]):
        """生成分析报告"""
        total_trades = len(trades)
        total_volume = sum(trade.amount for trade in trades)
        avg_price = sum(trade.price for trade in trades) / total_trades if total_trades > 0 else 0
        
        print(f"\n{'='*60}")
        print(f"Deribit期权交易分析报告")
        print(f"{'='*60}")
        print(f"合约名称: {instrument_name}")
        print(f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"总交易数: {total_trades}")
        print(f"总交易量: {total_volume:.4f}")
        print(f"平均价格: ${avg_price:.2f}")
        print(f"\n价格区间分析:")
        print(f"{'价格区间':<20} {'交易数':<8} {'交易量':<12} {'占比':<8} {'均价':<10}")
        print("-" * 60)
        
        for item in analysis:
            print(f"{item.price_range:<20} {item.trade_count:<8} {item.total_volume:<12.4f} {item.percentage:<8.2f}% ${item.avg_price:<10.2f}")
        
        print(f"{'='*60}\n")
        
        # 保存到文件
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"deribit_analysis_{timestamp}.txt"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"Deribit期权交易分析报告\n")
            f.write(f"合约名称: {instrument_name}\n")
            f.write(f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"总交易数: {total_trades}\n")
            f.write(f"总交易量: {total_volume:.4f}\n")
            f.write(f"平均价格: ${avg_price:.2f}\n\n")
            f.write("价格区间分析:\n")
            for item in analysis:
                f.write(f"{item.price_range}: {item.trade_count}笔交易, {item.total_volume:.4f}量, {item.percentage:.2f}%, 均价${item.avg_price:.2f}\n")
        
        logger.info(f"报告已保存到: {filename}")
    
    def start_scheduled_collection(self, interval_minutes: int = 15):
        """启动定时数据采集"""
        logger.info(f"启动定时数据采集，间隔: {interval_minutes}分钟")
        
        schedule.every(interval_minutes).minutes.do(self.collect_and_analyze)
        
        while True:
            schedule.run_pending()
            time.sleep(60)  # 每分钟检查一次
    
    def list_active_options(self):
        """列出活跃的期权合约"""
        logger.info("获取活跃的BTC期权合约...")
        
        instruments = self.collector.get_instruments("BTC", "option")
        if not instruments:
            print("无法获取期权合约列表")
            return
        
        print(f"\n活跃的BTC期权合约 (共{len(instruments)}个):")
        print(f"{'合约名称':<30} {'到期日':<12} {'行权价':<10} {'类型':<6}")
        print("-" * 60)
        
        for instrument in instruments[:20]:  # 显示前20个
            exp_date = datetime.fromtimestamp(instrument['expiration_timestamp'] / 1000).strftime('%Y-%m-%d')
            print(f"{instrument['instrument_name']:<30} {exp_date:<12} ${instrument['strike']:<10} {instrument['option_type']:<6}")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Deribit期权交易数据分析POC")
    parser.add_argument('--instrument', type=str, help='指定要分析的期权合约名称')
    parser.add_argument('--schedule', type=int, help='启动定时采集，指定间隔分钟数')
    parser.add_argument('--list', action='store_true', help='列出活跃的期权合约')
    
    args = parser.parse_args()
    
    poc = DeribitAnalysisPOC()
    
    if args.list:
        poc.list_active_options()
    elif args.schedule:
        poc.start_scheduled_collection(args.schedule)
    else:
        poc.collect_and_analyze(args.instrument)

if __name__ == "__main__":
    main()