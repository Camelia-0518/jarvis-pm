"""Add skill execution table

Revision ID: 20260411_160228
Revises:
Create Date: 2026-04-11 16:02:28

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql, sqlite

# revision identifiers, used by Alembic.
revision = '20260411_160228'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create skill_executions table with indexes"""

    # Detect database dialect
    dialect = op.get_context().dialect.name

    # Create skill_executions table
    op.create_table(
        'skill_executions',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('skill_id', sa.String(), nullable=False),
        sa.Column('workflow_id', sa.String(), nullable=True),
        sa.Column('project_id', sa.String(), nullable=True),
        sa.Column('inputs', sa.JSON(), nullable=True, default=dict),
        sa.Column('output', sa.JSON(), nullable=True),
        sa.Column('success', sa.Boolean(), default=True),
        sa.Column('execution_time_ms', sa.Integer(), default=0),
        sa.Column('token_usage', sa.JSON(), nullable=True, default=dict),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for common query patterns
    op.create_index('idx_skill_executions_skill_id', 'skill_executions', ['skill_id'])
    op.create_index('idx_skill_executions_workflow_id', 'skill_executions', ['workflow_id'])
    op.create_index('idx_skill_executions_project_id', 'skill_executions', ['project_id'])
    op.create_index('idx_skill_executions_created_at', 'skill_executions', ['created_at'])
    op.create_index('idx_skill_executions_success', 'skill_executions', ['success'])

    # Create composite index for common query: skill executions by project ordered by date
    op.create_index(
        'idx_skill_executions_project_created',
        'skill_executions',
        ['project_id', 'created_at']
    )

    # Create foreign key constraints (optional, based on existing tables)
    # Note: These will only work if the referenced tables exist
    try:
        op.create_foreign_key(
            'fk_skill_executions_project',
            'skill_executions', 'projects',
            ['project_id'], ['id'],
            ondelete='SET NULL'
        )
    except Exception:
        # Projects table might not exist, skip FK
        pass

    try:
        op.create_foreign_key(
            'fk_skill_executions_workflow',
            'skill_executions', 'workflows',
            ['workflow_id'], ['id'],
            ondelete='SET NULL'
        )
    except Exception:
        # Workflows table might not exist, skip FK
        pass

    # Database-specific optimizations
    if dialect == 'postgresql':
        # PostgreSQL: Create GIN index for JSON columns
        op.create_index(
            'idx_skill_executions_inputs_gin',
            'skill_executions',
            ['inputs'],
            postgresql_using='gin'
        )
        op.create_index(
            'idx_skill_executions_output_gin',
            'skill_executions',
            ['output'],
            postgresql_using='gin'
        )

    elif dialect == 'sqlite':
        # SQLite: No special JSON indexes, but we can add a comment
        pass


def downgrade() -> None:
    """Drop skill_executions table and indexes"""

    # Drop indexes first
    op.drop_index('idx_skill_executions_project_created', table_name='skill_executions')
    op.drop_index('idx_skill_executions_success', table_name='skill_executions')
    op.drop_index('idx_skill_executions_created_at', table_name='skill_executions')
    op.drop_index('idx_skill_executions_project_id', table_name='skill_executions')
    op.drop_index('idx_skill_executions_workflow_id', table_name='skill_executions')
    op.drop_index('idx_skill_executions_skill_id', table_name='skill_executions')

    # Drop PostgreSQL-specific indexes if they exist
    dialect = op.get_context().dialect.name
    if dialect == 'postgresql':
        try:
            op.drop_index('idx_skill_executions_output_gin', table_name='skill_executions')
            op.drop_index('idx_skill_executions_inputs_gin', table_name='skill_executions')
        except Exception:
            pass

    # Drop foreign keys if they exist
    try:
        op.drop_constraint('fk_skill_executions_workflow', 'skill_executions', type_='foreignkey')
    except Exception:
        pass

    try:
        op.drop_constraint('fk_skill_executions_project', 'skill_executions', type_='foreignkey')
    except Exception:
        pass

    # Drop table
    op.drop_table('skill_executions')
