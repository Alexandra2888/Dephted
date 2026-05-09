"use client"

import { useState } from "react"
import { sessionsApi } from "@/lib/api/sessions"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { CodeBlock } from "@/components/shared/code-block"
import type { LessonStep } from "@/lib/types"

interface StepProblemProps {
  step: LessonStep | null
  sessionId: string
  onComplete: (step: LessonStep) => void
}

export function StepProblem({ step, sessionId, onComplete }: StepProblemProps) {
  const [code, setCode] = useState(step?.code ?? "")
  const [loading, setLoading] = useState(false)
  const [hinting, setHinting] = useState(false)
  const [hint, setHint] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const submitted = !!step?.code && step.gaps !== undefined

  async function handleSubmit() {
    if (!code.trim()) return
    setLoading(true)
    setError(null)
    try {
      await sessionsApi.answer(sessionId, code.trim())
      onComplete({
        type: "problem",
        content: step?.content ?? "",
        code: code.trim(),
        gaps: [],
      })
    } catch {
      setError("something went wrong, try again")
    } finally {
      setLoading(false)
    }
  }

  async function handleHint() {
    setHinting(true)
    try {
      const res = await sessionsApi.hint(sessionId)
      setHint(res.hint)
    } catch {
      // silent
    } finally {
      setHinting(false)
    }
  }

  return (
    <div className="flex flex-col gap-5">
      {step?.content && <CodeBlock code={step.content} language="python" />}

      {hint && (
        <div className="font-mono text-[11px] text-muted-foreground px-3.5 py-2.5 rounded-md bg-muted/50 border border-border">
          <span className="text-primary-light mr-1.5">hint:</span>
          {hint}
        </div>
      )}

      {submitted ? (
        <div className="flex flex-col gap-2">
          <div className="font-mono text-[11px] tracking-[0.06em] text-subtle-foreground">
            YOUR SOLUTION
          </div>
          <CodeBlock code={step!.code!} language="python" />
        </div>
      ) : (
        <div className="flex flex-col gap-2.5">
          <Textarea
            value={code}
            onChange={(e) => setCode(e.target.value)}
            placeholder="def your_solution(...):"
            spellCheck={false}
            disabled={loading}
            rows={10}
            className="bg-card-elevated border-border focus-visible:border-primary/40 focus-visible:ring-0 px-3.5 py-3 text-[13px] font-mono leading-[1.7] resize-y"
          />
          {error && (
            <p className="font-mono text-[11px] text-destructive">{error}</p>
          )}
          <div className="flex items-center justify-between">
            <button
              type="button"
              onClick={handleHint}
              disabled={hinting}
              className="font-mono text-[11px] text-subtle-foreground hover:text-muted-foreground transition-colors disabled:opacity-40"
            >
              {hinting ? "fetching hint…" : "get hint →"}
            </button>
            <Button
              variant="violet"
              onClick={handleSubmit}
              disabled={loading || !code.trim()}
              className="h-9 px-4 text-xs"
            >
              {loading ? "submitting…" : "submit →"}
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
