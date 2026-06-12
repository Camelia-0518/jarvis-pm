"""Database configuration with connection pooling and optimizations"""

import logging
import re

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool, QueuePool
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)
INDEX_TARGET_RE = re.compile(r"\bON\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", re.IGNORECASE)

# Create async engine with connection pooling
if settings.DEBUG:
    # Development: Use NullPool for SQLite or simple pooling
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG,
        poolclass=NullPool,
    )
else:
    # Production: Use QueuePool with optimized settings
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG,
        poolclass=QueuePool,
        pool_size=20,              # Base pool size
        max_overflow=10,           # Max overflow connections
        pool_pre_ping=True,        # Verify connections before using
        pool_recycle=3600,         # Recycle connections after 1 hour
        pool_timeout=60,           # Timeout for getting connection from pool
    )

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Base model
Base = declarative_base()


async def get_db():
    """Get database session with automatic cleanup"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_db_transaction():
    """Get database session for manual transaction control"""
    session = AsyncSessionLocal()
    try:
        yield session
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def init_db():
    """Initialize database: connection settings + conditional schema creation.

    In DEBUG mode: creates tables via ``Base.metadata.create_all`` and seeds
    builtin data.  In production: only sets up connection-level settings
    (WAL mode, etc.) — schema migration is handled by Alembic.
    """
    # Enable WAL mode for SQLite to allow concurrent reads during writes
    if "sqlite" in settings.DATABASE_URL:
        async with engine.begin() as conn:
            await conn.execute(text("PRAGMA journal_mode=WAL"))
            await conn.execute(text("PRAGMA synchronous=NORMAL"))
        logger.info("SQLite WAL mode enabled")

    if not settings.DEBUG:
        logger.info(
            "Production mode: skipping create_all (use Alembic migrations). "
            "Run 'alembic upgrade head' before starting the app."
        )
        return

    # --- DEBUG only below this point ---
    from app.models import (
        User,
        Project,
        PRD,
        SkillExecution,
        MemoryEntry,
        Feedback,
        PRDVersion,
        PRDAnnotation,
        PRDComment,
        MemoryChunk,
        Persona,
        Competitor,
        Template,
        PromptTemplate,
        PRDRevisionTask,
        DeliveryPlan,
        DeliveryMethodology,
        Retrospective,
        Lesson,
    )
    from app.api.v1.endpoints.templates import seed_builtin_templates

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables initialized")

    # Seed builtin templates
    async with AsyncSessionLocal() as session:
        try:
            await seed_builtin_templates(session)
            logger.info("Builtin templates seeded")
        except Exception as e:
            logger.warning(f"Failed to seed builtin templates: {e}")
            await session.rollback()

    # Seed builtin prompts
    from app.services.prompt_migration import seed_builtin_prompts
    async with AsyncSessionLocal() as session:
        try:
            await seed_builtin_prompts(session)
            logger.info("Builtin prompts seeded")
        except Exception as e:
            logger.warning(f"Failed to seed builtin prompts: {e}")
            await session.rollback()


async def close_db():
    """Close database connections"""
    await engine.dispose()
    logger.info("Database connections closed")


async def check_db_health() -> dict:
    """Check database health and return status"""
    try:
        async with AsyncSessionLocal() as session:
            # Test connection
            result = await session.execute(text("SELECT 1"))
            result.scalar()

            # Get connection info (PostgreSQL specific)
            if "postgresql" in settings.DATABASE_URL:
                version_result = await session.execute(text("SELECT version()"))
                version = version_result.scalar()

                # Get active connections
                conn_result = await session.execute(text(
                    "SELECT count(*) FROM pg_stat_activity WHERE datname = current_database()"
                ))
                connections = conn_result.scalar()

                return {
                    "status": "healthy",
                    "database": "postgresql",
                    "version": version.split()[1] if version else "unknown",
                    "active_connections": connections
                }
            else:
                return {
                    "status": "healthy",
                    "database": "sqlite"
                }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }


# ============== Database Index Management ==============

INDEX_DEFINITIONS = {
    # Project indexes
    "idx_projects_created_by": "CREATE INDEX IF NOT EXISTS idx_projects_created_by ON projects(created_by)",
    "idx_projects_status": "CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status)",
    "idx_projects_created_at": "CREATE INDEX IF NOT EXISTS idx_projects_created_at ON projects(created_at DESC)",
    "idx_projects_industry": "CREATE INDEX IF NOT EXISTS idx_projects_industry ON projects(industry)",

    # PRD indexes
    "idx_prds_project_id": "CREATE INDEX IF NOT EXISTS idx_prds_project_id ON prds(project_id)",
    "idx_prds_created_by": "CREATE INDEX IF NOT EXISTS idx_prds_created_by ON prds(created_by)",
    "idx_prds_status": "CREATE INDEX IF NOT EXISTS idx_prds_status ON prds(status)",
    "idx_prds_created_at": "CREATE INDEX IF NOT EXISTS idx_prds_created_at ON prds(created_at DESC)",

    # User indexes
    "idx_users_email": "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users(email)",
    "idx_users_role": "CREATE INDEX IF NOT EXISTS idx_users_role ON users(role)",

    # Skill execution indexes
    "idx_skill_executions_skill_id": "CREATE INDEX IF NOT EXISTS idx_skill_executions_skill_id ON skill_executions(skill_id)",
    "idx_skill_executions_workflow_id": "CREATE INDEX IF NOT EXISTS idx_skill_executions_workflow_id ON skill_executions(workflow_id)",
    "idx_skill_executions_project_id": "CREATE INDEX IF NOT EXISTS idx_skill_executions_project_id ON skill_executions(project_id)",
    "idx_skill_executions_created_at": "CREATE INDEX IF NOT EXISTS idx_skill_executions_created_at ON skill_executions(created_at)",
    "idx_skill_executions_success": "CREATE INDEX IF NOT EXISTS idx_skill_executions_success ON skill_executions(success)",
    "idx_skill_executions_project_created": "CREATE INDEX IF NOT EXISTS idx_skill_executions_project_created ON skill_executions(project_id, created_at)",

    # Memory chunk indexes
    "idx_memory_chunks_source": "CREATE INDEX IF NOT EXISTS idx_memory_chunks_source ON memory_chunks(source_type, source_id)",
    "idx_memory_chunks_created": "CREATE INDEX IF NOT EXISTS idx_memory_chunks_created ON memory_chunks(created_at)",

    # Feedback indexes
    "idx_feedback_user_id": "CREATE INDEX IF NOT EXISTS idx_feedback_user_id ON feedback(user_id)",
    "idx_feedback_category": "CREATE INDEX IF NOT EXISTS idx_feedback_category ON feedback(category)",
    "idx_feedback_created_at": "CREATE INDEX IF NOT EXISTS idx_feedback_created_at ON feedback(created_at DESC)",

    # PRD version indexes
    "idx_prd_versions_prd_id": "CREATE INDEX IF NOT EXISTS idx_prd_versions_prd_id ON prd_versions(prd_id)",
    "idx_prd_versions_created_by": "CREATE INDEX IF NOT EXISTS idx_prd_versions_created_by ON prd_versions(created_by)",

    # Persona indexes
    "idx_personas_created_by": "CREATE INDEX IF NOT EXISTS idx_personas_created_by ON personas(created_by)",

    # Competitor indexes
    "idx_competitors_created_by": "CREATE INDEX IF NOT EXISTS idx_competitors_created_by ON competitors(created_by)",

    # Requirement indexes
    "idx_requirements_created_by": "CREATE INDEX IF NOT EXISTS idx_requirements_created_by ON requirements(created_by)",
    "idx_requirements_status": "CREATE INDEX IF NOT EXISTS idx_requirements_status ON requirements(status)",

    # Composite indexes for common query patterns
    "idx_prds_project_status": "CREATE INDEX IF NOT EXISTS idx_prds_project_status ON prds(project_id, status)",
    "idx_projects_status_created": "CREATE INDEX IF NOT EXISTS idx_projects_status_created ON projects(status, created_at DESC)",

    # Prompt template indexes
    "idx_prompt_templates_name": "CREATE INDEX IF NOT EXISTS idx_prompt_templates_name ON prompt_templates(name)",
    "idx_prompt_templates_active": "CREATE INDEX IF NOT EXISTS idx_prompt_templates_active ON prompt_templates(is_active)",
    "idx_prompt_templates_name_version": "CREATE UNIQUE INDEX IF NOT EXISTS idx_prompt_templates_name_version ON prompt_templates(name, version)",

    # Delivery plan indexes
    "idx_delivery_plans_project_id": "CREATE INDEX IF NOT EXISTS idx_delivery_plans_project_id ON delivery_plans(project_id)",
    "idx_delivery_plans_prd_id": "CREATE INDEX IF NOT EXISTS idx_delivery_plans_prd_id ON delivery_plans(prd_id)",
    "idx_delivery_plans_status": "CREATE INDEX IF NOT EXISTS idx_delivery_plans_status ON delivery_plans(status)",
    "idx_delivery_plans_created_by": "CREATE INDEX IF NOT EXISTS idx_delivery_plans_created_by ON delivery_plans(created_by)",
    "idx_delivery_plans_created_at": "CREATE INDEX IF NOT EXISTS idx_delivery_plans_created_at ON delivery_plans(created_at DESC)",
}


async def create_indexes():
    """Create database indexes for performance optimization"""
    async with engine.begin() as conn:
        existing_tables = await conn.run_sync(
            lambda sync_conn: set(inspect(sync_conn).get_table_names())
        )

        for index_name, sql in INDEX_DEFINITIONS.items():
            match = INDEX_TARGET_RE.search(sql)
            table_name = match.group(1) if match else None

            if table_name and table_name not in existing_tables:
                logger.warning(
                    "Skipping index %s because table %s is not present in current schema",
                    index_name,
                    table_name,
                )
                continue

            try:
                await conn.execute(text(sql))
                logger.info(f"Created index: {index_name}")
            except Exception as e:
                logger.warning(f"Failed to create index {index_name}: {e}")
                if not settings.DEBUG:
                    raise


async def optimize_db():
    """Run database optimization commands.

    WARNING: VACUUM requires an exclusive lock and should only be run
    during maintenance windows. ANALYZE is safe to run online.
    PRAGMA optimize is skipped in DEBUG mode as it can be slow on large DBs.
    """
    async with engine.begin() as conn:
        if "sqlite" in settings.DATABASE_URL:
            # SQLite: ANALYZE is sufficient for query planner stats.
            # PRAGMA optimize is omitted in DEBUG to avoid startup delays.
            if not settings.DEBUG:
                await conn.execute(text("PRAGMA optimize"))
            await conn.execute(text("ANALYZE"))
        elif "postgresql" in settings.DATABASE_URL:
            # PostgreSQL: ANALYZE only (safe online), skip VACUUM
            await conn.execute(text("ANALYZE"))

    logger.info("Database optimization completed")


# ============== Query Helpers ==============

class QueryOptimizer:
    """Database query optimization helpers"""

    @staticmethod
    def paginate(query, page: int = 1, limit: int = 20):
        """Apply pagination to query"""
        offset = (page - 1) * limit
        return query.offset(offset).limit(limit)

    @staticmethod
    async def get_count(session, query) -> int:
        """Get total count for pagination"""
        from sqlalchemy import func, select
        count_query = select(func.count()).select_from(query.subquery())
        result = await session.execute(count_query)
        return result.scalar()

    @staticmethod
    def eager_load(query, *relationships):
        """Apply eager loading to query"""
        from sqlalchemy.orm import selectinload

        for relationship in relationships:
            if isinstance(relationship, str):
                query = query.options(selectinload(relationship))
            else:
                query = query.options(relationship)
        return query
