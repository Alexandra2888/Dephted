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

    # Cost monitoring (Phase 3).
    theory_cache_enabled: bool = True  # cache first-attempt theory per (topic, difficulty)
    hint_max_per_topic: int = 3  # hint cost cap; refuse further hints past this
    cost_alert_per_session_usd: float = 0.50  # aggregate CLI --alert drift threshold (< abort)

    # Online eval (Phase 4). Deterministic signals ride free on 100% of traffic (derived from
    # cost_events / guardrail_events). This gates only the sampled LLM-judge leg, which runs
    # async off the request path — keep it low; it costs one judge pass per sampled session.
    eval_sample_rate: float = 0.05  # fraction of completed sessions the LLM judge scores
    # aggregate_quality --alert drift thresholds (a scheduled run fails when quality slips):
    quality_min_completion_rate: float = 0.80  # reached-feedback rate floor
    quality_min_judge_score: float = 0.60  # judge-overall floor (matches evals.run soft gate)
    quality_judge_positive_threshold: float = 0.70  # judge mean >= this ⇒ "judge says good"


@lru_cache
def get_settings() -> Settings:
    return Settings()
