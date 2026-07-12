"""Session router: start a lesson, drive the agent graph over SSE, hint, end, fetch.

The graph streams typed events (docs/architecture.md §8): token / section_start /
section_complete / tool_call, terminated by done or error.
"""

import json
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Annotated, Any, cast

import structlog
from fastapi import APIRouter, Depends, HTTPException, Response, status
from langchain_core.messages import HumanMessage, SystemMessage
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse
from starlette.background import BackgroundTask

from agents.llms import GPT_MINI, openai_llm
from config import get_settings
from db import SessionLocal, get_db
from deps import CurrentUserDep
from graph import get_graph, thread_config
from guards import (
    Action,
    GuardContext,
    GuardDecision,
    decision_from_dict,
    input_guards,
    output_guards,
    persist_guard_decisions,
    run_guards,
)
from guards import budget as budget_guard
from lessons import build_lesson_data, messages_from_state
from models import Message as MessageModel
from models import Session as SessionModel
from models import Trace as TraceModel
from models import UserMemory as UserMemoryModel
from ratelimit import RateLimitedUserDep
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

# Fixed refusal shown when an input guard blocks in enforce mode — constant, so it can never be
# steered into anything harmful.
GUARD_REFUSAL = (
    "That input was blocked by a safety check. Please rephrase your response and try again."
)
BUDGET_MESSAGE = "This lesson has reached its usage budget. Please start a new session to continue."


@dataclass
class GuardRun:
    """Collects guard decisions produced across one streamed request so a single BackgroundTask
    can persist them after the response is sent (zero request-path latency)."""

    session_id: str
    trace_id: str | None = None
    decisions: list[GuardDecision] = field(default_factory=list)


async def _persist_run(run: GuardRun) -> None:
    await persist_guard_decisions(run.session_id, run.trace_id, run.decisions)


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


async def _screen_input(session_id: str, user_id: str, text: str) -> tuple[list[GuardDecision], Action]:
    """Run the input guards over one text; returns (decisions, effective action)."""
    return await run_guards(
        input_guards(),
        GuardContext(session_id=session_id, trace_id=None, user_id=user_id, text=text),
        get_settings().guardrails_enforce,
    )


@router.post("/start", response_model=SessionStartResponse)
async def start(
    body: SessionStartRequest,
    user: RateLimitedUserDep,
    db: DbDep,
    response: Response,
) -> SessionStartResponse:
    row = SessionModel(user_id=uuid.UUID(user.user_id), topic=body.topic, status="active")
    db.add(row)
    await db.commit()
    await db.refresh(row)
    # Screen the topic as telemetry. The scope guard + input guards enforce at /stream (the
    # generation chokepoint); /start just records so the topic screening is observable too.
    decisions, _ = await _screen_input(str(row.id), user.user_id, body.topic)
    response.background = BackgroundTask(
        persist_guard_decisions, str(row.id), None, decisions
    )
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


def _record_usage(sid: str, payload: Any) -> None:
    """Feed one `messages`-mode stream item into the per-session token/cost ledger."""
    try:
        chunk, meta = payload
    except (TypeError, ValueError):
        return
    node = (meta or {}).get("langgraph_node")
    usage = getattr(chunk, "usage_metadata", None)
    if node and usage:
        budget_guard.record(
            sid, node, usage.get("input_tokens", 0) or 0, usage.get("output_tokens", 0) or 0
        )


async def _event_stream(
    session_id: uuid.UUID, user_id: str, topic: str, user_input: str | None, run: GuardRun
) -> AsyncIterator[dict[str, str]]:
    graph = get_graph()
    sid = str(session_id)
    cfg = thread_config(sid)
    enforce = get_settings().guardrails_enforce
    out_guards = output_guards()
    try:
        # ── Input guards (before any LLM) ──────────────────────────────────────────────
        # The user text for this leg is the resume input, or the topic on the initial leg.
        screen_text = user_input if user_input is not None else topic
        in_decisions, in_effect = await run_guards(
            input_guards(),
            GuardContext(session_id=sid, trace_id=None, user_id=user_id, text=screen_text),
            enforce,
        )
        run.decisions.extend(in_decisions)
        if enforce and in_effect in (Action.BLOCK, Action.REFUSE):
            yield {"data": json.dumps({"type": "section_start", "section": "check"})}
            yield {"data": json.dumps(
                {"type": "section_complete", "section": "check", "data": GUARD_REFUSAL}
            )}
            yield {"data": json.dumps({"type": "done", "status": "blocked"})}
            return

        # ── Budget guardrail: abort before spending more on an over-budget session ──────
        exceeded, reason = budget_guard.over_budget(sid)
        if enforce and exceeded:
            logger.info("session.budget_exceeded", session_id=sid, reason=reason)
            yield {"data": json.dumps(
                {"type": "section_complete", "section": "check", "data": BUDGET_MESSAGE}
            )}
            yield {"data": json.dumps({"type": "done", "status": "budget_exceeded"})}
            return

        with lesson_span(sid, user_id, topic) as trace_id:
            run.trace_id = trace_id
            snapshot = await graph.aget_state(cfg)
            if not snapshot.values:
                stream_input: Any = {"user_id": user_id, "topic": topic}
            else:
                await graph.aupdate_state(cfg, {"pending_input": user_input or ""})
                stream_input = None

            # Multi-mode: forward `custom` events to the client; use `messages` for token usage.
            section_buf: dict[str, list[str]] = {}
            async for mode, payload in graph.astream(
                stream_input, cfg, stream_mode=["custom", "messages"]
            ):
                if mode == "messages":
                    _record_usage(sid, payload)
                    continue
                event = cast(dict[str, Any], payload)
                yield {"data": json.dumps(event)}
                async for extra in _handle_output_guards(event, section_buf, out_guards, run, enforce):
                    yield extra

            # Drain the scope guard's decision (produced inside the graph) for persistence.
            snap = await graph.aget_state(cfg)
            scope_dec = snap.values.get("scope_decision") if snap.values else None
            if isinstance(scope_dec, dict):
                run.decisions.append(decision_from_dict(scope_dec))

            if not snap.next:
                await _finalize(session_id, dict(snap.values), trace_id)
                budget_guard.reset(sid)
                yield {"data": json.dumps({"type": "done", "status": "complete"})}
            else:
                yield {
                    "data": json.dumps(
                        {"type": "done", "status": "waiting", "next": snap.next[0]}
                    )
                }
    except Exception as exc:  # noqa: BLE001 — surface as a terminal SSE error event
        logger.exception("session.stream_failed", session_id=sid)
        yield {"data": json.dumps({"type": "error", "data": str(exc)})}


async def _handle_output_guards(
    event: dict[str, Any],
    section_buf: dict[str, list[str]],
    out_guards: list[Any],
    run: GuardRun,
    enforce: bool,
) -> AsyncIterator[dict[str, str]]:
    """Accumulate streamed section text; on section_complete, run output guards over it.

    Shadow mode only records decisions (tokens already streamed). In enforce mode a triggered
    BLOCK is surfaced as a terminal `guard_block` retraction event for the client to render —
    a post-hoc retraction, since SSE tokens cannot be un-sent (buffer-before-send is deferred).
    """
    etype = event.get("type")
    section = event.get("section")
    if etype == "token" and section:
        section_buf.setdefault(section, []).append(str(event.get("data", "")))
    elif etype == "section_complete" and section:
        text = "".join(section_buf.pop(section, []))
        if not text.strip():
            return
        decisions, effect = await run_guards(
            out_guards,
            GuardContext(
                session_id=run.session_id,
                trace_id=run.trace_id,
                user_id="",
                text=text,
                section=section,
            ),
            enforce,
        )
        run.decisions.extend(decisions)
        if enforce and effect in (Action.BLOCK, Action.REFUSE):
            yield {"data": json.dumps(
                {"type": "guard_block", "section": section, "data": GUARD_REFUSAL}
            )}


@router.post("/stream")
async def stream(
    body: SessionStreamRequest, user: RateLimitedUserDep, db: DbDep
) -> EventSourceResponse:
    row = await _load_owned_session(db, body.session_id, user.user_id)
    run = GuardRun(session_id=str(row.id))
    return EventSourceResponse(
        _event_stream(row.id, user.user_id, row.topic, body.input, run),
        background=BackgroundTask(_persist_run, run),
    )


@router.post("/hint", response_model=SessionHintResponse)
async def hint(
    body: SessionHintRequest, user: RateLimitedUserDep, db: DbDep, response: Response
) -> SessionHintResponse:
    row = await _load_owned_session(db, body.session_id, user.user_id)
    snap = await get_graph().aget_state(thread_config(str(row.id)))
    problem = snap.values.get("problem_text", "") if snap.values else ""

    # Screen the text feeding the hint LLM; persist the decision out-of-band.
    prompt_text = problem or row.topic
    decisions, effect = await _screen_input(str(row.id), user.user_id, prompt_text)
    response.background = BackgroundTask(
        persist_guard_decisions, str(row.id), None, decisions
    )
    if get_settings().guardrails_enforce and effect in (Action.BLOCK, Action.REFUSE):
        return SessionHintResponse(hint=GUARD_REFUSAL)

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
    llm_response = await llm.ainvoke(
        [
            SystemMessage(
                content=(
                    "You give a single, short hint that nudges the learner toward solving "
                    "the problem. Do NOT give the solution or write the code for them."
                )
            ),
            HumanMessage(content=f"Problem:\n{prompt_text}\n\nGive one hint."),
        ]
    )
    content = llm_response.content
    hint_text = content if isinstance(content, str) else str(content)
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
