"""Application settings, loaded from environment variables.

Nothing outside this module should read os.environ directly — every other module gets
configuration through `get_settings()` so there is a single, testable source of truth.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Database ---
    database_url: str = "postgresql+asyncpg://wardrobe:wardrobe@localhost:5432/wardrobe"

    # --- Auth ---
    jwt_secret: str = "change-me-to-a-long-random-string"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440

    # --- Object storage ---
    storage_endpoint: str = "http://localhost:9000"
    storage_bucket: str = "wardrobe-media"
    storage_access_key: str = "minioadmin"
    storage_secret_key: str = "minioadmin"
    storage_region: str = "us-east-1"
    storage_use_ssl: bool = False

    # --- LLM provider ---
    llm_provider: str = "mock"
    llm_api_key: str = ""
    llm_model: str = ""

    # --- Vision provider ---
    vision_provider: str = "mock"
    vision_api_key: str = ""
    vision_model: str = ""

    # --- Embedding provider ---
    embedding_provider: str = "mock"
    embedding_api_key: str = ""
    embedding_model: str = ""
    embedding_dimension: int = 1536

    # --- Try-on provider ---
    tryon_provider: str = "mock"
    tryon_api_key: str = ""

    # --- API ---
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
