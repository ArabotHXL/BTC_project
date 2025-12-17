-- =====================================================
-- HashInsight CDC Foundation Migration
-- Version: 001
-- Description: Event Outbox, Consumer Inbox, TimescaleDB
-- =====================================================

-- 启用TimescaleDB扩展
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- 启用Row Level Security支持
ALTER DATABASE hashinsight SET row_security = on;

-- =====================================================
-- 1. Event Outbox表（Transactional Outbox模式）
-- =====================================================

CREATE TABLE IF NOT EXISTS event_outbox (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    kind TEXT NOT NULL,                          -- 事件类型: miner.added, treasury.trade_executed等
    user_id TEXT NOT NULL,                       -- 用户ID（用作Kafka消息键）
    tenant_id TEXT NOT NULL DEFAULT 'default',   -- 租户ID（多租户支持）
    entity_id TEXT,                              -- 实体ID（可选）
    payload JSONB NOT NULL,                      -- 事件负载
    idempotency_key TEXT UNIQUE,                 -- 幂等键
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    processed BOOLEAN NOT NULL DEFAULT false,    -- 是否已被Debezium处理
    processed_at TIMESTAMPTZ                     -- 处理时间
);

-- Outbox关键索引
CREATE INDEX idx_outbox_processed_created ON event_outbox (processed, created_at) 
    WHERE processed = false;  -- 部分索引，只索引未处理的
CREATE INDEX idx_outbox_user_created ON event_outbox (user_id, created_at);
CREATE INDEX idx_outbox_kind ON event_outbox (kind);
CREATE INDEX idx_outbox_tenant ON event_outbox (tenant_id);

-- Outbox注释
COMMENT ON TABLE event_outbox IS 'Transactional Outbox: 所有领域事件的发件箱';
COMMENT ON COLUMN event_outbox.kind IS '事件类型，用于路由到不同Kafka主题';
COMMENT ON COLUMN event_outbox.idempotency_key IS '幂等键，防止重复事件';

-- =====================================================
-- 2. Consumer Inbox表（幂等消费）
-- =====================================================

CREATE TABLE IF NOT EXISTS consumer_inbox (
    consumer_name TEXT NOT NULL,                 -- 消费者名称: portfolio-consumer, intel-consumer
    event_id TEXT NOT NULL,                      -- 原始事件ID
    event_kind TEXT NOT NULL,                    -- 事件类型
    user_id TEXT NOT NULL,                       -- 用户ID
    payload JSONB NOT NULL,                      -- 事件负载
    consumed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    processing_duration_ms INTEGER,              -- 处理耗时（毫秒）
    PRIMARY KEY (consumer_name, event_id)        -- 复合主键实现幂等
);

-- Inbox索引
CREATE INDEX idx_inbox_consumer_time ON consumer_inbox (consumer_name, consumed_at DESC);
CREATE INDEX idx_inbox_user ON consumer_inbox (user_id);

COMMENT ON TABLE consumer_inbox IS 'Consumer Inbox: 已消费事件记录，实现幂等消费';

-- =====================================================
-- 3. Dead Letter Queue表（失败事件）
-- =====================================================

CREATE TABLE IF NOT EXISTS event_dlq (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    consumer_name TEXT NOT NULL,
    event_id TEXT NOT NULL,
    event_kind TEXT NOT NULL,
    payload JSONB NOT NULL,
    error_message TEXT,
    error_stacktrace TEXT,
    retry_count INTEGER NOT NULL DEFAULT 0,
    first_failed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_failed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved BOOLEAN NOT NULL DEFAULT false,
    resolved_at TIMESTAMPTZ
);

CREATE INDEX idx_dlq_consumer ON event_dlq (consumer_name, resolved, last_failed_at DESC);

-- =====================================================
-- 4. TimescaleDB Hypertable设置
-- =====================================================

-- 将时序表转换为Hypertable（如果存在）

-- miner_telemetry分区
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'miner_telemetry') THEN
        PERFORM create_hypertable('miner_telemetry', 'recorded_at', 
            chunk_time_interval => INTERVAL '1 day',
            if_not_exists => TRUE
        );
    END IF;
END $$;

-- network_snapshots分区
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'network_snapshots') THEN
        PERFORM create_hypertable('network_snapshots', 'recorded_at', 
            chunk_time_interval => INTERVAL '1 day',
            if_not_exists => TRUE
        );
    END IF;
END $$;

-- forecast_daily分区
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'forecast_daily') THEN
        PERFORM create_hypertable('forecast_daily', 'forecast_date', 
            chunk_time_interval => INTERVAL '1 day',
            if_not_exists => TRUE
        );
    END IF;
END $$;

-- market_analytics分区
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'market_analytics') THEN
        PERFORM create_hypertable('market_analytics', 'recorded_at', 
            chunk_time_interval => INTERVAL '1 day',
            if_not_exists => TRUE
        );
    END IF;
END $$;

-- =====================================================
-- 5. Row Level Security (RLS) 策略
-- =====================================================

-- 启用RLS（示例：user_miners表）
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'user_miners') THEN
        ALTER TABLE user_miners ENABLE ROW LEVEL SECURITY;
        
        -- 策略：用户只能看到自己的矿机
        DROP POLICY IF EXISTS user_miners_select_policy ON user_miners;
        CREATE POLICY user_miners_select_policy ON user_miners
            FOR SELECT
            USING (
                user_id::text = current_setting('app.user_id', true)
                OR 
                current_setting('app.role', true) = 'admin'
            );
            
        -- 策略：多租户隔离（如果有tenant_id列）
        -- DROP POLICY IF EXISTS user_miners_tenant_policy ON user_miners;
        -- CREATE POLICY user_miners_tenant_policy ON user_miners
        --     FOR ALL
        --     USING (tenant_id = current_setting('app.tenant_id', true));
    END IF;
END $$;

-- event_outbox RLS示例
ALTER TABLE event_outbox ENABLE ROW LEVEL SECURITY;

CREATE POLICY outbox_tenant_policy ON event_outbox
    FOR ALL
    USING (
        tenant_id = current_setting('app.tenant_id', true)
        OR
        current_setting('app.role', true) = 'admin'
    );

-- =====================================================
-- 6. 审计日志增强（如果表存在）
-- =====================================================

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'audit_logs') THEN
        -- 添加tenant_id列（如果不存在）
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'audit_logs' AND column_name = 'tenant_id'
        ) THEN
            ALTER TABLE audit_logs ADD COLUMN tenant_id TEXT DEFAULT 'default';
        END IF;
        
        -- 添加索引
        CREATE INDEX IF NOT EXISTS idx_audit_tenant_time ON audit_logs (tenant_id, created_at DESC);
    END IF;
END $$;

-- =====================================================
-- 7. 性能优化配置
-- =====================================================

-- 设置Outbox自动清理（保留7天）
CREATE OR REPLACE FUNCTION cleanup_old_outbox_events() 
RETURNS void AS $$
BEGIN
    DELETE FROM event_outbox 
    WHERE processed = true 
    AND processed_at < now() - INTERVAL '7 days';
END;
$$ LANGUAGE plpgsql;

-- 设置Inbox自动清理（保留30天）
CREATE OR REPLACE FUNCTION cleanup_old_inbox_events() 
RETURNS void AS $$
BEGIN
    DELETE FROM consumer_inbox 
    WHERE consumed_at < now() - INTERVAL '30 days';
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- 8. 初始化配置
-- =====================================================

-- 插入系统配置
CREATE TABLE IF NOT EXISTS system_config (
    key TEXT PRIMARY KEY,
    value JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO system_config (key, value) VALUES 
    ('cdc_version', '"1.0.0"'::jsonb),
    ('debezium_enabled', 'true'::jsonb),
    ('kafka_enabled', 'true'::jsonb)
ON CONFLICT (key) DO NOTHING;

-- =====================================================
-- 完成
-- =====================================================

SELECT 'CDC Foundation Migration Completed Successfully!' AS status;
