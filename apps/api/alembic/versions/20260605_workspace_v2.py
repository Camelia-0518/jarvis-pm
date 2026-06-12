"""add workspace_id to existing resource tables (SQLite batch-safe)

Revision ID: 20260605_workspace_v2
Revises: 20260605_workspace
Create Date: 2026-06-05
"""

from alembic import op
import sqlalchemy as sa

revision = '20260605_workspace_v2'
down_revision = '20260605_workspace'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # SQLite doesn't support ALTER with FK constraints — use batch mode.
    # After adding the column, we skip the FK so the column is just a plain
    # String that app-layer code resolves.  Index is still created.

    with op.batch_alter_table('projects') as batch:
        batch.add_column(sa.Column('workspace_id', sa.String(), nullable=True))
        batch.create_index('ix_projects_workspace_id', ['workspace_id'])

    with op.batch_alter_table('prds') as batch:
        batch.add_column(sa.Column('workspace_id', sa.String(), nullable=True))
        batch.create_index('ix_prds_workspace_id', ['workspace_id'])

    with op.batch_alter_table('jobs') as batch:
        batch.add_column(sa.Column('workspace_id', sa.String(), nullable=True))
        batch.create_index('ix_jobs_workspace_id', ['workspace_id'])


def downgrade() -> None:
    with op.batch_alter_table('jobs') as batch:
        batch.drop_index('ix_jobs_workspace_id')
        batch.drop_column('workspace_id')

    with op.batch_alter_table('prds') as batch:
        batch.drop_index('ix_prds_workspace_id')
        batch.drop_column('workspace_id')

    with op.batch_alter_table('projects') as batch:
        batch.drop_index('ix_projects_workspace_id')
        batch.drop_column('workspace_id')
