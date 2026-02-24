"""
Tests for src.claude — Claude API integration for focus group responses.

All tests mock anthropic.Anthropic so no real API calls are made.
"""

from unittest.mock import MagicMock, patch

import pytest

from focus_groups.personas.cards import PersonaCard
from focus_groups.claude import (
    MODEL,
    build_system_prompt,
    generate_persona_response,
    get_client,
    run_focus_group,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_client():
    """Return a mock Anthropic client with a canned response."""
    client = MagicMock()
    message = MagicMock()
    message.content = [MagicMock(text="I think AI hiring is risky.")]
    client.messages.create.return_value = message
    return client


@pytest.fixture
def sample_card():
    return PersonaCard(
        post_id=42,
        demographic_tags={"age_group": "25-34", "gender": "male"},
        text_excerpt="I got laid off after the AI rollout...",
        sector="tech",
    )


@pytest.fixture
def sample_cards():
    return [
        PersonaCard(
            post_id=1,
            demographic_tags={"age_group": "25-34", "gender": "male"},
            text_excerpt="Tech layoffs are brutal.",
            sector="tech",
        ),
        PersonaCard(
            post_id=2,
            demographic_tags={"age_group": "35-44", "gender": "female"},
            text_excerpt="My company just adopted AI tools.",
            sector="tech",
        ),
    ]


# ── get_client ────────────────────────────────────────────────────────────────

@patch("focus_groups.claude.anthropic")
def test_get_client_returns_anthropic_instance(mock_anthropic):
    """get_client() should instantiate anthropic.Anthropic."""
    mock_anthropic.Anthropic.return_value = MagicMock()
    client = get_client()
    mock_anthropic.Anthropic.assert_called_once()
    assert client is not None


# ── generate_persona_response ─────────────────────────────────────────────────

def test_generate_persona_response_calls_api(mock_client, sample_card):
    """Should call messages.create with correct system prompt and question."""
    result = generate_persona_response(
        mock_client, sample_card, "What do you think about AI in hiring?"
    )

    mock_client.messages.create.assert_called_once()
    call_kwargs = mock_client.messages.create.call_args[1]

    assert call_kwargs["model"] == MODEL
    assert call_kwargs["max_tokens"] == 1024
    assert "simulating a real person" in call_kwargs["system"]
    assert call_kwargs["messages"][0]["role"] == "user"
    assert "AI in hiring" in call_kwargs["messages"][0]["content"]

    assert result == "I think AI hiring is risky."


def test_generate_persona_response_uses_build_system_prompt(mock_client, sample_card):
    """System prompt should include demographic details and excerpt."""
    generate_persona_response(mock_client, sample_card, "Test?")
    call_kwargs = mock_client.messages.create.call_args[1]
    system = call_kwargs["system"]

    assert "25-34" in system
    assert "male" in system
    assert "laid off" in system


# ── run_focus_group ───────────────────────────────────────────────────────────

def test_run_focus_group_returns_list(mock_client, sample_cards):
    """Should return one response dict per card."""
    results = run_focus_group(
        mock_client, sample_cards, "What do you think about AI?"
    )

    assert len(results) == 2
    assert mock_client.messages.create.call_count == 2


def test_run_focus_group_response_shape(mock_client, sample_cards):
    """Each response should contain required fields."""
    results = run_focus_group(
        mock_client, sample_cards, "What do you think about AI?"
    )

    for r in results:
        assert "post_id" in r
        assert "persona_summary" in r
        assert "system_prompt" in r
        assert "response_text" in r
        assert "model" in r

    assert results[0]["post_id"] == 1
    assert results[1]["post_id"] == 2
    assert results[0]["model"] == MODEL


def test_run_focus_group_persona_summary(mock_client, sample_cards):
    """Persona summary should contain demographic info."""
    results = run_focus_group(
        mock_client, sample_cards, "Test?"
    )

    assert "25-34" in results[0]["persona_summary"]
    assert "35-44" in results[1]["persona_summary"]


def test_run_focus_group_empty_cards(mock_client):
    """Empty card list should return empty results."""
    results = run_focus_group(mock_client, [], "Test?")
    assert results == []
    mock_client.messages.create.assert_not_called()
