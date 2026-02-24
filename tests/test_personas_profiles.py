"""
Tests for personas/profiles.py

What we expect:
- format_demographic_summary({}) returns empty string or a reasonable fallback
- format_demographic_summary with age_group + gender contains both values
- format_demographic_summary with income contains income value
- build_system_prompt returns a string
- build_system_prompt contains demographic summary from the card's tags
- build_system_prompt contains the text_excerpt
- build_system_prompt contains the sector when present
- build_system_prompt still works when sector is None
- build_system_prompt still works when demographic_tags is empty
"""

import pytest
from personas.cards import PersonaCard
from personas.profiles import build_system_prompt, format_demographic_summary


# --- format_demographic_summary ---

def test_format_summary_empty_tags():
    result = format_demographic_summary({})
    assert isinstance(result, str)


def test_format_summary_age_and_gender():
    result = format_demographic_summary({"age_group": "25-34", "gender": "male"})
    assert "25-34" in result
    assert "male" in result


def test_format_summary_income():
    result = format_demographic_summary({"income_bracket": "high_income"})
    assert "high_income" in result or "high income" in result


def test_format_summary_all_fields():
    tags = {"age_group": "35-44", "gender": "female", "income_bracket": "middle_income"}
    result = format_demographic_summary(tags)
    assert "35-44" in result
    assert "female" in result
    # income should appear in some form
    assert "middle" in result or "income" in result


def test_format_summary_returns_string():
    result = format_demographic_summary({"age_group": "18-24"})
    assert isinstance(result, str)
    assert len(result) > 0


# --- build_system_prompt ---

def make_card(**kwargs) -> PersonaCard:
    defaults = dict(
        post_id=1,
        demographic_tags={"age_group": "25-34", "gender": "male"},
        text_excerpt="I think the tech industry is moving too fast.",
        sector="tech",
    )
    defaults.update(kwargs)
    return PersonaCard(**defaults)


def test_build_system_prompt_returns_string():
    card = make_card()
    result = build_system_prompt(card)
    assert isinstance(result, str)
    assert len(result) > 0


def test_build_system_prompt_contains_demographic_info():
    card = make_card(demographic_tags={"age_group": "25-34", "gender": "male"})
    result = build_system_prompt(card)
    assert "25-34" in result
    assert "male" in result


def test_build_system_prompt_contains_excerpt():
    card = make_card(text_excerpt="I love discussing politics online.")
    result = build_system_prompt(card)
    assert "I love discussing politics online." in result


def test_build_system_prompt_contains_sector():
    card = make_card(sector="financial")
    result = build_system_prompt(card)
    assert "financial" in result


def test_build_system_prompt_sector_none():
    card = make_card(sector=None)
    result = build_system_prompt(card)
    assert isinstance(result, str)
    assert len(result) > 0


def test_build_system_prompt_empty_tags():
    card = make_card(demographic_tags={})
    result = build_system_prompt(card)
    assert isinstance(result, str)
    assert len(result) > 0


def test_build_system_prompt_instructs_authentic_response():
    """The prompt should instruct the model to respond as this person."""
    card = make_card()
    result = build_system_prompt(card)
    lower = result.lower()
    # Should contain some instruction for authentic/simulated response
    assert any(word in lower for word in ["authentic", "respond", "simulat", "person", "voice"])
