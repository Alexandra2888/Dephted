import { apiGet, apiPost, streamSSE } from "./client"
import type { DashboardData, LessonData, SSEEvent } from "@/lib/types"

export const sessionsApi = {
  start: (topic: string) =>
    apiPost<{ session_id: string }>("/session/start", { topic }),

  /**
   * Drive the agent graph over SSE. `input` is null to generate the first theory
   * section, otherwise the learner's comprehension answer or problem solution.
   */
  stream: (
    session_id: string,
    input: string | null,
    onEvent: (event: SSEEvent) => void,
  ) => streamSSE("/session/stream", { session_id, input }, onEvent),

  hint: (session_id: string) =>
    apiPost<{ hint: string }>("/session/hint", { session_id }),

  end: (session_id: string) =>
    apiPost<void>("/session/end", { session_id }),

  get: (session_id: string) => apiGet<LessonData>(`/session/${session_id}`),
}

export const userApi = {
  memory: () => apiGet<DashboardData>("/user/memory"),
  sessions: (page = 1) => apiGet<LessonData[]>(`/user/sessions?page=${page}`),
}
