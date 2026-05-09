export type SessionStatus = "active" | "completed"
export type TopicStatus = "covered" | "struggling" | "suggested"
export type AgentType = "curriculum" | "theory" | "problem" | "feedback" | "memory"
export type MessageRole = "user" | "agent" | "system"

export interface Session {
  id: string
  user_id: string
  topic: string
  status: SessionStatus
  created_at: string
  updated_at: string
}

export interface Message {
  id: string
  session_id: string
  role: MessageRole
  content: string
  agent_type: AgentType | null
  created_at: string
}

export interface UserMemory {
  id: string
  user_id: string
  topic: string
  status: TopicStatus
  hint_count: number
  last_seen_at: string
}

export interface LessonStep {
  type: "theory" | "check" | "problem" | "feedback"
  content: string
  user_answer?: string
  verdict?: "passed" | "failed"
  code?: string
  gaps?: string[]
  streaming?: boolean
}

export interface LessonData {
  session: Session
  memory: UserMemory | null
  steps: LessonStep[]
}

export interface TopicCard {
  topic: string
  status: TopicStatus
  hint_count: number
  last_seen_at: string
  session_id: string
}

export interface DashboardData {
  suggested_next: TopicCard | null
  topics: TopicCard[]
}
