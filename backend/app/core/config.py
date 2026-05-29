from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "Momentum"
    debug: bool = True
    database_url: str = "sqlite:///./momentum.db"
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str = "change-me-in-production"
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]
    seed_demo_data: bool = False


settings = Settings()
