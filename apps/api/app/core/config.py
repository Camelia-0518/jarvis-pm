"""Application configuration"""

from pathlib import Path
from pydantic import model_validator
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings"""

    # App
    APP_NAME: str = "Jarvis PM API"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:3001"]

    # Database (SQLite for local development, PostgreSQL for production)
    DATABASE_URL: str = "sqlite+aiosqlite:///./jarvis_pm.db"
    DATABASE_URL_SYNC: str = "sqlite:///./jarvis_pm.db"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    SECRET_KEY: str = ""
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Security
    SINGLE_USER_MODE: bool = False

    # AI/LLM - Kimi (Moonshot AI)
    # Available models: k2.6-code-preview / moonshot-v1-32k / moonshot-v1-128k
    KIMI_API_KEY: str = ""
    KIMI_BASE_URL: str = "https://api.kimi.com/coding/"
    KIMI_MODEL: str = "k2.6-code-preview"

    # AI/LLM - Alternative providers
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_BASE_URL: str = "https://api.anthropic.com"
    ANTHROPIC_MODEL: str = "claude-3-5-sonnet-20241022"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4"

    # Default AI provider (kimi/claude/anthropic/openai)
    # IMPORTANT: "mock" is removed from defaults. Set a real provider to get actual AI responses.
    # NOTE: For Kimi For Coding, use "claude" or "anthropic" (OpenAI format is not supported).
    DEFAULT_AI_PROVIDER: str = "claude"
    DEFAULT_AI_MODEL: str = "k2.6-code-preview"
    DEFAULT_LLM_PROVIDER: str = "anthropic"  # kimi/openai/anthropic — NEVER mock for real usage

    # Cache configuration
    CACHE_TTL: int = 3600  # 1 hour
    ENABLE_LLM_CACHE: bool = True

    # Feature flags
    ENABLE_OUTPUT_VALIDATION: bool = True
    ENABLE_WORKFLOW_ENGINE: bool = True

    # File storage
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB

    @property
    def available_llm_providers(self) -> List[str]:
        """Return a list of LLM providers that have a non-empty API key configured."""
        providers = []
        if self.KIMI_API_KEY.strip():
            providers.append("kimi")
        if self.OPENAI_API_KEY.strip():
            providers.append("openai")
        if self.ANTHROPIC_API_KEY.strip():
            providers.append("anthropic")
        return providers

    @model_validator(mode="after")
    def check_secret_key(self):
        if not self.SECRET_KEY or not self.SECRET_KEY.strip():
            raise ValueError("SECRET_KEY must be set. Please configure it in your .env file or environment variables.")
        return self

    class Config:
        env_file = str(Path(__file__).parent.parent.parent / ".env")
        env_file_encoding = "utf-8"


settings = Settings()
