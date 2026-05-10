from datetime import datetime
from typing import Literal

from pydantic import BaseModel

TopicStatus = Literal["covered", "struggling", "suggested"]


class UserMemory(BaseModel):
    id: str
    user_id: str
    topic: str
    status: TopicStatus
    hint_count: int
    last_seen_at: datetime


class TopicCard(BaseModel):
    topic: str
    status: TopicStatus
    hint_count: int
    last_seen_at: datetime
    session_id: str


class DashboardData(BaseModel):
    suggested_next: TopicCard | None
    topics: list[TopicCard]
