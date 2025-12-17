-- Migration 012: Device Envelope Encryption (X25519 + Sealed Box)
-- Implements device-key based E2EE for miner credentials
-- Created: 2025-01

-- ============================================================================
-- Edge Collector Devices Table
-- Stores device public keys and status for X25519 sealed box encryption
-- ============================================================================
CREATE TABLE IF NOT EXISTS edge_devices (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES user_access(id),
    site_id INTEGER REFERENCES hosting_sites(id),
    device_name VARCHAR(200) NOT NULL,
    device_token VARCHAR(512) UNIQUE,
    public_key TEXT NOT NULL,
    key_version INTEGER DEFAULT 1 NOT NULL,
    status VARCHAR(20) DEFAULT 'ACTIVE' NOT NULL CHECK (status IN ('ACTIVE', 'REVOKED', 'PENDING')),
    last_seen_at TIMESTAMP,
    revoked_at TIMESTAMP,
    revoked_by INTEGER REFERENCES user_access(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_edge_devices_tenant ON edge_devices(tenant_id);
CREATE INDEX IF NOT EXISTS idx_edge_devices_site ON edge_devices(site_id);
CREATE INDEX IF NOT EXISTS idx_edge_devices_status ON edge_devices(status);
CREATE INDEX IF NOT EXISTS idx_edge_devices_token ON edge_devices(device_token);

COMMENT ON TABLE edge_devices IS 'Edge Collector devices with X25519 public keys for sealed box encryption';
COMMENT ON COLUMN edge_devices.public_key IS 'Base64-encoded X25519 public key';
COMMENT ON COLUMN edge_devices.key_version IS 'Key version for rotation support';
COMMENT ON COLUMN edge_devices.status IS 'Device status: ACTIVE, REVOKED, PENDING';

-- ============================================================================
-- Miner Secrets Table
-- Stores encrypted credential packages (sealed box wrapped DEK + AES-GCM payload)
-- ============================================================================
CREATE TABLE IF NOT EXISTS miner_secrets (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES user_access(id),
    device_id INTEGER NOT NULL REFERENCES edge_devices(id),
    miner_id INTEGER NOT NULL REFERENCES hosting_miners(id),
    encrypted_payload TEXT NOT NULL,
    wrapped_dek TEXT NOT NULL,
    nonce VARCHAR(64) NOT NULL,
    aad JSONB NOT NULL,
    counter INTEGER DEFAULT 1 NOT NULL,
    schema_version INTEGER DEFAULT 1 NOT NULL,
    key_version INTEGER DEFAULT 1 NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    UNIQUE(miner_id, device_id)
);

CREATE INDEX IF NOT EXISTS idx_miner_secrets_tenant ON miner_secrets(tenant_id);
CREATE INDEX IF NOT EXISTS idx_miner_secrets_device ON miner_secrets(device_id);
CREATE INDEX IF NOT EXISTS idx_miner_secrets_miner ON miner_secrets(miner_id);

COMMENT ON TABLE miner_secrets IS 'Encrypted miner credentials using device envelope encryption';
COMMENT ON COLUMN miner_secrets.encrypted_payload IS 'AES-256-GCM encrypted credentials JSON (base64)';
COMMENT ON COLUMN miner_secrets.wrapped_dek IS 'X25519 sealed box wrapped DEK (base64)';
COMMENT ON COLUMN miner_secrets.nonce IS 'AES-GCM nonce/IV (base64)';
COMMENT ON COLUMN miner_secrets.aad IS 'Additional Authenticated Data: {tenant_id, device_id, miner_id, schema_version, key_version, counter}';
COMMENT ON COLUMN miner_secrets.counter IS 'Anti-replay counter, must be strictly increasing';

-- ============================================================================
-- Miner Capability Levels
-- Level 1: Discovery only (no credentials needed)
-- Level 2: Read-only telemetry (may work without credentials on some miners)
-- Level 3: Full control (requires credentials + E2EE)
-- ============================================================================
ALTER TABLE hosting_miners ADD COLUMN IF NOT EXISTS capability_level INTEGER DEFAULT 1 NOT NULL;
ALTER TABLE hosting_miners ADD COLUMN IF NOT EXISTS bound_device_id INTEGER REFERENCES edge_devices(id);

CREATE INDEX IF NOT EXISTS idx_hosting_miners_capability ON hosting_miners(capability_level);
CREATE INDEX IF NOT EXISTS idx_hosting_miners_bound_device ON hosting_miners(bound_device_id);

COMMENT ON COLUMN hosting_miners.capability_level IS 'Capability level: 1=discovery, 2=telemetry, 3=control';
COMMENT ON COLUMN hosting_miners.bound_device_id IS 'Edge device bound to this miner for E2EE';

-- ============================================================================
-- Device Event Audit Log
-- Track all device-related security events
-- ============================================================================
CREATE TABLE IF NOT EXISTS device_audit_events (
    id SERIAL PRIMARY KEY,
    event_type VARCHAR(50) NOT NULL,
    tenant_id INTEGER REFERENCES user_access(id),
    device_id INTEGER REFERENCES edge_devices(id),
    miner_id INTEGER REFERENCES hosting_miners(id),
    actor_id INTEGER REFERENCES user_access(id),
    actor_type VARCHAR(20) DEFAULT 'user',
    ip_address VARCHAR(45),
    user_agent TEXT,
    event_data JSONB,
    result VARCHAR(20) DEFAULT 'success',
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_device_audit_tenant ON device_audit_events(tenant_id);
CREATE INDEX IF NOT EXISTS idx_device_audit_device ON device_audit_events(device_id);
CREATE INDEX IF NOT EXISTS idx_device_audit_type ON device_audit_events(event_type);
CREATE INDEX IF NOT EXISTS idx_device_audit_created ON device_audit_events(created_at);

COMMENT ON TABLE device_audit_events IS 'Security audit log for device operations';
COMMENT ON COLUMN device_audit_events.event_type IS 'Event types: DEVICE_REGISTER, SECRET_UPLOAD, SECRET_FETCH, DEVICE_REVOKE, COUNTER_REJECT, etc.';

-- ============================================================================
-- IP Range Scan Jobs
-- Track network scan operations
-- ============================================================================
CREATE TABLE IF NOT EXISTS ip_scan_jobs (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES user_access(id),
    site_id INTEGER REFERENCES hosting_sites(id),
    device_id INTEGER REFERENCES edge_devices(id),
    ip_range_start VARCHAR(45) NOT NULL,
    ip_range_end VARCHAR(45) NOT NULL,
    scan_type VARCHAR(30) DEFAULT 'DISCOVERY',
    status VARCHAR(20) DEFAULT 'PENDING',
    total_ips INTEGER DEFAULT 0,
    scanned_ips INTEGER DEFAULT 0,
    discovered_miners INTEGER DEFAULT 0,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_scan_jobs_tenant ON ip_scan_jobs(tenant_id);
CREATE INDEX IF NOT EXISTS idx_scan_jobs_status ON ip_scan_jobs(status);

COMMENT ON TABLE ip_scan_jobs IS 'Network IP range scan jobs for miner discovery';

-- ============================================================================
-- Discovered Miners (from network scan)
-- Temporary storage before user confirms import
-- ============================================================================
CREATE TABLE IF NOT EXISTS discovered_miners (
    id SERIAL PRIMARY KEY,
    scan_job_id INTEGER NOT NULL REFERENCES ip_scan_jobs(id) ON DELETE CASCADE,
    tenant_id INTEGER NOT NULL REFERENCES user_access(id),
    ip_address VARCHAR(45) NOT NULL,
    api_port INTEGER DEFAULT 4028,
    detected_model VARCHAR(100),
    detected_firmware VARCHAR(100),
    detected_hashrate_ghs FLOAT,
    mac_address VARCHAR(20),
    hostname VARCHAR(200),
    is_imported BOOLEAN DEFAULT FALSE,
    imported_miner_id INTEGER REFERENCES hosting_miners(id),
    raw_response JSONB,
    discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_discovered_job ON discovered_miners(scan_job_id);
CREATE INDEX IF NOT EXISTS idx_discovered_imported ON discovered_miners(is_imported);

COMMENT ON TABLE discovered_miners IS 'Miners discovered during network scan, pending user confirmation';
