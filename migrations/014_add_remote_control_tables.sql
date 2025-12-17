-- Migration: Add Remote Control Tables
-- Remote Miner Control System - Command Queue and Results
-- Created: 2025-12-16

-- Remote Commands Table
CREATE TABLE IF NOT EXISTS remote_commands (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id INTEGER NOT NULL REFERENCES user_access(id),
    site_id INTEGER NOT NULL REFERENCES hosting_sites(id),
    requested_by_user_id INTEGER NOT NULL REFERENCES user_access(id),
    requested_by_role VARCHAR(50) NOT NULL DEFAULT 'user',
    command_type VARCHAR(50) NOT NULL,
    payload_json JSONB NOT NULL DEFAULT '{}',
    target_scope VARCHAR(20) NOT NULL DEFAULT 'MINER',
    target_ids JSONB NOT NULL DEFAULT '[]',
    status VARCHAR(30) NOT NULL DEFAULT 'PENDING',
    require_approval BOOLEAN NOT NULL DEFAULT FALSE,
    approved_by_user_id INTEGER REFERENCES user_access(id),
    approved_at TIMESTAMP,
    idempotency_key VARCHAR(255),
    expires_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_command_type CHECK (command_type IN ('REBOOT', 'POWER_MODE', 'CHANGE_POOL', 'SET_FREQ', 'THERMAL_POLICY', 'LED')),
    CONSTRAINT chk_target_scope CHECK (target_scope IN ('MINER', 'GROUP', 'SITE')),
    CONSTRAINT chk_status CHECK (status IN ('PENDING', 'PENDING_APPROVAL', 'QUEUED', 'RUNNING', 'SUCCEEDED', 'FAILED', 'CANCELLED', 'EXPIRED'))
);

-- Unique constraint for idempotency
CREATE UNIQUE INDEX IF NOT EXISTS uq_remote_commands_idempotency 
ON remote_commands(tenant_id, requested_by_user_id, idempotency_key) 
WHERE idempotency_key IS NOT NULL;

-- Indexes for command polling and listing
CREATE INDEX IF NOT EXISTS idx_remote_commands_site_status 
ON remote_commands(site_id, status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_remote_commands_tenant 
ON remote_commands(tenant_id, created_at DESC);

-- Remote Command Results Table
CREATE TABLE IF NOT EXISTS remote_command_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    command_id UUID NOT NULL REFERENCES remote_commands(id) ON DELETE CASCADE,
    edge_device_id INTEGER REFERENCES edge_devices(id),
    miner_id VARCHAR(100) NOT NULL,
    started_at TIMESTAMP,
    finished_at TIMESTAMP,
    result_status VARCHAR(30) NOT NULL DEFAULT 'PENDING',
    result_message TEXT,
    metrics_json JSONB DEFAULT '{}',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_result_status CHECK (result_status IN ('PENDING', 'RUNNING', 'SUCCEEDED', 'FAILED', 'SKIPPED'))
);

-- Index for command results lookup
CREATE INDEX IF NOT EXISTS idx_remote_command_results_command 
ON remote_command_results(command_id);

CREATE INDEX IF NOT EXISTS idx_remote_command_results_miner 
ON remote_command_results(miner_id);

-- Comments for documentation
COMMENT ON TABLE remote_commands IS 'Remote miner control command queue';
COMMENT ON TABLE remote_command_results IS 'Per-miner execution results for remote commands';
COMMENT ON COLUMN remote_commands.command_type IS 'REBOOT, POWER_MODE, CHANGE_POOL, SET_FREQ, THERMAL_POLICY, LED';
COMMENT ON COLUMN remote_commands.target_scope IS 'MINER (single/multiple), GROUP (miner group), SITE (all miners in site)';
COMMENT ON COLUMN remote_commands.status IS 'PENDING->QUEUED->RUNNING->SUCCEEDED/FAILED or PENDING_APPROVAL->QUEUED';
