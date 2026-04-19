"""Database configuration with connection pooling and optimizations"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool, QueuePool
from sqlalchemy import event, text
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

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
        pool_timeout=30,           # Timeout for getting connection from pool
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
    finally:
        await session.close()


async def init_db():
    """Initialize database tables"""
    # Import all models to ensure they are registered with Base.metadata
    from app.models import (
        User,
        Project,
        PRD,
        SkillExecution,
        Battle,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables initialized")


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
}


async def create_indexes():
    """Create database indexes for performance optimization"""
    async with engine.begin() as conn:
        for index_name, sql in INDEX_DEFINITIONS.items():
            try:
                await conn.execute(text(sql))
                logger.info(f"Created index: {index_name}")
            except Exception as e:
                logger.warning(f"Failed to create index {index_name}: {e}")


async def optimize_db():
    """Run database optimization commands"""
    async with engine.begin() as conn:
        if "sqlite" in settings.DATABASE_URL:
            # SQLite optimizations
            await conn.execute(text("PRAGMA optimize"))
            await conn.execute(text("ANALYZE"))
        elif "postgresql" in settings.DATABASE_URL:
            # PostgreSQL optimizations
            await conn.execute(text("ANALYZE"))
            await conn.execute(text("VACUUM ANALYZE"))

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
        from sqlalchemy.orm import joinedload, selectinload

        for relationship in relationships:
            if isinstance(relationship, str):
                query = query.options(selectinload(relationship))
            else:
                query = query.options(relationship)
        return query
