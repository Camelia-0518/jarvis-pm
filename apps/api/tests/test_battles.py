"""Battle (Campaign) endpoints tests"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.battle import Battle, BattleStatus
from app.models.project import Project


# ============== /battles ==============

@pytest.mark.integration
async def test_list_battles_empty(async_client: AsyncClient):
    """GET /api/v1/battles should return empty list when no battles."""
    response = await async_client.get("/api/v1/battles")
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["data"]["total"] == 0
    assert data["data"]["items"] == []


@pytest.mark.integration
async def test_create_battle(async_client: AsyncClient, sample_project: Project):
    """POST /api/v1/battles should create a new battle."""
    response = await async_client.post("/api/v1/battles", json={
        "name": "Sprint Campaign",
        "description": "A test battle campaign",
        "project_id": sample_project.id,
    })
    assert response.status_code == 201

    data = response.json()
    assert data["success"] is True
    assert data["data"]["name"] == "Sprint Campaign"
    assert data["data"]["status"] == "active"
    assert data["data"]["current_day"] == 1
    assert data["data"]["total_days"] == 5
    assert len(data["data"]["days"]) == 5


@pytest.mark.integration
async def test_create_battle_with_custom_days(async_client: AsyncClient):
    """POST /api/v1/battles should support custom days."""
    response = await async_client.post("/api/v1/battles", json={
        "name": "Custom Battle",
        "description": "With custom days",
        "days": [
            {"day": "Day 1", "task": "调研", "status": "pending", "tool": "research", "notes": ""},
            {"day": "Day 2", "task": "设计", "status": "pending", "tool": "design", "notes": ""},
        ],
    })
    assert response.status_code == 201

    data = response.json()
    assert data["data"]["total_days"] == 2
    assert len(data["data"]["days"]) == 2


@pytest.mark.integration
async def test_create_battle_invalid_project(async_client: AsyncClient):
    """POST /api/v1/battles should 404 for non-existent project."""
    response = await async_client.post("/api/v1/battles", json={
        "name": "Invalid Battle",
        "project_id": "non-existent-project-id",
    })
    assert response.status_code == 404


@pytest.mark.integration
async def test_list_battles_with_data(async_client: AsyncClient, db_session: AsyncSession, sample_project: Project):
    """GET /api/v1/battles should return created battles."""
    battle = Battle(
        name="Test Battle",
        description="A battle for testing",
        created_by="single-user",
        project_id=sample_project.id,
        status=BattleStatus.ACTIVE,
        current_day=1,
        total_days=5,
    )
    db_session.add(battle)
    await db_session.commit()

    response = await async_client.get("/api/v1/battles")
    assert response.status_code == 200

    data = response.json()
    assert data["data"]["total"] == 1
    assert data["data"]["items"][0]["name"] == "Test Battle"


@pytest.mark.integration
async def test_list_battles_with_status_filter(async_client: AsyncClient, db_session: AsyncSession):
    """GET /api/v1/battles should filter by status."""
    battle = Battle(
        name="Completed Battle",
        description="Done",
        created_by="single-user",
        status=BattleStatus.COMPLETED,
        current_day=5,
        total_days=5,
    )
    db_session.add(battle)
    await db_session.commit()

    response = await async_client.get("/api/v1/battles?status_filter=completed")
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["total"] == 1
    assert data["data"]["items"][0]["status"] == "completed"


# ============== /battles/{battle_id} ==============

@pytest.mark.integration
async def test_get_battle(async_client: AsyncClient, db_session: AsyncSession, sample_project: Project):
    """GET /api/v1/battles/{id} should return battle details."""
    battle = Battle(
        name="Get Battle Test",
        description="Testing get",
        created_by="single-user",
        project_id=sample_project.id,
        status=BattleStatus.ACTIVE,
        current_day=2,
        total_days=5,
    )
    db_session.add(battle)
    await db_session.commit()
    await db_session.refresh(battle)

    response = await async_client.get(f"/api/v1/battles/{battle.id}")
    assert response.status_code == 200

    data = response.json()
    assert data["data"]["name"] == "Get Battle Test"
    assert data["data"]["current_day"] == 2


@pytest.mark.integration
async def test_get_battle_not_found(async_client: AsyncClient):
    """GET /api/v1/battles/{id} should 404 for unknown battle."""
    response = await async_client.get("/api/v1/battles/non-existent-id")
    assert response.status_code == 404


# ============== /battles/{battle_id} (PUT) ==============

@pytest.mark.integration
async def test_update_battle(async_client: AsyncClient, db_session: AsyncSession):
    """PUT /api/v1/battles/{id} should update battle fields."""
    battle = Battle(
        name="Original Name",
        description="Original desc",
        created_by="single-user",
        status=BattleStatus.ACTIVE,
        current_day=1,
        total_days=5,
    )
    db_session.add(battle)
    await db_session.commit()
    await db_session.refresh(battle)

    response = await async_client.put(f"/api/v1/battles/{battle.id}", json={
        "name": "Updated Name",
        "description": "Updated desc",
        "status": "completed",
        "current_day": 3,
    })
    assert response.status_code == 200

    data = response.json()
    assert data["data"]["name"] == "Updated Name"
    assert data["data"]["status"] == "completed"
    assert data["data"]["current_day"] == 3


@pytest.mark.integration
async def test_update_battle_not_found(async_client: AsyncClient):
    """PUT /api/v1/battles/{id} should 404 for unknown battle."""
    response = await async_client.put("/api/v1/battles/non-existent-id", json={
        "name": "Updated",
    })
    assert response.status_code == 404


# ============== /battles/{battle_id} (DELETE) ==============

@pytest.mark.integration
async def test_delete_battle(async_client: AsyncClient, db_session: AsyncSession):
    """DELETE /api/v1/battles/{id} should remove battle."""
    battle = Battle(
        name="To Delete",
        description="Will be deleted",
        created_by="single-user",
        status=BattleStatus.ACTIVE,
        current_day=1,
        total_days=5,
    )
    db_session.add(battle)
    await db_session.commit()
    await db_session.refresh(battle)

    response = await async_client.delete(f"/api/v1/battles/{battle.id}")
    assert response.status_code == 200
    assert response.json()["data"]["deleted"] is True

    # Verify deletion
    result = await db_session.execute(select(Battle).where(Battle.id == battle.id))
    assert result.scalar_one_or_none() is None


@pytest.mark.integration
async def test_delete_battle_not_found(async_client: AsyncClient):
    """DELETE /api/v1/battles/{id} should 404 for unknown battle."""
    response = await async_client.delete("/api/v1/battles/non-existent-id")
    assert response.status_code == 404


# ============== /battles/{battle_id}/advance ==============

@pytest.mark.integration
async def test_advance_battle(async_client: AsyncClient, db_session: AsyncSession, sample_project: Project):
    """POST /api/v1/battles/{id}/advance should advance to next day."""
    battle = Battle(
        name="Advance Test",
        description="Testing advance",
        created_by="single-user",
        project_id=sample_project.id,
        status=BattleStatus.ACTIVE,
        current_day=1,
        total_days=5,
        days=[
            {"day": "Day 1", "task": "用户调研", "status": "completed", "tool": "research", "notes": ""},
            {"day": "Day 2", "task": "竞品分析", "status": "pending", "tool": "research", "notes": ""},
        ],
    )
    db_session.add(battle)
    await db_session.commit()
    await db_session.refresh(battle)

    response = await async_client.post(f"/api/v1/battles/{battle.id}/advance")
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    # Should advance current_day or mark battle as completed


@pytest.mark.integration
async def test_advance_battle_not_found(async_client: AsyncClient):
    """POST /api/v1/battles/{id}/advance should 404 for unknown battle."""
    response = await async_client.post("/api/v1/battles/non-existent-id/advance")
    assert response.status_code == 404
