"""AI endpoint tests — Phase 2 priority (historical bug-prone area)

Covers: chat, optimize-prompt, generate-prd, generate-prd-stream,
        review-materials, chat/stream SSE.

All AI calls are mocked (AsyncMock) — no real LLM requests in tests.
"""

import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient

from app.models.prd import PRD
from app.models.project import Project


# ============== Helpers ==============

def _sse_lines(response_text: str) -> list[dict]:
    """Parse SSE response text into list of JSON payloads."""
    lines = []
    for line in response_text.strip().split("\n"):
        line = line.strip()
        if line.startswith("data: "):
            payload = json.loads(line[6:].strip())
            lines.append(payload)
    return lines


# ============== /chat ==============

@pytest.mark.integration
async def test_chat_success(async_client: AsyncClient, sample_project: Project):
    """POST /api/v1/ai/chat should return AI response."""
    with patch("app.api.v1.endpoints.ai.ai_service.chat", new_callable=AsyncMock) as mock_chat, \
         patch("app.api.v1.endpoints.ai.retrieval_engine.search") as mock_search:
        mock_chat.return_value = "这是AI的回复"
        mock_search.return_value = []

        response = await async_client.post("/api/v1/ai/chat", json={
            "message": "Hello",
            "context": {"conversation_id": "test-session"}
        })
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["data"]["response"] == "这是AI的回复"
        assert data["data"]["reply"] == "这是AI的回复"
        mock_chat.assert_awaited_once()


@pytest.mark.integration
async def test_chat_with_rag_context(async_client: AsyncClient, sample_project: Project):
    """POST /api/v1/ai/chat should inject RAG context when results exist."""
    with patch("app.api.v1.endpoints.ai.ai_service.chat", new_callable=AsyncMock) as mock_chat, \
         patch("app.api.v1.endpoints.ai.retrieval_engine.search") as mock_search:
        mock_chat.return_value = "RAG增强回复"

        class FakeResult:
            doc_id = "doc1"
            content = "这是Obsidian文档的内容"
            metadata = {"filename": "test.md"}

        mock_search.return_value = [FakeResult()]

        response = await async_client.post("/api/v1/ai/chat", json={
            "message": "什么是PRD",
        })
        assert response.status_code == 200

        # Verify chat was called with RAG context in system_prompt
        call_args = mock_chat.call_args
        context_arg = call_args[0][1] if len(call_args[0]) > 1 else call_args.kwargs.get("context", {})
        system_prompt = context_arg.get("system_prompt", "")
        assert "参考资料" in system_prompt


# ============== /optimize-prompt ==============

@pytest.mark.integration
async def test_optimize_prompt(async_client: AsyncClient):
    """POST /api/v1/ai/optimize-prompt should return structured prompt data."""
    with patch("app.api.v1.endpoints.ai.ai_service.optimize_prompt", new_callable=AsyncMock) as mock_opt:
        mock_opt.return_value = {
            "task_type": "prd",
            "structured_prompt": "## 结构化提示词",
            "next_steps": "Review and refine"
        }

        response = await async_client.post("/api/v1/ai/optimize-prompt", json={
            "input": "帮我写个登录功能",
        })
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["data"]["task_type"] == "prd"
        assert data["data"]["structured_prompt"] == "## 结构化提示词"
        assert data["data"]["next_steps"] == "Review and refine"


@pytest.mark.integration
async def test_optimize_prompt_fallback(async_client: AsyncClient):
    """optimize-prompt should use input as fallback when LLM returns unexpected data."""
    with patch("app.api.v1.endpoints.ai.ai_service.optimize_prompt", new_callable=AsyncMock) as mock_opt:
        # Simulate LLM returning incomplete data (no structured_prompt)
        mock_opt.return_value = {"task_type": "general"}

        response = await async_client.post("/api/v1/ai/optimize-prompt", json={
            "input": "帮我写个登录功能",
        })
        assert response.status_code == 200

        data = response.json()
        assert data["data"]["structured_prompt"] == "帮我写个登录功能"


# ============== /generate-prd ==============

@pytest.mark.integration
async def test_generate_prd(async_client: AsyncClient):
    """POST /api/v1/ai/generate-prd should return PRD structure."""
    with patch("app.api.v1.endpoints.ai.ai_service.generate_prd", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = {
            "outline": {"sections": [{"chapter": 1, "title": "背景"}]},
            "content": {"background": {"executive_summary": "摘要"}},
            "suggestions": ["建议1"]
        }

        response = await async_client.post("/api/v1/ai/generate-prd", json={
            "title": "测试PRD",
            "description": "测试描述",
            "industry": "saas",
        })
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["data"]["outline"]["sections"][0]["title"] == "背景"


# ============== /generate-prd-stream ==============

@pytest.mark.integration
async def test_generate_prd_stream(async_client: AsyncClient):
    """POST /api/v1/ai/generate-prd-stream should return SSE with chunks + done."""
    async def fake_stream(*args, **kwargs):
        yield "# 测试PRD"
        yield "\n\n## 背景"
        yield "\n测试内容"

    with patch("app.api.v1.endpoints.ai.ai_service.generate_prd_stream", side_effect=fake_stream):
        response = await async_client.post("/api/v1/ai/generate-prd-stream", json={
            "title": "测试PRD",
            "description": "测试描述",
        })
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")

        text = response.text
        events = _sse_lines(text)

        # Should have chunk events
        chunk_events = [e for e in events if e.get("type") == "chunk"]
        assert len(chunk_events) >= 1

        # Should have done event with markdown
        done_events = [e for e in events if e.get("type") == "done"]
        assert len(done_events) == 1
        assert done_events[0]["markdown"] == "# 测试PRD\n\n## 背景\n测试内容"


@pytest.mark.integration
async def test_generate_prd_stream_done_has_markdown(async_client: AsyncClient):
    """SSE done event must contain full markdown — regression for empty markdown bug."""
    async def fake_stream(*args, **kwargs):
        yield "Hello"
        yield " World"

    with patch("app.api.v1.endpoints.ai.ai_service.generate_prd_stream", side_effect=fake_stream):
        response = await async_client.post("/api/v1/ai/generate-prd-stream", json={
            "title": "测试",
            "description": "测试",
        })
        assert response.status_code == 200

        events = _sse_lines(response.text)
        done_events = [e for e in events if e.get("type") == "done"]
        assert len(done_events) == 1
        # Critical: done event must have non-empty markdown
        assert done_events[0]["markdown"] == "Hello World"
        assert done_events[0]["markdown"] != ""


# ============== /review-materials ==============

@pytest.mark.integration
async def test_review_materials(async_client: AsyncClient, sample_project: Project):
    """POST /api/v1/ai/review-materials should return review material."""
    with patch("app.api.v1.endpoints.ai.ai_service.generate_review_material", new_callable=AsyncMock) as mock_rm:
        mock_rm.return_value = {
            "type": "agenda",
            "content": "## 评审议程\n\n1. 开场"
        }

        response = await async_client.post("/api/v1/ai/review-materials", json={
            "project_id": sample_project.id,
            "material_type": "agenda",
        })
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["data"]["material_type"] == "agenda"
        assert "content" in data["data"]


@pytest.mark.integration
async def test_review_materials_invalid_type(async_client: AsyncClient, sample_project: Project):
    """POST /api/v1/ai/review-materials with invalid material_type should return 422."""
    response = await async_client.post("/api/v1/ai/review-materials", json={
        "project_id": sample_project.id,
        "material_type": "invalid_type",
    })
    assert response.status_code == 422


@pytest.mark.integration
async def test_review_materials_all_types(async_client: AsyncClient, sample_project: Project):
    """All valid material types should be accepted."""
    valid_types = ["agenda", "qa", "risks", "decisions", "standup"]

    with patch("app.api.v1.endpoints.ai.ai_service.generate_review_material", new_callable=AsyncMock) as mock_rm:
        mock_rm.return_value = {"type": "mock", "content": "mock content"}

        for mt in valid_types:
            response = await async_client.post("/api/v1/ai/review-materials", json={
                "project_id": sample_project.id,
                "material_type": mt,
            })
            assert response.status_code == 200, f"material_type={mt} should be valid"


# ============== /chat/stream ==============

@pytest.mark.integration
async def test_chat_stream_sse(async_client: AsyncClient):
    """POST /api/v1/ai/chat/stream should return SSE chunks with done event."""
    with patch("app.api.v1.endpoints.ai.create_default_client") as mock_create_client, \
         patch("app.api.v1.endpoints.ai.retrieval_engine.search") as mock_search:
        mock_search.return_value = []

        mock_llm = MagicMock()

        async def fake_llm_stream(*args, **kwargs):
            yield "Hello"
            yield " "
            yield "World"

        mock_llm.chat_stream = fake_llm_stream
        mock_create_client.return_value = mock_llm

        response = await async_client.post("/api/v1/ai/chat/stream", params={
            "conversation_id": "test-conv",
            "content": "Hello",
        })
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")

        events = _sse_lines(response.text)
        # Should contain content chunks and a done chunk
        assert len(events) >= 1
        # Last event should be done=True
        assert events[-1].get("done") is True
        assert events[-1].get("full_content") == "Hello World"


@pytest.mark.integration
async def test_chat_stream_error_handling(async_client: AsyncClient):
    """chat/stream should yield error message when LLM fails."""
    with patch("app.api.v1.endpoints.ai.create_default_client") as mock_create_client, \
         patch("app.api.v1.endpoints.ai.retrieval_engine.search") as mock_search:
        mock_search.return_value = []

        mock_llm = MagicMock()
        # Make chat_stream raise immediately when called
        mock_llm.chat_stream = MagicMock(side_effect=RuntimeError("LLM service unavailable"))
        mock_create_client.return_value = mock_llm

        response = await async_client.post("/api/v1/ai/chat/stream", params={
            "conversation_id": "test-conv-error",
            "content": "Hello",
        })
        assert response.status_code == 200
        # Should still return SSE even on error
        assert "text/event-stream" in response.headers.get("content-type", "")

        events = _sse_lines(response.text)
        # Error should be surfaced in the stream
        assert len(events) >= 1
        assert any("Error" in e.get("content", "") for e in events)
