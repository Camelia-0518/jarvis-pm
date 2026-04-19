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

    def __init__(self, api_key: str = None, model: str = "kimi-k2.5"):
        self.api_key = api_key or os.getenv("KIMI_API_KEY")
        self.model = model
        self.base_url = "https://api.kimi.com/v1"

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
                timeout=120.0
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
                timeout=120.0
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
                timeout=120.0
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
                timeout=120.0
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


class MockProvider(LLMProvider):
    """Mock Provider - 用于测试"""

    async def complete(self, prompt: str, **kwargs) -> str:
        """返回mock结果"""
        return '{"result": "mock response", "timestamp": "' + str(__import__('datetime').datetime.now()) + '"}'

    async def stream(self, prompt: str, **kwargs) -> AsyncGenerator[str, None]:
        """返回mock流"""
        yield '{"result": "mock'
        yield ' response"}'


class LLMProviderFactory:
    """LLM Provider工厂"""

    _providers = {
        "kimi": KimiProvider,
        "openai": OpenAIProvider,
        "mock": MockProvider,
    }

    @classmethod
    def create(cls, provider_name: str = None, **kwargs) -> LLMProvider:
        """创建LLM Provider实例"""
        provider_name = provider_name or os.getenv("DEFAULT_LLM_PROVIDER", "mock")
        provider_class = cls._providers.get(provider_name)
        if not provider_class:
            raise ValueError(f"Unknown provider: {provider_name}")
        return provider_class(**kwargs)

    @classmethod
    def list_providers(cls) -> list:
        """列出所有支持的provider"""
        return list(cls._providers.keys())
