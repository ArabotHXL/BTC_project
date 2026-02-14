import logging
from datetime import datetime, timedelta
from skills.spec import SkillSpec
from skills.errors import SkillError, ErrorCode
from skills.utils import build_evidence_ref

logger = logging.getLogger(__name__)


def run(ctx: dict, payload: dict) -> dict:
    """Returns {"data": {...}, "warnings": [...], "evidence_refs": [...]}"""
    from services.telemetry_service import TelemetryService

    warnings = []
    evidence_refs = []

    miner_id = payload["miner_id"]
    site_id = payload.get("site_id") or ctx.get("site_id")
    window_min = payload.get("window_min", 10)

    try:
        live_data = TelemetryService.get_live(site_id=site_id, miner_id=miner_id)
    except Exception as exc:
        raise SkillError(
            code=ErrorCode.UPSTREAM_FAILED,
            message=f"TelemetryService.get_live failed: {exc}",
            http_status=502,
        )

    current = live_data[0] if live_data else None
    if not current:
        warnings.append("No live telemetry data found for this miner")

    window_stats = {}
    anomalies = []

    if site_id:
        end = datetime.utcnow()
        start = end - timedelta(minutes=window_min)
        try:
            history = TelemetryService.get_history(
                site_id=site_id,
                start=start,
                end=end,
                miner_id=miner_id,
                resolution="5min",
            )
        except Exception as exc:
            raise SkillError(
                code=ErrorCode.UPSTREAM_FAILED,
                message=f"TelemetryService.get_history failed: {exc}",
                http_status=502,
            )

        series = history.get("series", [])
        points = []
        for s in series:
            points.extend(s.get("data", []))

        if points:
            hashrates = [p["hashrate_ths"] for p in points if p.get("hashrate_ths") is not None]
            temps = [p["temp_c"] for p in points if p.get("temp_c") is not None]
            powers = [p["power_w"] for p in points if p.get("power_w") is not None]

            def _stats(vals):
                if not vals:
                    return {"min": None, "max": None, "avg": None}
                return {
                    "min": round(min(vals), 2),
                    "max": round(max(vals), 2),
                    "avg": round(sum(vals) / len(vals), 2),
                }

            window_stats = {
                "hashrate_ths": _stats(hashrates),
                "temperature_c": _stats(temps),
                "power_w": _stats(powers),
                "samples": len(points),
                "window_minutes": window_min,
            }

            if temps and max(temps) > 75:
                anomalies.append({
                    "type": "high_temperature",
                    "detail": f"Max temperature {max(temps):.1f}°C exceeds 75°C threshold",
                })

            if hashrates and len(hashrates) >= 2:
                avg_hr = sum(hashrates) / len(hashrates)
                if avg_hr > 0:
                    latest_hr = hashrates[-1]
                    drop_pct = (avg_hr - latest_hr) / avg_hr
                    if drop_pct > 0.20:
                        anomalies.append({
                            "type": "hashrate_drop",
                            "detail": f"Latest hashrate {latest_hr:.2f} TH/s is {drop_pct*100:.1f}% below window avg {avg_hr:.2f} TH/s",
                        })
        else:
            warnings.append("No historical data points in the requested window")
    else:
        warnings.append("site_id not provided; history lookup skipped")

    evidence_refs.append(build_evidence_ref("telemetry_live", miner_id, source="miner_telemetry_live"))
    if site_id:
        evidence_refs.append(build_evidence_ref("telemetry_history", f"{site_id}:{miner_id}", source="telemetry_history_5min"))

    return {
        "data": {
            "miner_id": miner_id,
            "site_id": site_id,
            "current": current,
            "window_stats": window_stats,
            "anomalies": anomalies,
        },
        "warnings": warnings,
        "evidence_refs": evidence_refs,
    }


spec = SkillSpec(
    id="telemetry_snapshot",
    name="Telemetry Snapshot",
    name_zh="遥测快照",
    desc="Fetch live telemetry and recent history for a miner, compute window stats and flag anomalies.",
    desc_zh="获取矿机实时遥测和近期历史数据，计算窗口统计并标记异常。",
    required_permissions=["skills:run:telemetry"],
    input_schema={
        "required": ["miner_id"],
        "properties": {
            "site_id": {"type": "integer"},
            "miner_id": {"type": "string"},
            "window_min": {"type": "integer", "default": 10},
        },
    },
    output_fields=["current", "window_stats", "anomalies"],
    run_fn=run,
    tags=["telemetry", "snapshot", "P0"],
)
