"""
Robust JSON extraction from Claude responses.

Claude sometimes wraps JSON in markdown fences or adds explanatory text.
This module extracts the first valid JSON object from such responses.
"""

from __future__ import annotations

import json
import re


def extract_json(text: str) -> dict:
    """
    Extract the first JSON object from a string that may contain
    surrounding text, markdown fences, or other non-JSON content.

    Tries in order:
    1. Direct json.loads on stripped text
    2. Extract from ```json ... ``` fences
    3. Find first { ... } substring and parse it

    Raises:
        ValueError: If no valid JSON object can be extracted.
    """
    stripped = text.strip()

    # 1. Try direct parse
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass

    # 2. Try markdown code fence extraction
    fence_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", stripped, re.DOTALL)
    if fence_match:
        try:
            return json.loads(fence_match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # 3. Find first { ... } with balanced braces
    start = stripped.find("{")
    if start != -1:
        depth = 0
        for i in range(start, len(stripped)):
            if stripped[i] == "{":
                depth += 1
            elif stripped[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(stripped[start : i + 1])
                    except json.JSONDecodeError:
                        break

    raise ValueError(f"Could not extract JSON from response: {stripped[:200]}")
