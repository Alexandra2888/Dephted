"""Theory Agent (claude-sonnet-4-6).

Two nodes:
- `theory_explain`: stream a concise explanation ending in a comprehension question.
- `comprehension`: evaluate the learner's answer; mark passed/failed. (The Theory Agent
  owns the comprehension gate per architecture §6.2–6.3.)
"""

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.config import get_stream_writer

from agents._util import chunk_text, extract_check_question
from agents.llms import anthropic_llm
from agents.state import LessonState
from prompts import load_prompt


async def theory_explain(state: LessonState) -> dict[str, object]:
    writer = get_stream_writer()
    plan = state["plan"]
    attempts = state.get("attempts", 0)

    retry_note = ""
    if attempts > 0:
        retry_note = (
            "\n\nThe learner did NOT pass the comprehension check. Re-explain the concept "
            "from a different angle, more simply, with a concrete example. End with a fresh "
            "comprehension question."
        )

    messages = [
        SystemMessage(content=load_prompt("theory")),
        HumanMessage(
            content=(
                f"Topic: {plan['topic']}\n"
                f"Difficulty: {plan['difficulty']}\n"
                f"Theory focus: {plan['theory_focus']}\n"
                f"Comprehension check should probe: {plan['comprehension_question_hint']}"
                f"{retry_note}"
            )
        ),
    ]

    writer({"type": "section_start", "section": "theory"})
    parts: list[str] = []
    async for chunk in anthropic_llm().astream(messages):
        text = chunk_text(chunk)
        if text:
            parts.append(text)
            writer({"type": "token", "section": "theory", "data": text})
    theory_text = "".join(parts)
    writer({"type": "section_complete", "section": "theory"})

    return {"theory_text": theory_text}


async def comprehension(state: LessonState) -> dict[str, object]:
    writer = get_stream_writer()
    answer = (state.get("pending_input") or state.get("comprehension_answer") or "").strip()
    question = extract_check_question(state.get("theory_text", ""))

    writer({"type": "section_start", "section": "check"})

    llm = anthropic_llm(temperature=0.0, max_tokens=300)
    messages = [
        SystemMessage(
            content=(
                "You grade a learner's answer to a comprehension question. Decide if they "
                "demonstrated genuine understanding of the concept (not just keyword match). "
                "Reply with exactly one word on the first line: PASSED or FAILED. Then one "
                "short sentence explaining why."
            )
        ),
        HumanMessage(
            content=(
                f"Question: {question}\n\n"
                f"Learner's answer: {answer}\n\n"
                f"Concept being tested: {state['plan'].get('theory_focus', '')}"
            )
        ),
    ]
    response = await llm.ainvoke(messages)
    body = response.content if isinstance(response.content, str) else str(response.content)
    verdict = "passed" if body.strip().upper().startswith("PASSED") else "failed"

    attempts = state.get("attempts", 0) + (0 if verdict == "passed" else 1)
    writer(
        {"type": "section_complete", "section": "check", "verdict": verdict, "data": answer}
    )

    return {
        "comprehension_answer": answer,
        "comprehension_verdict": verdict,
        "attempts": attempts,
        "pending_input": None,
    }
