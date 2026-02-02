"""baseline initial schema

Revision ID: baseline_001
Revises: 
Create Date: 2026-02-01 00:00:00.000000

This is the baseline migration representing the existing database schema.
For existing databases, run: alembic stamp baseline_001
For new databases, this migration will create all tables.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'baseline_001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Baseline migration - represents existing schema.
    
    This migration is intentionally empty for existing databases.
    The actual schema is managed by SQLAlchemy models and db.create_all().
    
    For new databases:
    1. Run: python -c "from app import app, db; app.app_context().push(); db.create_all()"
    2. Then: alembic stamp baseline_001
    
    Future migrations will use Alembic autogenerate.
    """
    pass


def downgrade() -> None:
    """
    Downgrade is not supported for baseline migration.
    This would require dropping all tables which is destructive.
    """
    raise NotImplementedError(
        "Cannot downgrade from baseline. "
        "To reset the database, drop all tables manually and re-run db.create_all()."
    )
