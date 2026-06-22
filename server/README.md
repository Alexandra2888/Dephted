# server

FastAPI + LangGraph backend for depthed.

See [`../docs/architecture.md`](../docs/architecture.md) §§5–11 for the agent graph, streaming protocol, and persistence design, and [`../plan.md`](../plan.md) for the build order.

## Status

**Phase A scaffold.** The HTTP surface is declared but most endpoints return `501 Not Implemented`. Working endpoints today:

- `GET /health` — liveness probe (no auth)
- `GET /me` — current user from Supabase JWT (auth required)

`/docs` shows the full surface (9 endpoints).

## Quick start

```
cd server
cp .env.example .env       # then fill SUPABASE_URL + SUPABASE_JWT_SECRET
uv sync
uv run uvicorn main:app --reload --port 8000
```

Then open http://localhost:8000/docs.

Smoke test:

```
curl -i localhost:8000/health                                  # 200
curl -i localhost:8000/me                                       # 401 (no token)
curl -i localhost:8000/me -H "Authorization: Bearer <jwt>"      # 200 with valid token
```

## Other scripts

```
uv run ruff check .
uv run mypy .
uv run pytest
```

## Environment

| Variable                    | Required for | Purpose                                                                            |
| --------------------------- | ------------ | ---------------------------------------------------------------------------------- |
| `SUPABASE_URL`              | Phase A      | Project URL                                                                        |
| `SUPABASE_JWT_SECRET`       | Phase A      | Supabase dashboard → Project Settings → API → JWT Secret. Used to verify FE tokens |
| `ALLOWED_ORIGINS`           | Phase A      | Comma-separated CORS origins (default `http://localhost:3000`)                     |
| `LOG_LEVEL`                 | Phase A      | `DEBUG` for console renderer; otherwise JSON logs                                  |
| `SUPABASE_SERVICE_ROLE_KEY` | Phase B      | DB writes from BE                                                                  |
| `DATABASE_URL`              | Phase B      | Supabase Postgres connection                                                       |
| `OPENAI_API_KEY`            | Phase D      | Curriculum / Problem agents                                                        |
| `ANTHROPIC_API_KEY`         | Phase D      | Theory / Feedback agents                                                           |

## Layout

```
server/
├── main.py             # FastAPI app, CORS, router mount
├── config.py           # Settings (pydantic-settings)
├── deps.py             # get_current_user (Supabase JWT, HS256)
├── logging_config.py   # structlog setup
├── routers/
│   ├── health.py       # GET /health
│   ├── me.py           # GET /me
│   ├── session.py      # POST /session/{start,answer,hint,end}, GET /session/{id}
│   └── user.py         # GET /user/{memory,sessions}
└── schemas/            # Pydantic models mirroring client/src/lib/types.ts
```
