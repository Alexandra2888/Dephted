from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from schemas.user import UserMemory

SessionStatus = Literal["active", "completed"]
AgentType = Literal["curriculum", "theory", "problem", "feedback", "memory"]
MessageRole = Literal["user", "agent", "system"]
LessonStepType = Literal["theory", "check", "problem", "feedback"]
Verdict = Literal["passed", "failed"]


class Session(BaseModel):
    id: str
    user_id: str
    topic: str
    status: SessionStatus
    created_at: datetime
    updated_at: datetime


class Message(BaseModel):
    id: str
    session_id: str
    role: MessageRole
    content: str
    agent_type: AgentType | None = None
    created_at: datetime


class LessonStep(BaseModel):
    type: LessonStepType
    content: str
    user_answer: str | None = None
    verdict: Verdict | None = None
    code: str | None = None
    gaps: list[str] | None = None
    streaming: bool | None = None


class LessonData(BaseModel):
    session: Session
    memory: UserMemory | None
    steps: list[LessonStep]


class SessionStartRequest(BaseModel):
    topic: str


class SessionAnswerRequest(BaseModel):
    session_id: str
    answer: str


class SessionStreamRequest(BaseModel):
    session_id: str
    # None / omitted = drive the initial leg (theory); otherwise the learner's
    # comprehension answer or problem solution to resume the graph with.
    input: str | None = None


class SessionHintRequest(BaseModel):
    session_id: str


class SessionEndRequest(BaseModel):
    session_id: str


class SessionStartResponse(BaseModel):
    session_id: str


class SessionAnswerResponse(BaseModel):
    next_step: str
    verdict: Verdict | None = None


class SessionHintResponse(BaseModel):
    hint: str
