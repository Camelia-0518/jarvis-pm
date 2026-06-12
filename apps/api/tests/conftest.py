"""Pytest fixtures for Jarvis PM API tests

Provides:
- Async in-memory SQLite database (isolated per test via fresh :memory: DB)
- AsyncSession fixture for direct DB operations
- AsyncClient fixture for HTTP API testing
- Authenticated client fixture (single-user mode)
- Sample data fixtures (user, project, prd)
"""

import os
import uuid
from typing import AsyncGenerator

# Patch bcrypt before passlib imports it — newer bcrypt (4.1+) rejects
# passwords >72 bytes without explicit truncation, but passlib's internal
# detection code passes a long test password. We truncate at the source.
import bcrypt as _bcrypt_lib
_original_bcrypt_hashpw = _bcrypt_lib.hashpw
_original_bcrypt_checkpw = _bcrypt_lib.checkpw


def _patched_hashpw(password: bytes, salt: bytes) -> bytes:
    if isinstance(password, str):
        password = password.encode("utf-8")
    if len(password) > 72:
        password = password[:72]
    return _original_bcrypt_hashpw(password, salt)


def _patched_checkpw(password: bytes, hashed_password: bytes) -> bool:
    if isinstance(password, str):
        password = password.encode("utf-8")
    if len(password) > 72:
        password = password[:72]
    return _original_bcrypt_checkpw(password, hashed_password)


_bcrypt_lib.hashpw = _patched_hashpw
_bcrypt_lib.checkpw = _patched_checkpw

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

# =============================================================================
# CRITICAL: Override settings and patch decorators BEFORE any app module imports.
# =============================================================================

# Use a shared-cache in-memory URI so multiple connections see the same DB.
# aiosqlite requires the `uri=true` query parameter to parse URI filenames.
_SHARED_MEMORY_URL = "sqlite+aiosqlite:///file:testdb?mode=memory&cache=shared&uri=true"

os.environ["DATABASE_URL"] = _SHARED_MEMORY_URL
os.environ["DATABASE_URL_SYNC"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-secret-key-not-for-production"
os.environ["SINGLE_USER_MODE"] = "true"
os.environ["DEBUG"] = "true"
os.environ["REDIS_URL"] = ""
os.environ["KIMI_API_KEY"] = "test-dummy-key"
os.environ["OPENAI_API_KEY"] = ""
os.environ["ANTHROPIC_API_KEY"] = ""

# Disable rate limiting BEFORE endpoint modules are imported and decorated.
import app.core.rate_limit as _rate_limit_module


def _no_op_rate_limit(requests=100, window=60, key_func=None):
    """No-op rate limit decorator for tests."""
    def decorator(func):
        return func
    return decorator


_rate_limit_module.rate_limit = _no_op_rate_limit

# Now import app modules — they will pick up the overridden env vars.
from app.main import app
from app.core.database import Base, get_db, engine as _app_engine, AsyncSessionLocal as _app_async_session_local
from app.core.cache import cache_manager
from app.core.config import Settings
from app.core.security import get_password_hash
from app.models.user import User, UserRole
from app.models.project import Project, ProjectStatus
from app.models.prd import PRD, PRDStatus
from app.models.template import Template
from app.models.prd_annotation import PRDAnnotation, AnnotationStatus, AnnotationType
from app.models.feedback import Feedback
from app.models.persona import Persona
from app.models.requirement import Requirement

# Re-instantiate settings so the test values are reflected everywhere.
import app.core.config as _config_module
_config_module.settings = Settings()
from app.core.config import settings


# ============== Database per test (shared-cache in-memory SQLite) ==============

@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide an isolated async database session per test.

    Each test gets its own in-memory SQLite database.  We use a
    shared-cache URI (mode=memory&cache=shared) so that the single
    connection held open by the engine and any additional connections
    opened by ``get_db()`` all see the same database contents.
    """
    # Generate a unique DB name per test so tests are fully isolated.
    db_name = f"test_{uuid.uuid4().hex}"
    db_url = (
        f"sqlite+aiosqlite:///file:{db_name}?mode=memory&cache=shared&uri=true"
    )

    test_engine = create_async_engine(
        db_url,
        echo=False,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
        future=True,
    )

    TestAsyncSessionLocal = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    # Create all tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Monkey-patch the app's module-level globals so that get_db()
    # (which references AsyncSessionLocal) and lifespan init_db()
    # both use this test database.
    import app.core.database as _db_module
    original_engine = _db_module.engine
    original_async_session_local = _db_module.AsyncSessionLocal
    _db_module.engine = test_engine
    _db_module.AsyncSessionLocal = TestAsyncSessionLocal

    session = TestAsyncSessionLocal()

    # Override the app's get_db to yield our session
    async def override_get_db():
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    # Ensure single-user mode for tests
    original_single_user = settings.SINGLE_USER_MODE
    settings.SINGLE_USER_MODE = True

    try:
        yield session
    finally:
        settings.SINGLE_USER_MODE = original_single_user
        app.dependency_overrides.pop(get_db, None)
        await session.close()
        # Restore original engine
        _db_module.engine = original_engine
        _db_module.AsyncSessionLocal = original_async_session_local
        await test_engine.dispose()


# ============== HTTP Client ==============

@pytest_asyncio.fixture
async def async_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Provide an httpx AsyncClient for the FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest_asyncio.fixture
async def authenticated_client(async_client: AsyncClient) -> AsyncClient:
    """Provide an authenticated AsyncClient.

    In single-user mode, no JWT token is required — the endpoint
    returns 'single-user' automatically. This fixture exists for
    explicit token-based testing if needed.
    """
    # Single-user mode: auth is automatic, but we can set a header
    # if we want to test the token path explicitly.
    return async_client


# ============== Global Mocks ==============

@pytest.fixture(autouse=True)
def mock_memory_indexer(monkeypatch):
    """Globally mock memory_indexer to avoid loading sentence-transformers."""
    class _FakeIndexer:
        async def index_document(self, *args, **kwargs):
            return 0

        async def delete_document_index(self, *args, **kwargs):
            return None

        async def semantic_search(self, *args, **kwargs):
            return []

    import app.services.memory_indexer as _mi_mod
    monkeypatch.setattr(_mi_mod, "memory_indexer", _FakeIndexer())


@pytest.fixture(autouse=True)
def mock_ai_services(monkeypatch):
    """Globally mock external AI/LLM calls to prevent network access during tests.

    This ensures CRUD tests don't accidentally trigger real LLM connections
    via background tasks (e.g., compliance check on PRD update).
    """
    from unittest.mock import AsyncMock

    # Mock ai_service.chat — the primary LLM call point
    import app.services.ai_service as _ai_mod
    _fake_chat = AsyncMock(return_value="Mock AI response for testing")
    monkeypatch.setattr(_ai_mod.ai_service, "chat", _fake_chat)

    # Mock ComplianceChecker — used in background re-review tasks
    try:
        from app.agents.agents.compliance_checker import ComplianceChecker
        _fake_result = AsyncMock()
        _fake_result.success = True
        _fake_result.output = "Mock compliance check passed"
        _fake_result.error = None
        _fake_result.compliance_score = 85.0
        monkeypatch.setattr(ComplianceChecker, "execute", AsyncMock(return_value=_fake_result))
    except ImportError:
        pass


# ============== Sample Data Fixtures ==============

# User ID that matches single-user mode auth
SINGLE_USER_ID = "single-user"


@pytest_asyncio.fixture
async def sample_user(db_session: AsyncSession) -> User:
    """Create and return a sample user with the single-user ID."""
    user = User(
        id=SINGLE_USER_ID,
        email="test@example.com",
        hashed_password=get_password_hash("testpassword123"),
        name="Test User",
        role=UserRole.ADMIN,
        is_active=True,
        preferences={},
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def sample_project(db_session: AsyncSession, sample_user: User) -> Project:
    """Create and return a sample project owned by the single user."""
    project = Project(
        id=str(uuid.uuid4()),
        name="Test Project",
        description="A project for testing",
        industry="saas",
        status=ProjectStatus.ACTIVE,
        created_by=SINGLE_USER_ID,
        settings={},
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


@pytest_asyncio.fixture
async def sample_prd(db_session: AsyncSession, sample_project: Project, sample_user: User) -> PRD:
    """Create and return a sample PRD belonging to sample_project."""
    prd = PRD(
        id=str(uuid.uuid4()),
        project_id=sample_project.id,
        title="Test PRD",
        version="1.0",
        status=PRDStatus.DRAFT,
        content={"chapters": {}, "template": "default", "industry": "saas"},
        markdown="# Test PRD",
        ai_generated={"template": "default", "industry": "saas", "ai_generated": False},
        created_by=SINGLE_USER_ID,
    )
    db_session.add(prd)
    await db_session.commit()
    await db_session.refresh(prd)
    return prd


@pytest_asyncio.fixture
async def multiple_projects(db_session: AsyncSession, sample_user: User) -> list[Project]:
    """Create multiple projects for pagination/filtering tests."""
    projects = []
    for i in range(5):
        project = Project(
            id=str(uuid.uuid4()),
            name=f"Project {i + 1}",
            description=f"Description for project {i + 1}",
            industry="medical" if i % 2 == 0 else "saas",
            status=ProjectStatus.ACTIVE if i < 4 else ProjectStatus.ARCHIVED,
            created_by=SINGLE_USER_ID,
            settings={},
        )
        db_session.add(project)
        projects.append(project)
    await db_session.commit()
    for p in projects:
        await db_session.refresh(p)
    return projects


@pytest_asyncio.fixture
async def sample_template(db_session: AsyncSession) -> Template:
    """Create and return a sample custom template."""
    template = Template(
        id=str(uuid.uuid4()),
        name="Test Template",
        description="A template for testing",
        industry="saas",
        chapters=["Chapter 1", "Chapter 2"],
        icon="🧪",
        color="bg-blue-500",
        is_builtin=False,
        created_by=SINGLE_USER_ID,
    )
    db_session.add(template)
    await db_session.commit()
    await db_session.refresh(template)
    return template


@pytest_asyncio.fixture
async def sample_annotation(db_session: AsyncSession, sample_prd: PRD) -> PRDAnnotation:
    """Create and return a sample PRD annotation."""
    annotation = PRDAnnotation(
        prd_id=sample_prd.id,
        chapter_num="1",
        chapter_title="Introduction",
        line_index=5,
        selected_text="sample text",
        content="This is a test annotation",
        annotation_type=AnnotationType.COMMENT,
        status=AnnotationStatus.OPEN,
        created_by=SINGLE_USER_ID,
    )
    db_session.add(annotation)
    await db_session.commit()
    await db_session.refresh(annotation)
    return annotation


@pytest_asyncio.fixture
async def sample_feedback(db_session: AsyncSession) -> Feedback:
    """Create and return a sample feedback entry."""
    fb = Feedback(
        user_id=SINGLE_USER_ID,
        category="bug",
        content="Something is broken",
        rating=3,
        context="workspace page",
    )
    db_session.add(fb)
    await db_session.commit()
    await db_session.refresh(fb)
    return fb


@pytest_asyncio.fixture
async def sample_persona(db_session: AsyncSession, sample_project: Project) -> Persona:
    """Create and return a sample persona."""
    p = Persona(
        project_id=sample_project.id,
        created_by=SINGLE_USER_ID,
        name="门诊医生",
        role="医生",
        description="三甲医院门诊医生",
        pain_points="系统切换频繁",
        goals="提高工作效率",
        scenarios="门诊接诊",
        demographics="30-50岁",
    )
    db_session.add(p)
    await db_session.commit()
    await db_session.refresh(p)
    return p


@pytest_asyncio.fixture
async def sample_requirement(db_session: AsyncSession, sample_project: Project) -> Requirement:
    """Create and return a sample requirement."""
    r = Requirement(
        project_id=sample_project.id,
        created_by=SINGLE_USER_ID,
        title="用户登录功能",
        description="支持手机号验证码登录",
        status="backlog",
        priority="p1",
        rice_reach=100,
        rice_impact=3.0,
        rice_confidence=80,
        rice_effort=2.0,
        rice_score=120.0,
        kano_category="must_be",
    )
    db_session.add(r)
    await db_session.commit()
    await db_session.refresh(r)
    return r