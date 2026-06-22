"""Session router: start a lesson, drive the agent graph over SSE, hint, end, fetch.

The graph streams typed events (docs/architecture.md §8): token / section_start /
section_complete / tool_call, terminated by done or error.
"""

import json
import uuid
from collections.abc import AsyncIterator
from typing import Annotated, Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Response, status
from langchain_core.messages import HumanMessage, SystemMessage
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from agents.llms import GPT_MINI, openai_llm
from db import SessionLocal, get_db
from deps import CurrentUserDep
from graph import get_graph, thread_config
from lessons import build_lesson_data, messages_from_state
from models import Message as MessageModel
from models import Session as SessionModel
from models import Trace as TraceModel
from models import UserMemory as UserMemoryModel
from schemas.session import (
    LessonData,
    SessionEndRequest,
    SessionHintRequest,
    SessionHintResponse,
    SessionStartRequest,
    SessionStartResponse,
    SessionStreamRequest,
)
from tracing import lesson_span

logger = structlog.get_logger(__name__)
router = APIRouter()

DbDep = Annotated[AsyncSession, Depends(get_db)]


async def _load_owned_session(
    db: AsyncSession, session_id: str, user_id: str
) -> SessionModel:
    try:
        sid = uuid.UUID(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Session not found") from exc
    row = await db.get(SessionModel, sid)
    if row is None or str(row.user_id) != user_id:
        raise HTTPException(status_code=404, detail="Session not found")
    return row


async def _memory_for_topic(
    db: AsyncSession, user_id: str, topic: str
) -> UserMemoryModel | None:
    result = await db.execute(
        select(UserMemoryModel).where(
            UserMemoryModel.user_id == uuid.UUID(user_id),
            UserMemoryModel.topic == topic,
        )
    )
    return result.scalar_one_or_none()


@router.post("/start", response_model=SessionStartResponse)
async def start(
    body: SessionStartRequest, user: CurrentUserDep, db: DbDep
) -> SessionStartResponse:
    row = SessionModel(user_id=uuid.UUID(user.user_id), topic=body.topic, status="active")
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return SessionStartResponse(session_id=str(row.id))


async def _finalize(
    session_id: uuid.UUID, values: dict[str, Any], trace_id: str | None
) -> None:
    """On graph END: persist the message artifact, trace id, mark session completed."""
    async with SessionLocal() as db:
        await db.execute(delete(MessageModel).where(MessageModel.session_id == session_id))
        for msg in messages_from_state(session_id, values):
            db.add(msg)
        if trace_id:
            db.add(TraceModel(session_id=session_id, phoenix_trace_id=trace_id))
        row = await db.get(SessionModel, session_id)
        if row is not None:
            row.status = "completed"
        await db.commit()


async def _event_stream(
    session_id: uuid.UUID, user_id: str, topic: str, user_input: str | None
) -> AsyncIterator[dict[str, str]]:
    graph = get_graph()
    cfg = thread_config(str(session_id))
    try:
        with lesson_span(str(session_id), user_id, topic) as trace_id:
            snapshot = await graph.aget_state(cfg)
            if not snapshot.values:
                stream_input: Any = {"user_id": user_id, "topic": topic}
            else:
                await graph.aupdate_state(cfg, {"pending_input": user_input or ""})
                stream_input = None

            async for event in graph.astream(stream_input, cfg, stream_mode="custom"):
                yield {"data": json.dumps(event)}

            snap = await graph.aget_state(cfg)
            if not snap.next:
                await _finalize(session_id, dict(snap.values), trace_id)
                yield {"data": json.dumps({"type": "done", "status": "complete"})}
            else:
                yield {
                    "data": json.dumps(
                        {"type": "done", "status": "waiting", "next": snap.next[0]}
                    )
                }
    except Exception as exc:  # noqa: BLE001 — surface as a terminal SSE error event
        logger.exception("session.stream_failed", session_id=str(session_id))
        yield {"data": json.dumps({"type": "error", "data": str(exc)})}


@router.post("/stream")
async def stream(
    body: SessionStreamRequest, user: CurrentUserDep, db: DbDep
) -> EventSourceResponse:
    row = await _load_owned_session(db, body.session_id, user.user_id)
    return EventSourceResponse(
        _event_stream(row.id, user.user_id, row.topic, body.input)
    )


@router.post("/hint", response_model=SessionHintResponse)
async def hint(
    body: SessionHintRequest, user: CurrentUserDep, db: DbDep
) -> SessionHintResponse:
    row = await _load_owned_session(db, body.session_id, user.user_id)
    snap = await get_graph().aget_state(thread_config(str(row.id)))
    problem = snap.values.get("problem_text", "") if snap.values else ""

    # Track hint usage on the topic card.
    await db.execute(
        pg_insert(UserMemoryModel)
        .values(user_id=uuid.UUID(user.user_id), topic=row.topic, status="suggested", hint_count=1)
        .on_conflict_do_update(
            constraint="uq_user_memory_user_topic",
            set_={"hint_count": UserMemoryModel.hint_count + 1},
        )
    )
    await db.commit()

    llm = openai_llm(GPT_MINI, temperature=0.4)
    response = await llm.ainvoke(
        [
            SystemMessage(
                content=(
                    "You give a single, short hint that nudges the learner toward solving "
                    "the problem. Do NOT give the solution or write the code for them."
                )
            ),
            HumanMessage(content=f"Problem:\n{problem or row.topic}\n\nGive one hint."),
        ]
    )
    hint_text = response.content if isinstance(response.content, str) else str(response.content)
    return SessionHintResponse(hint=hint_text.strip())


@router.post("/end", status_code=status.HTTP_204_NO_CONTENT)
async def end(body: SessionEndRequest, user: CurrentUserDep, db: DbDep) -> Response:
    row = await _load_owned_session(db, body.session_id, user.user_id)
    row.status = "completed"
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{session_id}", response_model=LessonData)
async def get_session(session_id: str, user: CurrentUserDep, db: DbDep) -> LessonData:
    row = await _load_owned_session(db, session_id, user.user_id)
    snap = await get_graph().aget_state(thread_config(str(row.id)))
    memory_row = await _memory_for_topic(db, user.user_id, row.topic)
    return build_lesson_data(row, memory_row, dict(snap.values) if snap.values else {})
