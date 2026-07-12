"use client"

import { useState } from "react"
import { Prose } from "@/components/shared/prose"
import { StreamingCursor } from "@/components/shared/streaming-cursor"
import { sessionsApi } from "@/lib/api/sessions"
import { cn } from "@/lib/utils"

interface StepFeedbackProps {
  sessionId: string
  content: string
  gaps: string[]
  streaming: boolean
}

export function StepFeedback({ sessionId, content, streaming }: StepFeedbackProps) {
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
      {streaming ? <StreamingCursor /> : <FeedbackVote sessionId={sessionId} />}
    </div>
  )
}

/**
 * Thumbs on the feedback section — the human signal for Phase 4 online eval. Optimistic and
 * fire-and-forget (a lost vote is not worth interrupting the learner); re-voting overwrites
 * server-side. Hidden from print.
 */
function FeedbackVote({ sessionId }: { sessionId: string }) {
  const [rating, setRating] = useState<"up" | "down" | null>(null)

  const vote = (next: "up" | "down") => {
    setRating(next)
    sessionsApi.feedback(sessionId, next).catch(() => {})
  }

  return (
    <div className="mt-6 flex items-center gap-3 print:hidden">
      <span className="font-mono text-[11px] text-subtle-foreground">was this helpful?</span>
      <div className="flex items-center gap-1.5">
        <VoteButton
          label="helpful"
          active={rating === "up"}
          onClick={() => vote("up")}
        >
          ↑
        </VoteButton>
        <VoteButton
          label="not helpful"
          active={rating === "down"}
          onClick={() => vote("down")}
        >
          ↓
        </VoteButton>
      </div>
      {rating && (
        <span className="font-mono text-[11px] text-subtle-foreground">thanks</span>
      )}
    </div>
  )
}

function VoteButton({
  label,
  active,
  onClick,
  children,
}: {
  label: string
  active: boolean
  onClick: () => void
  children: React.ReactNode
}) {
  return (
    <button
      type="button"
      aria-label={label}
      aria-pressed={active}
      onClick={onClick}
      className={cn(
        "flex h-7 w-7 items-center justify-center rounded-md border font-mono text-xs transition-colors",
        active
          ? "border-primary/40 bg-primary/10 text-primary-light"
          : "border-border text-subtle-foreground hover:text-muted-foreground hover:border-muted-foreground/40",
      )}
    >
      {children}
    </button>
  )
}
