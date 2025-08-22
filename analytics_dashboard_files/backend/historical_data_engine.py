"""
Historical Data Engine
历史数据收集和管理引擎
"""

import logging
import requests
import psycopg2
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import json
import os
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class HistoricalDataPoint:
    """历史数据点"""
    timestamp: datetime
    btc_price: float
    network_hashrate: float
    network_difficulty: float
    block_reward: float
    source: str = "api"

class HistoricalDataEngine:
    """历史数据引擎"""
    
    def __init__(self):
        self.db_url = os.environ.get('DATABASE_URL')
        self.connection = None
        self.api_endpoints = {
            'coingecko': 'https://api.coingecko.com/api/v3',
            'blockchain_info': 'https://api.blockchain.info',
            'mempool': 'https://mempool.space/api/v1'
        }
        
    def connect_db(self):
        """连接数据库"""
        try:
            if self.db_url:
                self.connection = psycopg2.connect(self.db_url)
                return self.connection
            else:
                logger.warning("DATABASE_URL not configured")
                return None
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            return None
    
    def fetch_historical_prices(self, days: int = 365) -> List[Dict]:
        """获取历史价格数据"""
        try:
            url = f"{self.api_endpoints['coingecko']}/coins/bitcoin/market_chart"
            params = {
                'vs_currency': 'usd',
                'days': days,
                'interval': 'daily'
            }
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            prices = data.get('prices', [])
            
            historical_data = []
            for price_point in prices:
                timestamp = datetime.fromtimestamp(price_point[0] / 1000)
                price = price_point[1]
                
                historical_data.append({
                    'timestamp': timestamp,
                    'btc_price': price,
                    'source': 'coingecko'
                })
            
            logger.info(f"获取到 {len(historical_data)} 个历史价格数据点")
            return historical_data
            
        except Exception as e:
            logger.error(f"获取历史价格数据失败: {e}")
            return []
    
    def fetch_network_difficulty_history(self, days: int = 365) -> List[Dict]:
        """获取网络难度历史数据"""
        try:
            # 使用Blockchain.info API获取难度历史
            url = f"{self.api_endpoints['blockchain_info']}/charts/difficulty"
            params = {
                'timespan': f'{days}days',
                'format': 'json'
            }
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            values = data.get('values', [])
            
            difficulty_data = []
            for point in values:
                timestamp = datetime.fromtimestamp(point['x'])
                difficulty = point['y']
                
                difficulty_data.append({
                    'timestamp': timestamp,
                    'network_difficulty': difficulty,
                    'source': 'blockchain_info'
                })
            
            logger.info(f"获取到 {len(difficulty_data)} 个难度历史数据点")
            return difficulty_data
            
        except Exception as e:
            logger.error(f"获取网络难度历史失败: {e}")
            return []
    
    def fetch_hashrate_history(self, days: int = 365) -> List[Dict]:
        """获取算力历史数据"""
        try:
            # 使用Blockchain.info算力图表API
            url = f"{self.api_endpoints['blockchain_info']}/charts/hash-rate"
            params = {
                'timespan': f'{days}days',
                'format': 'json'
            }
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            values = data.get('values', [])
            
            hashrate_data = []
            for point in values:
                timestamp = datetime.fromtimestamp(point['x'])
                hashrate = point['y'] / 1e18  # 转换为EH/s
                
                hashrate_data.append({
                    'timestamp': timestamp,
                    'network_hashrate': hashrate,
                    'source': 'blockchain_info'
                })
            
            logger.info(f"获取到 {len(hashrate_data)} 个算力历史数据点")
            return hashrate_data
            
        except Exception as e:
            logger.error(f"获取算力历史失败: {e}")
            return []
    
    def consolidate_historical_data(self, days: int = 365) -> List[HistoricalDataPoint]:
        """整合历史数据"""
        try:
            # 获取各类历史数据
            price_data = self.fetch_historical_prices(days)
            difficulty_data = self.fetch_network_difficulty_history(days)
            hashrate_data = self.fetch_hashrate_history(days)
            
            # 创建数据框进行合并
            price_df = pd.DataFrame(price_data)
            difficulty_df = pd.DataFrame(difficulty_data)
            hashrate_df = pd.DataFrame(hashrate_data)
            
            if price_df.empty:
                logger.warning("价格数据为空，无法整合")
                return []
            
            # 按日期合并数据
            price_df['date'] = price_df['timestamp'].dt.date
            if not difficulty_df.empty:
                difficulty_df['date'] = difficulty_df['timestamp'].dt.date
            if not hashrate_df.empty:
                hashrate_df['date'] = hashrate_df['timestamp'].dt.date
            
            # 合并所有数据
            consolidated = price_df.copy()
            
            if not difficulty_df.empty:
                consolidated = consolidated.merge(
                    difficulty_df[['date', 'network_difficulty']], 
                    on='date', 
                    how='left'
                )
            
            if not hashrate_df.empty:
                consolidated = consolidated.merge(
                    hashrate_df[['date', 'network_hashrate']], 
                    on='date', 
                    how='left'
                )
            
            # 填充缺失值
            consolidated['network_difficulty'] = consolidated['network_difficulty'].fillna(method='ffill')
            consolidated['network_hashrate'] = consolidated['network_hashrate'].fillna(method='ffill')
            consolidated['block_reward'] = 3.125  # 当前区块奖励
            
            # 转换为HistoricalDataPoint列表
            historical_points = []
            for _, row in consolidated.iterrows():
                point = HistoricalDataPoint(
                    timestamp=row['timestamp'],
                    btc_price=row['btc_price'],
                    network_hashrate=row.get('network_hashrate', 950.0),
                    network_difficulty=row.get('network_difficulty', 129435235580344.0),
                    block_reward=3.125,
                    source='consolidated'
                )
                historical_points.append(point)
            
            logger.info(f"成功整合 {len(historical_points)} 个历史数据点")
            return historical_points
            
        except Exception as e:
            logger.error(f"整合历史数据失败: {e}")
            return []
    
    def save_historical_data(self, data_points: List[HistoricalDataPoint]) -> bool:
        """保存历史数据到数据库"""
        try:
            conn = self.connect_db()
            if not conn:
                logger.warning("无法连接数据库，跳过保存")
                return False
            
            cursor = conn.cursor()
            
            # 批量插入数据
            insert_query = """
                INSERT INTO market_analytics 
                (recorded_at, btc_price, network_hashrate, network_difficulty, 
                 block_reward, source, price_change_1h, price_change_24h, price_change_7d)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (recorded_at) DO UPDATE SET
                btc_price = EXCLUDED.btc_price,
                network_hashrate = EXCLUDED.network_hashrate,
                network_difficulty = EXCLUDED.network_difficulty
            """
            
            saved_count = 0
            for point in data_points:
                try:
                    cursor.execute(insert_query, (
                        point.timestamp,
                        point.btc_price,
                        point.network_hashrate,
                        point.network_difficulty,
                        point.block_reward,
                        point.source,
                        0.0,  # price_change_1h
                        0.0,  # price_change_24h
                        0.0   # price_change_7d
                    ))
                    saved_count += 1
                except Exception as e:
                    logger.error(f"保存数据点失败: {e}")
                    continue
            
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info(f"成功保存 {saved_count}/{len(data_points)} 个历史数据点")
            return True
            
        except Exception as e:
            logger.error(f"保存历史数据失败: {e}")
            return False
    
    def backfill_historical_data(self, days: int = 365) -> bool:
        """回填历史数据"""
        try:
            logger.info(f"开始回填 {days} 天的历史数据...")
            
            # 获取整合的历史数据
            historical_data = self.consolidate_historical_data(days)
            
            if not historical_data:
                logger.warning("没有获取到历史数据")
                return False
            
            # 保存到数据库
            success = self.save_historical_data(historical_data)
            
            if success:
                logger.info(f"历史数据回填完成: {len(historical_data)} 个数据点")
            else:
                logger.error("历史数据回填失败")
            
            return success
            
        except Exception as e:
            logger.error(f"历史数据回填错误: {e}")
            return False
    
    def get_data_gaps(self) -> List[Tuple[datetime, datetime]]:
        """检测数据缺口"""
        try:
            conn = self.connect_db()
            if not conn:
                return []
            
            cursor = conn.cursor()
            
            # 查找数据缺口
            query = """
                WITH date_series AS (
                    SELECT generate_series(
                        (SELECT MIN(recorded_at::date) FROM market_analytics),
                        CURRENT_DATE,
                        '1 day'::interval
                    )::date AS expected_date
                ),
                existing_dates AS (
                    SELECT DISTINCT recorded_at::date AS actual_date
                    FROM market_analytics
                )
                SELECT expected_date
                FROM date_series
                LEFT JOIN existing_dates ON date_series.expected_date = existing_dates.actual_date
                WHERE existing_dates.actual_date IS NULL
                ORDER BY expected_date;
            """
            
            cursor.execute(query)
            missing_dates = [row[0] for row in cursor.fetchall()]
            
            cursor.close()
            conn.close()
            
            # 转换为日期范围
            gaps = []
            if missing_dates:
                start_date = missing_dates[0]
                end_date = missing_dates[0]
                
                for date in missing_dates[1:]:
                    if (date - end_date).days == 1:
                        end_date = date
                    else:
                        gaps.append((start_date, end_date))
                        start_date = date
                        end_date = date
                
                gaps.append((start_date, end_date))
            
            logger.info(f"发现 {len(gaps)} 个数据缺口")
            return gaps
            
        except Exception as e:
            logger.error(f"检测数据缺口失败: {e}")
            return []

# 全局实例
historical_engine = HistoricalDataEngine()

def backfill_data(days: int = 365) -> bool:
    """便捷的数据回填函数"""
    return historical_engine.backfill_historical_data(days)

# 兼容性导出
__all__ = ['HistoricalDataEngine', 'HistoricalDataPoint', 'historical_engine', 'backfill_data']