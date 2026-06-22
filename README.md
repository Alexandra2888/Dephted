# depthed

> `learn by going deeper_`

A multi-agent AI tutor for backend development. Each session renders as a **progressively-revealed lesson page** — not a chat — so the artifact you walk away with is a permanent, exportable study reference.

The pedagogical core is Socratic: explain a concept, gate progress on a comprehension check, generate a coding problem scoped to what was just taught, and give feedback that flags gaps rather than praising correct answers.

## Why

- **Lesson page, not chat.** A scrollback is ephemeral; a structured page with `Theory → Check → Problem → Solution → Feedback` is a study artifact you keep and export.
- **Quality bar in the loop.** Eval gates on PRs touching prompts or graph wiring; online sampling and weekly review.
- **Honest feedback.** Feedback agent is tuned to surface gaps, not to congratulate.

## Status

v1 implemented end-to-end: Next.js frontend + FastAPI/LangGraph backend with the full
Theory → Check → Problem → Feedback loop over SSE, Supabase auth + Postgres persistence,
Phoenix tracing, and an LLM-judged eval gate. See [`docs/architecture.md`](docs/architecture.md)
for the system design and [`plan.md`](plan.md) for the build punch list.

**Deployed:** web `https://<your-vercel-app>.vercel.app` · api `https://depthed-api.fly.dev`
_(fill in after deploying — see the deploy sections below)._

## Stack

| Layer        | Choice                                                |
| ------------ | ----------------------------------------------------- |
| Framework    | Next.js 15 (App Router) + React 19 + TypeScript       |
| Styling      | Tailwind CSS + shadcn/ui                              |
| Server state | TanStack Query                                        |
| Auth         | Supabase SSR                                          |
| DB           | Supabase Postgres (SQLAlchemy 2.x async on the API)   |
| Highlighting | react-syntax-highlighter                              |
| Backend      | FastAPI + LangGraph                                    |
| Checkpointer | langgraph-checkpoint-postgres                          |
| Agents       | OpenAI (`gpt-4o`, `gpt-4o-mini`) + Anthropic (Sonnet) |
| Tracing      | Phoenix (Arize)                                       |
| Streaming    | SSE                                                   |

## Quick start

The frontend lives in `client/`; the backend will live in `server/`. All FE scripts run from inside `client/`.

```
cd client
npm install
cp .env.local.example .env.local
npm run dev
```

Then open http://localhost:3000.

Other scripts (from `client/`):

```
npm run typecheck
npm run lint
npm run build
```

### Backend (`server/`)

```
cd server
cp .env.example .env       # fill Supabase + model keys + DATABASE_URL (session pooler)
uv sync
uv run python -m migrations.run      # create app tables
uv run uvicorn main:app --reload --port 8000
```

Set `client/.env.local`'s `NEXT_PUBLIC_API_URL` to `http://localhost:8000`. Full backend
details (endpoints, agents, evals, deploy) are in [`server/README.md`](server/README.md).

## Environment

`client/.env.local` keys (see `client/.env.local.example`):

| Variable                        | Purpose                                                 |
| ------------------------------- | ------------------------------------------------------- |
| `NEXT_PUBLIC_SUPABASE_URL`      | Supabase project URL                                    |
| `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` | Supabase publishable key (used by both browser and SSR client) |
| `NEXT_PUBLIC_API_URL`           | Base URL of the FastAPI backend (planned)               |

## Project layout

```
.
├── client/                # Next.js frontend
│   └── src/
│       ├── app/             # authed shell, auth, lesson, dashboard
│       ├── components/      # dashboard, lesson, shared, ui, logo
│       ├── lib/             # supabase, api client, mock data, utils
│       └── middleware.ts    # Supabase JWT cookie refresh
├── server/                # FastAPI backend (placeholder, see server/README.md)
├── docs/
│   └── architecture.md    # full system design
├── plan.md                # build punch list (gitignored)
└── README.md
```

## Deployment

- **Frontend:** Vercel — set the project's **Root Directory** to `client/`.
- **Backend:** FastAPI on Fly.io or Railway (see RFC §11).

## Brand

Identity is monospace, terminal-inspired. The wordmark is `depthed` followed by a blinking cursor block; the favicon is `d_` in a rounded square.

`client/src/components/logo.tsx` exports `DepthedLogo` with three variants (`wordmark`, `wordmark-tagline`, `favicon`) and three themes (`light`, `dark`, `auto`).

Tagline: `learn by going deeper_`

## Architecture

The full system design — agent graph, streaming protocol, persistence model, tracing, and evals — lives in [`docs/architecture.md`](docs/architecture.md).

## Author

Alex.
