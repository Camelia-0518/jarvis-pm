import pytest

from app.core.config import Settings


class TestSettingsLLMValidation:
    def test_available_providers_all_empty(self):
        settings = Settings(
            KIMI_API_KEY="",
            OPENAI_API_KEY="",
            ANTHROPIC_API_KEY="",
        )
        assert settings.available_llm_providers == []

    def test_available_providers_kimi_only(self):
        settings = Settings(
            KIMI_API_KEY="sk-test",
            OPENAI_API_KEY="",
            ANTHROPIC_API_KEY="",
        )
        assert settings.available_llm_providers == ["kimi"]

    def test_available_providers_openai_only(self):
        settings = Settings(
            KIMI_API_KEY="",
            OPENAI_API_KEY="sk-openai",
            ANTHROPIC_API_KEY="",
        )
        assert settings.available_llm_providers == ["openai"]

    def test_available_providers_anthropic_only(self):
        settings = Settings(
            KIMI_API_KEY="",
            OPENAI_API_KEY="",
            ANTHROPIC_API_KEY="sk-anthropic",
        )
        assert settings.available_llm_providers == ["anthropic"]

    def test_available_providers_all_set(self):
        settings = Settings(
            KIMI_API_KEY="sk-kimi",
            OPENAI_API_KEY="sk-openai",
            ANTHROPIC_API_KEY="sk-anthropic",
        )
        assert settings.available_llm_providers == ["kimi", "openai", "anthropic"]

    def test_available_providers_ignores_whitespace(self):
        settings = Settings(
            KIMI_API_KEY="   ",
            OPENAI_API_KEY="sk-openai",
            ANTHROPIC_API_KEY="",
        )
        assert settings.available_llm_providers == ["openai"]
