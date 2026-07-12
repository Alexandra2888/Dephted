"""Compiled regex banks for the input/output guards (no external deps).

Kept deliberately conservative and cheap — these are a fast first layer, not a complete
jailbreak classifier. The point in shadow mode is to measure how often each pattern fires on
real traffic before any of them is allowed to block.
"""

from __future__ import annotations

import re

from prompts import load_prompt

Pattern = tuple[str, re.Pattern[str]]


def _bank(entries: dict[str, str]) -> list[Pattern]:
    return [(name, re.compile(rx, re.IGNORECASE)) for name, rx in entries.items()]


# Prompt-injection / jailbreak markers in *user input*. Deliberately targeted at imperative
# override / verdict-forcing / prompt-leak phrasings (not ordinary content words) so the
# false-positive rate on real answers stays low. Measured in shadow before any of them blocks.
INJECTION_PATTERNS: list[Pattern] = _bank(
    {
        # "ignore/disregard/forget the rubric | previous instructions | the question | ..."
        "override_directive": (
            r"\b(?:ignore|disregard|forget|override)\b[\s\S]{0,40}?"
            r"\b(?:instruction|prompt|rubric|question|check|rule|previous|prior|above|earlier|system)\b"
        ),
        "output_verdict": r"output\s*:?\s*(?:passed|failed|completed|struggling)",
        # Tolerates markdown decoration: "**Verdict:** completed", "Verdict = PASSED".
        "verdict_directive": r"\bverdict\b\W{0,6}(?:passed|failed|completed|struggling)",
        "force_grade": r"\bsay\b[\s\S]{0,30}?\b(?:passed|complete|completed|correct|perfect)\b",
        # Prompt-leak seeking: "repeat/print/reveal ... (your|system) prompt/instructions".
        "leak_seek": (
            r"\b(?:repeat|print|output|reveal|show|summar\w+|translate)\b[\s\S]{0,40}?"
            r"(?:system\s+(?:prompt|instruction|message)|your\s+(?:\w+\s+){0,2}"
            r"(?:instruction|prompt|rule|stance))"
        ),
        "system_prompt_ref": r"\bsystem\s+(?:prompt|instructions?|message)\b",
        "dan": r"\bDAN\b|do\s+anything\s+now",
        "role_marker": r"(?:^|\n)\s*(?:system|assistant)\s*:",
        "delimiter_injection": r"<<<.*?>>>",
        "role_override": r"you\s+are\s+now\b|pretend\s+to\s+be\b|act\s+as\s+(?:a|an|the)\b",
        "new_instructions": r"new\s+instructions?\s*:",
    }
)

# Distinctive system-prompt fragments — if any surface in *model output*, a leak is likely.
# The opening lines of the agent prompts are pulled at import so the markers track the prompts.
_PROMPT_LEAK_LITERALS = {
    "grader_rubric": r"you\s+grade\s+a\s+learner'?s\s+answer",
    "verdict_instruction": r"reply\s+with\s+exactly\s+one\s+word",
    "system_message": r"\bSystemMessage\b",
    "comprehension_hint": r"comprehension_question_hint",
}


def _prompt_opening_markers() -> dict[str, str]:
    """First sentence of each agent prompt, escaped, as leak canaries."""
    markers: dict[str, str] = {}
    for name in ("theory", "feedback", "guard"):
        try:
            opening = load_prompt(name).splitlines()[0].strip()
        except (FileNotFoundError, IndexError):
            continue
        if len(opening) >= 20:
            markers[f"prompt_{name}"] = re.escape(opening[:80])
    return markers


PROMPT_LEAK_MARKERS: list[Pattern] = _bank({**_PROMPT_LEAK_LITERALS, **_prompt_opening_markers()})

# Dangerous constructs in generated code the learner might copy and run. FLAG only — backend
# lessons legitimately discuss subprocess/sockets, so this observes rather than blocks.
CODE_SAFETY_PATTERNS: list[Pattern] = _bank(
    {
        "os_system": r"os\.system\s*\(",
        "subprocess": r"\bsubprocess\.(?:run|call|Popen|check_output)\b",
        "rm_rf": r"\brm\s+-rf\b",
        "eval": r"\beval\s*\(",
        "exec": r"\bexec\s*\(",
        "socket": r"\bsocket\.socket\b",
        "http_call": r"\brequests\.(?:get|post|put|delete)\b|\burllib\.request\b",
        "shell_fetch": r"\b(?:curl|wget)\s+https?://",
        "pickle_loads": r"\bpickle\.loads?\b",
    }
)


def first_match(text: str, patterns: list[Pattern]) -> tuple[str | None, str]:
    """Return (pattern_name, matched_snippet) of the first pattern that matches, else (None, "")."""
    for name, rx in patterns:
        m = rx.search(text)
        if m:
            snippet = m.group(0)
            return name, snippet[:120]
    return None, ""
