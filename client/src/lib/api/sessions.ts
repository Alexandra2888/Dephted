import { apiGet, apiPost, apiStream } from "./client"
import type { LessonData, DashboardData } from "@/lib/types"

export const sessionsApi = {
  start: (topic: string) =>
    apiPost<{ session_id: string }>("/session/start", { topic }),

  answer: (session_id: string, answer: string) =>
    apiPost<{ next_step: string; verdict?: "passed" | "failed" }>(
      "/session/answer",
      { session_id, answer }
    ),

  hint: (session_id: string) =>
    apiPost<{ hint: string }>("/session/hint", { session_id }),

  end: (session_id: string) =>
    apiPost<void>("/session/end", { session_id }),

  get: (session_id: string) =>
    apiGet<LessonData>(`/session/${session_id}`),

  streamAnswer: (
    session_id: string,
    answer: string,
    onChunk: (chunk: string) => void,
    onDone: () => void
  ) => apiStream("/session/answer", { session_id, answer }, onChunk, onDone),
}

export const userApi = {
  memory: () => apiGet<DashboardData>("/user/memory"),
  sessions: (page = 1) => apiGet<LessonData[]>(`/user/sessions?page=${page}`),
}
