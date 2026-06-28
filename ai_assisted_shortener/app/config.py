from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI-Assisted URL Shortener"
    database_path: str = "data/ai_assisted_shortener.db"
    public_base_url: str = "http://127.0.0.1:8010/r"
    require_engineer_signoff: bool = True
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"

    model_config = SettingsConfigDict(env_file=".env", env_prefix="AI_SHORTENER_", extra="ignore")

    @property
    def database_file(self) -> Path:
        return Path(self.database_path)


@lru_cache
def get_settings() -> Settings:
    return Settings()
