"""add jobs table for async task lifecycle management

Revision ID: 20260605_jobs
Revises: 20260605_review
Create Date: 2026-06-05
"""

from alembic import op
import sqlalchemy as sa

revision = '20260605_jobs'
down_revision = '20260605_review'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'jobs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),

        sa.Column('job_type', sa.Enum('compliance_check', 're_review', 'prd_generation', 'prototype_generation', 'export', 'general', name='jobtype'), nullable=False, server_default='general'),
        sa.Column('status', sa.Enum('queued', 'running', 'succeeded', 'failed', name='jobstatus'), nullable=False, server_default='queued'),

        sa.Column('project_id', sa.String(), sa.ForeignKey('projects.id'), nullable=True, index=True),
        sa.Column('prd_id', sa.String(), sa.ForeignKey('prds.id'), nullable=True, index=True),
        sa.Column('task_id', sa.String(), sa.ForeignKey('prd_revision_tasks.id'), nullable=True, index=True),
        sa.Column('triggered_by', sa.String(), sa.ForeignKey('users.id'), nullable=False),

        sa.Column('input_data', sa.JSON(), server_default='{}'),
        sa.Column('output_data', sa.JSON(), server_default='{}'),
        sa.Column('result_summary', sa.Text(), nullable=True),

        sa.Column('attempt', sa.Integer(), server_default='1'),
        sa.Column('max_attempts', sa.Integer(), server_default='3'),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),

        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),

        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('jobs')
    op.execute('DROP TYPE IF EXISTS jobtype')
    op.execute('DROP TYPE IF EXISTS jobstatus')
