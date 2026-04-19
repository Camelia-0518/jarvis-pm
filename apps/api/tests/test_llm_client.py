"""Tests for app.agents.llm_client fallback behavior."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.agents.llm_client import (
    LLMClient,
    LLMClientFactory,
    FallbackLLMClient,
    KimiHTTPClient,
    OpenAIHTTPClient,
    AnthropicHTTPClient,
    MockLLMClient,
    create_default_client,
)


class TestKimiHTTPClient:
    @pytest.mark.asyncio
    async def test_chat_success(self):
        client = KimiHTTPClient(api_key="test-key")
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Hello from Kimi"))]
        with patch.object(client, "_get_client") as mock_get_client:
            mock_openai = AsyncMock()
            mock_openai.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_openai
            result = await client.chat([{"role": "user", "content": "Hi"}])
            assert result == "Hello from Kimi"

    @pytest.mark.asyncio
    async def test_missing_api_key_raises(self):
        client = KimiHTTPClient(api_key="")
        with pytest.raises(Exception):
            await client.chat([{"role": "user", "content": "Hi"}])


class TestOpenAIHTTPClient:
    @pytest.mark.asyncio
    async def test_chat_success(self):
        client = OpenAIHTTPClient(api_key="test-key")
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Hello from OpenAI"))]
        with patch.object(client, "_get_client") as mock_get_client:
            mock_openai = AsyncMock()
            mock_openai.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_openai
            result = await client.chat([{"role": "user", "content": "Hi"}])
            assert result == "Hello from OpenAI"


class TestAnthropicHTTPClient:
    @pytest.mark.asyncio
    async def test_chat_success(self):
        client = AnthropicHTTPClient(api_key="test-key")
        mock_response = MagicMock()
        content_block = MagicMock()
        content_block.text = "Hello from Claude"
        mock_response.content = [content_block]
        with patch.object(client, "_get_client") as mock_get_client:
            mock_anthropic = AsyncMock()
            mock_anthropic.messages.create = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_anthropic
            result = await client.chat([{"role": "user", "content": "Hi"}])
            assert result == "Hello from Claude"

    def test_convert_messages(self):
        client = AnthropicHTTPClient(api_key="test-key")
        system, msgs = client._convert_messages([
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "Hi"},
        ])
        assert system == "You are helpful"
        assert msgs == [{"role": "user", "content": "Hi"}]


class TestMockLLMClient:
    @pytest.mark.asyncio
    async def test_chat(self):
        client = MockLLMClient("mocked")
        result = await client.chat([{"role": "user", "content": "Hi"}])
        assert result == "mocked"

    @pytest.mark.asyncio
    async def test_stream(self):
        client = MockLLMClient("mocked")
        chunks = [c async for c in client.chat_stream([{"role": "user", "content": "Hi"}])]
        assert chunks == ["mocked"]


class FailingClient(LLMClient):
    async def chat(self, messages, **kwargs):
        raise RuntimeError("fail")
    async def chat_stream(self, messages, **kwargs):
        raise RuntimeError("fail")


class TestFallbackLLMClient:
    @pytest.mark.asyncio
    async def test_fallback_to_mock_when_all_fail(self):
        bad_client = FailingClient()
        mock_client = MockLLMClient("fallback-ok")
        fallback = FallbackLLMClient(clients=[bad_client, bad_client, bad_client, mock_client])
        result = await fallback.chat([{"role": "user", "content": "Hi"}])
        assert result == "fallback-ok"

    @pytest.mark.asyncio
    async def test_uses_first_successful(self):
        bad_kimi = KimiHTTPClient(api_key="")
        good_openai = OpenAIHTTPClient(api_key="test-key")
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="openai-wins"))]
        with patch.object(good_openai, "_get_client") as mock_get_client:
            mock_o = AsyncMock()
            mock_o.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_o
            fallback = FallbackLLMClient(clients=[bad_kimi, good_openai])
            result = await fallback.chat([{"role": "user", "content": "Hi"}])
            assert result == "openai-wins"

    @pytest.mark.asyncio
    async def test_stream_fallback(self):
        bad_kimi = KimiHTTPClient(api_key="")
        mock_client = MockLLMClient("stream-fallback")
        fallback = FallbackLLMClient(clients=[bad_kimi, mock_client])
        chunks = [c async for c in fallback.chat_stream([{"role": "user", "content": "Hi"}])]
        assert chunks == ["stream-fallback"]

    def test_fallback_includes_only_configured_clients(self):
        from app.core.config import Settings
        settings = Settings(
            KIMI_API_KEY="sk-kimi",
            OPENAI_API_KEY="",
            ANTHROPIC_API_KEY="",
        )
        # FallbackLLMClient reads global settings when clients=None
        # So we patch settings directly on the module
        from app.agents import llm_client as llm_client_module
        original_settings = getattr(llm_client_module, "settings", None)
        try:
            llm_client_module.settings = settings
            client = FallbackLLMClient()
            names = [c.__class__.__name__ for c in client.clients]
            assert names == ["KimiHTTPClient", "MockLLMClient"]
        finally:
            llm_client_module.settings = original_settings

    def test_fallback_no_keys_uses_mock_only(self):
        from app.core.config import Settings
        settings = Settings(
            KIMI_API_KEY="",
            OPENAI_API_KEY="",
            ANTHROPIC_API_KEY="",
        )
        from app.agents import llm_client as llm_client_module
        original_settings = getattr(llm_client_module, "settings", None)
        try:
            llm_client_module.settings = settings
            client = FallbackLLMClient()
            names = [c.__class__.__name__ for c in client.clients]
            assert names == ["MockLLMClient"]
        finally:
            llm_client_module.settings = original_settings


class TestLLMClientFactory:
    def test_create_fallback(self):
        client = LLMClientFactory.create("fallback")
        assert isinstance(client, FallbackLLMClient)

    def test_create_kimi(self):
        client = LLMClientFactory.create("kimi")
        assert isinstance(client, KimiHTTPClient)

    def test_create_openai(self):
        client = LLMClientFactory.create("openai")
        assert isinstance(client, OpenAIHTTPClient)

    def test_create_anthropic(self):
        client = LLMClientFactory.create("anthropic")
        assert isinstance(client, AnthropicHTTPClient)

    def test_create_mock(self):
        client = LLMClientFactory.create("mock")
        assert isinstance(client, MockLLMClient)

    def test_create_unknown(self):
        with pytest.raises(ValueError):
            LLMClientFactory.create("unknown")


class TestCreateDefaultClient:
    def test_returns_fallback(self):
        client = create_default_client()
        assert isinstance(client, FallbackLLMClient)
