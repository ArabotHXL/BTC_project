-- ============================================================================
-- HashInsight CDC Platform - DLQ Replay Fields
-- 为event_dlq表添加回放字段
-- 
-- Author: HashInsight Team
-- Version: 1.0.0
-- Date: 2025-10-08
-- ============================================================================

-- 1. 添加回放状态字段
ALTER TABLE event_dlq 
ADD COLUMN IF NOT EXISTS replayed BOOLEAN DEFAULT false;

ALTER TABLE event_dlq 
ADD COLUMN IF NOT EXISTS replayed_at TIMESTAMP;

-- 2. 创建索引（提升查询性能）
CREATE INDEX IF NOT EXISTS idx_dlq_replayed ON event_dlq(replayed) WHERE replayed = false;
CREATE INDEX IF NOT EXISTS idx_dlq_consumer_kind ON event_dlq(consumer_name, event_kind);

-- 3. 添加注释
COMMENT ON COLUMN event_dlq.replayed IS '是否已从DLQ回放';
COMMENT ON COLUMN event_dlq.replayed_at IS 'DLQ回放时间';

-- ============================================================================
-- 回滚脚本：
-- 
-- DROP INDEX IF EXISTS idx_dlq_replayed;
-- DROP INDEX IF EXISTS idx_dlq_consumer_kind;
-- ALTER TABLE event_dlq DROP COLUMN IF EXISTS replayed;
-- ALTER TABLE event_dlq DROP COLUMN IF EXISTS replayed_at;
-- ============================================================================
