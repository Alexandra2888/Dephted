"""User router: dashboard memory + session history."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_db
from deps import CurrentUserDep
from graph import get_graph, thread_config
from lessons import build_lesson_data
from models import Session as SessionModel
from models import UserMemory as UserMemoryModel
from schemas.session import LessonData
from schemas.user import DashboardData, TopicCard

router = APIRouter()

DbDep = Annotated[AsyncSession, Depends(get_db)]
PAGE_SIZE = 10


@router.get("/memory", response_model=DashboardData)
async def memory(user: CurrentUserDep, db: DbDep) -> DashboardData:
    uid = uuid.UUID(user.user_id)

    mem_rows = (
        await db.execute(
            select(UserMemoryModel)
            .where(UserMemoryModel.user_id == uid)
            .order_by(UserMemoryModel.last_seen_at.desc())
        )
    ).scalars().all()

    # Map topic -> most recent session id for deep-linking topic cards.
    session_rows = (
        await db.execute(
            select(SessionModel)
            .where(SessionModel.user_id == uid)
            .order_by(SessionModel.updated_at.desc())
        )
    ).scalars().all()
    session_by_topic: dict[str, str] = {}
    for s in session_rows:
        session_by_topic.setdefault(s.topic, str(s.id))

    def card(row: UserMemoryModel) -> TopicCard:
        return TopicCard(
            topic=row.topic,
            status=row.status,  # type: ignore[arg-type]
            hint_count=row.hint_count,
            last_seen_at=row.last_seen_at,
            session_id=session_by_topic.get(row.topic, ""),
        )

    topics = [card(r) for r in mem_rows if r.status in ("covered", "struggling")]
    suggested = next((card(r) for r in mem_rows if r.status == "suggested"), None)

    return DashboardData(suggested_next=suggested, topics=topics)


@router.get("/sessions", response_model=list[LessonData])
async def sessions(
    user: CurrentUserDep, db: DbDep, page: Annotated[int, Query(ge=1)] = 1
) -> list[LessonData]:
    uid = uuid.UUID(user.user_id)
    rows = (
        await db.execute(
            select(SessionModel)
            .where(SessionModel.user_id == uid)
            .order_by(SessionModel.updated_at.desc())
            .offset((page - 1) * PAGE_SIZE)
            .limit(PAGE_SIZE)
        )
    ).scalars().all()

    graph = get_graph()
    out: list[LessonData] = []
    for row in rows:
        snap = await graph.aget_state(thread_config(str(row.id)))
        out.append(build_lesson_data(row, None, dict(snap.values) if snap.values else {}))
    return out
