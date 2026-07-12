"""LLM client factories. Models per docs/architecture.md §5–6.

API keys come from Settings (loaded from .env), passed explicitly so we don't depend
on process-environment leakage.
"""

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from config import get_settings

# Model ids (architecture §6).
GPT_MINI = "gpt-4o-mini"  # Curriculum, Memory — routing/planning
GPT_4O = "gpt-4o"  # Problem — code generation
SONNET = "claude-sonnet-4-6"  # Theory, Feedback — explanation/critique quality


def openai_llm(model: str, temperature: float = 0.3) -> ChatOpenAI:
    settings = get_settings()
    return ChatOpenAI(
        model=model,
        temperature=temperature,
        api_key=SecretStr(settings.openai_api_key),
        streaming=True,
        # Emit a final usage-only chunk on the stream so token usage is recoverable for
        # cost metrics; without this, streamed OpenAI calls report no usage_metadata. The
        # extra chunk has empty content, which chunk_text() (agents/_util.py) returns "".
        stream_usage=True,
    )


def cached_system(text: str) -> SystemMessage:
    """A system message marked for Anthropic prompt (prefix) caching.

    The large, static Sonnet system prompt (theory, feedback) is identical across calls, so
    marking it ``cache_control: ephemeral`` lets Anthropic serve it from its prefix cache on
    repeat calls (re-explains, the comprehension/feedback pair) at a fraction of the input-token
    cost. Anthropic-only — do not use with the OpenAI clients.
    """
    return SystemMessage(
        content=[{"type": "text", "text": text, "cache_control": {"type": "ephemeral"}}]
    )


def anthropic_llm(
    model: str = SONNET, temperature: float = 0.4, max_tokens: int = 1500
) -> ChatAnthropic:
    settings = get_settings()
    return ChatAnthropic(  # type: ignore[call-arg]
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=60,
        api_key=SecretStr(settings.anthropic_api_key),
    )
