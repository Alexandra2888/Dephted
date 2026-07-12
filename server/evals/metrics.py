"""Agentic path metrics — cost, latency, step count, re-explain rate.

RAG evals grade the answer; agent evals must grade the *path*. A lesson that reads well
but looped the re-explainer five times or spent $0.40 in tokens is a regression even if
every judge scores 1.0. These metrics are captured **in-process** from the graph stream
(no Phoenix dependency) and reported alongside the run — they are informational this
phase, not a gate.

Token usage is read from `stream_mode="messages"` chunks (`usage_metadata`, attributed to
a node via `metadata["langgraph_node"]`); per-node latency is wall-clock time between
`stream_mode="updates"` node-completion events. Latency is therefore approximate (it
includes scheduling/stream overhead) but consistent enough for a P95 trend.
"""

import time
from collections import defaultdict
from typing import Any

import pricing
from evals.anchors import KNOWN_NODES


class SessionMetrics:
    """Collects usage + timing for one lesson run. `run.py` feeds it stream events."""

    def __init__(self) -> None:
        self.tokens: dict[str, dict[str, int]] = defaultdict(
            lambda: {"input": 0, "output": 0}
        )
        self.latencies: dict[str, list[float]] = defaultdict(list)
        self.node_counts: dict[str, int] = defaultdict(int)
        # Ordered list of executed nodes — the true trajectory, captured live from the
        # `updates` stream (checkpoint metadata['writes'] is empty in this LangGraph build).
        self.trajectory: list[str] = []
        self._boundary: float | None = None

    def start_segment(self) -> None:
        """Call right before each `graph.astream(...)` segment (resets the latency clock)."""
        self._boundary = time.perf_counter()

    def on_event(self, mode: str, payload: Any) -> None:
        if mode == "messages":
            chunk, meta = payload
            node = (meta or {}).get("langgraph_node")
            usage = getattr(chunk, "usage_metadata", None)
            if node and usage:
                self.tokens[node]["input"] += usage.get("input_tokens", 0) or 0
                self.tokens[node]["output"] += usage.get("output_tokens", 0) or 0
        elif mode == "updates":
            now = time.perf_counter()
            for node in (payload or {}).keys():
                if node not in KNOWN_NODES:
                    continue
                if self._boundary is not None:
                    self.latencies[node].append(now - self._boundary)
                self.node_counts[node] += 1
                self.trajectory.append(node)
                self._boundary = now

    # per-session rollups
    def cost_per_agent(self) -> dict[str, float]:
        return {
            node: pricing.cost(pricing.model_for_node(node), t["input"], t["output"])
            for node, t in self.tokens.items()
        }

    def total_cost(self) -> float:
        return sum(self.cost_per_agent().values())

    def step_count(self) -> int:
        return sum(self.node_counts.values())

    def re_explained(self) -> bool:
        return self.node_counts.get("theory", 0) > 1


def _percentile(samples: list[float], p: float) -> float:
    if not samples:
        return 0.0
    ordered = sorted(samples)
    k = max(0, min(len(ordered) - 1, int(round((p / 100) * (len(ordered) - 1)))))
    return ordered[k]


def aggregate(sessions: list[SessionMetrics]) -> dict[str, Any]:
    """Roll up a list of per-session metrics into the run report."""
    sessions = [s for s in sessions if s is not None]
    n = len(sessions) or 1

    cost_per_agent: dict[str, float] = defaultdict(float)
    latency_samples: dict[str, list[float]] = defaultdict(list)
    for s in sessions:
        for node, c in s.cost_per_agent().items():
            cost_per_agent[node] += c
        for node, lats in s.latencies.items():
            latency_samples[node].extend(lats)

    total_cost = sum(cost_per_agent.values())
    steps = [s.step_count() for s in sessions]
    re_explains = sum(1 for s in sessions if s.re_explained())

    return {
        "sessions": len(sessions),
        "total_cost": total_cost,
        "cost_per_session": total_cost / n,
        "cost_per_agent": dict(cost_per_agent),
        "latency_p95": {node: _percentile(lats, 95) for node, lats in latency_samples.items()},
        "avg_steps": sum(steps) / n,
        "max_steps": max(steps, default=0),
        "re_explain_rate": re_explains / n,
    }


def format_report(report: dict[str, Any]) -> str:
    lines = ["\nAgentic path metrics (informational, not gated):"]
    lines.append(f"  sessions            {report['sessions']}")
    lines.append(
        f"  cost/session        ${report['cost_per_session']:.4f}"
        f"   (total ${report['total_cost']:.4f})"
    )
    lines.append("  cost per agent:")
    for node, c in sorted(report["cost_per_agent"].items(), key=lambda kv: -kv[1]):
        lines.append(f"    {node:<14} ${c:.4f}")
    lines.append("  latency P95 per node (s):")
    for node, p95 in sorted(report["latency_p95"].items(), key=lambda kv: -kv[1]):
        lines.append(f"    {node:<14} {p95:.2f}")
    lines.append(
        f"  steps: avg={report['avg_steps']:.1f} max={report['max_steps']}"
        f"   re-explain rate={report['re_explain_rate']:.0%}"
    )
    return "\n".join(lines)
