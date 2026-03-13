"""
Format PersonaCards into Claude API system prompts.

Loads prompt templates from src/focus_groups/prompts/ and fills in
persona-specific data at runtime.
"""

from __future__ import annotations

from pathlib import Path

from focus_groups.personas.cards import PersonaCard

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


def load_prompt_template(filename: str) -> str:
    """
    Load a prompt template file from the prompts directory.

    Args:
        filename: Name of the template file (e.g. "identity.txt")

    Returns:
        Raw template string with {placeholders} intact.

    Raises:
        FileNotFoundError: If the template file does not exist.
    """
    path = PROMPTS_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Prompt template not found: {path}")
    return path.read_text().strip()


def format_demographic_summary(tags: dict) -> str:
    """
    Convert a demographic tags dict into a readable summary string.

    Example:
        {"age_group": "25-34", "gender": "male", "income_bracket": "high_income"}
        -> "25-34 year old male, high income"

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
        # Convert "high_income" -> "high income"
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

    Loads template files from the prompts/ directory and fills in
    persona-specific data.

    Args:
        card: PersonaCard with demographic_tags, text_excerpt, sector

    Returns:
        System prompt string ready to pass to the Claude API.
    """
    demo_summary = format_demographic_summary(card.demographic_tags)

    # Build the demographic line
    demo_line = demo_summary if demo_summary else "unspecified"
    if card.sector:
        demo_line += f", {card.sector} sector"

    identity = load_prompt_template("identity.txt").format(
        demographic_summary=demo_line,
    )
    voice = load_prompt_template("voice.txt").format(
        text_excerpt=card.text_excerpt,
    )
    instructions = load_prompt_template("instructions.txt")
    fmt = load_prompt_template("format.txt")

    sections = [identity, "", voice, "", instructions, "", fmt]
    return "\n".join(sections)
