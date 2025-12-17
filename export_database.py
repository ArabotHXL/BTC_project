#!/usr/bin/env python3
"""
HashInsight Enterprise - Database Export Utility

SECURITY WARNING:
This script requires database credentials to be set via environment variables.
NEVER commit database passwords to version control.

REQUIRED ENVIRONMENT VARIABLES:
- DB_HOST: Database hostname (e.g., ep-xxx.neon.tech)
- DB_PORT: Database port (default: 5432)
- DB_USER: Database username
- DB_PASSWORD: Database password
- DB_NAME: Database name

USAGE:
1. Set environment variables:
   export DB_HOST="your-host.neon.tech"
   export DB_USER="your_user"
   export DB_PASSWORD="your_password"
   export DB_NAME="your_database"

2. Run the script:
   python export_database.py

3. The script will create 'database_backup_full.sql' in the current directory.

SAFETY CONSIDERATIONS:
- Always backup your database before running migrations
- Review the generated SQL file before importing
- Ensure sufficient disk space for large databases
- Test imports on a development database first

OUTPUT:
- File: database_backup_full.sql
- Format: PostgreSQL-compatible SQL with DROP/CREATE/INSERT statements
- Encoding: UTF-8
"""
import psycopg2
import os
import sys
from datetime import datetime

# Database connection configuration - REQUIRES environment variables
def get_db_config():
    """Get database configuration from environment variables."""
    required_vars = ['DB_HOST', 'DB_USER', 'DB_PASSWORD', 'DB_NAME']
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        print("❌ ERROR: Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nPlease set all required environment variables before running this script.")
        print("See the script header for usage instructions.")
        sys.exit(1)
    
    return {
        'host': os.environ.get('DB_HOST'),
        'port': int(os.environ.get('DB_PORT', '5432')),
        'user': os.environ.get('DB_USER'),
        'password': os.environ.get('DB_PASSWORD'),
        'database': os.environ.get('DB_NAME')
    }

def export_database():
    """导出完整数据库到SQL文件"""
    print("=" * 80)
    print("HashInsight Enterprise - 完整数据库导出")
    print("=" * 80)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Get database configuration
    db_config = get_db_config()
    
    try:
        # 连接到数据库
        print(f"连接到数据库: {db_config['host']}")
        conn = psycopg2.connect(**db_config)
        cur = conn.cursor()
        
        # 获取所有表
        cur.execute("""
            SELECT tablename 
            FROM pg_tables 
            WHERE schemaname = 'public' 
            ORDER BY tablename
        """)
        tables = [row[0] for row in cur.fetchall()]
        print(f"✅ 找到 {len(tables)} 个表\n")
        
        # 创建SQL导出文件
        sql_file = open('database_backup_full.sql', 'w', encoding='utf-8')
        
        # 写入头部注释
        sql_file.write(f"""-- HashInsight Enterprise Database Backup
-- 导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
-- 数据库: {db_config['database']}
-- 主机: {db_config['host']}
-- 表数量: {len(tables)}

SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;

""")
        
        total_rows = 0
        
        for table_name in tables:
            try:
                # 获取表的行数
                cur.execute(f"SELECT COUNT(*) FROM {table_name}")
                row_count = cur.fetchone()[0]
                total_rows += row_count
                
                print(f"导出表: {table_name} ({row_count} rows)")
                
                # 导出表结构（使用pg_dump格式）
                sql_file.write(f"\n-- Table: {table_name}\n")
                sql_file.write(f"DROP TABLE IF EXISTS {table_name} CASCADE;\n")
                
                # 获取CREATE TABLE语句
                cur.execute(f"""
                    SELECT 
                        'CREATE TABLE ' || quote_ident(tablename) || ' (' ||
                        string_agg(
                            quote_ident(column_name) || ' ' || 
                            data_type || 
                            CASE WHEN character_maximum_length IS NOT NULL 
                                THEN '(' || character_maximum_length || ')' 
                                ELSE '' END ||
                            CASE WHEN is_nullable = 'NO' THEN ' NOT NULL' ELSE '' END ||
                            CASE WHEN column_default IS NOT NULL 
                                THEN ' DEFAULT ' || column_default 
                                ELSE '' END,
                            ', '
                        ) || ');'
                    FROM information_schema.columns c
                    JOIN pg_tables t ON c.table_name = t.tablename
                    WHERE c.table_name = '{table_name}' AND c.table_schema = 'public'
                    GROUP BY tablename
                """)
                
                create_result = cur.fetchone()
                if create_result:
                    sql_file.write(create_result[0] + "\n")
                
                # 导出数据（如果有）
                if row_count > 0:
                    cur.execute(f"SELECT * FROM {table_name}")
                    columns = [desc[0] for desc in cur.description]
                    
                    sql_file.write(f"\n-- Data for {table_name}\n")
                    
                    for row in cur.fetchall():
                        # 构造INSERT语句
                        values = []
                        for val in row:
                            if val is None:
                                values.append('NULL')
                            elif isinstance(val, str):
                                # 转义单引号
                                escaped = val.replace("'", "''")
                                values.append(f"'{escaped}'")
                            elif isinstance(val, (int, float)):
                                values.append(str(val))
                            elif isinstance(val, bool):
                                values.append('TRUE' if val else 'FALSE')
                            elif isinstance(val, datetime):
                                values.append(f"'{val.isoformat()}'")
                            else:
                                # 其他类型转为字符串
                                values.append(f"'{str(val)}'")
                        
                        insert_stmt = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({', '.join(values)});\n"
                        sql_file.write(insert_stmt)
                
                sql_file.write("\n")
                
            except Exception as e:
                print(f"⚠️  导出表 {table_name} 时出错: {e}")
                continue
        
        sql_file.close()
        cur.close()
        conn.close()
        
        # 获取文件大小
        file_size = os.path.getsize('database_backup_full.sql') / (1024 * 1024)
        
        print("\n" + "=" * 80)
        print("✅ 数据库导出完成！")
        print("=" * 80)
        print(f"导出表数量: {len(tables)}")
        print(f"总数据行数: {total_rows:,}")
        print(f"SQL文件大小: {file_size:.2f} MB")
        print(f"文件位置: database_backup_full.sql")
        print("=" * 80)
        
        return True
        
    except Exception as e:
        print(f"\n❌ 导出失败: {e}")
        return False

if __name__ == "__main__":
    success = export_database()
    
    if success:
        print("\n✨ 下一步：")
        print("   1. 在Replit创建新的PostgreSQL数据库")
        print("   2. 运行导入脚本将数据导入新数据库")
    else:
        print("\n⚠️  导出失败，请检查数据库连接")
