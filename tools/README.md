# Telemetry Data Generation Tools

## Overview

This directory contains tools for generating historical telemetry data for miners in the HashInsight platform.

## Preferred Tool: `generate_telemetry_24h.py`

**Use this tool for all telemetry data generation.**

### Features

- **NULL-safe baseline handling**: Uses layered fallbacks to prevent NULL reference errors
  - Primary: `miner.actual_hashrate` / `miner.actual_power`
  - Secondary: `miner.miner_model.reference_hashrate` / `miner.miner_model.reference_power`
  - Fallback: Default constants (110.0 TH/s, 3000.0 W)

- **Accurate hourly cadence**: Generates exactly 24 records per miner, aligned to whole hours

- **Status-aware generation**:
  - **Active miners**: ±10% hashrate jitter, ±8% power jitter
  - **Maintenance miners**: Low metrics (5-20% of base), elevated temperatures
  - **Offline miners**: Zero values, NULL temperatures

- **Built-in validation**: Automatically validates data quality after generation
  - Verifies 24 records per miner
  - Checks 1-hour intervals between records
  - Validates metric ranges by status

- **Transactional safety**: Uses database transactions with rollback support

### Usage

```bash
# Run from project root
cd tools
python3 generate_telemetry_24h.py

# Or run from anywhere
python3 tools/generate_telemetry_24h.py
```

### Default Parameters

- **site_id**: 5 (HashPower MegaFarm)
- **batch_size**: 10,000 rows per batch
- **time_range**: 24 hours (aligned to whole hours)

### Validation Results

The tool includes automatic validation that checks:

1. **Record Count**: Each miner should have exactly 24 records
2. **Hourly Cadence**: Records should be exactly 1 hour apart
3. **Metric Ranges**: Values should match expected ranges by status

Example validation output:
```
✅ PASS: 所有矿机都有24条记录
✅ PASS: 所有记录的时间间隔都是1小时
✅ PASS: 各状态指标范围正常
```

## Deprecated Tool: `fast_insert_telemetry.py`

**⚠️ DO NOT USE THIS TOOL DIRECTLY**

This tool has been converted to a compatibility wrapper that delegates to `generate_telemetry_24h.py`. It exists only for backward compatibility with existing scripts or documentation that may reference it.

### Why It Was Deprecated

1. **NULL reference errors**: Direct access to `miner.actual_hashrate` without NULL checks
2. **Limited status handling**: Only processed 'active' miners
3. **No built-in validation**: Required manual SQL queries to verify data quality
4. **Duplicate functionality**: Superseded by the more robust `generate_telemetry_24h.py`

### Migration

If you have scripts that call `fast_insert_telemetry.py`, update them to use `generate_telemetry_24h.py`:

```python
# Old (deprecated)
from tools.fast_insert_telemetry import fast_generate_telemetry
fast_generate_telemetry()

# New (preferred)
from tools.generate_telemetry_24h import generate_telemetry_24h
generate_telemetry_24h()
```

## Implementation Details

### NULL-Safe Baseline Helpers

The preferred tool uses helper functions to safely retrieve baseline values:

```python
def get_base_hashrate(miner):
    """Get base hashrate with layered fallbacks"""
    if miner.actual_hashrate:
        return miner.actual_hashrate
    if hasattr(miner, 'miner_model') and miner.miner_model:
        if hasattr(miner.miner_model, 'reference_hashrate'):
            return miner.miner_model.reference_hashrate
    return DEFAULT_HASHRATE_TH  # 110.0

def get_base_power(miner):
    """Get base power with layered fallbacks"""
    if miner.actual_power:
        return miner.actual_power
    if hasattr(miner, 'miner_model') and miner.miner_model:
        if hasattr(miner.miner_model, 'reference_power'):
            return miner.miner_model.reference_power
    return DEFAULT_POWER_W  # 3000.0
```

### Data Generation Strategy

For each miner and each hourly timestamp:

1. **Determine base values**: Use NULL-safe helpers to get hashrate/power baselines
2. **Apply status-based jitter**:
   - Active: Realistic variations around baseline
   - Maintenance: Reduced performance, elevated temps
   - Offline: Zero values
3. **Create record**: Build dictionary with all telemetry fields
4. **Batch insert**: Group records into batches of 10,000 for efficient insertion

### Database Schema

Records are inserted into the `miner_telemetry` table with these fields:

- `miner_id`: Foreign key to `hosting_miners`
- `hashrate`: Mining hashrate (TH/s)
- `power_consumption`: Power draw (W)
- `temperature`: Operating temperature (°C, NULL for offline)
- `fan_speed`: Fan RPM (NULL for offline)
- `recorded_at`: Timestamp (aligned to whole hour)
- `accepted_shares`: Mining pool accepted shares
- `rejected_shares`: Mining pool rejected shares

## Recent Changes (November 2025)

### Fix Summary

**Problem**: NULL reference errors when generating telemetry for miners without `actual_hashrate` or `actual_power` values.

**Solution**: Implemented 3-step architect plan:

1. ✅ Converted `fast_insert_telemetry.py` to wrapper
2. ✅ Added NULL-safe baseline helpers to `generate_telemetry_24h.py`
3. ✅ Deleted old data, regenerated with fixes, validated results

**Results**:
- 144,000 records generated for 6,000 miners
- All validation checks passed
- Zero NULL reference errors
- Proper fallback to defaults when needed

### Validation SQL Queries

If you need to manually verify data quality:

```sql
-- Check record count per miner
SELECT miner_id, COUNT(*) as record_count
FROM miner_telemetry
WHERE miner_id IN (SELECT id FROM hosting_miners WHERE site_id = 5)
GROUP BY miner_id
HAVING COUNT(*) != 24;

-- Check hourly cadence
WITH telemetry_with_lag AS (
    SELECT 
        miner_id,
        recorded_at,
        LAG(recorded_at) OVER (PARTITION BY miner_id ORDER BY recorded_at) as prev_time,
        EXTRACT(epoch FROM recorded_at - LAG(recorded_at) OVER (PARTITION BY miner_id ORDER BY recorded_at))/3600 as hours_gap
    FROM miner_telemetry
    WHERE miner_id IN (SELECT id FROM hosting_miners WHERE site_id = 5)
)
SELECT * FROM telemetry_with_lag
WHERE hours_gap IS NOT NULL AND ABS(hours_gap - 1.0) > 0.01;

-- Check metric ranges by status
SELECT 
    hm.status,
    COUNT(*) as record_count,
    AVG(mt.hashrate) as avg_hashrate,
    AVG(mt.power_consumption) as avg_power,
    MIN(mt.hashrate) as min_hashrate,
    MAX(mt.hashrate) as max_hashrate
FROM miner_telemetry mt
JOIN hosting_miners hm ON mt.miner_id = hm.id
WHERE hm.site_id = 5
GROUP BY hm.status;
```

## Troubleshooting

### Common Issues

**Issue**: Script fails with "No miners found"
- **Cause**: Invalid `site_id` or no miners exist for that site
- **Solution**: Verify the site exists and has miners in the database

**Issue**: Validation fails with "时间间隔不是1小时"
- **Cause**: Existing data conflicts or timestamp calculation error
- **Solution**: Delete existing telemetry data for the site and regenerate

**Issue**: Database connection errors
- **Cause**: Database not running or incorrect DATABASE_URL
- **Solution**: Check `.env` file and ensure PostgreSQL is running

## Data Initialization: Seed Scripts

### Curtailment Strategies Seed Script

**Location**: `seeds/seed_curtailment_strategies.py`

This script initializes default curtailment strategies for HashPower MegaFarm (site_id=5) to ensure the smart power management feature works correctly in any environment (new deployments, database resets, etc.).

#### Usage

```bash
# Basic usage - creates default strategies for site_id=5
python seeds/seed_curtailment_strategies.py

# Specify a different site
python seeds/seed_curtailment_strategies.py --site-id 3

# Force recreate (deletes existing strategies first)
python seeds/seed_curtailment_strategies.py --force

# Verify existing strategies without creating new ones
python seeds/seed_curtailment_strategies.py --verify-only
```

#### Python API

You can also call the seed function from Python code:

```python
from seeds.seed_curtailment_strategies import seed_megafarm_strategies, verify_strategies

# Create default strategies
with app.app_context():
    count = seed_megafarm_strategies(site_id=5, force=False)
    print(f"Created {count} strategies")
    
    # Verify creation
    verify_strategies(site_id=5)
```

#### What It Creates

The script creates 4 default curtailment strategies:

1. **Performance Priority** - Optimizes for mining performance (70% weight)
2. **Customer Priority** - Protects VIP customers (with uptime protection)
3. **Fair Distribution** - Balanced approach (equal weights)
4. **Custom Rules** - Flexible custom configuration

#### Features

- **Idempotent**: Safe to run multiple times (skips if strategies exist)
- **Force mode**: Can recreate strategies with `--force` flag
- **Validation**: Automatically validates strategy configuration
- **Weight verification**: Ensures weights sum to 1.0

#### Expected Output

```
📝 开始创建 4 个限电策略...
   ✓ Performance Priority - MegaFarm (performance_priority)
   ✓ Customer Priority - MegaFarm (customer_priority)
   ✓ Fair Distribution - MegaFarm (fair_distribution)
   ✓ Custom Rules - MegaFarm (custom)
✅ 成功为site 5 创建 4 个限电策略

🔍 验证结果:
   站点ID: 5
   策略数量: 4
   ✅ 所有策略类型完整
   活跃策略: 4/4
   ✓ 策略 'Performance Priority - MegaFarm' 权重配置正确
   ✓ 策略 'Customer Priority - MegaFarm' 权重配置正确
   ✓ 策略 'Fair Distribution - MegaFarm' 权重配置正确
   ✓ 策略 'Custom Rules - MegaFarm' 权重配置正确
✅ 验证完成
```

#### Troubleshooting

**Issue**: Script reports "已有策略，跳过"
- **Cause**: Strategies already exist for the site
- **Solution**: Use `--force` flag to recreate, or `--verify-only` to check existing strategies

**Issue**: Database connection error
- **Cause**: Database not accessible or incorrect DATABASE_URL
- **Solution**: Check `.env` file and database status

**Issue**: ImportError for models
- **Cause**: Script not run from project root
- **Solution**: Run from project root directory or ensure PYTHONPATH is set correctly

## Support

For questions or issues:
1. Check this README first
2. Review the validation output for specific errors
3. Contact the platform team with error details

---

**Last Updated**: November 15, 2025  
**Maintained By**: HashInsight Platform Team
