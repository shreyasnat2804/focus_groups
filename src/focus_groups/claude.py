"""
Claude API integration for generating focus group responses.

Each persona (PersonaCard) gets a system prompt built from their demographic
profile and text excerpt, then Claude answers the focus group question in
that persona's voice.
"""

from __future__ import annotations

import os

import anthropic

from focus_groups.personas.cards import PersonaCard
from focus_groups.personas.profiles import build_system_prompt, format_demographic_summary

MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")
MAX_TOKENS = int(os.getenv("CLAUDE_MAX_TOKENS", "1024"))


def get_client() -> anthropic.Anthropic:
    """Return an Anthropic client (reads ANTHROPIC_API_KEY from env)."""
    return anthropic.Anthropic()


def generate_persona_response(
    client: anthropic.Anthropic,
    card: PersonaCard,
    question: str,
) -> str:
    """
    Call Claude with a persona system prompt and return the response text.

    Args:
        client:   Anthropic API client
        card:     PersonaCard with demographics + text excerpt
        question: The focus group question to answer

    Returns:
        Claude's response text as a string.
    """
    system_prompt = build_system_prompt(card)

    message = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=system_prompt,
        messages=[{"role": "user", "content": question}],
    )

    return message.content[0].text


def run_focus_group(
    client: anthropic.Anthropic,
    cards: list[PersonaCard],
    question: str,
) -> list[dict]:
    """
    Run a full focus group: call Claude once per persona card.

    Args:
        client:   Anthropic API client
        cards:    List of PersonaCards (from personas.select_personas)
        question: The focus group question

    Returns:
        List of dicts with keys:
          post_id, persona_summary, system_prompt, response_text, model
    """
    results = []

    for card in cards:
        system_prompt = build_system_prompt(card)
        persona_summary = format_demographic_summary(card.demographic_tags)
        response_text = generate_persona_response(client, card, question)

        results.append({
            "post_id": card.post_id,
            "persona_summary": persona_summary,
            "system_prompt": system_prompt,
            "response_text": response_text,
            "model": MODEL,
        })

    return results
