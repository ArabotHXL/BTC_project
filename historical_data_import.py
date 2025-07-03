#!/usr/bin/env python3
"""
历史数据导入脚本
Historical Data Import Script

将比特币价格历史数据和网络算力数据合并插入到market_analytics表中
Merge Bitcoin price history and network hashrate data into market_analytics table
"""

import csv
import os
import psycopg2
from datetime import datetime
import re

def clean_price(price_str):
    """清理价格数据，去除逗号"""
    if isinstance(price_str, str):
        return float(price_str.replace(',', ''))
    return float(price_str)

def clean_volume(volume_str):
    """清理交易量数据，处理K单位"""
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

def load_price_data(file_path):
    """加载价格历史数据"""
    price_data = {}
    
    with open(file_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                # 处理可能的BOM字符
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
                    'close_price': clean_price(row['收盘']),
                    'open_price': clean_price(row['开盘']),
                    'high_price': clean_price(row['高']),
                    'low_price': clean_price(row['低']),
                    'volume_24h': clean_volume(row['交易量']),
                    'price_change_24h': clean_percentage(row['涨跌幅'])
                }
            except Exception as e:
                # print(f"跳过价格数据行: {row}, 错误: {e}")
                continue
    
    return price_data

def load_hashrate_data(file_path):
    """加载算力历史数据"""
    hashrate_data = {}
    
    with open(file_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                # 处理可能的BOM字符
                date_key_found = None
                for key in row.keys():
                    if 'Date' in key:
                        date_key_found = key
                        break
                
                if not date_key_found:
                    continue
                    
                date_obj = parse_date(row[date_key_found])
                date_key = date_obj.strftime("%Y-%m-%d")
                
                hashrate_data[date_key] = {
                    'network_hashrate': float(row['HashRate_EH_s']),
                    'network_difficulty': convert_difficulty_to_full(float(row['Difficulty_T']))
                }
            except Exception as e:
                # print(f"跳过算力数据行: {row}, 错误: {e}")
                continue
    
    return hashrate_data

def merge_and_insert_data():
    """合并数据并插入到market_analytics表"""
    
    # 文件路径
    price_file = "attached_assets/比特币历史数据_1751510290564.csv"
    hashrate_file = "attached_assets/BTC_Hashrate_2024-01-01_to_2025-07-02_1751510290562.csv"
    
    print("正在加载价格历史数据...")
    price_data = load_price_data(price_file)
    print(f"加载了 {len(price_data)} 条价格记录")
    
    print("正在加载算力历史数据...")
    hashrate_data = load_hashrate_data(hashrate_file)
    print(f"加载了 {len(hashrate_data)} 条算力记录")
    
    # 数据库连接
    conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
    cursor = conn.cursor()
    
    # 找到共同的日期
    common_dates = set(price_data.keys()) & set(hashrate_data.keys())
    print(f"找到 {len(common_dates)} 个共同日期")
    
    # 清理现有历史数据（可选，避免重复）
    print("清理现有历史数据...")
    cursor.execute("""
        DELETE FROM market_analytics 
        WHERE recorded_at >= '2024-01-01' 
        AND recorded_at < '2025-07-03'
        AND source LIKE '%historical%'
    """)
    
    # 插入合并数据
    inserted_count = 0
    for date_key in sorted(common_dates):
        try:
            price = price_data[date_key]
            hashrate = hashrate_data[date_key]
            
            # 设置记录时间为该日期的中午12点
            recorded_at = datetime.strptime(date_key, "%Y-%m-%d").replace(hour=12, minute=0, second=0)
            
            cursor.execute("""
                INSERT INTO market_analytics (
                    recorded_at, btc_price, btc_market_cap, btc_volume_24h,
                    network_hashrate, network_difficulty, block_reward,
                    fear_greed_index, price_change_1h, price_change_24h, price_change_7d,
                    source, created_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            """, (
                recorded_at,
                price['close_price'],
                None,  # btc_market_cap
                price['volume_24h'],
                hashrate['network_hashrate'],
                hashrate['network_difficulty'],
                3.125,  # 当前区块奖励
                None,  # fear_greed_index
                None,  # price_change_1h
                price['price_change_24h'],
                None,  # price_change_7d
                'historical_import',
                datetime.now()
            ))
            
            inserted_count += 1
            
        except Exception as e:
            print(f"插入数据失败 {date_key}: {e}")
            continue
    
    conn.commit()
    cursor.close()
    conn.close()
    
    print(f"成功插入 {inserted_count} 条历史数据记录")
    return inserted_count

if __name__ == "__main__":
    print("开始历史数据导入...")
    try:
        count = merge_and_insert_data()
        print(f"历史数据导入完成！共插入 {count} 条记录")
    except Exception as e:
        print(f"导入失败: {e}")
        import traceback
        traceback.print_exc()