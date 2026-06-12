"""Requirement endpoint tests"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.requirement import Requirement
from app.models.project import Project


# ============== Create ==============

@pytest.mark.integration
async def test_create_requirement_success(async_client: AsyncClient, sample_project: Project):
    """POST /projects/{id}/requirements should create a requirement."""
    payload = {
        "title": "支付功能",
        "description": "集成微信支付",
        "status": "backlog",
        "priority": "p0",
        "rice_reach": 500,
        "rice_impact": 3.0,
        "rice_confidence": 90,
        "rice_effort": 1.5,
        "kano_category": "must_be",
    }
    response = await async_client.post(f"/api/v1/projects/{sample_project.id}/requirements", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["data"]["title"] == "支付功能"
    assert data["data"]["rice_score"] > 0


@pytest.mark.integration
async def test_create_requirement_minimal(async_client: AsyncClient, sample_project: Project):
    """POST should work with minimal fields and calculate default RICE."""
    payload = {"title": "简单需求"}
    response = await async_client.post(f"/api/v1/projects/{sample_project.id}/requirements", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["data"]["title"] == "简单需求"
    assert data["data"]["status"] == "backlog"
    assert data["data"]["priority"] == "p1"


@pytest.mark.integration
async def test_create_requirement_project_not_found(async_client: AsyncClient):
    """POST should return error for non-existent project."""
    payload = {"title": "Orphan requirement"}
    response = await async_client.post("/api/v1/projects/non-existent/requirements", json=payload)
    assert response.status_code == 404  # Returns proper HTTP error status

    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "NOT_FOUND"


# ============== List ==============

@pytest.mark.integration
async def test_list_requirements_empty(async_client: AsyncClient, sample_project: Project):
    """GET /projects/{id}/requirements should return empty list."""
    response = await async_client.get(f"/api/v1/projects/{sample_project.id}/requirements")
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["data"] == []


@pytest.mark.integration
async def test_list_requirements_with_data(async_client: AsyncClient, sample_requirement: Requirement):
    """GET should return requirements."""
    response = await async_client.get(f"/api/v1/projects/{sample_requirement.project_id}/requirements")
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert len(data["data"]) == 1
    assert data["data"][0]["id"] == sample_requirement.id


@pytest.mark.integration
async def test_list_requirements_sort_by_rice(async_client: AsyncClient, db_session: AsyncSession, sample_project: Project):
    """GET should sort by rice_score."""
    r1 = Requirement(project_id=sample_project.id, created_by="single-user", title="Low", rice_score=10.0)
    r2 = Requirement(project_id=sample_project.id, created_by="single-user", title="High", rice_score=100.0)
    db_session.add_all([r1, r2])
    await db_session.commit()

    response = await async_client.get(f"/api/v1/projects/{sample_project.id}/requirements?sort_by=rice_score&order=desc")
    assert response.status_code == 200

    data = response.json()
    assert data["data"][0]["rice_score"] == 100.0
    assert data["data"][1]["rice_score"] == 10.0


# ============== Get ==============

@pytest.mark.integration
async def test_get_requirement_success(async_client: AsyncClient, sample_requirement: Requirement):
    """GET /requirements/{id} should return requirement details."""
    response = await async_client.get(f"/api/v1/requirements/{sample_requirement.id}")
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["data"]["id"] == sample_requirement.id
    assert data["data"]["title"] == sample_requirement.title


@pytest.mark.integration
async def test_get_requirement_not_found(async_client: AsyncClient):
    """GET should return error for non-existent requirement."""
    response = await async_client.get("/api/v1/requirements/non-existent-id")
    assert response.status_code == 404  # Returns proper HTTP error status

    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "NOT_FOUND"


# ============== Update ==============

@pytest.mark.integration
async def test_update_requirement_success(async_client: AsyncClient, sample_requirement: Requirement):
    """PUT /requirements/{id} should update fields and recalculate RICE."""
    payload = {
        "title": "更新后的需求",
        "rice_reach": 200,
        "rice_impact": 2.0,
        "rice_confidence": 100,
        "rice_effort": 1.0,
    }
    response = await async_client.put(f"/api/v1/requirements/{sample_requirement.id}", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["data"]["title"] == "更新后的需求"
    # RICE = 200 * 2.0 * (100/100) / 1.0 = 400
    assert data["data"]["rice_score"] == 400.0


@pytest.mark.integration
async def test_update_requirement_not_found(async_client: AsyncClient):
    """PUT should return error for non-existent requirement."""
    payload = {"title": "Updated"}
    response = await async_client.put("/api/v1/requirements/non-existent-id", json=payload)
    assert response.status_code == 404  # Returns proper HTTP error status

    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "NOT_FOUND"


# ============== Delete ==============

@pytest.mark.integration
async def test_delete_requirement_success(async_client: AsyncClient, sample_requirement: Requirement, db_session: AsyncSession):
    """DELETE /requirements/{id} should delete requirement."""
    response = await async_client.delete(f"/api/v1/requirements/{sample_requirement.id}")
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True

    result = await db_session.execute(select(Requirement).where(Requirement.id == sample_requirement.id))
    found = result.scalar_one_or_none()
    assert found is not None
    assert found.deleted_at is not None


@pytest.mark.integration
async def test_delete_requirement_not_found(async_client: AsyncClient):
    """DELETE should return error for non-existent requirement."""
    response = await async_client.delete("/api/v1/requirements/non-existent-id")
    assert response.status_code == 404  # Returns proper HTTP error status

    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "NOT_FOUND"


# ============== Priority Matrix ==============

@pytest.mark.integration
async def test_get_priority_matrix(async_client: AsyncClient, sample_requirement: Requirement):
    """GET /projects/{id}/requirements/priority-matrix should return matrix data."""
    response = await async_client.get(f"/api/v1/projects/{sample_requirement.project_id}/requirements/priority-matrix")
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["data"]["total"] == 1
    assert "rice_top" in data["data"]
    assert "kano_distribution" in data["data"]


@pytest.mark.integration
async def test_get_priority_matrix_not_found(async_client: AsyncClient):
    """GET should return error for non-existent project."""
    response = await async_client.get("/api/v1/projects/non-existent/requirements/priority-matrix")
    assert response.status_code == 404  # Returns proper HTTP error status

    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "NOT_FOUND"