"""Application configuration"""

from pathlib import Path
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings
from typing import List

# Compute default DB path relative to this config file (apps/api/jarvis_pm.db)
_DB_DIR = Path(__file__).resolve().parent.parent.parent
_DEFAULT_SQLITE_PATH = str(_DB_DIR / "jarvis_pm.db")


class Settings(BaseSettings):
    """Application settings"""

    # App
    APP_NAME: str = "Jarvis PM API"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    ]

    # Database (SQLite for local development, PostgreSQL for production)
    DATABASE_URL: str = f"sqlite+aiosqlite:///{_DEFAULT_SQLITE_PATH}"
    DATABASE_URL_SYNC: str = f"sqlite:///{_DEFAULT_SQLITE_PATH}"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    SECRET_KEY: str = Field(default="", repr=False)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Security
    SINGLE_USER_MODE: bool = False

    # AI/LLM - Kimi (Moonshot AI)
    # Available models: k2.6-code-preview / moonshot-v1-32k / moonshot-v1-128k
    KIMI_API_KEY: str = Field(default="", repr=False)
    KIMI_BASE_URL: str = "https://api.kimi.com/coding/"
    KIMI_MODEL: str = "k2.6-code-preview"

    # AI/LLM - Alternative providers
    ANTHROPIC_API_KEY: str = Field(default="", repr=False)
    ANTHROPIC_BASE_URL: str = "https://api.anthropic.com"
    ANTHROPIC_MODEL: str = "claude-3-5-sonnet-20241022"
    OPENAI_API_KEY: str = Field(default="", repr=False)
    OPENAI_MODEL: str = "gpt-4"

    # AI/LLM - DeepSeek (OpenAI-compatible, fast for PRD generation)
    DEEPSEEK_API_KEY: str = Field(default="", repr=False)
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com/v1"
    DEEPSEEK_MODEL: str = "deepseek-v4-flash"

    # Default AI provider (kimi/anthropic/openai/deepseek)
    # IMPORTANT: "mock" is removed from defaults. Set a real provider to get actual AI responses.
    DEFAULT_AI_PROVIDER: str = "deepseek"
    DEFAULT_AI_MODEL: str = "deepseek-v4-flash"
    DEFAULT_LLM_PROVIDER: str = "deepseek"  # kimi/openai/anthropic/deepseek — NEVER mock for real usage

    # Cache configuration
    CACHE_TTL: int = 3600  # 1 hour
    ENABLE_LLM_CACHE: bool = True

    # Feature flags
    ENABLE_OUTPUT_VALIDATION: bool = True
    ENABLE_WORKFLOW_ENGINE: bool = True

    # File storage
    UPLOAD_DIR: str = str(_DB_DIR / "uploads")
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
        if self.DEEPSEEK_API_KEY.strip():
            providers.append("deepseek")
        return providers

    @model_validator(mode="after")
    def check_secret_key(self):
        if not self.SECRET_KEY or not self.SECRET_KEY.strip():
            if self.DEBUG:
                import secrets
                self.SECRET_KEY = secrets.token_urlsafe(32)
                import logging
                logging.getLogger(__name__).warning(
                    "SECRET_KEY was auto-generated for DEBUG mode. "
                    "Sessions will be invalidated on restart. "
                    "Set SECRET_KEY in .env for persistent sessions."
                )
            else:
                raise ValueError(
                    "SECRET_KEY must be set in production. "
                    "Please configure it in your .env file or environment variables."
                )
        return self

    class Config:
        env_file = str(Path(__file__).parent.parent.parent / ".env")
        env_file_encoding = "utf-8"


settings = Settings()
