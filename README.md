# depthed

> `learn by going deeper_`

A multi-agent AI tutor for backend development. Each session renders as a **progressively-revealed lesson page** — not a chat — so the artifact you walk away with is a permanent, exportable study reference.

The pedagogical core is Socratic: explain a concept, gate progress on a comprehension check, generate a coding problem scoped to what was just taught, and give feedback that flags gaps rather than praising correct answers.

## Why

- **Lesson page, not chat.** A scrollback is ephemeral; a structured page with `Theory → Check → Problem → Solution → Feedback` is a study artifact you keep and export.
- **Quality bar in the loop.** Eval gates on PRs touching prompts or graph wiring; online sampling and weekly review.
- **Honest feedback.** Feedback agent is tuned to surface gaps, not to congratulate.

## Status

Frontend in progress; backend in design. See [`docs/architecture.md`](docs/architecture.md) for the full system design.

## Stack

| Layer        | Choice                                                |
| ------------ | ----------------------------------------------------- |
| Framework    | Next.js 15 (App Router) + React 19 + TypeScript       |
| Styling      | Tailwind CSS + shadcn/ui                              |
| Server state | TanStack Query                                        |
| Auth         | Supabase SSR                                          |
| DB           | Supabase Postgres (Drizzle ORM)                       |
| Highlighting | react-syntax-highlighter                              |
| Backend      | FastAPI + LangGraph (planned, see RFC)                |
| Agents       | OpenAI (`gpt-4o`, `gpt-4o-mini`) + Anthropic (Sonnet) |
| Tracing      | Phoenix (Arize)                                       |
| Streaming    | SSE                                                   |

## Quick start

```
npm install
cp .env.local.example .env.local
npm run dev
```

Then open http://localhost:3000.

Other scripts:

```
npm run typecheck
npm run lint
npm run build
```

## Environment

`.env.local` keys (see `.env.local.example`):

| Variable                        | Purpose                                                 |
| ------------------------------- | ------------------------------------------------------- |
| `NEXT_PUBLIC_SUPABASE_URL`      | Supabase project URL                                    |
| `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` | Supabase publishable key (used by both browser and SSR client) |
| `NEXT_PUBLIC_API_URL`           | Base URL of the FastAPI backend (planned)               |

## Project layout (current)

```
src/
├── app/
│   ├── (app)/             # authed app shell, dashboard, lesson pages
│   └── (auth)/            # login, signup
├── components/
│   ├── dashboard/         # topic grid, filters, new-session input
│   ├── lesson/            # lesson-page steps (theory, check, problem, feedback, complete)
│   ├── shared/            # code block, status badge, streaming cursor, brand mark
│   ├── ui/                # shadcn primitives
│   └── logo.tsx           # DepthedLogo (wordmark | wordmark-tagline | favicon)
├── lib/
│   ├── supabase/          # browser + server SSR clients
│   ├── api/               # FastAPI client + session calls
│   ├── mock/              # mock lesson data for FE-only development
│   └── utils.ts
└── middleware.ts          # Supabase JWT cookie refresh
```

The target monorepo layout (`apps/web/` + `apps/api/`) is described in the RFC.

## Deployment

- **Frontend:** Vercel — zero-config from this repo.
- **Backend:** FastAPI on Fly.io or Railway (see RFC §11).

## Brand

Identity is monospace, terminal-inspired. The wordmark is `depthed` followed by a blinking cursor block; the favicon is `d_` in a rounded square.

`src/components/logo.tsx` exports `DepthedLogo` with three variants (`wordmark`, `wordmark-tagline`, `favicon`) and three themes (`light`, `dark`, `auto`).

Tagline: `learn by going deeper_`

## Architecture

The full system design — agent graph, streaming protocol, persistence model, tracing, and evals — lives in [`docs/architecture.md`](docs/architecture.md).

## Author

Alex.
