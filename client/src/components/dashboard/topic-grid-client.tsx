"use client"

import { useState } from "react"
import { TopicCard } from "./topic-card"
import { Filters, type FilterValue } from "./filters"
import type { TopicCard as TopicCardType } from "@/lib/types"

interface TopicGridClientProps {
  suggested: TopicCardType | null
  topics: TopicCardType[]
  suggestedReason?: string
}

export function TopicGridClient({
  suggested,
  topics,
  suggestedReason,
}: TopicGridClientProps) {
  const [filter, setFilter] = useState<FilterValue>("all")

  const filtered =
    filter === "all" ? topics : topics.filter((t) => t.status === filter)

  if (!suggested && topics.length === 0) {
    return (
      <p className="font-mono text-sm text-subtle-foreground py-16 text-center">
        no sessions yet — enter a topic above to start_
      </p>
    )
  }

  return (
    <div className="flex flex-col gap-8">
      {suggested && (
        <TopicCard topic={suggested} suggested reason={suggestedReason} />
      )}

      <div className="flex flex-col gap-5">
        <Filters value={filter} onChange={setFilter} />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {filtered.map((t) => (
            <TopicCard key={t.session_id} topic={t} />
          ))}
        </div>
      </div>
    </div>
  )
}
