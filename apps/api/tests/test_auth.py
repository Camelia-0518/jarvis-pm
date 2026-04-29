"""Auth endpoints tests"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User
from app.core.security import get_password_hash, create_access_token


@pytest.mark.integration
async def test_register(async_client: AsyncClient):
    """POST /api/v1/auth/register should create a new user."""
    response = await async_client.post("/api/v1/auth/register", json={
        "email": "newuser@example.com",
        "password": "securepassword123",
        "name": "New User",
    })
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["data"]["user"]["email"] == "newuser@example.com"
    assert "access_token" in data["data"]


@pytest.mark.integration
async def test_register_duplicate_email(async_client: AsyncClient, db_session: AsyncSession):
    """POST /api/v1/auth/register should reject duplicate email."""
    user = User(email="dup@example.com", hashed_password=get_password_hash("pass"), name="Dup", is_active=True)
    db_session.add(user)
    await db_session.commit()

    response = await async_client.post("/api/v1/auth/register", json={
        "email": "dup@example.com",
        "password": "securepassword123",
        "name": "Another",
    })
    assert response.status_code == 409


@pytest.mark.integration
async def test_register_validation_error(async_client: AsyncClient):
    """POST /api/v1/auth/register should validate input."""
    response = await async_client.post("/api/v1/auth/register", json={
        "email": "not-an-email",
        "password": "short",
        "name": "",
    })
    assert response.status_code == 422


@pytest.mark.integration
async def test_login(async_client: AsyncClient, db_session: AsyncSession):
    """POST /api/v1/auth/login should return token for valid credentials."""
    user = User(
        email="login@example.com",
        hashed_password=get_password_hash("mypassword123"),
        name="Login User",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()

    response = await async_client.post("/api/v1/auth/login", json={
        "email": "login@example.com",
        "password": "mypassword123",
    })
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert "access_token" in data["data"]
    assert data["data"]["user"]["email"] == "login@example.com"


@pytest.mark.integration
async def test_login_invalid_password(async_client: AsyncClient, db_session: AsyncSession):
    """POST /api/v1/auth/login should reject invalid password."""
    user = User(
        email="login2@example.com",
        hashed_password=get_password_hash("correctpass"),
        name="User",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()

    response = await async_client.post("/api/v1/auth/login", json={
        "email": "login2@example.com",
        "password": "wrongpass",
    })
    assert response.status_code == 401


@pytest.mark.integration
async def test_login_user_not_found(async_client: AsyncClient):
    """POST /api/v1/auth/login should reject non-existent user."""
    response = await async_client.post("/api/v1/auth/login", json={
        "email": "nobody@example.com",
        "password": "somepassword123",
    })
    assert response.status_code == 401


@pytest.mark.integration
async def test_get_me(async_client: AsyncClient, db_session: AsyncSession):
    """GET /api/v1/auth/me should return current user info."""
    user = User(
        id="single-user",
        email="me@example.com",
        hashed_password=get_password_hash("pass"),
        name="Me",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()

    response = await async_client.get("/api/v1/auth/me")
    assert response.status_code == 200
    assert response.json()["data"]["email"] == "me@example.com"


@pytest.mark.integration
async def test_get_me_default_user(async_client: AsyncClient):
    """GET /api/v1/auth/me should return default user when not in DB."""
    response = await async_client.get("/api/v1/auth/me")
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["id"] == "single-user"
    assert data["data"]["role"] == "admin"


@pytest.mark.integration
async def test_change_password(async_client: AsyncClient, db_session: AsyncSession):
    """PUT /api/v1/auth/me/password should update password."""
    user = User(
        id="single-user",
        email="pass@example.com",
        hashed_password=get_password_hash("oldpassword"),
        name="Pass User",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()

    response = await async_client.put("/api/v1/auth/me/password", json={
        "old_password": "oldpassword",
        "new_password": "newsecurepassword123",
    })
    assert response.status_code == 200
    assert response.json()["success"] is True

    # Verify new password works
    response = await async_client.post("/api/v1/auth/login", json={
        "email": "pass@example.com",
        "password": "newsecurepassword123",
    })
    assert response.status_code == 200


@pytest.mark.integration
async def test_change_password_wrong_old(async_client: AsyncClient, db_session: AsyncSession):
    """PUT /api/v1/auth/me/password should reject wrong old password."""
    user = User(
        id="single-user",
        email="pass2@example.com",
        hashed_password=get_password_hash("correct"),
        name="User",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()

    response = await async_client.put("/api/v1/auth/me/password", json={
        "old_password": "wrong",
        "new_password": "newpassword123",
    })
    assert response.status_code == 401


@pytest.mark.integration
async def test_refresh_token(async_client: AsyncClient, db_session: AsyncSession):
    """POST /api/v1/auth/refresh should return new access token."""
    user = User(
        id="single-user",
        email="refresh@example.com",
        hashed_password=get_password_hash("pass"),
        name="Refresh User",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()

    token = create_access_token({"sub": user.id})

    response = await async_client.post(
        "/api/v1/auth/refresh",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert "access_token" in response.json()["data"]


@pytest.mark.integration
async def test_refresh_token_invalid(async_client: AsyncClient):
    """POST /api/v1/auth/refresh should reject invalid token."""
    response = await async_client.post(
        "/api/v1/auth/refresh",
        headers={"Authorization": "Bearer invalid-token"},
    )
    assert response.status_code == 401
