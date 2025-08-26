#!/usr/bin/env python3
"""
数据库架构提取工具
生成完整的CREATE TABLE语句和数据库重建脚本
"""

import os
import psycopg2
import json
from datetime import datetime

def get_database_connection():
    """获取数据库连接"""
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL environment variable not found")
    return psycopg2.connect(database_url)

def get_table_schema(conn, table_name):
    """获取表的完整架构信息"""
    cursor = conn.cursor()
    
    # 获取表结构
    cursor.execute("""
        SELECT 
            column_name,
            data_type,
            is_nullable,
            column_default,
            character_maximum_length,
            numeric_precision,
            numeric_scale
        FROM information_schema.columns 
        WHERE table_name = %s 
        AND table_schema = 'public'
        ORDER BY ordinal_position;
    """, (table_name,))
    
    columns = cursor.fetchall()
    
    # 获取主键信息
    cursor.execute("""
        SELECT column_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu 
        ON tc.constraint_name = kcu.constraint_name
        WHERE tc.table_name = %s 
        AND tc.constraint_type = 'PRIMARY KEY'
        AND tc.table_schema = 'public';
    """, (table_name,))
    
    primary_keys = [row[0] for row in cursor.fetchall()]
    
    # 获取外键信息
    cursor.execute("""
        SELECT
            kcu.column_name,
            ccu.table_name AS foreign_table_name,
            ccu.column_name AS foreign_column_name
        FROM information_schema.table_constraints AS tc
        JOIN information_schema.key_column_usage AS kcu
        ON tc.constraint_name = kcu.constraint_name
        JOIN information_schema.constraint_column_usage AS ccu
        ON ccu.constraint_name = tc.constraint_name
        WHERE tc.constraint_type = 'FOREIGN KEY'
        AND tc.table_name = %s
        AND tc.table_schema = 'public';
    """, (table_name,))
    
    foreign_keys = cursor.fetchall()
    
    # 获取索引信息
    cursor.execute("""
        SELECT
            i.relname AS index_name,
            array_agg(a.attname ORDER BY a.attnum) AS column_names,
            ix.indisunique
        FROM pg_class t
        JOIN pg_index ix ON t.oid = ix.indrelid
        JOIN pg_class i ON i.oid = ix.indexrelid
        JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY(ix.indkey)
        WHERE t.relname = %s
        AND t.relkind = 'r'
        AND i.relname NOT LIKE '%%_pkey'
        GROUP BY i.relname, ix.indisunique;
    """, (table_name,))
    
    indexes = cursor.fetchall()
    
    cursor.close()
    
    return {
        'columns': columns,
        'primary_keys': primary_keys,
        'foreign_keys': foreign_keys,
        'indexes': indexes
    }

def generate_create_table_sql(table_name, schema_info):
    """生成CREATE TABLE SQL语句"""
    sql_parts = [f"CREATE TABLE {table_name} ("]
    column_definitions = []
    
    for column in schema_info['columns']:
        col_name, data_type, is_nullable, col_default, char_max_len, num_precision, num_scale = column
        
        # 构建列定义
        col_def = f"    {col_name} "
        
        # 数据类型处理
        if data_type == 'character varying':
            if char_max_len:
                col_def += f"VARCHAR({char_max_len})"
            else:
                col_def += "VARCHAR"
        elif data_type == 'integer':
            col_def += "INTEGER"
        elif data_type == 'bigint':
            col_def += "BIGINT"
        elif data_type == 'numeric':
            if num_precision and num_scale:
                col_def += f"NUMERIC({num_precision},{num_scale})"
            elif num_precision:
                col_def += f"NUMERIC({num_precision})"
            else:
                col_def += "NUMERIC"
        elif data_type == 'timestamp without time zone':
            col_def += "TIMESTAMP"
        elif data_type == 'timestamp with time zone':
            col_def += "TIMESTAMPTZ"
        elif data_type == 'boolean':
            col_def += "BOOLEAN"
        elif data_type == 'text':
            col_def += "TEXT"
        elif data_type == 'date':
            col_def += "DATE"
        elif data_type == 'real':
            col_def += "REAL"
        elif data_type == 'double precision':
            col_def += "DOUBLE PRECISION"
        elif data_type == 'json':
            col_def += "JSON"
        elif data_type == 'jsonb':
            col_def += "JSONB"
        else:
            col_def += data_type.upper()
        
        # 处理NOT NULL
        if is_nullable == 'NO':
            col_def += " NOT NULL"
        
        # 处理默认值
        if col_default:
            if 'nextval' in col_default:
                # 序列类型，转换为SERIAL
                if 'bigint' in data_type:
                    col_def = col_def.replace('BIGINT', 'BIGSERIAL')
                else:
                    col_def = col_def.replace('INTEGER', 'SERIAL')
                col_def = col_def.replace(' NOT NULL', '')  # SERIAL自动包含NOT NULL
            else:
                col_def += f" DEFAULT {col_default}"
        
        column_definitions.append(col_def)
    
    sql_parts.append(",\n".join(column_definitions))
    
    # 添加主键约束
    if schema_info['primary_keys']:
        pk_cols = ", ".join(schema_info['primary_keys'])
        sql_parts.append(f",\n    PRIMARY KEY ({pk_cols})")
    
    sql_parts.append("\n);")
    
    return "".join(sql_parts)

def generate_foreign_key_sql(table_name, schema_info):
    """生成外键约束SQL"""
    fk_sqls = []
    for fk in schema_info['foreign_keys']:
        col_name, foreign_table, foreign_col = fk
        constraint_name = f"fk_{table_name}_{col_name}"
        sql = f"ALTER TABLE {table_name} ADD CONSTRAINT {constraint_name} " \
              f"FOREIGN KEY ({col_name}) REFERENCES {foreign_table}({foreign_col});"
        fk_sqls.append(sql)
    return fk_sqls

def generate_index_sql(table_name, schema_info):
    """生成索引SQL"""
    index_sqls = []
    for idx in schema_info['indexes']:
        idx_name, columns, is_unique = idx
        cols = ", ".join(columns)
        unique_str = "UNIQUE " if is_unique else ""
        sql = f"CREATE {unique_str}INDEX {idx_name} ON {table_name} ({cols});"
        index_sqls.append(sql)
    return index_sqls

def extract_complete_schema():
    """提取完整的数据库架构"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = f"complete_database_backup_{timestamp}"
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        conn = get_database_connection()
        print("✅ 数据库连接成功")
        
        # 获取所有表名
        cursor = conn.cursor()
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name;
        """)
        tables = [row[0] for row in cursor.fetchall()]
        cursor.close()
        
        print(f"📊 发现 {len(tables)} 个表")
        
        # 生成完整的SQL脚本
        create_tables_sql = []
        foreign_keys_sql = []
        indexes_sql = []
        
        schema_summary = {
            "extraction_timestamp": datetime.now().isoformat(),
            "total_tables": len(tables),
            "tables": []
        }
        
        for table_name in tables:
            print(f"📋 处理表: {table_name}")
            
            schema_info = get_table_schema(conn, table_name)
            
            # 生成CREATE TABLE语句
            create_sql = generate_create_table_sql(table_name, schema_info)
            create_tables_sql.append(f"-- 表: {table_name}\n{create_sql}\n")
            
            # 生成外键语句
            fk_sqls = generate_foreign_key_sql(table_name, schema_info)
            foreign_keys_sql.extend(fk_sqls)
            
            # 生成索引语句
            idx_sqls = generate_index_sql(table_name, schema_info)
            indexes_sql.extend(idx_sqls)
            
            table_summary = {
                "table_name": table_name,
                "column_count": len(schema_info['columns']),
                "primary_keys": schema_info['primary_keys'],
                "foreign_keys_count": len(schema_info['foreign_keys']),
                "indexes_count": len(schema_info['indexes'])
            }
            schema_summary["tables"].append(table_summary)
        
        # 写入完整的数据库创建脚本
        full_script_path = os.path.join(output_dir, "01_create_database_schema.sql")
        with open(full_script_path, 'w', encoding='utf-8') as f:
            f.write("-- ========================================\n")
            f.write("-- BTC Mining Calculator Database Schema\n")
            f.write(f"-- Generated: {datetime.now().isoformat()}\n")
            f.write("-- ========================================\n\n")
            
            f.write("-- 创建数据库表\n")
            f.write("-- ========================================\n\n")
            f.write("\n".join(create_tables_sql))
            
            if foreign_keys_sql:
                f.write("\n-- 外键约束\n")
                f.write("-- ========================================\n\n")
                f.write("\n".join(foreign_keys_sql))
                f.write("\n")
            
            if indexes_sql:
                f.write("\n-- 索引\n")
                f.write("-- ========================================\n\n")
                f.write("\n".join(indexes_sql))
                f.write("\n")
        
        # 保存架构摘要
        summary_path = os.path.join(output_dir, "database_schema_summary.json")
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(schema_summary, f, indent=2, ensure_ascii=False)
        
        print(f"\n🎉 数据库架构提取完成!")
        print(f"📁 输出目录: {output_dir}")
        print(f"📄 SQL脚本: {full_script_path}")
        print(f"📊 架构摘要: {summary_path}")
        
        conn.close()
        return output_dir
        
    except Exception as e:
        print(f"❌ 架构提取失败: {e}")
        return None

if __name__ == "__main__":
    schema_dir = extract_complete_schema()
    if schema_dir:
        print(f"\n✨ 数据库架构提取完成: {schema_dir}")