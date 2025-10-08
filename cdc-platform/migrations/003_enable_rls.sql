-- ============================================================================
-- HashInsight CDC Platform - Row-Level Security (RLS) Migration
-- 启用行级安全策略，实现多租户数据隔离
-- 
-- Author: HashInsight Team
-- Version: 1.0.0
-- Date: 2025-10-08
-- ============================================================================

-- 1. 启用RLS扩展（如果需要）
-- PostgreSQL 9.5+ 内置RLS支持

-- 2. 为event_outbox表启用RLS
ALTER TABLE event_outbox ENABLE ROW LEVEL SECURITY;

-- 3. 创建RLS策略 - 租户隔离
-- 用户只能看到自己租户的事件
CREATE POLICY tenant_isolation_select ON event_outbox
    FOR SELECT
    USING (
        tenant_id = COALESCE(
            current_setting('app.tenant_id', true),
            'default'
        )
    );

-- 4. 创建RLS策略 - 插入限制
-- 用户只能插入到自己的租户
CREATE POLICY tenant_isolation_insert ON event_outbox
    FOR INSERT
    WITH CHECK (
        tenant_id = COALESCE(
            current_setting('app.tenant_id', true),
            'default'
        )
    );

-- 5. 创建RLS策略 - 更新限制
CREATE POLICY tenant_isolation_update ON event_outbox
    FOR UPDATE
    USING (
        tenant_id = COALESCE(
            current_setting('app.tenant_id', true),
            'default'
        )
    );

-- 6. 创建RLS策略 - 删除限制
CREATE POLICY tenant_isolation_delete ON event_outbox
    FOR DELETE
    USING (
        tenant_id = COALESCE(
            current_setting('app.tenant_id', true),
            'default'
        )
    );

-- 7. 为consumer_inbox表启用RLS
ALTER TABLE consumer_inbox ENABLE ROW LEVEL SECURITY;

-- 8. consumer_inbox策略（消费者级别隔离）
CREATE POLICY consumer_isolation ON consumer_inbox
    FOR ALL
    USING (
        consumer_name = current_setting('app.consumer_name', true)
        OR current_setting('app.is_admin', true) = 'true'
    );

-- 9. 为event_dlq表启用RLS
ALTER TABLE event_dlq ENABLE ROW LEVEL SECURITY;

-- 10. event_dlq策略（全局访问，但记录审计日志）
CREATE POLICY dlq_access ON event_dlq
    FOR ALL
    USING (true);

-- 11. 创建辅助函数 - 设置租户上下文
CREATE OR REPLACE FUNCTION set_tenant_context(p_tenant_id TEXT)
RETURNS VOID AS $$
BEGIN
    PERFORM set_config('app.tenant_id', p_tenant_id, false);
END;
$$ LANGUAGE plpgsql;

-- 12. 创建辅助函数 - 设置消费者上下文
CREATE OR REPLACE FUNCTION set_consumer_context(p_consumer_name TEXT)
RETURNS VOID AS $$
BEGIN
    PERFORM set_config('app.consumer_name', p_consumer_name, false);
END;
$$ LANGUAGE plpgsql;

-- 13. 创建辅助函数 - 设置管理员模式
CREATE OR REPLACE FUNCTION set_admin_mode(p_is_admin BOOLEAN)
RETURNS VOID AS $$
BEGIN
    PERFORM set_config('app.is_admin', p_is_admin::TEXT, false);
END;
$$ LANGUAGE plpgsql;

-- 14. 授予执行权限
GRANT EXECUTE ON FUNCTION set_tenant_context(TEXT) TO PUBLIC;
GRANT EXECUTE ON FUNCTION set_consumer_context(TEXT) TO PUBLIC;
GRANT EXECUTE ON FUNCTION set_admin_mode(BOOLEAN) TO PUBLIC;

-- ============================================================================
-- 使用示例：
-- 
-- 1. 在应用中设置租户上下文：
--    SELECT set_tenant_context('tenant_123');
-- 
-- 2. 在消费者中设置消费者上下文：
--    SELECT set_consumer_context('portfolio-consumer');
-- 
-- 3. 管理员模式（绕过RLS）：
--    SELECT set_admin_mode(true);
-- 
-- 4. 测试RLS策略：
--    SELECT set_tenant_context('tenant_a');
--    SELECT * FROM event_outbox;  -- 只返回tenant_a的数据
-- ============================================================================

-- 15. 添加审计日志表（可选）
CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    user_id TEXT,
    action TEXT NOT NULL,
    table_name TEXT NOT NULL,
    record_id TEXT,
    old_data JSONB,
    new_data JSONB,
    ip_address TEXT,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 16. 创建审计触发器函数
CREATE OR REPLACE FUNCTION audit_trigger_func()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO audit_logs (
        tenant_id,
        action,
        table_name,
        record_id,
        old_data,
        new_data
    ) VALUES (
        COALESCE(current_setting('app.tenant_id', true), 'default'),
        TG_OP,
        TG_TABLE_NAME,
        CASE 
            WHEN TG_OP = 'DELETE' THEN OLD.id::TEXT
            ELSE NEW.id::TEXT
        END,
        CASE 
            WHEN TG_OP = 'DELETE' OR TG_OP = 'UPDATE' THEN row_to_json(OLD)
            ELSE NULL
        END,
        CASE 
            WHEN TG_OP = 'INSERT' OR TG_OP = 'UPDATE' THEN row_to_json(NEW)
            ELSE NULL
        END
    );
    
    RETURN CASE 
        WHEN TG_OP = 'DELETE' THEN OLD
        ELSE NEW
    END;
END;
$$ LANGUAGE plpgsql;

-- 17. 为event_outbox添加审计触发器
CREATE TRIGGER event_outbox_audit
    AFTER INSERT OR UPDATE OR DELETE ON event_outbox
    FOR EACH ROW
    EXECUTE FUNCTION audit_trigger_func();

-- ============================================================================
-- 回滚脚本（如需禁用RLS）：
-- 
-- DROP TRIGGER IF EXISTS event_outbox_audit ON event_outbox;
-- DROP POLICY IF EXISTS tenant_isolation_select ON event_outbox;
-- DROP POLICY IF EXISTS tenant_isolation_insert ON event_outbox;
-- DROP POLICY IF EXISTS tenant_isolation_update ON event_outbox;
-- DROP POLICY IF EXISTS tenant_isolation_delete ON event_outbox;
-- DROP POLICY IF EXISTS consumer_isolation ON consumer_inbox;
-- DROP POLICY IF EXISTS dlq_access ON event_dlq;
-- ALTER TABLE event_outbox DISABLE ROW LEVEL SECURITY;
-- ALTER TABLE consumer_inbox DISABLE ROW LEVEL SECURITY;
-- ALTER TABLE event_dlq DISABLE ROW LEVEL SECURITY;
-- DROP FUNCTION IF EXISTS set_tenant_context(TEXT);
-- DROP FUNCTION IF EXISTS set_consumer_context(TEXT);
-- DROP FUNCTION IF EXISTS set_admin_mode(BOOLEAN);
-- DROP FUNCTION IF EXISTS audit_trigger_func();
-- ============================================================================
