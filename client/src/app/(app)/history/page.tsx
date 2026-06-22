import Link from "next/link"
import { serverApi } from "@/lib/api/server"
import type { LessonData } from "@/lib/types"

export const dynamic = "force-dynamic"

const fmt = new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric", year: "numeric" })

export default async function HistoryPage() {
  let sessions: LessonData[] = []
  try {
    sessions = await serverApi.sessions()
  } catch {
    sessions = []
  }

  return (
    <div className="flex flex-col gap-8">
      <h1 className="font-sans text-[28px] font-semibold tracking-tight text-foreground">
        history
      </h1>

      {sessions.length === 0 ? (
        <p className="font-mono text-sm text-subtle-foreground py-12 text-center">
          no past sessions yet_
        </p>
      ) : (
        <div className="flex flex-col gap-3">
          {sessions.map(({ session }) => (
            <Link
              key={session.id}
              href={`/lesson/${session.id}`}
              className="block rounded-[10px] border border-border bg-card px-5 py-4 transition-all hover:-translate-y-px hover:shadow-[0_4px_16px_rgba(0,0,0,0.3)]"
            >
              <div className="flex items-center justify-between gap-3">
                <span className="font-sans text-[15px] font-medium text-foreground">
                  {session.topic}
                </span>
                <span className="font-mono text-[10px] uppercase tracking-[0.06em] text-subtle-foreground">
                  {session.status}
                </span>
              </div>
              <div className="font-mono text-[11px] text-subtle-foreground mt-1">
                {fmt.format(new Date(session.created_at))}
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
