"""
Tests for personas/selection.py — select_personas() with mocked DB.
"""

from unittest.mock import MagicMock, patch

import pytest

from focus_groups.personas.cards import PersonaCard
from focus_groups.personas.selection import select_personas


def _make_post(post_id: int, sector: str = "tech") -> dict:
    return {
        "post_id": post_id,
        "embedding": [float(post_id)] * 384,  # fake embedding
        "title": f"Post {post_id}",
        "text": f"Body of post {post_id} with enough text to fill excerpt",
        "sector": sector,
        "demographic_tags": {"age_group": "25-34", "gender": "male"},
    }


# ── Happy path ───────────────────────────────────────────────────────────────

@patch("focus_groups.personas.selection.get_posts_with_embeddings")
def test_happy_path_returns_persona_cards(mock_get_posts):
    posts = [_make_post(i) for i in range(10)]
    mock_get_posts.return_value = posts
    conn = MagicMock()

    cards = select_personas(conn, n=5, pool_size=100)

    assert len(cards) == 5
    assert all(isinstance(c, PersonaCard) for c in cards)
    mock_get_posts.assert_called_once_with(
        conn, demographic_filter=None, sector=None, limit=100,
    )


@patch("focus_groups.personas.selection.get_posts_with_embeddings")
def test_cards_have_correct_fields(mock_get_posts):
    posts = [_make_post(42, sector="financial")]
    mock_get_posts.return_value = posts
    conn = MagicMock()

    cards = select_personas(conn, n=1)

    card = cards[0]
    assert card.post_id == 42
    assert card.sector == "financial"
    assert card.demographic_tags == {"age_group": "25-34", "gender": "male"}
    assert len(card.text_excerpt) <= 300


# ── Fewer posts than requested ───────────────────────────────────────────────

@patch("focus_groups.personas.selection.get_posts_with_embeddings")
def test_fewer_posts_than_requested(mock_get_posts):
    """When pool has 3 posts but n=10, should return 3."""
    posts = [_make_post(i) for i in range(3)]
    mock_get_posts.return_value = posts
    conn = MagicMock()

    cards = select_personas(conn, n=10)

    assert len(cards) == 3


# ── Empty pool ───────────────────────────────────────────────────────────────

@patch("focus_groups.personas.selection.get_posts_with_embeddings")
def test_empty_pool_returns_empty(mock_get_posts):
    mock_get_posts.return_value = []
    conn = MagicMock()

    cards = select_personas(conn, n=5)

    assert cards == []


# ── Demographic filter passthrough ───────────────────────────────────────────

@patch("focus_groups.personas.selection.get_posts_with_embeddings")
def test_demographic_filter_passed_to_db(mock_get_posts):
    mock_get_posts.return_value = []
    conn = MagicMock()
    demo_filter = {"age_group": "25-34", "gender": "female"}

    select_personas(conn, demographic_filter=demo_filter, n=5)

    mock_get_posts.assert_called_once_with(
        conn, demographic_filter=demo_filter, sector=None, limit=500,
    )


# ── Sector filter passthrough ───────────────────────────────────────────────

@patch("focus_groups.personas.selection.get_posts_with_embeddings")
def test_sector_passed_to_db(mock_get_posts):
    mock_get_posts.return_value = []
    conn = MagicMock()

    select_personas(conn, sector="political", n=5)

    mock_get_posts.assert_called_once_with(
        conn, demographic_filter=None, sector="political", limit=500,
    )


# ── Excerpt length ───────────────────────────────────────────────────────────

@patch("focus_groups.personas.selection.get_posts_with_embeddings")
def test_excerpt_len_parameter(mock_get_posts):
    post = _make_post(1)
    post["text"] = "A" * 1000
    mock_get_posts.return_value = [post]
    conn = MagicMock()

    cards = select_personas(conn, n=1, excerpt_len=50)

    assert len(cards[0].text_excerpt) <= 50


# ── Pool size passthrough ────────────────────────────────────────────────────

@patch("focus_groups.personas.selection.get_posts_with_embeddings")
def test_pool_size_passed_to_db(mock_get_posts):
    mock_get_posts.return_value = []
    conn = MagicMock()

    select_personas(conn, n=5, pool_size=200)

    mock_get_posts.assert_called_once_with(
        conn, demographic_filter=None, sector=None, limit=200,
    )
