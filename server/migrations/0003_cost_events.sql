-- Phase 3 cost monitoring — one row per LLM call (graph nodes + /hint).
-- Idempotent: safe to re-run. Mirrors models.py CostEvent.

create table if not exists cost_events (
    id             uuid primary key default gen_random_uuid(),
    session_id     uuid not null references sessions (id) on delete cascade,
    trace_id       text,
    node           varchar(32) not null,            -- graph node or 'hint' (the agent)
    model          varchar(48) not null,
    input_tokens   integer not null default 0,
    output_tokens  integer not null default 0,
    cost_usd       double precision not null default 0,
    latency_ms     integer not null default 0,
    cache_hit      boolean not null default false,  -- theory cache hit (tokens = 0)
    created_at     timestamptz not null default now()
);
create index if not exists ix_cost_events_session_id on cost_events (session_id);
create index if not exists ix_cost_events_trace_id   on cost_events (trace_id);
create index if not exists ix_cost_events_created_at on cost_events (created_at);
