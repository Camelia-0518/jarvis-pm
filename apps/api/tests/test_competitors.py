"""Competitor endpoints tests"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.competitor import Competitor
from app.models.project import Project
from app.models.user import User


# ============== Fixtures helper ==============

@pytest.fixture
async def sample_competitor(db_session: AsyncSession, sample_project: Project) -> Competitor:
    """Create a sample competitor."""
    c = Competitor(
        project_id=sample_project.id,
        created_by=sample_project.created_by,
        name="竞品A",
        description="主要竞品",
        strengths="品牌知名度高",
        weaknesses="价格昂贵",
        features=["功能1", "功能2"],
        pricing="999元/月",
        market_position="高端市场",
        source="公开信息",
    )
    db_session.add(c)
    await db_session.commit()
    await db_session.refresh(c)
    return c


# ============== List ==============

@pytest.mark.integration
async def test_list_competitors_empty(async_client: AsyncClient, sample_project: Project):
    """GET /api/v1/projects/{id}/competitors should return empty list."""
    response = await async_client.get(f"/api/v1/projects/{sample_project.id}/competitors")
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["data"] == []


@pytest.mark.integration
async def test_list_competitors_with_data(async_client: AsyncClient, sample_competitor: Competitor, sample_project: Project):
    """GET should return created competitors."""
    response = await async_client.get(f"/api/v1/projects/{sample_project.id}/competitors")
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert len(data["data"]) == 1
    assert data["data"][0]["name"] == "竞品A"
    assert data["data"][0]["project_id"] == sample_project.id


@pytest.mark.integration
async def test_list_competitors_project_not_found(async_client: AsyncClient):
    """GET for non-existent project should return NOT_FOUND."""
    response = await async_client.get("/api/v1/projects/non-existent/competitors")
    assert response.status_code == 404
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "NOT_FOUND"


# ============== Create ==============

@pytest.mark.integration
async def test_create_competitor(async_client: AsyncClient, sample_project: Project):
    """POST should create a new competitor."""
    payload = {
        "name": "竞品B",
        "description": "新竞品",
        "strengths": "用户体验好",
        "weaknesses": "功能单一",
        "features": ["核心功能"],
        "pricing": "免费",
        "market_position": "低端市场",
    }
    response = await async_client.post(f"/api/v1/projects/{sample_project.id}/competitors", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["data"]["name"] == "竞品B"
    assert data["data"]["project_id"] == sample_project.id
    assert data["data"]["features"] == ["核心功能"]


@pytest.mark.integration
async def test_create_competitor_minimal(async_client: AsyncClient, sample_project: Project):
    """POST with only name should succeed."""
    payload = {"name": "Minimal Competitor"}
    response = await async_client.post(f"/api/v1/projects/{sample_project.id}/competitors", json=payload)
    assert response.status_code == 200
    assert response.json()["success"] is True


@pytest.mark.integration
async def test_create_competitor_project_not_found(async_client: AsyncClient):
    """POST for non-existent project should return NOT_FOUND."""
    payload = {"name": "Test"}
    response = await async_client.post("/api/v1/projects/non-existent/competitors", json=payload)
    assert response.status_code == 404
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "NOT_FOUND"


# ============== Get ==============

@pytest.mark.integration
async def test_get_competitor(async_client: AsyncClient, sample_competitor: Competitor):
    """GET /api/v1/competitors/{id} should return competitor details."""
    response = await async_client.get(f"/api/v1/competitors/{sample_competitor.id}")
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["data"]["id"] == sample_competitor.id
    assert data["data"]["name"] == "竞品A"


@pytest.mark.integration
async def test_get_competitor_not_found(async_client: AsyncClient):
    """GET non-existent competitor should return NOT_FOUND."""
    response = await async_client.get("/api/v1/competitors/non-existent")
    assert response.status_code == 404
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "NOT_FOUND"


# ============== Update ==============

@pytest.mark.integration
async def test_update_competitor(async_client: AsyncClient, sample_competitor: Competitor):
    """PUT should update competitor fields."""
    payload = {
        "name": "竞品A-重命名",
        "pricing": "1999元/年",
    }
    response = await async_client.put(f"/api/v1/competitors/{sample_competitor.id}", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["data"]["name"] == "竞品A-重命名"
    assert data["data"]["pricing"] == "1999元/年"
    # Unchanged fields preserved
    assert data["data"]["description"] == "主要竞品"


@pytest.mark.integration
async def test_update_competitor_not_found(async_client: AsyncClient):
    """PUT for non-existent competitor should return NOT_FOUND."""
    response = await async_client.put("/api/v1/competitors/non-existent", json={"name": "x"})
    assert response.status_code == 404
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "NOT_FOUND"


# ============== Delete ==============

@pytest.mark.integration
async def test_delete_competitor(async_client: AsyncClient, sample_competitor: Competitor, db_session: AsyncSession):
    """DELETE should remove competitor."""
    response = await async_client.delete(f"/api/v1/competitors/{sample_competitor.id}")
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["data"]["deleted"] is True

    # Verify soft deletion — record still exists but deleted_at is set
    result = await db_session.execute(select(Competitor).where(Competitor.id == sample_competitor.id))
    found = result.scalar_one_or_none()
    assert found is not None
    assert found.deleted_at is not None


@pytest.mark.integration
async def test_delete_competitor_not_found(async_client: AsyncClient):
    """DELETE non-existent competitor should return NOT_FOUND."""
    response = await async_client.delete("/api/v1/competitors/non-existent")
    assert response.status_code == 404
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "NOT_FOUND"