"""Per-request cost capture (Phase 3).

``CostCollector`` consumes the LangGraph stream (``messages`` + ``updates`` + ``custom``) and
builds one ``cost_events`` row per node execution — tokens, priced cost, wall-clock latency,
and a cache-hit marker. It is the durable analogue of the in-process ledger in
``guards/budget.py`` (which it keeps feeding, so the budget guardrail is unchanged), and the
runtime twin of ``evals/metrics.py:SessionMetrics`` (runtime must not import ``evals``).

``persist_cost_events`` is the out-of-request-path writer, cloned from
``guards/persistence.py``: it opens its own session and swallows errors so telemetry never
breaks a request. Dispatched via a Starlette ``BackgroundTask`` after the response is sent.
"""

from __future__ import annotations

import time
import uuid
from collections import defaultdict
from typing import Any

import structlog

import pricing
from db import SessionLocal
from guards import budget as budget_guard
from models import CostEvent

logger = structlog.get_logger(__name__)

# Graph node names (pricing.NODE_MODEL minus the non-graph "hint" call). Used to filter the
# `updates` stream, which is keyed by whichever node just completed.
_GRAPH_NODES = set(pricing.NODE_MODEL) - {"hint"}

CACHE_HIT_EVENT = "cache_hit"  # custom stream event emitted by a theory cache hit


class CostCollector:
    """Accumulates cost rows for one streamed request leg. Not thread-safe (single async task)."""

    def __init__(self) -> None:
        self._pending: dict[str, dict[str, int]] = defaultdict(
            lambda: {"input": 0, "output": 0}
        )
        self._cache_hit: set[str] = set()
        self._boundary: float | None = None
        self._rows: list[dict[str, Any]] = []
        self._tokens_total = 0
        self._cost_total = 0.0

    def start_segment(self) -> None:
        """Call right before ``graph.astream(...)`` — starts the per-node latency clock."""
        self._boundary = time.perf_counter()

    def on_event(self, session_id: str, mode: str, payload: Any) -> None:
        if mode == "messages":
            self._on_messages(session_id, payload)
        elif mode == "updates":
            self._on_updates(payload)
        elif mode == "custom" and isinstance(payload, dict) and (
            payload.get("type") == CACHE_HIT_EVENT
        ):
            self._cache_hit.add(str(payload.get("node", "theory")))

    def _on_messages(self, session_id: str, payload: Any) -> None:
        try:
            chunk, meta = payload
        except (TypeError, ValueError):
            return
        node = (meta or {}).get("langgraph_node")
        usage = getattr(chunk, "usage_metadata", None)
        if not node or not usage:
            return
        inp = usage.get("input_tokens", 0) or 0
        out = usage.get("output_tokens", 0) or 0
        self._pending[node]["input"] += inp
        self._pending[node]["output"] += out
        # Keep the in-process budget ledger fed (this replaces the old _record_usage).
        budget_guard.record(session_id, node, inp, out)

    def _on_updates(self, payload: Any) -> None:
        now = time.perf_counter()
        for node in payload or {}:
            if node not in _GRAPH_NODES:
                continue
            latency_ms = int((now - self._boundary) * 1000) if self._boundary is not None else 0
            tok = self._pending.pop(node, {"input": 0, "output": 0})
            self._emit(node, tok["input"], tok["output"], latency_ms)
            self._boundary = now

    def _emit(self, node: str, inp: int, out: int, latency_ms: int) -> None:
        cache_hit = node in self._cache_hit
        self._cache_hit.discard(node)
        model = pricing.model_for_node(node)
        c = pricing.cost(model, inp, out)
        self._tokens_total += inp + out
        self._cost_total += c
        self._rows.append(
            {
                "node": node,
                "model": model,
                "input_tokens": inp,
                "output_tokens": out,
                "cost_usd": c,
                "latency_ms": latency_ms,
                "cache_hit": cache_hit,
            }
        )

    def rows(self) -> list[dict[str, Any]]:
        """Flush any node whose tokens never saw an `updates` event, then return all rows."""
        for node in list(self._pending):
            tok = self._pending.pop(node)
            self._emit(node, tok["input"], tok["output"], 0)
        # A cache-hit node with no token flow still owes a row (0 tokens, cache_hit=True).
        for node in list(self._cache_hit):
            self._emit(node, 0, 0, 0)
        return self._rows

    def totals(self) -> tuple[int, float]:
        """(total_tokens, total_cost_usd) captured so far — for span attributes."""
        return self._tokens_total, self._cost_total


async def persist_cost_events(
    session_id: str, trace_id: str | None, rows: list[dict[str, Any]]
) -> None:
    if not rows:
        return
    try:
        sid = uuid.UUID(session_id)
    except ValueError:
        logger.warning("cost.persist.bad_session_id", session_id=session_id)
        return
    try:
        async with SessionLocal() as db:
            db.add_all(
                CostEvent(
                    session_id=sid,
                    trace_id=trace_id,
                    node=r["node"],
                    model=r["model"],
                    input_tokens=r["input_tokens"],
                    output_tokens=r["output_tokens"],
                    cost_usd=r["cost_usd"],
                    latency_ms=r["latency_ms"],
                    cache_hit=r["cache_hit"],
                )
                for r in rows
            )
            await db.commit()
    except Exception as exc:  # noqa: BLE001 — telemetry must never break a request
        logger.warning("cost.persist.failed", session_id=session_id, error=str(exc))
