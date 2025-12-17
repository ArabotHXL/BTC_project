-- Migration 011: Add owner-level encryption support
-- Creates hosting_owner_encryption table and adds encryption_scope to hosting_miners

-- Create owner encryption metadata table
CREATE TABLE IF NOT EXISTS hosting_owner_encryption (
    id SERIAL PRIMARY KEY,
    owner_id INTEGER NOT NULL REFERENCES user_access(id),
    site_id INTEGER REFERENCES hosting_sites(id),
    encrypted_data_key TEXT NOT NULL,
    key_salt VARCHAR(64) NOT NULL,
    key_iterations INTEGER DEFAULT 100000 NOT NULL,
    key_algo VARCHAR(32) DEFAULT 'AES-256-GCM' NOT NULL,
    key_version INTEGER DEFAULT 1 NOT NULL,
    encrypted_miners_count INTEGER DEFAULT 0 NOT NULL,
    status VARCHAR(20) DEFAULT 'active' NOT NULL,
    last_rotated_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    UNIQUE(owner_id)
);

-- Add encryption_scope field to hosting_miners
ALTER TABLE hosting_miners ADD COLUMN IF NOT EXISTS encryption_scope VARCHAR(20) DEFAULT 'none' NOT NULL;

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_owner_encryption_owner ON hosting_owner_encryption(owner_id);
CREATE INDEX IF NOT EXISTS idx_owner_encryption_site ON hosting_owner_encryption(site_id);
CREATE INDEX IF NOT EXISTS idx_hosting_miners_encryption_scope ON hosting_miners(encryption_scope);

-- Add comments
COMMENT ON TABLE hosting_owner_encryption IS 'Owner-level encryption metadata for batch miner encryption';
COMMENT ON COLUMN hosting_owner_encryption.encrypted_data_key IS 'Encrypted data key (ODK) using owner passphrase-derived KEK';
COMMENT ON COLUMN hosting_miners.encryption_scope IS 'Encryption scope: none, miner (per-miner passphrase), owner (owner-level batch)';
