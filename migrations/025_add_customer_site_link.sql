-- Migration: Add site and user account links to CRM Customer
-- Date: 2026-01-27

-- Add site_id to link customer to hosting site
ALTER TABLE crm_customers ADD COLUMN IF NOT EXISTS site_id INTEGER REFERENCES hosting_sites(id);

-- Add user_account_id to link customer to login account
ALTER TABLE crm_customers ADD COLUMN IF NOT EXISTS user_account_id INTEGER REFERENCES user_access(id);

-- Create indexes for faster lookups
CREATE INDEX IF NOT EXISTS idx_crm_customers_site_id ON crm_customers(site_id);
CREATE INDEX IF NOT EXISTS idx_crm_customers_user_account_id ON crm_customers(user_account_id);
