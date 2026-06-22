"""Phoenix (Arize) tracing — docs/architecture.md §10.

OpenTelemetry spans from every LangChain/LangGraph node are exported to Phoenix.
A per-session parent span carries `user_id`, `session_id`, `agent_type`, `topic` so
all child agent spans inherit them. Tracing is optional: if no collector endpoint is
configured, every hook here is a no-op.
"""

import os
from collections.abc import Iterator
from contextlib import contextmanager

import structlog

from config import Settings

logger = structlog.get_logger(__name__)

_ready = False


def setup_tracing(settings: Settings) -> None:
    global _ready
    if _ready or not settings.phoenix_collector_endpoint:
        if not settings.phoenix_collector_endpoint:
            logger.info("tracing.disabled")
        return
    try:
        from openinference.instrumentation.langchain import LangChainInstrumentor
        from phoenix.otel import register

        if settings.phoenix_api_key:
            os.environ.setdefault("PHOENIX_API_KEY", settings.phoenix_api_key)

        tracer_provider = register(
            project_name="depthed",
            endpoint=settings.phoenix_collector_endpoint,
            set_global_tracer_provider=False,
        )
        LangChainInstrumentor().instrument(tracer_provider=tracer_provider)
        _ready = True
        logger.info("tracing.ready", endpoint=settings.phoenix_collector_endpoint)
    except Exception as exc:  # noqa: BLE001 — never let tracing break the app
        logger.error("tracing.setup_failed", error=str(exc))


@contextmanager
def lesson_span(session_id: str, user_id: str, topic: str) -> Iterator[str | None]:
    """Open a parent span for a lesson run; yields the trace_id hex (or None)."""
    if not _ready:
        yield None
        return
    from opentelemetry import trace

    tracer = trace.get_tracer("depthed")
    with tracer.start_as_current_span("lesson.run") as span:
        span.set_attribute("session_id", session_id)
        span.set_attribute("user_id", user_id)
        span.set_attribute("topic", topic)
        span.set_attribute("agent_type", "graph")
        trace_id = format(span.get_span_context().trace_id, "032x")
        yield trace_id
