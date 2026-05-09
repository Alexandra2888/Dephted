import { cn } from "@/lib/utils"

interface StreamingCursorProps {
  visible?: boolean
  className?: string
}

export function StreamingCursor({ visible = true, className }: StreamingCursorProps) {
  if (!visible) return null
  return (
    <span
      aria-hidden
      className={cn(
        "inline-block align-middle ml-0.5 w-[2px] h-[1em] bg-primary-light rounded-[1px] cursor-blink",
        className,
      )}
    />
  )
}
