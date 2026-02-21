import logging
import uuid
from functools import wraps

from flask import g, session, request, jsonify
from sqlalchemy import false as sa_false

from db import db
from models_hi import HiOrg, HiTenant, HiAuditLog, HiTenantMembership

logger = logging.getLogger(__name__)

ROLE_TO_HI_ROLE = {
    'owner': 'operator_admin',
    'admin': 'operator_admin',
    'mining_site_owner': 'operator_ops',
    'operator': 'operator_ops',
    'client': 'tenant_viewer',
}

OPERATOR_ROLES = ('operator_admin', 'operator_ops')
TENANT_ROLES = ('tenant_admin', 'tenant_viewer')


def init_hi_tenant(app):
    @app.before_request
    def _populate_hi_context():
        g.hi_org_id = None
        g.hi_tenant_id = None
        g.hi_role = None

        if not session.get('authenticated'):
            return

        user_id = session.get('user_id')
        role = session.get('role', '')
        hi_role = ROLE_TO_HI_ROLE.get(role, 'guest')
        g.hi_role = hi_role

        if hi_role in OPERATOR_ROLES:
            try:
                org = HiOrg.query.filter_by(org_type='self').first()
                if org:
                    g.hi_org_id = org.id
                else:
                    logger.debug("No default org (org_type='self') found for operator user_id=%s", user_id)
            except Exception as e:
                logger.error("Error finding default org for operator: %s", e)
            g.hi_tenant_id = None

        elif hi_role in TENANT_ROLES:
            tenant_id = session.get('hi_tenant_id')
            if tenant_id:
                g.hi_tenant_id = tenant_id
                try:
                    tenant = db.session.get(HiTenant, tenant_id)
                    if tenant:
                        g.hi_org_id = tenant.org_id
                except Exception as e:
                    logger.error("Error looking up tenant %s: %s", tenant_id, e)
            else:
                try:
                    membership = HiTenantMembership.query.filter_by(
                        user_id=user_id
                    ).order_by(
                        HiTenantMembership.is_default.desc(),
                        HiTenantMembership.tenant_id.asc()
                    ).first()

                    if membership:
                        tenant = db.session.get(HiTenant, membership.tenant_id)
                        if tenant and tenant.status == 'active':
                            g.hi_tenant_id = tenant.id
                            g.hi_org_id = tenant.org_id
                            if membership.member_role in TENANT_ROLES:
                                g.hi_role = membership.member_role
                            session['hi_tenant_id'] = tenant.id
                            logger.debug(
                                "Membership-based tenant binding: user_id=%s -> tenant_id=%s, role=%s",
                                user_id, tenant.id, g.hi_role
                            )
                        else:
                            logger.debug("Membership tenant_id=%s not active or not found", membership.tenant_id)
                    else:
                        logger.debug(
                            "No hi_tenant_membership found for user_id=%s; hi_tenant_id remains None",
                            user_id
                        )
                except Exception as e:
                    logger.error("Error looking up membership for user_id=%s: %s", user_id, e)


def hi_require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('authenticated') or not getattr(g, 'hi_role', None):
            return jsonify({'error': 'Authentication required', 'code': 'HI_AUTH_REQUIRED'}), 401
        if getattr(g, 'hi_role', None) in TENANT_ROLES and getattr(g, 'hi_tenant_id', None) is None:
            return jsonify({'error': 'Tenant binding required', 'code': 'HI_TENANT_BINDING_REQUIRED'}), 403
        return f(*args, **kwargs)
    return decorated


def hi_require_operator(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('authenticated') or not getattr(g, 'hi_role', None):
            return jsonify({'error': 'Authentication required', 'code': 'HI_AUTH_REQUIRED'}), 401
        if getattr(g, 'hi_role', None) not in OPERATOR_ROLES:
            return jsonify({'error': 'Operator access required', 'code': 'HI_OPERATOR_REQUIRED'}), 403
        return f(*args, **kwargs)
    return decorated


def hi_require_tenant_or_operator(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('authenticated') or not getattr(g, 'hi_role', None):
            return jsonify({'error': 'Authentication required', 'code': 'HI_AUTH_REQUIRED'}), 401
        allowed = OPERATOR_ROLES + TENANT_ROLES
        if getattr(g, 'hi_role', None) not in allowed:
            return jsonify({'error': 'Tenant or operator access required', 'code': 'HI_ACCESS_DENIED'}), 403
        if getattr(g, 'hi_role', None) in TENANT_ROLES and getattr(g, 'hi_tenant_id', None) is None:
            return jsonify({'error': 'Tenant binding required', 'code': 'HI_TENANT_BINDING_REQUIRED'}), 403
        return f(*args, **kwargs)
    return decorated


def hi_filter_by_tenant(query, model, tenant_id_column='tenant_id', org_id_column='org_id'):
    hi_role = getattr(g, 'hi_role', None)

    if hi_role in OPERATOR_ROLES:
        org_id = getattr(g, 'hi_org_id', None)
        if org_id and hasattr(model, org_id_column):
            query = query.filter(getattr(model, org_id_column) == org_id)
        return query

    if hi_role in TENANT_ROLES:
        tenant_id = getattr(g, 'hi_tenant_id', None)
        if tenant_id and hasattr(model, tenant_id_column):
            query = query.filter(getattr(model, tenant_id_column) == tenant_id)
            return query
        return query.filter(sa_false())

    return query.filter(sa_false())


def hi_check_tenant_id_override(requested_tenant_id):
    hi_role = getattr(g, 'hi_role', None)
    if hi_role in TENANT_ROLES:
        my_tenant_id = getattr(g, 'hi_tenant_id', None)
        if requested_tenant_id is not None and int(requested_tenant_id) != my_tenant_id:
            return False
    elif hi_role in OPERATOR_ROLES:
        org_id = getattr(g, 'hi_org_id', None)
        if requested_tenant_id is not None and org_id:
            tenant = db.session.get(HiTenant, int(requested_tenant_id))
            if not tenant or tenant.org_id != org_id:
                return False
    return True


def hi_get_org_tenant_ids():
    org_id = getattr(g, 'hi_org_id', None)
    if not org_id:
        return []
    return [t.id for t in HiTenant.query.filter_by(org_id=org_id).all()]


def hi_write_audit(action_type, entity_type, entity_id, detail_json=None, tenant_id=None):
    try:
        entry = HiAuditLog(
            org_id=getattr(g, 'hi_org_id', None),
            tenant_id=tenant_id if tenant_id is not None else getattr(g, 'hi_tenant_id', None),
            actor_user_id=session.get('user_id'),
            action_type=action_type,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id is not None else None,
            request_id=str(uuid.uuid4()),
            detail_json=detail_json,
        )
        db.session.add(entry)
        db.session.commit()
        logger.debug("Audit log written: %s %s:%s", action_type, entity_type, entity_id)
        return entry
    except Exception as e:
        db.session.rollback()
        logger.error("Failed to write audit log: %s", e)
        return None
