"""Baseline tables: users, projects, prds, annotations, versions, battles,
personas, competitors, requirements, feedback, memory, templates, prompt_templates.

Revision ID: 3d74fbcb1515
Revises: 20260411_160228 (skill_executions)
Create Date: 2026-06-03

All 14 tables that were previously created only via Base.metadata.create_all().
FK order: users → projects → prds → everything else.
"""

from alembic import op
import sqlalchemy as sa

revision = '3d74fbcb1515'
down_revision = '20260411_160228'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ---- Tier 0: users (standalone) ----
    op.create_table(
        'users',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('avatar', sa.String(), nullable=True),
        sa.Column('role', sa.String(), nullable=True, server_default='member'),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default=sa.text('1')),
        sa.Column('preferences', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email', name='uq_users_email'),
    )
    op.create_index('idx_users_role', 'users', ['role'])
    # skill_executions indexes: already inline via Column(index=True) in migration 20260411_160228

    # ---- Tier 1: projects (FK → users) ----
    op.create_table(
        'projects',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('created_by', sa.String(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('industry', sa.String(), nullable=True, server_default='other'),
        sa.Column('status', sa.String(), nullable=True, server_default='active'),
        sa.Column('settings', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_projects_created_by', 'projects', ['created_by'])
    op.create_index('idx_projects_status', 'projects', ['status'])
    op.create_index('idx_projects_created_at', 'projects', ['created_at'])
    op.create_index('idx_projects_industry', 'projects', ['industry'])
    op.create_index('idx_projects_status_created', 'projects', ['status', 'created_at'])

    # ---- Tier 2: prds (FK → projects, users) ----
    op.create_table(
        'prds',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('project_id', sa.String(), sa.ForeignKey('projects.id'), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('version', sa.String(), nullable=True, server_default='1.0'),
        sa.Column('status', sa.String(), nullable=True, server_default='draft'),
        sa.Column('content', sa.JSON(), nullable=True),
        sa.Column('markdown', sa.Text(), nullable=True, server_default=''),
        sa.Column('ai_generated', sa.JSON(), nullable=True),
        sa.Column('created_by', sa.String(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_prds_project_id', 'prds', ['project_id'])
    op.create_index('idx_prds_created_by', 'prds', ['created_by'])
    op.create_index('idx_prds_status', 'prds', ['status'])
    op.create_index('idx_prds_created_at', 'prds', ['created_at'])
    op.create_index('idx_prds_project_status', 'prds', ['project_id', 'status'])

    # ---- Tier 3: prd_annotations (FK → prds, self, users) ----
    # revision_task_id is a plain column here — the FK to prd_revision_tasks
    # is deferred to migration e8f2b6f641ad where that table is created.
    op.create_table(
        'prd_annotations',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('prd_id', sa.String(), sa.ForeignKey('prds.id'), nullable=False),
        sa.Column('parent_id', sa.String(), sa.ForeignKey('prd_annotations.id'), nullable=True),
        sa.Column('chapter_num', sa.String(), nullable=True),
        sa.Column('chapter_title', sa.String(), nullable=True),
        sa.Column('line_index', sa.Integer(), nullable=True),
        sa.Column('selected_text', sa.Text(), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('annotation_type', sa.String(), nullable=True, server_default='comment'),
        sa.Column('status', sa.String(), nullable=True, server_default='open'),
        sa.Column('revision_task_id', sa.String(), nullable=True),
        sa.Column('created_by', sa.String(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolved_by', sa.String(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )

    # ---- Tier 3 continued: tables depending on users / projects / prds ----

    op.create_table(
        'prd_versions',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('prd_id', sa.String(), sa.ForeignKey('prds.id'), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('markdown', sa.Text(), nullable=True, server_default=''),
        sa.Column('content', sa.Text(), nullable=True, server_default=''),
        sa.Column('change_summary', sa.String(), nullable=True),
        sa.Column('created_by', sa.String(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_prd_versions_prd_id', 'prd_versions', ['prd_id'])
    op.create_index('idx_prd_versions_created_by', 'prd_versions', ['created_by'])

    op.create_table(
        'battles',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('created_by', sa.String(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('project_id', sa.String(), sa.ForeignKey('projects.id'), nullable=True),
        sa.Column('prd_id', sa.String(), sa.ForeignKey('prds.id'), nullable=True),
        sa.Column('status', sa.String(), nullable=True, server_default='active'),
        sa.Column('current_day', sa.Integer(), nullable=True, server_default='1'),
        sa.Column('total_days', sa.Integer(), nullable=True, server_default='5'),
        sa.Column('days', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_battles_project_id', 'battles', ['project_id'])
    op.create_index('idx_battles_prd_id', 'battles', ['prd_id'])
    op.create_index('idx_battles_created_by', 'battles', ['created_by'])

    op.create_table(
        'personas',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('project_id', sa.String(), sa.ForeignKey('projects.id'), nullable=False),
        sa.Column('created_by', sa.String(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('role', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('pain_points', sa.Text(), nullable=True),
        sa.Column('goals', sa.Text(), nullable=True),
        sa.Column('scenarios', sa.Text(), nullable=True),
        sa.Column('demographics', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_personas_created_by', 'personas', ['created_by'])

    op.create_table(
        'competitors',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('project_id', sa.String(), sa.ForeignKey('projects.id'), nullable=False),
        sa.Column('created_by', sa.String(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('strengths', sa.Text(), nullable=True),
        sa.Column('weaknesses', sa.Text(), nullable=True),
        sa.Column('features', sa.JSON(), nullable=True),
        sa.Column('pricing', sa.Text(), nullable=True),
        sa.Column('market_position', sa.Text(), nullable=True),
        sa.Column('source', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_competitors_created_by', 'competitors', ['created_by'])

    op.create_table(
        'requirements',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('project_id', sa.String(), sa.ForeignKey('projects.id'), nullable=False),
        sa.Column('created_by', sa.String(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(), nullable=True, server_default='backlog'),
        sa.Column('priority', sa.String(), nullable=True, server_default='p1'),
        sa.Column('rice_reach', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('rice_impact', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('rice_confidence', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('rice_effort', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('rice_score', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('kano_category', sa.String(), nullable=True, server_default=''),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_requirements_created_by', 'requirements', ['created_by'])
    op.create_index('idx_requirements_status', 'requirements', ['status'])

    # ---- Tier 4: tables with no or weak FK dependencies ----

    op.create_table(
        'feedback',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('category', sa.String(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('rating', sa.Integer(), nullable=True),
        sa.Column('context', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_feedback_user_id', 'feedback', ['user_id'])
    op.create_index('idx_feedback_category', 'feedback', ['category'])
    op.create_index('idx_feedback_created_at', 'feedback', ['created_at'])

    op.create_table(
        'memory_entries',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('memory_type', sa.String(length=50), nullable=False),
        sa.Column('content', sa.JSON(), nullable=False),
        sa.Column('tags', sa.JSON(), nullable=False),
        sa.Column('project_id', sa.String(length=36), nullable=True),
        sa.Column('importance', sa.Float(), nullable=False, server_default='5.0'),
        sa.Column('access_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'memory_chunks',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('source_type', sa.String(), nullable=False),
        sa.Column('source_id', sa.String(), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('embedding', sa.Text(), nullable=True),
        sa.Column('chunk_metadata', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_memory_chunks_source', 'memory_chunks', ['source_type', 'source_id'])
    op.create_index('idx_memory_chunks_created', 'memory_chunks', ['created_at'])

    op.create_table(
        'templates',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('industry', sa.String(), nullable=True, server_default='other'),
        sa.Column('chapters', sa.JSON(), nullable=True),
        sa.Column('icon', sa.String(), nullable=True, server_default='📄'),
        sa.Column('color', sa.String(), nullable=True, server_default='bg-slate-500'),
        sa.Column('is_builtin', sa.Boolean(), nullable=True, server_default=sa.text('0')),
        sa.Column('created_by', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'prompt_templates',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('version', sa.String(), nullable=False, server_default='1.0'),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default=sa.text('0')),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('created_by', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', 'version', name='uq_prompt_templates_name_version'),
    )
    op.create_index('idx_prompt_templates_name', 'prompt_templates', ['name'])
    op.create_index('idx_prompt_templates_active', 'prompt_templates', ['is_active'])


def downgrade() -> None:
    op.drop_table('prompt_templates')
    op.drop_table('templates')
    op.drop_table('memory_chunks')
    op.drop_table('memory_entries')
    op.drop_table('feedback')
    op.drop_table('requirements')
    op.drop_table('competitors')
    op.drop_table('personas')
    op.drop_table('battles')
    op.drop_table('prd_versions')
    op.drop_table('prd_annotations')
    op.drop_table('prds')
    op.drop_table('projects')
    op.drop_index('idx_users_role', table_name='users')
    # uq_users_email is an inline UniqueConstraint — dropped with the table
    op.drop_table('users')
