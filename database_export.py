#!/usr/bin/env python3
"""
数据库完整导出工具
导出所有表的数据为多种格式
"""

import os
import psycopg2
import pandas as pd
from datetime import datetime
import json
import csv

def get_database_connection():
    """获取数据库连接"""
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL environment variable not found")
    return psycopg2.connect(database_url)

def get_all_tables(conn):
    """获取所有表名"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        ORDER BY table_name;
    """)
    tables = [row[0] for row in cursor.fetchall()]
    cursor.close()
    return tables

def export_table_to_csv(conn, table_name, output_dir):
    """导出表为CSV格式"""
    try:
        df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
        csv_file = os.path.join(output_dir, f"{table_name}.csv")
        df.to_csv(csv_file, index=False, encoding='utf-8')
        return len(df), csv_file
    except Exception as e:
        print(f"Error exporting {table_name} to CSV: {e}")
        return 0, None

def export_table_to_json(conn, table_name, output_dir):
    """导出表为JSON格式"""
    try:
        df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
        # 处理日期时间字段
        df = df.where(pd.notnull(df), None)
        for col in df.columns:
            if df[col].dtype == 'datetime64[ns]':
                df[col] = df[col].dt.strftime('%Y-%m-%d %H:%M:%S')
        
        json_file = os.path.join(output_dir, f"{table_name}.json")
        df.to_json(json_file, orient='records', indent=2, force_ascii=False)
        return len(df), json_file
    except Exception as e:
        print(f"Error exporting {table_name} to JSON: {e}")
        return 0, None

def export_all_data():
    """导出所有数据"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = f"database_export_{timestamp}"
    os.makedirs(output_dir, exist_ok=True)
    
    export_summary = {
        "export_timestamp": datetime.now().isoformat(),
        "tables_exported": [],
        "total_records": 0,
        "files_created": []
    }
    
    try:
        conn = get_database_connection()
        print("✅ 数据库连接成功")
        
        tables = get_all_tables(conn)
        print(f"📊 发现 {len(tables)} 个表:")
        for table in tables:
            print(f"  - {table}")
        
        print(f"\n🚀 开始导出数据到目录: {output_dir}")
        
        for table_name in tables:
            print(f"\n📋 导出表: {table_name}")
            
            # 导出为CSV
            csv_count, csv_file = export_table_to_csv(conn, table_name, output_dir)
            if csv_file:
                print(f"  ✅ CSV: {csv_count} 条记录 -> {csv_file}")
                export_summary["files_created"].append(csv_file)
            
            # 导出为JSON
            json_count, json_file = export_table_to_json(conn, table_name, output_dir)
            if json_file:
                print(f"  ✅ JSON: {json_count} 条记录 -> {json_file}")
                export_summary["files_created"].append(json_file)
            
            table_info = {
                "table_name": table_name,
                "record_count": csv_count if csv_count else json_count,
                "csv_file": csv_file,
                "json_file": json_file
            }
            export_summary["tables_exported"].append(table_info)
            export_summary["total_records"] += table_info["record_count"]
        
        # 保存导出摘要
        summary_file = os.path.join(output_dir, "export_summary.json")
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(export_summary, f, indent=2, ensure_ascii=False)
        
        print(f"\n🎉 导出完成!")
        print(f"📁 输出目录: {output_dir}")
        print(f"📊 总计 {len(tables)} 个表, {export_summary['total_records']} 条记录")
        print(f"📄 导出摘要: {summary_file}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ 导出失败: {e}")
        return None
    
    return output_dir

if __name__ == "__main__":
    export_dir = export_all_data()
    if export_dir:
        print(f"\n✨ 数据库完整导出完成: {export_dir}")