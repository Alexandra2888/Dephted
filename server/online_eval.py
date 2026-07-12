"""Phase 4 online eval — the sampled LLM-judge leg, run async off the request path.

Online eval has three signal sources (docs/architecture.md §11):

  1. deterministic signals on 100% of traffic — DERIVED from cost_events / guardrail_events at
     aggregation time (evals/aggregate_quality.py). Free, no code here.
  2. an LLM judge on a configurable sample — THIS module.
  3. human thumbs — the /session/feedback endpoint + session_feedback table.

At graph END a hash-of-session_id sample (``EVAL_SAMPLE_RATE``) is judged by reference-free
scorers and the scores persisted to ``eval_scores``. It runs inside the response
``BackgroundTask`` (routers/session._persist_run), so it never touches the request path — the
learner has already gotten every token before a judge is ever called.

Two deliberate choices:

  * **Sampling is hash-based, not RNG.** ``sampled(session_id)`` is a pure function of the id,
    so a session is deterministically in or out — reproducible, and independent of process
    state (no shared ``random`` to seed or race).
  * **Reference-free judges.** Online there is no gold ``reference_points`` / ``expected_gap``
    (those live in the offline dataset), so these grade intrinsic quality — coherence,
    well-formedness, non-sycophantic specificity — rather than agreement with a reference. They
    reuse the same judge model (``gpt-4o-mini``) as the offline scorers so the online and
    offline numbers stay comparable. Kept out of ``evals/`` on purpose: runtime must not import
    ``evals`` (same boundary as cost.py).
"""

from __future__ import annotations

import hashlib
import uuid
from typing import Any

import structlog
from langchain_core.messages import HumanMessage, SystemMessage

from agents._util import parse_json_object
from agents.llms import GPT_MINI, openai_llm
from config import get_settings
from db import SessionLocal
from models import EvalScore

logger = structlog.get_logger(__name__)

JUDGE_MODEL = GPT_MINI
_SAMPLE_BUCKETS = 10_000  # hash resolution for the sampling gate
_JSON_SUFFIX = ' Respond with JSON only: {"score": <number 0.0-1.0>, "reason": "<short>"}'


def sampled(session_id: str, rate: float) -> bool:
    """Deterministic sampling gate: is this session in the judged fraction?

    Pure function of ``session_id`` (SHA-256 → a bucket in [0, 1)), so the same session is
    always in or out — reproducible and RNG-free. ``rate <= 0`` disables online judging;
    ``rate >= 1`` judges everything.
    """
    if rate <= 0.0:
        return False
    if rate >= 1.0:
        return True
    digest = hashlib.sha256(session_id.encode()).hexdigest()
    bucket = int(digest[:8], 16) % _SAMPLE_BUCKETS
    return bucket < rate * _SAMPLE_BUCKETS


async def _judge(instruction: str, content: str) -> float:
    llm = openai_llm(JUDGE_MODEL, temperature=0.0)
    response = await llm.ainvoke(
        [SystemMessage(content=instruction + _JSON_SUFFIX), HumanMessage(content=content)]
    )
    body = response.content if isinstance(response.content, str) else str(response.content)
    data = parse_json_object(body)
    try:
        return max(0.0, min(1.0, float(data.get("score", 0.0))))
    except (TypeError, ValueError):
        return 0.0


async def _theory_quality(topic: str, theory_text: str) -> float:
    return await _judge(
        "You judge whether a programming explanation is clear, technically correct, and "
        "self-contained for a learner on the given topic. Score 1.0 for an accurate, coherent "
        "explanation; score lower for factual errors, confusion, or an off-topic answer.",
        f"Topic: {topic}\n\nExplanation:\n{theory_text}",
    )


async def _problem_wellformed(problem_text: str) -> float:
    # Same instruction as the offline scorer (evals.scorers.problem_wellformed) — already
    # reference-free, so it carries over unchanged and stays comparable across online/offline.
    return await _judge(
        "You judge whether a coding problem statement is well-formed: a single, clearly scoped, "
        "solvable task with stated expectations. Score 1.0 for a clean solvable problem, lower "
        "if vague, multi-part, or unsolvable.",
        f"Problem statement:\n{problem_text}",
    )


async def _feedback_quality(problem_text: str, solution: str, feedback_text: str) -> float:
    return await _judge(
        "You judge whether code-review feedback is specific and honest (not sycophantic) about "
        "the submitted solution. Score 1.0 if it engages with the actual code — flagging real "
        "problems, or confirming correctness with concrete specifics; score low if it is vague, "
        "flattering, or factually wrong about the code.",
        f"Problem:\n{problem_text}\n\nSubmitted solution:\n{solution}\n\nFeedback:\n{feedback_text}",
    )


async def score_session(values: dict[str, Any]) -> list[dict[str, Any]]:
    """Reference-free judge pass over a completed lesson's final checkpoint values.

    Returns one row per dimension (only for sections that actually ran). ``trajectory`` is the
    deterministic completeness check — reached the feedback section — so it is scored without a
    judge and tagged model='deterministic'.
    """
    topic = values.get("topic", "")
    theory = values.get("theory_text", "")
    problem = values.get("problem_text", "")
    solution = values.get("solution", "")
    feedback = values.get("feedback_text", "")

    rows: list[dict[str, Any]] = []
    if theory:
        rows.append({"dimension": "theory", "model": JUDGE_MODEL,
                     "score": await _theory_quality(topic, theory)})
    if problem:
        rows.append({"dimension": "problem", "model": JUDGE_MODEL,
                     "score": await _problem_wellformed(problem)})
    if feedback:
        rows.append({"dimension": "feedback", "model": JUDGE_MODEL,
                     "score": await _feedback_quality(problem, solution, feedback)})
    rows.append({"dimension": "trajectory", "model": "deterministic",
                 "score": 1.0 if feedback else 0.0})
    return rows


async def persist_eval_scores(
    session_id: str, trace_id: str | None, rows: list[dict[str, Any]]
) -> None:
    """Out-of-request-path writer — opens its own session, swallows errors (telemetry must never
    break a request). Mirrors cost.persist_cost_events / guards.persist_guard_decisions."""
    if not rows:
        return
    try:
        sid = uuid.UUID(session_id)
    except ValueError:
        logger.warning("eval.persist.bad_session_id", session_id=session_id)
        return
    try:
        async with SessionLocal() as db:
            db.add_all(
                EvalScore(
                    session_id=sid,
                    trace_id=trace_id,
                    dimension=r["dimension"],
                    score=r["score"],
                    model=r["model"],
                )
                for r in rows
            )
            await db.commit()
    except Exception as exc:  # noqa: BLE001 — telemetry must never break a request
        logger.warning("eval.persist.failed", session_id=session_id, error=str(exc))


async def maybe_score_session(
    session_id: str, trace_id: str | None, values: dict[str, Any]
) -> None:
    """Sample-gate, judge, and persist. Called from the response BackgroundTask after a session
    reaches END. A no-op unless the session is in the sample; never raises (judging happens after
    the response is sent, but a stray error still must not crash the background task)."""
    rate = get_settings().eval_sample_rate
    if not sampled(session_id, rate):
        return
    try:
        rows = await score_session(values)
    except Exception as exc:  # noqa: BLE001 — judging is best-effort, off the request path
        logger.warning("eval.score.failed", session_id=session_id, error=str(exc))
        return
    await persist_eval_scores(session_id, trace_id, rows)
    logger.info("eval.scored", session_id=session_id, dimensions=len(rows))


# ── Zero-cost self-test of the sampling gate (pure logic, no LLM / DB) ────────────────────

def _selftest() -> int:
    def check(name: str, got: bool, want: bool) -> bool:
        ok = got == want
        print(f"  {'ok ' if ok else 'FAIL'} {name}: got={got} want={want}")
        return ok

    ids = [f"00000000-0000-0000-0000-{i:012d}" for i in range(2000)]
    at_half = sum(sampled(i, 0.5) for i in ids) / len(ids)
    stable = all(sampled(i, 0.5) == sampled(i, 0.5) for i in ids)
    # Monotone: everything sampled at 0.2 is still sampled at 0.8 (nested buckets).
    monotone = all(not sampled(i, 0.2) or sampled(i, 0.8) for i in ids)

    results = [
        check("rate=0 disables", sampled(ids[0], 0.0), False),
        check("rate=1 samples all", all(sampled(i, 1.0) for i in ids[:50]), True),
        check("rate=0.5 ~ half (0.45-0.55)", 0.45 <= at_half <= 0.55, True),
        check("deterministic per id", stable, True),
        check("monotone in rate", monotone, True),
    ]
    ok = all(results)
    print(f"\n{'PASS' if ok else 'FAIL'}: {sum(results)}/{len(results)} sampling self-tests")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(_selftest())
