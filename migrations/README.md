# Database Migrations

## Overview
This directory contains SQL migration scripts for the BTC Mining Calculator database.

## How it works
1. Migrations are executed automatically during app startup (in app.py)
2. Each migration is idempotent (safe to run multiple times)
3. Migrations are executed in alphabetical order (use numbered prefixes: 001_, 002_, etc.)

## Running migrations manually
```bash
# Execute a specific migration
psql $DATABASE_URL -f migrations/001_add_customer_mining_fields.sql
```

## Current migrations
- **001_add_customer_mining_fields.sql**: Add mining-specific fields to crm_customers table
  - Adds `status` column (VARCHAR(20), default 'active')
  - Adds `electricity_cost` column (DOUBLE PRECISION)
  - Adds `miners_count` column (INTEGER, default 0)
  - Adds `primary_miner_model` column (VARCHAR(100))

## Migration Safety
- All migrations use idempotent patterns (safe to run multiple times)
- Each column check uses `information_schema.columns` to verify existence
- Failed migrations are logged but don't stop the application startup
- Migrations run within transactions for atomicity
