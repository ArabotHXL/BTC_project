"""hi tables

Revision ID: a1b2c3d4e5f6
Revises: baseline_001
Create Date: 2026-02-21 00:01:00.000000

Creates all hi_* tables for the HashInsight hosting-insight module,
adds hi_org_id to hosting_sites, hi_tenant_id and nominal_watts to miners,
and backfills a self-mining org/tenant.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'baseline_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'hi_orgs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('org_type', sa.String(20), server_default='self'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), index=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()')),
    )

    op.create_table(
        'hi_tenants',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('org_id', sa.Integer(), sa.ForeignKey('hi_orgs.id'), nullable=False, index=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('tenant_type', sa.String(20), server_default='self'),
        sa.Column('status', sa.String(20), server_default='active', index=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), index=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()')),
    )
    op.create_index('idx_hi_tenant_org_status', 'hi_tenants', ['org_id', 'status'])

    op.create_table(
        'hi_groups',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('site_id', sa.Integer(), sa.ForeignKey('hosting_sites.id'), nullable=False, index=True),
        sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('hi_tenants.id'), nullable=True, index=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('selector_json', sa.JSON(), nullable=True),
        sa.Column('priority', sa.Integer(), server_default='100'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), index=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()')),
    )
    op.create_index('idx_hi_group_site_tenant', 'hi_groups', ['site_id', 'tenant_id'])

    op.create_table(
        'hi_audit_log',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('org_id', sa.Integer(), sa.ForeignKey('hi_orgs.id'), nullable=True, index=True),
        sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('hi_tenants.id'), nullable=True, index=True),
        sa.Column('actor_user_id', sa.Integer(), sa.ForeignKey('user_access.id'), nullable=True, index=True),
        sa.Column('action_type', sa.String(50), nullable=False, index=True),
        sa.Column('entity_type', sa.String(50), nullable=True),
        sa.Column('entity_id', sa.String(50), nullable=True),
        sa.Column('request_id', sa.String(100), nullable=True),
        sa.Column('detail_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), index=True),
    )
    op.create_index('idx_hi_audit_org_action', 'hi_audit_log', ['org_id', 'action_type'])
    op.create_index('idx_hi_audit_entity', 'hi_audit_log', ['entity_type', 'entity_id'])

    op.create_table(
        'hi_curtailment_plans',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('org_id', sa.Integer(), sa.ForeignKey('hi_orgs.id'), nullable=False, index=True),
        sa.Column('site_id', sa.Integer(), sa.ForeignKey('hosting_sites.id'), nullable=False, index=True),
        sa.Column('tenant_scope', sa.String(20), server_default='site_wide'),
        sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('hi_tenants.id'), nullable=True, index=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('objective', sa.String(20), server_default='save_cost'),
        sa.Column('inputs_json', sa.JSON(), nullable=True),
        sa.Column('expected_json', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(20), server_default='draft', index=True),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('user_access.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), index=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()')),
    )
    op.create_index('idx_hi_cplan_org_site', 'hi_curtailment_plans', ['org_id', 'site_id'])
    op.create_index('idx_hi_cplan_org_status', 'hi_curtailment_plans', ['org_id', 'status'])

    op.create_table(
        'hi_curtailment_actions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('plan_id', sa.Integer(), sa.ForeignKey('hi_curtailment_plans.id'), nullable=False, index=True),
        sa.Column('org_id', sa.Integer(), sa.ForeignKey('hi_orgs.id'), nullable=False, index=True),
        sa.Column('site_id', sa.Integer(), sa.ForeignKey('hosting_sites.id'), nullable=False, index=True),
        sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('hi_tenants.id'), nullable=True, index=True),
        sa.Column('target_type', sa.String(20), nullable=False),
        sa.Column('target_id', sa.Integer(), nullable=False),
        sa.Column('command_type', sa.String(20), nullable=False),
        sa.Column('command_payload_json', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(20), server_default='queued', index=True),
        sa.Column('ack_json', sa.JSON(), nullable=True),
        sa.Column('request_id', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), index=True),
    )
    op.create_index('idx_hi_caction_plan_status', 'hi_curtailment_actions', ['plan_id', 'status'])
    op.create_index('idx_hi_caction_org_site', 'hi_curtailment_actions', ['org_id', 'site_id'])

    op.create_table(
        'hi_curtailment_results',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('plan_id', sa.Integer(), sa.ForeignKey('hi_curtailment_plans.id'), nullable=False, unique=True, index=True),
        sa.Column('org_id', sa.Integer(), sa.ForeignKey('hi_orgs.id'), nullable=False, index=True),
        sa.Column('site_id', sa.Integer(), sa.ForeignKey('hosting_sites.id'), nullable=False, index=True),
        sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('hi_tenants.id'), nullable=True, index=True),
        sa.Column('before_snapshot_json', sa.JSON(), nullable=True),
        sa.Column('after_snapshot_json', sa.JSON(), nullable=True),
        sa.Column('actual_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), index=True),
    )
    op.create_index('idx_hi_cresult_org_site', 'hi_curtailment_results', ['org_id', 'site_id'])

    op.create_table(
        'hi_command_queue',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('org_id', sa.Integer(), sa.ForeignKey('hi_orgs.id'), nullable=False, index=True),
        sa.Column('site_id', sa.Integer(), sa.ForeignKey('hosting_sites.id'), nullable=False, index=True),
        sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('hi_tenants.id'), nullable=True, index=True),
        sa.Column('target_type', sa.String(20), nullable=False),
        sa.Column('target_id', sa.Integer(), nullable=False),
        sa.Column('command_type', sa.String(30), nullable=False),
        sa.Column('payload_json', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(20), server_default='queued', index=True),
        sa.Column('request_id', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), index=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()')),
    )
    op.create_index('idx_hi_cmdq_org_site', 'hi_command_queue', ['org_id', 'site_id'])
    op.create_index('idx_hi_cmdq_status', 'hi_command_queue', ['status', 'created_at'])

    op.create_table(
        'hi_tariffs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('org_id', sa.Integer(), sa.ForeignKey('hi_orgs.id'), nullable=False, index=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('tariff_type', sa.String(20), server_default='flat'),
        sa.Column('params_json', sa.JSON(), nullable=True),
        sa.Column('currency', sa.String(10), server_default='USD'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), index=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()')),
    )

    op.create_table(
        'hi_contracts',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('org_id', sa.Integer(), sa.ForeignKey('hi_orgs.id'), nullable=False, index=True),
        sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('hi_tenants.id'), nullable=False, index=True),
        sa.Column('site_id', sa.Integer(), sa.ForeignKey('hosting_sites.id'), nullable=False, index=True),
        sa.Column('tariff_id', sa.Integer(), sa.ForeignKey('hi_tariffs.id'), nullable=True, index=True),
        sa.Column('hosting_fee_type', sa.String(20), server_default='per_kw'),
        sa.Column('hosting_fee_params_json', sa.JSON(), nullable=True),
        sa.Column('curtailment_split_pct', sa.Float(), server_default='0.0'),
        sa.Column('billing_cycle', sa.String(20), server_default='monthly'),
        sa.Column('effective_from', sa.DateTime(), nullable=True),
        sa.Column('effective_to', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), index=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()')),
    )
    op.create_index('idx_hi_contract_org_tenant', 'hi_contracts', ['org_id', 'tenant_id'])
    op.create_index('idx_hi_contract_org_site', 'hi_contracts', ['org_id', 'site_id'])

    op.create_table(
        'hi_usage_records',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('org_id', sa.Integer(), sa.ForeignKey('hi_orgs.id'), nullable=False, index=True),
        sa.Column('site_id', sa.Integer(), sa.ForeignKey('hosting_sites.id'), nullable=False, index=True),
        sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('hi_tenants.id'), nullable=False, index=True),
        sa.Column('period_start', sa.DateTime(), nullable=False),
        sa.Column('period_end', sa.DateTime(), nullable=False),
        sa.Column('kwh_estimated', sa.Float(), server_default='0.0'),
        sa.Column('avg_kw_estimated', sa.Float(), server_default='0.0'),
        sa.Column('method', sa.String(30), server_default='nominal_watts'),
        sa.Column('evidence_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), index=True),
    )
    op.create_index('idx_hi_usage_period', 'hi_usage_records', ['tenant_id', 'period_start', 'period_end'])
    op.create_index('idx_hi_usage_org_site', 'hi_usage_records', ['org_id', 'site_id'])

    op.create_table(
        'hi_invoices',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('org_id', sa.Integer(), sa.ForeignKey('hi_orgs.id'), nullable=False, index=True),
        sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('hi_tenants.id'), nullable=False, index=True),
        sa.Column('contract_id', sa.Integer(), sa.ForeignKey('hi_contracts.id'), nullable=True, index=True),
        sa.Column('period_start', sa.DateTime(), nullable=False),
        sa.Column('period_end', sa.DateTime(), nullable=False),
        sa.Column('subtotal', sa.Float(), server_default='0.0'),
        sa.Column('total', sa.Float(), server_default='0.0'),
        sa.Column('status', sa.String(20), server_default='draft', index=True),
        sa.Column('line_items_json', sa.JSON(), nullable=True),
        sa.Column('evidence_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), index=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()')),
    )
    op.create_index('idx_hi_invoice_period', 'hi_invoices', ['tenant_id', 'period_start', 'period_end'])
    op.create_index('idx_hi_invoice_org_tenant', 'hi_invoices', ['org_id', 'tenant_id'])

    op.add_column('hosting_sites', sa.Column('hi_org_id', sa.Integer(), sa.ForeignKey('hi_orgs.id'), nullable=True))
    op.add_column('miners', sa.Column('hi_tenant_id', sa.Integer(), sa.ForeignKey('hi_tenants.id'), nullable=True))
    op.add_column('miners', sa.Column('nominal_watts', sa.Float(), nullable=True))

    op.execute(
        "INSERT INTO hi_orgs (name, org_type) VALUES ('HashInsight Self-Mining', 'self')"
    )
    op.execute(
        "INSERT INTO hi_tenants (org_id, name, tenant_type, status) "
        "VALUES ((SELECT id FROM hi_orgs WHERE org_type='self' LIMIT 1), "
        "'Self-Mining Operations', 'self', 'active')"
    )

    op.execute(
        "UPDATE hosting_sites SET hi_org_id = "
        "(SELECT id FROM hi_orgs WHERE org_type='self' LIMIT 1) "
        "WHERE hi_org_id IS NULL"
    )
    op.execute(
        "UPDATE miners SET hi_tenant_id = "
        "(SELECT id FROM hi_tenants WHERE tenant_type='self' LIMIT 1) "
        "WHERE hi_tenant_id IS NULL"
    )

    op.alter_column('hosting_sites', 'hi_org_id', nullable=False)
    op.alter_column('miners', 'hi_tenant_id', nullable=False)


def downgrade() -> None:
    op.drop_column('miners', 'nominal_watts')
    op.drop_column('miners', 'hi_tenant_id')
    op.drop_column('hosting_sites', 'hi_org_id')

    op.drop_table('hi_invoices')
    op.drop_table('hi_usage_records')
    op.drop_table('hi_contracts')
    op.drop_table('hi_tariffs')
    op.drop_table('hi_command_queue')
    op.drop_table('hi_curtailment_results')
    op.drop_table('hi_curtailment_actions')
    op.drop_table('hi_curtailment_plans')
    op.drop_table('hi_audit_log')
    op.drop_table('hi_groups')
    op.drop_table('hi_tenants')
    op.drop_table('hi_orgs')
