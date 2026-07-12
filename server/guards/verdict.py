"""Structured verdict models — the type-level defense against verdict injection.

Forcing the grader to return one of these via ``llm.with_structured_output(...)`` means the
routing decision is a typed enum, not a token scraped out of free text with a regex. An
injection can still *try* (the input guard screens for it), but it can no longer produce an
out-of-band verdict token that the router keys on. This also removes the first-match-wins
regex bug class in ``agents/theory.py`` / ``agents/feedback.py`` permanently.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ComprehensionVerdict(BaseModel):
    """Grader output for the comprehension gate."""

    verdict: Literal["PASSED", "FAILED"]
    reason: str = Field(default="", description="One short sentence explaining the grade.")


class FeedbackVerdict(BaseModel):
    """Grader output for the feedback gate."""

    verdict: Literal["COMPLETED", "STRUGGLING"]
    reason: str = Field(default="", description="One short sentence explaining the grade.")
