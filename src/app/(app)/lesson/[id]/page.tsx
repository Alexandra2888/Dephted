import { LessonPage } from "@/components/lesson/lesson-page"
import { MOCK_LESSONS } from "@/lib/mock/lesson-detail"
import type { LessonData } from "@/lib/types"

async function getLessonData(id: string): Promise<LessonData | null> {
  return MOCK_LESSONS[id] ?? null
}

export default async function LessonRoute({
  params,
}: {
  params: Promise<{ id: string }>
}) {
  const { id } = await params
  const data = await getLessonData(id)

  return <LessonPage sessionId={id} initialData={data} />
}
