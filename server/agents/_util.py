"""Shared helpers for agent nodes: token extraction, JSON parsing, text slicing."""

import json
import re
from typing import Any

from langchain_core.messages import BaseMessage


def chunk_text(chunk: BaseMessage) -> str:
    """Extract plain text from a streamed message chunk across providers.

    OpenAI chunks carry a string `content`; Anthropic may carry a list of content
    blocks (dicts with `type: text` or objects exposing `.text`).
    """
    content: Any = chunk.content
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                if block.get("type") == "text":
                    parts.append(str(block.get("text", "")))
            else:
                text = getattr(block, "text", None)
                if isinstance(text, str):
                    parts.append(text)
        return "".join(parts)
    return ""


def parse_json_object(raw: str) -> dict[str, Any]:
    """Parse a JSON object from an LLM response, tolerating code fences / prose."""
    text = raw.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.MULTILINE).strip()
    try:
        result = json.loads(text)
        if isinstance(result, dict):
            return result
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if match:
        try:
            result = json.loads(match.group(0))
            if isinstance(result, dict):
                return result
        except json.JSONDecodeError:
            pass
    return {}


_CHECK_RE = re.compile(r"\*\*check:\*\*\s*(.+)\s*$", flags=re.IGNORECASE | re.DOTALL)


def extract_check_question(theory_text: str) -> str:
    """Pull the trailing `**Check:** ...` comprehension question out of theory text."""
    match = _CHECK_RE.search(theory_text)
    return match.group(1).strip() if match else ""


def strip_check_question(theory_text: str) -> str:
    """Theory explanation without the trailing comprehension question."""
    return _CHECK_RE.sub("", theory_text).strip()
