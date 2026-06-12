"""Feedback endpoint tests"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.feedback import Feedback


# ============== Create ==============

@pytest.mark.integration
async def test_create_feedback_success(async_client: AsyncClient):
    """POST /api/v1/feedback should create feedback."""
    payload = {
        "category": "feature",
        "content": "希望增加深色模式",
        "rating": 5,
        "context": "settings page",
    }
    response = await async_client.post("/api/v1/feedback", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert "id" in data["data"]
    assert "感谢" in data["data"]["message"]


@pytest.mark.integration
async def test_create_feedback_minimal(async_client: AsyncClient):
    """POST should work with only required fields."""
    payload = {"category": "bug", "content": "页面加载慢"}
    response = await async_client.post("/api/v1/feedback", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True


@pytest.mark.integration
async def test_create_feedback_invalid_category(async_client: AsyncClient):
    """POST should reject invalid category."""
    payload = {"category": "invalid", "content": "test"}
    response = await async_client.post("/api/v1/feedback", json=payload)
    assert response.status_code == 422


@pytest.mark.integration
async def test_create_feedback_empty_content(async_client: AsyncClient):
    """POST should reject empty content."""
    payload = {"category": "bug", "content": ""}
    response = await async_client.post("/api/v1/feedback", json=payload)
    assert response.status_code == 422


@pytest.mark.integration
async def test_create_feedback_rating_out_of_range(async_client: AsyncClient):
    """POST should reject rating > 5."""
    payload = {"category": "bug", "content": "test", "rating": 6}
    response = await async_client.post("/api/v1/feedback", json=payload)
    assert response.status_code == 422


# ============== List ==============

@pytest.mark.integration
async def test_list_feedback_empty(async_client: AsyncClient):
    """GET /api/v1/feedback should return empty list."""
    response = await async_client.get("/api/v1/feedback")
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["data"]["items"] == []
    assert data["data"]["total"] == 0


@pytest.mark.integration
async def test_list_feedback_with_data(async_client: AsyncClient, sample_feedback: Feedback):
    """GET should return created feedback."""
    response = await async_client.get("/api/v1/feedback")
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["data"]["total"] == 1
    assert data["data"]["items"][0]["id"] == sample_feedback.id
    assert data["data"]["items"][0]["content"] == sample_feedback.content


@pytest.mark.integration
async def test_list_feedback_filter_by_category(async_client: AsyncClient, db_session: AsyncSession):
    """GET should filter by category."""
    fb1 = Feedback(user_id="single-user", category="bug", content="bug report")
    fb2 = Feedback(user_id="single-user", category="feature", content="feature request")
    db_session.add_all([fb1, fb2])
    await db_session.commit()

    response = await async_client.get("/api/v1/feedback?category=bug")
    assert response.status_code == 200

    data = response.json()
    assert data["data"]["total"] == 1
    assert data["data"]["items"][0]["category"] == "bug"


@pytest.mark.integration
async def test_list_feedback_pagination(async_client: AsyncClient, db_session: AsyncSession):
    """GET should respect limit and offset."""
    for i in range(3):
        db_session.add(Feedback(user_id="single-user", category="other", content=f"fb {i}"))
    await db_session.commit()

    response = await async_client.get("/api/v1/feedback?limit=2&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["total"] == 3
    assert len(data["data"]["items"]) == 2