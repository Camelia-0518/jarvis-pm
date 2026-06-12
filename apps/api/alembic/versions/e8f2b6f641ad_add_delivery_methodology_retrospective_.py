"""add delivery, methodology, retrospective, lesson, prd comment & revision task tables

Revision ID: e8f2b6f641ad
Revises: 20260411_160228
Create Date: 2026-06-03 13:47:50.899594

Adds 6 tables that were previously managed only by Base.metadata.create_all():
  - delivery_plans      (WBS, milestones, risks, RACI, etc.)
  - delivery_methodologies (Stage-Gate templates)
  - retrospectives      (project post-mortem)
  - lessons             (reusable lessons learned)
  - prd_comments        (chapter comments with @mentions)
  - prd_revision_tasks  (annotation-driven revision tasks with status flow)
"""

from alembic import op
import sqlalchemy as sa

revision = 'e8f2b6f641ad'
down_revision = '3d74fbcb1515'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- delivery_plans (depends on projects, prds, users) ---
    op.create_table(
        'delivery_plans',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('project_id', sa.String(), sa.ForeignKey('projects.id'), nullable=False),
        sa.Column('prd_id', sa.String(), sa.ForeignKey('prds.id'), nullable=True),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=True, server_default='draft'),
        sa.Column('industry', sa.String(), nullable=True, server_default='medical'),
        sa.Column('wbs', sa.JSON(), nullable=True),
        sa.Column('milestones', sa.JSON(), nullable=True),
        sa.Column('resources', sa.JSON(), nullable=True),
        sa.Column('gantt', sa.JSON(), nullable=True),
        sa.Column('risks', sa.JSON(), nullable=True),
        sa.Column('risk_matrix', sa.JSON(), nullable=True),
        sa.Column('risk_response_plan', sa.JSON(), nullable=True),
        sa.Column('stakeholders', sa.JSON(), nullable=True),
        sa.Column('raci', sa.JSON(), nullable=True),
        sa.Column('communication_plan', sa.JSON(), nullable=True),
        sa.Column('status_template', sa.JSON(), nullable=True),
        sa.Column('plan_markdown', sa.Text(), nullable=True, server_default=''),
        sa.Column('risk_markdown', sa.Text(), nullable=True, server_default=''),
        sa.Column('stakeholder_markdown', sa.Text(), nullable=True, server_default=''),
        sa.Column('ai_generated', sa.JSON(), nullable=True),
        sa.Column('created_by', sa.String(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )

    # --- delivery_methodologies (depends on users) ---
    op.create_table(
        'delivery_methodologies',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True, server_default=''),
        sa.Column('industry', sa.String(), nullable=True, server_default='general'),
        sa.Column('stages', sa.JSON(), nullable=True),
        sa.Column('best_practices', sa.JSON(), nullable=True),
        sa.Column('pitfalls', sa.JSON(), nullable=True),
        sa.Column('templates', sa.JSON(), nullable=True),
        sa.Column('created_by', sa.String(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )

    # --- retrospectives (depends on projects, users) ---
    op.create_table(
        'retrospectives',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('project_id', sa.String(), sa.ForeignKey('projects.id'), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('what_went_well', sa.Text(), nullable=True, server_default=''),
        sa.Column('what_went_wrong', sa.Text(), nullable=True, server_default=''),
        sa.Column('surprises', sa.Text(), nullable=True, server_default=''),
        sa.Column('key_decisions', sa.JSON(), nullable=True),
        sa.Column('planned_days', sa.Float(), nullable=True),
        sa.Column('actual_days', sa.Float(), nullable=True),
        sa.Column('planned_budget', sa.Float(), nullable=True),
        sa.Column('actual_budget', sa.Float(), nullable=True),
        sa.Column('lessons', sa.JSON(), nullable=True),
        sa.Column('ai_analysis', sa.Text(), nullable=True, server_default=''),
        sa.Column('ai_suggestions', sa.JSON(), nullable=True),
        sa.Column('created_by', sa.String(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )

    # --- lessons (depends on projects, delivery_plans) ---
    op.create_table(
        'lessons',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('project_id', sa.String(), sa.ForeignKey('projects.id'), nullable=True),
        sa.Column('delivery_plan_id', sa.String(), sa.ForeignKey('delivery_plans.id'), nullable=True),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('category', sa.String(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('industry', sa.String(), nullable=True, server_default='medical'),
        sa.Column('source_type', sa.String(), nullable=True, server_default='ai_generated'),
        sa.Column('is_reusable', sa.JSON(), nullable=True),
        sa.Column('related_lessons', sa.JSON(), nullable=True),
        sa.Column('action_item', sa.Text(), nullable=True, server_default=''),
        sa.Column('severity', sa.String(), nullable=True, server_default='medium'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )

    # --- prd_comments (depends on prds, self, users) ---
    op.create_table(
        'prd_comments',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('prd_id', sa.String(), sa.ForeignKey('prds.id'), nullable=False),
        sa.Column('chapter_id', sa.String(), nullable=False),
        sa.Column('parent_id', sa.String(), sa.ForeignKey('prd_comments.id'), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('mentions', sa.Text(), nullable=True, server_default=''),
        sa.Column('created_by', sa.String(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )

    # --- prd_revision_tasks (depends on prds, prd_annotations, users) ---
    op.create_table(
        'prd_revision_tasks',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('prd_id', sa.String(), sa.ForeignKey('prds.id'), nullable=False),
        sa.Column('annotation_id', sa.String(), sa.ForeignKey('prd_annotations.id'), nullable=True),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True, server_default='todo'),
        sa.Column('assigned_to', sa.String(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_by', sa.String(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completion_note', sa.Text(), nullable=True),
        sa.Column('re_review_status', sa.String(length=20), nullable=True),
        sa.Column('re_review_result', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )

    # --- indexes for delivery_plans (performance-critical queries) ---
    op.create_index('idx_delivery_plans_project_id', 'delivery_plans', ['project_id'])
    op.create_index('idx_delivery_plans_prd_id', 'delivery_plans', ['prd_id'])
    op.create_index('idx_delivery_plans_status', 'delivery_plans', ['status'])
    op.create_index('idx_delivery_plans_created_by', 'delivery_plans', ['created_by'])
    op.create_index('idx_delivery_plans_created_at', 'delivery_plans', ['created_at'])


def downgrade() -> None:
    # indexes are dropped automatically with tables in SQLite;
    # for PostgreSQL they'd need explicit op.drop_index calls.
    op.drop_index('idx_delivery_plans_created_at', table_name='delivery_plans')
    op.drop_index('idx_delivery_plans_created_by', table_name='delivery_plans')
    op.drop_index('idx_delivery_plans_status', table_name='delivery_plans')
    op.drop_index('idx_delivery_plans_prd_id', table_name='delivery_plans')
    op.drop_index('idx_delivery_plans_project_id', table_name='delivery_plans')
    op.drop_table('prd_revision_tasks')
    op.drop_table('prd_comments')
    op.drop_table('lessons')
    op.drop_table('retrospectives')
    op.drop_table('delivery_methodologies')
    op.drop_table('delivery_plans')
