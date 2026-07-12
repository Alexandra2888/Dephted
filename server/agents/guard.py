"""Scope Guard (gpt-4o-mini) — runs before Theory.

Classifies the requested topic as an in-scope backend-learning topic or an off-topic /
abusive request. Out-of-scope requests are refused with a fixed message and the graph
routes straight to END, so the Theory agent never generates the requested content. This
is the product fix for the scope-abuse breach the adversarial suite surfaced (the tutor
would otherwise happily write a keylogger or an essay).
"""

import re

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.config import get_stream_writer

from agents.llms import GPT_MINI, openai_llm
from agents.state import LessonState
from guards import decision_as_dict, make_scope_decision
from prompts import load_prompt

_SCOPE_RE = re.compile(r"\b(OUT_OF_SCOPE|IN_SCOPE)\b", flags=re.IGNORECASE)

# Fixed, safe refusal — never generated content, so it can't be steered into anything harmful.
REFUSAL = (
    "I can only help with backend software engineering topics — APIs, databases, auth, "
    "concurrency, caching, system design, and the like. Let's pick a backend topic to work on."
)


async def topic_guard(state: LessonState) -> dict[str, object]:
    llm = openai_llm(GPT_MINI, temperature=0.0)
    messages = [
        SystemMessage(content=load_prompt("guard")),
        HumanMessage(content=f"Requested topic:\n{state['topic']}"),
    ]
    response = await llm.ainvoke(messages)
    body = response.content if isinstance(response.content, str) else str(response.content)
    match = _SCOPE_RE.search(body)
    # Fail open to a legitimate lesson only when the classifier is explicit; an explicit
    # OUT_OF_SCOPE (or an unparseable response on an abusive topic) refuses.
    verdict = match.group(1).upper() if match else "OUT_OF_SCOPE"

    # Record this existing classification as a guard decision (no second LLM call). The router
    # drains `scope_decision` from state and persists it alongside the other guard events.
    scope_decision = decision_as_dict(
        make_scope_decision(out_of_scope=verdict != "IN_SCOPE", verdict=verdict)
    )

    if verdict == "IN_SCOPE":
        return {"scope_ok": True, "scope_decision": scope_decision}

    writer = get_stream_writer()
    writer({"type": "section_start", "section": "theory"})
    writer({"type": "token", "section": "theory", "data": REFUSAL})
    writer({"type": "section_complete", "section": "theory"})
    return {"scope_ok": False, "theory_text": REFUSAL, "scope_decision": scope_decision}
