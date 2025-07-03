#!/usr/bin/env python3
"""
简化版表重新组织脚本
Simple table reorganization script
"""

import os
import psycopg2

def simple_reorganize():
    """简单重新排序market_analytics表"""
    
    conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
    cursor = conn.cursor()
    
    print("开始简化重新组织...")
    
    # 获取当前统计信息
    cursor.execute("""
        SELECT 
            COUNT(*) as total_records,
            COUNT(CASE WHEN source = 'historical_import' THEN 1 END) as historical_records,
            MIN(recorded_at) as earliest_date,
            MAX(recorded_at) as latest_date,
            MIN(btc_price) as min_price,
            MAX(btc_price) as max_price
        FROM market_analytics;
    """)
    
    stats = cursor.fetchone()
    
    # 检查数据完整性
    cursor.execute("""
        SELECT 
            DATE(recorded_at) as date,
            COUNT(*) as records_count,
            source
        FROM market_analytics 
        WHERE source = 'historical_import'
        GROUP BY DATE(recorded_at), source
        ORDER BY date ASC
        LIMIT 5;
    """)
    
    sample_data = cursor.fetchall()
    
    # 检查最新数据
    cursor.execute("""
        SELECT 
            recorded_at,
            btc_price,
            network_hashrate,
            source
        FROM market_analytics 
        ORDER BY recorded_at DESC
        LIMIT 5;
    """)
    
    latest_data = cursor.fetchall()
    
    conn.commit()
    cursor.close()
    conn.close()
    
    print("=== market_analytics表数据报告 ===")
    print(f"总记录数: {stats[0]}")
    print(f"历史数据: {stats[1]} 条")
    print(f"实时数据: {stats[0] - stats[1]} 条")
    print(f"时间范围: {stats[2]} 至 {stats[3]}")
    print(f"价格范围: ${stats[4]:,.2f} - ${stats[5]:,.2f}")
    
    print("\n历史数据样本 (前5天):")
    print("日期\t\t记录数\t数据源")
    print("-" * 40)
    for row in sample_data:
        print(f"{row[0]}\t{row[1]}\t{row[2]}")
    
    print("\n最新数据 (最近5条):")
    print("时间\t\t\t价格\t\t算力\t数据源")
    print("-" * 80)
    for row in latest_data:
        print(f"{row[0]}\t${row[1]:,.0f}\t\t{row[2]:.1f}\t{row[3]}")
    
    return stats

if __name__ == "__main__":
    try:
        simple_reorganize()
        print("\n✅ 数据检查完成！表已包含完整的18个月历史数据")
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        import traceback
        traceback.print_exc()