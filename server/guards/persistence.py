"""Out-of-request-path writer for guard decisions.

Opens its own DB session (independent of the request's ``get_db``) and bulk-inserts one
``guardrail_events`` row per decision. Handed to a Starlette ``BackgroundTask`` so it runs
after the response is fully sent — zero request-path latency. Telemetry must never break a
request, so all errors are swallowed and logged. Follows the ``_finalize`` pattern in
``routers/session.py``.
"""

from __future__ import annotations

import uuid

import structlog

from db import SessionLocal
from models import GuardrailEvent

from .base import GuardDecision

logger = structlog.get_logger(__name__)


async def persist_guard_decisions(
    session_id: str, trace_id: str | None, decisions: list[GuardDecision]
) -> None:
    if not decisions:
        return
    try:
        sid = uuid.UUID(session_id)
    except ValueError:
        logger.warning("guard.persist.bad_session_id", session_id=session_id)
        return
    try:
        async with SessionLocal() as db:
            db.add_all(
                GuardrailEvent(
                    session_id=sid,
                    trace_id=trace_id,
                    stage=d.stage.value,
                    guard_name=d.guard_name,
                    action=d.action.value,
                    triggered=d.triggered,
                    final_action=d.final_action.value,
                    enforce=d.enforce,
                    reason=d.reason or None,
                    score=d.score,
                    latency_ms=d.latency_ms,
                )
                for d in decisions
            )
            await db.commit()
    except Exception as exc:  # noqa: BLE001 — telemetry must never break a request
        logger.warning("guard.persist.failed", session_id=session_id, error=str(exc))
