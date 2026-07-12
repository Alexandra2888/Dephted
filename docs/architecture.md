# depthed — System Design (RFC)

**Project:** depthed
**Tagline:** `learn by going deeper_`
**Status:** Target architecture — design of record for v1.

---

## 1. Summary

depthed is a multi-agent AI learning platform that teaches backend development through a Socratic lesson loop. Each topic session renders as a progressively-revealed structured page — `Theory → Comprehension Check → Problem → Solution → Feedback` — that doubles as a permanent, exportable study artifact. The pedagogical bet is that an artifact-shaped UX produces better retention than a chat-shaped one, and that gating progression on comprehension checks (rather than free-form chat) produces a more honest learning signal.

---

## 2. Goals

depthed exists because I needed to learn this stack — Python, FastAPI, LangGraph, multi-agent design — fast, coming from a Node + Express background. The loop that actually worked for me was: a tight explanation of one concept, a comprehension check before moving on, a small problem to write, and honest feedback on what I'd missed. depthed is that loop, packaged so other backend devs in the same spot don't have to reassemble it from scratch.

Concrete goals for v1:

1. **A tutor for backend devs picking up an adjacent ecosystem.** Default audience: Node/Express engineers learning Python + FastAPI, or FastAPI engineers branching into agent frameworks. Topics are scoped for someone with adjacent experience — no "intro to programming."
2. **The artifact is the value.** Each session produces a lesson page, not a chat scrollback. You keep it, refer back to it, and export to PDF. Optimised for retention and review, not in-the-moment satisfaction.
3. **Honest, gap-flagging feedback.** The Feedback Agent is tuned to say what's wrong or missing, not to congratulate. Faster than self-grading; less ego-protective than asking a friend.

The differentiator vs. existing AI tutors is the lesson-page artifact + Socratic gating. Most are chat-shaped; this one produces a study reference the learner keeps.

---

## 3. Non-goals (v1)

- RAG / vector store. The v1 lesson loop does not need retrieval; pedagogy is generated, not retrieved.
- Model fallbacks (`with_fallbacks`). Add when a provider outage forces it.
- Server-side PDF rendering. Client-side `react-to-print` is sufficient for v1.
- Mobile app. Web-only for v1.
- Multi-tenant orgs. Single-user accounts only.

---

## 4. Constraints

- Multiple concurrent users with isolated session state.
- Auth via Supabase (email/password + OAuth).
- All agent traces captured and queryable.
- Frontend deployable to Vercel.
- Backend deployable as a single FastAPI service (Fly.io / Railway).
- Streaming end-to-end via SSE (see §8).

---

## 5. System overview

```
User (Browser)
    │
    ▼
Next.js Frontend (Vercel)
    │  REST + SSE
    ▼
FastAPI Backend
    ├── Auth middleware (Supabase JWT validation)
    ├── Guardrails (input/output, fail-open, shadow-first — §12)
    ├── Cost collector (per-node token/cost, off-hot-path — §13)
    ├── Session router
    ├── History router
    └── LangGraph Orchestrator
            ├── Curriculum Agent      (gpt-4o-mini)
            ├── Topic Guard           (gpt-4o-mini)  — scope screen, fixed refusal
            ├── Theory Agent          (claude-sonnet-4-6)
            ├── Problem Agent         (gpt-4o)
            ├── Feedback Agent        (claude-sonnet-4-6)
            └── Memory Agent          (gpt-4o-mini)
                    │
                    ▼
            Supabase (Postgres + Auth + Checkpointer)
                    │
                    ├──► Phoenix (Arize) — Tracing
                    └──► Eval pipeline — offline PR gate + online quality/cost rollups (§11)
```

---

## 6. Agent architecture (LangGraph)

Each agent is a LangGraph node. The graph is compiled with `langgraph-checkpoint-postgres` against the same Supabase Postgres instance, giving cross-session per-user persistence with no extra infrastructure.

### 6.1 Curriculum Agent — `gpt-4o-mini`

Entry point. Receives the topic, decomposes it into a session plan: theory summary → comprehension check → coding problem. Difficulty is selected from the user's history (read via Memory Agent at session start).

**Why mini:** routing/planning is low-reasoning, called every session — cost matters.

### 6.2 Theory Agent — `claude-sonnet-4-6`

Generates a concise, opinionated explanation of the concept. No padding. Ends with a single comprehension question. **Does not proceed until the user answers.**

**Why Sonnet:** explanation quality is the product. Claude tends to produce more pedagogically sound prose with fewer hallucinated specifics.

### 6.3 Problem Agent — `gpt-4o`

Activated only after Theory Agent marks comprehension as passed. Generates a minimal coding problem scoped to the concept just explained. Accepts the user's solution and routes to Feedback Agent.

**Why 4o:** problems must be syntactically correct and runnable; code-tuned models earn their keep here.

### 6.4 Feedback Agent — `claude-sonnet-4-6`

Reviews the submitted solution. Identifies specific gaps. Doesn't praise correct answers — only flags what's wrong or missing. Marks the topic as `completed` or `struggling` in memory.

**Why Sonnet:** feedback quality and tone matter; Claude is better at honest, non-sycophantic critique.

### 6.5 Memory Agent — `gpt-4o-mini`

Reads and writes user learning state: topics covered, topics struggled with, last session timestamp, suggested next topic. Runs at session start (read) and session end (write). Backed by Supabase Postgres via Drizzle.

**Why mini:** structured read/write with no creative reasoning required.

### 6.6 Routing

```
START
  ↓
Memory Agent (read)
  ↓
Curriculum Agent
  ↓
Topic Guard ──► out-of-scope ──► END (fixed refusal, content never generated)
  ↓ (in-scope)
Theory Agent ──► comprehension check
  ↓ (passed)         ↓ (failed, attempts < cap)
Problem Agent     re-explain (capped, then advance)
  ↓
Feedback Agent
  ↓
Memory Agent (write)
  ↓
END
```

Verdicts (comprehension pass/fail, feedback completed/struggling) are **typed `Literal`
fields** via `with_structured_output`, not tokens scraped from prose — see §12.2.

---

## 7. Frontend architecture

### 7.1 Stack

| Concern           | Library                  |
| ----------------- | ------------------------ |
| Framework         | Next.js (App Router)     |
| Language          | TypeScript               |
| Styling           | Tailwind CSS             |
| Components        | shadcn/ui                |
| Server state      | TanStack Query           |
| Routing           | Next App Router          |
| Auth              | Supabase SSR             |
| Code highlighting | react-syntax-highlighter |
| PDF export        | react-to-print           |

### 7.2 UI model — lesson page, not chat

Each session renders as a progressively-revealed structured document:

- Title and topic metadata at the top.
- Sections appear one at a time as the agent graph progresses: `Theory → Comprehension Check → Problem → Solution → Feedback`.
- Each section has a status badge (`pending`, `streaming`, `complete`, `struggling`).
- Code blocks use `react-syntax-highlighter`.
- The completed page is permanent — accessible from history, exportable to PDF via `react-to-print`.

This is the core UX bet: **the artifact is the value**. A chat scrollback is ephemeral; a lesson page is a study reference.

### 7.3 Optimistic updates

When the user submits an answer or requests a hint, the message is appended to the local TanStack Query cache **immediately**, before the API response. On error, TanStack rolls back. Agent streaming responses append as they arrive via SSE, with a pending skeleton shown until the first chunk lands.

### 7.4 Brand identity

Monospace, terminal-inspired. Wordmark is `depthed` followed by a blinking cursor block; favicon is `d_` in a rounded square. Implemented in `client/src/components/logo.tsx` via the `DepthedLogo` component (variants: `wordmark | wordmark-tagline | favicon`; themes: `light | dark | auto`). Generous whitespace and terminal-cursor accents are consistent across logo and lesson UI.

---

## 8. Streaming — SSE

**Decision: SSE (server-sent events), not WebSocket.**

Rationale:

- Unidirectional (server → client) is all that's needed; agent runs are one-shot.
- SSE works over plain HTTP, with no framing protocol and automatic browser reconnection.
- WebSockets add handshake, ping/pong, and reconnection logic without a benefit here.
- FastAPI's `StreamingResponse` makes the implementation trivial.

The frontend consumes `text/event-stream` and routes events by `type`:

| `type`             | Meaning                                  |
| ------------------ | ---------------------------------------- |
| `token`            | Incremental token from an agent          |
| `section_start`    | A new lesson section is starting         |
| `section_complete` | The current section finished             |
| `tool_call`        | Agent invoked a tool (logged for traces) |
| `done`             | The graph reached `END`                  |
| `error`            | Terminal error; client should rollback   |

---

## 9. Persistence — Supabase

Supabase is the **single backing store** for the entire system:

- **Auth** — Supabase Auth (email/password + OAuth).
- **Application data** — Postgres tables. _Implementation note: the original design named
  Drizzle, but Drizzle is JS-only; the Python API uses **SQLAlchemy 2.x (async)** with
  asyncpg. Schema lives in `server/models.py` + `server/migrations/`._
- **LangGraph checkpoints** — `langgraph-checkpoint-postgres` configured against the same Postgres instance, so per-user graph state lives next to the application data with no extra infra.

### 9.1 Schema

#### `users`

Managed by Supabase Auth.

#### `sessions`

```
id, user_id, topic, status (active | completed), created_at, updated_at
```

#### `messages`

```
id, session_id, role (user | agent | system), content, agent_type, section, created_at
```

`section` distinguishes which lesson-page section the message belongs to (`theory`, `problem`, `feedback`, …).

#### `user_memory`

```
id, user_id, topic, status (covered | struggling | suggested), last_seen_at
```

#### `traces`

```
id, session_id, phoenix_trace_id, created_at
```

LangGraph checkpoint tables (`checkpoints`, `checkpoint_writes`, etc.) are managed by `langgraph-checkpoint-postgres` and live in the same database under their own schema.

#### Telemetry / eval tables (migrations `0002`–`0005`)

Added by the guardrails (§12), cost (§13), and online-eval (§11.4) phases. All idempotent
and cascade-delete with their session; all **write-mostly**, populated off the request path
and read only by the batch aggregators.

```
guardrail_events(session_id, trace_id, stage, guard_name, action, triggered,
                 final_action, enforce, reason, score, latency_ms, created_at)
cost_events(session_id, trace_id, node, model, input_tokens, output_tokens,
            cost_usd, latency_ms, cache_hit, created_at)
theory_cache(topic, difficulty, prompt_version, theory_text, hit_count, created_at)
             UNIQUE(topic, difficulty, prompt_version)
eval_scores(session_id, trace_id, dimension, score, model, created_at)
session_feedback(session_id [PK], rating, created_at, updated_at)
```

---

## 10. Tracing — Phoenix (Arize)

Every LangGraph node emits OpenTelemetry spans to Phoenix. Each span is tagged with:

- `user_id`
- `session_id`
- `agent_type`
- `topic`

Trace IDs are stored in the `traces` table for cross-referencing with session data. This becomes the foundation for the eval pipeline (§11).

---

## 11. Evals — the AI quality bar

This is what turns the project from "shipped a thing" into "defined and maintained an AI quality bar."

### 11.1 What we measure

- **Theory faithfulness** — does the explanation contain factual errors? LLM-judge against curated reference notes.
- **Problem correctness** — does the generated coding problem compile and have a valid solution? Structural check + runtime check.
- **Feedback accuracy** — for known-buggy submissions, does Feedback Agent flag the right gaps? LLM-judge against labeled reference.
- **Trajectory** — did the graph route through the right sequence of agents? Trace inspection.
- **Cost per session** — total tokens × per-model rate.
- **Latency P95** per agent.

### 11.2 Where we measure

- **PR gate** — 30-example dataset run on every PR that touches prompts or graph wiring. Threshold blocks merge.
- **Online** — 5% sampling of production sessions, scored asynchronously, dashboarded weekly.

### 11.3 Dataset

Hand-curated golden set: 30 sessions across 5 backend topics (HTTP basics, REST design, async, auth, databases). Every production failure becomes a new eval case.

### 11.4 Online eval (Phase 4)

The offline suite (§11.1–11.3) gates merges; online eval watches live traffic. Three signal sources, folded into one windowed report (`evals/aggregate_quality.py`, scheduled in `quality.yml`):

- **Deterministic signals — 100% of traffic, free.** Trajectory completeness (reached feedback), re-explain rate, LLM-step count, cost/session, guardrail-trigger rate, and refusal rate are *derived* at aggregation time from the `cost_events` (Phase 3) and `guardrail_events` (Phase 2) already written — no new hot-path write.
- **LLM judge on a sample.** `EVAL_SAMPLE_RATE` (default 5%) of completed sessions are scored by reference-free judges (`online_eval.py`), run inside the after-response `BackgroundTask` so they never touch the request path. Sampling is a pure hash of `session_id` (reproducible, RNG-free). Scores land in `eval_scores`. Reference-free because online there is no gold reference — the judges grade intrinsic quality, on the same `gpt-4o-mini` as the offline scorers so the numbers stay comparable.
- **Human feedback.** A thumb on the feedback section (`POST /session/feedback` → `session_feedback`), correlated by `session_id`.

The payoff is **judge-vs-human agreement**: for sessions with both a judge mean and a thumb, does the judge (mean ≥ threshold ⇒ "good") agree with the human? That is the senior answer to "how do you know your judge is right?" — and the number to watch as the sample rate rises. `aggregate_quality --alert` turns completion-rate / judge-score drift into a non-zero exit for the scheduled run.

---

## 12. Guardrails & safety

Guardrails are a **composable protocol**, not a scatter of `if` statements. A `Guard` is a
`Protocol` (`guards/base.py`) with `name`, `stage` (`input`/`output`), `action`, and one
`async check(ctx) -> GuardDecision`. A registry (`guards/registry.py`) composes them into
ordered input/output lists; a single `run_guards(...)` runner executes them. Two policies are
first-class:

- **Fail-open.** Every guard runs inside `try/except`; a guard that raises is logged and
  degraded to a non-triggering decision. Layered at the runner, the moderation call's own
  timeout, and the persistence writer. Invariant: **a guard never breaks a lesson.**
- **Shadow-first.** A single `guardrails_enforce` flag gates enforcement. Off (default):
  every guard runs and every decision is persisted to `guardrail_events`, but nothing is
  blocked — so each pattern's real firing rate is measured before it can reject a learner.

### 12.1 The guards

| Guard | Stage | Action | What it does |
| ----- | ----- | ------ | ------------ |
| Injection screen | input | BLOCK | Regex bank of override / verdict-forcing / prompt-leak phrasings (`guards/patterns.py`). Runs on the request path before any LLM. |
| Length cap | input | BLOCK | Rejects oversized input before it reaches a paid model (cost/DoS). |
| Prompt-leak | output | BLOCK | Detects grader/rubric fragments + prompt "canaries" in streamed output. |
| Code-safety | output | **FLAG only** | Records `os.system`/`eval`/`rm -rf` sightings but never blocks — backend lessons legitimately discuss these. |
| Toxicity | output | BLOCK | OpenAI `omni-moderation-latest`, prod-only, timeout-bounded, fails open. |
| Budget | request leg | abort | In-process token/cost ledger per `session_id`; hard-stops a runaway before the next expensive graph run. Robust backstop is LangGraph's `recursion_limit`. |

### 12.2 The structural controls (the ones that matter)

The regex banks are a cheap first layer. The **real** defenses are structural and enforce
regardless of the shadow flag:

1. **`topic_guard` node.** A dedicated graph node (`agents/guard.py`, `prompts/guard.md`)
   classifies the topic as in- or out-of-scope backend learning and emits a single
   `IN_SCOPE`/`OUT_OF_SCOPE` token. It sits `curriculum → topic_guard → {theory | END}`.
   Out-of-scope requests stream a **fixed refusal constant** and route to `END` — the Theory
   agent never generates the requested content, so there is nothing to steer. Fails safe:
   unparseable output defaults to `OUT_OF_SCOPE`. (This closed the scope-abuse breach in
   `docs/adversarial-findings.md`, Finding 10.)
2. **Typed verdicts.** Comprehension/feedback verdicts are `Literal` enum fields returned via
   `with_structured_output` (`guards/verdict.py`) — not a token scraped from prose with a
   regex. This **eliminates the verdict-injection bug class**: the graph's routing token
   can't be injected into a typed field.

### 12.3 Persistence

Every decision (shadow or enforce) is written to `guardrail_events` (migration `0002`) by
`persist_guard_decisions` (`guards/persistence.py`), which opens its own DB session and
swallows all errors — telemetry must never break a request. Writes happen off the request
path in a Starlette `BackgroundTask` after the response is sent. The table feeds the online
quality/refusal-rate signals in §11.4 for free.

---

## 13. Cost monitoring & caching

Per-session cost is a **first-class quality signal**, captured additively and off the hot
path.

- **Capture.** A `CostCollector` (`cost.py`) piggybacks on the LangGraph `messages` stream
  the request already consumes, reads `usage_metadata` per node, prices it, and writes one
  `cost_events` row per call (node, model, tokens, `cost_usd`, latency, `cache_hit`) in a
  `BackgroundTask` after the response — zero request-path latency. The non-graph `/hint` call
  is metered identically.
- **One pricing table.** `pricing.py` maps node→model and model→rate; the runtime, the budget
  guard (§12), and the offline evals (`evals/metrics.py`) all import it, so a rate change is a
  one-line edit and cost is computed identically everywhere. Runtime never imports `evals`.
- **Theory cache.** `theory_cache` (migration `0004`) keys on `(topic, difficulty,
  prompt_version)`, where `prompt_version` is a SHA-256 of the theory prompt template itself —
  editing the prompt self-invalidates the cache. Only first-attempt theory is cached
  (re-explains stay fresh). A hit replaces an entire streamed **Sonnet** generation (the most
  expensive model) with an instant, zero-token DB read, re-chunked to the same SSE event shape.
  Writes use `on_conflict_do_nothing` (first writer wins); reads/writes fail open. Hit rate is
  a tracked column.
- **Closed loop.** `evals/aggregate_online.py` reports avg + p95 cost/session, cost per node,
  and cache-hit rate; `cost.yml` (scheduled weekly) runs it with `--alert` against a
  per-session USD threshold and fails the run on drift — catching prompt bloat or a re-explain
  loop before the hard in-session budget ceiling ever trips.

---

## 14. Build vs buy

| Component         | Decision                            | Why                                                                     |
| ----------------- | ----------------------------------- | ----------------------------------------------------------------------- |
| LLM inference     | Buy (OpenAI + Anthropic APIs)       | No reason to self-host at this scale                                    |
| Vector store      | Not used in v1                      | RAG isn't needed for the v1 lesson loop                                 |
| Agent framework   | Buy LangGraph                       | Multi-agent supervisor is exactly its use case                          |
| State persistence | Buy LangGraph Postgres checkpointer | Solved problem; runs against Supabase Postgres                          |
| Tracing           | Buy Phoenix (Arize)                 | Free tier; OTel-compatible; good agent UI                               |
| Eval framework    | Build minimal pytest loop           | 50 lines beats adopting a framework prematurely                         |
| Auth              | Buy Supabase                        | Free tier covers it; SSR helper exists for Next                         |
| DB                | Buy Supabase Postgres               | Same provider as Auth; pgvector available if RAG comes later            |
| ORM               | SQLAlchemy 2.x async (Python API)   | Drizzle is JS-only; SQLAlchemy is the Python equivalent, typed + async  |
| Prompts           | Build with Git                      | Prompts in `prompts/*.md`, versioned in repo                            |
| Guardrails        | Build composable + structural       | Domain-specific scope screen + typed verdicts; OpenAI moderation as a backstop (see §12) |
| UI components     | Buy shadcn/ui (compose)             | Standard primitives, customizable                                       |
| Streaming         | Build over SSE                      | Simpler than WebSocket; FastAPI native                                  |
| PDF export        | Buy react-to-print                  | Solved problem                                                          |

---

## 15. Repo layout (as built)

```
depthed/
├── client/                  # Next.js frontend
│   ├── src/
│   │   ├── app/
│   │   ├── components/
│   │   │   └── logo.tsx
│   │   └── lib/
│   └── package.json
├── server/                  # FastAPI backend
│   ├── agents/
│   │   ├── curriculum.py  theory.py  problem.py  feedback.py  memory.py
│   │   ├── guard.py         # topic-scope classifier node (§12.2)
│   │   └── llms.py          # model routing
│   ├── guards/              # composable guardrails (§12)
│   │   ├── base.py  registry.py  patterns.py
│   │   ├── input.py  output.py  verdict.py  budget.py
│   │   └── persistence.py
│   ├── cost.py  pricing.py  # cost collector + single pricing table (§13)
│   ├── online_eval.py       # sampled reference-free judge (§11.4)
│   ├── graph.py
│   ├── routers/             # session, user, me, health
│   ├── prompts/             # *.md files (theory, feedback, guard, …)
│   ├── evals/
│   │   ├── dataset.jsonl  adversarial.jsonl
│   │   ├── run.py  scorers.py  anchors.py  metrics.py  adversarial.py
│   │   └── aggregate_quality.py  aggregate_online.py
│   ├── migrations/          # 0001_init … 0005_online_eval
│   └── pyproject.toml
├── docs/
│   ├── architecture.md      # this file
│   ├── interview-guide.md   # implementation deep-dive + Q&A
│   └── adversarial-findings.md
├── README.md
└── .github/
    └── workflows/
        └── evals.yml  quality.yml  cost.yml  keepalive.yml
```

---

## 16. Definition of done (v1)

For interview-readiness as a portfolio piece — not feature-complete, not pretty, **shipped**:

- [ ] Deployed (web on Vercel, api on Fly.io / Railway).
- [ ] One end-to-end flow works: user picks a topic, gets a Theory section, answers comprehension check, gets a Problem, submits solution, gets Feedback. All five sections render on the lesson page with proper status badges.
- [ ] Auth works (Supabase email/password is enough; OAuth can wait).
- [ ] At least one previous session viewable from history.
- [ ] PDF export of a completed session works.
- [ ] Phoenix tracing wired up; traces visible.
- [ ] Eval dataset has at least 10 examples; eval script runs and produces a score.
- [ ] README explains what it is, the architecture, the build vs buy choices, how to run it locally, and the deployed URL.

Anything beyond this is v2.

---

## 17. Resolved decisions

These were open questions during design; defaults below are the design of record for v1.

1. **Checkpointer:** `langgraph-checkpoint-postgres` against the same Supabase Postgres — no extra infra, proper per-user isolation.
2. **Routing:** Next App Router. TanStack Router was overkill for this app and adds complexity.
3. **Repo structure:** `client/` + `server/` at the repo root. No npm workspaces — each side is independent. Promote to a workspace if shared TS types or tooling become useful.
4. **Model fallbacks:** skip `with_fallbacks` for v1; add when needed.
5. **PDF export:** client-side `react-to-print` for v1; revisit if styling diverges.
