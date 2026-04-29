"""LLM Provider抽象层

支持Kimi、OpenAI、Anthropic等多种LLM服务
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, AsyncGenerator, Optional
import os
import httpx


class LLMProvider(ABC):
    """LLM Provider抽象基类"""

    @abstractmethod
    async def complete(self, prompt: str, **kwargs) -> str:
        """同步完成"""
        pass

    @abstractmethod
    async def stream(self, prompt: str, **kwargs) -> AsyncGenerator[str, None]:
        """流式输出"""
        pass


class KimiProvider(LLMProvider):
    """Kimi API Provider"""

    def __init__(self, api_key: str = None, model: str = None):
        from app.core.config import settings
        self.api_key = api_key or settings.KIMI_API_KEY
        self.model = model or settings.KIMI_MODEL
        self.base_url = settings.KIMI_BASE_URL.rstrip('/')

    async def complete(self, prompt: str, temperature: float = 0.7, max_tokens: int = 4000) -> str:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": temperature,
                    "max_tokens": max_tokens
                },
                timeout=180.0
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]

    async def stream(self, prompt: str, **kwargs) -> AsyncGenerator[str, None]:
        """流式输出实现"""
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": True,
                    **kwargs
                },
                timeout=180.0
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        import json
                        try:
                            chunk = json.loads(data)
                            delta = chunk["choices"][0].get("delta", {})
                            if "content" in delta:
                                yield delta["content"]
                        except:
                            pass


class OpenAIProvider(LLMProvider):
    """OpenAI API Provider"""

    def __init__(self, api_key: str = None, model: str = "gpt-4o"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        self.base_url = "https://api.openai.com/v1"

    async def complete(self, prompt: str, **kwargs) -> str:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    **kwargs
                },
                timeout=180.0
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]

    async def stream(self, prompt: str, **kwargs) -> AsyncGenerator[str, None]:
        """流式输出实现"""
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": True,
                    **kwargs
                },
                timeout=180.0
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        import json
                        try:
                            chunk = json.loads(data)
                            delta = chunk["choices"][0].get("delta", {})
                            if "content" in delta:
                                yield delta["content"]
                        except:
                            pass


class AnthropicProvider(LLMProvider):
    """Anthropic API Provider - 用于 Kimi for Coding (Anthropic兼容格式)"""

    def __init__(self, api_key: str = None, model: str = None):
        from app.core.config import settings
        self.api_key = api_key or settings.ANTHROPIC_API_KEY
        self.model = model or settings.ANTHROPIC_MODEL
        self.base_url = getattr(settings, 'ANTHROPIC_BASE_URL', 'https://api.anthropic.com').rstrip('/')

    async def complete(self, prompt: str, temperature: float = 0.7, max_tokens: int = 4000) -> str:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/v1/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=180.0
            )
            response.raise_for_status()
            data = response.json()
            # Anthropic messages API 返回 content[0].text
            return data["content"][0]["text"]

    async def stream(self, prompt: str, **kwargs) -> AsyncGenerator[str, None]:
        """流式输出实现"""
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/v1/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "max_tokens": 4000,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": True,
                    **kwargs
                },
                timeout=180.0
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        import json
                        try:
                            event = json.loads(data)
                            if event.get("type") == "content_block_delta":
                                delta = event.get("delta", {})
                                if "text" in delta:
                                    yield delta["text"]
                        except:
                            pass


class LLMProviderFactory:
    """LLM Provider工厂 — 仅创建真实AI提供商，绝不静默降级到Mock"""

    _providers = {
        "kimi": KimiProvider,
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
        "claude": AnthropicProvider,  # alias for Anthropic-compatible API (e.g., Kimi For Coding)
    }

    @classmethod
    def create(cls, provider_name: str = None, **kwargs) -> LLMProvider:
        """创建LLM Provider实例

        Raises:
            ValueError: 当请求未知的provider，或没有配置任何真实provider的API key时
        """
        from app.core.config import settings

        if not provider_name:
            provider_name = settings.DEFAULT_AI_PROVIDER

        provider_class = cls._providers.get(provider_name)

        # 如果指定了具体provider但找不到，尝试fallback到已配置的provider
        if not provider_class:
            available = settings.available_llm_providers
            if available:
                fallback_name = available[0]
                provider_class = cls._providers.get(fallback_name)
                provider_name = fallback_name
            else:
                raise ValueError(
                    f"Unknown provider '{provider_name}' and no configured providers available. "
                    f"Set KIMI_API_KEY, OPENAI_API_KEY, or ANTHROPIC_API_KEY."
                )

        if not provider_class:
            raise ValueError(f"Provider class not found for: {provider_name}")

        return provider_class(**kwargs)

    @classmethod
    def list_providers(cls) -> list:
        """列出所有支持的真实provider"""
        return list(cls._providers.keys())
