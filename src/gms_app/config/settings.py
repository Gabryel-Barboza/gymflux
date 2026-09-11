from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Config central — env prefix GMS_ + .env opcional."""

    model_config = SettingsConfigDict(
        env_prefix="GMS_", env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    henry_mock: bool = Field(default=True, description="Força MockHenry7x mesmo em Windows")
    henry_dll_path: str = Field(default="vendor/kernel7x.dll")
    henry_porta: str = Field(default="1", description="COM1, 192.168.0.100:3000 ou MOCK:1")
    henry_timeout_ms: int = Field(default=7000, ge=1000, le=30000)

    db_url: str = Field(default="sqlite:///data/gms.db")
    log_level: str = Field(default="INFO")

    app_name: str = Field(default="GMS")
    app_version: str = Field(default="0.1.0")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
