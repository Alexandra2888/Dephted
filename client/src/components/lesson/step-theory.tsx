"use client"

import { useEffect, useState } from "react"
import { sessionsApi } from "@/lib/api/sessions"
import { StreamingCursor } from "@/components/shared/streaming-cursor"
import type { LessonStep } from "@/lib/types"

interface StepTheoryProps {
  step: LessonStep | null
  sessionId: string
  onComplete: (step: LessonStep) => void
}

export function StepTheory({ step, sessionId, onComplete }: StepTheoryProps) {
  const [streaming, setStreaming] = useState(false)
  const [content, setContent] = useState(step?.content ?? "")

  useEffect(() => {
    if (step || streaming) return
    // eslint-disable-next-line react-hooks/set-state-in-effect -- intentional one-shot guard; refactor when wiring real BE stream
    setStreaming(true)
    let buffer = ""

    sessionsApi.streamAnswer(
      sessionId,
      "__init__",
      (chunk) => {
        buffer += chunk
        setContent(buffer)
      },
      () => {
        setStreaming(false)
        onComplete({ type: "theory", content: buffer })
      },
    )
    // eslint-disable-next-line react-hooks/exhaustive-deps -- run once on mount; props are stable for the session
  }, [])

  if (!content && streaming) {
    return (
      <div className="flex items-center gap-2 font-mono text-[11px] text-subtle-foreground">
        <span>generating</span>
        <StreamingCursor />
      </div>
    )
  }

  const paragraphs = content.split("\n\n")

  return (
    <div className="font-sans text-[15px] leading-[1.75] text-muted-foreground">
      {paragraphs.map((para, i) => (
        <p key={i} className={i > 0 ? "mt-3" : undefined}>
          {para}
          {streaming && i === paragraphs.length - 1 && (
            <StreamingCursor />
          )}
        </p>
      ))}
    </div>
  )
}
