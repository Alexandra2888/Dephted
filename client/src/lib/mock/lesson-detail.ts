import type {
  LessonData,
  LessonStep,
  Session,
  TopicStatus,
  UserMemory,
} from "@/lib/types"

const userId = "u-mock"

const day = (n: number) => {
  const d = new Date()
  d.setDate(d.getDate() - n)
  return d.toISOString()
}

function buildSession(
  id: string,
  topic: string,
  daysAgo: number,
  status: Session["status"] = "completed",
): Session {
  const t = day(daysAgo)
  return {
    id,
    user_id: userId,
    topic,
    status,
    created_at: t,
    updated_at: t,
  }
}

function buildMemory(
  topic: string,
  status: TopicStatus,
  hintCount: number,
  daysAgo: number,
): UserMemory {
  return {
    id: `m-${topic}`,
    user_id: userId,
    topic,
    status,
    hint_count: hintCount,
    last_seen_at: day(daysAgo),
  }
}

const fastApiDiSteps: LessonStep[] = [
  {
    type: "theory",
    content: `FastAPI's dependency injection rests on a single idea: a function declares what it needs as parameters, and FastAPI figures out how to provide them. You don't construct dependencies — you declare them with Depends().

Every endpoint is a function. Its parameters are either request data (path, query, body) or dependencies. At request time FastAPI walks the dependency graph, calls each function in order, and passes the results to your handler.

Coming from Express, the closest analogue is composing req.user, req.db, etc. through middleware before the route runs — except FastAPI types the result, so the handler signature itself documents what's available.`,
  },
  {
    type: "check",
    content:
      "From FastAPI's perspective, what determines whether a parameter is a request input vs a dependency?",
    user_answer:
      "FastAPI inspects every parameter. If it's wrapped with Depends(...), it's resolved via the dependency graph (calling sub-functions, cached per-request). Otherwise FastAPI tries to populate it from the request itself — body, query, path, or headers depending on the type.",
    verdict: "passed",
  },
  {
    type: "problem",
    content: `# Build:
#   get_current_user(token: str) -> dict
#     Decode the JWT. Raise HTTPException(401) on invalid token.
#
#   GET /me
#     Endpoint that depends on get_current_user.
#     Handler signature should declare only current_user, not token.`,
    code: `from fastapi import Depends, FastAPI, HTTPException, status
from jose import JWTError, jwt

app = FastAPI()
SECRET = "..."

def get_current_user(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET, algorithms=["HS256"])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid token",
        )

@app.get("/me")
def me(current_user: dict = Depends(get_current_user)):
    return current_user`,
    gaps: [],
  },
  {
    type: "feedback",
    content:
      "clean implementation. Depends() is wired correctly, the dependency raises HTTPException with a 401, and the endpoint signature exposes only current_user — no token leakage. topic marked as covered.",
    gaps: [],
  },
]

const pydanticSteps: LessonStep[] = [
  {
    type: "theory",
    content: `Pydantic models turn dict-shaped data into typed Python objects with runtime validation. Inherit from BaseModel, declare fields as type annotations, and Pydantic does the rest at instantiation: parsing, coercing where reasonable, and raising ValidationError on bad input.

The thing that trips up Node devs: Pydantic v2 coerces between types where there's an unambiguous standard parse — "42" → 42, "2024-01-01" → datetime — but it won't invent structure. int → list doesn't work; you'll get a ValidationError.

Type hints in Python are just metadata; the runtime ignores them. Pydantic uses them as a schema. That's the bridge between Python's static-type story and runtime data validation.`,
  },
  {
    type: "check",
    content: "Why use Pydantic instead of @dataclass?",
    user_answer: "Pydantic does runtime validation; dataclasses don't.",
    verdict: "passed",
  },
  {
    type: "problem",
    content: `# Define User with:
#   email:  EmailStr
#   age:    int (>= 0)
#   tags:   list[str], default []
#
# Then write parse_user(raw: dict) -> User | None.
# Return None on validation error; do not let it propagate.`,
    code: `from pydantic import BaseModel, EmailStr

class User(BaseModel):
    email: EmailStr
    age: int
    tags: list[str] = []

def parse_user(raw: dict) -> User | None:
    return User(**raw)`,
    gaps: [
      "missing the age >= 0 constraint — use Field(..., ge=0) or PositiveInt-style validation. As written, age=-5 is accepted.",
      "parse_user does not catch pydantic.ValidationError. On bad input it raises instead of returning None — wrap the construction in try/except.",
    ],
  },
  {
    type: "feedback",
    content:
      "the model shape is right, but validation rules and error handling need work. revisit Field constraints and the difference between model construction and safe parsing.",
    gaps: [
      "missing the age >= 0 constraint — use Field(..., ge=0) or PositiveInt-style validation. As written, age=-5 is accepted.",
      "parse_user does not catch pydantic.ValidationError. On bad input it raises instead of returning None — wrap the construction in try/except.",
    ],
  },
]

const asyncSteps: LessonStep[] = [
  {
    type: "theory",
    content: `Python's async/await is cooperative concurrency on a single thread. An async function returns a coroutine; awaiting it yields control to the event loop, which schedules other coroutines while you wait on I/O.

If you're coming from Node, the model is nearly identical to Promises + async/await — same single-threaded event loop, same colored functions. The biggest gotcha: blocking calls (CPU work, sync DB drivers, time.sleep) freeze the entire loop. Use asyncio.to_thread or a thread pool to escape.

await is not parallelism. await asyncio.gather(...) is.`,
  },
  {
    type: "check",
    content:
      "Why does calling time.sleep(1) inside an async handler block the whole server, while await asyncio.sleep(1) doesn't?",
    user_answer:
      "time.sleep is a blocking syscall — it parks the OS thread. Since asyncio runs on a single thread, every other coroutine is stuck behind it. asyncio.sleep yields to the event loop, which schedules other coroutines until the timer fires.",
    verdict: "passed",
  },
  {
    type: "problem",
    content: `# Implement fetch_all(urls: list[str]) -> list[str]
# Fetch every URL concurrently with httpx.AsyncClient.
# Return response bodies in input order.`,
    code: `import asyncio
import httpx

async def fetch_all(urls: list[str]) -> list[str]:
    async with httpx.AsyncClient() as client:
        tasks = [client.get(u) for u in urls]
        responses = await asyncio.gather(*tasks)
        return [r.text for r in responses]`,
    gaps: [],
  },
  {
    type: "feedback",
    content:
      "correct use of asyncio.gather to run requests concurrently, with the AsyncClient context-managed to share connections. ordering preserved by gather's contract. topic marked as covered.",
    gaps: [],
  },
]

const langgraphStateSteps: LessonStep[] = [
  {
    type: "theory",
    content: `LangGraph models a multi-agent system as a state machine. You define a TypedDict for the shared state, register nodes (functions that mutate state), and add edges (rules for which node runs next).

Each node receives the current state and returns a partial dict that LangGraph merges back in. Reducers control how merges work — by default, last-write-wins; for lists, you typically want operator.add to append.

The "graph" framing matters: branches and loops are first-class. Conditional edges let an agent decide whether the run is finished, whether to retry, or which sibling node to call next — without that machinery you end up rebuilding it inside a chain.`,
  },
  {
    type: "check",
    content:
      "What's the role of a reducer on a state field, and when does the default last-write-wins fail?",
    user_answer:
      "Reducers tell LangGraph how to merge a node's partial state update with existing state. last-write-wins works for scalar fields like a current step or status. It fails for accumulating fields like a message history — you'd want operator.add (or a custom reducer) so each node appends rather than overwrites.",
    verdict: "passed",
  },
  {
    type: "problem",
    content: `# Define a LangGraph state with:
#   messages:  list[str], reducer = operator.add
#   step:      str (last-write-wins)
#
# Compile a 2-node graph: "greet" -> "farewell" -> END.
# Each node appends one message.`,
    code: `import operator
from typing import Annotated, TypedDict
from langgraph.graph import END, StateGraph

class State(TypedDict):
    messages: Annotated[list[str], operator.add]
    step: str

def greet(s: State) -> dict:
    return {"messages": ["hello"], "step": "greet"}

def farewell(s: State) -> dict:
    return {"messages": ["bye"], "step": "farewell"}

g = StateGraph(State)
g.add_node("greet", greet)
g.add_node("farewell", farewell)
g.set_entry_point("greet")
g.add_edge("greet", "farewell")
g.add_edge("farewell", END)
graph = g.compile()`,
    gaps: [],
  },
  {
    type: "feedback",
    content:
      "the Annotated reducer is correct, the entry point is set, and the linear edge sequence terminates at END. topic marked as covered.",
    gaps: [],
  },
]

const ragSteps: LessonStep[] = [
  {
    type: "theory",
    content: `Retrieval-Augmented Generation is a pattern, not a product. The shape: at query time, embed the user's question, retrieve the top-k most similar chunks from a vector store, stuff those chunks into the prompt as context, and let the model answer.

The hard parts aren't the embedding call — they're chunking strategy (paragraph? sentence? sliding window?), retrieval quality (do you re-rank?), and prompt assembly (how do you tell the model "answer only from these"?). Skipping any of those gives you confident hallucinations.

For depthed v1 we don't ship RAG: the lesson loop is generated, not retrieved. But understanding when RAG is the right tool is part of agent literacy.`,
  },
  {
    type: "check",
    content:
      "Why does just dumping retrieved chunks into the prompt without instruction often produce confidently wrong answers?",
    user_answer:
      "the model treats prompt context as suggestion, not constraint. without an explicit 'answer only from the provided context, say I don't know otherwise' instruction, it falls back on training-data priors and confabulates.",
    verdict: "passed",
  },
  {
    type: "problem",
    content: `# Build a minimal RAG step:
#   retrieve(query, k=4)  -> top-k chunks from a Chroma collection
#   answer(query)         -> calls the LLM with the chunks as context
#
# Use any embedding + LLM. Keep it under 30 lines.`,
    code: `from openai import OpenAI
import chromadb

client = OpenAI()
chroma = chromadb.Client()
col = chroma.get_or_create_collection("docs")

def retrieve(query: str, k: int = 4) -> list[str]:
    res = col.query(query_texts=[query], n_results=k)
    return res["documents"][0]

def answer(query: str) -> str:
    chunks = retrieve(query)
    context = "\\n\\n".join(chunks)
    out = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": f"{query}\\n\\n{context}"}],
    )
    return out.choices[0].message.content`,
    gaps: [
      "no system prompt constraining the model to the retrieved context. With this prompt, the model will happily answer from training data when retrieval is weak — exactly the failure mode of RAG.",
      "no handling for empty retrieval. If the collection is empty or no chunks pass a similarity threshold, you should short-circuit with 'I don't know' instead of inventing.",
      "chunks are concatenated without source markers. When the model cites or quotes, you can't trace which chunk it used — kills observability and downstream eval.",
    ],
  },
  {
    type: "feedback",
    content:
      "the wiring works, but this is the textbook 'RAG that hallucinates'. the missing pieces are exactly what separates a demo from a system you'd ship.",
    gaps: [
      "no system prompt constraining the model to the retrieved context. With this prompt, the model will happily answer from training data when retrieval is weak — exactly the failure mode of RAG.",
      "no handling for empty retrieval. If the collection is empty or no chunks pass a similarity threshold, you should short-circuit with 'I don't know' instead of inventing.",
      "chunks are concatenated without source markers. When the model cites or quotes, you can't trace which chunk it used — kills observability and downstream eval.",
    ],
  },
]

const jwtSteps: LessonStep[] = [
  {
    type: "theory",
    content: `A JWT is three base64url segments separated by dots: header.payload.signature. The header names the algorithm, the payload carries claims (sub, exp, iat, plus whatever you put there), and the signature is HMAC or RSA over the first two parts using a secret only the server knows.

The point is statelessness. The server doesn't store sessions — it issues a signed token, the client sends it back on every request, the server verifies the signature and trusts the claims. Tampering breaks the signature; expiry is enforced via the exp claim.

Common pitfall: treating the payload as confidential. It's base64, not encrypted. Don't put secrets there. Use it for identity and authorization claims only.`,
  },
  {
    type: "check",
    content:
      "If the JWT payload is just base64-encoded JSON, what makes a JWT 'secure' — and what guarantee does it provide?",
    user_answer:
      "the signature. anyone can read the payload, but only someone with the signing secret can produce a token whose signature verifies. so JWTs guarantee integrity and origin (this token was issued by us and hasn't been tampered with), not confidentiality.",
    verdict: "passed",
  },
  {
    type: "problem",
    content: `# Implement:
#   issue(user_id: str)  -> JWT, exp = now + 1 hour
#   verify(token: str)   -> user_id, raise on invalid or expired
#
# Use python-jose, HS256, secret from env.`,
    code: `import os
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt

SECRET = os.environ["JWT_SECRET"]
ALG = "HS256"

def issue(user_id: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {"sub": user_id, "iat": now, "exp": now + timedelta(hours=1)}
    return jwt.encode(payload, SECRET, algorithm=ALG)

def verify(token: str) -> str:
    try:
        payload = jwt.decode(token, SECRET, algorithms=[ALG])
    except JWTError as e:
        raise ValueError("invalid token") from e
    return payload["sub"]`,
    gaps: [],
  },
  {
    type: "feedback",
    content:
      "exp is set, decode validates the signature, and JWTError is mapped to a domain error. nothing leaks the secret. topic marked as covered.",
    gaps: [],
  },
]

const checkpointersSteps: LessonStep[] = [
  {
    type: "theory",
    content: `LangGraph checkpointers persist graph state at every super-step so a run can be paused, resumed, or branched. Without one, a graph is in-memory only — fine for one-shot scripts, useless for an agent that waits on user input across HTTP calls.

The interface: a checkpointer reads and writes a versioned snapshot of the State for a given thread_id. langgraph-checkpoint-postgres ships an implementation backed by Postgres tables; you point it at a connection string and pass it to graph.compile(checkpointer=...).

For depthed, the comprehension check and the problem submit are interrupt points. The graph runs until interrupt-before, the checkpointer saves the State, the response returns to the browser, and on the next user submit we resume from that checkpoint with the new input merged in.`,
  },
  {
    type: "check",
    content:
      "Why does compile(checkpointer=...) require a thread_id at runtime, and what would happen if two concurrent users shared one?",
    user_answer: "",
  },
]

export const MOCK_LESSONS: Record<string, LessonData> = {
  "s-fastapi-di": {
    session: buildSession("s-fastapi-di", "FastAPI Dependency Injection", 1),
    memory: buildMemory("FastAPI Dependency Injection", "covered", 0, 1),
    steps: fastApiDiSteps,
  },
  "s-pydantic": {
    session: buildSession("s-pydantic", "Python Type Hints & Pydantic", 2),
    memory: buildMemory("Python Type Hints & Pydantic", "struggling", 2, 2),
    steps: pydanticSteps,
  },
  "s-async": {
    session: buildSession("s-async", "Async/Await in Python", 3),
    memory: buildMemory("Async/Await in Python", "covered", 1, 3),
    steps: asyncSteps,
  },
  "s-langgraph-state": {
    session: buildSession("s-langgraph-state", "LangGraph State Machines", 4),
    memory: buildMemory("LangGraph State Machines", "covered", 0, 4),
    steps: langgraphStateSteps,
  },
  "s-rag": {
    session: buildSession("s-rag", "RAG Architecture", 5),
    memory: buildMemory("RAG Architecture", "struggling", 3, 5),
    steps: ragSteps,
  },
  "s-jwt": {
    session: buildSession("s-jwt", "JWT Authentication", 6),
    memory: buildMemory("JWT Authentication", "covered", 0, 6),
    steps: jwtSteps,
  },
  "s-langgraph-checkpointers": {
    session: buildSession(
      "s-langgraph-checkpointers",
      "LangGraph Checkpointers",
      0,
      "active",
    ),
    memory: buildMemory("LangGraph Checkpointers", "suggested", 0, 0),
    steps: checkpointersSteps,
  },
}
