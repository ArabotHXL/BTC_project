# Seeds Directory

数据库种子数据脚本目录 / Database Seed Data Scripts

## Overview

This directory contains seed scripts for initializing database with default data. These scripts ensure that the platform can function correctly in any environment (new deployments, database resets, development, staging, production).

## Available Seed Scripts

### 1. Curtailment Strategies (`seed_curtailment_strategies.py`)

Initializes default power curtailment strategies for HashPower MegaFarm.

**Quick Start:**
```bash
python seeds/seed_curtailment_strategies.py
```

**Features:**
- Creates 4 default strategies (Performance Priority, Customer Priority, Fair Distribution, Custom)
- Idempotent (safe to run multiple times)
- Automatic validation after creation
- Force mode to recreate strategies

**See Also:** `tools/README.md` for detailed documentation

## Best Practices

1. **Idempotency**: All seed scripts should be safe to run multiple times
2. **Validation**: Include verification logic to confirm data was created correctly
3. **Logging**: Use clear logging messages to show progress and results
4. **Error Handling**: Gracefully handle errors and provide helpful error messages
5. **Documentation**: Document what data is created and why it's needed

## Adding New Seed Scripts

When creating new seed scripts:

1. Follow the naming convention: `seed_<feature_name>.py`
2. Include a docstring explaining what the script does
3. Implement both CLI and Python API interfaces
4. Add `--force` flag for recreating existing data
5. Add validation function to verify created data
6. Update this README with usage examples

## Integration with Application

To automatically run seed scripts on application startup, you can add initialization calls in `app.py`:

```python
# In app.py, after database initialization
from seeds.seed_curtailment_strategies import seed_megafarm_strategies

with app.app_context():
    seed_megafarm_strategies(force=False)
```

## Support

For questions or issues with seed scripts:
1. Check script's built-in help: `python seeds/script_name.py --help`
2. Review the validation output for specific errors
3. Check `tools/README.md` for detailed documentation
4. Contact the platform team

---

**Last Updated**: November 15, 2025  
**Maintained By**: HashInsight Platform Team
