"""Code generation endpoints tests"""

import pytest
from unittest.mock import patch
from httpx import AsyncClient


# ============== /prototype ==============

@pytest.mark.integration
async def test_generate_prototype(async_client: AsyncClient):
    """POST /api/v1/code/prototype should return HTML files."""
    with patch("app.api.v1.endpoints.code.generate_prototype_from_prd") as mock_gen:
        mock_gen.return_value = {
            "files": {"index.html": "<html>test</html>", "styles.css": "", "scripts.js": ""},
            "metadata": {"name": "Test", "page_count": 1, "pages": []},
        }

        response = await async_client.post("/api/v1/code/prototype", json={
            "prd_content": "A" * 100,  # >50 chars
        })
        assert response.status_code == 200

        data = response.json()
        assert "files" in data
        assert "index.html" in data["files"]


@pytest.mark.integration
async def test_generate_prototype_too_short(async_client: AsyncClient):
    """POST with short PRD should return 400."""
    response = await async_client.post("/api/v1/code/prototype", json={
        "prd_content": "short",
    })
    assert response.status_code == 400


# ============== /prototype-ai ==============

@pytest.mark.integration
async def test_generate_prototype_ai(async_client: AsyncClient):
    """POST /api/v1/code/prototype-ai should return AI-enhanced HTML."""
    with patch("app.api.v1.endpoints.code.ai_service.chat", new_callable=AsyncMock) as mock_chat:
        mock_chat.return_value = "```html\n<html>AI原型</html>\n```"

        response = await async_client.post("/api/v1/code/prototype-ai", json={
            "prd_content": "A" * 100,
            "project_id": None,
        })
        assert response.status_code == 200

        data = response.json()
        assert "files" in data
        assert "index.html" in data["files"]
        assert "AI" in data["files"]["index.html"] or "html" in data["files"]["index.html"]


@pytest.mark.integration
async def test_generate_prototype_ai_no_code_block(async_client: AsyncClient):
    """AI response without code block should still produce valid HTML."""
    with patch("app.api.v1.endpoints.code.ai_service.chat", new_callable=AsyncMock) as mock_chat:
        mock_chat.return_value = "<div>Some content</div>"

        response = await async_client.post("/api/v1/code/prototype-ai", json={
            "prd_content": "A" * 100,
        })
        assert response.status_code == 200
        data = response.json()
        assert "files" in data
        # Should wrap in HTML structure if no code block
        assert "html" in data["files"]["index.html"].lower() or "<" in data["files"]["index.html"]


# ============== /api-spec ==============

@pytest.mark.integration
async def test_generate_api_spec(async_client: AsyncClient):
    """POST /api/v1/code/api-spec should return OpenAPI spec."""
    with patch("app.api.v1.endpoints.code.generate_api_from_prd") as mock_gen:
        mock_gen.return_value = {
            "openapi": {"openapi": "3.0.0", "paths": {}},
            "crud_files": {},
            "metadata": {"endpoint_count": 5, "schema_count": 3},
        }

        response = await async_client.post("/api/v1/code/api-spec", json={
            "prd_content": "A" * 100,
        })
        assert response.status_code == 200
        assert "openapi" in response.json()


# ============== /components ==============

@pytest.mark.integration
async def test_generate_components(async_client: AsyncClient):
    """POST /api/v1/code/components should return React components."""
    with patch("app.api.v1.endpoints.code.generate_components_from_prd") as mock_gen:
        mock_gen.return_value = {
            "components": [],
            "files": {},
            "metadata": {"total_count": 0},
        }

        response = await async_client.post("/api/v1/code/components", json={
            "prd_content": "A" * 100,
        })
        assert response.status_code == 200


# ============== /components/suggestions ==============

@pytest.mark.integration
async def test_get_component_suggestions(async_client: AsyncClient):
    """POST /api/v1/code/components/suggestions should return component list."""
    with patch("app.api.v1.endpoints.code.get_component_suggestions") as mock_gen:
        mock_gen.return_value = ["Button", "Modal", "Form"]

        response = await async_client.post("/api/v1/code/components/suggestions", json={
            "prd_content": "A" * 100,
        })
        assert response.status_code == 200
        assert response.json()["suggestions"] == ["Button", "Modal", "Form"]


# ============== /generate-all ==============

@pytest.mark.integration
async def test_generate_all(async_client: AsyncClient):
    """POST /api/v1/code/generate-all should return prototype + api + components."""
    with patch("app.api.v1.endpoints.code.generate_prototype_from_prd") as mock_proto, \
         patch("app.api.v1.endpoints.code.generate_api_from_prd") as mock_api, \
         patch("app.api.v1.endpoints.code.generate_components_from_prd") as mock_comp:
        mock_proto.return_value = {"metadata": {"page_count": 3}, "files": {}}
        mock_api.return_value = {"metadata": {"endpoint_count": 5, "schema_count": 2}, "openapi": {}, "crud_files": {}}
        mock_comp.return_value = {"metadata": {"total_count": 4}, "components": [], "files": {}}

        response = await async_client.post("/api/v1/code/generate-all", json={
            "prd_content": "A" * 100,
        })
        assert response.status_code == 200

        data = response.json()
        assert "prototype" in data
        assert "api_spec" in data
        assert "components" in data
        assert data["summary"]["pages"] == 3
        assert data["summary"]["endpoints"] == 5
        assert data["summary"]["components"] == 4


# ============== /export ==============

@pytest.mark.integration
async def test_export_code(async_client: AsyncClient):
    """POST /api/v1/code/export should accept valid formats."""
    for fmt in ["html", "zip", "json"]:
        response = await async_client.post("/api/v1/code/export", json={
            "format": fmt,
            "files": {"index.html": "test"},
        })
        assert response.status_code == 200, f"format={fmt} should succeed"
        assert fmt in response.json()["message"]


@pytest.mark.integration
async def test_export_code_invalid_format(async_client: AsyncClient):
    """POST with invalid format should return 400."""
    response = await async_client.post("/api/v1/code/export", json={
        "format": "exe",
        "files": {},
    })
    assert response.status_code == 400


# ============== /preview ==============

@pytest.mark.integration
async def test_preview_prototype(async_client: AsyncClient):
    """POST /api/v1/code/preview should merge HTML/CSS/JS."""
    response = await async_client.post("/api/v1/code/preview", json={
        "files": {
            "index.html": "<html><head></head><body>Hello</body></html>",
            "styles.css": "body { color: red; }",
            "scripts.js": "console.log('test');",
        },
        "device": "mobile",
    })
    assert response.status_code == 200

    data = response.json()
    assert data["html"] is not None
    assert "body { color: red; }" in data["html"]
    assert "console.log" in data["html"]
    assert data["device"] == "mobile"


@pytest.mark.integration
async def test_preview_empty_files(async_client: AsyncClient):
    """POST with empty files should return 400."""
    response = await async_client.post("/api/v1/code/preview", json={
        "files": {},
    })
    assert response.status_code == 400


# Need AsyncMock import
from unittest.mock import AsyncMock
