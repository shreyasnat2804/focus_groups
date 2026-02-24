"""
Format PersonaCards into Claude API system prompts.

No DB dependency — pure string formatting.
"""

from __future__ import annotations

from personas.cards import PersonaCard


def format_demographic_summary(tags: dict) -> str:
    """
    Convert a demographic tags dict into a readable summary string.

    Example:
        {"age_group": "25-34", "gender": "male", "income_bracket": "high_income"}
        → "25-34 year old male, high income"

    Args:
        tags: {dimension_name: value} e.g. from PersonaCard.demographic_tags

    Returns:
        Human-readable demographic description, or empty string if tags is empty.
    """
    if not tags:
        return ""

    parts = []

    age = tags.get("age_group")
    gender = tags.get("gender")
    income = tags.get("income_bracket")

    if age and gender:
        parts.append(f"{age} year old {gender}")
    elif age:
        parts.append(f"{age} year old")
    elif gender:
        parts.append(gender)

    if income:
        # Convert "high_income" → "high income"
        parts.append(income.replace("_", " "))

    # Include any remaining dimensions not handled above
    handled = {"age_group", "gender", "income_bracket"}
    for dim, val in tags.items():
        if dim not in handled:
            parts.append(f"{dim.replace('_', ' ')}: {val}")

    return ", ".join(parts)


def build_system_prompt(card: PersonaCard) -> str:
    """
    Format a PersonaCard as a Claude system prompt string.

    Used by Stage 3 backend to ground Claude in a persona's voice.

    Args:
        card: PersonaCard with demographic_tags, text_excerpt, sector

    Returns:
        System prompt string ready to pass to the Claude API.
    """
    demo_summary = format_demographic_summary(card.demographic_tags)

    lines = ["You are simulating a real person with the following profile:"]

    demo_line = f"Demographics: {demo_summary}" if demo_summary else "Demographics: unspecified"
    if card.sector:
        demo_line += f", {card.sector} sector"
    lines.append(demo_line)

    lines.append("")
    lines.append("Here is an example of how this person communicates:")
    lines.append(f'"{card.text_excerpt}"')
    lines.append("")
    lines.append(
        "Respond authentically as this person would, matching their tone, "
        "vocabulary, and perspective. Do not break character."
    )

    return "\n".join(lines)
