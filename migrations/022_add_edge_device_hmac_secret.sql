-- Add HMAC secret field to edge_devices for command signing
ALTER TABLE edge_devices ADD COLUMN IF NOT EXISTS hmac_secret VARCHAR(64);

-- Generate default secrets for existing devices (optional, can be done via admin UI)
-- UPDATE edge_devices SET hmac_secret = encode(gen_random_bytes(32), 'hex') WHERE hmac_secret IS NULL;

COMMENT ON COLUMN edge_devices.hmac_secret IS 'HMAC-SHA256 secret for command signature verification';
