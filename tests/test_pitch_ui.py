"""
Tests for UI overhaul: product pitch flow and sentiment parsing.

What we expect:
- build_system_prompt instructs persona to react to a product pitch
- build_system_prompt asks for a one-word sentiment label at the start
- build_system_prompt mentions POSITIVE, NEGATIVE, MIXED, NEUTRAL as options
- build_system_prompt still contains demographic info and excerpt
- build_system_prompt still works with sector=None and empty tags
"""

import pytest
from focus_groups.personas.cards import PersonaCard
from focus_groups.personas.profiles import build_system_prompt


def make_card(**kwargs) -> PersonaCard:
    defaults = dict(
        post_id=1,
        demographic_tags={"age_group": "25-34", "gender": "male"},
        text_excerpt="I think the tech industry is moving too fast.",
        sector="tech",
    )
    defaults.update(kwargs)
    return PersonaCard(**defaults)


# --- Sentiment label instruction ---

def test_prompt_requests_sentiment_label():
    """The prompt should instruct the persona to start with a sentiment label."""
    card = make_card()
    result = build_system_prompt(card)
    lower = result.lower()
    assert "positive" in lower
    assert "negative" in lower
    assert "mixed" in lower
    assert "neutral" in lower


def test_prompt_mentions_product_pitch():
    """The prompt should frame the interaction as a product pitch."""
    card = make_card()
    result = build_system_prompt(card)
    lower = result.lower()
    assert "product" in lower or "pitch" in lower


def test_prompt_asks_for_honest_reaction():
    """The prompt should ask for honest/genuine sentiment."""
    card = make_card()
    result = build_system_prompt(card)
    lower = result.lower()
    assert any(word in lower for word in ["honest", "genuine", "authentic", "real"])


# --- Existing behavior preserved ---

def test_prompt_still_contains_demographics():
    card = make_card(demographic_tags={"age_group": "35-44", "gender": "female"})
    result = build_system_prompt(card)
    assert "35-44" in result
    assert "female" in result


def test_prompt_still_contains_excerpt():
    card = make_card(text_excerpt="I love budgeting apps")
    result = build_system_prompt(card)
    assert "I love budgeting apps" in result


def test_prompt_still_contains_sector():
    card = make_card(sector="financial")
    result = build_system_prompt(card)
    assert "financial" in result


def test_prompt_works_with_no_sector():
    card = make_card(sector=None)
    result = build_system_prompt(card)
    assert isinstance(result, str)
    assert len(result) > 0


def test_prompt_works_with_empty_tags():
    card = make_card(demographic_tags={})
    result = build_system_prompt(card)
    assert isinstance(result, str)
    assert len(result) > 0
