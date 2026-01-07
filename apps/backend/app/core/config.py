"""Application configuration settings."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import EmailStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_name: str = "AI E-Sign"
    debug: bool = False
    secret_key: str = "change-me-in-production-use-a-real-secret-key"

    # API
    api_v1_prefix: str = "/api/v1"

    # Database
    database_url: str = "sqlite+aiosqlite:///./esign.db"

    # Storage
    storage_backend: Literal["local", "s3"] = "local"
    storage_path: Path = Path("./storage")

    # LLM Configuration
    llm_provider: Literal["openai", "anthropic", "none"] = "none"
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    llm_model: str = "gpt-4o"

    # Email (for magic links)
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    email_from: EmailStr | None = None

    # Signing links
    signing_link_base_url: str = "http://localhost:3000"
    signing_link_expiry_hours: int = 72

    # Security
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days

    # Field Detection Thresholds
    detection_confidence_threshold: float = 0.5
    classification_confidence_threshold: float = 0.6
    owner_confidence_threshold: float = 0.5


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
