import { NewSessionInput } from "@/components/dashboard/new-session-input"
import { DashboardGrid } from "@/components/dashboard/dashboard-grid"
import { BrandMark } from "@/components/shared/brand-mark"
import { serverApi } from "@/lib/api/server"
import type { DashboardData } from "@/lib/types"

export const dynamic = "force-dynamic"

export default async function DashboardPage() {
  let data: DashboardData = { suggested_next: null, topics: [] }
  try {
    data = await serverApi.dashboard()
  } catch {
    // backend unreachable — render the empty state and let the user start a session
  }

  const covered = data.topics.filter((t) => t.status === "covered").length
  const struggling = data.topics.filter((t) => t.status === "struggling").length

  return (
    <div className="flex flex-col gap-12">
      <header className="flex flex-col gap-3">
        <BrandMark />
        <h1 className="font-sans text-[32px] font-semibold tracking-tight text-foreground leading-tight">
          your lessons
        </h1>
        <p className="font-sans text-sm text-subtle-foreground">
          {covered} covered · {struggling} struggling
        </p>
      </header>

      <NewSessionInput />

      <DashboardGrid initialData={data} fetchedAt={Date.now()} />
    </div>
  )
}
