"use client"

import { StreamingCursor } from "@/components/shared/streaming-cursor"

interface StepTheoryProps {
  content: string
  streaming: boolean
}

export function StepTheory({ content, streaming }: StepTheoryProps) {
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
        <p key={i} className={i > 0 ? "mt-3 whitespace-pre-wrap" : "whitespace-pre-wrap"}>
          {para}
          {streaming && i === paragraphs.length - 1 && <StreamingCursor />}
        </p>
      ))}
    </div>
  )
}
