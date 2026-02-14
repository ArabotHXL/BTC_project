import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional

from skills.registry import SkillRegistry
from skills.spec import SkillSpec
from skills.errors import SkillError, ErrorCode
from skills.utils import redact_payload, iso_now

logger = logging.getLogger(__name__)


class SkillRunner:

    @staticmethod
    def run(skill_id: str, payload: dict, ctx: dict) -> dict:
        received_at = iso_now()
        audit_id = None

        registry = SkillRegistry.instance()
        spec = registry.get(skill_id)

        if not spec:
            raise SkillError(
                code=ErrorCode.NOT_FOUND,
                message=f"Skill '{skill_id}' not found",
                http_status=404
            )

        from flask import current_app
        skills_enabled = current_app.config.get('SKILLS_ENABLED', True)
        if not skills_enabled:
            raise SkillError(
                code=ErrorCode.FEATURE_DISABLED,
                message="Skills system is disabled",
                http_status=503
            )

        allowlist = current_app.config.get('SKILLS_ALLOWLIST', None)
        if allowlist and skill_id not in allowlist:
            raise SkillError(
                code=ErrorCode.FEATURE_DISABLED,
                message=f"Skill '{skill_id}' is not enabled",
                http_status=503
            )

        user_permissions = ctx.get('permissions', [])
        has_perm = any(p in user_permissions for p in spec.required_permissions)
        if not has_perm:
            raise SkillError(
                code=ErrorCode.FORBIDDEN,
                message="Insufficient permissions for this skill",
                details={"required": spec.required_permissions},
                http_status=403
            )

        payload_with_defaults = spec.apply_defaults(payload)
        validation_errors = spec.validate_input(payload_with_defaults)
        if validation_errors:
            raise SkillError(
                code=ErrorCode.INVALID_INPUT,
                message="Input validation failed",
                details={"errors": validation_errors},
                http_status=400
            )

        start_time = time.time()
        try:
            result = spec.run_fn(ctx, payload_with_defaults)
            elapsed_ms = int((time.time() - start_time) * 1000)

            data = result.get('data', {})
            warnings = result.get('warnings', [])
            evidence_refs = result.get('evidence_refs', [])

            audit_id = SkillRunner._write_audit(
                skill_id=skill_id,
                ctx=ctx,
                payload=payload_with_defaults,
                status='success',
                elapsed_ms=elapsed_ms,
                evidence_refs=evidence_refs
            )

            return {
                "ok": True,
                "skill_id": skill_id,
                "audit_id": audit_id,
                "received_at": received_at,
                "elapsed_ms": elapsed_ms,
                "data": data,
                "warnings": warnings,
                "evidence_refs": evidence_refs,
                "error": None
            }

        except SkillError:
            raise
        except Exception as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Skill '{skill_id}' execution failed: {e}", exc_info=True)

            audit_id = SkillRunner._write_audit(
                skill_id=skill_id,
                ctx=ctx,
                payload=payload_with_defaults,
                status='failed',
                elapsed_ms=elapsed_ms,
                error_code='INTERNAL_ERROR',
                error_message=str(e)
            )

            raise SkillError(
                code=ErrorCode.UPSTREAM_FAILED,
                message=f"Skill execution failed: {str(e)}",
                http_status=500
            )

    @staticmethod
    def _write_audit(skill_id, ctx, payload, status, elapsed_ms=None,
                     error_code=None, error_message=None, evidence_refs=None):
        try:
            from api.control_plane_api import log_audit_event

            redacted_input = redact_payload(payload)

            targets = []
            if payload.get('miner_id'):
                targets.append(payload['miner_id'])
            if payload.get('miner_ids'):
                targets.extend(payload['miner_ids'])

            audit_payload = {
                'skill_id': skill_id,
                'actor_role': ctx.get('role'),
                'tenant_id': ctx.get('tenant_id'),
                'targets': targets[:20],
                'input_redacted': redacted_input,
                'status': status,
                'elapsed_ms': elapsed_ms,
            }
            if error_code:
                audit_payload['error_code'] = error_code
            if error_message:
                audit_payload['error_message'] = error_message[:500]
            if evidence_refs:
                audit_payload['evidence_ref_count'] = len(evidence_refs)

            event = log_audit_event(
                event_type='skill_run',
                actor_type='user',
                actor_id=str(ctx.get('user_id', 'unknown')),
                site_id=ctx.get('site_id'),
                ref_type='skill',
                ref_id=skill_id,
                payload=audit_payload
            )

            return str(event.id) if event else None
        except Exception as e:
            logger.error(f"Failed to write skill audit: {e}")
            return None
