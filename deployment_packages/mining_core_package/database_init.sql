-- Mining Core Module Database Initialization Script
-- 挖矿核心模块数据库初始化脚本

-- 创建数据库 (如果不存在)
-- Create database (if not exists)
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'mining_core_db') THEN
        PERFORM dblink_exec('host=localhost user=postgres', 'CREATE DATABASE mining_core_db');
    END IF;
END $$;

-- 连接到mining_core_db数据库
\c mining_core_db;

-- 创建扩展
-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- 设置时区
-- Set timezone
SET timezone = 'UTC';

-- 创建索引函数
-- Create index functions
CREATE OR REPLACE FUNCTION create_index_if_not_exists(table_name text, index_name text, index_def text)
RETURNS void AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE tablename = table_name AND indexname = index_name
    ) THEN
        EXECUTE index_def;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- 性能优化配置
-- Performance optimization settings
ALTER SYSTEM SET shared_preload_libraries = 'pg_stat_statements';
ALTER SYSTEM SET max_connections = 100;
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET default_statistics_target = 100;
ALTER SYSTEM SET random_page_cost = 1.1;
ALTER SYSTEM SET effective_io_concurrency = 200;

-- 重新加载配置
-- Reload configuration
SELECT pg_reload_conf();

-- 创建应用用户 (如果不存在)
-- Create application user (if not exists)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_user WHERE usename = 'mining_user') THEN
        CREATE USER mining_user WITH PASSWORD 'mining_password';
    END IF;
END $$;

-- 授予权限
-- Grant privileges
GRANT CONNECT ON DATABASE mining_core_db TO mining_user;
GRANT USAGE ON SCHEMA public TO mining_user;
GRANT CREATE ON SCHEMA public TO mining_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO mining_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO mining_user;

-- 设置默认权限
-- Set default privileges
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO mining_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO mining_user;

-- 优化查询性能的自定义函数
-- Custom functions for query optimization
CREATE OR REPLACE FUNCTION update_modified_time()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 创建清理旧数据的函数
-- Create function to clean old data
CREATE OR REPLACE FUNCTION clean_old_data(table_name text, days_to_keep integer)
RETURNS void AS $$
BEGIN
    EXECUTE format('DELETE FROM %I WHERE created_at < NOW() - INTERVAL ''%s days''', 
                   table_name, days_to_keep);
END;
$$ LANGUAGE plpgsql;

-- 显示初始化完成信息
-- Show initialization completion
\echo 'Mining Core Database initialization completed successfully!'
\echo 'Database: mining_core_db'
\echo 'User: mining_user'
\echo 'Extensions: uuid-ossp, pg_stat_statements'
\echo 'Performance optimizations applied'