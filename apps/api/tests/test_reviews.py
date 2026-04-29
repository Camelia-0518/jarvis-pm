"""Review checklist endpoint tests"""

import pytest
from httpx import AsyncClient

from app.models.project import Project, ProjectStatus


# ============== Checklist Get ==============

@pytest.mark.integration
async def test_get_checklist_medical(async_client: AsyncClient, sample_project: Project):
    """GET /projects/{id}/reviews/checklist should return medical checklist."""
    response = await async_client.get(f"/api/v1/projects/{sample_project.id}/reviews/checklist")
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["data"]["project_id"] == sample_project.id
    assert "items" in data["data"]
    assert len(data["data"]["items"]) > 0


@pytest.mark.integration
async def test_get_checklist_saas(async_client: AsyncClient, db_session):
    """GET should return saas checklist for saas industry."""
    from sqlalchemy.ext.asyncio import AsyncSession
    project = Project(
        id="saas-proj-123",
        name="SaaS Project",
        industry="saas",
        status=ProjectStatus.ACTIVE,
        created_by="single-user",
    )
    db_session.add(project)
    await db_session.commit()

    response = await async_client.get("/api/v1/projects/saas-proj-123/reviews/checklist")
    assert response.status_code == 200

    data = response.json()
    assert data["data"]["industry"] == "saas"
    items = data["data"]["items"]
    assert len(items) > 0
    # SaaS checklist should have auth-related items
    categories = {item["category"] for item in items}
    assert "安全" in categories or "通用" in categories


@pytest.mark.integration
async def test_get_checklist_ecommerce(async_client: AsyncClient, db_session):
    """GET should return ecommerce checklist for ecommerce industry."""
    from sqlalchemy.ext.asyncio import AsyncSession
    project = Project(
        id="ecom-proj-123",
        name="Ecommerce Project",
        industry="ecommerce",
        status=ProjectStatus.ACTIVE,
        created_by="single-user",
    )
    db_session.add(project)
    await db_session.commit()

    response = await async_client.get("/api/v1/projects/ecom-proj-123/reviews/checklist")
    assert response.status_code == 200

    data = response.json()
    assert data["data"]["industry"] == "ecommerce"
    items = data["data"]["items"]
    categories = {item["category"] for item in items}
    assert "交易" in categories or "通用" in categories


@pytest.mark.integration
async def test_get_checklist_default_industry(async_client: AsyncClient, db_session):
    """GET should return default checklist for unknown industry."""
    from sqlalchemy.ext.asyncio import AsyncSession
    project = Project(
        id="unknown-proj-123",
        name="Unknown Project",
        industry="space_travel",
        status=ProjectStatus.ACTIVE,
        created_by="single-user",
    )
    db_session.add(project)
    await db_session.commit()

    response = await async_client.get("/api/v1/projects/unknown-proj-123/reviews/checklist")
    assert response.status_code == 200

    data = response.json()
    assert data["data"]["industry"] == "space_travel"
    assert len(data["data"]["items"]) > 0


@pytest.mark.integration
async def test_get_checklist_not_found(async_client: AsyncClient):
    """GET should return error for non-existent project."""
    response = await async_client.get("/api/v1/projects/non-existent-id/reviews/checklist")
    assert response.status_code == 200  # Endpoint returns 200 with error body

    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "NOT_FOUND"


# ============== Checklist Submit ==============

@pytest.mark.integration
async def test_submit_checklist_success(async_client: AsyncClient, sample_project: Project):
    """POST /projects/{id}/reviews/checklist should submit checklist results."""
    response = await async_client.get(f"/api/v1/projects/{sample_project.id}/reviews/checklist")
    items = response.json()["data"]["items"]

    payload = {
        "items": [
            {"item_id": items[0]["id"], "checked": True, "note": "Looks good"},
            {"item_id": items[1]["id"], "checked": False, "note": "Needs work"},
        ]
    }
    response = await async_client.post(
        f"/api/v1/projects/{sample_project.id}/reviews/checklist",
        json=payload,
    )
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["data"]["project_id"] == sample_project.id
    assert data["data"]["checked_count"] == 1
    assert data["data"]["total_items"] == len(items)
    assert "all_required_passed" in data["data"]


@pytest.mark.integration
async def test_submit_checklist_all_required_passed(async_client: AsyncClient, db_session):
    """POST should report all_required_passed when all required items checked."""
    from sqlalchemy.ext.asyncio import AsyncSession
    project = Project(
        id="check-proj-123",
        name="Check Project",
        industry="default",
        status=ProjectStatus.ACTIVE,
        created_by="single-user",
    )
    db_session.add(project)
    await db_session.commit()

    response = await async_client.get("/api/v1/projects/check-proj-123/reviews/checklist")
    items = response.json()["data"]["items"]

    # Check all required items
    required_items = [i for i in items if i["required"]]
    payload = {
        "items": [
            {"item_id": item["id"], "checked": True, "note": ""}
            for item in required_items
        ]
    }
    response = await async_client.post(
        "/api/v1/projects/check-proj-123/reviews/checklist",
        json=payload,
    )
    data = response.json()
    assert data["data"]["all_required_passed"] is True
    assert data["data"]["required_checked"] == len(required_items)


@pytest.mark.integration
async def test_submit_checklist_not_found(async_client: AsyncClient):
    """POST should return error for non-existent project."""
    payload = {"items": [{"item_id": "d1", "checked": True}]}
    response = await async_client.post(
        "/api/v1/projects/non-existent-id/reviews/checklist",
        json=payload,
    )
    assert response.status_code == 200  # Endpoint returns 200 with error body

    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "NOT_FOUND"
