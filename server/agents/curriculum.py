"""Curriculum Agent (gpt-4o-mini) — decompose the topic into a session plan."""

from langchain_core.messages import HumanMessage, SystemMessage

from agents._util import parse_json_object
from agents.llms import GPT_MINI, openai_llm
from agents.state import LessonState
from prompts import load_prompt


async def curriculum(state: LessonState) -> dict[str, object]:
    llm = openai_llm(GPT_MINI, temperature=0.2)
    messages = [
        SystemMessage(content=load_prompt("curriculum")),
        HumanMessage(
            content=(
                f"Topic: {state['topic']}\n"
                f"Learner context: {state.get('memory_summary', 'No prior history.')}"
            )
        ),
    ]
    response = await llm.ainvoke(messages)
    plan = parse_json_object(
        response.content if isinstance(response.content, str) else str(response.content)
    )

    # Defensive defaults so downstream nodes never KeyError on a malformed plan.
    plan.setdefault("topic", state["topic"])
    plan.setdefault("difficulty", "intermediate")
    plan.setdefault("theory_focus", state["topic"])
    plan.setdefault("comprehension_question_hint", "core understanding of the concept")
    plan.setdefault("problem_brief", f"a small exercise on {state['topic']}")

    return {"plan": {k: str(v) for k, v in plan.items()}, "attempts": 0}
