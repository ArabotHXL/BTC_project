import logging
import uuid
from datetime import datetime
from functools import wraps

from flask import Blueprint, request, jsonify, session, g, redirect, render_template, Response
from db import db
from models_ab import (
    Org, Tenant, MinerGroup, ABAuditLog,
    ABCurtailmentPlan, ABCurtailmentAction, ABCurtailmentResult,
    Tariff, ABContract, ABUsageRecord, ABInvoice
)
from models import UserAccess, HostingSite, Miner
from services.curtailment_engine import CurtailmentEngine
from services.usage_service import UsageService
from services.billing_service import BillingService

logger = logging.getLogger(__name__)

ab_api_bp = Blueprint('ab_api_bp', __name__, url_prefix='/api/ab')

OPERATOR_ROLES = {'owner', 'admin', 'operator', 'operator_admin', 'operator_ops'}

_command_store = {}


def get_current_ab_user():
    user_id = session.get('user_id')
    if not user_id:
        return None
    user = UserAccess.query.get(user_id)
    if not user:
        return None
    role = user.role or 'guest'
    org_id = None
    tenant_id = None
    org = Org.query.first()
    if org:
        org_id = org.id
    if role in OPERATOR_ROLES:
        tenant_id = None
    else:
        tenant = Tenant.query.filter_by(org_id=org_id).first() if org_id else None
        tenant_id = tenant.id if tenant else None
    return {
        'user_id': user.id,
        'org_id': org_id,
        'tenant_id': tenant_id,
        'role': role
    }


def require_ab_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        ab_user = get_current_ab_user()
        if not ab_user:
            return jsonify({'error': 'Authentication required'}), 401
        g.ab_user = ab_user
        return f(*args, **kwargs)
    return decorated


def require_operator(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        ab_user = get_current_ab_user()
        if not ab_user:
            return jsonify({'error': 'Authentication required'}), 401
        if ab_user['role'] not in OPERATOR_ROLES:
            return jsonify({'error': 'Operator access required'}), 403
        g.ab_user = ab_user
        return f(*args, **kwargs)
    return decorated


def write_audit(action_type, entity_type, entity_id, detail_json=None):
    try:
        ab_user = g.ab_user
        audit = ABAuditLog(
            org_id=ab_user.get('org_id'),
            tenant_id=ab_user.get('tenant_id'),
            actor_user_id=ab_user.get('user_id'),
            action_type=action_type,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id else None,
            detail_json=detail_json
        )
        db.session.add(audit)
        db.session.commit()
    except Exception as e:
        logger.error(f"Audit write failed: {e}")


def tenant_filter(query, model):
    ab_user = g.ab_user
    if ab_user['role'] not in OPERATOR_ROLES and ab_user.get('tenant_id'):
        query = query.filter(model.tenant_id == ab_user['tenant_id'])
    return query


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


@ab_api_bp.route('/portal')
def portal_page():
    if 'user_id' not in session:
        return redirect('/login')
    return render_template('portal.html')


@ab_api_bp.route('/me', methods=['GET'])
@require_ab_auth
def me():
    return jsonify(g.ab_user)


@ab_api_bp.route('/tenants', methods=['GET'])
@require_ab_auth
def list_tenants():
    try:
        ab_user = g.ab_user
        q = Tenant.query
        if ab_user.get('org_id'):
            q = q.filter_by(org_id=ab_user['org_id'])
        if ab_user['role'] not in OPERATOR_ROLES and ab_user.get('tenant_id'):
            q = q.filter_by(id=ab_user['tenant_id'])
        tenants = q.all()
        return jsonify([t.to_dict() for t in tenants])
    except Exception as e:
        logger.error(f"list_tenants error: {e}")
        return jsonify({'error': str(e)}), 500


@ab_api_bp.route('/tenants', methods=['POST'])
@require_operator
def create_tenant():
    try:
        data = request.get_json(force=True)
        tenant = Tenant(
            org_id=g.ab_user['org_id'],
            name=data.get('name', 'New Tenant'),
            tenant_type=data.get('tenant_type', 'self')
        )
        db.session.add(tenant)
        db.session.commit()
        write_audit('TENANT_CREATE', 'tenant', tenant.id, {'name': tenant.name})
        return jsonify(tenant.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        logger.error(f"create_tenant error: {e}")
        return jsonify({'error': str(e)}), 500


@ab_api_bp.route('/sites', methods=['GET'])
@require_ab_auth
def list_sites():
    try:
        sites = HostingSite.query.all()
        return jsonify([{
            'id': s.id, 'name': s.name, 'slug': s.slug,
            'location': s.location, 'capacity_mw': s.capacity_mw,
            'electricity_rate': s.electricity_rate,
            'operator_name': s.operator_name, 'status': s.status
        } for s in sites])
    except Exception as e:
        logger.error(f"list_sites error: {e}")
        return jsonify({'error': str(e)}), 500


@ab_api_bp.route('/sites', methods=['POST'])
@require_operator
def create_site():
    try:
        data = request.get_json(force=True)
        site = HostingSite(
            name=data['name'],
            slug=data['slug'],
            location=data['location'],
            capacity_mw=float(data['capacity_mw']),
            electricity_rate=float(data['electricity_rate']),
            operator_name=data['operator_name']
        )
        db.session.add(site)
        db.session.commit()
        write_audit('SITE_CREATE', 'site', site.id, {'name': site.name})
        return jsonify({
            'id': site.id, 'name': site.name, 'slug': site.slug,
            'location': site.location, 'capacity_mw': site.capacity_mw,
            'electricity_rate': site.electricity_rate,
            'operator_name': site.operator_name
        }), 201
    except Exception as e:
        db.session.rollback()
        logger.error(f"create_site error: {e}")
        return jsonify({'error': str(e)}), 500


@ab_api_bp.route('/miners', methods=['GET'])
@require_ab_auth
def list_miners():
    try:
        q = Miner.query
        site_id = request.args.get('site_id')
        tenant_id = request.args.get('tenant_id')
        if site_id:
            q = q.filter_by(site_id=str(site_id))
        miners = q.all()
        return jsonify([{
            'id': m.id, 'miner_id': m.miner_id, 'site_id': m.site_id,
            'model': m.model, 'ip': m.ip, 'status': m.status,
            'created_at': m.created_at.isoformat() if m.created_at else None
        } for m in miners])
    except Exception as e:
        logger.error(f"list_miners error: {e}")
        return jsonify({'error': str(e)}), 500


@ab_api_bp.route('/miners', methods=['POST'])
@require_operator
def create_miner():
    try:
        data = request.get_json(force=True)
        miner = Miner(
            miner_id=data.get('miner_id', f'miner-{uuid.uuid4().hex[:8]}'),
            site_id=str(data['site_id']),
            ip=data['ip'],
            model=data.get('model'),
            port=data.get('port'),
            api=data.get('api'),
            note=data.get('note')
        )
        db.session.add(miner)
        db.session.commit()
        write_audit('MINER_CREATE', 'miner', miner.id, {'miner_id': miner.miner_id})
        return jsonify({
            'id': miner.id, 'miner_id': miner.miner_id, 'site_id': miner.site_id,
            'model': miner.model, 'ip': miner.ip
        }), 201
    except Exception as e:
        db.session.rollback()
        logger.error(f"create_miner error: {e}")
        return jsonify({'error': str(e)}), 500


@ab_api_bp.route('/groups', methods=['GET'])
@require_ab_auth
def list_groups():
    try:
        q = MinerGroup.query
        site_id = request.args.get('site_id')
        if site_id:
            q = q.filter_by(site_id=int(site_id))
        q = tenant_filter(q, MinerGroup)
        groups = q.all()
        return jsonify([g_item.to_dict() for g_item in groups])
    except Exception as e:
        logger.error(f"list_groups error: {e}")
        return jsonify({'error': str(e)}), 500


@ab_api_bp.route('/groups', methods=['POST'])
@require_ab_auth
def create_group():
    try:
        ab_user = g.ab_user
        data = request.get_json(force=True)
        t_id = data.get('tenant_id')
        if ab_user['role'] not in OPERATOR_ROLES:
            if ab_user['role'] != 'tenant_admin':
                return jsonify({'error': 'Permission denied'}), 403
            if t_id and int(t_id) != ab_user.get('tenant_id'):
                return jsonify({'error': 'Cannot create group for another tenant'}), 403
            t_id = ab_user.get('tenant_id')
        group = MinerGroup(
            site_id=int(data['site_id']),
            tenant_id=int(t_id) if t_id else None,
            name=data.get('name', 'New Group'),
            selector_json=data.get('selector_json'),
            priority=data.get('priority', 100)
        )
        db.session.add(group)
        db.session.commit()
        write_audit('GROUP_CREATE', 'group', group.id, {'name': group.name})
        return jsonify(group.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        logger.error(f"create_group error: {e}")
        return jsonify({'error': str(e)}), 500


@ab_api_bp.route('/commands/miner/<int:miner_id>', methods=['POST'])
@require_ab_auth
def command_miner(miner_id):
    try:
        data = request.get_json(force=True)
        req_id = str(uuid.uuid4())
        entry = {
            'request_id': req_id,
            'status': 'queued',
            'target': 'miner',
            'target_id': miner_id,
            'command_type': data.get('command_type', 'status'),
            'payload': data.get('payload', {}),
            'created_at': datetime.utcnow().isoformat()
        }
        _command_store[req_id] = entry
        write_audit('COMMAND_MINER', 'miner', miner_id, {
            'request_id': req_id, 'command_type': entry['command_type']
        })
        return jsonify(entry), 202
    except Exception as e:
        logger.error(f"command_miner error: {e}")
        return jsonify({'error': str(e)}), 500


@ab_api_bp.route('/commands/group/<int:group_id>', methods=['POST'])
@require_ab_auth
def command_group(group_id):
    try:
        data = request.get_json(force=True)
        req_id = str(uuid.uuid4())
        entry = {
            'request_id': req_id,
            'status': 'queued',
            'target': 'group',
            'target_id': group_id,
            'command_type': data.get('command_type', 'status'),
            'payload': data.get('payload', {}),
            'created_at': datetime.utcnow().isoformat()
        }
        _command_store[req_id] = entry
        write_audit('COMMAND_GROUP', 'group', group_id, {
            'request_id': req_id, 'command_type': entry['command_type']
        })
        return jsonify(entry), 202
    except Exception as e:
        logger.error(f"command_group error: {e}")
        return jsonify({'error': str(e)}), 500


@ab_api_bp.route('/commands/<request_id>', methods=['GET'])
@require_ab_auth
def command_status(request_id):
    entry = _command_store.get(request_id)
    if not entry:
        return jsonify({'error': 'Command not found'}), 404
    return jsonify(entry)


@ab_api_bp.route('/curtailment/plans', methods=['GET'])
@require_ab_auth
def list_curtailment_plans():
    try:
        q = ABCurtailmentPlan.query
        site_id = request.args.get('site_id')
        if site_id:
            q = q.filter_by(site_id=int(site_id))
        q = tenant_filter(q, ABCurtailmentPlan)
        if g.ab_user.get('org_id'):
            q = q.filter_by(org_id=g.ab_user['org_id'])
        plans = q.order_by(ABCurtailmentPlan.created_at.desc()).all()
        return jsonify([p.to_dict() for p in plans])
    except Exception as e:
        logger.error(f"list_curtailment_plans error: {e}")
        return jsonify({'error': str(e)}), 500


@ab_api_bp.route('/curtailment/plans', methods=['POST'])
@require_ab_auth
def create_curtailment_plan():
    try:
        data = request.get_json(force=True)
        ab_user = g.ab_user
        plan = ABCurtailmentPlan(
            org_id=ab_user['org_id'],
            site_id=int(data['site_id']),
            tenant_scope=data.get('tenant_scope', 'site_wide'),
            tenant_id=int(data['tenant_id']) if data.get('tenant_id') else None,
            name=data.get('name', 'Curtailment Plan'),
            objective=data.get('objective', 'save_cost'),
            inputs_json=data.get('inputs_json', {}),
            created_by=ab_user['user_id']
        )
        db.session.add(plan)
        db.session.commit()
        write_audit('CURTAILMENT_CREATE', 'curtailment_plan', plan.id, {'name': plan.name})
        return jsonify(plan.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        logger.error(f"create_curtailment_plan error: {e}")
        return jsonify({'error': str(e)}), 500


@ab_api_bp.route('/curtailment/plans/<int:plan_id>/simulate', methods=['POST'])
@require_ab_auth
def simulate_plan(plan_id):
    try:
        result = CurtailmentEngine.simulate(plan_id)
        if 'error' in result:
            return jsonify(result), 400
        return jsonify(result)
    except Exception as e:
        logger.error(f"simulate_plan error: {e}")
        return jsonify({'error': str(e)}), 500


@ab_api_bp.route('/curtailment/plans/<int:plan_id>/execute', methods=['POST'])
@require_ab_auth
def execute_plan(plan_id):
    try:
        result = CurtailmentEngine.execute(plan_id, actor_user_id=g.ab_user['user_id'])
        if 'error' in result:
            return jsonify(result), 400
        write_audit('CURTAILMENT_EXECUTE', 'curtailment_plan', plan_id, result)
        return jsonify(result)
    except Exception as e:
        logger.error(f"execute_plan error: {e}")
        return jsonify({'error': str(e)}), 500


@ab_api_bp.route('/curtailment/plans/<int:plan_id>/verify', methods=['POST'])
@require_ab_auth
def verify_plan(plan_id):
    try:
        result = CurtailmentEngine.verify(plan_id, actor_user_id=g.ab_user['user_id'])
        if 'error' in result:
            return jsonify(result), 400
        write_audit('CURTAILMENT_VERIFY', 'curtailment_plan', plan_id, result)
        return jsonify(result)
    except Exception as e:
        logger.error(f"verify_plan error: {e}")
        return jsonify({'error': str(e)}), 500


@ab_api_bp.route('/curtailment/plans/<int:plan_id>/report', methods=['GET'])
@require_ab_auth
def plan_report(plan_id):
    try:
        plan = ABCurtailmentPlan.query.get(plan_id)
        if not plan:
            return jsonify({'error': 'Plan not found'}), 404
        result = ABCurtailmentResult.query.filter_by(plan_id=plan_id).first()
        actions = ABCurtailmentAction.query.filter_by(plan_id=plan_id).all()
        report = {
            'plan': plan.to_dict(),
            'result': result.to_dict() if result else None,
            'actions': [a.to_dict() for a in actions]
        }
        fmt = request.args.get('format')
        if fmt == 'csv':
            import csv
            import io
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(['Plan Report'])
            writer.writerow(['Plan ID', plan.id])
            writer.writerow(['Name', plan.name])
            writer.writerow(['Status', plan.status])
            writer.writerow(['Objective', plan.objective])
            writer.writerow([])
            writer.writerow(['Action ID', 'Target Type', 'Target ID', 'Command', 'Status'])
            for a in actions:
                writer.writerow([a.id, a.target_type, a.target_id, a.command_type, a.status])
            if result:
                writer.writerow([])
                writer.writerow(['Actual Results'])
                actual = result.actual_json or {}
                for k, v in actual.items():
                    writer.writerow([k, v])
            csv_data = output.getvalue()
            return Response(csv_data, mimetype='text/csv',
                            headers={'Content-Disposition': f'attachment; filename=plan_{plan_id}_report.csv'})
        return jsonify(report)
    except Exception as e:
        logger.error(f"plan_report error: {e}")
        return jsonify({'error': str(e)}), 500


@ab_api_bp.route('/contracts', methods=['POST'])
@require_operator
def create_contract():
    try:
        data = request.get_json(force=True)
        contract = ABContract(
            org_id=g.ab_user['org_id'],
            tenant_id=int(data['tenant_id']),
            site_id=int(data['site_id']),
            tariff_id=int(data['tariff_id']) if data.get('tariff_id') else None,
            hosting_fee_type=data.get('hosting_fee_type', 'per_kw'),
            hosting_fee_params_json=data.get('hosting_fee_params_json'),
            curtailment_split_pct=float(data.get('curtailment_split_pct', 0)),
            sla_json=data.get('sla_json'),
            billing_cycle=data.get('billing_cycle', 'monthly'),
            effective_from=_parse_date(data.get('effective_from')),
            effective_to=_parse_date(data.get('effective_to'))
        )
        db.session.add(contract)
        db.session.commit()
        write_audit('CONTRACT_CREATE', 'contract', contract.id, {'tenant_id': contract.tenant_id})
        return jsonify(contract.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        logger.error(f"create_contract error: {e}")
        return jsonify({'error': str(e)}), 500


@ab_api_bp.route('/contracts', methods=['GET'])
@require_ab_auth
def list_contracts():
    try:
        q = ABContract.query
        if g.ab_user.get('org_id'):
            q = q.filter_by(org_id=g.ab_user['org_id'])
        q = tenant_filter(q, ABContract)
        tid = request.args.get('tenant_id')
        if tid:
            q = q.filter_by(tenant_id=int(tid))
        contracts = q.all()
        return jsonify([c.to_dict() for c in contracts])
    except Exception as e:
        logger.error(f"list_contracts error: {e}")
        return jsonify({'error': str(e)}), 500


@ab_api_bp.route('/usage/generate', methods=['POST'])
@require_ab_auth
def generate_usage():
    try:
        data = request.get_json(force=True)
        period_start = _parse_date(data['period_start'])
        period_end = _parse_date(data['period_end'])
        site_id = int(data['site_id'])
        tenant_id = int(data['tenant_id'])
        org_id = g.ab_user['org_id']
        result = UsageService.generate_usage(org_id, site_id, tenant_id, period_start, period_end)
        write_audit('USAGE_GENERATE', 'usage_record', result.get('id'), {
            'site_id': site_id, 'tenant_id': tenant_id
        })
        return jsonify(result), 201
    except Exception as e:
        logger.error(f"generate_usage error: {e}")
        return jsonify({'error': str(e)}), 500


@ab_api_bp.route('/invoices/generate', methods=['POST'])
@require_ab_auth
def generate_invoice():
    try:
        data = request.get_json(force=True)
        contract_id = int(data['contract_id'])
        period_start = _parse_date(data['period_start'])
        period_end = _parse_date(data['period_end'])
        result = BillingService.generate_invoice(
            contract_id, period_start, period_end,
            actor_user_id=g.ab_user['user_id']
        )
        if 'error' in result:
            return jsonify(result), 400
        return jsonify(result), 201
    except Exception as e:
        logger.error(f"generate_invoice error: {e}")
        return jsonify({'error': str(e)}), 500


@ab_api_bp.route('/invoices', methods=['GET'])
@require_ab_auth
def list_invoices():
    try:
        q = ABInvoice.query
        if g.ab_user.get('org_id'):
            q = q.filter_by(org_id=g.ab_user['org_id'])
        q = tenant_filter(q, ABInvoice)
        tid = request.args.get('tenant_id')
        if tid:
            q = q.filter_by(tenant_id=int(tid))
        invoices = q.order_by(ABInvoice.created_at.desc()).all()
        return jsonify([inv.to_dict() for inv in invoices])
    except Exception as e:
        logger.error(f"list_invoices error: {e}")
        return jsonify({'error': str(e)}), 500


@ab_api_bp.route('/invoices/<int:invoice_id>', methods=['GET'])
@require_ab_auth
def get_invoice(invoice_id):
    try:
        invoice = ABInvoice.query.get(invoice_id)
        if not invoice:
            return jsonify({'error': 'Invoice not found'}), 404
        return jsonify(invoice.to_dict())
    except Exception as e:
        logger.error(f"get_invoice error: {e}")
        return jsonify({'error': str(e)}), 500


@ab_api_bp.route('/invoices/<int:invoice_id>/export.csv', methods=['GET'])
@require_ab_auth
def export_invoice_csv(invoice_id):
    try:
        csv_data = BillingService.export_invoice_csv(invoice_id)
        if csv_data is None:
            return jsonify({'error': 'Invoice not found'}), 404
        return Response(csv_data, mimetype='text/csv',
                        headers={'Content-Disposition': f'attachment; filename=invoice_{invoice_id}.csv'})
    except Exception as e:
        logger.error(f"export_invoice_csv error: {e}")
        return jsonify({'error': str(e)}), 500
