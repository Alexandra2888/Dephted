"""Per-session token / cost budget guardrail.

An in-process ledger keyed by ``session_id``, fed from the graph's ``messages`` stream in the
router (no node changes). Checked at the top of each ``/session/stream`` leg — i.e. before the
next expensive graph run — so a session that has burned through its ceiling aborts gracefully
instead of running more paid calls.

Limitation (same as ``ratelimit.py``): state lives in this process. Counters reset on redeploy
and do not span multiple instances — move the ledger to Redis to enforce across a fleet. The
hard step cap (``recursion_limit`` in ``graph.py``) has no such limitation; it is the robust
half of the budget guardrail.
"""

from __future__ import annotations

import threading
from collections import defaultdict

from config import get_settings

# Mirror of evals/metrics.py NODE_MODEL/PRICES (kept local so runtime code does not import the
# eval package). Keep the two in sync when provider rates change.
_NODE_MODEL = {
    "memory_read": "gpt-4o-mini",
    "memory_write": "gpt-4o-mini",
    "curriculum": "gpt-4o-mini",
    "topic_guard": "gpt-4o-mini",
    "theory": "claude-sonnet-4-6",
    "comprehension": "claude-sonnet-4-6",
    "feedback": "claude-sonnet-4-6",
    "problem": "gpt-4o",
}

# USD per 1K tokens (input, output). APPROXIMATE — verify against current provider pricing.
_PRICES = {
    "gpt-4o-mini": (0.00015, 0.00060),
    "gpt-4o": (0.00250, 0.01000),
    "claude-sonnet-4-6": (0.00300, 0.01500),
}


def _cost(model: str, input_tokens: int, output_tokens: int) -> float:
    in_rate, out_rate = _PRICES.get(model, (0.0, 0.0))
    return (input_tokens / 1000) * in_rate + (output_tokens / 1000) * out_rate


class _Ledger:
    __slots__ = ("tokens", "cost")

    def __init__(self) -> None:
        self.tokens = 0
        self.cost = 0.0


_ledgers: dict[str, _Ledger] = defaultdict(_Ledger)
_lock = threading.Lock()


def record(session_id: str, node: str, input_tokens: int, output_tokens: int) -> None:
    """Add one node's token usage (and its priced cost) to the session ledger."""
    model = _NODE_MODEL.get(node, "")
    with _lock:
        ledger = _ledgers[session_id]
        ledger.tokens += input_tokens + output_tokens
        ledger.cost += _cost(model, input_tokens, output_tokens)


def usage(session_id: str) -> tuple[int, float]:
    """Return (total_tokens, total_cost_usd) recorded for the session so far."""
    with _lock:
        ledger = _ledgers[session_id]
        return ledger.tokens, ledger.cost


def over_budget(session_id: str) -> tuple[bool, str]:
    """True + a human reason if the session has exceeded its token or cost ceiling."""
    settings = get_settings()
    tokens, cost = usage(session_id)
    if tokens >= settings.guardrail_max_tokens_per_session:
        return True, f"token budget reached ({tokens} >= {settings.guardrail_max_tokens_per_session})"
    if cost >= settings.guardrail_max_cost_per_session:
        return True, f"cost budget reached (${cost:.2f} >= ${settings.guardrail_max_cost_per_session:.2f})"
    return False, ""


def reset(session_id: str) -> None:
    """Drop a session's ledger (call when the lesson completes)."""
    with _lock:
        _ledgers.pop(session_id, None)
