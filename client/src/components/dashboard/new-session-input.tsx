"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { sessionsApi } from "@/lib/api/sessions"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"

export function NewSessionInput() {
  const router = useRouter()
  const [topic, setTopic] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function startSession() {
    if (!topic.trim()) return
    setLoading(true)
    setError(null)
    try {
      const { session_id } = await sessionsApi.start(topic.trim())
      router.push(`/lesson/${session_id}`)
    } catch {
      setError("failed to start session")
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="flex gap-2.5">
        <Input
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && startSession()}
          placeholder="enter a backend topic to learn..."
          disabled={loading}
          className="h-11 flex-1 bg-card border-border focus-visible:border-primary/40 focus-visible:ring-0 px-4 text-sm"
        />
        <Button
          variant="violet"
          onClick={startSession}
          disabled={loading || !topic.trim()}
          className="h-11 px-5 text-xs"
        >
          {loading ? "starting…" : "start →"}
        </Button>
      </div>
      {error && (
        <p className="font-mono text-[11px] text-destructive">{error}</p>
      )}
    </div>
  )
}
