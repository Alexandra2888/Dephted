"""Shared LangGraph state for a lesson run.

One graph thread == one session (thread_id = session_id). The checkpointer persists
this between HTTP calls, so the graph can pause at the comprehension check and the
problem submission and resume when the learner responds.
"""

from typing import Literal, TypedDict


class LessonState(TypedDict, total=False):
    # set at start
    user_id: str
    topic: str

    # memory agent (read)
    memory_summary: str

    # curriculum agent
    plan: dict[str, str]

    # scope guard (runs before theory; False → refuse, skip the lesson)
    scope_ok: bool
    # serialized GuardDecision from topic_guard, drained by the router for persistence
    scope_decision: dict[str, object]

    # theory agent
    theory_text: str
    attempts: int

    # generic resume input (the learner's latest answer / solution)
    pending_input: str | None

    # comprehension check (theory agent eval)
    comprehension_answer: str
    comprehension_verdict: Literal["passed", "failed"]

    # problem agent
    problem_text: str
    solution: str

    # feedback agent
    feedback_text: str
    gaps: list[str]
    verdict: Literal["completed", "struggling"]

    # memory agent (write)
    suggested_next: str
