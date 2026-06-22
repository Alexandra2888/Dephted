"use client"

import { useCallback, useEffect, useRef, useState } from "react"
import { sessionsApi } from "@/lib/api/sessions"
import type { LessonData, LessonStep, SSEEvent } from "@/lib/types"

export type LessonPhase =
  | "idle"
  | "streaming"
  | "awaiting_check"
  | "awaiting_solution"
  | "complete"
  | "error"

export interface LessonView {
  theory: string
  theoryStreaming: boolean
  checkQuestion: string
  checkAnswer: string
  checkVerdict: "passed" | "failed" | null
  problem: string
  problemStreaming: boolean
  solution: string
  feedback: string
  feedbackStreaming: boolean
  feedbackGaps: string[]
  feedbackVerdict: "passed" | "failed" | null
}

const EMPTY: LessonView = {
  theory: "",
  theoryStreaming: false,
  checkQuestion: "",
  checkAnswer: "",
  checkVerdict: null,
  problem: "",
  problemStreaming: false,
  solution: "",
  feedback: "",
  feedbackStreaming: false,
  feedbackGaps: [],
  feedbackVerdict: null,
}

const CHECK_RE = /\*\*check:\*\*\s*/i

function splitCheck(text: string): [string, string] {
  const m = CHECK_RE.exec(text)
  if (!m) return [text, ""]
  return [text.slice(0, m.index).trim(), text.slice(m.index + m[0].length).trim()]
}

function parseGaps(text: string): string[] {
  return text
    .split("\n")
    .map((l) => l.trim())
    .filter((l) => /^[-*]\s+/.test(l))
    .map((l) => l.replace(/^[-*]\s+/, "").trim())
    .filter(Boolean)
}

function hydrate(steps: LessonStep[]): LessonView {
  const by = new Map(steps.map((s) => [s.type, s]))
  const feedback = by.get("feedback")
  return {
    ...EMPTY,
    theory: by.get("theory")?.content ?? "",
    checkQuestion: by.get("check")?.content ?? "",
    checkAnswer: by.get("check")?.user_answer ?? "",
    checkVerdict: by.get("check")?.verdict ?? null,
    problem: by.get("problem")?.content ?? "",
    solution: by.get("problem")?.code ?? "",
    feedback: feedback?.content ?? "",
    feedbackGaps: feedback?.gaps ?? [],
    feedbackVerdict: feedback?.verdict ?? null,
  }
}

export function useLesson(sessionId: string, initial: LessonData | null) {
  const [view, setView] = useState<LessonView>(() =>
    initial?.steps?.length ? hydrate(initial.steps) : EMPTY,
  )
  const [phase, setPhase] = useState<LessonPhase>("idle")
  const [error, setError] = useState<string | null>(null)
  const buffers = useRef({ theory: "", problem: "", feedback: "" })
  const started = useRef(false)

  const onEvent = useCallback((ev: SSEEvent) => {
    switch (ev.type) {
      case "section_start":
        if (ev.section === "theory") {
          buffers.current.theory = ""
          setView((v) => ({ ...v, theory: "", checkQuestion: "", checkAnswer: "", checkVerdict: null, theoryStreaming: true }))
        } else if (ev.section === "problem") {
          buffers.current.problem = ""
          setView((v) => ({ ...v, problem: "", problemStreaming: true }))
        } else if (ev.section === "feedback") {
          buffers.current.feedback = ""
          setView((v) => ({ ...v, feedback: "", feedbackGaps: [], feedbackStreaming: true }))
        }
        break
      case "token":
        if (ev.section === "theory") {
          buffers.current.theory += ev.data
          const [exp, q] = splitCheck(buffers.current.theory)
          setView((v) => ({ ...v, theory: exp, checkQuestion: q }))
        } else if (ev.section === "problem") {
          buffers.current.problem += ev.data
          setView((v) => ({ ...v, problem: buffers.current.problem }))
        } else if (ev.section === "feedback") {
          buffers.current.feedback += ev.data
          setView((v) => ({ ...v, feedback: buffers.current.feedback }))
        }
        break
      case "section_complete":
        if (ev.section === "theory") {
          setView((v) => ({ ...v, theoryStreaming: false }))
        } else if (ev.section === "check") {
          setView((v) => ({
            ...v,
            checkVerdict: ev.verdict ?? null,
            checkAnswer: ev.data ?? v.checkAnswer,
          }))
        } else if (ev.section === "problem") {
          setView((v) => ({ ...v, problemStreaming: false }))
        } else if (ev.section === "feedback") {
          const gaps = parseGaps(buffers.current.feedback)
          const cleaned = buffers.current.feedback.replace(/\n*\*\*verdict:\*\*[\s\S]*$/i, "").trim()
          setView((v) => ({
            ...v,
            feedback: cleaned,
            feedbackStreaming: false,
            feedbackGaps: gaps,
            feedbackVerdict: ev.verdict ?? null,
          }))
        }
        break
      case "done":
        if (ev.status === "complete") setPhase("complete")
        else if (ev.next === "feedback") setPhase("awaiting_solution")
        else setPhase("awaiting_check")
        break
      case "error":
        setError(ev.data)
        setPhase("error")
        break
    }
  }, [])

  const run = useCallback(
    async (input: string | null) => {
      setError(null)
      setPhase("streaming")
      try {
        await sessionsApi.stream(sessionId, input, onEvent)
      } catch (e) {
        setError(e instanceof Error ? e.message : "stream failed")
        setPhase("error")
      }
    },
    [sessionId, onEvent],
  )

  const submitAnswer = useCallback(
    (text: string) => {
      setView((v) => ({ ...v, checkAnswer: text }))
      return run(text)
    },
    [run],
  )

  const submitSolution = useCallback(
    (text: string) => {
      setView((v) => ({ ...v, solution: text }))
      return run(text)
    },
    [run],
  )

  const getHint = useCallback(async () => {
    const { hint } = await sessionsApi.hint(sessionId)
    return hint
  }, [sessionId])

  // One-shot init: hydrate phase from existing data, or kick off the first stream.
  // Deferred to a microtask so we don't setState synchronously inside the effect body.
  useEffect(() => {
    if (started.current) return
    started.current = true

    queueMicrotask(() => {
      const steps = initial?.steps ?? []
      if (steps.length === 0) {
        void run(null)
        return
      }
      const has = (t: string) => steps.some((s) => s.type === t)
      if (initial?.session?.status === "completed" || has("feedback")) setPhase("complete")
      else if (has("problem")) setPhase("awaiting_solution")
      else setPhase("awaiting_check")
    })
  }, [initial, run])

  return { view, phase, error, submitAnswer, submitSolution, getHint }
}
