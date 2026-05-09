import { cn } from "@/lib/utils"

interface NumberedSectionProps {
  num: string
  label: string
  children: React.ReactNode
  className?: string
}

export function NumberedSection({
  num,
  label,
  children,
  className,
}: NumberedSectionProps) {
  return (
    <section className={cn("mb-11 fade-up", className)}>
      <div className="flex items-center gap-3 mb-4">
        <span className="font-mono text-[10px] uppercase tracking-[0.1em] text-subtle-foreground whitespace-nowrap">
          {num} — {label}
        </span>
        <div className="flex-1 h-px bg-border" />
      </div>
      {children}
    </section>
  )
}
