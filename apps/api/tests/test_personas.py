"""Persona endpoint tests"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.persona import Persona
from app.models.project import Project


# ============== Create ==============

@pytest.mark.integration
async def test_create_persona_success(async_client: AsyncClient, sample_project: Project):
    """POST /projects/{id}/personas should create a persona."""
    payload = {
        "name": "护士",
        "role": "护理人员",
        "description": "住院部护士",
        "pain_points": "交接班信息不全",
        "goals": "减少重复录入",
        "scenarios": "晨间护理",
        "demographics": "25-40岁",
    }
    response = await async_client.post(f"/api/v1/projects/{sample_project.id}/personas", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["data"]["name"] == "护士"
    assert data["data"]["role"] == "护理人员"


@pytest.mark.integration
async def test_create_persona_project_not_found(async_client: AsyncClient):
    """POST should return error for non-existent project."""
    payload = {"name": "Test", "role": "User"}
    response = await async_client.post("/api/v1/projects/non-existent/personas", json=payload)
    assert response.status_code == 404  # Returns proper HTTP error status

    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "NOT_FOUND"


# ============== List ==============

@pytest.mark.integration
async def test_list_personas_empty(async_client: AsyncClient, sample_project: Project):
    """GET /projects/{id}/personas should return empty list."""
    response = await async_client.get(f"/api/v1/projects/{sample_project.id}/personas")
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["data"] == []


@pytest.mark.integration
async def test_list_personas_with_data(async_client: AsyncClient, sample_persona: Persona):
    """GET should return personas for project."""
    response = await async_client.get(f"/api/v1/projects/{sample_persona.project_id}/personas")
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert len(data["data"]) == 1
    assert data["data"][0]["id"] == sample_persona.id


@pytest.mark.integration
async def test_list_personas_wrong_project(async_client: AsyncClient, sample_persona: Persona):
    """GET should return error for project not owned."""
    response = await async_client.get("/api/v1/projects/non-existent/personas")
    assert response.status_code in (400, 404)  # Returns proper HTTP error status

    data = response.json()
    assert data["success"] is False


# ============== Get ==============

@pytest.mark.integration
async def test_get_persona_success(async_client: AsyncClient, sample_persona: Persona):
    """GET /personas/{id} should return persona details."""
    response = await async_client.get(f"/api/v1/personas/{sample_persona.id}")
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["data"]["id"] == sample_persona.id
    assert data["data"]["name"] == sample_persona.name


@pytest.mark.integration
async def test_get_persona_not_found(async_client: AsyncClient):
    """GET should return error for non-existent persona."""
    response = await async_client.get("/api/v1/personas/non-existent-id")
    assert response.status_code == 404  # Returns proper HTTP error status

    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "NOT_FOUND"


# ============== Update ==============

@pytest.mark.integration
async def test_update_persona_success(async_client: AsyncClient, sample_persona: Persona):
    """PUT /personas/{id} should update persona."""
    payload = {"name": "更新后的名字", "role": "新角色"}
    response = await async_client.put(f"/api/v1/personas/{sample_persona.id}", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["data"]["name"] == "更新后的名字"
    assert data["data"]["role"] == "新角色"


@pytest.mark.integration
async def test_update_persona_not_found(async_client: AsyncClient):
    """PUT should return error for non-existent persona."""
    payload = {"name": "Updated"}
    response = await async_client.put("/api/v1/personas/non-existent-id", json=payload)
    assert response.status_code == 404  # Returns proper HTTP error status

    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "NOT_FOUND"


# ============== Delete ==============

@pytest.mark.integration
async def test_delete_persona_success(async_client: AsyncClient, sample_persona: Persona, db_session: AsyncSession):
    """DELETE /personas/{id} should delete persona."""
    response = await async_client.delete(f"/api/v1/personas/{sample_persona.id}")
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True

    result = await db_session.execute(select(Persona).where(Persona.id == sample_persona.id))
    found = result.scalar_one_or_none()
    assert found is not None
    assert found.deleted_at is not None


@pytest.mark.integration
async def test_delete_persona_not_found(async_client: AsyncClient):
    """DELETE should return error for non-existent persona."""
    response = await async_client.delete("/api/v1/personas/non-existent-id")
    assert response.status_code == 404  # Returns proper HTTP error status

    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "NOT_FOUND"