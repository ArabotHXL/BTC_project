import logging
from datetime import datetime

from flask import Blueprint, request, jsonify, session, g, redirect, render_template, Response
from db import db
from models_hi import (HiOrg, HiTenant, HiGroup, HiAuditLog,
    HiCurtailmentPlan, HiCurtailmentAction, HiCurtailmentResult, HiCommandQueue,
    HiTariff, HiContract, HiUsageRecord, HiInvoice, HiTenantMembership)
from models import UserAccess, HostingSite, Miner
from common.hi_tenant import (hi_require_auth, hi_require_operator,
    hi_require_tenant_or_operator, hi_filter_by_tenant, hi_write_audit,
    hi_check_tenant_id_override, hi_get_org_tenant_ids,
    OPERATOR_ROLES, TENANT_ROLES)
from services.curtailment_engine import CurtailmentEngine
from services.usage_service import UsageService
from services.billing_service import BillingService

logger = logging.getLogger(__name__)

hi_api_bp = Blueprint('hi_api_bp', __name__, url_prefix='/api/hi')


def _error(code, message, status=400):
    return jsonify({'error': {'code': code, 'message': message}}), status


def _parse_date(s):
    if not s:
        return None
    if isinstance(s, datetime):
        return s
    for fmt in ('%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M:%S.%f', '%Y-%m-%d'):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return datetime.fromisoformat(s)


def _get_scoped_plan_or_404(plan_id):
    plan = HiCurtailmentPlan.query.get(plan_id)
    if not plan:
        return None, _error('NOT_FOUND', 'Plan not found', 404)
    hi_role = getattr(g, 'hi_role', None)
    if hi_role in OPERATOR_ROLES:
        org_id = getattr(g, 'hi_org_id', None)
        if org_id and plan.org_id != org_id:
            return None, _error('ACCESS_DENIED', 'Plan not in your org', 403)
    elif hi_role in TENANT_ROLES:
        my_tid = getattr(g, 'hi_tenant_id', None)
        if plan.tenant_id != my_tid:
            return None, _error('ACCESS_DENIED', 'Plan not accessible', 403)
    else:
        return None, _error('ACCESS_DENIED', 'Access denied', 403)
    return plan, None


def _get_scoped_invoice_or_404(invoice_id):
    invoice = HiInvoice.query.get(invoice_id)
    if not invoice:
        return None, _error('NOT_FOUND', 'Invoice not found', 404)
    hi_role = getattr(g, 'hi_role', None)
    if hi_role in OPERATOR_ROLES:
        org_id = getattr(g, 'hi_org_id', None)
        if org_id and invoice.org_id != org_id:
            return None, _error('ACCESS_DENIED', 'Invoice not in your org', 403)
    elif hi_role in TENANT_ROLES:
        if invoice.tenant_id != getattr(g, 'hi_tenant_id', None):
            return None, _error('ACCESS_DENIED', 'You do not have access to this invoice', 403)
    else:
        return None, _error('ACCESS_DENIED', 'Access denied', 403)
    return invoice, None


def _tenant_id_for_request(body_key='tenant_id'):
    hi_role = getattr(g, 'hi_role', None)
    if hi_role in TENANT_ROLES:
        return getattr(g, 'hi_tenant_id', None)
    data = request.get_json(silent=True) or {}
    return data.get(body_key)


@hi_api_bp.route('/portal')
def portal_page():
    if 'user_id' not in session:
        return redirect('/login')
    return render_template('portal.html')


@hi_api_bp.route('/me', methods=['GET'])
@hi_require_auth
def me():
    return jsonify({
        'hi_org_id': getattr(g, 'hi_org_id', None),
        'hi_tenant_id': getattr(g, 'hi_tenant_id', None),
        'hi_role': getattr(g, 'hi_role', None),
        'user_id': session.get('user_id')
    })


@hi_api_bp.route('/tenants', methods=['GET'])
@hi_require_auth
def list_tenants():
    try:
        hi_role = getattr(g, 'hi_role', None)
        if hi_role in OPERATOR_ROLES:
            org_id = getattr(g, 'hi_org_id', None)
            q = HiTenant.query
            if org_id:
                q = q.filter_by(org_id=org_id)
            tenants = q.all()
        elif hi_role in TENANT_ROLES:
            tid = getattr(g, 'hi_tenant_id', None)
            tenants = [db.session.get(HiTenant, tid)] if tid else []
            tenants = [t for t in tenants if t]
        else:
            tenants = []
        return jsonify([t.to_dict() for t in tenants])
    except Exception as e:
        logger.error(f"list_tenants error: {e}")
        return _error('TENANT_LIST_FAILED', str(e), 500)


@hi_api_bp.route('/tenants', methods=['POST'])
@hi_require_operator
def create_tenant():
    try:
        data = request.get_json(force=True)
        tenant = HiTenant(
            org_id=getattr(g, 'hi_org_id', None),
            name=data.get('name', 'New Tenant'),
            tenant_type=data.get('tenant_type', 'client'),
            status='active'
        )
        db.session.add(tenant)
        db.session.commit()
        hi_write_audit('TENANT_CREATE', 'tenant', tenant.id, {'name': tenant.name})
        return jsonify(tenant.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        logger.error(f"create_tenant error: {e}")
        return _error('TENANT_CREATE_FAILED', str(e), 500)


@hi_api_bp.route('/miners', methods=['GET'])
@hi_require_auth
def list_miners():
    try:
        q = Miner.query
        site_id = request.args.get('site_id')
        req_tenant_id = request.args.get('tenant_id')
        if site_id:
            q = q.filter_by(site_id=str(site_id))

        hi_role = getattr(g, 'hi_role', None)
        if hi_role in TENANT_ROLES:
            if req_tenant_id is not None and int(req_tenant_id) != getattr(g, 'hi_tenant_id', None):
                return _error('ACCESS_DENIED', 'Cannot query other tenant miners', 403)
            q = q.filter(Miner.hi_tenant_id == getattr(g, 'hi_tenant_id', None))
        elif hi_role in OPERATOR_ROLES:
            org_tenant_ids = hi_get_org_tenant_ids()
            if org_tenant_ids:
                q = q.filter(Miner.hi_tenant_id.in_(org_tenant_ids))
            else:
                q = q.filter(Miner.hi_tenant_id == -1)
            if req_tenant_id:
                if not hi_check_tenant_id_override(req_tenant_id):
                    return _error('ACCESS_DENIED', 'Tenant not in your org', 403)
                q = q.filter(Miner.hi_tenant_id == int(req_tenant_id))
        else:
            return jsonify([])

        miners = q.all()
        hi_write_audit('MINER_LIST', 'miner', None)
        return jsonify([{
            'id': m.id, 'miner_id': m.miner_id, 'site_id': m.site_id,
            'model': m.model, 'ip': m.ip, 'status': m.status,
            'hi_tenant_id': getattr(m, 'hi_tenant_id', None),
            'created_at': m.created_at.isoformat() if m.created_at else None
        } for m in miners])
    except Exception as e:
        logger.error(f"list_miners error: {e}")
        return _error('MINER_LIST_FAILED', str(e), 500)


@hi_api_bp.route('/groups', methods=['GET'])
@hi_require_auth
def list_groups():
    try:
        q = HiGroup.query
        site_id = request.args.get('site_id')
        req_tenant_id = request.args.get('tenant_id')
        if site_id:
            q = q.filter_by(site_id=int(site_id))

        hi_role = getattr(g, 'hi_role', None)
        if hi_role in TENANT_ROLES:
            if req_tenant_id is not None and int(req_tenant_id) != getattr(g, 'hi_tenant_id', None):
                return _error('ACCESS_DENIED', 'Cannot query other tenant groups', 403)
            q = q.filter(HiGroup.tenant_id == getattr(g, 'hi_tenant_id', None))
        elif hi_role in OPERATOR_ROLES:
            org_tenant_ids = hi_get_org_tenant_ids()
            if org_tenant_ids:
                q = q.filter(HiGroup.tenant_id.in_(org_tenant_ids))
            else:
                q = q.filter(HiGroup.tenant_id == -1)
            if req_tenant_id:
                if not hi_check_tenant_id_override(req_tenant_id):
                    return _error('ACCESS_DENIED', 'Tenant not in your org', 403)
                q = q.filter(HiGroup.tenant_id == int(req_tenant_id))
        else:
            return jsonify([])

        groups = q.all()
        hi_write_audit('GROUP_LIST', 'group', None)
        return jsonify([grp.to_dict() for grp in groups])
    except Exception as e:
        logger.error(f"list_groups error: {e}")
        return _error('GROUP_LIST_FAILED', str(e), 500)


@hi_api_bp.route('/groups', methods=['POST'])
@hi_require_tenant_or_operator
def create_group():
    try:
        data = request.get_json(force=True)
        hi_role = getattr(g, 'hi_role', None)
        if hi_role in TENANT_ROLES:
            if hi_role != 'tenant_admin':
                return _error('PERMISSION_DENIED', 'Only tenant_admin can create groups', 403)
            t_id = getattr(g, 'hi_tenant_id', None)
        else:
            t_id = data.get('tenant_id')
            if t_id and not hi_check_tenant_id_override(t_id):
                return _error('ACCESS_DENIED', 'Tenant not in your org', 403)

        group = HiGroup(
            site_id=int(data['site_id']),
            tenant_id=int(t_id) if t_id else None,
            name=data.get('name', 'New Group'),
            selector_json=data.get('selector_json'),
            priority=int(data.get('priority', 100))
        )
        db.session.add(group)
        db.session.commit()
        hi_write_audit('GROUP_CREATE', 'group', group.id, {'name': group.name})
        return jsonify(group.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        logger.error(f"create_group error: {e}")
        return _error('GROUP_CREATE_FAILED', str(e), 500)


@hi_api_bp.route('/audit', methods=['GET'])
@hi_require_auth
def list_audit():
    try:
        q = HiAuditLog.query
        q = hi_filter_by_tenant(q, HiAuditLog)
        limit = request.args.get('limit', 50, type=int)
        logs = q.order_by(HiAuditLog.created_at.desc()).limit(min(limit, 200)).all()
        return jsonify([l.to_dict() for l in logs])
    except Exception as e:
        logger.error(f"list_audit error: {e}")
        return _error('AUDIT_LIST_FAILED', str(e), 500)


@hi_api_bp.route('/sites', methods=['GET'])
@hi_require_auth
def list_sites():
    try:
        hi_role = getattr(g, 'hi_role', None)
        if hi_role in OPERATOR_ROLES:
            org_id = getattr(g, 'hi_org_id', None)
            if org_id:
                sites = HostingSite.query.filter_by(hi_org_id=org_id).all()
            else:
                sites = []
        elif hi_role in TENANT_ROLES:
            my_tid = getattr(g, 'hi_tenant_id', None)
            if my_tid:
                org_id = getattr(g, 'hi_org_id', None)
                site_ids = db.session.query(
                    db.func.cast(Miner.site_id, db.Integer)
                ).filter(
                    Miner.hi_tenant_id == my_tid
                ).distinct().all()
                site_id_list = [s[0] for s in site_ids]
                if site_id_list and org_id:
                    sites = HostingSite.query.filter(
                        HostingSite.id.in_(site_id_list),
                        HostingSite.hi_org_id == org_id
                    ).all()
                else:
                    sites = []
            else:
                sites = []
        else:
            sites = []

        hi_write_audit('SITE_LIST', 'site', None)
        return jsonify([{
            'id': s.id, 'name': s.name, 'slug': s.slug,
            'location': s.location, 'capacity_mw': s.capacity_mw,
            'electricity_rate': s.electricity_rate,
            'operator_name': s.operator_name, 'status': s.status
        } for s in sites])
    except Exception as e:
        logger.error(f"list_sites error: {e}")
        return _error('SITE_LIST_FAILED', str(e), 500)


@hi_api_bp.route('/curtailment/plans', methods=['GET'])
@hi_require_auth
def list_curtailment_plans():
    try:
        q = HiCurtailmentPlan.query
        site_id = request.args.get('site_id')
        req_tenant_id = request.args.get('tenant_id')
        if site_id:
            q = q.filter_by(site_id=int(site_id))

        hi_role = getattr(g, 'hi_role', None)
        if hi_role in TENANT_ROLES:
            if req_tenant_id is not None and int(req_tenant_id) != getattr(g, 'hi_tenant_id', None):
                return _error('ACCESS_DENIED', 'Cannot query other tenant plans', 403)
            q = q.filter(HiCurtailmentPlan.tenant_id == getattr(g, 'hi_tenant_id', None))
        elif hi_role in OPERATOR_ROLES:
            q = hi_filter_by_tenant(q, HiCurtailmentPlan)
            if req_tenant_id:
                if not hi_check_tenant_id_override(req_tenant_id):
                    return _error('ACCESS_DENIED', 'Tenant not in your org', 403)
                q = q.filter(HiCurtailmentPlan.tenant_id == int(req_tenant_id))

        plans = q.order_by(HiCurtailmentPlan.created_at.desc()).all()
        return jsonify([p.to_dict() for p in plans])
    except Exception as e:
        logger.error(f"list_curtailment_plans error: {e}")
        return _error('PLAN_LIST_FAILED', str(e), 500)


@hi_api_bp.route('/curtailment/plans', methods=['POST'])
@hi_require_tenant_or_operator
def create_curtailment_plan():
    try:
        data = request.get_json(force=True)
        hi_role = getattr(g, 'hi_role', None)
        if hi_role in TENANT_ROLES and hi_role != 'tenant_admin':
            return _error('PERMISSION_DENIED', 'Only tenant_admin can create plans', 403)

        if hi_role in TENANT_ROLES:
            t_id = getattr(g, 'hi_tenant_id', None)
        else:
            t_id = data.get('tenant_id')
            if t_id and not hi_check_tenant_id_override(t_id):
                return _error('ACCESS_DENIED', 'Tenant not in your org', 403)

        plan = HiCurtailmentPlan(
            org_id=getattr(g, 'hi_org_id', None),
            site_id=int(data['site_id']),
            tenant_scope=data.get('tenant_scope', 'site_wide'),
            tenant_id=int(t_id) if t_id else None,
            name=data.get('name', 'Curtailment Plan'),
            objective=data.get('objective', 'save_cost'),
            inputs_json=data.get('inputs_json', {}),
            created_by=session.get('user_id')
        )
        db.session.add(plan)
        db.session.commit()
        hi_write_audit('PLAN_CREATE', 'curtailment_plan', plan.id, {'name': plan.name})
        return jsonify(plan.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        logger.error(f"create_curtailment_plan error: {e}")
        return _error('PLAN_CREATE_FAILED', str(e), 500)


@hi_api_bp.route('/curtailment/plans/<int:plan_id>/simulate', methods=['POST'])
@hi_require_auth
def simulate_plan(plan_id):
    try:
        plan, err = _get_scoped_plan_or_404(plan_id)
        if err:
            return err
        result = CurtailmentEngine.simulate(plan_id)
        if 'error' in result:
            return _error('SIMULATE_FAILED', result['error'], 400)
        return jsonify(result)
    except Exception as e:
        logger.error(f"simulate_plan error: {e}")
        return _error('SIMULATE_FAILED', str(e), 500)


@hi_api_bp.route('/curtailment/plans/<int:plan_id>/execute', methods=['POST'])
@hi_require_auth
def execute_plan(plan_id):
    try:
        plan, err = _get_scoped_plan_or_404(plan_id)
        if err:
            return err
        result = CurtailmentEngine.execute(plan_id, actor_user_id=session.get('user_id'))
        if 'error' in result:
            return _error('EXECUTE_FAILED', result['error'], 400)
        return jsonify(result)
    except Exception as e:
        logger.error(f"execute_plan error: {e}")
        return _error('EXECUTE_FAILED', str(e), 500)


@hi_api_bp.route('/curtailment/plans/<int:plan_id>/verify', methods=['POST'])
@hi_require_auth
def verify_plan(plan_id):
    try:
        plan, err = _get_scoped_plan_or_404(plan_id)
        if err:
            return err
        result = CurtailmentEngine.verify(plan_id, actor_user_id=session.get('user_id'))
        if 'error' in result:
            return _error('VERIFY_FAILED', result['error'], 400)
        return jsonify(result)
    except Exception as e:
        logger.error(f"verify_plan error: {e}")
        return _error('VERIFY_FAILED', str(e), 500)


@hi_api_bp.route('/curtailment/plans/<int:plan_id>/report', methods=['GET'])
@hi_require_auth
def plan_report(plan_id):
    try:
        plan, err = _get_scoped_plan_or_404(plan_id)
        if err:
            return err
        result = HiCurtailmentResult.query.filter_by(plan_id=plan_id).first()
        actions = HiCurtailmentAction.query.filter_by(plan_id=plan_id).all()
        report = {
            'plan': plan.to_dict(),
            'result': result.to_dict() if result else None,
            'actions': [a.to_dict() for a in actions]
        }
        return jsonify(report)
    except Exception as e:
        logger.error(f"plan_report error: {e}")
        return _error('REPORT_FAILED', str(e), 500)


@hi_api_bp.route('/commands/<request_id>', methods=['GET'])
@hi_require_auth
def command_status(request_id):
    try:
        q = HiCommandQueue.query.filter_by(request_id=request_id)
        hi_role = getattr(g, 'hi_role', None)
        if hi_role in OPERATOR_ROLES:
            org_id = getattr(g, 'hi_org_id', None)
            if org_id:
                q = q.filter(HiCommandQueue.org_id == org_id)
        elif hi_role in TENANT_ROLES:
            my_tid = getattr(g, 'hi_tenant_id', None)
            q = q.filter(HiCommandQueue.tenant_id == my_tid)
        else:
            return jsonify([])
        commands = q.all()
        return jsonify([c.to_dict() for c in commands])
    except Exception as e:
        logger.error(f"command_status error: {e}")
        return _error('COMMAND_QUERY_FAILED', str(e), 500)


@hi_api_bp.route('/tariffs', methods=['GET'])
@hi_require_operator
def list_tariffs():
    try:
        org_id = getattr(g, 'hi_org_id', None)
        q = HiTariff.query
        if org_id:
            q = q.filter_by(org_id=org_id)
        tariffs = q.all()
        return jsonify([t.to_dict() for t in tariffs])
    except Exception as e:
        logger.error(f"list_tariffs error: {e}")
        return _error('TARIFF_LIST_FAILED', str(e), 500)


@hi_api_bp.route('/tariffs', methods=['POST'])
@hi_require_operator
def create_tariff():
    try:
        data = request.get_json(force=True)
        tariff = HiTariff(
            org_id=getattr(g, 'hi_org_id', None),
            name=data.get('name', 'New Tariff'),
            tariff_type=data.get('tariff_type', 'flat'),
            params_json=data.get('params_json'),
            currency=data.get('currency', 'USD')
        )
        db.session.add(tariff)
        db.session.commit()
        return jsonify(tariff.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        logger.error(f"create_tariff error: {e}")
        return _error('TARIFF_CREATE_FAILED', str(e), 500)


@hi_api_bp.route('/contracts', methods=['GET'])
@hi_require_auth
def list_contracts():
    try:
        q = HiContract.query
        q = hi_filter_by_tenant(q, HiContract)
        req_tid = request.args.get('tenant_id')
        if req_tid:
            if not hi_check_tenant_id_override(req_tid):
                return _error('ACCESS_DENIED', 'Cannot query other tenant contracts', 403)
            q = q.filter_by(tenant_id=int(req_tid))
        contracts = q.all()
        return jsonify([c.to_dict() for c in contracts])
    except Exception as e:
        logger.error(f"list_contracts error: {e}")
        return _error('CONTRACT_LIST_FAILED', str(e), 500)


@hi_api_bp.route('/contracts', methods=['POST'])
@hi_require_operator
def create_contract():
    try:
        data = request.get_json(force=True)
        t_id = int(data['tenant_id'])
        if not hi_check_tenant_id_override(t_id):
            return _error('ACCESS_DENIED', 'Tenant not in your org', 403)
        contract = HiContract(
            org_id=getattr(g, 'hi_org_id', None),
            tenant_id=t_id,
            site_id=int(data['site_id']),
            tariff_id=int(data['tariff_id']) if data.get('tariff_id') else None,
            hosting_fee_type=data.get('hosting_fee_type', 'per_kw'),
            hosting_fee_params_json=data.get('hosting_fee_params_json'),
            curtailment_split_pct=float(data.get('curtailment_split_pct', 0)),
            billing_cycle=data.get('billing_cycle', 'monthly'),
            effective_from=_parse_date(data.get('effective_from')),
            effective_to=_parse_date(data.get('effective_to'))
        )
        db.session.add(contract)
        db.session.commit()
        return jsonify(contract.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        logger.error(f"create_contract error: {e}")
        return _error('CONTRACT_CREATE_FAILED', str(e), 500)


@hi_api_bp.route('/usage/generate', methods=['POST'])
@hi_require_auth
def generate_usage():
    try:
        data = request.get_json(force=True)
        period_start = _parse_date(data['period_start'])
        period_end = _parse_date(data['period_end'])
        site_id = int(data['site_id'])

        hi_role = getattr(g, 'hi_role', None)
        if hi_role in TENANT_ROLES:
            tenant_id = getattr(g, 'hi_tenant_id', None)
        else:
            tenant_id = int(data['tenant_id'])
            if not hi_check_tenant_id_override(tenant_id):
                return _error('ACCESS_DENIED', 'Tenant not in your org', 403)

        org_id = getattr(g, 'hi_org_id', None)
        result = UsageService.generate_usage(org_id, site_id, tenant_id, period_start, period_end)
        hi_write_audit('USAGE_GENERATE', 'usage_record', result.get('id'), {
            'site_id': site_id, 'tenant_id': tenant_id
        })
        return jsonify(result), 201
    except Exception as e:
        logger.error(f"generate_usage error: {e}")
        return _error('USAGE_GENERATE_FAILED', str(e), 500)


@hi_api_bp.route('/usage', methods=['GET'])
@hi_require_auth
def list_usage():
    try:
        q = HiUsageRecord.query
        q = hi_filter_by_tenant(q, HiUsageRecord)

        req_tid = request.args.get('tenant_id')
        if req_tid:
            if not hi_check_tenant_id_override(req_tid):
                return _error('ACCESS_DENIED', 'Cannot query other tenant usage', 403)
            q = q.filter_by(tenant_id=int(req_tid))

        site_id = request.args.get('site_id')
        from_date = request.args.get('from')
        to_date = request.args.get('to')
        if site_id:
            q = q.filter_by(site_id=int(site_id))
        if from_date:
            q = q.filter(HiUsageRecord.period_start >= _parse_date(from_date))
        if to_date:
            q = q.filter(HiUsageRecord.period_end <= _parse_date(to_date))
        records = q.all()
        return jsonify([r.to_dict() for r in records])
    except Exception as e:
        logger.error(f"list_usage error: {e}")
        return _error('USAGE_LIST_FAILED', str(e), 500)


@hi_api_bp.route('/invoices/generate', methods=['POST'])
@hi_require_auth
def generate_invoice():
    try:
        data = request.get_json(force=True)
        contract_id = int(data['contract_id'])
        contract = HiContract.query.get(contract_id)
        if not contract:
            return _error('NOT_FOUND', 'Contract not found', 404)

        hi_role = getattr(g, 'hi_role', None)
        if hi_role in OPERATOR_ROLES:
            org_id = getattr(g, 'hi_org_id', None)
            if org_id and contract.org_id != org_id:
                return _error('ACCESS_DENIED', 'Contract not in your org', 403)
        elif hi_role in TENANT_ROLES:
            if contract.tenant_id != getattr(g, 'hi_tenant_id', None):
                return _error('ACCESS_DENIED', 'Contract not accessible', 403)

        period_start = _parse_date(data['period_start'])
        period_end = _parse_date(data['period_end'])
        result = BillingService.generate_invoice(
            contract_id, period_start, period_end,
            actor_user_id=session.get('user_id')
        )
        if isinstance(result, dict) and 'error' in result:
            return _error('INVOICE_GENERATE_FAILED', result['error'], 400)
        hi_write_audit('INVOICE_GENERATE', 'invoice', result.get('id'), {
            'contract_id': contract_id
        })
        return jsonify(result), 201
    except Exception as e:
        logger.error(f"generate_invoice error: {e}")
        return _error('INVOICE_GENERATE_FAILED', str(e), 500)


@hi_api_bp.route('/invoices', methods=['GET'])
@hi_require_auth
def list_invoices():
    try:
        q = HiInvoice.query
        q = hi_filter_by_tenant(q, HiInvoice)

        req_tid = request.args.get('tenant_id')
        if req_tid:
            if not hi_check_tenant_id_override(req_tid):
                return _error('ACCESS_DENIED', 'Cannot query other tenant invoices', 403)
            q = q.filter_by(tenant_id=int(req_tid))

        from_date = request.args.get('from')
        to_date = request.args.get('to')
        if from_date:
            q = q.filter(HiInvoice.period_start >= _parse_date(from_date))
        if to_date:
            q = q.filter(HiInvoice.period_end <= _parse_date(to_date))
        invoices = q.order_by(HiInvoice.created_at.desc()).all()
        return jsonify([inv.to_dict() for inv in invoices])
    except Exception as e:
        logger.error(f"list_invoices error: {e}")
        return _error('INVOICE_LIST_FAILED', str(e), 500)


@hi_api_bp.route('/invoices/<int:invoice_id>', methods=['GET'])
@hi_require_auth
def get_invoice(invoice_id):
    try:
        invoice, err = _get_scoped_invoice_or_404(invoice_id)
        if err:
            return err
        return jsonify(invoice.to_dict())
    except Exception as e:
        logger.error(f"get_invoice error: {e}")
        return _error('INVOICE_GET_FAILED', str(e), 500)


@hi_api_bp.route('/invoices/<int:invoice_id>/export.csv', methods=['GET'])
@hi_require_auth
def export_invoice_csv(invoice_id):
    try:
        invoice, err = _get_scoped_invoice_or_404(invoice_id)
        if err:
            return err
        csv_data = BillingService.export_invoice_csv(invoice_id)
        if csv_data is None:
            return _error('NOT_FOUND', 'Invoice not found', 404)
        hi_write_audit('INVOICE_EXPORT', 'invoice', invoice_id)
        return Response(csv_data, mimetype='text/csv',
                        headers={'Content-Disposition': f'attachment; filename=invoice_{invoice_id}.csv'})
    except Exception as e:
        logger.error(f"export_invoice_csv error: {e}")
        return _error('INVOICE_EXPORT_FAILED', str(e), 500)
