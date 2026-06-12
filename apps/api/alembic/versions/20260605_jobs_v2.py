"""add failure_type, error_code, next_retry_at to jobs table

Revision ID: 20260605_jobs_v2
Revises: 20260605_jobs
Create Date: 2026-06-05
"""

from alembic import op
import sqlalchemy as sa

revision = '20260605_jobs_v2'
down_revision = '20260605_jobs'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('jobs', sa.Column('failure_type', sa.Enum('business', 'system', 'timeout', 'cancelled', name='failuretype'), nullable=True))
    op.add_column('jobs', sa.Column('error_code', sa.String(50), nullable=True))
    op.add_column('jobs', sa.Column('retry_backoff_seconds', sa.Integer(), nullable=True))
    op.add_column('jobs', sa.Column('next_retry_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('jobs', 'next_retry_at')
    op.drop_column('jobs', 'retry_backoff_seconds')
    op.drop_column('jobs', 'error_code')
    op.drop_column('jobs', 'failure_type')
    op.execute('DROP TYPE IF EXISTS failuretype')
