-- Migration: Add IP encryption mode to hosting_miners
-- Date: December 2025
-- Description: Add support for IP hiding strategies (方案1/2/3)

-- Add ip_encryption_mode column (1=MASK, 2=SERVER_ENCRYPT, 3=E2EE)
ALTER TABLE hosting_miners 
ADD COLUMN IF NOT EXISTS ip_encryption_mode INTEGER DEFAULT 1;

-- Add encrypted_ip column for server-side encrypted IPs (Strategy 2)
ALTER TABLE hosting_miners 
ADD COLUMN IF NOT EXISTS encrypted_ip TEXT;

-- Add comment for documentation
COMMENT ON COLUMN hosting_miners.ip_encryption_mode IS 'IP encryption mode: 1=UI Mask, 2=Server Encrypt, 3=E2EE';
COMMENT ON COLUMN hosting_miners.encrypted_ip IS 'Server-encrypted IP (when ip_encryption_mode=2)';

-- Create index for encryption mode filtering
CREATE INDEX IF NOT EXISTS idx_hosting_miners_ip_encryption_mode 
ON hosting_miners(ip_encryption_mode);
