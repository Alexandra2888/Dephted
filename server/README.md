# server

FastAPI + LangGraph backend for depthed.

See [`../docs/architecture.md`](../docs/architecture.md) §§5–11 for the agent graph, streaming protocol, and persistence design, and [`../plan.md`](../plan.md) for the build order.

## Endpoints

- `GET /health` — liveness probe (no auth)
- `GET /me` — current user from Supabase JWT (auth required)
- `POST /session/start` — create a session → `{ session_id }`
- `POST /session/stream` — drive the agent graph over **SSE**; `input` is `null` for the
  first theory leg, otherwise the comprehension answer or problem solution
- `POST /session/hint` — a non-spoiler hint for the current problem
- `POST /session/end` — mark a session completed
- `GET /session/{id}` — full `LessonData` (rebuilt from the graph checkpoint)
- `GET /user/memory` — dashboard topic cards + suggested next
- `GET /user/sessions?page=` — session history

`/docs` shows the full surface.

## Architecture

```
POST /session/stream
   └─ LangGraph (Postgres checkpointer, thread_id = session_id)
        memory_read → curriculum → theory →┊interrupt┊ comprehension
                                            ├ passed → problem →┊interrupt┊ feedback → memory_write → END
                                            └ failed → theory (re-explain, capped at 2)
```

Agents (`agents/`): curriculum + memory (`gpt-4o-mini`), theory + feedback
(`claude-sonnet-4-6`), problem (`gpt-4o`). Each streaming node emits a typed SSE
envelope via LangGraph custom streaming: `token` / `section_start` / `section_complete`
/ `done` / `error`.

## Quick start

```
cd server
cp .env.example .env       # fill SUPABASE_URL, SUPABASE_JWT_SECRET, DATABASE_URL, model keys
uv sync
uv run python -m migrations.run     # create app tables (sessions, messages, ...)
uv run uvicorn main:app --reload --port 8000
```

The LangGraph checkpoint tables are created automatically on startup. Open
http://localhost:8000/docs.

> **DB note:** use the Supabase **Session pooler** (port 5432), not the transaction
> pooler (6543) — the checkpointer needs session-scoped prepared statements.

Smoke test:

```
curl -i localhost:8000/health                                  # 200
curl -i localhost:8000/me                                       # 401 (no token)
curl -i localhost:8000/me -H "Authorization: Bearer <jwt>"      # 200 with valid token
```

## Scripts

```
uv run ruff check .
uv run mypy .
uv run python -m migrations.run        # apply SQL migrations
uv run python -m evals.run             # run the eval suite (LLM-judged)
uv run python -m evals.run --limit 2   # quick subset
```

## Environment

| Variable                     | Purpose                                                              |
| ---------------------------- | ------------------------------------------------------------------- |
| `SUPABASE_URL`               | Project URL (JWKS for ES256/RS256 token verification)               |
| `SUPABASE_JWT_SECRET`        | Only for legacy HS256 tokens; blank for new projects                |
| `SUPABASE_SERVICE_ROLE_KEY`  | Service role key (reserved for service-role DB access)              |
| `DATABASE_URL`               | Supabase Postgres — **session pooler** connection string           |
| `OPENAI_API_KEY`             | Curriculum / Problem / Memory agents                                |
| `ANTHROPIC_API_KEY`          | Theory / Feedback agents                                            |
| `PHOENIX_COLLECTOR_ENDPOINT` | Phoenix OTel endpoint; blank disables tracing                       |
| `PHOENIX_API_KEY`            | Phoenix cloud API key                                               |
| `ALLOWED_ORIGINS`            | Comma-separated CORS origins                                        |
| `LOG_LEVEL`                  | `DEBUG` for console renderer; otherwise JSON logs                   |

## Layout

```
server/
├── main.py             # FastAPI app, lifespan (graph + tracing), CORS, routers
├── config.py           # Settings (pydantic-settings)
├── db.py               # async SQLAlchemy engine + session factory
├── models.py           # ORM models (sessions, messages, user_memory, traces)
├── deps.py             # get_current_user (Supabase JWT: ES256/RS256 via JWKS, HS256)
├── graph.py            # LangGraph assembly, Postgres checkpointer, interrupts
├── lessons.py          # build LessonData from checkpoint state; persist artifact
├── tracing.py          # Phoenix (Arize) OTel tracing
├── logging_config.py   # structlog setup
├── agents/             # curriculum, theory, problem, feedback, memory + llms
├── prompts/            # *.md agent prompts + cached loader
├── routers/            # health, me, session (SSE), user
├── schemas/            # Pydantic request/response models
├── migrations/         # SQL migrations + runner (python -m migrations.run)
└── evals/              # dataset.jsonl, scorers.py, run.py (LLM-judged eval gate)
```

## Deploy (Fly.io)

```
fly launch --no-deploy
fly secrets set SUPABASE_URL=... SUPABASE_JWT_SECRET=... DATABASE_URL=... \
  OPENAI_API_KEY=... ANTHROPIC_API_KEY=... ALLOWED_ORIGINS=https://<vercel-app>
fly deploy
```

See [`fly.toml`](fly.toml) and [`Dockerfile`](Dockerfile).
