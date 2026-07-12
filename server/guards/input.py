"""Input guards (run before user text reaches any LLM) + shared primitives.

The primitives ``cap_length`` and ``is_effectively_empty`` are imported by BOTH the router
(shadow-first guards) and the graph nodes (always-on structural fixes) so the logic exists
in one place. ``make_scope_decision`` lets ``agents/guard.py`` emit its existing scope verdict
as a guard decision without a second classifier call.
"""

from __future__ import annotations

import re

from config import get_settings

from .base import Action, GuardContext, GuardDecision, Stage
from .patterns import INJECTION_PATTERNS, first_match


def contains_injection(text: str) -> tuple[bool, str]:
    """True + the matched pattern name if ``text`` trips an injection marker.

    Used as an always-on node-level screen: a graded answer/solution carrying an injection
    attempt is deterministically failed rather than handed to the grader (which the structured
    verdict keeps from being *scraped*, but can still be *persuaded*). The router runs the same
    patterns as a shadow guard for telemetry.
    """
    name, _ = first_match(text, INJECTION_PATTERNS)
    return name is not None, name or ""

# Whitespace / punctuation only ⇒ effectively empty. Unicode word chars (accented letters,
# non-Latin scripts) count as content, so a legitimate non-English answer is never "empty".
_CONTENT_RE = re.compile(r"\w", re.UNICODE)


def _max_input_chars() -> int:
    return get_settings().guardrail_max_input_chars


def cap_length(text: str) -> tuple[str, bool]:
    """Truncate ``text`` to the configured cap. Returns (possibly-truncated, was_capped)."""
    cap = _max_input_chars()
    if len(text) > cap:
        return text[:cap], True
    return text, False


def is_effectively_empty(text: str) -> bool:
    """True if ``text`` has no word characters (empty / whitespace / punctuation only)."""
    return _CONTENT_RE.search(text) is None


class InjectionScreenGuard:
    name = "injection_screen"
    stage = Stage.INPUT
    action = Action.BLOCK

    async def check(self, ctx: GuardContext) -> GuardDecision:
        matched, snippet = first_match(ctx.text, INJECTION_PATTERNS)
        return GuardDecision(
            guard_name=self.name,
            stage=self.stage,
            action=self.action,
            triggered=matched is not None,
            reason=f"{matched}: {snippet}" if matched else "",
        )


class LengthCapGuard:
    name = "length_cap"
    stage = Stage.INPUT
    action = Action.BLOCK

    async def check(self, ctx: GuardContext) -> GuardDecision:
        cap = _max_input_chars()
        length = len(ctx.text)
        over = length > cap
        return GuardDecision(
            guard_name=self.name,
            stage=self.stage,
            action=self.action,
            triggered=over,
            reason=f"len={length} cap={cap}" if over else "",
            score=float(length) / cap if cap else None,
        )


def make_scope_decision(out_of_scope: bool, verdict: str) -> GuardDecision:
    """Build the scope-check decision from ``topic_guard``'s existing classification.

    The scope classifier runs inside the graph (``agents/guard.py``), so scope can't run as a
    pre-graph input guard without a second LLM call. Instead ``topic_guard`` calls this to
    record its verdict; the router drains it from graph state for persistence.
    """
    return GuardDecision(
        guard_name="scope_check",
        stage=Stage.INPUT,
        action=Action.REFUSE,
        triggered=out_of_scope,
        reason=verdict,
    )
