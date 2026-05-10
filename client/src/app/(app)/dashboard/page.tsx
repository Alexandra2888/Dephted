import { Suspense } from "react"
import { TopicGrid } from "@/components/dashboard/topic-grid"
import { NewSessionInput } from "@/components/dashboard/new-session-input"
import { Skeleton } from "@/components/ui/skeleton"
import { BrandMark } from "@/components/shared/brand-mark"
import { MOCK_DASHBOARD } from "@/lib/mock/lessons"

export default function DashboardPage() {
  // mock-derived counts; replaced when topic-grid switches to API data
  const covered = MOCK_DASHBOARD.topics.filter((t) => t.status === "covered").length
  const struggling = MOCK_DASHBOARD.topics.filter((t) => t.status === "struggling").length

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

      <Suspense fallback={<TopicGridSkeleton />}>
        <TopicGrid />
      </Suspense>
    </div>
  )
}

function TopicGridSkeleton() {
  return (
    <div className="flex flex-col gap-8">
      <Skeleton className="h-24 rounded-[10px]" />
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-[110px] rounded-[10px]" />
        ))}
      </div>
    </div>
  )
}
