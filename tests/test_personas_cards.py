"""
Tests for personas/cards.py

What we expect:
- PersonaCard stores all four fields: post_id, demographic_tags, text_excerpt, sector
- __repr__ contains the post_id and sector
- text_excerpt is stored as-is (truncation happens in selection.py, not in the dataclass)
- sector can be None
- demographic_tags can be empty
"""

import pytest
from personas.cards import PersonaCard


def test_persona_card_all_fields():
    card = PersonaCard(
        post_id=7,
        demographic_tags={"age_group": "25-34", "gender": "male"},
        text_excerpt="Some post text about tech.",
        sector="tech",
    )
    assert card.post_id == 7
    assert card.demographic_tags == {"age_group": "25-34", "gender": "male"}
    assert card.text_excerpt == "Some post text about tech."
    assert card.sector == "tech"


def test_persona_card_sector_none():
    card = PersonaCard(
        post_id=99,
        demographic_tags={},
        text_excerpt="Generic text.",
        sector=None,
    )
    assert card.sector is None


def test_persona_card_empty_tags():
    card = PersonaCard(
        post_id=5,
        demographic_tags={},
        text_excerpt="Text here.",
        sector="financial",
    )
    assert card.demographic_tags == {}


def test_persona_card_repr_contains_post_id():
    card = PersonaCard(
        post_id=42,
        demographic_tags={"gender": "female"},
        text_excerpt="Finance discussion.",
        sector="financial",
    )
    r = repr(card)
    assert "42" in r


def test_persona_card_repr_contains_sector():
    card = PersonaCard(
        post_id=10,
        demographic_tags={},
        text_excerpt="Political text.",
        sector="political",
    )
    r = repr(card)
    assert "political" in r


def test_persona_card_long_excerpt_stored_fully():
    """Cards store whatever excerpt text is given; truncation is caller's job."""
    long_text = "x" * 500
    card = PersonaCard(
        post_id=1,
        demographic_tags={},
        text_excerpt=long_text,
        sector=None,
    )
    assert card.text_excerpt == long_text


def test_persona_card_repr_truncates_excerpt_in_display():
    """Repr should not blow up on a very long excerpt."""
    long_text = "word " * 200
    card = PersonaCard(
        post_id=3,
        demographic_tags={},
        text_excerpt=long_text,
        sector="tech",
    )
    r = repr(card)
    assert "3" in r
    assert len(r) < 500  # repr is a summary, not the full text
