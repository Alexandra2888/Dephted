"use client"

import Link from "next/link"
import { useState } from "react"
import { StepTheory } from "./step-theory"
import { StepCheck } from "./step-check"
import { StepProblem } from "./step-problem"
import { StepFeedback } from "./step-feedback"
import { LessonComplete } from "./lesson-complete"
import { NumberedSection } from "@/components/shared/numbered-section"
import { StatusBadge } from "@/components/shared/status-badge"
import { Button } from "@/components/ui/button"
import type { LessonData, LessonStep } from "@/lib/types"

interface LessonPageProps {
  sessionId: string
  initialData: LessonData | null
}

const dateFormatter = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
})

export function LessonPage({ sessionId, initialData }: LessonPageProps) {
  const [steps, setSteps] = useState<LessonStep[]>(initialData?.steps ?? [])
  const session = initialData?.session
  const memory = initialData?.memory

  const isComplete = session?.status === "completed"
  const topicStatus = memory?.status ?? "suggested"
  const date = session?.created_at
    ? dateFormatter.format(new Date(session.created_at))
    : null
  const hintCount = memory?.hint_count ?? 0

  const stepDone = (i: number) => steps.length > i
  const stepUnlocked = (i: number) => steps.length >= i

  return (
    <div className="max-w-2xl mx-auto">
      <div className="flex items-center justify-between mb-10">
        <Link
          href="/dashboard"
          className="flex items-center gap-1.5 font-mono text-xs text-subtle-foreground hover:text-muted-foreground transition-colors"
        >
          <span aria-hidden>←</span>
          <span>dashboard</span>
        </Link>
        <div className="flex items-center gap-3">
          <StatusBadge status={topicStatus} />
          {isComplete && (
            <Button
              variant="violet"
              size="sm"
              onClick={() => window.print()}
              className="h-8 px-3 text-[11px]"
            >
              ↓ export pdf
            </Button>
          )}
        </div>
      </div>

      <div className="mb-12">
        <div className="font-mono text-[11px] uppercase tracking-[0.1em] text-subtle-foreground mb-2.5">
          {date ?? "now"}
          {hintCount > 0 && (
            <>
              {" · "}
              {hintCount} hint{hintCount > 1 ? "s" : ""}
            </>
          )}
        </div>
        <h1 className="font-sans text-[28px] font-semibold leading-[1.2] text-foreground">
          {session?.topic ?? "loading..."}
        </h1>
      </div>

      <NumberedSection num="01" label="theory">
        <StepTheory
          step={steps[0] ?? null}
          sessionId={sessionId}
          onComplete={(step) => setSteps([step])}
        />
      </NumberedSection>

      {stepUnlocked(1) && (
        <NumberedSection num="02" label="comprehension check">
          <StepCheck
            step={steps[1] ?? null}
            sessionId={sessionId}
            onComplete={(step) => setSteps((prev) => [...prev.slice(0, 1), step])}
          />
        </NumberedSection>
      )}

      {stepUnlocked(2) && stepDone(1) && (
        <NumberedSection num="03" label="coding problem">
          <StepProblem
            step={steps[2] ?? null}
            sessionId={sessionId}
            onComplete={(step) => setSteps((prev) => [...prev.slice(0, 2), step])}
          />
        </NumberedSection>
      )}

      {stepUnlocked(3) && stepDone(2) && (
        <NumberedSection num="04" label="feedback">
          <StepFeedback step={steps[3] ?? null} />
        </NumberedSection>
      )}

      {isComplete && <LessonComplete />}
    </div>
  )
}
