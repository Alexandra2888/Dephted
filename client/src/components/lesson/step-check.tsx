"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { cn } from "@/lib/utils"

interface StepCheckProps {
  question: string
  answer: string
  verdict: "passed" | "failed" | null
  canSubmit: boolean
  busy: boolean
  onSubmit: (answer: string) => void
}

export function StepCheck({ question, answer, verdict, canSubmit, busy, onSubmit }: StepCheckProps) {
  const [draft, setDraft] = useState("")

  return (
    <div className="flex flex-col gap-5">
      {question && (
        <p className="font-sans text-[15px] leading-[1.75] text-muted-foreground whitespace-pre-wrap">
          {question}
        </p>
      )}

      {canSubmit ? (
        <div className="flex flex-col gap-2.5">
          <Textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="type your answer..."
            disabled={busy}
            className="min-h-[100px] bg-card-elevated border-border focus-visible:border-primary/40 focus-visible:ring-0 px-3.5 py-3 text-sm font-sans leading-[1.6] resize-y"
          />
          <Button
            variant="violet"
            onClick={() => draft.trim() && onSubmit(draft.trim())}
            disabled={busy || !draft.trim()}
            className="self-end h-9 px-4 text-xs"
          >
            {busy ? "checking…" : "submit →"}
          </Button>
        </div>
      ) : (
        answer && (
          <div className="rounded-lg bg-card-elevated border border-border px-4 py-3.5">
            <div className="font-mono text-[10px] tracking-[0.06em] text-subtle-foreground mb-2">
              YOUR ANSWER
            </div>
            <p className="font-sans text-sm leading-[1.65] text-muted-foreground whitespace-pre-wrap">
              {answer}
            </p>
            {verdict && (
              <div
                className={cn(
                  "mt-3 pt-3 border-t border-border font-mono text-[11px]",
                  verdict === "passed" ? "text-success" : "text-destructive",
                )}
              >
                {verdict === "passed" ? "✓ correct" : "✗ not quite — re-explaining"}
              </div>
            )}
          </div>
        )
      )}
    </div>
  )
}
