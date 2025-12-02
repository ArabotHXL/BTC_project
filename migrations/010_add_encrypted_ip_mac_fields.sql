-- Migration 010: Add encrypted IP and MAC address fields for E2EE
-- These fields store AES-256-GCM encrypted values for sensitive network identifiers

ALTER TABLE hosting_miners ADD COLUMN IF NOT EXISTS encrypted_ip TEXT;
ALTER TABLE hosting_miners ADD COLUMN IF NOT EXISTS encrypted_mac TEXT;

-- Add comment for documentation
COMMENT ON COLUMN hosting_miners.encrypted_ip IS 'E2EE encrypted IP address (AES-256-GCM with PBKDF2)';
COMMENT ON COLUMN hosting_miners.encrypted_mac IS 'E2EE encrypted MAC address (AES-256-GCM with PBKDF2)';
