"""Agent endpoints tests"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from httpx import AsyncClient


# ============== /agents ==============

@pytest.mark.integration
async def test_list_agents(async_client: AsyncClient):
    """GET /api/v1/agents should return all registered agents."""
    with patch("app.api.v1.endpoints.agents.AgentRegistry") as MockRegistry:
        mock_registry = MagicMock()
        mock_registry.get_all_info.return_value = [
            {
                "name": "prd_generator",
                "description": "PRD生成Agent",
                "version": "1.0",
                "capabilities": ["prd", "文档生成"],
            },
            {
                "name": "requirement_analyzer",
                "description": "需求分析Agent",
                "version": "1.0",
                "capabilities": ["分析", "需求"],
            },
        ]
        MockRegistry.return_value = mock_registry

        response = await async_client.get("/api/v1/agents")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 2
        assert data["data"][0]["name"] == "prd_generator"


@pytest.mark.integration
async def test_list_agents_empty(async_client: AsyncClient):
    """GET /api/v1/agents should handle empty registry."""
    with patch("app.api.v1.endpoints.agents.AgentRegistry") as MockRegistry:
        mock_registry = MagicMock()
        mock_registry.get_all_info.return_value = []
        MockRegistry.return_value = mock_registry

        response = await async_client.get("/api/v1/agents")
        assert response.status_code == 200
        assert response.json()["data"] == []


# ============== /agents/stats ==============

@pytest.mark.integration
async def test_get_agent_stats(async_client: AsyncClient):
    """GET /api/v1/agents/stats should return queue and manager stats."""
    with patch("app.api.v1.endpoints.agents.get_task_queue") as mock_get_queue:
        mock_queue = MagicMock()
        mock_queue.get_stats.return_value = {"pending": 2, "running": 1, "completed": 10}
        mock_get_queue.return_value = mock_queue

        with patch("app.api.v1.endpoints.agents.manager") as mock_manager:
            mock_manager.get_stats.return_value = {"agents": 5, "tasks": 13}

            response = await async_client.get("/api/v1/agents/stats")
            assert response.status_code == 200

            data = response.json()
            assert data["success"] is True
            assert data["data"]["queue"]["pending"] == 2
            assert data["data"]["manager"]["agents"] == 5


# ============== /agents/prd/generate ==============

@pytest.mark.integration
async def test_generate_prd(async_client: AsyncClient):
    """POST /api/v1/agents/prd/generate should queue a PRD generation task."""
    with patch("app.api.v1.endpoints.agents.get_task_queue") as mock_get_queue:
        mock_queue = AsyncMock()
        mock_queue.submit.return_value = "task-uuid-123"
        mock_get_queue.return_value = mock_queue

        response = await async_client.post("/api/v1/agents/prd/generate", json={
            "product_name": "测试产品",
            "description": "这是一个测试产品的详细描述，足够长以通过验证。",
            "target_users": "产品经理",
            "key_features": ["功能A", "功能B"],
        })
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["data"]["task_id"] == "task-uuid-123"
        assert data["data"]["status"] == "queued"

        mock_queue.submit.assert_awaited_once()
        call_kwargs = mock_queue.submit.call_args.kwargs
        assert call_kwargs["agent_name"] == "prd_generator"
        assert call_kwargs["priority"].value == 2


@pytest.mark.integration
async def test_generate_prd_validation_error(async_client: AsyncClient):
    """POST /api/v1/agents/prd/generate should validate input."""
    response = await async_client.post("/api/v1/agents/prd/generate", json={
        "product_name": "",
        "description": "短",
        "target_users": "",
        "key_features": [],
    })
    assert response.status_code == 422


# ============== /agents/requirements/analyze ==============

@pytest.mark.integration
async def test_analyze_requirements(async_client: AsyncClient):
    """POST /api/v1/agents/requirements/analyze should queue a requirement analysis task."""
    with patch("app.api.v1.endpoints.agents.get_task_queue") as mock_get_queue:
        mock_queue = AsyncMock()
        mock_queue.submit.return_value = "task-uuid-456"
        mock_get_queue.return_value = mock_queue

        response = await async_client.post("/api/v1/agents/requirements/analyze", json={
            "raw_requirements": "用户需要一个登录功能，支持手机号验证码登录和微信登录。",
            "product_name": "测试产品",
            "industry": "saas",
            "analysis_depth": "standard",
        })
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["data"]["task_id"] == "task-uuid-456"

        mock_queue.submit.assert_awaited_once()
        call_kwargs = mock_queue.submit.call_args.kwargs
        assert call_kwargs["agent_name"] == "requirement_analyzer"


@pytest.mark.integration
async def test_analyze_requirements_validation_error(async_client: AsyncClient):
    """POST /api/v1/agents/requirements/analyze should validate input."""
    response = await async_client.post("/api/v1/agents/requirements/analyze", json={
        "raw_requirements": "短",
    })
    assert response.status_code == 422


# ============== /agents/tasks ==============

@pytest.mark.integration
async def test_list_tasks(async_client: AsyncClient):
    """GET /api/v1/agents/tasks should return paginated tasks."""
    with patch("app.api.v1.endpoints.agents.get_task_queue") as mock_get_queue:
        mock_queue = MagicMock()

        mock_task = MagicMock()
        mock_task.id = "task-1"
        mock_task.agent_name = "prd_generator"
        mock_task.status = "completed"
        mock_task.created_at.isoformat.return_value = "2024-01-01T00:00:00"

        mock_queue.list_tasks.return_value = [mock_task]
        mock_get_queue.return_value = mock_queue

        response = await async_client.get("/api/v1/agents/tasks")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["data"]["total"] == 1
        assert len(data["data"]["items"]) == 1
        assert data["data"]["items"][0]["agent_name"] == "prd_generator"


@pytest.mark.integration
async def test_list_tasks_with_status_filter(async_client: AsyncClient):
    """GET /api/v1/agents/tasks should support status filter."""
    with patch("app.api.v1.endpoints.agents.get_task_queue") as mock_get_queue:
        mock_queue = MagicMock()
        mock_queue.list_tasks.return_value = []
        mock_get_queue.return_value = mock_queue

        response = await async_client.get("/api/v1/agents/tasks?status=completed")
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["total"] == 0


# ============== /agents/tasks/{task_id} ==============

@pytest.mark.integration
async def test_get_task_status(async_client: AsyncClient):
    """GET /api/v1/agents/tasks/{task_id} should return task details."""
    with patch("app.api.v1.endpoints.agents.get_task_queue") as mock_get_queue:
        mock_queue = AsyncMock()

        mock_result = MagicMock()
        mock_result.to_dict.return_value = {"output": "PRD content"}

        mock_task = MagicMock()
        mock_task.id = "task-uuid-123"
        mock_task.status = "completed"
        mock_task.result = mock_result
        mock_task.error = None

        mock_queue.get_task.return_value = mock_task
        mock_get_queue.return_value = mock_queue

        response = await async_client.get("/api/v1/agents/tasks/12345678-1234-5678-1234-567812345678")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["data"]["status"] == "completed"
        assert data["data"]["result"]["output"] == "PRD content"


@pytest.mark.integration
async def test_get_task_not_found(async_client: AsyncClient):
    """GET /api/v1/agents/tasks/{task_id} should return 404 for unknown task."""
    with patch("app.api.v1.endpoints.agents.get_task_queue") as mock_get_queue:
        mock_queue = AsyncMock()
        mock_queue.get_task.return_value = None
        mock_get_queue.return_value = mock_queue

        response = await async_client.get("/api/v1/agents/tasks/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404


@pytest.mark.integration
async def test_get_task_invalid_uuid(async_client: AsyncClient):
    """GET /api/v1/agents/tasks/{task_id} should return 400 for invalid UUID."""
    response = await async_client.get("/api/v1/agents/tasks/not-a-uuid!!!")
    assert response.status_code == 400


# ============== /agents/{agent_name} ==============

@pytest.mark.integration
async def test_get_agent_detail(async_client: AsyncClient):
    """GET /api/v1/agents/{agent_name} should return agent details."""
    with patch("app.api.v1.endpoints.agents.AgentRegistry") as MockRegistry:
        mock_agent = MagicMock()
        mock_agent.name = "prd_generator"
        mock_agent.description = "PRD生成Agent"
        mock_agent.version = "1.0"
        mock_agent.capabilities = ["prd", "文档生成"]
        mock_agent.required_tools = []

        mock_registry = MagicMock()
        mock_registry.get.return_value = mock_agent
        MockRegistry.return_value = mock_registry

        response = await async_client.get("/api/v1/agents/prd_generator")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["data"]["name"] == "prd_generator"


@pytest.mark.integration
async def test_get_agent_detail_not_found(async_client: AsyncClient):
    """GET /api/v1/agents/{agent_name} should return 404 for unknown agent."""
    with patch("app.api.v1.endpoints.agents.AgentRegistry") as MockRegistry:
        mock_registry = MagicMock()
        mock_registry.get.return_value = None
        MockRegistry.return_value = mock_registry

        response = await async_client.get("/api/v1/agents/non_existent_agent")
        assert response.status_code == 404
