"""
Tests for src.api — FastAPI endpoints for focus group sessions.

All external dependencies (DB, Claude, persona selection) are mocked.
"""

from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

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
            "response_text": "I think AI is great.",
            "model": "claude-sonnet-4-20250514",
        },
        {
            "post_id": 2,
            "persona_summary": "35-44 year old female",
            "system_prompt": "You are simulating...",
            "response_text": "I'm worried about bias.",
            "model": "claude-sonnet-4-20250514",
        },
    ]


@pytest.fixture
def mock_deps(sample_cards, sample_responses):
    """Patch all external dependencies and return the FastAPI test client."""
    with (
        patch("focus_groups.api.get_conn") as mock_get_conn,
        patch("focus_groups.api.get_client") as mock_get_client,
        patch("focus_groups.api.select_personas") as mock_select,
        patch("focus_groups.api.run_focus_group") as mock_run,
        patch("focus_groups.api.create_session") as mock_create,
        patch("focus_groups.api.save_responses") as mock_save,
        patch("focus_groups.api.complete_session") as mock_complete,
        patch("focus_groups.api.fail_session") as mock_fail,
        patch("focus_groups.api.get_session") as mock_get_session,
        patch("focus_groups.api.list_sessions") as mock_list,
    ):
        mock_get_conn.return_value = MagicMock()
        mock_get_client.return_value = MagicMock()
        mock_select.return_value = sample_cards
        mock_run.return_value = sample_responses
        mock_create.return_value = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        mock_save.return_value = 2

        from focus_groups.api import app
        client = TestClient(app)

        yield {
            "client": client,
            "get_conn": mock_get_conn,
            "get_client": mock_get_client,
            "select_personas": mock_select,
            "run_focus_group": mock_run,
            "create_session": mock_create,
            "save_responses": mock_save,
            "complete_session": mock_complete,
            "fail_session": mock_fail,
            "get_session": mock_get_session,
            "list_sessions": mock_list,
        }


# ── POST /sessions ───────────────────────────────────────────────────────────

def test_create_session_success(mock_deps):
    resp = mock_deps["client"].post("/sessions", json={
        "question": "What do you think about AI?",
        "num_personas": 2,
        "sector": "tech",
    })

    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] == "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    assert data["status"] == "completed"
    assert data["num_responses"] == 2

    mock_deps["select_personas"].assert_called_once()
    mock_deps["run_focus_group"].assert_called_once()
    mock_deps["complete_session"].assert_called_once()


def test_create_session_minimal_params(mock_deps):
    """Only question and num_personas are required."""
    resp = mock_deps["client"].post("/sessions", json={
        "question": "Test?",
        "num_personas": 3,
    })

    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] == "a1b2c3d4-e5f6-7890-abcd-ef1234567890"


def test_create_session_with_demographic_filter(mock_deps):
    resp = mock_deps["client"].post("/sessions", json={
        "question": "Test?",
        "num_personas": 2,
        "demographic_filter": {"age_group": "25-34"},
    })

    assert resp.status_code == 200
    mock_deps["select_personas"].assert_called_once()
    call_kwargs = mock_deps["select_personas"].call_args
    assert call_kwargs[1].get("demographic_filter") == {"age_group": "25-34"} or \
           call_kwargs[0][1] == {"age_group": "25-34"}


def test_create_session_no_personas_found(mock_deps):
    mock_deps["select_personas"].return_value = []

    resp = mock_deps["client"].post("/sessions", json={
        "question": "Test?",
        "num_personas": 5,
        "sector": "tech",
    })

    assert resp.status_code == 404
    assert "No personas found" in resp.json()["detail"]


def test_create_session_missing_question(mock_deps):
    resp = mock_deps["client"].post("/sessions", json={
        "num_personas": 2,
    })

    assert resp.status_code == 422


def test_create_session_claude_error_marks_failed(mock_deps):
    mock_deps["run_focus_group"].side_effect = Exception("API error")

    resp = mock_deps["client"].post("/sessions", json={
        "question": "Test?",
        "num_personas": 2,
    })

    assert resp.status_code == 500
    mock_deps["fail_session"].assert_called_once()


# ── GET /sessions/{id} ───────────────────────────────────────────────────────

def test_get_session_success(mock_deps):
    now = datetime.now(timezone.utc).isoformat()
    mock_deps["get_session"].return_value = {
        "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "sector": "tech",
        "demographic_filter": {},
        "question": "Test?",
        "num_personas": 2,
        "status": "completed",
        "created_at": now,
        "completed_at": now,
        "responses": [
            {
                "id": 1,
                "post_id": 42,
                "persona_summary": "25-34 male",
                "system_prompt": "...",
                "response_text": "Response",
                "model": "claude-sonnet-4-20250514",
                "created_at": now,
            }
        ],
    }

    resp = mock_deps["client"].get("/sessions/a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    assert len(data["responses"]) == 1


def test_get_session_not_found(mock_deps):
    mock_deps["get_session"].return_value = None

    resp = mock_deps["client"].get("/sessions/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


# ── GET /sessions ─────────────────────────────────────────────────────────────

def test_list_sessions_success(mock_deps):
    now = datetime.now(timezone.utc).isoformat()
    mock_deps["list_sessions"].return_value = [
        {"id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890", "sector": "tech", "question": "Q?", "num_personas": 2, "status": "completed", "created_at": now},
    ]

    resp = mock_deps["client"].get("/sessions")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["id"] == "a1b2c3d4-e5f6-7890-abcd-ef1234567890"


def test_list_sessions_with_limit(mock_deps):
    mock_deps["list_sessions"].return_value = []

    resp = mock_deps["client"].get("/sessions?limit=5")
    assert resp.status_code == 200
    mock_deps["list_sessions"].assert_called_once()
