"""Tests for LLM Provider module.

This module tests the LLM provider implementations including:
- KimiProvider
- OpenAIProvider
- MockProvider
- LLMProviderFactory
"""

import pytest
import pytest_asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch, Mock
import httpx
import json

from app.services.llm_provider import (
    LLMProvider,
    KimiProvider,
    OpenAIProvider,
    MockProvider,
    LLMProviderFactory,
)


# ==================== KimiProvider Tests ====================

class TestKimiProvider:
    """Test suite for KimiProvider."""

    def test_kimi_provider_creation_with_api_key(self):
        """Test KimiProvider creation with explicit API key."""
        provider = KimiProvider(api_key="test-key", model="kimi-k2.5")
        assert provider.api_key == "test-key"
        assert provider.model == "kimi-k2.5"
        assert provider.base_url == "https://api.kimi.com/v1"

    def test_kimi_provider_creation_from_env(self, monkeypatch):
        """Test KimiProvider creation from environment variable."""
        monkeypatch.setenv("KIMI_API_KEY", "env-api-key")
        provider = KimiProvider()
        assert provider.api_key == "env-api-key"

    @pytest.mark.asyncio
    async def test_kimi_provider_complete_success(self, mock_kimi_api_key):
        """Test KimiProvider complete method with successful response."""
        provider = KimiProvider(api_key=mock_kimi_api_key)

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Test response"}}]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient.post", return_value=mock_response) as mock_post:
            mock_post.return_value = mock_response

            with patch.object(httpx.AsyncClient, "post", return_value=mock_response):
                async with httpx.AsyncClient() as client:
                    client.post = AsyncMock(return_value=mock_response)
                    result = await provider.complete("Test prompt")
                    assert result == "Test response"

    @pytest.mark.asyncio
    async def test_kimi_provider_complete_with_params(self, mock_kimi_api_key):
        """Test KimiProvider complete with custom parameters."""
        provider = KimiProvider(api_key=mock_kimi_api_key)

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Custom response"}}]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = await provider.complete(
                "Test prompt",
                temperature=0.5,
                max_tokens=2000
            )
            assert result == "Custom response"

    @pytest.mark.asyncio
    async def test_kimi_provider_stream(self, mock_kimi_api_key):
        """Test KimiProvider stream method."""
        provider = KimiProvider(api_key=mock_kimi_api_key)

        # Mock the streaming response
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        async def mock_aiter_lines():
            lines = [
                'data: {"choices": [{"delta": {"content": "Hello"}}]}',
                'data: {"choices": [{"delta": {"content": " World"}}]}',
                'data: [DONE]'
            ]
            for line in lines:
                yield line

        mock_response.aiter_lines = mock_aiter_lines

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.stream = MagicMock()
            mock_stream_context = AsyncMock()
            mock_stream_context.__aenter__ = AsyncMock(return_value=mock_response)
            mock_stream_context.__aexit__ = AsyncMock(return_value=False)
            mock_client.stream.return_value = mock_stream_context
            mock_client_class.return_value = mock_client

            chunks = []
            async for chunk in provider.stream("Test prompt"):
                chunks.append(chunk)

            assert len(chunks) == 2
            assert chunks[0] == "Hello"
            assert chunks[1] == " World"


# ==================== OpenAIProvider Tests ====================

class TestOpenAIProvider:
    """Test suite for OpenAIProvider."""

    def test_openai_provider_creation_with_api_key(self):
        """Test OpenAIProvider creation with explicit API key."""
        provider = OpenAIProvider(api_key="test-openai-key", model="gpt-4o")
        assert provider.api_key == "test-openai-key"
        assert provider.model == "gpt-4o"
        assert provider.base_url == "https://api.openai.com/v1"

    def test_openai_provider_creation_from_env(self, monkeypatch):
        """Test OpenAIProvider creation from environment variable."""
        monkeypatch.setenv("OPENAI_API_KEY", "env-openai-key")
        provider = OpenAIProvider()
        assert provider.api_key == "env-openai-key"

    @pytest.mark.asyncio
    async def test_openai_provider_complete(self, mock_openai_api_key):
        """Test OpenAIProvider complete method."""
        provider = OpenAIProvider(api_key=mock_openai_api_key)

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "OpenAI response"}}]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = await provider.complete("Test prompt")
            assert result == "OpenAI response"

    @pytest.mark.asyncio
    async def test_openai_provider_stream(self, mock_openai_api_key):
        """Test OpenAIProvider stream method."""
        provider = OpenAIProvider(api_key=mock_openai_api_key)

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        async def mock_aiter_lines():
            lines = [
                'data: {"choices": [{"delta": {"content": "Stream"}}]}',
                'data: {"choices": [{"delta": {"content": "ing"}}]}',
                'data: [DONE]'
            ]
            for line in lines:
                yield line

        mock_response.aiter_lines = mock_aiter_lines

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.stream = MagicMock()
            mock_stream_context = AsyncMock()
            mock_stream_context.__aenter__ = AsyncMock(return_value=mock_response)
            mock_stream_context.__aexit__ = AsyncMock(return_value=False)
            mock_client.stream.return_value = mock_stream_context
            mock_client_class.return_value = mock_client

            chunks = []
            async for chunk in provider.stream("Test prompt"):
                chunks.append(chunk)

            assert len(chunks) == 2
            assert "".join(chunks) == "Streaming"


# ==================== MockProvider Tests ====================

class TestMockProvider:
    """Test suite for MockProvider."""

    @pytest.mark.asyncio
    async def test_mock_provider_complete(self):
        """Test MockProvider complete method returns valid JSON."""
        provider = MockProvider()
        result = await provider.complete("Test prompt")

        # Should return a JSON string with mock response
        assert "mock response" in result
        assert "timestamp" in result

        # Verify it's valid JSON
        data = json.loads(result)
        assert data["result"] == "mock response"
        assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_mock_provider_complete_with_kwargs(self):
        """Test MockProvider complete method ignores extra kwargs."""
        provider = MockProvider()
        result = await provider.complete(
            "Test prompt",
            temperature=0.5,
            max_tokens=100,
            custom_param="value"
        )

        data = json.loads(result)
        assert data["result"] == "mock response"

    @pytest.mark.asyncio
    async def test_mock_provider_stream(self):
        """Test MockProvider stream method."""
        provider = MockProvider()

        chunks = []
        async for chunk in provider.stream("Test prompt"):
            chunks.append(chunk)

        assert len(chunks) == 2
        assert chunks[0] == '{"result": "mock'
        assert chunks[1] == ' response"}'

        # Combined should be valid JSON
        combined = "".join(chunks)
        data = json.loads(combined)
        assert data["result"] == "mock response"

    @pytest.mark.asyncio
    async def test_mock_provider_stream_with_kwargs(self):
        """Test MockProvider stream method ignores extra kwargs."""
        provider = MockProvider()

        chunks = []
        async for chunk in provider.stream("Test prompt", temperature=0.7):
            chunks.append(chunk)

        assert len(chunks) == 2


# ==================== LLMProviderFactory Tests ====================

class TestLLMProviderFactory:
    """Test suite for LLMProviderFactory."""

    def test_factory_create_kimi(self):
        """Test factory creates KimiProvider."""
        with patch.dict(os.environ, {"KIMI_API_KEY": "test-key"}):
            provider = LLMProviderFactory.create("kimi")
            assert isinstance(provider, KimiProvider)

    def test_factory_create_openai(self):
        """Test factory creates OpenAIProvider."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            provider = LLMProviderFactory.create("openai")
            assert isinstance(provider, OpenAIProvider)

    def test_factory_create_mock(self):
        """Test factory creates MockProvider."""
        provider = LLMProviderFactory.create("mock")
        assert isinstance(provider, MockProvider)

    def test_factory_create_default_from_env(self, monkeypatch):
        """Test factory creates provider from DEFAULT_LLM_PROVIDER env."""
        monkeypatch.setenv("DEFAULT_LLM_PROVIDER", "mock")
        provider = LLMProviderFactory.create()
        assert isinstance(provider, MockProvider)

    def test_factory_create_default_fallback(self, monkeypatch):
        """Test factory falls back to mock when no env is set."""
        monkeypatch.delenv("DEFAULT_LLM_PROVIDER", raising=False)
        provider = LLMProviderFactory.create()
        assert isinstance(provider, MockProvider)

    def test_factory_create_unknown_provider(self):
        """Test factory raises error for unknown provider."""
        with pytest.raises(ValueError, match="Unknown provider: unknown"):
            LLMProviderFactory.create("unknown")

    def test_factory_create_with_kwargs(self):
        """Test factory passes kwargs to provider."""
        # MockProvider doesn't accept kwargs, so test with a provider that does
        with patch.dict(os.environ, {"KIMI_API_KEY": "test-key"}):
            provider = LLMProviderFactory.create("kimi", model="kimi-k2.5")
            assert isinstance(provider, KimiProvider)
            assert provider.model == "kimi-k2.5"

    def test_factory_list_providers(self):
        """Test factory lists all supported providers."""
        providers = LLMProviderFactory.list_providers()
        assert "kimi" in providers
        assert "openai" in providers
        assert "mock" in providers
        assert len(providers) == 3


# ==================== Integration Tests ====================

class TestLLMProviderIntegration:
    """Integration tests for LLM providers."""

    @pytest.mark.asyncio
    async def test_mock_provider_end_to_end(self):
        """Test complete flow with MockProvider."""
        provider = MockProvider()

        # Test complete
        result = await provider.complete("Analyze requirements")
        assert isinstance(result, str)
        assert len(result) > 0

        # Test stream
        chunks = []
        async for chunk in provider.stream("Analyze requirements"):
            chunks.append(chunk)
        assert len(chunks) > 0

    @pytest.mark.asyncio
    async def test_all_providers_have_required_methods(self):
        """Test that all providers implement required abstract methods."""
        providers = [
            MockProvider(),
        ]

        for provider in providers:
            assert hasattr(provider, "complete")
            assert hasattr(provider, "stream")
            assert callable(provider.complete)
            assert callable(provider.stream)

    def test_provider_inheritance(self):
        """Test that providers inherit from LLMProvider."""
        assert issubclass(KimiProvider, LLMProvider)
        assert issubclass(OpenAIProvider, LLMProvider)
        assert issubclass(MockProvider, LLMProvider)
