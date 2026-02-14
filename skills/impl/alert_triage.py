import hashlib
import logging
from datetime import datetime, timedelta
from skills.spec import SkillSpec
from skills.errors import SkillError, ErrorCode
from skills.utils import build_evidence_ref

logger = logging.getLogger(__name__)

SEVERITY_ORDER = {"critical": 1, "P1": 1, "warning": 2, "P2": 2, "info": 3, "P3": 3}


def _severity_rank(sev: str) -> int:
    return SEVERITY_ORDER.get(sev, 99)


def _bucket_key(ts, minutes=5):
    if isinstance(ts, str):
        try:
            ts = datetime.fromisoformat(ts)
        except Exception:
            return "unknown"
    if ts is None:
        return "unknown"
    epoch = int(ts.timestamp())
    bucket = epoch - (epoch % (minutes * 60))
    return str(bucket)


def run(ctx: dict, payload: dict) -> dict:
    """Returns {"data": {...}, "warnings": [...], "evidence_refs": [...]}"""
    warnings = []
    evidence_refs = []

    site_id = payload["site_id"]
    since_min = payload.get("since_min", 30)
    severity_floor = payload.get("severity_floor", "P3")
    floor_rank = _severity_rank(severity_floor)

    cutoff = datetime.utcnow() - timedelta(minutes=since_min)
    clusters = {}

    try:
        from services.alert_engine import MinerAlert
        from db import db

        alerts = MinerAlert.query.filter(
            MinerAlert.site_id == site_id,
            MinerAlert.triggered_at >= cutoff,
        ).order_by(MinerAlert.triggered_at.desc()).all()

        for a in alerts:
            sev = a.level or "info"
            if _severity_rank(sev) > floor_rank:
                continue

            bucket = _bucket_key(a.triggered_at)
            key = f"{a.miner_id}|{a.alert_type}|{bucket}"
            cid = hashlib.md5(key.encode()).hexdigest()[:12]

            if cid not in clusters:
                clusters[cid] = {
                    "cluster_id": cid,
                    "alert_type": a.alert_type,
                    "severity": sev,
                    "count": 0,
                    "affected_miners": [],
                    "top_signals": [],
                    "time_bucket": bucket,
                }

            c = clusters[cid]
            c["count"] += 1
            if a.miner_id and a.miner_id not in c["affected_miners"]:
                c["affected_miners"].append(a.miner_id)
            if _severity_rank(sev) < _severity_rank(c["severity"]):
                c["severity"] = sev
            sig = a.message or a.alert_type
            if sig not in c["top_signals"]:
                c["top_signals"].append(sig)

        evidence_refs.append(build_evidence_ref("alert_table", site_id, source="miner_alerts"))

    except Exception as exc:
        logger.warning(f"MinerAlert query failed, falling back to telemetry scan: {exc}")
        warnings.append(f"Alert table unavailable ({exc}); using live telemetry scan")

        try:
            from services.telemetry_service import TelemetryService

            live = TelemetryService.get_live(site_id=site_id)
            for m in live:
                mid = m.get("miner_id", "unknown")
                temp_max = (m.get("temperature") or {}).get("max")
                hr_val = (m.get("hashrate") or {}).get("value", 0)
                hr_exp = (m.get("hashrate") or {}).get("expected_ths", 0)

                if temp_max and temp_max > 75:
                    sev = "critical" if temp_max > 85 else "warning"
                    if _severity_rank(sev) <= floor_rank:
                        cid = hashlib.md5(f"{mid}|temp|now".encode()).hexdigest()[:12]
                        clusters[cid] = {
                            "cluster_id": cid,
                            "alert_type": "temperature_high",
                            "severity": sev,
                            "count": 1,
                            "affected_miners": [mid],
                            "top_signals": [f"temp_max={temp_max}°C"],
                            "time_bucket": "live",
                        }

                if hr_exp and hr_exp > 0 and hr_val < hr_exp * 0.5:
                    sev = "warning"
                    if _severity_rank(sev) <= floor_rank:
                        cid = hashlib.md5(f"{mid}|hashrate|now".encode()).hexdigest()[:12]
                        clusters[cid] = {
                            "cluster_id": cid,
                            "alert_type": "hashrate_low",
                            "severity": sev,
                            "count": 1,
                            "affected_miners": [mid],
                            "top_signals": [f"hashrate={hr_val} TH/s vs expected={hr_exp} TH/s"],
                            "time_bucket": "live",
                        }

            evidence_refs.append(build_evidence_ref("telemetry_live", site_id, source="miner_telemetry_live"))
        except Exception as inner_exc:
            warnings.append(f"Telemetry fallback also failed: {inner_exc}")

    sorted_clusters = sorted(clusters.values(), key=lambda c: _severity_rank(c["severity"]))

    return {
        "data": {
            "site_id": site_id,
            "since_min": since_min,
            "severity_floor": severity_floor,
            "total_clusters": len(sorted_clusters),
            "clusters": sorted_clusters,
        },
        "warnings": warnings,
        "evidence_refs": evidence_refs,
    }


spec = SkillSpec(
    id="alert_triage",
    name="Alert Triage",
    name_zh="告警聚合分级",
    desc="Aggregate and cluster recent alerts by miner, type, and time bucket, sorted by severity.",
    desc_zh="按矿机、类型和时间窗口聚合近期告警，按严重度排序。",
    required_permissions=["skills:run:alerts"],
    input_schema={
        "required": ["site_id"],
        "properties": {
            "site_id": {"type": "integer"},
            "since_min": {"type": "integer", "default": 30},
            "severity_floor": {"type": "string", "default": "P3"},
        },
    },
    output_fields=["total_clusters", "clusters"],
    run_fn=run,
    tags=["alerts", "triage", "P0"],
)
