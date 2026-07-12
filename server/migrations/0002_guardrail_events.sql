-- Phase 2 guardrails — one row per guard decision (shadow + enforce telemetry).
-- Idempotent: safe to re-run. Mirrors models.py GuardrailEvent.

create table if not exists guardrail_events (
    id            uuid primary key default gen_random_uuid(),
    session_id    uuid not null references sessions (id) on delete cascade,
    trace_id      text,
    stage         varchar(16) not null,          -- input | output
    guard_name    varchar(48) not null,
    action        varchar(16) not null,          -- proposed action
    triggered     boolean not null default false,
    final_action  varchar(16) not null default 'allow',
    enforce       boolean not null default false,
    reason        text,
    score         double precision,
    latency_ms    integer not null default 0,
    created_at    timestamptz not null default now()
);
create index if not exists ix_guardrail_events_session_id on guardrail_events (session_id);
create index if not exists ix_guardrail_events_trace_id   on guardrail_events (trace_id);
