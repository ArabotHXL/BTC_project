-- Migration: Add Multi-Tenant Customer Management Fields
-- Date: 2026-01-27
-- Description: Enable site owners to manage their own customers

-- Add owner_id to hosting_sites (links site to site owner)
ALTER TABLE hosting_sites 
ADD COLUMN IF NOT EXISTS owner_id INTEGER REFERENCES user_access(id);

CREATE INDEX IF NOT EXISTS idx_hosting_sites_owner_id ON hosting_sites(owner_id);

-- Add managed_by_site_id to user_access (links customer to their site)
ALTER TABLE user_access 
ADD COLUMN IF NOT EXISTS managed_by_site_id INTEGER REFERENCES hosting_sites(id);

CREATE INDEX IF NOT EXISTS idx_user_access_managed_by_site_id ON user_access(managed_by_site_id);

-- Add is_active field for soft disable of accounts
ALTER TABLE user_access 
ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE NOT NULL;

-- Comment for documentation
COMMENT ON COLUMN hosting_sites.owner_id IS 'Site owner (mining_site_owner role) who manages this site';
COMMENT ON COLUMN user_access.managed_by_site_id IS 'Site that this customer belongs to (for multi-tenant isolation)';
COMMENT ON COLUMN user_access.is_active IS 'Account active status - false means disabled';
