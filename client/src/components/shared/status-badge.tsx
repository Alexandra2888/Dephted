import { cn } from "@/lib/utils"
import type { TopicStatus } from "@/lib/types"

const styles: Record<
  TopicStatus,
  { dot: string; text: string; bg: string; ring: string }
> = {
  covered: {
    dot: "bg-success",
    text: "text-success",
    bg: "bg-success/[0.08]",
    ring: "ring-success/20",
  },
  struggling: {
    dot: "bg-warning",
    text: "text-warning",
    bg: "bg-warning/[0.08]",
    ring: "ring-warning/20",
  },
  suggested: {
    dot: "bg-subtle-foreground",
    text: "text-subtle-foreground",
    bg: "bg-subtle-foreground/[0.08]",
    ring: "ring-subtle-foreground/20",
  },
}

const dotShadow: Record<TopicStatus, string> = {
  covered: "shadow-[0_0_6px_hsl(var(--success))]",
  struggling: "shadow-[0_0_6px_hsl(var(--warning))]",
  suggested: "shadow-[0_0_6px_hsl(var(--subtle-foreground))]",
}

interface StatusBadgeProps {
  status: TopicStatus
  className?: string
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const s = styles[status]
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 px-2 py-[3px] rounded-full ring-1",
        s.bg,
        s.ring,
        className,
      )}
    >
      <span
        aria-hidden
        className={cn("w-1.5 h-1.5 rounded-full", s.dot, dotShadow[status])}
      />
      <span
        className={cn(
          "font-mono text-[10px] uppercase tracking-[0.06em]",
          s.text,
        )}
      >
        {status}
      </span>
    </span>
  )
}
