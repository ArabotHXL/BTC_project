#!/usr/bin/env python3
"""
优化的历史数据导入脚本 - 批量插入版本
Optimized Historical Data Import Script - Batch Insert Version
"""

import csv
import os
import psycopg2
from datetime import datetime
import psycopg2.extras

def clean_price(price_str):
    """清理价格数据"""
    if isinstance(price_str, str):
        return float(price_str.replace(',', ''))
    return float(price_str)

def clean_volume(volume_str):
    """清理交易量数据"""
    if isinstance(volume_str, str):
        volume_str = volume_str.replace(',', '')
        if volume_str.endswith('K'):
            return int(float(volume_str[:-1]) * 1000)
        return int(float(volume_str))
    return int(volume_str)

def clean_percentage(pct_str):
    """清理百分比数据"""
    if isinstance(pct_str, str):
        return float(pct_str.replace('%', ''))
    return float(pct_str)

def convert_difficulty_to_full(difficulty_t):
    """将难度从T单位转换为完整数值"""
    return float(difficulty_t) * 1e12

def parse_date(date_str):
    """解析日期字符串"""
    try:
        # 尝试解析 "2025-7-2" 格式
        if len(date_str.split('-')) == 3:
            year, month, day = date_str.split('-')
            return datetime(int(year), int(month), int(day))
    except:
        pass
    
    try:
        # 尝试解析 "2024-01-01 00:00:00" 格式
        return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
    except:
        pass
    
    try:
        # 尝试解析 "2024-01-01" 格式
        return datetime.strptime(date_str, "%Y-%m-%d")
    except:
        pass
    
    raise ValueError(f"无法解析日期格式: {date_str}")

def batch_import_data():
    """批量导入历史数据"""
    
    # 文件路径
    price_file = "attached_assets/比特币历史数据_1751510290564.csv"
    hashrate_file = "attached_assets/BTC_Hashrate_2024-01-01_to_2025-07-02_1751510290562.csv"
    
    print("开始批量历史数据导入...")
    
    # 准备合并数据
    merged_data = []
    
    # 加载价格数据
    print("正在加载价格数据...")
    price_data = {}
    with open(price_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                date_key_found = None
                for key in row.keys():
                    if '日期' in key:
                        date_key_found = key
                        break
                
                if not date_key_found:
                    continue
                    
                date_obj = parse_date(row[date_key_found])
                date_key = date_obj.strftime("%Y-%m-%d")
                
                price_data[date_key] = {
                    'date_obj': date_obj,
                    'close_price': clean_price(row['收盘']),
                    'volume_24h': clean_volume(row['交易量']),
                    'price_change_24h': clean_percentage(row['涨跌幅'])
                }
            except:
                continue
    
    print(f"加载了 {len(price_data)} 条价格记录")
    
    # 加载算力数据并合并
    print("正在加载算力数据并合并...")
    with open(hashrate_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                date_key_found = None
                for key in row.keys():
                    if 'Date' in key:
                        date_key_found = key
                        break
                
                if not date_key_found:
                    continue
                    
                date_obj = parse_date(row[date_key_found])
                date_key = date_obj.strftime("%Y-%m-%d")
                
                # 如果有对应的价格数据，则合并
                if date_key in price_data:
                    price_info = price_data[date_key]
                    
                    # 设置记录时间为该日期的中午12点
                    recorded_at = price_info['date_obj'].replace(hour=12, minute=0, second=0)
                    
                    merged_record = (
                        recorded_at,
                        price_info['close_price'],
                        None,  # btc_market_cap
                        price_info['volume_24h'],
                        float(row['HashRate_EH_s']),
                        convert_difficulty_to_full(float(row['Difficulty_T'])),
                        3.125,  # block_reward
                        None,  # fear_greed_index
                        None,  # price_change_1h
                        price_info['price_change_24h'],
                        None,  # price_change_7d
                        'historical_import',
                        datetime.now()
                    )
                    
                    merged_data.append(merged_record)
                    
            except:
                continue
    
    print(f"准备插入 {len(merged_data)} 条合并记录")
    
    # 数据库连接和批量插入
    conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
    cursor = conn.cursor()
    
    # 清理现有历史数据
    print("清理现有历史数据...")
    cursor.execute("""
        DELETE FROM market_analytics 
        WHERE source = 'historical_import'
    """)
    
    # 批量插入
    print("批量插入历史数据...")
    insert_query = """
        INSERT INTO market_analytics (
            recorded_at, btc_price, btc_market_cap, btc_volume_24h,
            network_hashrate, network_difficulty, block_reward,
            fear_greed_index, price_change_1h, price_change_24h, price_change_7d,
            source, created_at
        ) VALUES %s
    """
    
    psycopg2.extras.execute_values(
        cursor, insert_query, merged_data, 
        template=None, page_size=100
    )
    
    conn.commit()
    cursor.close()
    conn.close()
    
    print(f"成功插入 {len(merged_data)} 条历史数据记录")
    return len(merged_data)

if __name__ == "__main__":
    try:
        count = batch_import_data()
        print(f"历史数据导入完成！共插入 {count} 条记录")
    except Exception as e:
        print(f"导入失败: {e}")
        import traceback
        traceback.print_exc()