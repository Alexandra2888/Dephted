"""Run the eval dataset against the agent graph and score it.

Usage:
    uv run python -m evals.run                 # full dataset
    uv run python -m evals.run --limit 2       # quick subset
    uv run python -m evals.run --threshold 0.7 # custom gate

Exits non-zero if the overall mean score is below the threshold, so it can gate CI.
Runs the graph with an in-memory checkpointer (no database required).
"""

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

from langgraph.checkpoint.memory import MemorySaver

from evals import scorers
from graph import compile_graph

DATASET = Path(__file__).parent / "dataset.jsonl"
EVAL_USER = "00000000-0000-0000-0000-000000000002"
MAX_TURNS = 6


def load_dataset(limit: int | None) -> list[dict[str, Any]]:
    rows = [json.loads(line) for line in DATASET.read_text().splitlines() if line.strip()]
    return rows[:limit] if limit else rows


async def run_example(graph: Any, ex: dict[str, Any]) -> tuple[set[str], dict[str, Any]]:
    cfg = {"configurable": {"thread_id": f"eval-{ex['id']}"}}
    sections: set[str] = set()

    async def drive(inp: str | None, initial: bool) -> None:
        if initial:
            stream_input: Any = {"user_id": EVAL_USER, "topic": ex["topic"]}
        else:
            await graph.aupdate_state(cfg, {"pending_input": inp or ""})
            stream_input = None
        async for ev in graph.astream(stream_input, cfg, stream_mode="custom"):
            if ev.get("type") == "section_complete":
                sections.add(ev.get("section"))

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
    return sections, dict(snap.values)


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


async def main(limit: int | None, threshold: float) -> int:
    dataset = load_dataset(limit)
    graph = compile_graph(MemorySaver())

    print(f"Running {len(dataset)} eval examples...\n")
    all_scores: list[dict[str, float]] = []
    for ex in dataset:
        sections, values = await run_example(graph, ex)
        scores = await score_example(ex, sections, values)
        all_scores.append(scores)
        mean = sum(scores.values()) / len(scores)
        print(
            f"  {ex['id']:<10} {ex['category']:<10} mean={mean:.2f}  "
            + "  ".join(f"{k.split('_')[0]}={v:.2f}" for k, v in scores.items())
        )

    dims = list(all_scores[0].keys())
    print("\nPer-dimension averages:")
    for d in dims:
        avg = sum(s[d] for s in all_scores) / len(all_scores)
        print(f"  {d:<22} {avg:.3f}")

    overall = sum(sum(s.values()) for s in all_scores) / (len(all_scores) * len(dims))
    print(f"\nOVERALL: {overall:.3f}  (threshold {threshold:.2f})")

    if overall < threshold:
        print("FAIL: below threshold")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--threshold", type=float, default=0.6)
    args = parser.parse_args()
    raise SystemExit(asyncio.run(main(args.limit, args.threshold)))
