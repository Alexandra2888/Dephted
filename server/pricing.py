"""Single source of truth for node→model mapping and token pricing.

Both runtime (``guards/budget.py``, ``cost.py``) and the offline eval package
(``evals/metrics.py``) price token usage; keeping the tables here — a leaf module that
imports nothing from either — lets both sides share one definition without the runtime
depending on ``evals``. A provider rate change is now a one-line edit in one place.
"""

from __future__ import annotations

# Which model each graph node runs on (agents/llms.py:14-16 + per-agent wiring) plus the
# non-graph ``/hint`` call. Used to price token usage without depending on provider metadata.
NODE_MODEL = {
    "memory_read": "gpt-4o-mini",
    "memory_write": "gpt-4o-mini",
    "curriculum": "gpt-4o-mini",
    "topic_guard": "gpt-4o-mini",
    "theory": "claude-sonnet-4-6",
    "comprehension": "claude-sonnet-4-6",
    "feedback": "claude-sonnet-4-6",
    "problem": "gpt-4o",
    "hint": "gpt-4o-mini",
}

# USD per 1K tokens (input, output). APPROXIMATE — verify against current provider pricing
# and edit as rates change. claude-sonnet-4-6 priced at the Sonnet tier.
PRICES = {
    "gpt-4o-mini": (0.00015, 0.00060),
    "gpt-4o": (0.00250, 0.01000),
    "claude-sonnet-4-6": (0.00300, 0.01500),
}


def model_for_node(node: str) -> str:
    """Model id a node runs on, or "" if unknown (unknown → zero cost, never a crash)."""
    return NODE_MODEL.get(node, "")


def cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """USD cost of a call. Unknown models price at 0.0 rather than raising."""
    in_rate, out_rate = PRICES.get(model, (0.0, 0.0))
    return (input_tokens / 1000) * in_rate + (output_tokens / 1000) * out_rate
