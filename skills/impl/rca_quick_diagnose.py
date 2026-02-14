import logging
from datetime import datetime, timedelta
from skills.spec import SkillSpec
from skills.errors import SkillError, ErrorCode
from skills.utils import build_evidence_ref

logger = logging.getLogger(__name__)

RULE_TO_CATEGORY = {
    "overheat_crit": "Thermal",
    "overheat_warn": "Thermal",
    "temp_anomaly": "Thermal",
    "offline": "Hardware",
    "fan_zero": "Hardware",
    "boards_dead": "Hardware",
    "boards_degrading": "Hardware",
    "hashrate_zero": "Hardware",
    "hashrate_degradation": "Network",
    "efficiency_degradation": "Power",
    "fleet_outlier": "Network",
    "pool_reject": "Pool",
}

CATEGORY_CHECKS = {
    "Thermal": [
        "Check ambient temperature and cooling system",
        "Inspect fans and heat sinks for dust buildup",
        "Verify airflow direction and obstructions",
    ],
    "Hardware": [
        "Run board-level diagnostics",
        "Check power supply unit connections",
        "Inspect hash boards for visible damage",
        "Verify firmware version is up to date",
    ],
    "Network": [
        "Check network connectivity and latency to pool",
        "Verify DNS resolution and firewall rules",
        "Test with an alternative pool endpoint",
    ],
    "Pool": [
        "Verify pool credentials and worker name",
        "Check pool-side reject rate dashboard",
        "Try switching to a backup pool",
    ],
    "Power": [
        "Check input voltage stability",
        "Inspect PDU load distribution",
        "Verify power mode configuration",
    ],
    "Unknown": [
        "Collect full diagnostic logs from the miner",
        "Perform manual on-site inspection",
        "Contact manufacturer support if under warranty",
    ],
}


def run(ctx: dict, payload: dict) -> dict:
    """Returns {"data": {...}, "warnings": [...], "evidence_refs": [...]}"""
    from services.telemetry_service import TelemetryService

    warnings = []
    evidence_refs = []

    miner_id = payload["miner_id"]
    site_id = payload.get("site_id") or ctx.get("site_id")
    incident_hint = payload.get("incident_hint", "")

    try:
        live_data = TelemetryService.get_live(site_id=site_id, miner_id=miner_id)
    except Exception as exc:
        raise SkillError(
            code=ErrorCode.UPSTREAM_FAILED,
            message=f"TelemetryService.get_live failed: {exc}",
            http_status=502,
        )

    miner = live_data[0] if live_data else None
    if not miner:
        return {
            "data": {
                "miner_id": miner_id,
                "root_cause": "Unknown",
                "confidence": 0.05,
                "evidence": {"note": "No telemetry data available for this miner"},
                "next_checks": CATEGORY_CHECKS["Unknown"],
            },
            "warnings": ["No live telemetry data found; diagnosis inconclusive"],
            "evidence_refs": [],
        }

    hashrate_val = (miner.get("hashrate") or {}).get("value", 0)
    hashrate_exp = (miner.get("hashrate") or {}).get("expected_ths", 0)
    temp_max = (miner.get("temperature") or {}).get("max")
    temp_avg = (miner.get("temperature") or {}).get("avg")
    is_online = miner.get("online", False)
    boards_healthy = (miner.get("hardware") or {}).get("boards_healthy")
    boards_total = (miner.get("hardware") or {}).get("boards_total")
    hw_errors = (miner.get("hardware") or {}).get("errors", 0)

    hashrate_ratio = (hashrate_val / hashrate_exp) if hashrate_exp and hashrate_exp > 0 else (1.0 if is_online else 0.0)
    boards_ratio = (boards_healthy / boards_total) if boards_total and boards_total > 0 else 1.0

    fan_speed_min = None
    fan_speeds = miner.get("fan_speeds")
    if fan_speeds and isinstance(fan_speeds, (list, tuple)):
        numeric = [int(s) for s in fan_speeds if s is not None]
        if numeric:
            fan_speed_min = min(numeric)

    features = {
        "temp_max": temp_max or 0,
        "temp_avg": temp_avg or 0,
        "hashrate_ratio": round(hashrate_ratio, 4),
        "is_online": is_online,
        "boards_ratio": round(boards_ratio, 4),
        "fan_speed_min": fan_speed_min if fan_speed_min is not None else 1,
        "hardware_errors": hw_errors or 0,
    }

    triggered_rules = []
    try:
        from services.health_rules import HealthRulesEngine

        engine = HealthRulesEngine()
        hard = engine.evaluate_hard_rules(features)
        soft = engine.evaluate_soft_rules(features, {})
        triggered_rules = hard + soft
    except Exception as exc:
        logger.warning(f"HealthRulesEngine unavailable, using inline checks: {exc}")
        warnings.append("HealthRulesEngine unavailable; using simplified rule set")

        if features["temp_max"] >= 85:
            triggered_rules.append({"code": "overheat_crit", "severity": "P0", "evidence": {"temp_max": features["temp_max"]}})
        elif features["temp_max"] >= 75:
            triggered_rules.append({"code": "overheat_warn", "severity": "P1", "evidence": {"temp_max": features["temp_max"]}})
        if not is_online:
            triggered_rules.append({"code": "offline", "severity": "P0", "evidence": {"is_online": False}})
        if is_online and hashrate_ratio <= 0.01:
            triggered_rules.append({"code": "hashrate_zero", "severity": "P1", "evidence": {"hashrate_ratio": hashrate_ratio}})
        if boards_ratio <= 0.5:
            triggered_rules.append({"code": "boards_dead", "severity": "P1", "evidence": {"boards_ratio": boards_ratio}})
        if fan_speed_min == 0 and is_online:
            triggered_rules.append({"code": "fan_zero", "severity": "P1", "evidence": {"fan_speed_min": 0}})

    if not triggered_rules:
        return {
            "data": {
                "miner_id": miner_id,
                "root_cause": "Unknown",
                "confidence": 0.1,
                "evidence": {"features": features, "incident_hint": incident_hint},
                "triggered_rules": [],
                "next_checks": CATEGORY_CHECKS["Unknown"],
            },
            "warnings": ["No rules triggered; manual inspection recommended"],
            "evidence_refs": [build_evidence_ref("telemetry_live", miner_id, source="miner_telemetry_live")],
        }

    category_scores = {}
    for rule in triggered_rules:
        cat = RULE_TO_CATEGORY.get(rule["code"], "Unknown")
        sev = rule.get("severity", "P3")
        weight = {"P0": 1.0, "P1": 0.8, "P2": 0.5, "P3": 0.3}.get(sev, 0.2)
        category_scores[cat] = category_scores.get(cat, 0) + weight

    top_category = max(category_scores, key=category_scores.get)
    max_score = category_scores[top_category]
    confidence = min(1.0, round(max_score / 1.5, 2))

    evidence_refs.append(build_evidence_ref("telemetry_live", miner_id, source="miner_telemetry_live"))
    evidence_refs.append(build_evidence_ref("health_rules", miner_id, source="health_rules_engine"))

    return {
        "data": {
            "miner_id": miner_id,
            "root_cause": top_category,
            "confidence": confidence,
            "category_scores": category_scores,
            "triggered_rules": triggered_rules,
            "evidence": {"features": features, "incident_hint": incident_hint},
            "next_checks": CATEGORY_CHECKS.get(top_category, CATEGORY_CHECKS["Unknown"]),
        },
        "warnings": warnings,
        "evidence_refs": evidence_refs,
    }


spec = SkillSpec(
    id="rca_quick_diagnose",
    name="Quick Root Cause Analysis",
    name_zh="快速根因诊断",
    desc="Run health rules against live telemetry to identify the most likely root cause category and suggest next checks.",
    desc_zh="对实时遥测运行健康规则，识别最可能的根因类别并建议下一步检查。",
    required_permissions=["skills:run:diagnose"],
    input_schema={
        "required": ["miner_id"],
        "properties": {
            "site_id": {"type": "integer"},
            "miner_id": {"type": "string"},
            "incident_hint": {"type": "string"},
        },
    },
    output_fields=["root_cause", "confidence", "triggered_rules", "evidence", "next_checks"],
    run_fn=run,
    tags=["rca", "diagnose", "P0"],
)
