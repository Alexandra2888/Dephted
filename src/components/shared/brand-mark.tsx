import { cn } from "@/lib/utils"

interface BrandMarkProps {
  className?: string
}

export function BrandMark({ className }: BrandMarkProps) {
  return (
    <span
      className={cn(
        "font-mono text-[11px] uppercase tracking-[0.1em] text-subtle-foreground select-none",
        className,
      )}
    >
      depthed_
    </span>
  )
}
