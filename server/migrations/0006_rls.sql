-- Lock every app table out of the PostgREST API surface.
--
-- Nothing in this schema is meant to be reachable with the publishable/anon key: the Next
-- client uses Supabase for auth ONLY (supabase.auth.*, never .from()/.rpc()), and all data
-- access goes through the FastAPI server on DATABASE_URL as `postgres`, which carries
-- rolbypassrls — so RLS here costs the backend nothing.
--
-- Two independent locks, deliberately:
--   1. RLS enabled with ZERO policies  → default-deny for anon/authenticated/any future role.
--      This is what the Supabase advisor's "RLS Disabled in Public" / "Sensitive Columns
--      Exposed" criticals ask for. No policies are added on purpose: a policy here would be
--      dead weight at best and an accidental opening at worst.
--   2. Grants revoked from anon/authenticated → PostgREST 401s before RLS is even consulted.
--      Supabase's default privileges hand every new public table to these roles; undo that.
-- service_role keeps its grants (it bypasses RLS anyway and is reserved for backend use).
--
-- Idempotent: safe to re-run. Tables absent at migration time (the LangGraph checkpoint
-- tables are created on app startup, which may come after this runs) are skipped.

do $$
declare
    t text;
    tables text[] := array[
        -- 0001_init
        'sessions', 'messages', 'user_memory', 'traces',
        -- 0002-0005: guardrail / cost / online-eval telemetry
        'guardrail_events', 'cost_events', 'theory_cache', 'eval_scores', 'session_feedback',
        -- migration bookkeeping
        'schema_migrations',
        -- LangGraph Postgres checkpointer (created at app startup, not by a migration)
        'checkpoints', 'checkpoint_blobs', 'checkpoint_writes', 'checkpoint_migrations'
    ];
begin
    foreach t in array tables loop
        if to_regclass('public.' || quote_ident(t)) is null then
            raise notice 'skip % (does not exist yet)', t;
            continue;
        end if;
        execute format('alter table public.%I enable row level security', t);
        execute format('revoke all on public.%I from anon, authenticated', t);
    end loop;
end
$$;
