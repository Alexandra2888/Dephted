"""Memory Agent (gpt-4o-mini) — read user learning state at start, write at end.

Backed by the `user_memory` table. DB access is wrapped defensively: if the database
is unavailable (e.g. during evals) the node degrades to a no-op so the graph still runs.
"""

import uuid

import structlog
from langchain_core.messages import HumanMessage, SystemMessage
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from agents._util import parse_json_object
from agents.llms import GPT_MINI, openai_llm
from agents.state import LessonState
from db import SessionLocal
from models import UserMemory
from prompts import load_prompt

logger = structlog.get_logger(__name__)


async def memory_read(state: LessonState) -> dict[str, object]:
    user_id = state["user_id"]
    rows: list[UserMemory] = []
    try:
        async with SessionLocal() as db:
            result = await db.execute(
                select(UserMemory).where(UserMemory.user_id == uuid.UUID(user_id))
            )
            rows = list(result.scalars().all())
    except Exception as exc:  # noqa: BLE001 — degrade gracefully without the DB
        logger.warning("memory_read.db_unavailable", error=str(exc))

    if not rows:
        return {"memory_summary": "New learner; no prior history.", "attempts": 0}

    history = "\n".join(
        f"- {r.topic}: {r.status} (last seen {r.last_seen_at:%Y-%m-%d})" for r in rows
    )
    llm = openai_llm(GPT_MINI, temperature=0.2)
    response = await llm.ainvoke(
        [
            SystemMessage(content=load_prompt("memory")),
            HumanMessage(
                content=(
                    f"MODE: READ\nChosen topic: {state['topic']}\n"
                    f"Learner memory rows:\n{history}\n\n"
                    "Summarize in one or two sentences what's relevant for scoping this session."
                )
            ),
        ]
    )
    summary = response.content if isinstance(response.content, str) else str(response.content)
    return {"memory_summary": summary.strip(), "attempts": 0}


async def memory_write(state: LessonState) -> dict[str, object]:
    topic = state["plan"].get("topic", state["topic"])
    verdict = state.get("verdict", "struggling")
    status = "covered" if verdict == "completed" else "struggling"

    suggested_next = ""
    try:
        llm = openai_llm(GPT_MINI, temperature=0.4)
        response = await llm.ainvoke(
            [
                SystemMessage(content=load_prompt("memory")),
                HumanMessage(
                    content=(
                        f"MODE: WRITE\nTopic: {topic}\nVerdict: {verdict}\n"
                        "Return the JSON update."
                    )
                ),
            ]
        )
        body = response.content if isinstance(response.content, str) else str(response.content)
        data = parse_json_object(body)
        suggested_next = str(data.get("suggested_next", "")).strip()
    except Exception as exc:  # noqa: BLE001
        logger.warning("memory_write.llm_failed", error=str(exc))

    try:
        async with SessionLocal() as db:
            uid = uuid.UUID(state["user_id"])
            stmt = (
                pg_insert(UserMemory)
                .values(user_id=uid, topic=topic, status=status)
                .on_conflict_do_update(
                    constraint="uq_user_memory_user_topic",
                    set_={"status": status, "last_seen_at": func.now()},
                )
            )
            await db.execute(stmt)

            if suggested_next:
                await db.execute(
                    pg_insert(UserMemory)
                    .values(user_id=uid, topic=suggested_next, status="suggested")
                    .on_conflict_do_nothing(constraint="uq_user_memory_user_topic")
                )
            await db.commit()
    except Exception as exc:  # noqa: BLE001
        logger.warning("memory_write.db_unavailable", error=str(exc))

    return {"suggested_next": suggested_next}
