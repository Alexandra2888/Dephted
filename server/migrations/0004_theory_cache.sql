-- Phase 3 cost monitoring — cached theory explanation keyed by (topic, difficulty,
-- prompt_version). Idempotent: safe to re-run. Mirrors models.py TheoryCache.

create table if not exists theory_cache (
    id              uuid primary key default gen_random_uuid(),
    topic           text not null,
    difficulty      varchar(32) not null,
    prompt_version  varchar(16) not null,           -- hash of the theory prompt; versions the key
    theory_text     text not null,                  -- includes the embedded **Check:** question
    hit_count       integer not null default 0,
    created_at      timestamptz not null default now(),
    constraint uq_theory_cache_key unique (topic, difficulty, prompt_version)
);
