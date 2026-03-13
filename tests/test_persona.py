"""
Tests for src/persona.py

What we expect:
- mmr_select() returns exactly n items from a candidate pool
- MMR result is a subset of the input candidates
- MMR diversifies: repeated items not selected
- select_personas() returns PersonaCard objects with required fields
- PersonaCard has: post_id, demographic_tags, text_excerpt, sector
- Gracefully returns fewer personas when pool is smaller than n
"""

import math
import pytest
from unittest.mock import MagicMock, patch

from focus_groups.personas.mmr import mmr_select
from focus_groups.personas.cards import PersonaCard


# --- MMR unit tests (no DB needed) ---

def make_vecs(n: int, dim: int = 4) -> list[list[float]]:
    """Generate n orthogonal-ish unit vectors for testing."""
    import random
    random.seed(42)
    vecs = []
    for _ in range(n):
        v = [random.gauss(0, 1) for _ in range(dim)]
        norm = math.sqrt(sum(x * x for x in v))
        vecs.append([x / norm for x in v])
    return vecs


def test_mmr_returns_n_items():
    candidates = list(range(20))
    vecs = make_vecs(20)
    result = mmr_select(candidates, vecs, n=5)
    assert len(result) == 5


def test_mmr_subset_of_candidates():
    candidates = list(range(10))
    vecs = make_vecs(10)
    result = mmr_select(candidates, vecs, n=4)
    assert all(r in candidates for r in result)


def test_mmr_no_duplicates():
    candidates = list(range(10))
    vecs = make_vecs(10)
    result = mmr_select(candidates, vecs, n=6)
    assert len(result) == len(set(result))


def test_mmr_fewer_than_n():
    """When pool < n, return all candidates."""
    candidates = [1, 2, 3]
    vecs = make_vecs(3)
    result = mmr_select(candidates, vecs, n=10)
    assert len(result) == 3


def test_mmr_empty():
    result = mmr_select([], [], n=5)
    assert result == []


# --- PersonaCard structure ---

def test_persona_card_fields():
    card = PersonaCard(
        post_id=1,
        demographic_tags={"age_group": "25-34", "gender": "male"},
        text_excerpt="Sample post text here.",
        sector="tech",
    )
    assert card.post_id == 1
    assert "age_group" in card.demographic_tags
    assert isinstance(card.text_excerpt, str)
    assert card.sector == "tech"


def test_persona_card_repr():
    card = PersonaCard(
        post_id=42,
        demographic_tags={"gender": "female"},
        text_excerpt="Finance discussion.",
        sector="financial",
    )
    r = repr(card)
    assert "42" in r
