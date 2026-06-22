"use client"

import { Prose } from "@/components/shared/prose"
import { StreamingCursor } from "@/components/shared/streaming-cursor"

interface StepFeedbackProps {
  content: string
  gaps: string[]
  streaming: boolean
}

export function StepFeedback({ content, streaming }: StepFeedbackProps) {
  if (!content && !streaming) return null

  if (!content && streaming) {
    return (
      <div className="flex items-center gap-2 font-mono text-[11px] text-subtle-foreground">
        <span>reviewing</span>
        <StreamingCursor />
      </div>
    )
  }

  return (
    <div>
      <Prose text={content} />
      {streaming && <StreamingCursor />}
    </div>
  )
}
