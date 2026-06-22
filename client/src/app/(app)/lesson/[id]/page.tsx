import { LessonPage } from "@/components/lesson/lesson-page"
import { serverApi } from "@/lib/api/server"
import type { LessonData } from "@/lib/types"

export const dynamic = "force-dynamic"

export default async function LessonRoute({
  params,
}: {
  params: Promise<{ id: string }>
}) {
  const { id } = await params
  let data: LessonData | null = null
  try {
    data = await serverApi.lesson(id)
  } catch {
    data = null
  }

  return <LessonPage sessionId={id} initialData={data} />
}
