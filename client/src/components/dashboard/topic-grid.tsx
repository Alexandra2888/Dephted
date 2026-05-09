import { TopicGridClient } from "./topic-grid-client"
import { MOCK_DASHBOARD, MOCK_SUGGESTED_REASON } from "@/lib/mock/lessons"
import type { DashboardData } from "@/lib/types"

// TODO: replace with `await userApi.memory()` once BE is ready
async function getDashboard(): Promise<DashboardData> {
  return MOCK_DASHBOARD
}

export async function TopicGrid() {
  const data = await getDashboard()
  return (
    <TopicGridClient
      suggested={data.suggested_next}
      topics={data.topics}
      suggestedReason={MOCK_SUGGESTED_REASON}
    />
  )
}
