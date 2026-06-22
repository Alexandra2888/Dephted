"""Eval scorers (docs/architecture.md §11). LLM-judge with gpt-4o-mini.

Each judge returns a float in [0, 1]. Keep them small and independent so failures are
attributable to a single dimension.
"""

from langchain_core.messages import HumanMessage, SystemMessage

from agents._util import parse_json_object
from agents.llms import GPT_MINI, openai_llm

_JSON_SUFFIX = ' Respond with JSON only: {"score": <number 0.0-1.0>, "reason": "<short>"}'


async def _judge(instruction: str, content: str) -> float:
    llm = openai_llm(GPT_MINI, temperature=0.0)
    response = await llm.ainvoke(
        [
            SystemMessage(content=instruction + _JSON_SUFFIX),
            HumanMessage(content=content),
        ]
    )
    body = response.content if isinstance(response.content, str) else str(response.content)
    data = parse_json_object(body)
    try:
        return max(0.0, min(1.0, float(data.get("score", 0.0))))
    except (TypeError, ValueError):
        return 0.0


async def theory_faithfulness(theory_text: str, reference_points: list[str]) -> float:
    if not theory_text:
        return 0.0
    points = "\n".join(f"- {p}" for p in reference_points)
    return await _judge(
        "You judge whether an explanation is factually correct and covers the key points. "
        "Score 1.0 if it covers the points with no factual errors, lower if points are "
        "missing or anything is wrong.",
        f"Key points that should be covered:\n{points}\n\nExplanation:\n{theory_text}",
    )


async def problem_wellformed(problem_text: str) -> float:
    if not problem_text:
        return 0.0
    return await _judge(
        "You judge whether a coding problem statement is well-formed: a single, clearly "
        "scoped, solvable task with stated expectations. Score 1.0 for a clean solvable "
        "problem, lower if vague, multi-part, or unsolvable.",
        f"Problem statement:\n{problem_text}",
    )


async def feedback_accuracy(
    problem_text: str, solution: str, feedback_text: str, known_gap: str
) -> float:
    if not feedback_text:
        return 0.0
    return await _judge(
        "You judge whether code-review feedback is accurate, specific, and honest about the "
        "submitted solution — flagging real problems rather than praising. The solution is "
        f"known to have at least this issue: '{known_gap}'. Score 1.0 if the feedback honestly "
        "flags genuine problems with the solution (the known issue, other real bugs, or that "
        "it does not address the stated problem); score low if it is vague, sycophantic, or "
        "factually wrong about the code.",
        f"Problem:\n{problem_text}\n\nSubmitted solution:\n{solution}\n\nFeedback:\n{feedback_text}",
    )


def trajectory(reached_feedback: bool) -> float:
    """Did the graph route all the way through to the feedback section?"""
    return 1.0 if reached_feedback else 0.0
