import logging
from datetime import datetime, timedelta
from skills.spec import SkillSpec
from skills.errors import SkillError, ErrorCode
from skills.utils import build_evidence_ref

logger = logging.getLogger(__name__)


def run(ctx: dict, payload: dict) -> dict:
    """Returns {"data": {...}, "warnings": [...], "evidence_refs": [...]}"""
    warnings = []
    evidence_refs = []

    miner_id = payload["miner_id"]
    issue = payload["issue"]
    site_id = payload.get("site_id") or ctx.get("site_id")
    include_snapshot = payload.get("include_snapshot", True)

    draft = None
    try:
        from services.ai_ticket_draft_service import AITicketDraftService

        svc = AITicketDraftService()
        ticket = svc.generate_ticket_draft(
            site_id=site_id or 0,
            miner_ids=[miner_id],
            alert_type=issue,
            diagnosis_result={},
            site_info=None,
            miner_info=None,
        )
        draft = svc.to_dict(ticket)
        evidence_refs.append(build_evidence_ref("ai_ticket_draft", miner_id, source="ai_ticket_draft_service"))
    except Exception as exc:
        logger.warning(f"AITicketDraftService unavailable, using template fallback: {exc}")
        warnings.append(f"AI draft service unavailable ({exc}); using template fallback")

        issue_tag = issue.lower().replace(" ", "_")[:30]
        draft = {
            "title": f"[{issue}] Miner {miner_id} - Requires Attention",
            "title_zh": f"[{issue}] 矿机 {miner_id} - 需要关注",
            "description": f"Issue reported: {issue}\nAffected miner: {miner_id}\nSite: {site_id}",
            "description_zh": f"报告的问题: {issue}\n受影响矿机: {miner_id}\n站点: {site_id}",
            "priority": "P2",
            "category": "General",
            "tags": ["auto-generated", issue_tag],
            "recommended_parts": [],
            "troubleshooting_steps": [
                "Check miner status and connectivity",
                "Review recent logs",
                "Contact on-site technician if needed",
            ],
            "generated_at": datetime.utcnow().isoformat(),
        }

    snapshot = None
    if include_snapshot:
        try:
            from services.telemetry_service import TelemetryService

            live = TelemetryService.get_live(site_id=site_id, miner_id=miner_id)
            snapshot = live[0] if live else None
            if snapshot:
                evidence_refs.append(build_evidence_ref("telemetry_live", miner_id, source="miner_telemetry_live"))
            else:
                warnings.append("No live telemetry snapshot available for this miner")
        except Exception as exc:
            warnings.append(f"Failed to fetch telemetry snapshot: {exc}")

    result_data = {
        "miner_id": miner_id,
        "site_id": site_id,
        "issue": issue,
        "title": draft.get("title", ""),
        "description": draft.get("description") or draft.get("problem_description", ""),
        "priority": draft.get("priority", "P2"),
        "tags": draft.get("tags", []),
        "recommended_parts": draft.get("recommended_parts") or draft.get("recommended_actions", []),
        "full_draft": draft,
    }
    if include_snapshot:
        result_data["snapshot"] = snapshot

    return {
        "data": result_data,
        "warnings": warnings,
        "evidence_refs": evidence_refs,
    }


spec = SkillSpec(
    id="ticket_draft",
    name="Ticket Draft",
    name_zh="工单草拟",
    desc="Generate a structured maintenance ticket draft for a miner issue, optionally including a telemetry snapshot.",
    desc_zh="为矿机问题生成结构化维护工单草稿，可选包含遥测快照。",
    required_permissions=["skills:run:ticket"],
    input_schema={
        "required": ["miner_id", "issue"],
        "properties": {
            "site_id": {"type": "integer"},
            "miner_id": {"type": "string"},
            "issue": {"type": "string"},
            "include_snapshot": {"type": "boolean", "default": True},
        },
    },
    output_fields=["title", "description", "priority", "tags", "recommended_parts", "snapshot"],
    run_fn=run,
    tags=["ticket", "draft", "P0"],
)
