"""
Tests for src.cli_runner — CLI interface for running focus groups.

All external dependencies are mocked.
"""

from unittest.mock import MagicMock, patch
from io import StringIO

import pytest

from focus_groups.personas.cards import PersonaCard


# ── Fixtures ──────────────────────────────────────────────────────────────────

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
            text_excerpt="My company adopted AI tools.",
            sector="tech",
        ),
    ]


@pytest.fixture
def sample_responses():
    return [
        {
            "post_id": 1,
            "persona_summary": "25-34 year old male",
            "system_prompt": "You are simulating...",
            "response_text": "I think AI is great for productivity.",
            "model": "claude-sonnet-4-20250514",
        },
        {
            "post_id": 2,
            "persona_summary": "35-44 year old female",
            "system_prompt": "You are simulating...",
            "response_text": "I'm worried about bias in hiring.",
            "model": "claude-sonnet-4-20250514",
        },
    ]


# ── run_pipeline ──────────────────────────────────────────────────────────────

@patch("focus_groups.cli_runner.get_conn")
@patch("focus_groups.cli_runner.get_client")
@patch("focus_groups.cli_runner.select_personas")
@patch("focus_groups.cli_runner.run_focus_group")
@patch("focus_groups.cli_runner.create_session")
@patch("focus_groups.cli_runner.save_responses")
@patch("focus_groups.cli_runner.complete_session")
def test_run_pipeline_full(
    mock_complete, mock_save, mock_create, mock_run, mock_select,
    mock_get_client, mock_get_conn, sample_cards, sample_responses
):
    from focus_groups.cli_runner import run_pipeline

    mock_get_conn.return_value = MagicMock()
    mock_get_client.return_value = MagicMock()
    mock_select.return_value = sample_cards
    mock_run.return_value = sample_responses
    mock_create.return_value = 1
    mock_save.return_value = 2

    output = StringIO()
    run_pipeline(
        question="What do you think about AI?",
        sector="tech",
        num_personas=2,
        save=True,
        output=output,
    )

    text = output.getvalue()
    assert "25-34 year old male" in text
    assert "35-44 year old female" in text
    assert "AI is great" in text
    assert "worried about bias" in text

    mock_select.assert_called_once()
    mock_run.assert_called_once()
    mock_create.assert_called_once()
    mock_save.assert_called_once()
    mock_complete.assert_called_once()


@patch("focus_groups.cli_runner.get_conn")
@patch("focus_groups.cli_runner.get_client")
@patch("focus_groups.cli_runner.select_personas")
@patch("focus_groups.cli_runner.run_focus_group")
@patch("focus_groups.cli_runner.create_session")
@patch("focus_groups.cli_runner.save_responses")
@patch("focus_groups.cli_runner.complete_session")
def test_run_pipeline_no_save(
    mock_complete, mock_save, mock_create, mock_run, mock_select,
    mock_get_client, mock_get_conn, sample_cards, sample_responses
):
    from focus_groups.cli_runner import run_pipeline

    mock_get_conn.return_value = MagicMock()
    mock_get_client.return_value = MagicMock()
    mock_select.return_value = sample_cards
    mock_run.return_value = sample_responses

    output = StringIO()
    run_pipeline(
        question="Test?",
        sector=None,
        num_personas=2,
        save=False,
        output=output,
    )

    mock_create.assert_not_called()
    mock_save.assert_not_called()
    mock_complete.assert_not_called()

    text = output.getvalue()
    assert "25-34 year old male" in text


@patch("focus_groups.cli_runner.get_conn")
@patch("focus_groups.cli_runner.get_client")
@patch("focus_groups.cli_runner.select_personas")
def test_run_pipeline_no_personas(
    mock_select, mock_get_client, mock_get_conn
):
    from focus_groups.cli_runner import run_pipeline

    mock_get_conn.return_value = MagicMock()
    mock_select.return_value = []

    output = StringIO()
    run_pipeline(
        question="Test?",
        sector="tech",
        num_personas=5,
        save=True,
        output=output,
    )

    text = output.getvalue()
    assert "No personas found" in text


# ── parse_args ────────────────────────────────────────────────────────────────

def test_parse_args_required():
    from focus_groups.cli_runner import parse_args

    args = parse_args(["--question", "Test?", "--num-personas", "3"])
    assert args.question == "Test?"
    assert args.num_personas == 3
    assert args.sector is None
    assert args.no_save is False


def test_parse_args_all_options():
    from focus_groups.cli_runner import parse_args

    args = parse_args([
        "--question", "Test?",
        "--sector", "financial",
        "--num-personas", "5",
        "--no-save",
    ])
    assert args.sector == "financial"
    assert args.no_save is True


def test_parse_args_missing_question():
    from focus_groups.cli_runner import parse_args

    with pytest.raises(SystemExit):
        parse_args(["--num-personas", "3"])
