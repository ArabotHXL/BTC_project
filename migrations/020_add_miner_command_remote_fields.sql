-- Migration: Add remote_command_id and audit fields to miner_commands
-- Date: 2026-01-01

-- Add remote_command_id to link MinerCommand to RemoteCommand
ALTER TABLE miner_commands ADD COLUMN IF NOT EXISTS remote_command_id VARCHAR(36) REFERENCES remote_commands(id);

-- Add audit fields
ALTER TABLE miner_commands ADD COLUMN IF NOT EXISTS execution_time_ms INTEGER;
ALTER TABLE miner_commands ADD COLUMN IF NOT EXISTS edge_device_id VARCHAR(50);

-- Create index for remote_command_id lookup
CREATE INDEX IF NOT EXISTS ix_miner_commands_remote_cmd ON miner_commands(remote_command_id);
