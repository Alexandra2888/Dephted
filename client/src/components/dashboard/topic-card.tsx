import Link from "next/link"
import { cn } from "@/lib/utils"
import { StatusBadge } from "@/components/shared/status-badge"
import type { TopicCard as TopicCardType } from "@/lib/types"

interface TopicCardProps {
  topic: TopicCardType
  suggested?: boolean
  reason?: string
}

const dateFormatter = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
})

export function TopicCard({ topic, suggested, reason }: TopicCardProps) {
  const date = dateFormatter.format(new Date(topic.last_seen_at))

  return (
    <Link
      href={`/lesson/${topic.session_id}`}
      className={cn(
        "group relative block rounded-[10px] border bg-card overflow-hidden",
        "px-5 py-[18px] transition-all duration-150",
        "hover:-translate-y-px",
        suggested
          ? "border-primary/25 shadow-[0_0_0_1px_hsl(var(--primary)/0.15),0_4px_24px_hsl(var(--primary)/0.08)]"
          : "border-border hover:shadow-[0_4px_16px_rgba(0,0,0,0.3)]",
      )}
    >
      {suggested && (
        <span
          aria-hidden
          className="absolute top-0 left-0 right-0 h-[2px] shimmer-strip"
        />
      )}

      <div className="flex items-start justify-between gap-2 mb-2.5">
        <StatusBadge status={suggested ? "suggested" : topic.status} />
        {suggested ? (
          <span className="font-mono text-[10px] tracking-[0.06em] text-primary-light">
            NEXT UP
          </span>
        ) : topic.hint_count > 0 ? (
          <span className="font-mono text-[10px] text-subtle-foreground">
            {topic.hint_count} hint{topic.hint_count > 1 ? "s" : ""}
          </span>
        ) : null}
      </div>

      <div className="font-sans text-[15px] font-medium leading-[1.3] text-foreground mb-1.5">
        {topic.topic}
      </div>

      {suggested ? (
        <div className="font-mono text-[11px] text-subtle-foreground">
          {reason ?? "next recommended lesson"}
        </div>
      ) : (
        <div className="font-mono text-[11px] text-subtle-foreground">
          {date}
        </div>
      )}
    </Link>
  )
}
