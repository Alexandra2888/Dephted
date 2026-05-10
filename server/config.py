from functools import lru_cache
from typing import Annotated

from pydantic import BeforeValidator, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _csv_to_list(v: str | list[str]) -> list[str]:
    if isinstance(v, list):
        return v
    return [s.strip() for s in v.split(",") if s.strip()]


CsvList = Annotated[list[str], BeforeValidator(_csv_to_list)]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    supabase_url: str = ""
    supabase_jwt_secret: str = ""
    supabase_service_role_key: str = ""
    database_url: str = ""
    openai_api_key: str = ""
    anthropic_api_key: str = ""

    allowed_origins: CsvList = Field(default_factory=lambda: ["http://localhost:3000"])
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
