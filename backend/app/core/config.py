from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
_ENV_FILE = _BACKEND_DIR / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(_ENV_FILE), env_file_encoding="utf-8")

    app_name: str = "Momentum"
    debug: bool = True
    database_url: str = "sqlite:///./momentum.db"
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str = "change-me-in-production"
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]
    seed_demo_data: bool = False
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"


settings = Settings()
