"""RAG retrieval endpoints tests"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from httpx import AsyncClient

from app.models.project import Project


# ============== /search ==============

@pytest.mark.integration
async def test_rag_search_returns_results(async_client: AsyncClient):
    """POST /api/v1/rag/search should return search results."""
    with patch("app.api.v1.endpoints.rag.get_retrieval_engine") as mock_get_engine:
        mock_engine = MagicMock()

        class FakeResult:
            doc_id = "doc1"
            content = "Obsidian 文档内容"
            score = 0.95
            metadata = {"filename": "test.md"}

        mock_engine.search.return_value = [FakeResult()]
        mock_get_engine.return_value = mock_engine

        response = await async_client.post("/api/v1/rag/search", json={
            "query": "PRD 是什么",
            "top_k": 3,
        })
        assert response.status_code == 200

        data = response.json()
        assert data["query"] == "PRD 是什么"
        assert len(data["results"]) == 1
        assert data["results"][0]["doc_id"] == "doc1"
        assert data["results"][0]["score"] == 0.95


@pytest.mark.integration
async def test_rag_search_empty_results(async_client: AsyncClient):
    """POST /api/v1/rag/search with no matches should return empty list."""
    with patch("app.api.v1.endpoints.rag.get_retrieval_engine") as mock_get_engine:
        mock_engine = MagicMock()
        mock_engine.search.return_value = []
        mock_get_engine.return_value = mock_engine

        response = await async_client.post("/api/v1/rag/search", json={
            "query": "不存在的查询",
            "top_k": 3,
        })
        assert response.status_code == 200
        assert response.json()["results"] == []


@pytest.mark.integration
async def test_rag_search_error(async_client: AsyncClient):
    """Search failure should return 500."""
    with patch("app.api.v1.endpoints.rag.get_retrieval_engine") as mock_get_engine:
        mock_engine = MagicMock()
        mock_engine.search.side_effect = Exception("引擎故障")
        mock_get_engine.return_value = mock_engine

        response = await async_client.post("/api/v1/rag/search", json={
            "query": "test",
            "top_k": 3,
        })
        assert response.status_code == 500


# ============== /query (alias) ==============

@pytest.mark.integration
async def test_rag_query_alias(async_client: AsyncClient):
    """POST /api/v1/rag/query is an alias for /search."""
    with patch("app.api.v1.endpoints.rag.get_retrieval_engine") as mock_get_engine:
        mock_engine = MagicMock()
        mock_engine.search.return_value = []
        mock_get_engine.return_value = mock_engine

        response = await async_client.post("/api/v1/rag/query", json={
            "query": "alias test",
            "top_k": 3,
        })
        assert response.status_code == 200


# ============== /memory-search ==============

@pytest.mark.integration
async def test_memory_search(async_client: AsyncClient):
    """POST /api/v1/rag/memory-search should return semantic search results."""
    with patch("app.services.memory_indexer.memory_indexer") as mock_indexer:
        mock_indexer.semantic_search = AsyncMock(return_value=[
            {
                "id": "mem1",
                "source_type": "prd",
                "source_id": "prd-123",
                "content": "PRD 内容片段",
                "score": 0.88,
                "metadata": {"title": "测试PRD"},
            }
        ])

        response = await async_client.post("/api/v1/rag/memory-search", json={
            "query": "用户登录",
            "top_k": 5,
            "source_type": "prd",
        })
        assert response.status_code == 200

        data = response.json()
        assert data["query"] == "用户登录"
        assert len(data["results"]) == 1
        assert data["results"][0]["source_type"] == "prd"
        assert data["results"][0]["score"] == 0.88


@pytest.mark.integration
async def test_memory_search_error(async_client: AsyncClient):
    """Memory search failure should return 500."""
    with patch("app.services.memory_indexer.memory_indexer") as mock_indexer:
        mock_indexer.semantic_search = AsyncMock(side_effect=Exception("索引故障"))

        response = await async_client.post("/api/v1/rag/memory-search", json={
            "query": "test",
            "top_k": 5,
        })
        assert response.status_code == 500


# ============== /memory-index ==============

@pytest.mark.integration
async def test_index_memory_document(async_client: AsyncClient):
    """POST /api/v1/rag/memory-index/{type}/{id} should index content."""
    with patch("app.services.memory_indexer.memory_indexer") as mock_indexer:
        mock_indexer.index_document = AsyncMock(return_value=3)

        response = await async_client.post("/api/v1/rag/memory-index/prd/prd-123", json={
            "content": "这是要索引的PRD内容",
            "metadata": {"title": "测试"},
        })
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["data"]["indexed_chunks"] == 3
        assert data["data"]["source_type"] == "prd"


@pytest.mark.integration
async def test_index_memory_document_missing_content(async_client: AsyncClient):
    """POST without content should return error."""
    response = await async_client.post("/api/v1/rag/memory-index/prd/prd-123", json={})
    assert response.status_code == 400
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "INVALID"


# ============== DELETE /memory-index ==============

@pytest.mark.integration
async def test_delete_memory_index(async_client: AsyncClient):
    """DELETE /api/v1/rag/memory-index/{type}/{id} should remove index."""
    with patch("app.services.memory_indexer.memory_indexer") as mock_indexer:
        mock_indexer.delete_document_index = AsyncMock(return_value=None)

        response = await async_client.delete("/api/v1/rag/memory-index/prd/prd-123")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert "索引已删除" in data["data"]["message"]