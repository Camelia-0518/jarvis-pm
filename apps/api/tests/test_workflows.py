"""Workflow endpoints tests"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from httpx import AsyncClient


@pytest.fixture(autouse=True)
def clear_execution_records():
    """Clear in-memory execution records between tests."""
    import app.api.v1.endpoints.workflows as wf_mod
    wf_mod.execution_records.clear()
    yield


# ============== /templates ==============

@pytest.mark.integration
async def test_list_workflows(async_client: AsyncClient):
    """GET /api/v1/workflows/templates should return all workflows."""
    with patch("app.api.v1.endpoints.workflows.WorkflowEngine") as MockEngine:
        mock_engine = MagicMock()
        mock_engine.get_workflow_list.return_value = [
            {"name": "prd_workflow", "description": "PRD Workflow"},
            {"name": "design_workflow", "description": "Design Workflow"},
        ]
        MockEngine.return_value = mock_engine

        response = await async_client.get("/api/v1/workflows/templates")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 2
        assert data["data"][0]["name"] == "prd_workflow"


@pytest.mark.integration
async def test_get_workflow_detail(async_client: AsyncClient):
    """GET /api/v1/workflows/templates/{name} should return workflow detail."""
    with patch("app.api.v1.endpoints.workflows.WorkflowEngine") as MockEngine:
        mock_engine = MagicMock()
        mock_engine.get_workflow_detail.return_value = {
            "name": "prd_workflow",
            "steps": [{"name": "step1", "skill_id": "skill-1"}],
        }
        MockEngine.return_value = mock_engine

        response = await async_client.get("/api/v1/workflows/templates/prd_workflow")
        assert response.status_code == 200

        data = response.json()
        assert data["data"]["name"] == "prd_workflow"
        assert len(data["data"]["steps"]) == 1


@pytest.mark.integration
async def test_get_workflow_detail_not_found(async_client: AsyncClient):
    """GET non-existent workflow should return 404."""
    with patch("app.api.v1.endpoints.workflows.WorkflowEngine") as MockEngine:
        mock_engine = MagicMock()
        mock_engine.get_workflow_detail.return_value = None
        MockEngine.return_value = mock_engine

        response = await async_client.get("/api/v1/workflows/templates/non-existent")
        assert response.status_code == 404


# ============== /execute ==============

@pytest.mark.integration
async def test_execute_workflow(async_client: AsyncClient):
    """POST /api/v1/workflows/execute should run workflow synchronously."""
    with patch("app.api.v1.endpoints.workflows.STANDARD_WORKFLOWS", {"test_workflow": {}}), \
         patch("app.api.v1.endpoints.workflows.WorkflowEngine") as MockEngine:
        mock_engine = MagicMock()
        mock_engine.execute_workflow = AsyncMock(return_value={
            "completed": True,
            "outputs": {"result": "success"},
            "results": [{"step_name": "s1", "status": "success"}],
        })
        MockEngine.return_value = mock_engine

        response = await async_client.post("/api/v1/workflows/execute", json={
            "workflow_name": "test_workflow",
            "inputs": {"key": "value"},
            "project_id": "proj-1",
        })
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["data"]["completed"] is True
        assert "execution_id" in data["data"]


@pytest.mark.integration
async def test_execute_workflow_not_found(async_client: AsyncClient):
    """POST /execute with unknown workflow should 404."""
    with patch("app.api.v1.endpoints.workflows.STANDARD_WORKFLOWS", {}):
        response = await async_client.post("/api/v1/workflows/execute", json={
            "workflow_name": "unknown",
            "inputs": {},
        })
        assert response.status_code == 404


# ============== /execute-async ==============

@pytest.mark.integration
async def test_execute_workflow_async(async_client: AsyncClient):
    """POST /api/v1/workflows/execute-async should queue background execution."""
    with patch("app.api.v1.endpoints.workflows.STANDARD_WORKFLOWS", {"test_workflow": {}}):
        response = await async_client.post("/api/v1/workflows/execute-async", json={
            "workflow_name": "test_workflow",
            "inputs": {"key": "value"},
            "project_id": "proj-1",
        })
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["data"]["status"] == "running"
        assert "execution_id" in data["data"]


@pytest.mark.integration
async def test_execute_workflow_async_not_found(async_client: AsyncClient):
    """POST /execute-async with unknown workflow should 404."""
    with patch("app.api.v1.endpoints.workflows.STANDARD_WORKFLOWS", {}):
        response = await async_client.post("/api/v1/workflows/execute-async", json={
            "workflow_name": "unknown",
            "inputs": {},
        })
        assert response.status_code == 404


# ============== /executions ==============

@pytest.mark.integration
async def test_get_execution_status(async_client: AsyncClient):
    """GET /api/v1/workflows/executions/{id} should return execution record."""
    with patch("app.api.v1.endpoints.workflows.STANDARD_WORKFLOWS", {"test_workflow": {}}), \
         patch("app.api.v1.endpoints.workflows._run_workflow_background", new_callable=AsyncMock):
        response = await async_client.post("/api/v1/workflows/execute-async", json={
            "workflow_name": "test_workflow",
            "inputs": {},
        })
        execution_id = response.json()["data"]["execution_id"]

        response = await async_client.get(f"/api/v1/workflows/executions/{execution_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["execution_id"] == execution_id
        assert data["data"]["status"] == "running"


@pytest.mark.integration
async def test_get_execution_status_not_found(async_client: AsyncClient):
    """GET non-existent execution should return 404."""
    response = await async_client.get("/api/v1/workflows/executions/non-existent")
    assert response.status_code == 404


@pytest.mark.integration
async def test_list_executions(async_client: AsyncClient):
    """GET /api/v1/workflows/executions should return execution history."""
    with patch("app.api.v1.endpoints.workflows.STANDARD_WORKFLOWS", {"wf1": {}, "wf2": {}}), \
         patch("app.api.v1.endpoints.workflows._run_workflow_background", new_callable=AsyncMock):
        await async_client.post("/api/v1/workflows/execute-async", json={
            "workflow_name": "wf1",
            "inputs": {},
            "project_id": "p1",
        })
        await async_client.post("/api/v1/workflows/execute-async", json={
            "workflow_name": "wf2",
            "inputs": {},
            "project_id": "p2",
        })

        response = await async_client.get("/api/v1/workflows/executions")
        assert response.status_code == 200

        data = response.json()
        assert data["data"]["total"] == 2


@pytest.mark.integration
async def test_list_executions_with_filters(async_client: AsyncClient):
    """GET /executions should support workflow and status filters."""
    with patch("app.api.v1.endpoints.workflows.STANDARD_WORKFLOWS", {"wf1": {}, "wf2": {}}), \
         patch("app.api.v1.endpoints.workflows._run_workflow_background", new_callable=AsyncMock):
        await async_client.post("/api/v1/workflows/execute-async", json={
            "workflow_name": "wf1",
            "inputs": {},
        })

        response = await async_client.get("/api/v1/workflows/executions?workflow=wf1")
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["total"] == 1

        response = await async_client.get("/api/v1/workflows/executions?status=running")
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["total"] == 1

        response = await async_client.get("/api/v1/workflows/executions?workflow=nonexistent")
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["total"] == 0


@pytest.mark.integration
async def test_list_executions_pagination(async_client: AsyncClient):
    """GET /executions should support limit/offset pagination."""
    with patch("app.api.v1.endpoints.workflows.STANDARD_WORKFLOWS", {"wf1": {}}), \
         patch("app.api.v1.endpoints.workflows._run_workflow_background", new_callable=AsyncMock):
        for _ in range(3):
            await async_client.post("/api/v1/workflows/execute-async", json={
                "workflow_name": "wf1",
                "inputs": {},
            })

        response = await async_client.get("/api/v1/workflows/executions?limit=2&offset=0")
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]["items"]) == 2
        assert data["data"]["total"] == 3

        response = await async_client.get("/api/v1/workflows/executions?limit=2&offset=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]["items"]) == 1
