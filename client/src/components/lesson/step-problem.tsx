"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { CodeBlock } from "@/components/shared/code-block"
import { Prose } from "@/components/shared/prose"
import { StreamingCursor } from "@/components/shared/streaming-cursor"

interface StepProblemProps {
  problem: string
  streaming: boolean
  solution: string
  canSubmit: boolean
  busy: boolean
  onSubmit: (code: string) => void
  onHint: () => Promise<string>
}

export function StepProblem({
  problem,
  streaming,
  solution,
  canSubmit,
  busy,
  onSubmit,
  onHint,
}: StepProblemProps) {
  const [code, setCode] = useState("")
  const [hint, setHint] = useState<string | null>(null)
  const [hinting, setHinting] = useState(false)

  async function handleHint() {
    setHinting(true)
    try {
      setHint(await onHint())
    } catch {
      // silent
    } finally {
      setHinting(false)
    }
  }

  return (
    <div className="flex flex-col gap-5">
      <div>
        {problem ? <Prose text={problem} /> : null}
        {streaming && <StreamingCursor />}
      </div>

      {hint && (
        <div className="font-mono text-[11px] text-muted-foreground px-3.5 py-2.5 rounded-md bg-muted/50 border border-border">
          <span className="text-primary-light mr-1.5">hint:</span>
          {hint}
        </div>
      )}

      {canSubmit ? (
        <div className="flex flex-col gap-2.5">
          <Textarea
            value={code}
            onChange={(e) => setCode(e.target.value)}
            placeholder="def your_solution(...):"
            spellCheck={false}
            disabled={busy}
            rows={10}
            className="bg-card-elevated border-border focus-visible:border-primary/40 focus-visible:ring-0 px-3.5 py-3 text-[13px] font-mono leading-[1.7] resize-y"
          />
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
              onClick={() => code.trim() && onSubmit(code.trim())}
              disabled={busy || !code.trim()}
              className="h-9 px-4 text-xs"
            >
              {busy ? "submitting…" : "submit →"}
            </Button>
          </div>
        </div>
      ) : (
        solution && (
          <div className="flex flex-col gap-2">
            <div className="font-mono text-[11px] tracking-[0.06em] text-subtle-foreground">
              YOUR SOLUTION
            </div>
            <CodeBlock code={solution} language="python" />
          </div>
        )
      )}
    </div>
  )
}
