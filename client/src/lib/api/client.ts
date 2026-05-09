import { createClient } from "@/lib/supabase/client"

const API_URL = process.env.NEXT_PUBLIC_API_URL!

async function getAuthHeaders(): Promise<HeadersInit> {
  const supabase = createClient()
  const { data: { session } } = await supabase.auth.getSession()

  if (!session) throw new Error("No active session")

  return {
    "Content-Type": "application/json",
    Authorization: `Bearer ${session.access_token}`,
  }
}

export async function apiPost<T>(path: string, body?: unknown): Promise<T> {
  const headers = await getAuthHeaders()
  const res = await fetch(`${API_URL}${path}`, {
    method: "POST",
    headers,
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) throw new Error(`POST ${path} failed: ${res.status}`)
  return res.json()
}

export async function apiGet<T>(path: string): Promise<T> {
  const headers = await getAuthHeaders()
  const res = await fetch(`${API_URL}${path}`, { headers })
  if (!res.ok) throw new Error(`GET ${path} failed: ${res.status}`)
  return res.json()
}

export function apiStream(
  path: string,
  body: unknown,
  onChunk: (chunk: string) => void,
  onDone: () => void
): Promise<void> {
  return getAuthHeaders().then((headers) =>
    fetch(`${API_URL}${path}`, {
      method: "POST",
      headers,
      body: JSON.stringify(body),
    }).then(async (res) => {
      if (!res.ok || !res.body) throw new Error(`Stream ${path} failed`)
      const reader = res.body.getReader()
      const decoder = new TextDecoder()

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        const text = decoder.decode(value, { stream: true })
        text.split("\n")
          .filter((line) => line.startsWith("data: "))
          .forEach((line) => onChunk(line.slice(6)))
      }
      onDone()
    })
  )
}
