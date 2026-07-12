"""Run the eval dataset against the agent graph and score it.

Usage:
    uv run python -m evals.run                        # full dataset
    uv run python -m evals.run --limit 2              # quick subset
    uv run python -m evals.run --threshold 0.7        # judge gate
    uv run python -m evals.run --anchor-threshold 1.0 # deterministic-anchor gate

Two independent gates (exits non-zero if either fails):
  - Deterministic anchors (trajectory / verdict / attempt-cap) — the HARD gate. Read from
    the checkpoint, no LLM, can't be fooled. Must hold at `--anchor-threshold` (default 1.0).
  - LLM judges — a soft regression guard at `--threshold` (default 0.6).

Also prints agentic path metrics (cost, latency P95, step count, re-explain rate),
informational only. Runs the graph with an in-memory checkpointer (no database required).
"""

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

from langgraph.checkpoint.memory import MemorySaver

from evals import anchors, scorers
from evals.metrics import SessionMetrics, aggregate, format_report
from graph import compile_graph

DATASET = Path(__file__).parent / "dataset.jsonl"
EVAL_USER = "00000000-0000-0000-0000-000000000002"
MAX_TURNS = 6
ANCHOR_NAMES = ["trajectory_ok", "verdict_integrity", "attempt_cap_respected"]

STREAM_MODES = ["custom", "messages", "updates"]


def load_dataset(limit: int | None) -> list[dict[str, Any]]:
    rows = [json.loads(line) for line in DATASET.read_text().splitlines() if line.strip()]
    return rows[:limit] if limit else rows


async def run_example(
    graph: Any, ex: dict[str, Any]
) -> tuple[set[str], dict[str, Any], list[str], SessionMetrics]:
    cfg = {"configurable": {"thread_id": f"eval-{ex['id']}"}}
    sections: set[str] = set()
    metrics = SessionMetrics()

    async def drive(inp: str | None, initial: bool) -> None:
        if initial:
            stream_input: Any = {"user_id": EVAL_USER, "topic": ex["topic"]}
        else:
            await graph.aupdate_state(cfg, {"pending_input": inp or ""})
            stream_input = None
        metrics.start_segment()
        async for mode, payload in graph.astream(stream_input, cfg, stream_mode=STREAM_MODES):
            metrics.on_event(mode, payload)
            if mode == "custom" and isinstance(payload, dict):
                if payload.get("type") == "section_complete":
                    sections.add(payload.get("section"))

    await drive(None, initial=True)
    for _ in range(MAX_TURNS):
        snap = await graph.aget_state(cfg)
        if not snap.next:
            break
        nxt = snap.next[0]
        if nxt == "comprehension":
            await drive(ex["answer"], initial=False)
        elif nxt == "feedback":
            await drive(ex["solution"], initial=False)
        else:
            await drive(None, initial=False)

    snap = await graph.aget_state(cfg)
    return sections, dict(snap.values), list(metrics.trajectory), metrics


async def score_example(ex: dict[str, Any], sections: set[str], values: dict[str, Any]) -> dict[str, float]:
    theory = values.get("theory_text", "")
    problem = values.get("problem_text", "")
    feedback = values.get("feedback_text", "")
    return {
        "theory_faithfulness": await scorers.theory_faithfulness(theory, ex["reference_points"]),
        "problem_wellformed": await scorers.problem_wellformed(problem),
        "feedback_accuracy": await scorers.feedback_accuracy(
            problem, ex["solution"], feedback, ex["expected_gap"]
        ),
        "trajectory": scorers.trajectory("feedback" in sections),
    }


def score_anchors(trajectory: list[str], values: dict[str, Any]) -> dict[str, bool]:
    return {
        "trajectory_ok": anchors.trajectory_ok(trajectory),
        "verdict_integrity": anchors.verdict_integrity(values),
        "attempt_cap_respected": anchors.attempt_cap_respected(trajectory, values),
    }


def evaluate_gate(
    judge_overall: float,
    anchor_rates: dict[str, float],
    threshold: float,
    anchor_threshold: float,
) -> tuple[bool, list[str]]:
    """Pure gate decision → (passed, failure reasons). Anchors are hard, judges soft."""
    failures: list[str] = []
    worst_anchor = min(anchor_rates.values()) if anchor_rates else 0.0
    if worst_anchor < anchor_threshold:
        failures.append("a deterministic anchor is below threshold (broken path)")
    if judge_overall < threshold:
        failures.append("judge overall below threshold")
    return (not failures), failures


async def main(limit: int | None, threshold: float, anchor_threshold: float) -> int:
    dataset = load_dataset(limit)
    graph = compile_graph(MemorySaver())

    print(f"Running {len(dataset)} eval examples...\n")
    all_scores: list[dict[str, float]] = []
    all_anchors: list[dict[str, bool]] = []
    all_metrics: list[SessionMetrics] = []
    for ex in dataset:
        sections, values, trajectory, metrics = await run_example(graph, ex)
        scores = await score_example(ex, sections, values)
        anch = score_anchors(trajectory, values)
        all_scores.append(scores)
        all_anchors.append(anch)
        all_metrics.append(metrics)
        mean = sum(scores.values()) / len(scores)
        anchor_flag = "".join("." if anch[a] else "X" for a in ANCHOR_NAMES)
        print(
            f"  {ex['id']:<10} {ex['category']:<10} mean={mean:.2f}  anchors[{anchor_flag}]  "
            + "  ".join(f"{k.split('_')[0]}={v:.2f}" for k, v in scores.items())
        )

    dims = list(all_scores[0].keys())
    print("\nPer-dimension judge averages:")
    for d in dims:
        avg = sum(s[d] for s in all_scores) / len(all_scores)
        print(f"  {d:<22} {avg:.3f}")
    judge_overall = sum(sum(s.values()) for s in all_scores) / (len(all_scores) * len(dims))
    print(f"  {'JUDGE OVERALL':<22} {judge_overall:.3f}  (threshold {threshold:.2f})")

    print("\nDeterministic anchors (hard gate):")
    anchor_rates: dict[str, float] = {}
    for a in ANCHOR_NAMES:
        rate = sum(1 for row in all_anchors if row[a]) / len(all_anchors)
        anchor_rates[a] = rate
        flag = "" if rate >= anchor_threshold else "   <-- BELOW THRESHOLD"
        passes = sum(1 for row in all_anchors if row[a])
        print(f"  {a:<22} {passes}/{len(all_anchors)}  ({rate:.2f}){flag}")

    print(format_report(aggregate(all_metrics)))

    passed, failures = evaluate_gate(judge_overall, anchor_rates, threshold, anchor_threshold)
    print("")
    for reason in failures:
        print(f"FAIL: {reason}.")
    if passed:
        print("PASS")
        return 0
    return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--threshold", type=float, default=0.6)
    parser.add_argument("--anchor-threshold", type=float, default=1.0)
    args = parser.parse_args()
    raise SystemExit(asyncio.run(main(args.limit, args.threshold, args.anchor_threshold)))
