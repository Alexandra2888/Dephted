"""Online quality dashboard — fold all three online-eval signals into one windowed report.

Batch, not an endpoint (serving stays serving, batch stays batch — run on a schedule, see
``.github/workflows/quality.yml``). This is the Phase 4 counterpart to ``aggregate_online.py``
(which reports *cost*); this reports *quality*, over the same window, from three sources:

  1. deterministic signals, on 100% of traffic, DERIVED here from the cost_events / guardrail_events
     already written in Phases 2-3 — reached-feedback (trajectory completeness), re-explain rate,
     LLM-step count, cost/session, guardrail-trigger rate, refusal rate. Free: no online writes.
  2. the sampled LLM judge — averages per dimension over ``eval_scores`` (written by online_eval.py
     for the EVAL_SAMPLE_RATE fraction of sessions), plus its coverage.
  3. human thumbs — the thumbs-up rate over ``session_feedback``.

Then the senior payoff: **judge-vs-human agreement**. For sessions that have BOTH a judge mean and
a human thumb, does the judge (mean >= threshold ⇒ "good") agree with the thumb? That is how you
answer "how do you know your judge is right?" — and the number to watch when you raise the sample
rate. ``--alert`` turns completion-rate / judge-score drift into a non-zero exit so a scheduled run
fails when quality slips.

Usage:
    uv run python -m evals.aggregate_quality                 # last 7 days
    uv run python -m evals.aggregate_quality --since 30      # last 30 days
    uv run python -m evals.aggregate_quality --alert         # fail on quality drift
    uv run python -m evals.aggregate_quality --selftest      # pure-logic self-test, no DB
"""

import argparse
import asyncio
from typing import Any

import asyncpg

from config import get_settings
from db import to_psycopg_url

DIMENSIONS = ["theory", "problem", "feedback", "trajectory"]


def _percentile(samples: list[float], p: float) -> float:
    if not samples:
        return 0.0
    ordered = sorted(samples)
    k = max(0, min(len(ordered) - 1, int(round((p / 100) * (len(ordered) - 1)))))
    return ordered[k]


async def _fetch(since_days: int) -> dict[str, Any]:
    settings = get_settings()
    dsn = to_psycopg_url(settings.database_url)
    conn = await asyncpg.connect(dsn, statement_cache_size=0, ssl="require")
    try:
        # Deterministic signals, per session, derived from the cost ledger — one row per session
        # that ran an LLM call in the window (the population for every rate below).
        det = await conn.fetch(
            """
            select session_id,
                   count(*)                             as llm_steps,
                   count(*) filter (where node = 'theory')   as theory_calls,
                   bool_or(node = 'feedback')           as reached_feedback,
                   sum(cost_usd)                        as cost
            from cost_events
            where created_at >= now() - make_interval(days => $1::int)
            group by session_id
            """,
            since_days,
        )
        # Guardrail signals, per session: did any guard fire (trigger rate), did any propose a
        # block/refuse (refusal rate — meaningful even in shadow, where it is a "would-refuse").
        guard = await conn.fetch(
            """
            select session_id,
                   bool_or(triggered)                        as triggered_any,
                   bool_or(action in ('block', 'refuse'))    as refuse_any
            from guardrail_events
            where created_at >= now() - make_interval(days => $1::int)
            group by session_id
            """,
            since_days,
        )
        scores = await conn.fetch(
            """
            select session_id, dimension, score
            from eval_scores
            where created_at >= now() - make_interval(days => $1::int)
            """,
            since_days,
        )
        thumbs = await conn.fetch(
            """
            select session_id, rating
            from session_feedback
            where created_at >= now() - make_interval(days => $1::int)
            """,
            since_days,
        )
        return {"det": det, "guard": guard, "scores": scores, "thumbs": thumbs}
    finally:
        await conn.close()


def build_report(data: dict[str, Any], positive_threshold: float) -> dict[str, Any]:
    det = data["det"]
    n = len(det) or 1

    # ── 1. Deterministic signals (100% of traffic) ────────────────────────────────────────
    reached = sum(1 for r in det if r["reached_feedback"])
    re_explained = sum(1 for r in det if int(r["theory_calls"] or 0) > 1)
    steps = [int(r["llm_steps"] or 0) for r in det]
    session_costs = [float(r["cost"] or 0.0) for r in det]

    guard_rows = data["guard"]
    triggered = sum(1 for r in guard_rows if r["triggered_any"])
    refused = sum(1 for r in guard_rows if r["refuse_any"])

    # ── 2. Sampled LLM judge ──────────────────────────────────────────────────────────────
    by_dim: dict[str, list[float]] = {d: [] for d in DIMENSIONS}
    per_session: dict[str, list[float]] = {}
    for r in data["scores"]:
        by_dim.setdefault(r["dimension"], []).append(float(r["score"]))
        per_session.setdefault(str(r["session_id"]), []).append(float(r["score"]))
    judge_mean = {
        sid: sum(vs) / len(vs) for sid, vs in per_session.items() if vs
    }
    dim_avg = {d: (sum(v) / len(v) if v else None) for d, v in by_dim.items()}
    judged_scores = [s for vs in per_session.values() for s in vs]
    judge_overall = sum(judged_scores) / len(judged_scores) if judged_scores else None

    # ── 3. Human thumbs ───────────────────────────────────────────────────────────────────
    thumbs = {str(r["session_id"]): r["rating"] for r in data["thumbs"]}
    thumbs_up = sum(1 for v in thumbs.values() if v == "up")

    # ── Judge-vs-human agreement (the point of collecting both) ───────────────────────────
    # tp = both positive, tn = both negative, fp = judge good / human down, fn = judge bad / human up.
    tp = tn = fp = fn = 0
    for sid, rating in thumbs.items():
        mean = judge_mean.get(sid)
        if mean is None:
            continue  # no judge sample for this session — can't compare
        judge_pos = mean >= positive_threshold
        human_pos = rating == "up"
        if judge_pos and human_pos:
            tp += 1
        elif not judge_pos and not human_pos:
            tn += 1
        elif judge_pos and not human_pos:
            fp += 1
        else:
            fn += 1
    compared = tp + tn + fp + fn

    return {
        "sessions": len(det),
        "deterministic": {
            "reached_feedback_rate": reached / n,
            "re_explain_rate": re_explained / n,
            "avg_llm_steps": sum(steps) / n,
            "cost_per_session_avg": sum(session_costs) / n,
            "cost_per_session_p95": _percentile(session_costs, 95),
            "guardrail_trigger_rate": (triggered / n),
            "refusal_rate": (refused / n),
        },
        "judge": {
            "sessions_scored": len(judge_mean),
            "coverage": len(judge_mean) / n,
            "overall": judge_overall,
            "by_dimension": dim_avg,
        },
        "human": {
            "thumbs": len(thumbs),
            "thumbs_up_rate": (thumbs_up / len(thumbs)) if thumbs else None,
        },
        "agreement": {
            "compared": compared,
            "rate": ((tp + tn) / compared) if compared else None,
            "tp": tp, "tn": tn, "fp": fp, "fn": fn,
        },
    }


def _fmt_rate(v: float | None) -> str:
    return "  n/a" if v is None else f"{v:.0%}"


def _fmt_score(v: float | None) -> str:
    return "n/a" if v is None else f"{v:.3f}"


def format_report(rep: dict[str, Any]) -> str:
    d = rep["deterministic"]
    j = rep["judge"]
    h = rep["human"]
    a = rep["agreement"]
    lines = ["\nOnline quality report:"]
    lines.append(f"  sessions            {rep['sessions']}")
    lines.append("  deterministic (100% of traffic):")
    lines.append(f"    reached feedback    {_fmt_rate(d['reached_feedback_rate'])}")
    lines.append(f"    re-explain rate     {_fmt_rate(d['re_explain_rate'])}")
    lines.append(f"    avg LLM steps       {d['avg_llm_steps']:.1f}")
    lines.append(
        f"    cost/session        avg ${d['cost_per_session_avg']:.4f}"
        f"   p95 ${d['cost_per_session_p95']:.4f}"
    )
    lines.append(f"    guardrail triggers  {_fmt_rate(d['guardrail_trigger_rate'])}")
    lines.append(f"    refusal rate        {_fmt_rate(d['refusal_rate'])}")
    lines.append(
        f"  judge (sampled {j['sessions_scored']} sessions, {_fmt_rate(j['coverage'])} coverage):"
    )
    lines.append(f"    overall             {_fmt_score(j['overall'])}")
    for dim in DIMENSIONS:
        lines.append(f"    {dim:<18}  {_fmt_score(j['by_dimension'].get(dim))}")
    lines.append("  human thumbs:")
    lines.append(f"    thumbs              {h['thumbs']}")
    lines.append(f"    thumbs-up rate      {_fmt_rate(h['thumbs_up_rate'])}")
    lines.append("  judge vs human agreement:")
    lines.append(f"    compared            {a['compared']}")
    lines.append(f"    agreement           {_fmt_rate(a['rate'])}")
    lines.append(
        f"    tp={a['tp']} tn={a['tn']} fp={a['fp']} fn={a['fn']}"
        "   (fp=judge-good/human-down, fn=judge-bad/human-up)"
    )
    return "\n".join(lines)


def evaluate_alert(
    rep: dict[str, Any], min_completion: float, min_judge: float
) -> tuple[bool, list[str]]:
    """Pure drift decision → (breached, reasons). Judge floor only applies once sessions are
    actually sampled (no data ⇒ no false alarm)."""
    reasons: list[str] = []
    completion = rep["deterministic"]["reached_feedback_rate"]
    if rep["sessions"] and completion < min_completion:
        reasons.append(
            f"completion rate {completion:.0%} below floor {min_completion:.0%}"
        )
    overall = rep["judge"]["overall"]
    if overall is not None and overall < min_judge:
        reasons.append(f"judge overall {overall:.3f} below floor {min_judge:.2f}")
    return (bool(reasons), reasons)


async def main(since_days: int, alert: bool) -> int:
    settings = get_settings()
    data = await _fetch(since_days)
    rep = build_report(data, settings.quality_judge_positive_threshold)
    print(format_report(rep))

    if not alert:
        return 0
    breached, reasons = evaluate_alert(
        rep, settings.quality_min_completion_rate, settings.quality_min_judge_score
    )
    print("")
    if breached:
        for r in reasons:
            print(f"FAIL: {r}.")
        return 1
    print("PASS: online quality within thresholds.")
    return 0


# ── Zero-cost self-test of the pure report logic (no DB) ─────────────────────────────────

def _selftest() -> int:
    def check(name: str, cond: bool) -> bool:
        print(f"  {'ok ' if cond else 'FAIL'} {name}")
        return cond

    # 4 sessions: s1 clean+judged-good+thumb-up, s2 reached+judged-bad+thumb-down,
    # s3 no feedback (dropped), s4 re-explained+judged-good+thumb-down (a disagreement, fp).
    data = {
        "det": [
            {"session_id": "s1", "llm_steps": 8, "theory_calls": 1, "reached_feedback": True, "cost": 0.10},
            {"session_id": "s2", "llm_steps": 8, "theory_calls": 1, "reached_feedback": True, "cost": 0.12},
            {"session_id": "s3", "llm_steps": 4, "theory_calls": 1, "reached_feedback": False, "cost": 0.05},
            {"session_id": "s4", "llm_steps": 10, "theory_calls": 2, "reached_feedback": True, "cost": 0.20},
        ],
        "guard": [
            {"session_id": "s2", "triggered_any": True, "refuse_any": True},
            {"session_id": "s4", "triggered_any": True, "refuse_any": False},
        ],
        "scores": [
            {"session_id": "s1", "dimension": "theory", "score": 0.9},
            {"session_id": "s1", "dimension": "feedback", "score": 0.9},
            {"session_id": "s2", "dimension": "theory", "score": 0.4},
            {"session_id": "s2", "dimension": "feedback", "score": 0.4},
            {"session_id": "s4", "dimension": "theory", "score": 0.9},
        ],
        "thumbs": [
            {"session_id": "s1", "rating": "up"},
            {"session_id": "s2", "rating": "down"},
            {"session_id": "s4", "rating": "down"},
        ],
    }
    rep = build_report(data, positive_threshold=0.70)
    d, j, h, a = rep["deterministic"], rep["judge"], rep["human"], rep["agreement"]
    results = [
        check("4 sessions", rep["sessions"] == 4),
        check("reached-feedback 3/4", abs(d["reached_feedback_rate"] - 0.75) < 1e-9),
        check("re-explain 1/4", abs(d["re_explain_rate"] - 0.25) < 1e-9),
        check("guardrail trigger 2/4", abs(d["guardrail_trigger_rate"] - 0.5) < 1e-9),
        check("refusal 1/4", abs(d["refusal_rate"] - 0.25) < 1e-9),
        check("judge coverage 3/4", abs(j["coverage"] - 0.75) < 1e-9),
        check("thumbs-up rate 1/3", abs((h["thumbs_up_rate"] or 0) - 1 / 3) < 1e-9),
        # agreement: s1 tp (good/up), s2 tn (bad/down), s4 fp (good/down) → 2/3
        check("agreement compared=3", a["compared"] == 3),
        check("agreement tp=1 tn=1 fp=1 fn=0", (a["tp"], a["tn"], a["fp"], a["fn"]) == (1, 1, 1, 0)),
        check("agreement rate 2/3", abs((a["rate"] or 0) - 2 / 3) < 1e-9),
    ]
    # alert logic
    breached_lo, _ = evaluate_alert(rep, min_completion=0.90, min_judge=0.60)
    breached_ok, _ = evaluate_alert(rep, min_completion=0.50, min_judge=0.60)
    results.append(check("alert fires below completion floor", breached_lo))
    results.append(check("alert quiet within thresholds", not breached_ok))
    # empty window ⇒ no false alarm
    empty = build_report({"det": [], "guard": [], "scores": [], "thumbs": []}, 0.70)
    breached_empty, _ = evaluate_alert(empty, min_completion=0.90, min_judge=0.60)
    results.append(check("empty window does not alert", not breached_empty))

    ok = all(results)
    print(f"\n{'PASS' if ok else 'FAIL'}: {sum(results)}/{len(results)} quality-report self-tests")
    return 0 if ok else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--since", type=int, default=7, help="window in days")
    parser.add_argument("--alert", action="store_true", help="exit non-zero on quality drift")
    parser.add_argument("--selftest", action="store_true", help="run pure-logic self-test (no DB)")
    args = parser.parse_args()
    if args.selftest:
        raise SystemExit(_selftest())
    raise SystemExit(asyncio.run(main(args.since, args.alert)))
