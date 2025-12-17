"""
自动运行历史数据扩展 - 获取2年历史数据
"""
from historical_data_backfill import HistoricalDataBackfill
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_extended_backfill():
    """运行扩展历史数据回填"""
    backfill = HistoricalDataBackfill()
    
    logger.info("开始扩展历史数据 - 获取2年数据...")
    
    # 扩展730天（2年）历史数据
    success = backfill.extend_historical_data(730)
    
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
                COUNT(DISTINCT DATE(recorded_at)) as unique_days,
                COUNT(CASE WHEN btc_volume_24h > 0 THEN 1 END) as volume_records
            FROM market_analytics
        """)
        total, earliest, latest, unique_days, volume_records = cursor.fetchone()
        
        print(f"\n📊 扩展后数据库统计：")
        print(f"   总记录数: {total:,}")
        print(f"   时间跨度: {earliest} 到 {latest}")
        print(f"   覆盖天数: {unique_days}")
        print(f"   平均每天: {total/unique_days:.1f}条记录")
        print(f"   成交量记录: {volume_records:,} ({volume_records/total*100:.1f}%)")
        
        cursor.close()
        conn.close()
        
        return True
    else:
        print("❌ 历史数据扩展失败")
        return False

if __name__ == "__main__":
    run_extended_backfill()