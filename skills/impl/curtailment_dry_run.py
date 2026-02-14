import logging
from datetime import datetime, timedelta
from skills.spec import SkillSpec
from skills.errors import SkillError, ErrorCode
from skills.utils import build_evidence_ref

logger = logging.getLogger(__name__)

DRY_RUN_WARNING = "This is a dry-run simulation. No control actions were triggered."


def run(ctx: dict, payload: dict) -> dict:
    """Returns {"data": {...}, "warnings": [...], "evidence_refs": [...]}"""
    warnings = [DRY_RUN_WARNING]
    evidence_refs = []

    site_id = payload["site_id"]
    target_kw = payload.get("target_kw_reduction")
    curtailment_pct = payload.get("curtailment_pct")
    strategy = payload.get("strategy", "shutdown")
    step_size = payload.get("step_size", 50)

    if target_kw is None and curtailment_pct is None:
        warnings.append("Neither target_kw_reduction nor curtailment_pct provided; using curtailment_pct=10 as default")
        curtailment_pct = 10.0

    if target_kw is None and curtailment_pct is not None:
        try:
            from services.telemetry_service import TelemetryService
            summary = TelemetryService.get_site_summary(site_id)
            total_kw = (summary.get("power", {}).get("total_kw") or 0)
            if total_kw > 0:
                target_kw = round(total_kw * curtailment_pct / 100.0, 2)
            else:
                target_kw = 100.0
                warnings.append("Could not determine site total power; defaulting target_kw_reduction=100")
        except Exception as exc:
            target_kw = 100.0
            warnings.append(f"Failed to compute target from percentage: {exc}; defaulting target_kw_reduction=100")

    strategy_id = 1
    try:
        from models import CurtailmentStrategy
        strat = CurtailmentStrategy.query.filter(
            CurtailmentStrategy.strategy_name.ilike(f"%{strategy}%")
        ).first()
        if strat:
            strategy_id = strat.id
    except Exception:
        pass

    result = None
    try:
        from intelligence.curtailment_engine import calculate_curtailment_plan

        result = calculate_curtailment_plan(
            site_id=site_id,
            strategy_id=strategy_id,
            target_power_reduction_kw=target_kw,
        )
        evidence_refs.append(build_evidence_ref("curtailment_engine", site_id, source="intelligence.curtailment_engine"))
    except Exception as exc:
        logger.warning(f"calculate_curtailment_plan unavailable, using simplified calc: {exc}")
        warnings.append(f"Curtailment engine unavailable ({exc}); using simplified calculation")

        try:
            from services.telemetry_service import TelemetryService

            live = TelemetryService.get_live(site_id=site_id)
            miners_with_eff = []
            for m in live:
                power_w = (m.get("power") or {}).get("value") or 0
                hr = (m.get("hashrate") or {}).get("value") or 0
                eff = (power_w / hr) if hr > 0 else float("inf")
                miners_with_eff.append({
                    "miner_id": m.get("miner_id"),
                    "power_kw": round(power_w / 1000, 3),
                    "hashrate_ths": hr,
                    "efficiency_w_per_th": round(eff, 2),
                })

            miners_with_eff.sort(key=lambda x: -x["efficiency_w_per_th"])

            selected = []
            accum_kw = 0.0
            for mn in miners_with_eff:
                if accum_kw >= target_kw:
                    break
                selected.append(mn)
                accum_kw += mn["power_kw"]

            result = {
                "selected_miners": selected,
                "total_power_reduction_kw": round(accum_kw, 2),
                "total_hashrate_loss_ths": round(sum(m["hashrate_ths"] for m in selected), 2),
                "simplified": True,
            }
            evidence_refs.append(build_evidence_ref("telemetry_live", site_id, source="miner_telemetry_live"))
        except Exception as inner_exc:
            raise SkillError(
                code=ErrorCode.UPSTREAM_FAILED,
                message=f"Both curtailment engine and telemetry fallback failed: {inner_exc}",
                http_status=502,
            )

    selected_miners = result.get("selected_miners", [])
    steps = []
    for i in range(0, len(selected_miners), step_size):
        batch = selected_miners[i : i + step_size]
        batch_kw = 0.0
        batch_hash = 0.0
        miner_ids = []
        for m in batch:
            if isinstance(m, dict):
                miner_ids.append(m.get("miner_id") or m.get("serial_number", "unknown"))
                batch_kw += m.get("power_kw", 0) or (m.get("actual_power", 0) / 1000)
                batch_hash += m.get("hashrate_ths", 0) or (m.get("actual_hashrate", 0))
            else:
                miner_ids.append(str(m))

        steps.append({
            "step": len(steps) + 1,
            "miners": miner_ids,
            "miner_count": len(miner_ids),
            "estimated_kw": round(batch_kw, 2),
            "estimated_hash_loss_ths": round(batch_hash, 2),
        })

    return {
        "data": {
            "site_id": site_id,
            "dry_run": True,
            "strategy": strategy,
            "target_kw_reduction": target_kw,
            "curtailment_pct": curtailment_pct,
            "total_power_reduction_kw": result.get("total_power_reduction_kw") or result.get("calculated_power_reduction_kw", 0),
            "total_hashrate_loss_ths": result.get("total_hashrate_loss_ths", 0),
            "total_miners_affected": len(selected_miners),
            "steps": steps,
            "economic_impact": result.get("economic_impact"),
        },
        "warnings": warnings,
        "evidence_refs": evidence_refs,
    }


spec = SkillSpec(
    id="curtailment_dry_run",
    name="Curtailment Dry Run",
    name_zh="限电预演",
    desc="Simulate a curtailment plan without executing any control actions. Read-only, never writes to DB.",
    desc_zh="模拟限电计划但不执行任何控制操作。只读，不写数据库。",
    required_permissions=["skills:run:curtailment"],
    input_schema={
        "required": ["site_id"],
        "properties": {
            "site_id": {"type": "integer"},
            "target_kw_reduction": {"type": "number"},
            "curtailment_pct": {"type": "number"},
            "strategy": {"type": "string", "default": "shutdown"},
            "step_size": {"type": "integer", "default": 50},
            "constraints": {"type": "object"},
        },
    },
    output_fields=["dry_run", "steps", "total_power_reduction_kw", "total_miners_affected"],
    run_fn=run,
    tags=["curtailment", "dry-run", "simulation", "P0"],
)
