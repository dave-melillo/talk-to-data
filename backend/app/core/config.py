"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_name: str = "Talk To Data"
    app_version: str = "3.0.0"
    debug: bool = False

    # Database
    database_url: str = "postgresql://ttd:ttd@localhost:5432/talktodata"

    # File Upload
    max_upload_size_mb: int = 100
    allowed_extensions: list[str] = ["csv", "tsv", "xlsx", "parquet"]

    # LLM Configuration
    default_llm_provider: str = "anthropic"
    default_llm_model: str = "claude-sonnet-4-20250514"
    anthropic_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    google_api_key: Optional[str] = None

    # Query Limits
    max_query_rows: int = 10000
    query_timeout_seconds: int = 30
    
    # API Security
    require_api_key: bool = False  # Set to True to enable auth
    api_keys: str = ""  # Comma-separated list of valid API keys
    
    def get_valid_api_keys(self) -> set[str]:
        """Parse comma-separated API keys into a set."""
        if not self.api_keys:
            return set()
        return {key.strip() for key in self.api_keys.split(",") if key.strip()}


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
