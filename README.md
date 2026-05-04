# BTC_Project

Repository for https://replit.com/@hxl1992hao/BitcoinMiningCalculator.

## What This Contains

- Flask/SQLAlchemy HashInsight mining calculator and SaaS surfaces.
- TypeScript microservice APIs for DataHub, miner control, and curtailment logic.
- A HashInsight skills framework for telemetry snapshots, alert triage, RCA, ticket drafting, and curtailment dry runs.

## Quick Checks

```bash
# TypeScript unit tests
npm install
npm test

# Skills framework smoke test
python scripts/smoke_skills.py

# Python syntax check for the skills/API surface
python -m compileall -q skills api/skills_api.py tests/test_skills_api.py test_config.py
```

## Notes

- Copy `.env.example` to `.env` and replace all placeholder secrets before running the app.
- Runtime outputs such as logs, local databases, uploads, and export data are ignored by Git.
