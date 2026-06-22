"""Build API `LessonData` from LangGraph checkpoint state, and persist the artifact.

The checkpoint state (keyed by thread_id = session_id) is the source of truth for what
a lesson page shows. `messages` rows are written at session end for the durable artifact
and history, per docs/architecture.md §9.
"""

import uuid
from typing import Any

from agents._util import extract_check_question, strip_check_question
from models import Message as MessageModel
from models import Session as SessionModel
from models import UserMemory as UserMemoryModel
from schemas.session import LessonData, LessonStep
from schemas.session import Session as SessionSchema
from schemas.user import UserMemory as UserMemorySchema


def build_steps(values: dict[str, Any]) -> list[LessonStep]:
    steps: list[LessonStep] = []

    theory = values.get("theory_text")
    if theory:
        steps.append(LessonStep(type="theory", content=strip_check_question(theory)))
        question = extract_check_question(theory)
        answer = values.get("comprehension_answer")
        if question or answer:
            verdict = values.get("comprehension_verdict")
            steps.append(
                LessonStep(
                    type="check",
                    content=question,
                    user_answer=answer,
                    verdict=verdict if verdict in ("passed", "failed") else None,
                )
            )

    problem = values.get("problem_text")
    if problem:
        steps.append(
            LessonStep(type="problem", content=problem, code=values.get("solution"))
        )

    feedback = values.get("feedback_text")
    if feedback:
        mastery = values.get("verdict")
        badge = {"completed": "passed", "struggling": "failed"}.get(mastery or "")
        steps.append(
            LessonStep(
                type="feedback",
                content=feedback,
                gaps=values.get("gaps"),
                verdict=badge,  # type: ignore[arg-type]
            )
        )

    return steps


def session_schema(row: SessionModel) -> SessionSchema:
    return SessionSchema(
        id=str(row.id),
        user_id=str(row.user_id),
        topic=row.topic,
        status=row.status,  # type: ignore[arg-type]
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def memory_schema(row: UserMemoryModel | None) -> UserMemorySchema | None:
    if row is None:
        return None
    return UserMemorySchema(
        id=str(row.id),
        user_id=str(row.user_id),
        topic=row.topic,
        status=row.status,  # type: ignore[arg-type]
        hint_count=row.hint_count,
        last_seen_at=row.last_seen_at,
    )


def build_lesson_data(
    row: SessionModel, memory_row: UserMemoryModel | None, values: dict[str, Any] | None
) -> LessonData:
    return LessonData(
        session=session_schema(row),
        memory=memory_schema(memory_row),
        steps=build_steps(values or {}),
    )


def messages_from_state(session_id: uuid.UUID, values: dict[str, Any]) -> list[MessageModel]:
    rows: list[MessageModel] = []

    def add(role: str, content: str | None, *, agent_type: str | None, section: str) -> None:
        if content:
            rows.append(
                MessageModel(
                    session_id=session_id,
                    role=role,
                    content=content,
                    agent_type=agent_type,
                    section=section,
                )
            )

    add("agent", values.get("theory_text"), agent_type="theory", section="theory")
    add("user", values.get("comprehension_answer"), agent_type=None, section="check")
    add("agent", values.get("problem_text"), agent_type="problem", section="problem")
    add("user", values.get("solution"), agent_type=None, section="problem")
    add("agent", values.get("feedback_text"), agent_type="feedback", section="feedback")
    return rows
