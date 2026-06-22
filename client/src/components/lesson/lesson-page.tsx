"use client"

import Link from "next/link"
import { StepTheory } from "./step-theory"
import { StepCheck } from "./step-check"
import { StepProblem } from "./step-problem"
import { StepFeedback } from "./step-feedback"
import { LessonComplete } from "./lesson-complete"
import { NumberedSection } from "@/components/shared/numbered-section"
import { StatusBadge } from "@/components/shared/status-badge"
import { Button } from "@/components/ui/button"
import { useLesson } from "@/lib/hooks/use-lesson"
import type { LessonData } from "@/lib/types"

interface LessonPageProps {
  sessionId: string
  initialData: LessonData | null
}

const dateFormatter = new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric" })

export function LessonPage({ sessionId, initialData }: LessonPageProps) {
  const { view, phase, error, submitAnswer, submitSolution, getHint } = useLesson(
    sessionId,
    initialData,
  )

  const session = initialData?.session
  const memory = initialData?.memory
  const isComplete = phase === "complete"
  const topicStatus = memory?.status ?? "suggested"
  const date = session?.created_at ? dateFormatter.format(new Date(session.created_at)) : null
  const hintCount = memory?.hint_count ?? 0

  const showTheory = phase !== "idle"
  const showCheck = !!view.checkQuestion
  const showProblem = !!view.problem || view.problemStreaming
  const showFeedback = !!view.feedback || view.feedbackStreaming

  return (
    <div className="max-w-2xl mx-auto">
      <div className="flex items-center justify-between mb-10 print:hidden">
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
          {hintCount > 0 && ` · ${hintCount} hint${hintCount > 1 ? "s" : ""}`}
        </div>
        <h1 className="font-sans text-[28px] font-semibold leading-[1.2] text-foreground">
          {session?.topic ?? "loading..."}
        </h1>
      </div>

      {error && (
        <p className="mb-8 font-mono text-xs text-destructive">error: {error}</p>
      )}

      {showTheory && (
        <NumberedSection num="01" label="theory">
          <StepTheory content={view.theory} streaming={view.theoryStreaming} />
        </NumberedSection>
      )}

      {showCheck && (
        <NumberedSection num="02" label="comprehension check">
          <StepCheck
            question={view.checkQuestion}
            answer={view.checkAnswer}
            verdict={view.checkVerdict}
            canSubmit={phase === "awaiting_check"}
            busy={phase === "streaming"}
            onSubmit={submitAnswer}
          />
        </NumberedSection>
      )}

      {showProblem && (
        <NumberedSection num="03" label="coding problem">
          <StepProblem
            problem={view.problem}
            streaming={view.problemStreaming}
            solution={view.solution}
            canSubmit={phase === "awaiting_solution"}
            busy={phase === "streaming"}
            onSubmit={submitSolution}
            onHint={getHint}
          />
        </NumberedSection>
      )}

      {showFeedback && (
        <NumberedSection num="04" label="feedback">
          <StepFeedback
            content={view.feedback}
            gaps={view.feedbackGaps}
            streaming={view.feedbackStreaming}
          />
        </NumberedSection>
      )}

      {isComplete && <LessonComplete />}
    </div>
  )
}
