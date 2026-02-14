"""
Skills API - Unified capability plugin system

Endpoints:
  GET  /api/skills              - List available skills (filtered by user permissions)
  GET  /api/skills/<skill_id>   - Get skill spec
  POST /api/skills/<skill_id>/run - Execute a skill

curl examples:
  # List skills (requires auth cookie or API key)
  curl -H "X-API-Key: hsi_dev_key_2025" http://localhost:5000/api/skills
  
  # Run telemetry_snapshot
  curl -X POST -H "X-API-Key: hsi_dev_key_2025" -H "Content-Type: application/json" \
    -d '{"miner_id": "miner-001", "window_min": 10}' \
    http://localhost:5000/api/skills/telemetry_snapshot/run
  
  # Run curtailment_dry_run
  curl -X POST -H "X-API-Key: hsi_dev_key_2025" -H "Content-Type: application/json" \
    -d '{"site_id": 1, "target_kw_reduction": 500, "strategy": "shutdown"}' \
    http://localhost:5000/api/skills/curtailment_dry_run/run
"""

import logging
from flask import Blueprint, jsonify, request, session, g
from rate_limiting import rate_limit_api
from skills.registry import SkillRegistry
from skills.runner import SkillRunner
from skills.errors import SkillError, ErrorCode

logger = logging.getLogger(__name__)

skills_api_bp = Blueprint('skills_api', __name__)

SKILL_MODULE_MAP = {
    'skills:read': 'SKILLS_READ',
    'skills:run:telemetry': 'SKILLS_RUN_TELEMETRY',
    'skills:run:alerts': 'SKILLS_RUN_ALERTS',
    'skills:run:diagnose': 'SKILLS_RUN_DIAGNOSE',
    'skills:run:ticket': 'SKILLS_RUN_TICKET',
    'skills:run:curtailment': 'SKILLS_RUN_CURTAILMENT',
}

ROLE_NAME_MAP = {
    'owner': 'OWNER',
    'admin': 'ADMIN',
    'mining_site_owner': 'MINING_SITE_OWNER',
    'operator': 'OPERATOR',
    'client': 'CLIENT',
    'guest': 'GUEST',
    'developer': 'ADMIN',
}

def _resolve_permissions_from_rbac(role_lower: str) -> list:
    """Derive skill permissions from the central RBAC permission matrix"""
    try:
        from common.rbac import rbac_manager, Module, Role, AccessLevel
        rbac_role_name = ROLE_NAME_MAP.get(role_lower, 'GUEST')
        try:
            role_enum = Role[rbac_role_name]
        except KeyError:
            return []

        permissions = []
        for perm_str, module_name in SKILL_MODULE_MAP.items():
            try:
                module_enum = Module[module_name]
                access = rbac_manager.get_access_level(role_enum, module_enum)
                if access and access != AccessLevel.NONE:
                    permissions.append(perm_str)
            except (KeyError, Exception):
                continue
        return permissions
    except Exception as e:
        logger.warning(f"RBAC permission resolution failed, using fallback: {e}")
        fallback = {
            'owner': ['skills:read', 'skills:run:telemetry', 'skills:run:alerts', 'skills:run:diagnose', 'skills:run:ticket', 'skills:run:curtailment'],
            'admin': ['skills:read', 'skills:run:telemetry', 'skills:run:alerts', 'skills:run:diagnose', 'skills:run:ticket', 'skills:run:curtailment'],
            'mining_site_owner': ['skills:read', 'skills:run:telemetry', 'skills:run:alerts', 'skills:run:diagnose', 'skills:run:ticket', 'skills:run:curtailment'],
            'operator': ['skills:read', 'skills:run:telemetry', 'skills:run:alerts', 'skills:run:diagnose', 'skills:run:ticket'],
            'client': ['skills:read', 'skills:run:telemetry'],
            'guest': [],
        }
        return fallback.get(role_lower, [])

def _get_user_context():
    """Extract user context from session or API key auth"""
    auth = getattr(g, 'auth', None)
    if auth:
        role = getattr(g, 'user_role', 'admin')
        role_lower = role.lower().replace(' ', '_') if role else 'admin'
        permissions = _resolve_permissions_from_rbac(role_lower)
        return {
            'user_id': getattr(g, 'user_email', 'api_key_user'),
            'role': role_lower,
            'site_id': request.args.get('site_id'),
            'tenant_id': None,
            'permissions': permissions,
        }
    
    api_key = request.headers.get('X-API-Key')
    if api_key:
        from api_auth_middleware import APIKeyManager
        key_mgr = APIKeyManager()
        key_info = key_mgr.verify_api_key(api_key)
        if key_info:
            role = key_info.get('role', 'admin')
            role_lower = role.lower().replace(' ', '_') if role else 'admin'
            permissions = _resolve_permissions_from_rbac(role_lower)
            return {
                'user_id': key_info.get('name', 'api_key_user'),
                'role': role_lower,
                'site_id': request.args.get('site_id'),
                'tenant_id': None,
                'permissions': permissions,
            }

    if not session.get('authenticated'):
        raise SkillError(code=ErrorCode.AUTH_REQUIRED, message="Authentication required", http_status=401)
    
    user_id = session.get('user_id')
    role = session.get('role', 'guest')
    site_id = session.get('site_id') or request.args.get('site_id')
    
    role_lower = role.lower().replace(' ', '_') if role else 'guest'
    permissions = _resolve_permissions_from_rbac(role_lower)
    
    return {
        'user_id': user_id,
        'role': role_lower,
        'site_id': site_id,
        'tenant_id': session.get('tenant_id'),
        'permissions': permissions,
    }

@skills_api_bp.route('/api/skills', methods=['GET'])
def list_skills():
    """List available skills filtered by user permissions"""
    try:
        ctx = _get_user_context()
    except SkillError as e:
        return jsonify({"ok": False, "error": {"code": e.code.value, "message": e.message}}), e.http_status
    
    registry = SkillRegistry.instance()
    available = registry.list_for_permissions(ctx['permissions'])
    
    return jsonify({
        "ok": True,
        "skills": [s.to_dict() for s in available],
        "count": len(available)
    })

@skills_api_bp.route('/api/skills/<skill_id>', methods=['GET'])
def get_skill(skill_id):
    """Get skill specification"""
    try:
        ctx = _get_user_context()
    except SkillError as e:
        return jsonify({"ok": False, "error": {"code": e.code.value, "message": e.message}}), e.http_status
    
    registry = SkillRegistry.instance()
    spec = registry.get(skill_id)
    if not spec:
        return jsonify({"ok": False, "error": {"code": "NOT_FOUND", "message": f"Skill '{skill_id}' not found"}}), 404
    
    return jsonify({"ok": True, "skill": spec.to_dict()})

@skills_api_bp.route('/api/skills/<skill_id>/run', methods=['POST'])
@rate_limit_api(max_requests=30, window_minutes=1, feature_name="skills_run")
def run_skill(skill_id):
    """Execute a skill"""
    try:
        ctx = _get_user_context()
    except SkillError as e:
        return jsonify({"ok": False, "error": {"code": e.code.value, "message": e.message}}), e.http_status
    
    payload = request.get_json() or {}
    
    try:
        result = SkillRunner.run(skill_id, payload, ctx)
        return jsonify(result)
    except SkillError as e:
        return jsonify({
            "ok": False,
            "skill_id": skill_id,
            "audit_id": None,
            "received_at": None,
            "data": None,
            "warnings": [],
            "evidence_refs": [],
            "error": {
                "code": e.code.value,
                "message": e.message,
                "details": e.details
            }
        }), e.http_status
    except Exception as e:
        logger.error(f"Unexpected error running skill {skill_id}: {e}", exc_info=True)
        return jsonify({
            "ok": False,
            "skill_id": skill_id,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred"
            }
        }), 500
