from functools import lru_cache
import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI-Assisted URL Shortener"
    database_path: str = "data/ai_assisted_shortener.db"
    public_base_url: str = "http://127.0.0.1:8010/r"
    require_engineer_signoff: bool = True
    openai_api_key: str | None = None
    openai_enabled: bool = True
    generated_workspace_dir: str = "generated_workspaces"
    openai_model: str = "gpt-4.1"
    # Provider is informational; base_url points at any OpenAI-compatible
    # Chat Completions endpoint (OpenAI, DeepSeek, Meta Llama hosts, Claude via gateway).
    openai_provider: str = "openai"
    openai_base_url: str = "https://api.openai.com/v1/chat/completions"

    model_config = SettingsConfigDict(env_file=".env", env_prefix="AI_SHORTENER_", extra="ignore")

    @property
    def database_file(self) -> Path:
        return Path(self.database_path)

    @property
    def resolved_openai_api_key(self) -> str | None:
        if not self.openai_enabled:
            return None
        return self.openai_api_key or os.getenv("OPENAI_API_KEY")

    @property
    def generated_workspace_root(self) -> Path:
        return Path(self.generated_workspace_dir)


@lru_cache
def get_settings() -> Settings:
    return Settings()
