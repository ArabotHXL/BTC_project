-- Migration 009: Add E2EE (End-to-End Encryption) fields to hosting_miners
-- Supports Plan A (credentials E2EE) and Plan B (full connection E2EE)
-- Created: 2024-12-02

-- Plan A: Encrypted credentials only (username/password/pool_password)
-- IP/Port remain plaintext for Edge Collector connectivity
ALTER TABLE hosting_miners ADD COLUMN IF NOT EXISTS encrypted_credentials JSONB DEFAULT NULL;

-- Plan B: Full E2EE for entire connection (IP/Port + credentials)
-- When enabled, ip_address/port are ignored; all connection info comes from encrypted blob
ALTER TABLE hosting_miners ADD COLUMN IF NOT EXISTS encrypted_connection_full JSONB DEFAULT NULL;

-- Mode flag: false = Plan A (default), true = Plan B
ALTER TABLE hosting_miners ADD COLUMN IF NOT EXISTS use_full_e2ee BOOLEAN DEFAULT FALSE NOT NULL;

-- CGMiner API port (typically 4028, stored separately for convenience)
ALTER TABLE hosting_miners ADD COLUMN IF NOT EXISTS api_port INTEGER DEFAULT 4028;

-- Add comment for documentation
COMMENT ON COLUMN hosting_miners.encrypted_credentials IS 'Plan A: AES-256-GCM encrypted credentials JSON block {ciphertext, iv, salt, algo, version}';
COMMENT ON COLUMN hosting_miners.encrypted_connection_full IS 'Plan B: Full E2EE connection blob including IP/Port and credentials';
COMMENT ON COLUMN hosting_miners.use_full_e2ee IS 'Mode flag: false=Plan A (plaintext IP + encrypted creds), true=Plan B (fully encrypted)';
COMMENT ON COLUMN hosting_miners.api_port IS 'CGMiner API port, typically 4028';

-- Index for querying E2EE mode miners
CREATE INDEX IF NOT EXISTS idx_hosting_miners_e2ee_mode ON hosting_miners(use_full_e2ee) WHERE use_full_e2ee = TRUE;
