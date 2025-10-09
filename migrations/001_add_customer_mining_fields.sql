-- Migration: Add mining-specific fields to crm_customers table
-- Date: 2025-10-09
-- Description: Add status, electricity_cost, miners_count, primary_miner_model columns

-- Check and add status column (idempotent)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'crm_customers' AND column_name = 'status'
    ) THEN
        ALTER TABLE crm_customers 
        ADD COLUMN status VARCHAR(20) DEFAULT 'active' NOT NULL;
        RAISE NOTICE 'Added column: status';
    END IF;
END $$;

-- Check and add electricity_cost column (idempotent)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'crm_customers' AND column_name = 'electricity_cost'
    ) THEN
        ALTER TABLE crm_customers 
        ADD COLUMN electricity_cost DOUBLE PRECISION;
        RAISE NOTICE 'Added column: electricity_cost';
    END IF;
END $$;

-- Check and add miners_count column (idempotent)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'crm_customers' AND column_name = 'miners_count'
    ) THEN
        ALTER TABLE crm_customers 
        ADD COLUMN miners_count INTEGER DEFAULT 0 NOT NULL;
        RAISE NOTICE 'Added column: miners_count';
    END IF;
END $$;

-- Check and add primary_miner_model column (idempotent)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'crm_customers' AND column_name = 'primary_miner_model'
    ) THEN
        ALTER TABLE crm_customers 
        ADD COLUMN primary_miner_model VARCHAR(100);
        RAISE NOTICE 'Added column: primary_miner_model';
    END IF;
END $$;

-- Verify migration success
SELECT column_name, data_type, is_nullable, column_default 
FROM information_schema.columns 
WHERE table_name = 'crm_customers' 
AND column_name IN ('status', 'electricity_cost', 'miners_count', 'primary_miner_model')
ORDER BY column_name;
