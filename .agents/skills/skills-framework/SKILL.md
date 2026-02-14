# Skills Framework

Unified capability plugin system for HashInsight Enterprise AI closed-loop automation and human operators.

## Architecture

```
skills/
├── __init__.py          # Package exports
├── errors.py            # ErrorCode enum (8 codes) + SkillError exception
├── utils.py             # redact_payload, build_evidence_ref, iso_now
├── spec.py              # SkillSpec dataclass (schema validation, defaults)
├── registry.py          # SkillRegistry singleton (register, get, list)
├── runner.py            # SkillRunner (auth → validate → audit → execute → respond)
├── loader.py            # Auto-loads all skills at startup
└── impl/
    ├── telemetry_snapshot.py    # P0: Live telemetry + window stats + anomaly flags
    ├── alert_triage.py          # P0: Cluster alerts by miner/type/time bucket
    ├── rca_quick_diagnose.py    # P0: 5-category root cause analysis
    ├── ticket_draft.py          # P0: AI-generated or template ticket draft
    └── curtailment_dry_run.py   # P0: Read-only power reduction simulation
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/skills` | List available skills (filtered by role) |
| GET | `/api/skills/<id>` | Get skill specification |
| POST | `/api/skills/<id>/run` | Execute a skill |

Auth: Session cookie or `X-API-Key` header.

## Unified Response Format

```json
{
  "ok": true,
  "skill_id": "telemetry_snapshot",
  "audit_id": "12235",
  "received_at": "2026-02-14T21:49:28Z",
  "elapsed_ms": 64,
  "data": { ... },
  "warnings": [],
  "evidence_refs": [{"type": "telemetry_live", "id": "miner-001", "source": "miner_telemetry_live"}],
  "error": null
}
```

## RBAC Permissions

| Role | Telemetry | Alerts | Diagnose | Ticket | Curtailment |
|------|-----------|--------|----------|--------|-------------|
| Owner/Admin/Site Owner | FULL | FULL | FULL | FULL | FULL |
| Operator | FULL | FULL | FULL | FULL | - |
| Client | FULL | - | - | - | - |
| Guest | - | - | - | - | - |

## Adding a New Skill

1. Create `skills/impl/my_skill.py`:
```python
from skills.spec import SkillSpec
from skills.utils import build_evidence_ref

def run(ctx: dict, payload: dict) -> dict:
    data = {"result": "..."}
    return {"data": data, "warnings": [], "evidence_refs": []}

spec = SkillSpec(
    id="my_skill",
    name="My Skill",
    name_zh="我的技能",
    desc="Description",
    desc_zh="描述",
    required_permissions=["skills:run:my_skill"],
    input_schema={"required": ["field1"], "properties": {"field1": {"type": "string"}}},
    output_fields=["result"],
    run_fn=run,
    tags=["custom"]
)
```

2. Add module path to `skills/loader.py` `skill_modules` list.
3. Add RBAC entry in `common/rbac.py` (Module enum + PERMISSION_MATRIX).

## Feature Flags

- `SKILLS_ENABLED` (env var, default: true) - Global kill switch
- `SKILLS_ALLOWLIST` (config, default: None) - Restrict to specific skill IDs

## curl Examples

```bash
# List skills
curl -H "X-API-Key: hsi_dev_key_2025" http://localhost:5000/api/skills

# Run telemetry snapshot
curl -X POST -H "X-API-Key: hsi_dev_key_2025" -H "Content-Type: application/json" \
  -d '{"miner_id": "miner-001", "window_min": 10}' \
  http://localhost:5000/api/skills/telemetry_snapshot/run

# Run ticket draft
curl -X POST -H "X-API-Key: hsi_dev_key_2025" -H "Content-Type: application/json" \
  -d '{"miner_id": "miner-001", "issue": "hashrate_drop"}' \
  http://localhost:5000/api/skills/ticket_draft/run

# Run curtailment dry run
curl -X POST -H "X-API-Key: hsi_dev_key_2025" -H "Content-Type: application/json" \
  -d '{"site_id": 1, "target_kw_reduction": 500}' \
  http://localhost:5000/api/skills/curtailment_dry_run/run
```
