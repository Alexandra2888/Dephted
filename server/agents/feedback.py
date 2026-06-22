"""Feedback Agent (claude-sonnet-4-6) — honest, gap-flagging review of the solution."""

import re

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.config import get_stream_writer

from agents._util import chunk_text
from agents.llms import anthropic_llm
from agents.state import LessonState
from prompts import load_prompt

_VERDICT_RE = re.compile(r"\*\*verdict:\*\*\s*(completed|struggling)", flags=re.IGNORECASE)
_GAP_RE = re.compile(r"^\s*[-*]\s+(.*)$", flags=re.MULTILINE)


async def feedback_review(state: LessonState) -> dict[str, object]:
    writer = get_stream_writer()
    solution = (state.get("pending_input") or state.get("solution") or "").strip()

    messages = [
        SystemMessage(content=load_prompt("feedback")),
        HumanMessage(
            content=(
                f"Problem:\n{state.get('problem_text', '')}\n\n"
                f"Learner's solution:\n{solution or '(no solution submitted)'}\n\n"
                f"Theory focus: {state['plan'].get('theory_focus', '')}"
            )
        ),
    ]

    writer({"type": "section_start", "section": "feedback"})
    parts: list[str] = []
    async for chunk in anthropic_llm(temperature=0.3).astream(messages):
        text = chunk_text(chunk)
        if text:
            parts.append(text)
            writer({"type": "token", "section": "feedback", "data": text})
    feedback_text = "".join(parts)

    match = _VERDICT_RE.search(feedback_text)
    verdict = match.group(1).lower() if match else "struggling"
    gaps = [g.strip() for g in _GAP_RE.findall(feedback_text) if g.strip()]

    writer(
        {"type": "section_complete", "section": "feedback", "verdict": verdict}
    )

    return {
        "solution": solution,
        "feedback_text": feedback_text,
        "verdict": verdict,
        "gaps": gaps,
    }
