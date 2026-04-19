"""
LLM 客户端实现
支持多提供商 HTTP API 调用，带自动降级 fallback
"""

import os
from typing import List, Dict, Any, Optional, AsyncIterator
from abc import ABC, abstractmethod
import logging

import httpx
from openai import AsyncOpenAI, APIError, APITimeoutError, AuthenticationError
from anthropic import AsyncAnthropic, AuthenticationError as AnthropicAuthError

from app.core.config import settings

logger = logging.getLogger(__name__)

os.environ.setdefault("PYTHONIOENCODING", "utf-8")


class LLMClient(ABC):
    """LLM 客户端抽象基类"""

    @abstractmethod
    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """发送聊天请求"""
        pass

    @abstractmethod
    async def chat_stream(self, messages: List[Dict[str, str]], **kwargs) -> AsyncIterator[str]:
        """流式聊天请求"""
        pass


class KimiHTTPClient(LLMClient):
    """Kimi (Moonshot AI) HTTP 客户端，基于 OpenAI SDK"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.kimi.com/coding/",
        model: str = "k2.6-code-preview",
        timeout: float = 120.0,
    ):
        self.api_key = api_key or settings.KIMI_API_KEY
        self.base_url = base_url or settings.KIMI_BASE_URL
        self.model = model or settings.KIMI_MODEL
        self.timeout = timeout
        self._client: Optional[AsyncOpenAI] = None

    def _get_client(self) -> AsyncOpenAI:
        if self._client is None:
            if not self.api_key:
                raise AuthenticationError("Missing KIMI_API_KEY", request=None, body=None)
            self._client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=self.timeout,
            )
        return self._client

    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4000,
        **kwargs,
    ) -> str:
        client = self._get_client()
        response = await client.chat.completions.create(
            model=self.model,
            messages=messages,  # type: ignore[arg-type]
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )
        content = response.choices[0].message.content
        return content or ""

    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4000,
        **kwargs,
    ) -> AsyncIterator[str]:
        client = self._get_client()
        stream = await client.chat.completions.create(
            model=self.model,
            messages=messages,  # type: ignore[arg-type]
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
            **kwargs,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta


class OpenAIHTTPClient(LLMClient):
    """OpenAI HTTP 客户端"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4",
        timeout: float = 120.0,
    ):
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.model = model or settings.OPENAI_MODEL
        self.timeout = timeout
        self._client: Optional[AsyncOpenAI] = None

    def _get_client(self) -> AsyncOpenAI:
        if self._client is None:
            if not self.api_key:
                raise AuthenticationError("Missing OPENAI_API_KEY", request=None, body=None)
            self._client = AsyncOpenAI(
                api_key=self.api_key,
                timeout=self.timeout,
            )
        return self._client

    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4000,
        **kwargs,
    ) -> str:
        client = self._get_client()
        response = await client.chat.completions.create(
            model=self.model,
            messages=messages,  # type: ignore[arg-type]
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )
        content = response.choices[0].message.content
        return content or ""

    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4000,
        **kwargs,
    ) -> AsyncIterator[str]:
        client = self._get_client()
        stream = await client.chat.completions.create(
            model=self.model,
            messages=messages,  # type: ignore[arg-type]
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
            **kwargs,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta


class AnthropicHTTPClient(LLMClient):
    """Anthropic HTTP 客户端"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-3-5-sonnet-20241022",
        timeout: float = 120.0,
    ):
        self.api_key = api_key or settings.ANTHROPIC_API_KEY
        self.model = model or settings.ANTHROPIC_MODEL
        self.timeout = timeout
        self._client: Optional[AsyncAnthropic] = None

    def _get_client(self) -> AsyncAnthropic:
        if self._client is None:
            if not self.api_key:
                from anthropic import AuthenticationError as AnthropicAuthError
                raise AnthropicAuthError("Missing ANTHROPIC_API_KEY")
            self._client = AsyncAnthropic(
                api_key=self.api_key,
                timeout=self.timeout,
            )
        return self._client

    @staticmethod
    def _convert_messages(messages: List[Dict[str, str]]) -> tuple[Optional[str], List[Dict[str, Any]]]:
        """将 OpenAI 格式消息转换为 Anthropic 格式"""
        system_text: Optional[str] = None
        anthropic_messages: List[Dict[str, Any]] = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                system_text = content
                continue
            anthropic_messages.append({"role": role, "content": content})
        return system_text, anthropic_messages

    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4000,
        **kwargs,
    ) -> str:
        client = self._get_client()
        system_text, anthropic_messages = self._convert_messages(messages)
        response = await client.messages.create(
            model=self.model,
            messages=anthropic_messages,  # type: ignore[arg-type]
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_text,
            **kwargs,
        )
        content_block = response.content[0]
        return getattr(content_block, "text", "")

    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4000,
        **kwargs,
    ) -> AsyncIterator[str]:
        client = self._get_client()
        system_text, anthropic_messages = self._convert_messages(messages)
        async with client.messages.stream(
            model=self.model,
            messages=anthropic_messages,  # type: ignore[arg-type]
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_text,
            **kwargs,
        ) as stream:
            async for text in stream.text_stream:
                if text:
                    yield text


class MockLLMClient(LLMClient):
    """Mock LLM 客户端，用于最终降级"""

    def __init__(self, response_text: Optional[str] = None):
        self.response_text = response_text or "[Mock] 当前无可用 LLM 提供商，请检查 API Key 配置。"

    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        return self.response_text

    async def chat_stream(self, messages: List[Dict[str, str]], **kwargs) -> AsyncIterator[str]:
        yield self.response_text


class FallbackLLMClient(LLMClient):
    """
    带自动降级的 LLM 客户端
    尝试顺序: Kimi -> OpenAI -> Anthropic -> Mock
    """

    def __init__(
        self,
        clients: Optional[List[LLMClient]] = None,
    ):
        if clients is not None:
            self.clients = clients
        else:
            self.clients = []
            if settings.KIMI_API_KEY.strip():
                self.clients.append(KimiHTTPClient())
            if settings.OPENAI_API_KEY.strip():
                self.clients.append(OpenAIHTTPClient())
            if settings.ANTHROPIC_API_KEY.strip():
                self.clients.append(AnthropicHTTPClient())
            self.clients.append(MockLLMClient())

    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        last_error: Optional[Exception] = None
        for client in self.clients:
            provider_name = client.__class__.__name__
            try:
                logger.info("Trying provider %s for chat", provider_name)
                return await client.chat(messages, **kwargs)
            except (APIError, APITimeoutError, AuthenticationError, AnthropicAuthError, httpx.HTTPError) as e:
                logger.warning("Provider %s failed: %s", provider_name, e)
                last_error = e
                continue
            except Exception as e:
                logger.warning("Provider %s unexpected error: %s", provider_name, e)
                last_error = e
                continue
        # Should never reach here because MockLLMClient always succeeds,
        # but keep for type safety.
        raise last_error or RuntimeError("All LLM providers failed and mock was unreachable")

    async def chat_stream(self, messages: List[Dict[str, str]], **kwargs) -> AsyncIterator[str]:
        last_error: Optional[Exception] = None
        for client in self.clients:
            provider_name = client.__class__.__name__
            try:
                logger.info("Trying provider %s for chat_stream", provider_name)
                async for chunk in client.chat_stream(messages, **kwargs):
                    yield chunk
                return
            except (APIError, APITimeoutError, AuthenticationError, AnthropicAuthError, httpx.HTTPError) as e:
                logger.warning("Provider %s failed: %s", provider_name, e)
                last_error = e
                continue
            except Exception as e:
                logger.warning("Provider %s unexpected error: %s", provider_name, e)
                last_error = e
                continue
        # Fallback to mock if somehow reached
        async for chunk in MockLLMClient().chat_stream(messages, **kwargs):
            yield chunk


class LLMClientFactory:
    """LLM 客户端工厂"""

    @staticmethod
    def create(provider: str = "fallback") -> LLMClient:
        """
        创建 LLM 客户端

        Args:
            provider: 提供商名称
                - "fallback": 自动降级客户端（默认）
                - "kimi": Kimi HTTP 客户端
                - "openai": OpenAI HTTP 客户端
                - "anthropic": Anthropic HTTP 客户端
                - "mock": Mock 客户端

        Returns:
            LLMClient 实例
        """
        if provider == "fallback":
            return FallbackLLMClient()
        if provider == "kimi":
            return KimiHTTPClient()
        if provider == "openai":
            return OpenAIHTTPClient()
        if provider == "anthropic":
            return AnthropicHTTPClient()
        if provider == "mock":
            return MockLLMClient()
        raise ValueError(
            f"Unknown provider: {provider}. "
            "Available: fallback, kimi, openai, anthropic, mock"
        )


def create_default_client() -> LLMClient:
    """创建默认客户端（FallbackLLMClient）"""
    return LLMClientFactory.create("fallback")
