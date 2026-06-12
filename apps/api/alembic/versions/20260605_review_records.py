"""add review_records table

Revision ID: 20260605_review
Revises: e8f2b6f641ad
Create Date: 2026-06-05

迁移 project.settings 中零散的评审 JSON 到独立的 review_records 表，
支持检查清单评审、AI 合规评审、再评审的统一存储和历史查询。
"""

from alembic import op
import sqlalchemy as sa

revision = '20260605_review'
down_revision = 'e8f2b6f641ad'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'review_records',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),

        sa.Column('project_id', sa.String(), sa.ForeignKey('projects.id'), nullable=False, index=True),
        sa.Column('prd_id', sa.String(), sa.ForeignKey('prds.id'), nullable=True, index=True),
        sa.Column('revision_task_id', sa.String(), sa.ForeignKey('prd_revision_tasks.id'), nullable=True, index=True),

        sa.Column('review_type', sa.Enum('checklist', 'compliance', 're_review', name='reviewtype'), nullable=False, server_default='checklist'),
        sa.Column('status', sa.Enum('completed', 'pending', 'failed', name='reviewstatus'), nullable=False, server_default='completed'),
        sa.Column('industry', sa.String(), server_default='default'),
        sa.Column('trigger_source', sa.String(), server_default='manual'),

        sa.Column('total_items', sa.Integer(), server_default='0'),
        sa.Column('checked_count', sa.Integer(), server_default='0'),
        sa.Column('required_items', sa.Integer(), server_default='0'),
        sa.Column('required_checked', sa.Integer(), server_default='0'),
        sa.Column('all_required_passed', sa.Integer(), server_default='0'),

        sa.Column('items', sa.JSON(), server_default='[]'),
        sa.Column('score', sa.Float(), nullable=True),
        sa.Column('result_summary', sa.Text(), nullable=True),

        sa.Column('submitted_by', sa.String(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True),

        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('review_records')
    op.execute('DROP TYPE IF EXISTS reviewtype')
    op.execute('DROP TYPE IF EXISTS reviewstatus')
