"""Online cost dashboard — aggregate persisted ``cost_events`` into a spend report.

Batch, not an endpoint: serving stays serving, batch stays batch (run on a schedule, see
``.github/workflows/cost.yml``). Reports cost per session / user / agent over a window, the
theory-cache hit rate, and a daily trend; ``--alert`` turns cost-per-session drift into a
non-zero exit so a scheduled run fails when spend creeps toward the guardrail ceiling.

Usage:
    uv run python -m evals.aggregate_online                 # last 7 days
    uv run python -m evals.aggregate_online --since 30      # last 30 days
    uv run python -m evals.aggregate_online --since 7 --alert   # fail if over threshold
"""

import argparse
import asyncio
from typing import Any

import asyncpg

from config import get_settings
from db import to_psycopg_url


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
        # Per-session cost (+ user + first-seen), the spine for session/user/daily rollups.
        sessions = await conn.fetch(
            """
            select ce.session_id, s.user_id, sum(ce.cost_usd) as cost,
                   min(ce.created_at) as ts
            from cost_events ce
            join sessions s on s.id = ce.session_id
            where ce.created_at >= now() - make_interval(days => $1::int)
            group by ce.session_id, s.user_id
            """,
            since_days,
        )
        nodes = await conn.fetch(
            """
            select node, sum(cost_usd) as cost, count(*) as calls,
                   sum(input_tokens + output_tokens) as tokens
            from cost_events
            where created_at >= now() - make_interval(days => $1::int)
            group by node
            """,
            since_days,
        )
        cache = await conn.fetchrow(
            """
            select count(*) filter (where cache_hit) as hits, count(*) as total
            from cost_events
            where node = 'theory'
              and created_at >= now() - make_interval(days => $1::int)
            """,
            since_days,
        )
        return {"sessions": sessions, "nodes": nodes, "cache": cache}
    finally:
        await conn.close()


def build_report(data: dict[str, Any], top: int) -> dict[str, Any]:
    session_costs = [float(r["cost"]) for r in data["sessions"]]
    n = len(session_costs) or 1

    per_user: dict[str, float] = {}
    per_day: dict[str, list[float]] = {}
    for r in data["sessions"]:
        uid = str(r["user_id"])
        per_user[uid] = per_user.get(uid, 0.0) + float(r["cost"])
        day = r["ts"].strftime("%Y-%m-%d")
        per_day.setdefault(day, []).append(float(r["cost"]))

    cache = data["cache"] or {}
    hits, total = int(cache.get("hits") or 0), int(cache.get("total") or 0)

    return {
        "sessions": len(session_costs),
        "total_cost": sum(session_costs),
        "cost_per_session_avg": sum(session_costs) / n,
        "cost_per_session_p95": _percentile(session_costs, 95),
        "cost_per_agent": {r["node"]: float(r["cost"]) for r in data["nodes"]},
        "top_users": sorted(per_user.items(), key=lambda kv: -kv[1])[:top],
        "by_day": {
            day: sum(costs) / len(costs) for day, costs in sorted(per_day.items())
        },
        "cache_hit_rate": (hits / total) if total else 0.0,
        "cache_hits": hits,
        "cache_total": total,
    }


def format_report(rep: dict[str, Any]) -> str:
    lines = ["\nOnline cost report:"]
    lines.append(f"  sessions            {rep['sessions']}")
    lines.append(
        f"  cost/session        avg ${rep['cost_per_session_avg']:.4f}"
        f"   p95 ${rep['cost_per_session_p95']:.4f}   (total ${rep['total_cost']:.4f})"
    )
    lines.append(
        f"  theory cache        {rep['cache_hit_rate']:.0%} hit"
        f"   ({rep['cache_hits']}/{rep['cache_total']} theory events)"
    )
    lines.append("  cost per agent:")
    for node, c in sorted(rep["cost_per_agent"].items(), key=lambda kv: -kv[1]):
        lines.append(f"    {node:<14} ${c:.4f}")
    lines.append(f"  top {len(rep['top_users'])} users by cost:")
    for uid, c in rep["top_users"]:
        lines.append(f"    {uid:<38} ${c:.4f}")
    lines.append("  cost/session by day:")
    for day, c in rep["by_day"].items():
        lines.append(f"    {day}   ${c:.4f}")
    return "\n".join(lines)


async def main(since_days: int, top: int, alert: bool) -> int:
    data = await _fetch(since_days)
    rep = build_report(data, top)
    print(format_report(rep))

    if not alert:
        return 0
    threshold = get_settings().cost_alert_per_session_usd
    avg, p95 = rep["cost_per_session_avg"], rep["cost_per_session_p95"]
    breached = avg > threshold or p95 > threshold
    print("")
    if breached:
        print(
            f"FAIL: cost/session over threshold "
            f"(avg ${avg:.4f}, p95 ${p95:.4f} vs ${threshold:.2f})."
        )
        return 1
    print(f"PASS: cost/session within threshold (${threshold:.2f}).")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--since", type=int, default=7, help="window in days")
    parser.add_argument("--top", type=int, default=10, help="top-N users by cost")
    parser.add_argument("--alert", action="store_true", help="exit non-zero if over threshold")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(main(args.since, args.top, args.alert)))
