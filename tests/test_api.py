"""
Tests for src.api — FastAPI endpoints for focus group sessions.

All external dependencies (DB, Claude, persona selection) are mocked.
"""

from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from focus_groups.personas.cards import PersonaCard
from focus_groups.sessions import update_session_question, delete_responses


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
        patch("focus_groups.api.count_sessions") as mock_count,
        patch("focus_groups.api.update_session_question") as mock_update_q,
        patch("focus_groups.api.delete_responses") as mock_delete_resp,
    ):
        mock_get_conn.return_value = MagicMock()
        mock_get_client.return_value = MagicMock()
        mock_select.return_value = sample_cards
        mock_run.return_value = sample_responses
        mock_create.return_value = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        mock_save.return_value = 2
        mock_count.return_value = 0

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
            "count_sessions": mock_count,
            "update_session_question": mock_update_q,
            "delete_responses": mock_delete_resp,
        }


# ── POST /sessions ───────────────────────────────────────────────────────────

def test_create_session_success(mock_deps):
    resp = mock_deps["client"].post("/api/sessions", json={
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
    resp = mock_deps["client"].post("/api/sessions", json={
        "question": "Test?",
        "num_personas": 3,
    })

    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] == "a1b2c3d4-e5f6-7890-abcd-ef1234567890"


def test_create_session_with_demographic_filter(mock_deps):
    resp = mock_deps["client"].post("/api/sessions", json={
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

    resp = mock_deps["client"].post("/api/sessions", json={
        "question": "Test?",
        "num_personas": 5,
        "sector": "tech",
    })

    assert resp.status_code == 404
    assert "No personas found" in resp.json()["detail"]


def test_create_session_missing_question(mock_deps):
    resp = mock_deps["client"].post("/api/sessions", json={
        "num_personas": 2,
    })

    assert resp.status_code == 422


def test_create_session_claude_error_marks_failed(mock_deps):
    mock_deps["run_focus_group"].side_effect = Exception("API error")

    resp = mock_deps["client"].post("/api/sessions", json={
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

    resp = mock_deps["client"].get("/api/sessions/a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    assert len(data["responses"]) == 1


def test_get_session_not_found(mock_deps):
    mock_deps["get_session"].return_value = None

    resp = mock_deps["client"].get("/api/sessions/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


# ── GET /sessions ─────────────────────────────────────────────────────────────

def test_list_sessions_success(mock_deps):
    now = datetime.now(timezone.utc).isoformat()
    mock_deps["list_sessions"].return_value = [
        {"id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890", "sector": "tech", "question": "Q?", "num_personas": 2, "status": "completed", "created_at": now},
    ]
    mock_deps["count_sessions"].return_value = 1

    resp = mock_deps["client"].get("/api/sessions")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["id"] == "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    assert data["total"] == 1


def test_list_sessions_with_limit(mock_deps):
    mock_deps["list_sessions"].return_value = []
    mock_deps["count_sessions"].return_value = 0

    resp = mock_deps["client"].get("/api/sessions?limit=5")
    assert resp.status_code == 200
    mock_deps["list_sessions"].assert_called_once()


def test_list_sessions_returns_pagination_metadata(mock_deps):
    now = datetime.now(timezone.utc).isoformat()
    mock_deps["list_sessions"].return_value = [
        {"id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890", "sector": "tech", "question": "Q?", "num_personas": 2, "status": "completed", "created_at": now},
    ]
    mock_deps["count_sessions"].return_value = 25

    resp = mock_deps["client"].get("/api/sessions?limit=10&offset=0")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 25
    assert data["limit"] == 10
    assert data["offset"] == 0
    assert data["has_more"] is True
    assert len(data["items"]) == 1


def test_list_sessions_has_more_false_on_last_page(mock_deps):
    now = datetime.now(timezone.utc).isoformat()
    mock_deps["list_sessions"].return_value = [
        {"id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890", "sector": "tech", "question": "Q?", "num_personas": 2, "status": "completed", "created_at": now},
    ]
    mock_deps["count_sessions"].return_value = 5

    resp = mock_deps["client"].get("/api/sessions?limit=10&offset=0")
    data = resp.json()
    assert data["has_more"] is False


def test_list_sessions_with_offset(mock_deps):
    mock_deps["list_sessions"].return_value = []
    mock_deps["count_sessions"].return_value = 30

    resp = mock_deps["client"].get("/api/sessions?limit=10&offset=20")
    assert resp.status_code == 200
    data = resp.json()
    assert data["offset"] == 20
    mock_deps["list_sessions"].assert_called_once()


def test_list_sessions_clamps_offset_past_total(mock_deps):
    mock_deps["list_sessions"].return_value = []
    mock_deps["count_sessions"].return_value = 5

    resp = mock_deps["client"].get("/api/sessions?limit=10&offset=100")
    assert resp.status_code == 200
    data = resp.json()
    assert data["offset"] == 0
    assert data["has_more"] is False


def test_list_sessions_clamps_offset_to_last_page(mock_deps):
    mock_deps["list_sessions"].return_value = []
    mock_deps["count_sessions"].return_value = 25

    resp = mock_deps["client"].get("/api/sessions?limit=10&offset=100")
    assert resp.status_code == 200
    data = resp.json()
    assert data["offset"] == 20


# ── POST /sessions/{id}/rerun ────────────────────────────────────────────────

def _setup_rerun_session(mock_deps, now=None):
    """Configure mocks for rerun tests — session exists with standard fields."""
    if now is None:
        now = datetime.now(timezone.utc).isoformat()
    mock_deps["get_session"].return_value = {
        "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "sector": "tech",
        "demographic_filter": {"age_group": "25-34"},
        "question": "Old question?",
        "num_personas": 2,
        "status": "completed",
        "created_at": now,
        "completed_at": now,
        "responses": [],
    }


def test_rerun_session_success(mock_deps):
    _setup_rerun_session(mock_deps)

    resp = mock_deps["client"].post(
        "/api/sessions/a1b2c3d4-e5f6-7890-abcd-ef1234567890/rerun",
        json={"question": "New question?"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] == "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    assert data["status"] == "completed"
    assert data["num_responses"] == 2

    mock_deps["update_session_question"].assert_called_once()
    mock_deps["delete_responses"].assert_called_once()
    mock_deps["select_personas"].assert_called_once()
    mock_deps["run_focus_group"].assert_called_once()
    mock_deps["complete_session"].assert_called_once()


def test_rerun_session_with_options(mock_deps):
    """Rerun with overridden sector, demographic_filter, and num_personas."""
    _setup_rerun_session(mock_deps)

    resp = mock_deps["client"].post(
        "/api/sessions/a1b2c3d4-e5f6-7890-abcd-ef1234567890/rerun",
        json={
            "question": "Updated pitch",
            "sector": "financial",
            "num_personas": 8,
            "demographic_filter": {"gender": "female"},
        },
    )

    assert resp.status_code == 200
    # Verify select_personas was called with the overridden values
    call_kwargs = mock_deps["select_personas"].call_args
    assert call_kwargs[1]["sector"] == "financial"
    assert call_kwargs[1]["n"] == 8
    assert call_kwargs[1]["demographic_filter"] == {"gender": "female"}


def test_rerun_session_not_found(mock_deps):
    mock_deps["get_session"].return_value = None

    resp = mock_deps["client"].post(
        "/api/sessions/00000000-0000-0000-0000-000000000000/rerun",
        json={"question": "New?"},
    )

    assert resp.status_code == 404


def test_rerun_session_claude_error(mock_deps):
    _setup_rerun_session(mock_deps)
    mock_deps["run_focus_group"].side_effect = Exception("API error")

    resp = mock_deps["client"].post(
        "/api/sessions/a1b2c3d4-e5f6-7890-abcd-ef1234567890/rerun",
        json={"question": "New?"},
    )

    assert resp.status_code == 500
    mock_deps["fail_session"].assert_called_once()


def test_rerun_session_missing_question(mock_deps):
    _setup_rerun_session(mock_deps)

    resp = mock_deps["client"].post(
        "/api/sessions/a1b2c3d4-e5f6-7890-abcd-ef1234567890/rerun",
        json={},
    )

    assert resp.status_code == 422
