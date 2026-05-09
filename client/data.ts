const MOCK_LESSONS = [
  {
    id: 1,
    topic: "FastAPI Dependency Injection",
    date: "Apr 8",
    status: "covered",
    hints: 0,
  },
  {
    id: 2,
    topic: "Python Type Hints & Pydantic",
    date: "Apr 7",
    status: "struggling",
    hints: 2,
  },
  {
    id: 3,
    topic: "Async/Await in Python",
    date: "Apr 6",
    status: "covered",
    hints: 1,
  },
  {
    id: 4,
    topic: "LangGraph State Machines",
    date: "Apr 5",
    status: "covered",
    hints: 0,
  },
  {
    id: 5,
    topic: "RAG Architecture",
    date: "Apr 4",
    status: "struggling",
    hints: 3,
  },
  {
    id: 6,
    topic: "JWT Authentication",
    date: "Apr 3",
    status: "covered",
    hints: 0,
  },
];

const SUGGESTED = {
  id: 7,
  topic: "LangGraph Checkpointers",
  reason: "follows from State Machines",
};

const STATUS = {
  covered: {
    label: "covered",
    dot: "#4ade80",
    text: "#86efac",
    bg: "rgba(74,222,128,0.08)",
  },
  struggling: {
    label: "struggling",
    dot: "#fb923c",
    text: "#fdba74",
    bg: "rgba(251,146,60,0.08)",
  },
  suggested: {
    label: "suggested",
    dot: "#94a3b8",
    text: "#94a3b8",
    bg: "rgba(148,163,184,0.08)",
  },
};
