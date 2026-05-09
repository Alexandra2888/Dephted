import type { DashboardData, TopicCard } from "@/lib/types"

const day = (n: number) => {
  const d = new Date()
  d.setDate(d.getDate() - n)
  return d.toISOString()
}

export const MOCK_TOPICS: TopicCard[] = [
  {
    session_id: "s-fastapi-di",
    topic: "FastAPI Dependency Injection",
    status: "covered",
    hint_count: 0,
    last_seen_at: day(1),
  },
  {
    session_id: "s-pydantic",
    topic: "Python Type Hints & Pydantic",
    status: "struggling",
    hint_count: 2,
    last_seen_at: day(2),
  },
  {
    session_id: "s-async",
    topic: "Async/Await in Python",
    status: "covered",
    hint_count: 1,
    last_seen_at: day(3),
  },
  {
    session_id: "s-langgraph-state",
    topic: "LangGraph State Machines",
    status: "covered",
    hint_count: 0,
    last_seen_at: day(4),
  },
  {
    session_id: "s-rag",
    topic: "RAG Architecture",
    status: "struggling",
    hint_count: 3,
    last_seen_at: day(5),
  },
  {
    session_id: "s-jwt",
    topic: "JWT Authentication",
    status: "covered",
    hint_count: 0,
    last_seen_at: day(6),
  },
]

export const MOCK_SUGGESTED: TopicCard = {
  session_id: "s-langgraph-checkpointers",
  topic: "LangGraph Checkpointers",
  status: "suggested",
  hint_count: 0,
  last_seen_at: new Date().toISOString(),
}

export const MOCK_SUGGESTED_REASON = "follows from State Machines"

export const MOCK_DASHBOARD: DashboardData = {
  suggested_next: MOCK_SUGGESTED,
  topics: MOCK_TOPICS,
}
