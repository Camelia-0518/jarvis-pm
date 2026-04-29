"""Health check endpoint tests"""

import pytest
from httpx import AsyncClient


@pytest.mark.integration
async def test_health_check(async_client: AsyncClient):
    """GET /health should return healthy status with services info."""
    response = await async_client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] in ("healthy", "unhealthy")
    assert "timestamp" in data
    assert "services" in data
    assert "database" in data["services"]
    assert "cache" in data["services"]


@pytest.mark.integration
async def test_readiness_check(async_client: AsyncClient):
    """GET /ready should return ready status."""
    response = await async_client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


@pytest.mark.integration
async def test_liveness_check(async_client: AsyncClient):
    """GET /alive should return alive status."""
    response = await async_client.get("/alive")
    assert response.status_code == 200
    assert response.json() == {"status": "alive"}


@pytest.mark.integration
async def test_root_endpoint(async_client: AsyncClient):
    """GET / should return app metadata."""
    response = await async_client.get("/")
    assert response.status_code == 200

    data = response.json()
    assert "name" in data
    assert "version" in data
    assert "health" in data


@pytest.mark.integration
async def test_health_llm_endpoint(async_client: AsyncClient):
    """GET /health/llm should return LLM provider status."""
    response = await async_client.get("/health/llm")
    assert response.status_code == 200

    data = response.json()
    assert "status" in data
    assert "default_provider" in data
    assert "available_providers" in data
    assert "real_ai_only" in data
