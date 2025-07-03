#!/usr/bin/env python3
"""
market_analytics表重新组织脚本
Reorganize market_analytics table script

优化表结构和数据排列，提升查询性能
Optimize table structure and data arrangement for better query performance
"""

import os
import psycopg2

def reorganize_market_analytics():
    """重新组织market_analytics表"""
    
    conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
    cursor = conn.cursor()
    
    print("开始重新组织market_analytics表...")
    
    # 1. 创建备份表
    print("1. 创建数据备份...")
    cursor.execute("""
        DROP TABLE IF EXISTS market_analytics_backup;
        CREATE TABLE market_analytics_backup AS 
        SELECT * FROM market_analytics;
    """)
    
    # 2. 重建主表以优化性能
    print("2. 重建主表结构...")
    cursor.execute("""
        DROP TABLE IF EXISTS market_analytics_new;
        CREATE TABLE market_analytics_new (
            id SERIAL PRIMARY KEY,
            recorded_at TIMESTAMP NOT NULL,
            btc_price NUMERIC(12,2) NOT NULL,
            btc_market_cap BIGINT,
            btc_volume_24h BIGINT,
            network_hashrate NUMERIC(10,2) NOT NULL,
            network_difficulty NUMERIC(20,2) NOT NULL,
            block_reward NUMERIC(10,8),
            fear_greed_index INTEGER,
            price_change_1h NUMERIC(8,4),
            price_change_24h NUMERIC(8,4),
            price_change_7d NUMERIC(8,4),
            source VARCHAR(50),
            created_at TIMESTAMP DEFAULT NOW()
        );
    """)
    
    # 3. 创建优化索引
    print("3. 创建性能索引...")
    cursor.execute("""
        CREATE INDEX idx_market_analytics_recorded_at ON market_analytics_new(recorded_at DESC);
        CREATE INDEX idx_market_analytics_source ON market_analytics_new(source);
        CREATE INDEX idx_market_analytics_date ON market_analytics_new(DATE(recorded_at));
        CREATE INDEX idx_market_analytics_btc_price ON market_analytics_new(btc_price);
        CREATE INDEX idx_market_analytics_hashrate ON market_analytics_new(network_hashrate);
    """)
    
    # 4. 按时间顺序插入重新排列的数据
    print("4. 重新插入排序后的数据...")
    cursor.execute("""
        INSERT INTO market_analytics_new (
            recorded_at, btc_price, btc_market_cap, btc_volume_24h,
            network_hashrate, network_difficulty, block_reward,
            fear_greed_index, price_change_1h, price_change_24h, price_change_7d,
            source, created_at
        )
        SELECT 
            recorded_at, btc_price, btc_market_cap, btc_volume_24h,
            network_hashrate, network_difficulty, block_reward,
            fear_greed_index, price_change_1h, price_change_24h, price_change_7d,
            source, created_at
        FROM market_analytics_backup
        ORDER BY recorded_at ASC;
    """)
    
    # 5. 替换原表
    print("5. 替换原表...")
    cursor.execute("""
        DROP TABLE market_analytics;
        ALTER TABLE market_analytics_new RENAME TO market_analytics;
    """)
    
    # 6. 更新序列
    print("6. 重置序列...")
    cursor.execute("""
        SELECT setval('market_analytics_id_seq', (SELECT MAX(id) FROM market_analytics));
    """)
    
    # 7. 获取统计信息
    cursor.execute("""
        SELECT 
            COUNT(*) as total_records,
            COUNT(CASE WHEN source = 'historical_import' THEN 1 END) as historical_records,
            COUNT(CASE WHEN source LIKE '%mempool%' OR source LIKE '%blockchain%' THEN 1 END) as realtime_records,
            MIN(recorded_at) as earliest_date,
            MAX(recorded_at) as latest_date,
            MIN(btc_price) as min_price,
            MAX(btc_price) as max_price,
            MIN(network_hashrate) as min_hashrate,
            MAX(network_hashrate) as max_hashrate
        FROM market_analytics;
    """)
    
    stats = cursor.fetchone()
    
    conn.commit()
    cursor.close()
    conn.close()
    
    print("\n=== market_analytics表重新组织完成 ===")
    print(f"总记录数: {stats[0]}")
    print(f"历史数据: {stats[1]} 条")
    print(f"实时数据: {stats[2]} 条")
    print(f"时间范围: {stats[3]} 至 {stats[4]}")
    print(f"价格范围: ${stats[5]:,.2f} - ${stats[6]:,.2f}")
    print(f"算力范围: {stats[7]:.2f} - {stats[8]:.2f} EH/s")
    print("\n表已按时间顺序重新排列，并创建了性能优化索引")
    
    return stats

def analyze_data_quality():
    """分析数据质量"""
    
    conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
    cursor = conn.cursor()
    
    print("\n=== 数据质量分析 ===")
    
    # 检查数据完整性
    cursor.execute("""
        SELECT 
            DATE(recorded_at) as date,
            COUNT(*) as records_per_day,
            AVG(btc_price) as avg_price,
            AVG(network_hashrate) as avg_hashrate,
            source
        FROM market_analytics
        WHERE recorded_at >= '2024-01-01'
        GROUP BY DATE(recorded_at), source
        ORDER BY date DESC
        LIMIT 10;
    """)
    
    recent_data = cursor.fetchall()
    
    print("\n最近10天数据概览:")
    print("日期\t\t记录数\t平均价格\t平均算力\t数据源")
    print("-" * 80)
    for row in recent_data:
        print(f"{row[0]}\t{row[1]}\t${row[2]:,.0f}\t\t{row[3]:.1f} EH/s\t{row[4]}")
    
    # 检查数据连续性
    cursor.execute("""
        WITH date_series AS (
            SELECT generate_series(
                '2024-01-01'::date, 
                CURRENT_DATE::date, 
                '1 day'::interval
            )::date as expected_date
        ),
        actual_dates AS (
            SELECT DISTINCT DATE(recorded_at) as actual_date 
            FROM market_analytics 
            WHERE source = 'historical_import'
        )
        SELECT COUNT(*) as missing_days
        FROM date_series d
        LEFT JOIN actual_dates a ON d.expected_date = a.actual_date
        WHERE a.actual_date IS NULL;
    """)
    
    missing_days = cursor.fetchone()[0]
    print(f"\n历史数据缺失天数: {missing_days}")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    try:
        stats = reorganize_market_analytics()
        analyze_data_quality()
        print("\n✅ market_analytics表重新组织和优化完成!")
    except Exception as e:
        print(f"❌ 重新组织失败: {e}")
        import traceback
        traceback.print_exc()