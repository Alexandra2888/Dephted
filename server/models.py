"""SQLAlchemy 2.x ORM models mirroring the persistence schema in docs/architecture.md §9.

`users` is owned by Supabase Auth and not modelled here; `user_id` columns hold the
Supabase auth UUID (the JWT `sub` claim). LangGraph checkpoint tables are managed by
`langgraph-checkpoint-postgres` and live in the same database under their own names.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def _pk() -> Mapped[uuid.UUID]:
    return mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = _pk()
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    topic: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="active", server_default="active")
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    messages: Mapped[list["Message"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = _pk()
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(16))  # user | agent | system
    content: Mapped[str] = mapped_column(Text)
    agent_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    section: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )

    session: Mapped[Session] = relationship(back_populates="messages")


class UserMemory(Base):
    __tablename__ = "user_memory"
    __table_args__ = (UniqueConstraint("user_id", "topic", name="uq_user_memory_user_topic"),)

    id: Mapped[uuid.UUID] = _pk()
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    topic: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16))  # covered | struggling | suggested
    hint_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    last_seen_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Trace(Base):
    __tablename__ = "traces"

    id: Mapped[uuid.UUID] = _pk()
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), index=True
    )
    phoenix_trace_id: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )


class GuardrailEvent(Base):
    """One row per guard decision (Phase 2). Written out-of-band via BackgroundTask; used to
    calibrate thresholds and measure the false-positive rate during the shadow rollout.
    Correlated to a Phoenix trace via ``trace_id`` and to a lesson via ``session_id``."""

    __tablename__ = "guardrail_events"

    id: Mapped[uuid.UUID] = _pk()
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), index=True
    )
    trace_id: Mapped[str | None] = mapped_column(Text, nullable=True, index=True)
    stage: Mapped[str] = mapped_column(String(16))  # input | output
    guard_name: Mapped[str] = mapped_column(String(48))
    action: Mapped[str] = mapped_column(String(16))  # proposed action
    triggered: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    final_action: Mapped[str] = mapped_column(
        String(16), default="allow", server_default="allow"
    )
    enforce: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )


class CostEvent(Base):
    """One row per LLM call (Phase 3). Written out-of-band via BackgroundTask from the session
    stream (graph nodes) and the /hint endpoint. Durable sink for the in-process ledger in
    ``guards/budget.py`` — answers cost per session / user / agent over time, and (via
    ``cache_hit``) the theory-cache hit rate. Correlated to a Phoenix trace via ``trace_id``."""

    __tablename__ = "cost_events"

    id: Mapped[uuid.UUID] = _pk()
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), index=True
    )
    trace_id: Mapped[str | None] = mapped_column(Text, nullable=True, index=True)
    node: Mapped[str] = mapped_column(String(32))  # graph node or "hint" — the agent
    model: Mapped[str] = mapped_column(String(48))
    input_tokens: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    output_tokens: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0, server_default="0")
    latency_ms: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    cache_hit: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )


class TheoryCache(Base):
    """Cached theory explanation (Phase 3) keyed by (topic, difficulty, prompt_version). Theory
    is deterministic-ish per topic+difficulty, so the expensive Sonnet call is skipped on repeat
    topics. ``prompt_version`` (a hash of the theory prompt) versions the key, so editing the
    prompt naturally invalidates old rows. The cached text includes the embedded ``**Check:**``
    comprehension question."""

    __tablename__ = "theory_cache"
    __table_args__ = (
        UniqueConstraint("topic", "difficulty", "prompt_version", name="uq_theory_cache_key"),
    )

    id: Mapped[uuid.UUID] = _pk()
    topic: Mapped[str] = mapped_column(Text)
    difficulty: Mapped[str] = mapped_column(String(32))
    prompt_version: Mapped[str] = mapped_column(String(16))
    theory_text: Mapped[str] = mapped_column(Text)
    hit_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
