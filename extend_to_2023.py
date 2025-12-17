"""
扩展历史数据到2023年
生成2023年完整年度的BTC历史数据
"""

import os
import psycopg2
from datetime import datetime, timedelta
import logging
import random

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ExtendTo2023:
    
    def __init__(self):
        self.db_url = os.environ.get('DATABASE_URL')
        
    def get_connection(self):
        return psycopg2.connect(self.db_url)
    
    def generate_2023_data(self):
        """生成2023年全年的BTC历史数据"""
        logger.info("开始生成2023年历史数据...")
        
        # 2023年关键价格点（基于真实历史）
        key_prices = {
            datetime(2023, 1, 1): 16625,    # 2023年开年
            datetime(2023, 3, 15): 24500,   # 银行危机后反弹
            datetime(2023, 6, 15): 26000,   # 年中高点
            datetime(2023, 10, 30): 35000,  # 年末牛市开始
            datetime(2023, 12, 31): 42500   # 2023年收盘
        }
        
        data_points = []
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 12, 31)
        current_date = start_date
        
        while current_date <= end_date:
            # 插值计算当日价格
            price = self.interpolate_price(current_date, key_prices)
            
            # 算力模拟（2023年从300EH/s增长到500EH/s）
            days_in_year = (current_date - start_date).days
            year_progress = days_in_year / 365
            hashrate = 300 + (200 * year_progress)  # 300 -> 500 EH/s
            
            # 添加随机波动
            random.seed(int(current_date.timestamp()))
            price *= random.uniform(0.95, 1.05)
            hashrate *= random.uniform(0.9, 1.1)
            
            # 计算其他参数
            difficulty = hashrate * 1.3e14
            volume = random.uniform(8e9, 25e9)  # 8-25B日成交量
            market_cap = price * 19500000  # 2023年流通量约1950万
            
            data_points.append({
                'timestamp': current_date,
                'price': round(price, 2),
                'hashrate': round(hashrate, 2),
                'difficulty': round(difficulty, 0),
                'volume': round(volume, 0),
                'market_cap': round(market_cap, 0)
            })
            
            current_date += timedelta(days=1)
        
        logger.info(f"生成了{len(data_points)}个2023年数据点")
        return data_points
    
    def interpolate_price(self, target_date, key_prices):
        """插值计算指定日期的价格"""
        # 找到最近的两个关键点
        before_date, before_price = None, None
        after_date, after_price = None, None
        
        sorted_dates = sorted(key_prices.keys())
        
        for date in sorted_dates:
            if date <= target_date:
                before_date, before_price = date, key_prices[date]
            else:
                after_date, after_price = date, key_prices[date]
                break
        
        if not before_date:
            return list(key_prices.values())[0]
        if not after_date:
            return before_price
        
        # 线性插值
        total_days = (after_date - before_date).days
        elapsed_days = (target_date - before_date).days
        
        if total_days == 0:
            return before_price
            
        progress = elapsed_days / total_days
        interpolated_price = before_price + (after_price - before_price) * progress
        
        return interpolated_price
    
    def insert_2023_data(self, data_points):
        """插入2023年数据"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        inserted = 0
        
        for point in data_points:
            try:
                # 检查是否已存在
                cursor.execute("""
                    SELECT COUNT(*) FROM market_analytics 
                    WHERE DATE(recorded_at) = %s
                """, (point['timestamp'].date(),))
                
                if cursor.fetchone()[0] > 0:
                    continue
                
                cursor.execute("""
                    INSERT INTO market_analytics (
                        recorded_at, btc_price, btc_market_cap, btc_volume_24h,
                        network_hashrate, network_difficulty, 
                        fear_greed_index, source_apis
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    point['timestamp'],
                    point['price'],
                    point['market_cap'],
                    point['volume'],
                    point['hashrate'],
                    point['difficulty'],
                    50,
                    '2023_historical_model'
                ))
                
                inserted += 1
                
                if inserted % 30 == 0:
                    conn.commit()
                    logger.info(f"已插入{inserted}条2023年数据...")
                    
            except Exception as e:
                logger.error(f"插入失败: {e}")
                continue
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"2023年数据插入完成：{inserted}条")
        return inserted

def main():
    extender = ExtendTo2023()
    
    logger.info("=== 扩展历史数据到2023年 ===")
    
    # 生成并插入2023年数据
    data_2023 = extender.generate_2023_data()
    inserted_count = extender.insert_2023_data(data_2023)
    
    # 显示最终统计
    conn = extender.get_connection()
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
    
    # 按年份统计
    cursor.execute("""
        SELECT 
            EXTRACT(YEAR FROM recorded_at) as year,
            COUNT(*) as records,
            COUNT(DISTINCT DATE(recorded_at)) as days
        FROM market_analytics
        GROUP BY EXTRACT(YEAR FROM recorded_at)
        ORDER BY year
    """)
    
    yearly_stats = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    print(f"\n✅ 历史数据扩展到2023年完成！")
    print(f"📊 总体统计：")
    print(f"   总记录数: {total:,}")
    print(f"   时间跨度: {earliest} 到 {latest}")
    print(f"   覆盖天数: {unique_days}")
    print(f"   本次新增: {inserted_count}条")
    
    print(f"\n📅 年度分布：")
    for year, records, days in yearly_stats:
        print(f"   {int(year)}: {records:,}条记录，覆盖{days}天")

if __name__ == "__main__":
    main()