"""hi_tenant_memberships table

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2026-02-21 00:02:00.000000

Creates hi_tenant_memberships table for user-tenant bindings,
enabling membership-based tenant resolution and role overrides.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'b2c3d4e5f6g7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'hi_tenant_memberships',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('user_access.id'), nullable=False),
        sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('hi_tenants.id'), nullable=False),
        sa.Column('member_role', sa.String(30), server_default='tenant_viewer', nullable=False),
        sa.Column('is_default', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    op.create_index('ix_hi_tenant_memberships_user_id', 'hi_tenant_memberships', ['user_id'])
    op.create_index('ix_hi_tenant_memberships_tenant_id', 'hi_tenant_memberships', ['tenant_id'])
    op.create_unique_constraint(
        'uq_hi_membership_user_tenant',
        'hi_tenant_memberships',
        ['user_id', 'tenant_id']
    )
    op.create_index(
        'idx_hi_membership_user_default',
        'hi_tenant_memberships',
        ['user_id', 'is_default']
    )


def downgrade() -> None:
    op.drop_index('idx_hi_membership_user_default', table_name='hi_tenant_memberships')
    op.drop_constraint('uq_hi_membership_user_tenant', 'hi_tenant_memberships', type_='unique')
    op.drop_index('ix_hi_tenant_memberships_tenant_id', table_name='hi_tenant_memberships')
    op.drop_index('ix_hi_tenant_memberships_user_id', table_name='hi_tenant_memberships')
    op.drop_table('hi_tenant_memberships')
