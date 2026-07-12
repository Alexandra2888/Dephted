-- Phase 4 online eval — LLM-judge samples + human thumbs on live traffic.
-- The deterministic online signals (trajectory / step count / cost / re-explain / refusal /
-- guardrail-trigger rate) are DERIVED at aggregation time from the cost_events + guardrail_events
-- already written in Phases 2-3 — free, on 100% of traffic, no new hot-path write. These two
-- tables add only the sampled + human legs. Idempotent. Mirrors models.py EvalScore + SessionFeedback.

-- One row per (sampled session, judged dimension). Written out-of-band after the response, only
-- for the EVAL_SAMPLE_RATE fraction of completed sessions. Correlated to a Phoenix trace via trace_id.
create table if not exists eval_scores (
    id           uuid primary key default gen_random_uuid(),
    session_id   uuid not null references sessions (id) on delete cascade,
    trace_id     text,
    dimension    varchar(32) not null,            -- theory | problem | feedback | trajectory
    score        double precision not null,       -- [0, 1]
    model        varchar(48) not null,            -- judge model (or 'deterministic')
    created_at   timestamptz not null default now()
);
create index if not exists ix_eval_scores_session_id on eval_scores (session_id);
create index if not exists ix_eval_scores_created_at on eval_scores (created_at);

-- One thumb per session (PK session_id → last vote wins). Human signal on the feedback section,
-- correlated to the judge by session_id so aggregate_quality can measure judge-vs-human agreement.
create table if not exists session_feedback (
    session_id   uuid primary key references sessions (id) on delete cascade,
    rating       varchar(8) not null,             -- up | down
    created_at   timestamptz not null default now(),
    updated_at   timestamptz not null default now()
);
create index if not exists ix_session_feedback_created_at on session_feedback (created_at);
