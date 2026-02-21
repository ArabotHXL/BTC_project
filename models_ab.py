from datetime import datetime

from db import db


class Org(db.Model):
    __tablename__ = 'ab_orgs'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    org_type = db.Column(db.String(20), default='self')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    tenants = db.relationship('Tenant', backref='org', lazy='dynamic')
    tariffs = db.relationship('Tariff', backref='org', lazy='dynamic')
    contracts = db.relationship('ABContract', backref='org', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'org_type': self.org_type,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f'<Org {self.id}: {self.name}>'


class Tenant(db.Model):
    __tablename__ = 'ab_tenants'

    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('ab_orgs.id'), nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    tenant_type = db.Column(db.String(20), default='self')
    status = db.Column(db.String(20), default='active', index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    groups = db.relationship('MinerGroup', backref='tenant', lazy='dynamic')
    contracts = db.relationship('ABContract', backref='tenant', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'org_id': self.org_id,
            'name': self.name,
            'tenant_type': self.tenant_type,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f'<Tenant {self.id}: {self.name} (org={self.org_id})>'


class MinerGroup(db.Model):
    __tablename__ = 'ab_groups'

    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey('hosting_sites.id'), nullable=False, index=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('ab_tenants.id'), nullable=True, index=True)
    name = db.Column(db.String(200), nullable=False)
    selector_json = db.Column(db.JSON, nullable=True)
    priority = db.Column(db.Integer, default=100)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'site_id': self.site_id,
            'tenant_id': self.tenant_id,
            'name': self.name,
            'selector_json': self.selector_json,
            'priority': self.priority,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f'<MinerGroup {self.id}: {self.name} (site={self.site_id})>'


class ABAuditLog(db.Model):
    __tablename__ = 'ab_audit_log'

    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('ab_orgs.id'), nullable=True, index=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('ab_tenants.id'), nullable=True, index=True)
    actor_user_id = db.Column(db.Integer, db.ForeignKey('user_access.id'), nullable=True, index=True)
    action_type = db.Column(db.String(50), nullable=False, index=True)
    entity_type = db.Column(db.String(50), nullable=True)
    entity_id = db.Column(db.String(50), nullable=True)
    request_id = db.Column(db.String(100), nullable=True)
    detail_json = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    org = db.relationship('Org', backref='audit_logs')
    tenant = db.relationship('Tenant', backref='audit_logs')

    def to_dict(self):
        return {
            'id': self.id,
            'org_id': self.org_id,
            'tenant_id': self.tenant_id,
            'actor_user_id': self.actor_user_id,
            'action_type': self.action_type,
            'entity_type': self.entity_type,
            'entity_id': self.entity_id,
            'request_id': self.request_id,
            'detail_json': self.detail_json,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f'<ABAuditLog {self.id}: {self.action_type} by user={self.actor_user_id}>'


class ABCurtailmentPlan(db.Model):
    __tablename__ = 'ab_curtailment_plans'

    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('ab_orgs.id'), nullable=False, index=True)
    site_id = db.Column(db.Integer, db.ForeignKey('hosting_sites.id'), nullable=False, index=True)
    tenant_scope = db.Column(db.String(20), default='site_wide')
    tenant_id = db.Column(db.Integer, db.ForeignKey('ab_tenants.id'), nullable=True, index=True)
    name = db.Column(db.String(200), nullable=False)
    objective = db.Column(db.String(20), default='save_cost')
    inputs_json = db.Column(db.JSON, nullable=True)
    expected_json = db.Column(db.JSON, nullable=True)
    status = db.Column(db.String(20), default='draft', index=True)
    created_by = db.Column(db.Integer, db.ForeignKey('user_access.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    org = db.relationship('Org', backref='curtailment_plans')
    tenant = db.relationship('Tenant', backref='curtailment_plans')
    actions = db.relationship('ABCurtailmentAction', backref='plan', lazy='dynamic')
    result = db.relationship('ABCurtailmentResult', backref='plan', uselist=False)

    def to_dict(self):
        return {
            'id': self.id,
            'org_id': self.org_id,
            'site_id': self.site_id,
            'tenant_scope': self.tenant_scope,
            'tenant_id': self.tenant_id,
            'name': self.name,
            'objective': self.objective,
            'inputs_json': self.inputs_json,
            'expected_json': self.expected_json,
            'status': self.status,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f'<ABCurtailmentPlan {self.id}: {self.name} ({self.status})>'


class ABCurtailmentAction(db.Model):
    __tablename__ = 'ab_curtailment_actions'

    id = db.Column(db.Integer, primary_key=True)
    plan_id = db.Column(db.Integer, db.ForeignKey('ab_curtailment_plans.id'), nullable=False, index=True)
    target_type = db.Column(db.String(20), nullable=False)
    target_id = db.Column(db.Integer, nullable=False)
    command_type = db.Column(db.String(20), nullable=False)
    command_payload_json = db.Column(db.JSON, nullable=True)
    status = db.Column(db.String(20), default='queued', index=True)
    ack_json = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        return {
            'id': self.id,
            'plan_id': self.plan_id,
            'target_type': self.target_type,
            'target_id': self.target_id,
            'command_type': self.command_type,
            'command_payload_json': self.command_payload_json,
            'status': self.status,
            'ack_json': self.ack_json,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f'<ABCurtailmentAction {self.id}: {self.command_type} -> {self.target_type}:{self.target_id}>'


class ABCurtailmentResult(db.Model):
    __tablename__ = 'ab_curtailment_results'

    id = db.Column(db.Integer, primary_key=True)
    plan_id = db.Column(db.Integer, db.ForeignKey('ab_curtailment_plans.id'), nullable=False, unique=True, index=True)
    before_snapshot_json = db.Column(db.JSON, nullable=True)
    after_snapshot_json = db.Column(db.JSON, nullable=True)
    actual_json = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        return {
            'id': self.id,
            'plan_id': self.plan_id,
            'before_snapshot_json': self.before_snapshot_json,
            'after_snapshot_json': self.after_snapshot_json,
            'actual_json': self.actual_json,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f'<ABCurtailmentResult {self.id}: plan={self.plan_id}>'


class Tariff(db.Model):
    __tablename__ = 'ab_tariffs'

    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('ab_orgs.id'), nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    tariff_type = db.Column(db.String(20), default='flat')
    params_json = db.Column(db.JSON, nullable=True)
    currency = db.Column(db.String(10), default='USD')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    contracts = db.relationship('ABContract', backref='tariff', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'org_id': self.org_id,
            'name': self.name,
            'tariff_type': self.tariff_type,
            'params_json': self.params_json,
            'currency': self.currency,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f'<Tariff {self.id}: {self.name} ({self.tariff_type})>'


class ABContract(db.Model):
    __tablename__ = 'ab_contracts'

    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('ab_orgs.id'), nullable=False, index=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('ab_tenants.id'), nullable=False, index=True)
    site_id = db.Column(db.Integer, db.ForeignKey('hosting_sites.id'), nullable=False, index=True)
    tariff_id = db.Column(db.Integer, db.ForeignKey('ab_tariffs.id'), nullable=True, index=True)
    hosting_fee_type = db.Column(db.String(20), default='per_kw')
    hosting_fee_params_json = db.Column(db.JSON, nullable=True)
    curtailment_split_pct = db.Column(db.Float, default=0.0)
    sla_json = db.Column(db.JSON, nullable=True)
    billing_cycle = db.Column(db.String(20), default='monthly')
    effective_from = db.Column(db.DateTime, nullable=True)
    effective_to = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    invoices = db.relationship('ABInvoice', backref='contract', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'org_id': self.org_id,
            'tenant_id': self.tenant_id,
            'site_id': self.site_id,
            'tariff_id': self.tariff_id,
            'hosting_fee_type': self.hosting_fee_type,
            'hosting_fee_params_json': self.hosting_fee_params_json,
            'curtailment_split_pct': self.curtailment_split_pct,
            'sla_json': self.sla_json,
            'billing_cycle': self.billing_cycle,
            'effective_from': self.effective_from.isoformat() if self.effective_from else None,
            'effective_to': self.effective_to.isoformat() if self.effective_to else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f'<ABContract {self.id}: org={self.org_id} tenant={self.tenant_id}>'


class ABUsageRecord(db.Model):
    __tablename__ = 'ab_usage_records'

    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('ab_orgs.id'), nullable=False, index=True)
    site_id = db.Column(db.Integer, db.ForeignKey('hosting_sites.id'), nullable=False, index=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('ab_tenants.id'), nullable=False, index=True)
    period_start = db.Column(db.DateTime, nullable=False)
    period_end = db.Column(db.DateTime, nullable=False)
    kwh_estimated = db.Column(db.Float, default=0.0)
    avg_kw_estimated = db.Column(db.Float, default=0.0)
    method = db.Column(db.String(30), default='nominal_watts')
    evidence_json = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    org = db.relationship('Org', backref='usage_records')
    tenant = db.relationship('Tenant', backref='usage_records')

    __table_args__ = (
        db.Index('idx_ab_usage_period', 'tenant_id', 'period_start', 'period_end'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'org_id': self.org_id,
            'site_id': self.site_id,
            'tenant_id': self.tenant_id,
            'period_start': self.period_start.isoformat() if self.period_start else None,
            'period_end': self.period_end.isoformat() if self.period_end else None,
            'kwh_estimated': self.kwh_estimated,
            'avg_kw_estimated': self.avg_kw_estimated,
            'method': self.method,
            'evidence_json': self.evidence_json,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f'<ABUsageRecord {self.id}: tenant={self.tenant_id} {self.period_start}-{self.period_end}>'


class ABInvoice(db.Model):
    __tablename__ = 'ab_invoices'

    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('ab_orgs.id'), nullable=False, index=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('ab_tenants.id'), nullable=False, index=True)
    contract_id = db.Column(db.Integer, db.ForeignKey('ab_contracts.id'), nullable=True, index=True)
    period_start = db.Column(db.DateTime, nullable=False)
    period_end = db.Column(db.DateTime, nullable=False)
    subtotal = db.Column(db.Float, default=0.0)
    total = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='draft', index=True)
    line_items_json = db.Column(db.JSON, nullable=True)
    evidence_json = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    org = db.relationship('Org', backref='invoices')
    tenant = db.relationship('Tenant', backref='invoices')

    __table_args__ = (
        db.Index('idx_ab_invoice_period', 'tenant_id', 'period_start', 'period_end'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'org_id': self.org_id,
            'tenant_id': self.tenant_id,
            'contract_id': self.contract_id,
            'period_start': self.period_start.isoformat() if self.period_start else None,
            'period_end': self.period_end.isoformat() if self.period_end else None,
            'subtotal': self.subtotal,
            'total': self.total,
            'status': self.status,
            'line_items_json': self.line_items_json,
            'evidence_json': self.evidence_json,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f'<ABInvoice {self.id}: tenant={self.tenant_id} total={self.total} ({self.status})>'
