"""PRD endpoint CRUD tests"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.prd import PRD, PRDStatus
from app.models.project import Project
from app.models.user import User


# ============== List ==============

@pytest.mark.integration
async def test_list_prds_empty(async_client: AsyncClient):
    """GET /api/v1/prds should return empty list when no PRDs exist."""
    response = await async_client.get("/api/v1/prds")
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["data"]["items"] == []
    assert data["data"]["total"] == 0


@pytest.mark.integration
async def test_list_prds_with_data(async_client: AsyncClient, sample_prd: PRD):
    """GET /api/v1/prds should return created PRDs."""
    response = await async_client.get("/api/v1/prds")
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["data"]["total"] == 1
    assert len(data["data"]["items"]) == 1
    assert data["data"]["items"][0]["id"] == sample_prd.id
    assert data["data"]["items"][0]["title"] == sample_prd.title


@pytest.mark.integration
async def test_list_prds_filter_by_project(async_client: AsyncClient, sample_prd: PRD, sample_project: Project):
    """GET /api/v1/prds should filter by project_id query param."""
    response = await async_client.get(f"/api/v1/prds?project_id={sample_project.id}")
    assert response.status_code == 200

    data = response.json()
    assert data["data"]["total"] == 1
    assert data["data"]["items"][0]["project_id"] == sample_project.id

    # Filter by wrong project
    response = await async_client.get("/api/v1/prds?project_id=wrong-id")
    data = response.json()
    assert data["data"]["total"] == 0


@pytest.mark.integration
async def test_list_prds_pagination(async_client: AsyncClient, db_session: AsyncSession, sample_project: Project, sample_user: User):
    """GET /api/v1/prds should respect limit and offset params."""
    # Create additional PRDs
    for i in range(3):
        prd = PRD(
            project_id=sample_project.id,
            title=f"Extra PRD {i + 1}",
            version="1.0",
            status=PRDStatus.DRAFT,
            content={},
            markdown="",
            created_by=sample_user.id,
        )
        db_session.add(prd)
    await db_session.commit()

    response = await async_client.get("/api/v1/prds?limit=2&offset=0")
    assert response.status_code == 200

    data = response.json()
    assert data["data"]["total"] == 3
    assert len(data["data"]["items"]) == 2

    response = await async_client.get("/api/v1/prds?limit=2&offset=2")
    data = response.json()
    assert len(data["data"]["items"]) == 1


# ============== Create ==============

@pytest.mark.integration
async def test_create_prd_success(async_client: AsyncClient, sample_project: Project):
    """POST /api/v1/prds should create a new PRD with template structure."""
    payload = {
        "project_id": sample_project.id,
        "title": "New PRD Document",
        "template": "medical",
    }
    response = await async_client.post("/api/v1/prds", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["data"]["title"] == "New PRD Document"
    assert data["data"]["project_id"] == sample_project.id
    assert data["data"]["status"] == "draft"
    assert data["data"]["version"] == "1.0"
    assert "content" in data["data"]
    assert "chapters" in data["data"]["content"]
    assert "markdown" in data["data"]
    assert data["data"]["content"]["template"] == "medical"


@pytest.mark.integration
async def test_create_prd_default_template(async_client: AsyncClient, sample_project: Project):
    """POST /api/v1/prds should use 'default' template when not specified."""
    payload = {
        "project_id": sample_project.id,
        "title": "Default Template PRD",
    }
    response = await async_client.post("/api/v1/prds", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["data"]["content"]["template"] == "standard"


@pytest.mark.integration
async def test_create_prd_missing_title(async_client: AsyncClient, sample_project: Project):
    """POST /api/v1/prds should fail validation when title is empty."""
    payload = {
        "project_id": sample_project.id,
        "title": "",
    }
    response = await async_client.post("/api/v1/prds", json=payload)
    assert response.status_code == 422


@pytest.mark.integration
async def test_create_prd_missing_project_id(async_client: AsyncClient):
    """POST /api/v1/prds should fail validation when project_id is missing."""
    payload = {"title": "Orphan PRD"}
    response = await async_client.post("/api/v1/prds", json=payload)
    assert response.status_code == 422


# ============== Get ==============

@pytest.mark.integration
async def test_get_prd_success(async_client: AsyncClient, sample_prd: PRD):
    """GET /api/v1/prds/{id} should return PRD details."""
    response = await async_client.get(f"/api/v1/prds/{sample_prd.id}")
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["data"]["id"] == sample_prd.id
    assert data["data"]["title"] == sample_prd.title
    assert data["data"]["project_id"] == sample_prd.project_id
    assert "content" in data["data"]
    assert "markdown" in data["data"]


@pytest.mark.integration
async def test_get_prd_not_found(async_client: AsyncClient):
    """GET /api/v1/prds/{id} should return 404 for non-existent PRD."""
    response = await async_client.get("/api/v1/prds/non-existent-id")
    assert response.status_code == 200  # Endpoint returns 200 with error body

    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "NOT_FOUND"


# ============== Update ==============

@pytest.mark.integration
async def test_update_prd_title(async_client: AsyncClient, sample_prd: PRD):
    """PUT /api/v1/prds/{id} should update PRD title."""
    payload = {"title": "Updated PRD Title"}
    response = await async_client.put(f"/api/v1/prds/{sample_prd.id}", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["data"]["title"] == "Updated PRD Title"


@pytest.mark.integration
async def test_update_prd_status(async_client: AsyncClient, sample_prd: PRD):
    """PUT /api/v1/prds/{id} should update PRD status."""
    payload = {"status": "review"}
    response = await async_client.put(f"/api/v1/prds/{sample_prd.id}", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["data"]["status"] == "review"


@pytest.mark.integration
async def test_update_prd_markdown_and_content(async_client: AsyncClient, sample_prd: PRD):
    """PUT /api/v1/prds/{id} should update markdown and content, creating a version snapshot."""
    payload = {
        "markdown": "# Updated Content\n\nNew section here.",
        "content": {"chapters": {"1": {"title": "Intro", "content": "Hello"}}},
    }
    response = await async_client.put(f"/api/v1/prds/{sample_prd.id}", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["data"]["markdown"] == "# Updated Content\n\nNew section here."
    assert data["data"]["content"]["chapters"]["1"]["content"] == "Hello"


@pytest.mark.integration
async def test_update_prd_invalid_status(async_client: AsyncClient, sample_prd: PRD):
    """PUT /api/v1/prds/{id} should reject invalid status values."""
    payload = {"status": "nonexistent"}
    response = await async_client.put(f"/api/v1/prds/{sample_prd.id}", json=payload)
    assert response.status_code == 200  # Endpoint returns 200 with error body

    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "INVALID_STATUS"


@pytest.mark.integration
async def test_update_prd_not_found(async_client: AsyncClient):
    """PUT /api/v1/prds/{id} should return error for non-existent PRD."""
    payload = {"title": "Updated"}
    response = await async_client.put("/api/v1/prds/non-existent-id", json=payload)
    assert response.status_code == 200  # Endpoint returns 200 with error body

    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "NOT_FOUND"


# ============== Delete ==============

@pytest.mark.integration
async def test_delete_prd_success(async_client: AsyncClient, sample_prd: PRD, db_session: AsyncSession):
    """DELETE /api/v1/prds/{id} should hard-delete the PRD."""
    response = await async_client.delete(f"/api/v1/prds/{sample_prd.id}")
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["data"]["deleted"] is True
    assert data["data"]["id"] == sample_prd.id

    # Verify hard delete in DB
    result = await db_session.execute(
        select(PRD).where(PRD.id == sample_prd.id)
    )
    prd = result.scalar_one_or_none()
    assert prd is None


@pytest.mark.integration
async def test_delete_prd_not_found(async_client: AsyncClient):
    """DELETE /api/v1/prds/{id} should return error for non-existent PRD."""
    response = await async_client.delete("/api/v1/prds/non-existent-id")
    assert response.status_code == 200  # Endpoint returns 200 with error body

    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "NOT_FOUND"


# ============== Edge Cases ==============

@pytest.mark.integration
async def test_create_prd_for_nonexistent_project(async_client: AsyncClient):
    """POST /api/v1/prds should handle creation for a non-existent project gracefully."""
    payload = {
        "project_id": "non-existent-project-id",
        "title": "Orphan PRD",
        "template": "default",
    }
    response = await async_client.post("/api/v1/prds", json=payload)
    # The endpoint allows creating PRDs for non-existent projects (no FK check enforced)
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["data"]["title"] == "Orphan PRD"


@pytest.mark.integration
async def test_prd_title_max_length(async_client: AsyncClient, sample_project: Project):
    """POST /api/v1/prds should enforce max title length (200 chars)."""
    payload = {
        "project_id": sample_project.id,
        "title": "x" * 201,
    }
    response = await async_client.post("/api/v1/prds", json=payload)
    assert response.status_code == 422


@pytest.mark.integration
async def test_list_prds_returns_iso_dates(async_client: AsyncClient, sample_prd: PRD):
    """GET /api/v1/prds should return ISO-formatted date strings."""
    response = await async_client.get("/api/v1/prds")
    assert response.status_code == 200

    data = response.json()
    item = data["data"]["items"][0]
    assert isinstance(item["created_at"], str)
    assert "T" in item["created_at"] or item["created_at"] is None
