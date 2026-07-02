from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings. Zero-cost defaults: SQLite, in-memory cache,
    local Ollama. Everything can be overridden via environment or .env."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "AI Career Architect"
    debug: bool = False

    database_url: str = "sqlite+aiosqlite:///./career.db"
    redis_url: str = "redis://localhost:6379/0"

    llm_model: str = "ollama/qwen2.5:7b"
    llm_api_base: str = "http://localhost:11434"
    llm_timeout: int = 120

    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24

    github_token: str = ""
    cors_origins: list[str] = ["http://localhost:3000"]

    data_dir: str = "data"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
