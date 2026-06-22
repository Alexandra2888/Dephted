-- depthed initial schema — docs/architecture.md §9
-- Idempotent: safe to re-run.

create table if not exists sessions (
    id          uuid primary key default gen_random_uuid(),
    user_id     uuid not null,
    topic       text not null,
    status      varchar(16) not null default 'active',
    created_at  timestamptz not null default now(),
    updated_at  timestamptz not null default now()
);
create index if not exists ix_sessions_user_id on sessions (user_id);

create table if not exists messages (
    id          uuid primary key default gen_random_uuid(),
    session_id  uuid not null references sessions (id) on delete cascade,
    role        varchar(16) not null,
    content     text not null,
    agent_type  varchar(32),
    section     varchar(32),
    created_at  timestamptz not null default now()
);
create index if not exists ix_messages_session_id on messages (session_id);

create table if not exists user_memory (
    id            uuid primary key default gen_random_uuid(),
    user_id       uuid not null,
    topic         text not null,
    status        varchar(16) not null,
    hint_count    integer not null default 0,
    last_seen_at  timestamptz not null default now(),
    constraint uq_user_memory_user_topic unique (user_id, topic)
);
create index if not exists ix_user_memory_user_id on user_memory (user_id);

create table if not exists traces (
    id                uuid primary key default gen_random_uuid(),
    session_id        uuid not null references sessions (id) on delete cascade,
    phoenix_trace_id  text not null,
    created_at        timestamptz not null default now()
);
create index if not exists ix_traces_session_id on traces (session_id);
