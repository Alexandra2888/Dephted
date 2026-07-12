"""Output guards (run over generated text before/as it leaves the app).

Over SSE the tokens have usually already streamed, so in enforce mode these back a retraction
event rather than a true pre-send block (see ``routers/session.py``). In shadow mode they only
observe and persist.
"""

from __future__ import annotations

import asyncio

import structlog

from config import get_settings

from .base import Action, GuardContext, GuardDecision, Stage
from .patterns import CODE_SAFETY_PATTERNS, PROMPT_LEAK_MARKERS, first_match

logger = structlog.get_logger(__name__)

_MODERATION_TIMEOUT_S = 1.5
_MODERATION_MODEL = "omni-moderation-latest"


class PromptLeakGuard:
    name = "prompt_leak"
    stage = Stage.OUTPUT
    action = Action.BLOCK

    async def check(self, ctx: GuardContext) -> GuardDecision:
        matched, snippet = first_match(ctx.text, PROMPT_LEAK_MARKERS)
        return GuardDecision(
            guard_name=self.name,
            stage=self.stage,
            action=self.action,
            triggered=matched is not None,
            reason=f"{matched}: {snippet}" if matched else "",
        )


class CodeSafetyGuard:
    """FLAG only — backend lessons legitimately discuss subprocess/sockets, so never block."""

    name = "code_safety"
    stage = Stage.OUTPUT
    action = Action.FLAG

    async def check(self, ctx: GuardContext) -> GuardDecision:
        matched, snippet = first_match(ctx.text, CODE_SAFETY_PATTERNS)
        return GuardDecision(
            guard_name=self.name,
            stage=self.stage,
            action=self.action,
            triggered=matched is not None,
            reason=f"{matched}: {snippet}" if matched else "",
        )


class ToxicityGuard:
    """OpenAI moderation — prod-only opt-in, short timeout, fail-open.

    Disabled unless ``guardrail_toxicity_enabled`` is set. On any timeout/error it returns a
    non-triggering decision so a moderation outage can never stall or fail a lesson (the runner
    also fails open, but we guard internally too so the timeout is honoured per-call).
    """

    name = "toxicity"
    stage = Stage.OUTPUT
    action = Action.BLOCK

    async def check(self, ctx: GuardContext) -> GuardDecision:
        settings = get_settings()
        if not settings.guardrail_toxicity_enabled or not settings.openai_api_key:
            return GuardDecision(
                guard_name=self.name,
                stage=self.stage,
                action=self.action,
                triggered=False,
                reason="disabled",
            )
        if not ctx.text.strip():
            return GuardDecision(
                guard_name=self.name, stage=self.stage, action=self.action, triggered=False
            )
        try:
            flagged, score = await asyncio.wait_for(
                self._moderate(ctx.text, settings.openai_api_key), _MODERATION_TIMEOUT_S
            )
        except Exception as exc:  # noqa: BLE001 — fail open (incl. asyncio timeout)
            logger.warning("guard.toxicity.failed", error=str(exc))
            return GuardDecision(
                guard_name=self.name,
                stage=self.stage,
                action=self.action,
                triggered=False,
                reason=f"error: {exc}",
            )
        return GuardDecision(
            guard_name=self.name,
            stage=self.stage,
            action=self.action,
            triggered=flagged,
            reason="flagged by moderation" if flagged else "",
            score=score,
        )

    async def _moderate(self, text: str, api_key: str) -> tuple[bool, float]:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=api_key)
        resp = await client.moderations.create(model=_MODERATION_MODEL, input=text)
        result = resp.results[0]
        score = max(result.category_scores.model_dump().values(), default=0.0)
        return bool(result.flagged), float(score)
