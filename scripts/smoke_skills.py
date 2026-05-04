"""Smoke checks for the HashInsight skills framework.

This intentionally avoids live services and database calls. It verifies that
the skill registry can load every P0 skill and that the schema/default logic
still works for a representative skill.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from skills.loader import load_all_skills
from skills.registry import SkillRegistry


EXPECTED_SKILLS = {
    "telemetry_snapshot",
    "alert_triage",
    "rca_quick_diagnose",
    "ticket_draft",
    "curtailment_dry_run",
}


def main() -> int:
    loaded = load_all_skills()
    registry = SkillRegistry.instance()
    loaded_ids = {spec.id for spec in registry.list_all()}

    missing = EXPECTED_SKILLS - loaded_ids
    extra = loaded_ids - EXPECTED_SKILLS
    if loaded != len(EXPECTED_SKILLS) or missing:
        raise SystemExit(
            f"Skills smoke failed: loaded={loaded}, missing={sorted(missing)}, extra={sorted(extra)}"
        )

    telemetry = registry.get("telemetry_snapshot")
    if telemetry is None:
        raise SystemExit("telemetry_snapshot was not registered")

    payload = telemetry.apply_defaults({"miner_id": "miner-001"})
    errors = telemetry.validate_input(payload)
    if errors:
        raise SystemExit(f"telemetry_snapshot validation failed: {errors}")
    if payload.get("window_min") != 10:
        raise SystemExit("telemetry_snapshot default window_min was not applied")

    print("SKILLS_SMOKE_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
