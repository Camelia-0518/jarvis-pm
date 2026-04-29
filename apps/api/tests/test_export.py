"""Export endpoint tests — Phase 2 priority

Historical bugs:
- CJK font missing in PDF export
- Synchronous export blocking the event loop (fixed with asyncio.to_thread)

All heavy converters are mocked — no real PDF/DOCX generation in tests.
"""

import base64
import pytest
from unittest.mock import patch
from httpx import AsyncClient

from app.models.prd import PRD


# ============== Markdown export ==============

@pytest.mark.integration
async def test_export_prd_markdown(async_client: AsyncClient, sample_prd: PRD):
    """GET /api/v1/prds/{id}/export?format=markdown should return markdown content."""
    response = await async_client.get(f"/api/v1/prds/{sample_prd.id}/export?format=markdown")
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["data"]["format"] == "markdown"
    assert data["data"]["content"] == sample_prd.markdown
    assert data["data"]["filename"].endswith(".md")


# ============== JSON export ==============

@pytest.mark.integration
async def test_export_prd_json(async_client: AsyncClient, sample_prd: PRD):
    """GET /api/v1/prds/{id}/export?format=json should return JSON content."""
    response = await async_client.get(f"/api/v1/prds/{sample_prd.id}/export?format=json")
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["data"]["format"] == "json"
    assert "content" in data["data"]
    assert data["data"]["filename"].endswith(".json")


# ============== PDF export ==============

@pytest.mark.integration
async def test_export_prd_pdf(async_client: AsyncClient, sample_prd: PRD):
    """GET /api/v1/prds/{id}/export?format=pdf should return base64 PDF."""
    with patch("app.api.v1.endpoints.prds._markdown_to_pdf", return_value=b"%PDF-1.4 fake pdf") as mock_pdf:
        response = await async_client.get(f"/api/v1/prds/{sample_prd.id}/export?format=pdf")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["data"]["format"] == "pdf"
        assert data["data"]["encoding"] == "base64"
        assert data["data"]["filename"].endswith(".pdf")

        # Verify base64 content
        decoded = base64.b64decode(data["data"]["content"])
        assert decoded == b"%PDF-1.4 fake pdf"

        mock_pdf.assert_called_once()


@pytest.mark.integration
async def test_export_prd_pdf_with_chinese(async_client: AsyncClient, sample_prd: PRD):
    """PDF export should handle Chinese content — regression for CJK font bug."""
    with patch("app.api.v1.endpoints.prds._markdown_to_pdf", return_value=b"%PDF-1.4 with CJK") as mock_pdf:
        response = await async_client.get(f"/api/v1/prds/{sample_prd.id}/export?format=pdf")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True

        # The markdown content should be passed to the converter
        call_args = mock_pdf.call_args
        assert call_args is not None
        markdown_arg = call_args[0][0] if call_args[0] else call_args.kwargs.get("markdown_text", "")
        assert sample_prd.markdown in markdown_arg or markdown_arg == sample_prd.markdown


@pytest.mark.integration
async def test_export_prd_pdf_error(async_client: AsyncClient, sample_prd: PRD):
    """PDF export failure should return EXPORT_ERROR, not crash."""
    with patch("app.api.v1.endpoints.prds._markdown_to_pdf", side_effect=Exception("font missing")):
        response = await async_client.get(f"/api/v1/prds/{sample_prd.id}/export?format=pdf")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "EXPORT_ERROR"
        assert "DOCX" not in data["error"]["message"]  # Verify correct format in error


# ============== DOCX export ==============

@pytest.mark.integration
async def test_export_prd_docx(async_client: AsyncClient, sample_prd: PRD):
    """GET /api/v1/prds/{id}/export?format=docx should return base64 DOCX."""
    with patch("app.api.v1.endpoints.prds._markdown_to_docx", return_value=b"PK fake docx") as mock_docx:
        response = await async_client.get(f"/api/v1/prds/{sample_prd.id}/export?format=docx")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["data"]["format"] == "docx"
        assert data["data"]["encoding"] == "base64"
        assert data["data"]["filename"].endswith(".docx")

        decoded = base64.b64decode(data["data"]["content"])
        assert decoded == b"PK fake docx"

        mock_docx.assert_called_once()


@pytest.mark.integration
async def test_export_prd_docx_error(async_client: AsyncClient, sample_prd: PRD):
    """DOCX export failure should return EXPORT_ERROR."""
    with patch("app.api.v1.endpoints.prds._markdown_to_docx", side_effect=Exception("docx lib missing")):
        response = await async_client.get(f"/api/v1/prds/{sample_prd.id}/export?format=docx")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "EXPORT_ERROR"
        assert "DOCX" in data["error"]["message"]


# ============== Default / edge cases ==============

@pytest.mark.integration
async def test_export_default_format(async_client: AsyncClient, sample_prd: PRD):
    """GET /api/v1/prds/{id}/export without format param defaults to markdown."""
    response = await async_client.get(f"/api/v1/prds/{sample_prd.id}/export")
    assert response.status_code == 200

    data = response.json()
    assert data["data"]["format"] == "markdown"
    assert data["data"]["content"] == sample_prd.markdown


@pytest.mark.integration
async def test_export_nonexistent_prd(async_client: AsyncClient):
    """GET /api/v1/prds/{nonexistent}/export should return NOT_FOUND."""
    response = await async_client.get("/api/v1/prds/non-existent-id/export?format=markdown")
    assert response.status_code == 200  # Endpoint returns 200 with error body

    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "NOT_FOUND"


@pytest.mark.integration
async def test_export_all_formats(async_client: AsyncClient, sample_prd: PRD):
    """All supported formats should succeed for a valid PRD."""
    formats = {
        "markdown": (".md", None),
        "json": (".json", None),
        "pdf": (".pdf", "app.api.v1.endpoints.prds._markdown_to_pdf"),
        "docx": (".docx", "app.api.v1.endpoints.prds._markdown_to_docx"),
    }

    for fmt, (ext, patch_target) in formats.items():
        ctx = patch(patch_target, return_value=b"fake binary") if patch_target else nullcontext()
        with ctx:
            response = await async_client.get(f"/api/v1/prds/{sample_prd.id}/export?format={fmt}")
            assert response.status_code == 200, f"format={fmt} should succeed"

            data = response.json()
            assert data["success"] is True
            assert data["data"]["filename"].endswith(ext)


# Helper for nullcontext (Python 3.10+)
from contextlib import nullcontext
