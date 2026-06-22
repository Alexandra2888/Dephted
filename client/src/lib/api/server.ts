import "server-only"

import { createClient } from "@/lib/supabase/server"
import type { DashboardData, LessonData } from "@/lib/types"

const API_URL = process.env.NEXT_PUBLIC_API_URL!

async function serverHeaders(): Promise<HeadersInit> {
  const supabase = await createClient()
  const { data: { session } } = await supabase.auth.getSession()
  if (!session) throw new Error("No active session")
  return { Authorization: `Bearer ${session.access_token}` }
}

async function serverGet<T>(path: string): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    headers: await serverHeaders(),
    cache: "no-store",
  })
  if (!res.ok) throw new Error(`GET ${path} failed: ${res.status}`)
  return res.json()
}

/** Server-component data fetchers (use the Supabase SSR session cookie for auth). */
export const serverApi = {
  dashboard: () => serverGet<DashboardData>("/user/memory"),
  lesson: (sessionId: string) => serverGet<LessonData>(`/session/${sessionId}`),
  sessions: (page = 1) => serverGet<LessonData[]>(`/user/sessions?page=${page}`),
}
