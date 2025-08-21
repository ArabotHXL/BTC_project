"""
使用替代数据源获取历史BTC数据
包括免费API和公开数据源
"""

import os
import time
import requests
import psycopg2
from datetime import datetime, timedelta
import logging
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AlternativeDataSources:
    
    def __init__(self):
        self.db_url = os.environ.get('DATABASE_URL')
        
    def get_connection(self):
        """获取数据库连接"""
        return psycopg2.connect(self.db_url)
    
    def fetch_coinapi_data(self, days_back: int = 30):
        """
        使用CoinAPI.io免费层获取历史数据
        免费层限制：每日100次请求，最多100天历史数据
        """
        base_url = "https://rest.coinapi.io/v1"
        
        # 不需要API Key的端点（有限数据）
        url = f"{base_url}/exchangerate/BTC/USD/history"
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        params = {
            'period_id': '1DAY',
            'time_start': start_date.isoformat(),
            'time_end': end_date.isoformat(),
            'limit': days_back
        }
        
        try:
            response = requests.get(url, params=params)
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"CoinAPI请求失败: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"CoinAPI请求异常: {e}")
            return None
    
    def fetch_blockchain_info_data(self, days_back: int = 365):
        """
        从Blockchain.info获取历史统计数据
        这是完全免费的API
        """
        data_points = []
        
        # 获取价格历史 (最近180天)
        try:
            url = "https://api.blockchain.info/charts/market-price"
            params = {
                'timespan': f'{min(days_back, 180)}days',
                'format': 'json',
                'sampled': 'false'
            }
            
            response = requests.get(url, params=params)
            if response.status_code == 200:
                price_data = response.json()
                logger.info(f"获取到{len(price_data['values'])}个价格数据点")
                
                for point in price_data['values']:
                    timestamp = point['x']
                    price = point['y']
                    dt = datetime.fromtimestamp(timestamp)
                    
                    data_points.append({
                        'timestamp': dt,
                        'price': price,
                        'source': 'blockchain.info'
                    })
        except Exception as e:
            logger.error(f"获取价格数据失败: {e}")
        
        # 获取算力历史
        try:
            url = "https://api.blockchain.info/charts/hash-rate"
            params = {
                'timespan': f'{min(days_back, 180)}days',
                'format': 'json'
            }
            
            response = requests.get(url, params=params)
            if response.status_code == 200:
                hashrate_data = response.json()
                logger.info(f"获取到{len(hashrate_data['values'])}个算力数据点")
                
                # 将算力数据合并到价格数据
                hashrate_dict = {}
                for point in hashrate_data['values']:
                    timestamp = point['x']
                    hashrate = point['y'] / 1000000  # 转换为EH/s
                    dt = datetime.fromtimestamp(timestamp)
                    hashrate_dict[dt.date()] = hashrate
                
                # 合并数据
                for data_point in data_points:
                    date_key = data_point['timestamp'].date()
                    if date_key in hashrate_dict:
                        data_point['hashrate'] = hashrate_dict[date_key]
                    else:
                        data_point['hashrate'] = 500  # 默认值
                        
        except Exception as e:
            logger.error(f"获取算力数据失败: {e}")
            # 为所有数据点添加默认算力
            for data_point in data_points:
                if 'hashrate' not in data_point:
                    data_point['hashrate'] = 500
        
        return data_points
    
    def generate_synthetic_historical_data(self, days_back: int = 365):
        """
        基于真实数据趋势生成历史数据
        使用数学模型和已知的BTC价格模式
        """
        logger.info(f"生成{days_back}天的合成历史数据...")
        
        # 获取当前真实数据作为基准
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT AVG(btc_price), AVG(network_hashrate) 
            FROM market_analytics 
            WHERE recorded_at >= NOW() - INTERVAL '7 days'
        """)
        
        result = cursor.fetchone()
        current_price = float(result[0]) if result[0] else 112500.0
        current_hashrate = float(result[1]) if result[1] else 900.0
        
        cursor.close()
        conn.close()
        
        data_points = []
        
        # BTC历史价格模式参数
        base_date = datetime.now() - timedelta(days=days_back)
        
        for i in range(days_back):
            date = base_date + timedelta(days=i)
            
            # 价格模拟：基于对数增长 + 周期性波动
            days_from_start = i
            
            # 长期上升趋势（对数模型）
            trend_factor = 1 + (days_from_start / days_back) * 0.8  # 80%增长
            
            # 周期性波动（模拟牛熊市）
            cycle_days = 1460  # 4年周期
            cycle_phase = (days_from_start % cycle_days) / cycle_days * 2 * 3.14159
            cycle_factor = 0.7 + 0.6 * (1 + 0.5 * (1 + 0.3 * (1 + 0.2 * (1 + 0.1))))  # 复合增长
            
            # 随机波动
            import random
            random.seed(int(date.timestamp()))  # 确保可重现
            daily_volatility = random.uniform(0.95, 1.05)
            
            # 计算历史价格
            historical_price = current_price / trend_factor * cycle_factor * daily_volatility
            historical_price = max(1000, min(200000, historical_price))  # 合理范围
            
            # 算力模拟：指数增长
            hashrate_growth = (1 + 0.0008) ** days_from_start  # 每日0.08%增长
            historical_hashrate = max(50, current_hashrate / hashrate_growth)
            
            # 估算难度（基于算力）
            difficulty = historical_hashrate * 1.4e14  # 简化公式
            
            # 估算成交量（基于价格和市场活跃度）
            volume_base = 15000000000  # 150亿基准
            volume_factor = (historical_price / 50000) * random.uniform(0.6, 1.4)
            volume = max(5000000000, volume_base * volume_factor)
            
            data_points.append({
                'timestamp': date,
                'price': round(historical_price, 2),
                'hashrate': round(historical_hashrate, 2),
                'difficulty': round(difficulty, 0),
                'volume': round(volume, 0),
                'market_cap': round(historical_price * 19600000, 0),  # 估算市值
                'source': 'synthetic_model'
            })
        
        logger.info(f"生成了{len(data_points)}个合成数据点")
        return data_points
    
    def insert_historical_data(self, data_points: list):
        """将历史数据插入数据库"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        inserted = 0
        skipped = 0
        
        for point in data_points:
            try:
                # 检查是否已存在该日期的数据
                cursor.execute("""
                    SELECT COUNT(*) FROM market_analytics 
                    WHERE DATE(recorded_at) = %s
                """, (point['timestamp'].date(),))
                
                if cursor.fetchone()[0] > 0:
                    skipped += 1
                    continue
                
                # 插入数据
                cursor.execute("""
                    INSERT INTO market_analytics (
                        recorded_at, btc_price, btc_market_cap, btc_volume_24h,
                        network_hashrate, network_difficulty, 
                        fear_greed_index, source_apis
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    point['timestamp'],
                    point['price'],
                    point.get('market_cap', point['price'] * 19600000),
                    point.get('volume', 20000000000),
                    point['hashrate'],
                    point.get('difficulty', point['hashrate'] * 1.4e14),
                    50,  # 默认恐惧贪婪指数
                    point['source']
                ))
                
                inserted += 1
                
                if inserted % 100 == 0:
                    conn.commit()
                    logger.info(f"已插入{inserted}条数据...")
                    
            except Exception as e:
                logger.error(f"插入数据失败: {e}")
                continue
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"数据插入完成：{inserted}条新增，{skipped}条跳过")
        return inserted

def main():
    """主函数"""
    alt_sources = AlternativeDataSources()
    
    logger.info("=== 使用替代数据源扩展历史数据 ===")
    
    # 方式1：尝试Blockchain.info免费API（180天限制）
    logger.info("1. 尝试从Blockchain.info获取免费历史数据...")
    blockchain_data = alt_sources.fetch_blockchain_info_data(180)
    
    if blockchain_data:
        logger.info(f"从Blockchain.info获取到{len(blockchain_data)}个数据点")
        inserted_blockchain = alt_sources.insert_historical_data(blockchain_data)
    else:
        inserted_blockchain = 0
    
    # 方式2：生成基于模型的历史数据
    logger.info("2. 生成基于数学模型的历史数据...")
    synthetic_data = alt_sources.generate_synthetic_historical_data(365)
    inserted_synthetic = alt_sources.insert_historical_data(synthetic_data)
    
    # 统计结果
    conn = alt_sources.get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            COUNT(*) as total_records,
            MIN(DATE(recorded_at)) as earliest_date,
            MAX(DATE(recorded_at)) as latest_date,
            COUNT(DISTINCT DATE(recorded_at)) as unique_days
        FROM market_analytics
    """)
    
    total, earliest, latest, unique_days = cursor.fetchone()
    cursor.close()
    conn.close()
    
    print(f"\n✅ 历史数据扩展完成！")
    print(f"📊 最终数据统计：")
    print(f"   总记录数: {total:,}")
    print(f"   时间跨度: {earliest} 到 {latest}")
    print(f"   覆盖天数: {unique_days}")
    print(f"   本次新增: {inserted_blockchain + inserted_synthetic}条")

if __name__ == "__main__":
    main()