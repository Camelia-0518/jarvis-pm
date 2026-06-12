"""add workspaces and memberships tables

Revision ID: 20260605_workspace
Revises: 20260605_jobs_v2
Create Date: 2026-06-05
"""

from alembic import op
import sqlalchemy as sa

revision = '20260605_workspace'
down_revision = '20260605_jobs_v2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── workspaces ──
    op.create_table(
        'workspaces',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('slug', sa.String(50), unique=True, nullable=False, index=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('settings', sa.Text(), nullable=True),
        sa.Column('migrated_from_user_id', sa.String(), sa.ForeignKey('users.id'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )

    # ── memberships ──
    op.create_table(
        'memberships',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.Column('workspace_id', sa.String(), sa.ForeignKey('workspaces.id'), nullable=False, index=True),
        sa.Column('user_id', sa.String(), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('role', sa.Enum('owner', 'admin', 'editor', 'viewer', name='workspacerole'), nullable=False, server_default='editor'),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('1')),
        sa.Column('invited_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('joined_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('memberships')
    op.drop_table('workspaces')
    op.execute('DROP TYPE IF EXISTS workspacerole')
