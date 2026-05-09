import type { LessonStep } from "@/lib/types"

interface StepFeedbackProps {
  step: LessonStep | null
}

export function StepFeedback({ step }: StepFeedbackProps) {
  if (!step) return null

  const hasGaps = step.gaps && step.gaps.length > 0

  if (hasGaps) {
    return (
      <div className="flex flex-col gap-3">
        <p className="font-sans text-[15px] leading-[1.75] text-muted-foreground">
          {step.content}
        </p>
        <div className="flex flex-col gap-2.5 pt-1">
          <span className="font-mono text-[10px] tracking-[0.06em] text-subtle-foreground">
            GAPS IDENTIFIED
          </span>
          {step.gaps!.map((gap, i) => (
            <div
              key={i}
              className="font-sans text-sm leading-[1.65] text-foreground px-4 py-3 rounded-md bg-destructive/[0.06] border-l-2 border-destructive/40"
            >
              {gap}
            </div>
          ))}
        </div>
      </div>
    )
  }

  return (
    <p className="font-sans text-[15px] leading-[1.75] text-muted-foreground">
      {step.content || "no gaps — topic marked as covered."}
    </p>
  )
}
