"use client"

import { useQuery } from "@tanstack/react-query"
import { userApi } from "@/lib/api/sessions"
import { TopicGridClient } from "./topic-grid-client"
import type { DashboardData } from "@/lib/types"

export function DashboardGrid({ initialData }: { initialData: DashboardData }) {
  const { data } = useQuery({
    queryKey: ["dashboard"],
    queryFn: userApi.memory,
    initialData,
  })
  return <TopicGridClient suggested={data.suggested_next} topics={data.topics} />
}
