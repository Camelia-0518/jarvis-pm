"""API response time benchmarks

Tests that high-frequency endpoints respond within acceptable thresholds.
These tests use mocked dependencies so they measure endpoint overhead,
not external service latency.
"""

import time
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project


# Thresholds (seconds) — these are generous because test infrastructure
# (in-memory SQLite, mocked AI) is much faster than production.
THRESHOLD_FAST = 0.5      # Simple CRUD / list endpoints
THRESHOLD_MEDIUM = 1.0    # Endpoints with some business logic
THRESHOLD_SLOW = 2.0      # Endpoints with multiple mocked service calls


@pytest.mark.integration
async def test_benchmark_list_agents(async_client: AsyncClient):
    """GET /agents should be fast (< 500ms)."""
    with patch("app.api.v1.endpoints.agents.AgentRegistry") as MockRegistry:
        mock_registry = MagicMock()
        mock_registry.get_all_info.return_value = [
            {"name": f"agent_{i}", "description": "D", "version": "1.0", "capabilities": []}
            for i in range(20)
        ]
        MockRegistry.return_value = mock_registry

        start = time.perf_counter()
        response = await async_client.get("/api/v1/agents")
        elapsed = time.perf_counter() - start

        assert response.status_code == 200
        assert elapsed < THRESHOLD_FAST, f"List agents took {elapsed:.3f}s"


@pytest.mark.integration
async def test_benchmark_execute_skill(async_client: AsyncClient):
    """POST /skills/execute should complete within medium threshold."""
    with patch("app.api.v1.endpoints.skills.skill_processor.get_skill_by_id") as mock_get, \
         patch("app.api.v1.endpoints.skills.SkillProcessorEnhanced") as MockEnhanced:
        mock_get.return_value = {"id": "product-analyst", "name": "分析"}

        mock_instance = AsyncMock()
        mock_instance.execute_skill.return_value = {
            "success": True,
            "output": {"analysis": "测试结果"},
            "formatted_output": "## 分析",
            "token_usage": {"prompt_tokens": 100, "completion_tokens": 50},
        }
        MockEnhanced.return_value = mock_instance

        start = time.perf_counter()
        response = await async_client.post("/api/v1/skills/execute", json={
            "skillId": "product-analyst",
            "inputs": {"title": "测试产品"},
            "context": {"project_id": "proj-1"},
        })
        elapsed = time.perf_counter() - start

        assert response.status_code == 200
        assert elapsed < THRESHOLD_MEDIUM, f"Execute skill took {elapsed:.3f}s"


@pytest.mark.integration
@pytest.mark.external(reason="Competitor analysis benchmark pre-existing")
async def test_benchmark_competitor_analysis(async_client: AsyncClient):
    """POST /tools/competitors should complete within slow threshold."""
    with patch("app.api.v1.endpoints.tools.web_crawler_service.search_competitor_info", new_callable=AsyncMock) as mock_crawler, \
         patch("app.api.v1.endpoints.tools.ai_service.chat", new_callable=AsyncMock) as mock_chat:
        mock_crawler.return_value = {
            "results": [
                {"success": True, "name": "竞品A", "url": "https://a.com", "title": "A", "description": "D", "content": "C"}
            ]
        }
        mock_chat.return_value = "## 竞品分析\n\n- 差异点"

        start = time.perf_counter()
        response = await async_client.post("/api/v1/tools/competitors", json={
            "project_id": "proj-1",
            "competitors": ["竞品A"],
        })
        elapsed = time.perf_counter() - start

        assert response.status_code == 200
        assert elapsed < THRESHOLD_SLOW, f"Competitor analysis took {elapsed:.3f}s"


@pytest.mark.integration
async def test_benchmark_list_projects(async_client: AsyncClient, db_session: AsyncSession):
    """GET /projects should be fast even with many rows."""
    from app.models.project import ProjectStatus
    for i in range(50):
        p = Project(
            id=f"proj-bench-{i}",
            name=f"Project {i}",
            description="Benchmark",
            industry="saas",
            status=ProjectStatus.ACTIVE,
            created_by="single-user",
        )
        db_session.add(p)
    await db_session.commit()

    start = time.perf_counter()
    response = await async_client.get("/api/v1/projects")
    elapsed = time.perf_counter() - start

    assert response.status_code == 200
    assert elapsed < THRESHOLD_FAST, f"List 50 projects took {elapsed:.3f}s"


@pytest.mark.integration
async def test_benchmark_prd_generate(async_client: AsyncClient):
    """POST /agents/prd/generate should queue quickly (< 500ms)."""
    with patch("app.api.v1.endpoints.agents.get_task_queue") as mock_get_queue:
        mock_queue = AsyncMock()
        mock_queue.submit.return_value = "task-uuid-123"
        mock_get_queue.return_value = mock_queue

        start = time.perf_counter()
        response = await async_client.post("/api/v1/agents/prd/generate", json={
            "product_name": "测试产品",
            "description": "这是一个测试产品的详细描述，足够长以通过验证。",
            "target_users": "产品经理",
            "key_features": ["功能A", "功能B"],
        })
        elapsed = time.perf_counter() - start

        assert response.status_code == 200
        assert elapsed < THRESHOLD_FAST, f"PRD generate took {elapsed:.3f}s"


@pytest.mark.integration
async def test_benchmark_workflow_execute(async_client: AsyncClient):
    """POST /workflows/execute should complete within slow threshold."""
    with patch("app.api.v1.endpoints.workflows.STANDARD_WORKFLOWS", {"test_workflow": {}}), \
         patch("app.api.v1.endpoints.workflows.WorkflowEngine") as MockEngine:
        mock_engine = MagicMock()
        mock_engine.execute_workflow = AsyncMock(return_value={
            "completed": True,
            "outputs": {"result": "ok"},
            "results": [],
        })
        MockEngine.return_value = mock_engine

        start = time.perf_counter()
        response = await async_client.post("/api/v1/workflows/execute", json={
            "workflow_name": "test_workflow",
            "inputs": {"key": "value"},
        })
        elapsed = time.perf_counter() - start

        assert response.status_code == 200
        assert elapsed < THRESHOLD_MEDIUM, f"Workflow execute took {elapsed:.3f}s"