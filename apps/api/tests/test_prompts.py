"""Prompt template endpoint tests"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.prompt_template import PromptTemplate


@pytest.mark.integration
async def test_list_prompts_empty(async_client: AsyncClient):
    """GET /api/v1/prompts should return empty list when no prompts exist."""
    response = await async_client.get("/api/v1/prompts")
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["data"]["items"] == []
    assert data["data"]["total"] == 0


@pytest.mark.integration
async def test_create_prompt(async_client: AsyncClient):
    """POST /api/v1/prompts should create a new prompt."""
    payload = {
        "name": "test_prompt",
        "content": "This is a test prompt",
        "version": "1.0",
        "description": "Test description",
        "tags": ["test", "demo"],
    }
    response = await async_client.post("/api/v1/prompts", json=payload)
    assert response.status_code == 201

    data = response.json()
    assert data["success"] is True
    assert data["data"]["name"] == "test_prompt"
    assert data["data"]["content"] == "This is a test prompt"
    assert data["data"]["version"] == "1.0"
    assert data["data"]["is_active"] is False  # create_prompt defaults to inactive
    assert data["data"]["tags"] == ["test", "demo"]


@pytest.mark.integration
async def test_get_prompt(async_client: AsyncClient, db_session: AsyncSession):
    """GET /api/v1/prompts/{id} should return a prompt."""
    prompt = PromptTemplate(
        name="get_test",
        content="Get me",
        version="1.0",
        created_by="single-user",
    )
    db_session.add(prompt)
    await db_session.commit()
    await db_session.refresh(prompt)

    response = await async_client.get(f"/api/v1/prompts/{prompt.id}")
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["data"]["id"] == prompt.id
    assert data["data"]["name"] == "get_test"


@pytest.mark.integration
async def test_get_prompt_not_found(async_client: AsyncClient):
    """GET /api/v1/prompts/{id} should return 404 for non-existent prompt."""
    response = await async_client.get("/api/v1/prompts/non-existent-id")
    assert response.status_code == 404

    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "RES_001"


@pytest.mark.integration
async def test_update_prompt(async_client: AsyncClient, db_session: AsyncSession):
    """PUT /api/v1/prompts/{id} should update description and tags."""
    prompt = PromptTemplate(
        name="update_test",
        content="Update me",
        version="1.0",
        created_by="single-user",
    )
    db_session.add(prompt)
    await db_session.commit()
    await db_session.refresh(prompt)

    payload = {"description": "Updated description", "tags": ["updated"]}
    response = await async_client.put(f"/api/v1/prompts/{prompt.id}", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["data"]["description"] == "Updated description"
    assert data["data"]["tags"] == ["updated"]


@pytest.mark.integration
async def test_delete_prompt(async_client: AsyncClient, db_session: AsyncSession):
    """DELETE /api/v1/prompts/{id} should delete a prompt."""
    prompt = PromptTemplate(
        name="delete_test",
        content="Delete me",
        version="1.0",
        created_by="single-user",
    )
    db_session.add(prompt)
    await db_session.commit()
    await db_session.refresh(prompt)

    response = await async_client.delete(f"/api/v1/prompts/{prompt.id}")
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True

    # Verify deletion
    response = await async_client.get(f"/api/v1/prompts/{prompt.id}")
    assert response.status_code == 404


@pytest.mark.integration
async def test_activate_prompt(async_client: AsyncClient, db_session: AsyncSession):
    """POST /api/v1/prompts/{id}/activate should activate a prompt version."""
    # Create two versions of the same prompt
    v1 = PromptTemplate(
        name="activate_test",
        content="Version 1",
        version="1.0",
        is_active=True,
        created_by="single-user",
    )
    v2 = PromptTemplate(
        name="activate_test",
        content="Version 2",
        version="2.0",
        is_active=False,
        created_by="single-user",
    )
    db_session.add(v1)
    db_session.add(v2)
    await db_session.commit()
    await db_session.refresh(v1)
    await db_session.refresh(v2)

    response = await async_client.post(f"/api/v1/prompts/{v2.id}/activate")
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["data"]["is_active"] is True


@pytest.mark.integration
async def test_list_prompt_versions(async_client: AsyncClient, db_session: AsyncSession):
    """GET /api/v1/prompts/by-name/{name}/versions should list all versions."""
    v1 = PromptTemplate(
        name="version_test",
        content="Version 1",
        version="1.0",
        created_by="single-user",
    )
    v2 = PromptTemplate(
        name="version_test",
        content="Version 2",
        version="2.0",
        created_by="single-user",
    )
    db_session.add(v1)
    db_session.add(v2)
    await db_session.commit()

    response = await async_client.get("/api/v1/prompts/by-name/version_test/versions")
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert len(data["data"]) == 2


@pytest.mark.integration
async def test_list_prompts_filter_by_name(async_client: AsyncClient, db_session: AsyncSession):
    """GET /api/v1/prompts?name=... should filter by name."""
    p1 = PromptTemplate(name="alpha_prompt", content="Alpha", version="1.0", created_by="single-user")
    p2 = PromptTemplate(name="beta_prompt", content="Beta", version="1.0", created_by="single-user")
    db_session.add(p1)
    db_session.add(p2)
    await db_session.commit()

    response = await async_client.get("/api/v1/prompts?name=alpha_prompt")
    assert response.status_code == 200

    data = response.json()
    assert data["data"]["total"] == 1
    assert data["data"]["items"][0]["name"] == "alpha_prompt"