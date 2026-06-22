"""LangGraph assembly + lifecycle.

Routing (docs/architecture.md §6.6):

    START → memory_read → curriculum → theory → [interrupt] comprehension
            ├─ passed  → problem → [interrupt] feedback → memory_write → END
            └─ failed  → theory (re-explain, capped) → ...

The graph is compiled with `interrupt_before=["comprehension", "feedback"]` so it pauses
to wait for the learner's comprehension answer and problem solution across HTTP calls.
State is persisted by langgraph-checkpoint-postgres, keyed by thread_id = session_id.
"""

from typing import Any, Literal

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from agents.curriculum import curriculum
from agents.feedback import feedback_review
from agents.memory import memory_read, memory_write
from agents.problem import problem_generate
from agents.state import LessonState
from agents.theory import comprehension, theory_explain
from config import get_settings
from db import to_psycopg_url

MAX_THEORY_ATTEMPTS = 2
INTERRUPT_BEFORE = ["comprehension", "feedback"]

LessonGraph = CompiledStateGraph[LessonState]


def _route_after_check(state: LessonState) -> Literal["problem", "theory"]:
    if state.get("comprehension_verdict") == "passed":
        return "problem"
    if state.get("attempts", 0) >= MAX_THEORY_ATTEMPTS:
        return "problem"  # give up re-explaining; move the lesson forward
    return "theory"


def build_graph() -> StateGraph[LessonState]:
    builder: StateGraph[LessonState] = StateGraph(LessonState)
    builder.add_node("memory_read", memory_read)
    builder.add_node("curriculum", curriculum)
    builder.add_node("theory", theory_explain)
    builder.add_node("comprehension", comprehension)
    builder.add_node("problem", problem_generate)
    builder.add_node("feedback", feedback_review)
    builder.add_node("memory_write", memory_write)

    builder.add_edge(START, "memory_read")
    builder.add_edge("memory_read", "curriculum")
    builder.add_edge("curriculum", "theory")
    builder.add_edge("theory", "comprehension")
    builder.add_conditional_edges(
        "comprehension", _route_after_check, {"problem": "problem", "theory": "theory"}
    )
    builder.add_edge("problem", "feedback")
    builder.add_edge("feedback", "memory_write")
    builder.add_edge("memory_write", END)
    return builder


def compile_graph(checkpointer: BaseCheckpointSaver[Any] | None = None) -> LessonGraph:
    return build_graph().compile(
        checkpointer=checkpointer, interrupt_before=INTERRUPT_BEFORE
    )


# ── App lifecycle ────────────────────────────────────────────────────────────

_checkpointer_cm: object | None = None
_compiled: LessonGraph | None = None


def _conn_string() -> str:
    url = to_psycopg_url(get_settings().database_url)
    if "sslmode=" not in url:
        url += ("&" if "?" in url else "?") + "sslmode=require"
    return url


async def setup_graph() -> LessonGraph:
    """Open the Postgres checkpointer, run its migrations, compile the graph."""
    global _checkpointer_cm, _compiled
    cm = AsyncPostgresSaver.from_conn_string(_conn_string())
    saver = await cm.__aenter__()
    await saver.setup()
    _checkpointer_cm = cm
    _compiled = compile_graph(saver)
    return _compiled


async def teardown_graph() -> None:
    global _checkpointer_cm, _compiled
    if _checkpointer_cm is not None:
        await _checkpointer_cm.__aexit__(None, None, None)  # type: ignore[attr-defined]
        _checkpointer_cm = None
    _compiled = None


def get_graph() -> LessonGraph:
    if _compiled is None:
        raise RuntimeError("Graph not initialized; call setup_graph() in app lifespan.")
    return _compiled


def thread_config(session_id: str) -> RunnableConfig:
    return {"configurable": {"thread_id": session_id}}
