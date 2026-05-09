"use client"

import { useState } from "react"
import { sessionsApi } from "@/lib/api/sessions"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { cn } from "@/lib/utils"
import type { LessonStep } from "@/lib/types"

interface StepCheckProps {
  step: LessonStep | null
  sessionId: string
  onComplete: (step: LessonStep) => void
}

export function StepCheck({ step, sessionId, onComplete }: StepCheckProps) {
  const [answer, setAnswer] = useState(step?.user_answer ?? "")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const submitted = !!step?.user_answer

  async function handleSubmit() {
    if (!answer.trim()) return
    setLoading(true)
    setError(null)
    try {
      const res = await sessionsApi.answer(sessionId, answer.trim())
      onComplete({
        type: "check",
        content: step?.content ?? "",
        user_answer: answer.trim(),
        verdict: res.verdict,
      })
    } catch {
      setError("something went wrong, try again")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-col gap-5">
      {step?.content && (
        <p className="font-sans text-[15px] leading-[1.75] text-muted-foreground">
          {step.content}
        </p>
      )}

      {!submitted ? (
        <div className="flex flex-col gap-2.5">
          <Textarea
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
            placeholder="type your answer..."
            disabled={loading}
            className="min-h-[100px] bg-card-elevated border-border focus-visible:border-primary/40 focus-visible:ring-0 px-3.5 py-3 text-sm font-sans leading-[1.6] resize-y"
          />
          {error && (
            <p className="font-mono text-[11px] text-destructive">{error}</p>
          )}
          <Button
            variant="violet"
            onClick={handleSubmit}
            disabled={loading || !answer.trim()}
            className="self-end h-9 px-4 text-xs"
          >
            {loading ? "checking…" : "submit →"}
          </Button>
        </div>
      ) : (
        <div className="rounded-lg bg-card-elevated border border-border px-4 py-3.5">
          <div className="font-mono text-[10px] tracking-[0.06em] text-subtle-foreground mb-2">
            YOUR ANSWER
          </div>
          <p className="font-sans text-sm leading-[1.65] text-muted-foreground">
            {step?.user_answer}
          </p>
          {step?.verdict && (
            <div
              className={cn(
                "mt-3 pt-3 border-t border-border font-mono text-[11px]",
                step.verdict === "passed" ? "text-success" : "text-destructive",
              )}
            >
              {step.verdict === "passed" ? "✓ correct" : "✗ incorrect"}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
