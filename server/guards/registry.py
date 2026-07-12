"""Guard registry — the ordered lists the runner executes.

Constructed per call (guards are cheap, stateless objects). Keeps the router from importing
every guard class and gives one place to gate a guard behind config.
"""

from __future__ import annotations

from .base import Guard
from .input import InjectionScreenGuard, LengthCapGuard
from .output import CodeSafetyGuard, PromptLeakGuard, ToxicityGuard


def input_guards() -> list[Guard]:
    """Guards over raw user input, before any LLM. (scope_check runs in-graph, see guard.py.)"""
    return [InjectionScreenGuard(), LengthCapGuard()]


def output_guards() -> list[Guard]:
    """Guards over generated section text. ToxicityGuard self-disables unless enabled."""
    return [PromptLeakGuard(), CodeSafetyGuard(), ToxicityGuard()]
