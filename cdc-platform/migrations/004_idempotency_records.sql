-- ============================================================================
-- HashInsight CDC Platform - Idempotency Records Table
-- API幂等性记录表
-- 
-- Author: HashInsight Team
-- Version: 1.0.0
-- Date: 2025-10-08
-- ============================================================================

-- 1. 创建idempotency_records表
CREATE TABLE IF NOT EXISTS idempotency_records (
    id SERIAL PRIMARY KEY,
    idempotency_key TEXT NOT NULL,
    method VARCHAR(10) NOT NULL,
    path TEXT NOT NULL,
    response_status INTEGER NOT NULL,
    response_body JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    
    -- 复合唯一约束（同一幂等键+方法+路径只能有一条记录）
    CONSTRAINT uk_idempotency UNIQUE (idempotency_key, method, path)
);

-- 2. 创建索引（提升查询性能）
CREATE INDEX idx_idempotency_key ON idempotency_records(idempotency_key);
CREATE INDEX idx_idempotency_created_at ON idempotency_records(created_at);
CREATE INDEX idx_idempotency_composite ON idempotency_records(idempotency_key, method, path);

-- 3. 添加注释
COMMENT ON TABLE idempotency_records IS 'API幂等性记录表，防止重复请求';
COMMENT ON COLUMN idempotency_records.idempotency_key IS '客户端提供的幂等键（UUID或其他唯一标识）';
COMMENT ON COLUMN idempotency_records.method IS 'HTTP方法（POST/PATCH/PUT/DELETE）';
COMMENT ON COLUMN idempotency_records.path IS '请求路径';
COMMENT ON COLUMN idempotency_records.response_status IS 'HTTP响应状态码';
COMMENT ON COLUMN idempotency_records.response_body IS '响应体（JSON格式）';
COMMENT ON COLUMN idempotency_records.created_at IS '记录创建时间';

-- ============================================================================
-- 使用示例：
-- 
-- 1. 客户端发送请求时携带Idempotency-Key头：
--    POST /api/miners
--    Idempotency-Key: 550e8400-e29b-41d4-a716-446655440000
-- 
-- 2. 服务器检查idempotency_records表：
--    - 如果存在相同key+method+path，返回缓存的响应
--    - 如果不存在，处理请求并保存响应到此表
-- 
-- 3. 查询幂等性记录：
--    SELECT * FROM idempotency_records 
--    WHERE idempotency_key = '550e8400-e29b-41d4-a716-446655440000';
-- ============================================================================

-- 4. 定期清理过期记录的函数
CREATE OR REPLACE FUNCTION cleanup_expired_idempotency_records()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM idempotency_records
    WHERE created_at < NOW() - INTERVAL '24 hours';
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    RAISE NOTICE 'Cleaned up % expired idempotency records', deleted_count;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- 5. 创建定时任务（需要pg_cron扩展，可选）
-- CREATE EXTENSION IF NOT EXISTS pg_cron;
-- SELECT cron.schedule('cleanup-idempotency', '0 2 * * *', 'SELECT cleanup_expired_idempotency_records()');

-- ============================================================================
-- 回滚脚本：
-- 
-- DROP INDEX IF EXISTS idx_idempotency_key;
-- DROP INDEX IF EXISTS idx_idempotency_created_at;
-- DROP INDEX IF EXISTS idx_idempotency_composite;
-- DROP TABLE IF EXISTS idempotency_records;
-- DROP FUNCTION IF EXISTS cleanup_expired_idempotency_records();
-- ============================================================================
