"""Skills system endpoints tests"""

import pytest
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.skill_execution import SkillExecution


# ============== /definitions ==============

@pytest.mark.integration
async def test_list_skills(async_client: AsyncClient):
    """GET /api/v1/skills/definitions should return all skills."""
    with patch("app.api.v1.endpoints.skills.skill_processor.get_all_skills") as mock_get:
        mock_get.return_value = [
            {"id": "skill-1", "name": "分析技能", "category": "analysis", "agentRole": "ceo"},
            {"id": "skill-2", "name": "设计技能", "category": "design", "agentRole": "designer"},
        ]

        response = await async_client.get("/api/v1/skills/definitions")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["data"]["total"] == 2
        assert len(data["data"]["skills"]) == 2


@pytest.mark.integration
async def test_list_skills_with_category_filter(async_client: AsyncClient):
    """GET with category filter should return filtered skills."""
    with patch("app.api.v1.endpoints.skills.skill_processor.get_all_skills") as mock_get:
        mock_get.return_value = [
            {"id": "s1", "name": "分析", "category": "analysis"},
            {"id": "s2", "name": "设计", "category": "design"},
        ]

        response = await async_client.get("/api/v1/skills/definitions?category=analysis")
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["total"] == 1
        assert data["data"]["skills"][0]["id"] == "s1"


@pytest.mark.integration
async def test_list_skills_with_search(async_client: AsyncClient):
    """GET with search should filter by keyword."""
    with patch("app.api.v1.endpoints.skills.skill_processor.get_all_skills") as mock_get:
        mock_get.return_value = [
            {"id": "s1", "name": "需求分析", "description": "分析需求", "tags": ["prd"]},
            {"id": "s2", "name": "UI设计", "description": "设计界面", "tags": ["ui"]},
        ]

        response = await async_client.get("/api/v1/skills/definitions?search=需求")
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["total"] == 1
        assert data["data"]["skills"][0]["id"] == "s1"


# ============== /definitions/{id} ==============

@pytest.mark.integration
async def test_get_skill_by_id(async_client: AsyncClient):
    """GET /api/v1/skills/definitions/{id} should return skill detail."""
    with patch("app.api.v1.endpoints.skills.skill_processor.get_skill_by_id") as mock_get:
        mock_get.return_value = {"id": "skill-1", "name": "测试技能", "parameters": []}

        response = await async_client.get("/api/v1/skills/definitions/skill-1")
        assert response.status_code == 200
        assert response.json()["data"]["id"] == "skill-1"


@pytest.mark.integration
async def test_get_skill_not_found(async_client: AsyncClient):
    """GET non-existent skill should return 404."""
    with patch("app.api.v1.endpoints.skills.skill_processor.get_skill_by_id") as mock_get:
        mock_get.return_value = None

        response = await async_client.get("/api/v1/skills/definitions/non-existent")
        assert response.status_code == 404


# ============== /by-role/{role} ==============

@pytest.mark.integration
async def test_get_skills_by_role(async_client: AsyncClient):
    """GET /api/v1/skills/by-role/{role} should return role-specific skills."""
    with patch("app.api.v1.endpoints.skills.skill_processor.get_skills_by_role") as mock_get:
        mock_get.return_value = [{"id": "s1", "name": "战略分析"}]

        response = await async_client.get("/api/v1/skills/by-role/ceo")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["role"] == "ceo"
        assert data["data"]["total"] == 1


# ============== /categories ==============

@pytest.mark.integration
async def test_get_skill_categories(async_client: AsyncClient):
    """GET /api/v1/skills/categories should return category list."""
    response = await async_client.get("/api/v1/skills/categories")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["data"]) >= 6
    categories = [c["value"] for c in data["data"]]
    assert "analysis" in categories
    assert "medical" in categories


# ============== /validate ==============

@pytest.mark.integration
async def test_validate_skill_input_valid(async_client: AsyncClient):
    """POST /api/v1/skills/validate should return valid=true for correct inputs."""
    with patch("app.api.v1.endpoints.skills.skill_processor.get_skill_by_id") as mock_get:
        mock_get.return_value = {
            "id": "skill-1",
            "parameters": [
                {"name": "title", "label": "标题", "required": True},
                {"name": "desc", "label": "描述", "required": False},
            ]
        }

        response = await async_client.post("/api/v1/skills/validate", json={
            "skillId": "skill-1",
            "inputs": {"title": "测试标题"},
        })
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["valid"] is True
        assert data["data"]["errors"] == []


@pytest.mark.integration
async def test_validate_skill_input_missing_required(async_client: AsyncClient):
    """POST should return valid=false when required param missing."""
    with patch("app.api.v1.endpoints.skills.skill_processor.get_skill_by_id") as mock_get:
        mock_get.return_value = {
            "id": "skill-1",
            "parameters": [
                {"name": "title", "label": "标题", "required": True},
            ]
        }

        response = await async_client.post("/api/v1/skills/validate", json={
            "skillId": "skill-1",
            "inputs": {},
        })
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["valid"] is False
        assert len(data["data"]["errors"]) >= 1


@pytest.mark.integration
async def test_validate_skill_not_found(async_client: AsyncClient):
    """POST for non-existent skill should return 404."""
    with patch("app.api.v1.endpoints.skills.skill_processor.get_skill_by_id") as mock_get:
        mock_get.return_value = None

        response = await async_client.post("/api/v1/skills/validate", json={
            "skillId": "non-existent",
            "inputs": {},
        })
        assert response.status_code == 404


# ============== /execute ==============

@pytest.mark.integration
async def test_execute_skill(async_client: AsyncClient, db_session: AsyncSession):
    """POST /api/v1/skills/execute should run skill and persist record."""
    with patch("app.api.v1.endpoints.skills.skill_processor.get_skill_by_id") as mock_get, \
         patch("app.api.v1.endpoints.skills.SkillProcessorEnhanced") as MockEnhanced:
        mock_get.return_value = {"id": "product-analyst", "name": "产品分析"}

        mock_instance = AsyncMock()
        mock_instance.execute_skill.return_value = {
            "success": True,
            "output": {"analysis": "测试结果"},
            "formatted_output": "## 分析结果",
            "token_usage": {"prompt_tokens": 100, "completion_tokens": 50},
        }
        MockEnhanced.return_value = mock_instance

        response = await async_client.post("/api/v1/skills/execute", json={
            "skillId": "product-analyst",
            "inputs": {"title": "测试产品"},
            "context": {"project_id": "proj-1"},
        })
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["data"]["success"] is True
        assert data["data"]["skillId"] == "product-analyst"
        assert "executionId" in data["data"]
        assert data["data"]["output"]["analysis"] == "测试结果"

        # Verify DB record
        result = await db_session.execute(
            select(SkillExecution).where(SkillExecution.skill_id == "product-analyst")
        )
        record = result.scalar_one_or_none()
        assert record is not None
        assert record.success is True


@pytest.mark.integration
async def test_execute_skill_not_found(async_client: AsyncClient):
    """POST execute for non-existent skill should return 404."""
    with patch("app.api.v1.endpoints.skills.skill_processor.get_skill_by_id") as mock_get:
        mock_get.return_value = None

        response = await async_client.post("/api/v1/skills/execute", json={
            "skillId": "non-existent",
            "inputs": {},
        })
        assert response.status_code == 404


# ============== /executions ==============

@pytest.mark.integration
async def test_get_skill_execution(async_client: AsyncClient, db_session: AsyncSession):
    """GET /api/v1/skills/executions/{id} should return execution status."""
    # Create a record directly
    record = SkillExecution(
        skill_id="skill-1",
        inputs={"title": "test"},
        output={"result": "done"},
        success=True,
        execution_time_ms=1234,
    )
    db_session.add(record)
    await db_session.commit()
    await db_session.refresh(record)

    response = await async_client.get(f"/api/v1/skills/executions/{record.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["skill_id"] == "skill-1"
    assert data["data"]["success"] is True


@pytest.mark.integration
async def test_get_skill_execution_not_found(async_client: AsyncClient):
    """GET non-existent execution should return 404."""
    response = await async_client.get("/api/v1/skills/executions/non-existent")
    assert response.status_code == 404


# ============== /agent-roles ==============

@pytest.mark.integration
async def test_get_agent_roles(async_client: AsyncClient):
    """GET /api/v1/skills/agent-roles should return all roles and skills."""
    with patch("app.api.v1.endpoints.skills.skill_processor.get_skills_by_role") as mock_get:
        mock_get.return_value = [{"id": "s1", "name": "技能"}]

        response = await async_client.get("/api/v1/skills/agent-roles")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "ceo" in data["data"]
        assert "designer" in data["data"]
        assert "medical-officer" in data["data"]


# ============== /examples/{id} ==============

@pytest.mark.integration
async def test_get_skill_examples(async_client: AsyncClient):
    """GET /api/v1/skills/examples/{id} should return examples."""
    with patch("app.api.v1.endpoints.skills.skill_processor.get_skill_by_id") as mock_get:
        mock_get.return_value = {"id": "s1", "examples": [{"input": {"title": "test"}, "output": "result"}]}

        response = await async_client.get("/api/v1/skills/examples/s1")
        assert response.status_code == 200
        assert len(response.json()["data"]) == 1


@pytest.mark.integration
async def test_get_skill_examples_not_found(async_client: AsyncClient):
    """GET examples for non-existent skill should return 404."""
    with patch("app.api.v1.endpoints.skills.skill_processor.get_skill_by_id") as mock_get:
        mock_get.return_value = None

        response = await async_client.get("/api/v1/skills/examples/non-existent")
        assert response.status_code == 404
