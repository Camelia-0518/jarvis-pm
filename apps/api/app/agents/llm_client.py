"""
LLM 客户端实现
支持多提供商 HTTP API 调用，带自动降级 fallback + 智能缓存 + 小模型路由
"""

import asyncio
import hashlib
import json
import os
import time
from typing import List, Dict, Any, Optional, AsyncIterator
from abc import ABC, abstractmethod
import logging

import httpx
from openai import AsyncOpenAI, APIError, APITimeoutError, AuthenticationError
from anthropic import AsyncAnthropic, AuthenticationError as AnthropicAuthError

from app.core.config import settings

logger = logging.getLogger(__name__)

os.environ.setdefault("PYTHONIOENCODING", "utf-8")


# ============== Cost Optimization: Response Cache ==============

class LLMCacheEntry:
    """缓存条目"""
    def __init__(self, content: str, timestamp: float, model_key: str):
        self.content = content
        self.timestamp = timestamp
        self.model_key = model_key


class LLMResponseCache:
    """
    LLM 响应缓存，降低重复调用成本
    - 基于 prompt hash 做 key
    - TTL 过期自动清理
    - 仅缓存非流式请求
    """

    def __init__(self, default_ttl: int = 300):
        self._cache: Dict[str, LLMCacheEntry] = {}
        self.default_ttl = default_ttl  # 默认 5 分钟

    def _make_key(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """生成缓存 key"""
        key_data = json.dumps({"messages": messages, "params": kwargs}, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(key_data.encode("utf-8")).hexdigest()

    def get(self, messages: List[Dict[str, str]], **kwargs) -> Optional[str]:
        key = self._make_key(messages, **kwargs)
        entry = self._cache.get(key)
        if entry is None:
            return None
        if time.time() - entry.timestamp > self.default_ttl:
            del self._cache[key]
            return None
        logger.debug("Cache hit for key %s...", key[:8])
        return entry.content

    def set(self, messages: List[Dict[str, str]], content: str, model_key: str, **kwargs) -> None:
        key = self._make_key(messages, **kwargs)
        self._cache[key] = LLMCacheEntry(content, time.time(), model_key)
        # 简单清理：超过 500 条时清除一半最旧的
        if len(self._cache) > 500:
            sorted_items = sorted(self._cache.items(), key=lambda x: x[1].timestamp)
            for old_key, _ in sorted_items[:250]:
                del self._cache[old_key]

    def clear(self) -> None:
        self._cache.clear()


# 全局缓存实例（可在 settings 中开关）
_global_llm_cache = LLMResponseCache()


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
    """Kimi (Moonshot AI) HTTP 客户端

    使用 httpx 直接调用（非 OpenAI SDK），因为 Kimi For Coding API
    需要特殊 User-Agent 头才能访问 k2.6-code-preview 模型。
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.kimi.com/coding/",
        model: str = "k2.6-code-preview",
        timeout: float = 180.0,
    ):
        self.api_key = api_key or settings.KIMI_API_KEY
        self.model = model or settings.KIMI_MODEL
        self.timeout = timeout
        # 与 ai_service.py 保持一致：base_url 保留原样，请求时追加 /v1/chat/completions
        self.base_url = (base_url or settings.KIMI_BASE_URL).rstrip('/')

    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 4000,
        **kwargs,
    ) -> str:
        if not self.api_key:
            raise AuthenticationError("Missing KIMI_API_KEY", request=None, body=None)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "KimiCLI/1.30.0",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
            **kwargs,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/v1/chat/completions",
                headers=headers,
                json=payload,
            )
            if response.status_code != 200:
                raise APIError(
                    f"Kimi API error: {response.status_code} - {response.text}",
                    request=response.request,
                    body=response.text,
                )
            data = response.json()
            msg = data["choices"][0]["message"]
            content = msg.get("content") or ""
            # Kimi K2.6 reasoning model puts thinking in reasoning_content
            reasoning = msg.get("reasoning_content") or ""
            if not content.strip() and reasoning.strip():
                lines = reasoning.strip().split("\n")
                # Expanded filter: common thinking prefixes in Chinese & English
                THINKING_PREFIXES = (
                    "用户", "我需", "让我", "首先", "接下来", "我需要", "我应该",
                    "考虑到", "基于", "分析", "思考", "嗯", "好的", "那么",
                    "现在", "接下来", "最后", "总结", "因此", "所以",
                    "I need", "Let me", "First", "Next", "Then", "So",
                    "Based on", "Considering", "Analyzing", "Thinking",
                    "Okay", "Alright", "Now", "Finally", "Therefore",
                )
                for line in reversed(lines):
                    stripped = line.strip()
                    if stripped and len(stripped) > 5 and not any(stripped.startswith(p) for p in THINKING_PREFIXES):
                        content = stripped
                        break
                if not content:
                    # Fallback: if all lines filtered, try to find a code block or list
                    for line in reversed(lines):
                        stripped = line.strip()
                        if stripped and (stripped.startswith("#") or stripped.startswith("-") or stripped.startswith("|") or stripped.startswith("`")):
                            content = stripped
                            break
                if not content:
                    content = reasoning.strip()
            if not content.strip():
                raise APIError("Kimi API returned empty content and reasoning_content", request=None, body=None)
            return content

    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4000,
        **kwargs,
    ) -> AsyncIterator[str]:
        if not self.api_key:
            raise AuthenticationError("Missing KIMI_API_KEY", request=None, body=None)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "KimiCLI/1.30.0",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
            **kwargs,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/v1/chat/completions",
                headers=headers,
                json=payload,
            ) as response:
                if response.status_code != 200:
                    body = await response.aread()
                    raise APIError(
                        f"Kimi API error: {response.status_code} - {body.decode()}",
                        request=response.request,
                        body=body.decode(),
                    )
                async for line in response.aiter_lines():
                    if line.startswith("data:"):
                        data = line[5:].strip()
                        if data == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                            choices = chunk.get("choices")
                            if not choices:
                                continue
                            delta = choices[0].get("delta", {})
                            content = delta.get("content") or ""
                            # Never yield reasoning_content in streaming mode
                            # to prevent thinking content from leaking to users
                            if content:
                                yield content
                        except Exception:
                            logger.debug("Kimi SSE parse error, skipping line")


class DeepSeekHTTPClient(LLMClient):
    """DeepSeek HTTP 客户端 (OpenAI-compatible API)"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.deepseek.com/v1",
        model: str = "deepseek-v4-flash",
        timeout: float = 180.0,
    ):
        self.api_key = api_key or settings.DEEPSEEK_API_KEY
        self.model = model or settings.DEEPSEEK_MODEL
        self.timeout = timeout
        self.base_url = (base_url or settings.DEEPSEEK_BASE_URL).rstrip('/')

    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 4000,
        **kwargs,
    ) -> str:
        if not self.api_key:
            raise AuthenticationError("Missing DEEPSEEK_API_KEY", request=None, body=None)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
            **kwargs,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            if response.status_code != 200:
                raise APIError(
                    f"DeepSeek API error: {response.status_code} - {response.text}",
                    request=response.request,
                    body=response.text,
                )
            data = response.json()
            content = data["choices"][0]["message"].get("content") or ""
            if not content.strip():
                raise APIError("DeepSeek API returned empty content", request=None, body=None)
            return content

    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4000,
        **kwargs,
    ) -> AsyncIterator[str]:
        if not self.api_key:
            raise AuthenticationError("Missing DEEPSEEK_API_KEY", request=None, body=None)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
            **kwargs,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
            ) as response:
                if response.status_code != 200:
                    body = await response.aread()
                    raise APIError(
                        f"DeepSeek API error: {response.status_code} - {body.decode()}",
                        request=response.request,
                        body=body.decode(),
                    )
                async for line in response.aiter_lines():
                    if line.startswith("data:"):
                        data = line[5:].strip()
                        if data == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                            choices = chunk.get("choices")
                            if not choices:
                                continue
                            delta = choices[0].get("delta", {})
                            content = delta.get("content") or ""
                            if content:
                                yield content
                        except Exception:
                            logger.debug("DeepSeek SSE parse error, skipping line")


class OpenAIHTTPClient(LLMClient):
    """OpenAI HTTP 客户端"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4",
        timeout: float = 180.0,
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
        temperature: float = 0.3,
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
        timeout: float = 180.0,
    ):
        self.api_key = api_key or settings.ANTHROPIC_API_KEY
        self.model = model or settings.ANTHROPIC_MODEL
        self.timeout = timeout
        self.base_url = getattr(settings, 'ANTHROPIC_BASE_URL', 'https://api.anthropic.com').rstrip('/')
        self._client: Optional[AsyncAnthropic] = None

    def _get_client(self) -> AsyncAnthropic:
        if self._client is None:
            if not self.api_key:
                from anthropic import AuthenticationError as AnthropicAuthError
                raise AnthropicAuthError("Missing ANTHROPIC_API_KEY")
            self._client = AsyncAnthropic(
                api_key=self.api_key,
                base_url=self.base_url,
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
        temperature: float = 0.3,
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


class FallbackLLMClient(LLMClient):
    """
    带自动降级的 LLM 客户端
    尝试顺序: DeepSeek -> Kimi -> OpenAI -> Anthropic

    重要：如果没有配置任何真实 AI 提供商的 API key，将直接抛出错误，
    绝不静默降级到 Mock（避免用户误以为获得了真实 AI 响应）。
    """

    def __init__(
        self,
        clients: Optional[List[LLMClient]] = None,
    ):
        if clients is not None:
            self.clients = clients
        else:
            self.clients = []
            if settings.DEEPSEEK_API_KEY and settings.DEEPSEEK_API_KEY.strip():
                self.clients.append(DeepSeekHTTPClient())
            if settings.KIMI_API_KEY and settings.KIMI_API_KEY.strip():
                self.clients.append(KimiHTTPClient())
            if settings.OPENAI_API_KEY and settings.OPENAI_API_KEY.strip():
                self.clients.append(OpenAIHTTPClient())
            if settings.ANTHROPIC_API_KEY and settings.ANTHROPIC_API_KEY.strip():
                self.clients.append(AnthropicHTTPClient())

            # 如果没有任何真实 provider 被配置，立即报错
            if not self.clients:
                raise ValueError(
                    "[AI Setup Error] 未配置任何真实 LLM 提供商的 API key。\n"
                    "请在 .env 文件中至少设置以下之一：\n"
                    "  KIMI_API_KEY=your_kimi_key\n"
                    "  OPENAI_API_KEY=your_openai_key\n"
                    "  ANTHROPIC_API_KEY=your_anthropic_key\n"
                    "Jarvis PM 需要真实 AI 才能生成有意义的结果，不支持无 key 运行。"
                )

    RETRYABLE_ERRORS = (
        APIError, APITimeoutError, AuthenticationError,
        AnthropicAuthError, httpx.HTTPError,
    )

    async def _call_with_retry(self, client, operation, *args, **kwargs):
        """带指数退避重试的客户端调用"""
        provider_name = client.__class__.__name__
        last_error: Optional[Exception] = None
        for attempt in range(3):
            try:
                return await operation(*args, **kwargs)
            except self.RETRYABLE_ERRORS as e:
                last_error = e
                if attempt < 2:
                    wait = 2 ** attempt  # 1s, 2s
                    logger.warning(
                        "Provider %s %s attempt %d failed, retrying in %ds: %s",
                        provider_name, operation.__name__, attempt + 1, wait, e
                    )
                    await asyncio.sleep(wait)
                else:
                    logger.error("Provider %s %s exhausted all retries: %s", provider_name, operation.__name__, e)
            except Exception as e:
                last_error = e
                logger.warning("Provider %s %s unexpected error: %s", provider_name, operation.__name__, e)
                break  # 非可重试错误，不再重试
        raise last_error or RuntimeError(f"Provider {provider_name} failed after retries")

    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        use_cache = kwargs.pop("use_cache", True)
        cache_instance = kwargs.pop("cache_instance", _global_llm_cache)

        # 1. 检查缓存（仅当启用缓存时）
        if use_cache and cache_instance:
            cached = cache_instance.get(messages, **kwargs)
            if cached is not None:
                return cached

        last_error: Optional[Exception] = None
        result: Optional[str] = None
        used_model_key = "unknown"

        for client in self.clients:
            try:
                result = await self._call_with_retry(client, client.chat, messages, **kwargs)
                used_model_key = getattr(client, "model", client.__class__.__name__)
                break
            except Exception as e:
                last_error = e
                continue

        if result is None:
            raise last_error or RuntimeError(
                "All configured LLM providers failed. "
                "Please check your API keys and network connectivity."
            )

        # 2. 写入缓存
        if use_cache and cache_instance:
            cache_instance.set(messages, result, used_model_key, **kwargs)

        return result

    async def chat_stream(self, messages: List[Dict[str, str]], **kwargs) -> AsyncIterator[str]:
        last_error: Optional[Exception] = None
        for client in self.clients:
            try:
                # 对 streaming 也进行重试：如果连接或首块失败会重试
                for attempt in range(3):
                    try:
                        async for chunk in client.chat_stream(messages, **kwargs):
                            yield chunk
                        return
                    except self.RETRYABLE_ERRORS as e:
                        if attempt < 2:
                            wait = 2 ** attempt
                            logger.warning(
                                "Provider %s chat_stream attempt %d failed, retrying in %ds: %s",
                                client.__class__.__name__, attempt + 1, wait, e
                            )
                            await asyncio.sleep(wait)
                        else:
                            raise
            except Exception as e:
                last_error = e
                continue
        # All configured real providers failed
        raise last_error or RuntimeError(
            "All configured LLM providers failed (streaming). "
            "Please check your API keys and network connectivity."
        )


class LLMClientFactory:
    """LLM 客户端工厂 — 仅创建真实 AI 客户端"""

    @staticmethod
    def create(provider: str = "fallback") -> LLMClient:
        """
        创建 LLM 客户端

        Args:
            provider: 提供商名称
                - "fallback": 自动降级客户端（默认，Kimi -> OpenAI -> Anthropic）
                - "kimi": Kimi HTTP 客户端
                - "openai": OpenAI HTTP 客户端
                - "anthropic": Anthropic HTTP 客户端

        Returns:
            LLMClient 实例

        Raises:
            ValueError: 当未配置任何真实 provider 的 API key 时
        """
        if provider == "fallback":
            return FallbackLLMClient()
        if provider == "kimi":
            return KimiHTTPClient()
        if provider == "openai":
            return OpenAIHTTPClient()
        if provider in ("anthropic", "claude"):
            return AnthropicHTTPClient()
        if provider == "deepseek":
            return DeepSeekHTTPClient()
        raise ValueError(
            f"Unknown provider: {provider}. "
            "Available: fallback, kimi, openai, anthropic, claude, deepseek"
        )


def create_default_client() -> LLMClient:
    """创建默认客户端（FallbackLLMClient）"""
    return LLMClientFactory.create("fallback")
