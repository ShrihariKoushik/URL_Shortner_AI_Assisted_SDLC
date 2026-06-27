from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "local"
    database_url: str = "sqlite:///./data/app.db"
    base_url: str = "http://127.0.0.1:8001"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4.1-mini"
    require_human_approval: bool = True
    audit_log_path: str = "./data/audit.log"
    slug_length: int = Field(default=7, ge=4, le=32)

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()


