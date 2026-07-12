"""Composable guard protocol + shadow-first runner (Phase 2).

A `Guard` inspects one piece of text (a `GuardContext`) and returns a `GuardDecision`.
The runner executes an ordered list of guards, times each, **fails open** (a guard that
raises is logged and treated as non-triggering — a guard must never break a lesson), and
applies the shadow/enforce policy:

- shadow (``enforce=False``): every guard runs, every decision is recorded, but
  ``final_action`` is always ALLOW/FLAG — responses are unchanged.
- enforce (``enforce=True``): a triggered BLOCK/REFUSE guard sets ``final_action`` and the
  first such guard wins the returned effective action; the caller acts on it.

The runner does NOT touch the database — persistence is the caller's job so it can be moved
out of the request hot path (see ``guards.persistence``).
"""

from __future__ import annotations

import time
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol, runtime_checkable

import structlog

logger = structlog.get_logger(__name__)


class Stage(StrEnum):
    INPUT = "input"
    OUTPUT = "output"


class Action(StrEnum):
    ALLOW = "allow"
    BLOCK = "block"  # hard stop → canned refusal
    REFUSE = "refuse"  # scope refusal (fixed message)
    FLAG = "flag"  # observe only, never blocks


@dataclass(slots=True)
class GuardContext:
    session_id: str
    trace_id: str | None
    user_id: str
    text: str  # the payload this guard inspects
    section: str | None = None  # output guards: theory | problem | feedback | check


@dataclass(slots=True)
class GuardDecision:
    guard_name: str
    stage: Stage
    action: Action  # the action this guard PROPOSES when triggered
    triggered: bool
    reason: str = ""
    score: float | None = None
    latency_ms: int = 0
    # Filled by the runner:
    final_action: Action = Action.ALLOW  # what actually happened (shadow ⇒ ALLOW/FLAG)
    enforce: bool = False


def decision_as_dict(d: GuardDecision) -> dict[str, object]:
    """JSON-safe form for carrying a decision through checkpointed graph state."""
    return {
        "guard_name": d.guard_name,
        "stage": d.stage.value,
        "action": d.action.value,
        "triggered": d.triggered,
        "reason": d.reason,
        "score": d.score,
        "latency_ms": d.latency_ms,
        "final_action": d.final_action.value,
        "enforce": d.enforce,
    }


def decision_from_dict(data: Mapping[str, object]) -> GuardDecision:
    """Inverse of :func:`decision_as_dict`."""
    score_raw = data.get("score")
    score = float(score_raw) if isinstance(score_raw, int | float) else None
    latency_raw = data.get("latency_ms")
    latency = int(latency_raw) if isinstance(latency_raw, int | float | str) else 0
    return GuardDecision(
        guard_name=str(data["guard_name"]),
        stage=Stage(str(data["stage"])),
        action=Action(str(data["action"])),
        triggered=bool(data["triggered"]),
        reason=str(data.get("reason") or ""),
        score=score,
        latency_ms=latency,
        final_action=Action(str(data.get("final_action") or Action.ALLOW.value)),
        enforce=bool(data.get("enforce")),
    )


@runtime_checkable
class Guard(Protocol):
    name: str
    stage: Stage
    action: Action

    async def check(self, ctx: GuardContext) -> GuardDecision: ...


_BLOCKING = (Action.BLOCK, Action.REFUSE)


async def run_guards(
    guards: list[Guard], ctx: GuardContext, enforce: bool
) -> tuple[list[GuardDecision], Action]:
    """Run guards over one context; return (decisions, effective action).

    ``effective`` is ALLOW unless enforcing and a guard triggered a BLOCK/REFUSE, in which
    case it is the action of the first such guard. Every guard's decision is returned
    regardless, so the caller can persist the full shadow record.
    """
    decisions: list[GuardDecision] = []
    effective = Action.ALLOW
    for guard in guards:
        t0 = time.perf_counter()
        try:
            decision = await guard.check(ctx)
        except Exception as exc:  # noqa: BLE001 — fail open: a guard must never break a lesson
            logger.warning("guard.failed", guard=guard.name, error=str(exc))
            decision = GuardDecision(
                guard_name=guard.name,
                stage=guard.stage,
                action=guard.action,
                triggered=False,
                reason=f"error: {exc}",
            )
        decision.latency_ms = int((time.perf_counter() - t0) * 1000)
        decision.enforce = enforce

        if decision.triggered and enforce and decision.action in _BLOCKING:
            decision.final_action = decision.action
            if effective is Action.ALLOW:
                effective = decision.action  # first blocking guard wins
        elif decision.action is Action.FLAG:
            decision.final_action = Action.FLAG  # flags are recorded but never block
        else:
            decision.final_action = Action.ALLOW

        decisions.append(decision)
    return decisions, effective
