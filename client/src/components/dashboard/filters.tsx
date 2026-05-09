"use client"

import { cn } from "@/lib/utils"

export type FilterValue = "all" | "covered" | "struggling"

const OPTIONS: FilterValue[] = ["all", "covered", "struggling"]

interface FiltersProps {
  value: FilterValue
  onChange: (v: FilterValue) => void
}

export function Filters({ value, onChange }: FiltersProps) {
  return (
    <div className="flex gap-1.5">
      {OPTIONS.map((opt) => {
        const active = value === opt
        return (
          <button
            key={opt}
            type="button"
            onClick={() => onChange(opt)}
            className={cn(
              "px-3 py-[5px] rounded-full border font-mono text-[11px] uppercase tracking-[0.06em] transition-colors",
              active
                ? "bg-primary/[0.08] border-primary/20 text-primary-light"
                : "bg-transparent border-border text-subtle-foreground hover:text-muted-foreground hover:border-muted-foreground/30",
            )}
          >
            {opt}
          </button>
        )
      })}
    </div>
  )
}
