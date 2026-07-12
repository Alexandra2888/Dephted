from functools import lru_cache
from typing import Annotated

from pydantic import BeforeValidator, Field
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


def _csv_to_list(v: str | list[str]) -> list[str]:
    if isinstance(v, list):
        return v
    return [s.strip() for s in v.split(",") if s.strip()]


CsvList = Annotated[list[str], NoDecode, BeforeValidator(_csv_to_list)]


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

    # Phoenix (Arize) tracing — optional; tracing is skipped if no endpoint is set.
    phoenix_collector_endpoint: str = ""
    phoenix_api_key: str = ""

    # Guardrails (Phase 2). Shadow-first: with enforce off, every guard still runs and
    # every decision is persisted, but responses are unchanged. Flip to true once the
    # false-positive rate is calibrated on real traffic. (The structured-verdict fix in
    # the graph nodes is NOT gated by this flag — it is an always-on bug fix.)
    guardrails_enforce: bool = False
    guardrail_max_input_chars: int = 4000  # == evals MAX_ANSWER_CHARS; caps stored answers
    guardrail_max_steps_per_session: int = 24  # LangGraph recursion_limit — runaway-loop kill
    guardrail_max_tokens_per_session: int = 120_000  # graceful abort ceiling
    guardrail_max_cost_per_session: float = 1.00  # USD, graceful abort ceiling
    guardrail_toxicity_enabled: bool = False  # OpenAI moderation — prod-only opt-in


@lru_cache
def get_settings() -> Settings:
    return Settings()
