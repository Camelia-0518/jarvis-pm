"""Project endpoints tests"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.project import Project, ProjectStatus
from app.models.prd import PRD, PRDStatus


# ============== /projects ==============

@pytest.mark.integration
async def test_list_projects_empty(async_client: AsyncClient):
    """GET /api/v1/projects should return empty list."""
    response = await async_client.get("/api/v1/projects")
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["data"]["total"] == 0
    assert data["data"]["items"] == []


@pytest.mark.integration
async def test_list_projects_with_data(async_client: AsyncClient, db_session: AsyncSession):
    """GET /api/v1/projects should return created projects."""
    project = Project(
        name="Test Project",
        description="A test project",
        industry="saas",
        status=ProjectStatus.ACTIVE,
        created_by="single-user",
    )
    db_session.add(project)
    await db_session.commit()

    response = await async_client.get("/api/v1/projects")
    assert response.status_code == 200

    data = response.json()
    assert data["data"]["total"] == 1
    assert data["data"]["items"][0]["name"] == "Test Project"


@pytest.mark.integration
async def test_list_projects_with_filters(async_client: AsyncClient, db_session: AsyncSession):
    """GET /api/v1/projects should support status and industry filters."""
    p1 = Project(name="P1", industry="saas", status=ProjectStatus.ACTIVE, created_by="single-user")
    p2 = Project(name="P2", industry="medical", status=ProjectStatus.ARCHIVED, created_by="single-user")
    db_session.add_all([p1, p2])
    await db_session.commit()

    response = await async_client.get("/api/v1/projects?status=active")
    assert response.json()["data"]["total"] == 1

    response = await async_client.get("/api/v1/projects?industry=medical")
    assert response.json()["data"]["total"] == 1

    response = await async_client.get("/api/v1/projects?status=active&industry=saas")
    assert response.json()["data"]["total"] == 1


@pytest.mark.integration
async def test_create_project(async_client: AsyncClient):
    """POST /api/v1/projects should create a project."""
    response = await async_client.post("/api/v1/projects", json={
        "name": "New Project",
        "description": "A new project",
        "industry": "saas",
    })
    assert response.status_code == 201

    data = response.json()
    assert data["success"] is True
    assert data["data"]["name"] == "New Project"
    assert data["data"]["status"] == "active"


@pytest.mark.integration
async def test_create_project_duplicate(async_client: AsyncClient, db_session: AsyncSession):
    """POST /api/v1/projects should reject duplicate names."""
    project = Project(name="Duplicate", industry="saas", status=ProjectStatus.ACTIVE, created_by="single-user")
    db_session.add(project)
    await db_session.commit()

    response = await async_client.post("/api/v1/projects", json={
        "name": "Duplicate",
        "industry": "saas",
    })
    assert response.status_code == 409


@pytest.mark.integration
async def test_get_project(async_client: AsyncClient, db_session: AsyncSession):
    """GET /api/v1/projects/{id} should return project details."""
    project = Project(name="Get Test", industry="saas", status=ProjectStatus.ACTIVE, created_by="single-user")
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

    response = await async_client.get(f"/api/v1/projects/{project.id}")
    assert response.status_code == 200

    data = response.json()
    assert data["data"]["name"] == "Get Test"


@pytest.mark.integration
async def test_get_project_not_found(async_client: AsyncClient):
    """GET /api/v1/projects/{id} should 404 for unknown project."""
    response = await async_client.get("/api/v1/projects/non-existent")
    assert response.status_code == 404


@pytest.mark.integration
async def test_update_project(async_client: AsyncClient, db_session: AsyncSession):
    """PUT /api/v1/projects/{id} should update project fields."""
    project = Project(name="Original", industry="saas", status=ProjectStatus.ACTIVE, created_by="single-user")
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

    response = await async_client.put(f"/api/v1/projects/{project.id}", json={
        "name": "Updated",
        "description": "Updated desc",
        "industry": "medical",
        "status": "archived",
    })
    assert response.status_code == 200

    data = response.json()
    assert data["data"]["name"] == "Updated"
    assert data["data"]["industry"] == "medical"


@pytest.mark.integration
async def test_delete_project(async_client: AsyncClient, db_session: AsyncSession):
    """DELETE /api/v1/projects/{id} should soft-delete project."""
    project = Project(name="To Delete", industry="saas", status=ProjectStatus.ACTIVE, created_by="single-user")
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

    response = await async_client.delete(f"/api/v1/projects/{project.id}")
    assert response.status_code == 200

    # Verify soft delete
    result = await db_session.execute(select(Project).where(Project.id == project.id))
    assert result.scalar_one().status == ProjectStatus.DELETED


@pytest.mark.integration
async def test_get_project_stats(async_client: AsyncClient, db_session: AsyncSession):
    """GET /api/v1/projects/{id}/stats should return project stats."""
    project = Project(name="Stats Test", industry="saas", status=ProjectStatus.ACTIVE, created_by="single-user")
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

    # Add a PRD
    prd = PRD(project_id=project.id, title="Test PRD", version="1.0", status=PRDStatus.DRAFT, created_by="single-user")
    db_session.add(prd)
    await db_session.commit()

    response = await async_client.get(f"/api/v1/projects/{project.id}/stats")
    assert response.status_code == 200
    assert response.json()["success"] is True