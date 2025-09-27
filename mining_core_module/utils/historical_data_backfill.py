"""
历史数据回填脚本
从CoinGecko API获取更多BTC历史数据
"""

import os
import time
import requests
import psycopg2
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HistoricalDataBackfill:
    
    def __init__(self):
        self.db_url = os.environ.get('DATABASE_URL')
        self.coingecko_base = "https://api.coingecko.com/api/v3"
        
    def get_connection(self):
        """获取数据库连接"""
        return psycopg2.connect(self.db_url)
    
    def fetch_historical_prices(self, days: int = 365):
        """从CoinGecko获取历史价格数据"""
        url = f"{self.coingecko_base}/coins/bitcoin/market_chart"
        params = {
            'vs_currency': 'usd',
            'days': days,
            'interval': 'daily'  # 每日数据点
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            logger.info(f"成功获取{days}天历史数据")
            return data
        except Exception as e:
            logger.error(f"获取历史数据失败: {e}")
            return None
    
    def fetch_blockchain_stats(self, timestamp: int):
        """获取特定时间的区块链统计数据"""
        # Blockchain.info不提供历史数据API，使用估算值
        # 基于当前913.66EH/s和难度调整周期估算
        
        current_hashrate = 913.66
        current_difficulty = 129435235580344.0
        
        # 简化估算：根据时间距离调整算力
        days_from_now = (time.time() - timestamp) / 86400
        hashrate_growth_rate = 0.0003  # 每日0.03%增长率
        
        estimated_hashrate = current_hashrate * (1 - hashrate_growth_rate) ** days_from_now
        estimated_difficulty = current_difficulty * (estimated_hashrate / current_hashrate)
        
        return {
            'hashrate': max(100, estimated_hashrate),  # 最小100EH/s
            'difficulty': max(1e12, estimated_difficulty)  # 最小难度
        }
    
    def backfill_data(self, days: int = 365):
        """回填历史数据"""
        logger.info(f"开始回填{days}天历史数据...")
        
        # 获取历史价格数据
        data = self.fetch_historical_prices(days)
        if not data:
            return False
        
        prices = data['prices']
        volumes = data['total_volumes']
        market_caps = data['market_caps']
        
        logger.info(f"获取到{len(prices)}个数据点")
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 检查已存在的数据
        cursor.execute("""
            SELECT MIN(recorded_at), MAX(recorded_at), COUNT(*) 
            FROM market_analytics
        """)
        existing_min, existing_max, existing_count = cursor.fetchone()
        
        logger.info(f"数据库现有数据：{existing_count}条，时间范围：{existing_min} 到 {existing_max}")
        
        inserted_count = 0
        skipped_count = 0
        
        for i, (price_data, volume_data, cap_data) in enumerate(zip(prices, volumes, market_caps)):
            timestamp_ms, price = price_data
            _, volume = volume_data  
            _, market_cap = cap_data
            
            # 转换时间戳
            dt = datetime.fromtimestamp(timestamp_ms / 1000)
            
            # 检查是否已存在该日期的数据
            cursor.execute("""
                SELECT COUNT(*) FROM market_analytics 
                WHERE DATE(recorded_at) = %s
            """, (dt.date(),))
            
            if cursor.fetchone()[0] > 0:
                skipped_count += 1
                continue
            
            # 获取区块链统计数据
            blockchain_stats = self.fetch_blockchain_stats(timestamp_ms / 1000)
            
            # 插入数据
            cursor.execute("""
                INSERT INTO market_analytics (
                    recorded_at, btc_price, btc_market_cap, btc_volume_24h,
                    network_hashrate, network_difficulty, 
                    fear_greed_index, source_apis
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                dt,
                float(price),
                float(market_cap), 
                float(volume),
                blockchain_stats['hashrate'],
                blockchain_stats['difficulty'],
                50,  # 默认恐惧贪婪指数
                'coingecko_historical'
            ))
            
            inserted_count += 1
            
            # 每100条提交一次
            if inserted_count % 100 == 0:
                conn.commit()
                logger.info(f"已插入{inserted_count}条历史数据...")
                time.sleep(0.1)  # 避免API限制
        
        # 最终提交
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"历史数据回填完成！插入{inserted_count}条新数据，跳过{skipped_count}条已存在数据")
        return True
    
    def extend_historical_data(self, additional_days: int = 365):
        """扩展历史数据到更早的时间"""
        logger.info(f"扩展历史数据，增加{additional_days}天...")
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 获取当前最早的数据日期
        cursor.execute("""
            SELECT MIN(DATE(recorded_at)) FROM market_analytics
        """)
        earliest_date = cursor.fetchone()[0]
        
        if earliest_date:
            logger.info(f"当前最早数据日期：{earliest_date}")
            
            # 计算需要获取的总天数
            days_from_earliest = (datetime.now().date() - earliest_date).days + additional_days
            
            logger.info(f"将获取{days_from_earliest}天的完整历史数据")
            
            # 清除现有数据以避免重复（可选）
            # cursor.execute("DELETE FROM market_analytics WHERE source_apis = 'coingecko_historical'")
            
            # 获取扩展的历史数据
            return self.backfill_data(days_from_earliest)
        else:
            logger.info("数据库为空，获取365天历史数据")
            return self.backfill_data(365)

def main():
    backfill = HistoricalDataBackfill()
    
    print("=== BTC历史数据扩展工具 ===")
    print("1. 回填最近365天数据")
    print("2. 扩展额外365天历史数据") 
    print("3. 扩展额外730天历史数据（2年）")
    
    choice = input("请选择操作 (1-3): ").strip()
    
    if choice == "1":
        success = backfill.backfill_data(365)
    elif choice == "2":
        success = backfill.extend_historical_data(365)
    elif choice == "3":
        success = backfill.extend_historical_data(730)
    else:
        print("无效选择")
        return
    
    if success:
        print("✅ 历史数据扩展成功！")
        
        # 显示最新统计
        conn = backfill.get_connection()
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
        
        print(f"📊 数据库统计：")
        print(f"   总记录数: {total:,}")
        print(f"   时间跨度: {earliest} 到 {latest}")
        print(f"   覆盖天数: {unique_days}")
        print(f"   平均每天: {total/unique_days:.1f}条记录")
        
        cursor.close()
        conn.close()
    else:
        print("❌ 历史数据扩展失败")

if __name__ == "__main__":
    main()