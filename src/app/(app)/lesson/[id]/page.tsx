import { notFound } from "next/navigation"
import { LessonPage } from "@/components/lesson/lesson-page"
import type { LessonData } from "@/lib/types"

// TODO: fetch from API once BE is ready
async function getLessonData(id: string): Promise<LessonData | null> {
  return null
}

export default async function LessonRoute({
  params,
}: {
  params: Promise<{ id: string }>
}) {
  const { id } = await params
  const data = await getLessonData(id)

  if (!data) {
    return (
      <LessonPage
        sessionId={id}
        initialData={null}
      />
    )
  }

  return <LessonPage sessionId={id} initialData={data} />
}
