"""Runtime guardrails (Phase 2) — composable, fail-open, shadow-first.

See ``docs/adversarial-findings.md`` for the "before" holes these close.
"""

from __future__ import annotations

from .base import (
    Action,
    Guard,
    GuardContext,
    GuardDecision,
    Stage,
    decision_as_dict,
    decision_from_dict,
    run_guards,
)
from .input import (
    cap_length,
    contains_injection,
    is_effectively_empty,
    make_scope_decision,
)
from .persistence import persist_guard_decisions
from .registry import input_guards, output_guards

__all__ = [
    "Action",
    "Guard",
    "GuardContext",
    "GuardDecision",
    "Stage",
    "cap_length",
    "contains_injection",
    "decision_as_dict",
    "decision_from_dict",
    "input_guards",
    "is_effectively_empty",
    "make_scope_decision",
    "output_guards",
    "persist_guard_decisions",
    "run_guards",
]
