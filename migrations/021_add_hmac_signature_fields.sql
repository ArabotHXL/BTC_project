-- Add HMAC signature fields for proper nonce binding and signature verification
-- Supporting improved security for command dispatch and replay detection

ALTER TABLE miner_commands ADD COLUMN IF NOT EXISTS dispatch_nonce VARCHAR(36);
ALTER TABLE miner_commands ADD COLUMN IF NOT EXISTS signature VARCHAR(64);

-- Create index for nonce-based lookups (for replay detection)
CREATE INDEX IF NOT EXISTS ix_miner_commands_nonce ON miner_commands(dispatch_nonce) 
WHERE dispatch_nonce IS NOT NULL;

-- Create index for signature lookups
CREATE INDEX IF NOT EXISTS ix_miner_commands_signature ON miner_commands(signature) 
WHERE signature IS NOT NULL;

-- Document: dispatch_nonce is a UUID generated per command dispatch to the edge
-- Document: signature is the HMAC-SHA256 of (command_id + dispatch_nonce + expires_at + payload_hash)
-- Document: The signing key is derived as HMAC(device.token_hash, "command-signing-v1")
