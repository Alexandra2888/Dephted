"""Problem Agent (gpt-4o) — generate a scoped coding problem, streamed."""

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.config import get_stream_writer

from agents._util import chunk_text
from agents.llms import GPT_4O, openai_llm
from agents.state import LessonState
from prompts import load_prompt


async def problem_generate(state: LessonState) -> dict[str, object]:
    writer = get_stream_writer()
    plan = state["plan"]

    messages = [
        SystemMessage(content=load_prompt("problem")),
        HumanMessage(
            content=(
                "Generate the coding problem now.\n"
                f"Topic: {plan['topic']}\n"
                f"Difficulty: {plan['difficulty']}\n"
                f"Problem brief: {plan['problem_brief']}"
            )
        ),
    ]

    writer({"type": "section_start", "section": "problem"})
    parts: list[str] = []
    async for chunk in openai_llm(GPT_4O, temperature=0.3).astream(messages):
        text = chunk_text(chunk)
        if text:
            parts.append(text)
            writer({"type": "token", "section": "problem", "data": text})
    problem_text = "".join(parts)
    writer({"type": "section_complete", "section": "problem"})

    return {"problem_text": problem_text}
