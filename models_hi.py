from datetime import datetime

from db import db


class HiOrg(db.Model):
    __tablename__ = 'hi_orgs'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    org_type = db.Column(db.String(20), default='self')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    tenants = db.relationship('HiTenant', backref='hi_org', lazy='dynamic')
    tariffs = db.relationship('HiTariff', backref='hi_org', lazy='dynamic')
    contracts = db.relationship('HiContract', backref='hi_org', lazy='dynamic')
    curtailment_plans = db.relationship('HiCurtailmentPlan', backref='hi_org', lazy='dynamic')
    audit_logs = db.relationship('HiAuditLog', backref='hi_org', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'org_type': self.org_type,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f'<HiOrg {self.id}: {self.name}>'


class HiTenant(db.Model):
    __tablename__ = 'hi_tenants'

    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('hi_orgs.id'), nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    tenant_type = db.Column(db.String(20), default='self')
    status = db.Column(db.String(20), default='active', index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    groups = db.relationship('HiGroup', backref='hi_tenant', lazy='dynamic')
    contracts = db.relationship('HiContract', backref='hi_tenant', lazy='dynamic')
    usage_records = db.relationship('HiUsageRecord', backref='hi_tenant', lazy='dynamic')
    invoices = db.relationship('HiInvoice', backref='hi_tenant', lazy='dynamic')

    __table_args__ = (
        db.Index('idx_hi_tenant_org_status', 'org_id', 'status'),
    )

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
        return f'<HiTenant {self.id}: {self.name} (org={self.org_id})>'


class HiGroup(db.Model):
    __tablename__ = 'hi_groups'

    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey('hosting_sites.id'), nullable=False, index=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('hi_tenants.id'), nullable=True, index=True)
    name = db.Column(db.String(200), nullable=False)
    selector_json = db.Column(db.JSON, nullable=True)
    priority = db.Column(db.Integer, default=100)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.Index('idx_hi_group_site_tenant', 'site_id', 'tenant_id'),
    )

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
        return f'<HiGroup {self.id}: {self.name} (site={self.site_id})>'


class HiAuditLog(db.Model):
    __tablename__ = 'hi_audit_log'

    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('hi_orgs.id'), nullable=True, index=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('hi_tenants.id'), nullable=True, index=True)
    actor_user_id = db.Column(db.Integer, db.ForeignKey('user_access.id'), nullable=True, index=True)
    action_type = db.Column(db.String(50), nullable=False, index=True)
    entity_type = db.Column(db.String(50), nullable=True)
    entity_id = db.Column(db.String(50), nullable=True)
    request_id = db.Column(db.String(100), nullable=True)
    detail_json = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    tenant = db.relationship('HiTenant', backref='hi_audit_logs')

    __table_args__ = (
        db.Index('idx_hi_audit_org_action', 'org_id', 'action_type'),
        db.Index('idx_hi_audit_entity', 'entity_type', 'entity_id'),
    )

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
        return f'<HiAuditLog {self.id}: {self.action_type} by user={self.actor_user_id}>'


class HiCurtailmentPlan(db.Model):
    __tablename__ = 'hi_curtailment_plans'

    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('hi_orgs.id'), nullable=False, index=True)
    site_id = db.Column(db.Integer, db.ForeignKey('hosting_sites.id'), nullable=False, index=True)
    tenant_scope = db.Column(db.String(20), default='site_wide')
    tenant_id = db.Column(db.Integer, db.ForeignKey('hi_tenants.id'), nullable=True, index=True)
    name = db.Column(db.String(200), nullable=False)
    objective = db.Column(db.String(20), default='save_cost')
    inputs_json = db.Column(db.JSON, nullable=True)
    expected_json = db.Column(db.JSON, nullable=True)
    status = db.Column(db.String(20), default='draft', index=True)
    created_by = db.Column(db.Integer, db.ForeignKey('user_access.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    tenant = db.relationship('HiTenant', backref='hi_curtailment_plans')
    actions = db.relationship('HiCurtailmentAction', backref='hi_plan', lazy='dynamic')
    result = db.relationship('HiCurtailmentResult', backref='hi_plan', uselist=False)

    __table_args__ = (
        db.Index('idx_hi_cplan_org_site', 'org_id', 'site_id'),
        db.Index('idx_hi_cplan_org_status', 'org_id', 'status'),
    )

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
        return f'<HiCurtailmentPlan {self.id}: {self.name} ({self.status})>'


class HiCurtailmentAction(db.Model):
    __tablename__ = 'hi_curtailment_actions'

    id = db.Column(db.Integer, primary_key=True)
    plan_id = db.Column(db.Integer, db.ForeignKey('hi_curtailment_plans.id'), nullable=False, index=True)
    org_id = db.Column(db.Integer, db.ForeignKey('hi_orgs.id'), nullable=False, index=True)
    site_id = db.Column(db.Integer, db.ForeignKey('hosting_sites.id'), nullable=False, index=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('hi_tenants.id'), nullable=True, index=True)
    target_type = db.Column(db.String(20), nullable=False)
    target_id = db.Column(db.Integer, nullable=False)
    command_type = db.Column(db.String(20), nullable=False)
    command_payload_json = db.Column(db.JSON, nullable=True)
    status = db.Column(db.String(20), default='queued', index=True)
    ack_json = db.Column(db.JSON, nullable=True)
    request_id = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    org = db.relationship('HiOrg', backref='hi_curtailment_actions')
    tenant = db.relationship('HiTenant', backref='hi_curtailment_actions')

    __table_args__ = (
        db.Index('idx_hi_caction_plan_status', 'plan_id', 'status'),
        db.Index('idx_hi_caction_org_site', 'org_id', 'site_id'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'plan_id': self.plan_id,
            'org_id': self.org_id,
            'site_id': self.site_id,
            'tenant_id': self.tenant_id,
            'target_type': self.target_type,
            'target_id': self.target_id,
            'command_type': self.command_type,
            'command_payload_json': self.command_payload_json,
            'status': self.status,
            'ack_json': self.ack_json,
            'request_id': self.request_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f'<HiCurtailmentAction {self.id}: {self.command_type} -> {self.target_type}:{self.target_id}>'


class HiCurtailmentResult(db.Model):
    __tablename__ = 'hi_curtailment_results'

    id = db.Column(db.Integer, primary_key=True)
    plan_id = db.Column(db.Integer, db.ForeignKey('hi_curtailment_plans.id'), nullable=False, unique=True, index=True)
    org_id = db.Column(db.Integer, db.ForeignKey('hi_orgs.id'), nullable=False, index=True)
    site_id = db.Column(db.Integer, db.ForeignKey('hosting_sites.id'), nullable=False, index=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('hi_tenants.id'), nullable=True, index=True)
    before_snapshot_json = db.Column(db.JSON, nullable=True)
    after_snapshot_json = db.Column(db.JSON, nullable=True)
    actual_json = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    org = db.relationship('HiOrg', backref='hi_curtailment_results')
    tenant = db.relationship('HiTenant', backref='hi_curtailment_results')

    __table_args__ = (
        db.Index('idx_hi_cresult_org_site', 'org_id', 'site_id'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'plan_id': self.plan_id,
            'org_id': self.org_id,
            'site_id': self.site_id,
            'tenant_id': self.tenant_id,
            'before_snapshot_json': self.before_snapshot_json,
            'after_snapshot_json': self.after_snapshot_json,
            'actual_json': self.actual_json,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f'<HiCurtailmentResult {self.id}: plan={self.plan_id}>'


class HiCommandQueue(db.Model):
    __tablename__ = 'hi_command_queue'

    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('hi_orgs.id'), nullable=False, index=True)
    site_id = db.Column(db.Integer, db.ForeignKey('hosting_sites.id'), nullable=False, index=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('hi_tenants.id'), nullable=True, index=True)
    target_type = db.Column(db.String(20), nullable=False)
    target_id = db.Column(db.Integer, nullable=False)
    command_type = db.Column(db.String(30), nullable=False)
    payload_json = db.Column(db.JSON, nullable=True)
    status = db.Column(db.String(20), default='queued', index=True)
    request_id = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    org = db.relationship('HiOrg', backref='hi_command_queue')
    tenant = db.relationship('HiTenant', backref='hi_command_queue')

    __table_args__ = (
        db.Index('idx_hi_cmdq_org_site', 'org_id', 'site_id'),
        db.Index('idx_hi_cmdq_status', 'status', 'created_at'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'org_id': self.org_id,
            'site_id': self.site_id,
            'tenant_id': self.tenant_id,
            'target_type': self.target_type,
            'target_id': self.target_id,
            'command_type': self.command_type,
            'payload_json': self.payload_json,
            'status': self.status,
            'request_id': self.request_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f'<HiCommandQueue {self.id}: {self.command_type} -> {self.target_type}:{self.target_id} ({self.status})>'


class HiTariff(db.Model):
    __tablename__ = 'hi_tariffs'

    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('hi_orgs.id'), nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    tariff_type = db.Column(db.String(20), default='flat')
    params_json = db.Column(db.JSON, nullable=True)
    currency = db.Column(db.String(10), default='USD')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    contracts = db.relationship('HiContract', backref='hi_tariff', lazy='dynamic')

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
        return f'<HiTariff {self.id}: {self.name} ({self.tariff_type})>'


class HiContract(db.Model):
    __tablename__ = 'hi_contracts'

    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('hi_orgs.id'), nullable=False, index=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('hi_tenants.id'), nullable=False, index=True)
    site_id = db.Column(db.Integer, db.ForeignKey('hosting_sites.id'), nullable=False, index=True)
    tariff_id = db.Column(db.Integer, db.ForeignKey('hi_tariffs.id'), nullable=True, index=True)
    hosting_fee_type = db.Column(db.String(20), default='per_kw')
    hosting_fee_params_json = db.Column(db.JSON, nullable=True)
    curtailment_split_pct = db.Column(db.Float, default=0.0)
    billing_cycle = db.Column(db.String(20), default='monthly')
    effective_from = db.Column(db.DateTime, nullable=True)
    effective_to = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    invoices = db.relationship('HiInvoice', backref='hi_contract', lazy='dynamic')

    __table_args__ = (
        db.Index('idx_hi_contract_org_tenant', 'org_id', 'tenant_id'),
        db.Index('idx_hi_contract_org_site', 'org_id', 'site_id'),
    )

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
            'billing_cycle': self.billing_cycle,
            'effective_from': self.effective_from.isoformat() if self.effective_from else None,
            'effective_to': self.effective_to.isoformat() if self.effective_to else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f'<HiContract {self.id}: org={self.org_id} tenant={self.tenant_id}>'


class HiUsageRecord(db.Model):
    __tablename__ = 'hi_usage_records'

    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('hi_orgs.id'), nullable=False, index=True)
    site_id = db.Column(db.Integer, db.ForeignKey('hosting_sites.id'), nullable=False, index=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('hi_tenants.id'), nullable=False, index=True)
    period_start = db.Column(db.DateTime, nullable=False)
    period_end = db.Column(db.DateTime, nullable=False)
    kwh_estimated = db.Column(db.Float, default=0.0)
    avg_kw_estimated = db.Column(db.Float, default=0.0)
    method = db.Column(db.String(30), default='nominal_watts')
    evidence_json = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    org = db.relationship('HiOrg', backref='hi_usage_records')

    __table_args__ = (
        db.Index('idx_hi_usage_period', 'tenant_id', 'period_start', 'period_end'),
        db.Index('idx_hi_usage_org_site', 'org_id', 'site_id'),
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
        return f'<HiUsageRecord {self.id}: tenant={self.tenant_id} {self.period_start}-{self.period_end}>'


class HiInvoice(db.Model):
    __tablename__ = 'hi_invoices'

    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('hi_orgs.id'), nullable=False, index=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('hi_tenants.id'), nullable=False, index=True)
    contract_id = db.Column(db.Integer, db.ForeignKey('hi_contracts.id'), nullable=True, index=True)
    period_start = db.Column(db.DateTime, nullable=False)
    period_end = db.Column(db.DateTime, nullable=False)
    subtotal = db.Column(db.Float, default=0.0)
    total = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='draft', index=True)
    line_items_json = db.Column(db.JSON, nullable=True)
    evidence_json = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    org = db.relationship('HiOrg', backref='hi_invoices')

    __table_args__ = (
        db.Index('idx_hi_invoice_period', 'tenant_id', 'period_start', 'period_end'),
        db.Index('idx_hi_invoice_org_tenant', 'org_id', 'tenant_id'),
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
        return f'<HiInvoice {self.id}: tenant={self.tenant_id} total={self.total} ({self.status})>'
