"""add audit_logs table

Revision ID: 20260605_audit_log
Revises: 20260605_workspace_v2
Create Date: 2026-06-05
"""

from alembic import op
import sqlalchemy as sa

revision = '20260605_audit_log'
down_revision = '20260605_workspace_v2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.Column('user_id', sa.String(), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('workspace_id', sa.String(), sa.ForeignKey('workspaces.id'), nullable=True, index=True),
        sa.Column('action', sa.String(50), nullable=False, index=True),
        sa.Column('resource_type', sa.String(50), nullable=False),
        sa.Column('resource_id', sa.String(), nullable=True, index=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('details', sa.JSON(), server_default='{}'),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('audit_logs')
