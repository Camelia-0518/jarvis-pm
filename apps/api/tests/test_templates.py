"""Template endpoints tests"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.template import Template


# ============== /templates ==============

@pytest.mark.integration
async def test_list_templates(async_client: AsyncClient, db_session: AsyncSession):
    """GET /api/v1/templates should return templates including builtins."""
    # Builtin templates are seeded on startup, but in tests we add one manually
    template = Template(name="Custom", industry="saas", chapters=["C1"], created_by="single-user")
    db_session.add(template)
    await db_session.commit()

    response = await async_client.get("/api/v1/templates")
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["data"]["total"] >= 1


@pytest.mark.integration
async def test_list_templates_with_industry_filter(async_client: AsyncClient, db_session: AsyncSession):
    """GET /api/v1/templates should filter by industry."""
    t1 = Template(name="T1", industry="saas", chapters=["C1"], created_by="single-user")
    t2 = Template(name="T2", industry="medical", chapters=["C1"], created_by="single-user")
    db_session.add_all([t1, t2])
    await db_session.commit()

    response = await async_client.get("/api/v1/templates?industry=medical")
    assert response.status_code == 200
    assert response.json()["data"]["total"] == 1
    assert response.json()["data"]["items"][0]["industry"] == "medical"


@pytest.mark.integration
async def test_create_template(async_client: AsyncClient):
    """POST /api/v1/templates should create a custom template."""
    response = await async_client.post("/api/v1/templates", json={
        "name": "My Template",
        "description": "A custom template",
        "industry": "saas",
        "chapters": ["Intro", "Details"],
        "icon": "📝",
        "color": "bg-blue-500",
    })
    assert response.status_code == 201

    data = response.json()
    assert data["success"] is True
    assert data["data"]["name"] == "My Template"
    assert data["data"]["is_builtin"] is False


@pytest.mark.integration
async def test_create_template_duplicate(async_client: AsyncClient, db_session: AsyncSession):
    """POST /api/v1/templates should reject duplicate names."""
    template = Template(name="Duplicate", industry="saas", chapters=["C1"], created_by="single-user")
    db_session.add(template)
    await db_session.commit()

    response = await async_client.post("/api/v1/templates", json={
        "name": "duplicate",  # case-insensitive check
        "industry": "saas",
        "chapters": ["C1"],
    })
    assert response.status_code == 409


@pytest.mark.integration
async def test_get_template(async_client: AsyncClient, db_session: AsyncSession):
    """GET /api/v1/templates/{id} should return template details."""
    template = Template(name="Get Test", industry="saas", chapters=["C1"], created_by="single-user")
    db_session.add(template)
    await db_session.commit()
    await db_session.refresh(template)

    response = await async_client.get(f"/api/v1/templates/{template.id}")
    assert response.status_code == 200
    assert response.json()["data"]["name"] == "Get Test"


@pytest.mark.integration
async def test_get_template_not_found(async_client: AsyncClient):
    """GET /api/v1/templates/{id} should 404 for unknown template."""
    response = await async_client.get("/api/v1/templates/non-existent")
    assert response.status_code == 404


@pytest.mark.integration
async def test_update_template(async_client: AsyncClient, db_session: AsyncSession):
    """PUT /api/v1/templates/{id} should update template fields."""
    template = Template(name="Original", industry="saas", chapters=["C1"], created_by="single-user")
    db_session.add(template)
    await db_session.commit()
    await db_session.refresh(template)

    response = await async_client.put(f"/api/v1/templates/{template.id}", json={
        "name": "Updated",
        "description": "Updated desc",
        "chapters": ["C1", "C2"],
    })
    assert response.status_code == 200
    assert response.json()["data"]["name"] == "Updated"


@pytest.mark.integration
async def test_delete_template(async_client: AsyncClient, db_session: AsyncSession):
    """DELETE /api/v1/templates/{id} should remove template."""
    template = Template(name="To Delete", industry="saas", chapters=["C1"], created_by="single-user")
    db_session.add(template)
    await db_session.commit()
    await db_session.refresh(template)

    response = await async_client.delete(f"/api/v1/templates/{template.id}")
    assert response.status_code == 200

    result = await db_session.execute(select(Template).where(Template.id == template.id))
    assert result.scalar_one_or_none() is None
