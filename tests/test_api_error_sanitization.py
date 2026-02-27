"""
Tests for error sanitization — verify that 500 responses never leak
internal exception details, and that server-side logging captures them.
"""

import logging
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
    mock_conn = MagicMock()

    with (
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
        patch("focus_groups.api.update_session_name") as mock_update_name,
        patch("focus_groups.api.delete_responses") as mock_delete_resp,
    ):
        mock_get_client.return_value = MagicMock()
        mock_select.return_value = sample_cards
        mock_run.return_value = sample_responses
        mock_create.return_value = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        mock_save.return_value = 2
        mock_count.return_value = 0

        from focus_groups.api import app, get_db
        app.dependency_overrides[get_db] = lambda: mock_conn
        app.state.limiter.reset()
        client = TestClient(app, raise_server_exceptions=False)

        yield {
            "client": client,
            "conn": mock_conn,
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
            "update_session_name": mock_update_name,
            "delete_responses": mock_delete_resp,
        }

        app.dependency_overrides.clear()


# ── POST /sessions — error sanitization ──────────────────────────────────────

def test_create_session_error_hides_exception_details(mock_deps):
    """500 from create_session must NOT contain the raw exception message."""
    secret_msg = "secret_db_password_exposed_in_traceback"
    mock_deps["run_focus_group"].side_effect = Exception(secret_msg)

    resp = mock_deps["client"].post("/api/sessions", json={
        "question": "Test?",
        "num_personas": 2,
    })

    assert resp.status_code == 500
    detail = resp.json()["detail"]
    assert secret_msg not in detail
    assert "Focus group generation failed" in detail


def test_create_session_error_logs_exception(mock_deps, caplog):
    """The actual exception must be logged server-side."""
    secret_msg = "secret_db_password_exposed_in_traceback"
    mock_deps["run_focus_group"].side_effect = Exception(secret_msg)

    with caplog.at_level(logging.ERROR, logger="focus_groups.api"):
        mock_deps["client"].post("/api/sessions", json={
            "question": "Test?",
            "num_personas": 2,
        })

    assert secret_msg in caplog.text


# ── POST /sessions/{id}/rerun — error sanitization ──────────────────────────

def _setup_rerun_session(mock_deps):
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


def test_rerun_session_error_hides_exception_details(mock_deps):
    """500 from rerun must NOT contain the raw exception message."""
    _setup_rerun_session(mock_deps)
    secret_msg = "anthropic_api_key_abc123"
    mock_deps["run_focus_group"].side_effect = Exception(secret_msg)

    resp = mock_deps["client"].post(
        "/api/sessions/a1b2c3d4-e5f6-7890-abcd-ef1234567890/rerun",
        json={"question": "New?"},
    )

    assert resp.status_code == 500
    detail = resp.json()["detail"]
    assert secret_msg not in detail
    assert "Focus group re-run failed" in detail


def test_rerun_session_error_logs_exception(mock_deps, caplog):
    """The actual exception must be logged server-side."""
    _setup_rerun_session(mock_deps)
    secret_msg = "anthropic_api_key_abc123"
    mock_deps["run_focus_group"].side_effect = Exception(secret_msg)

    with caplog.at_level(logging.ERROR, logger="focus_groups.api"):
        mock_deps["client"].post(
            "/api/sessions/a1b2c3d4-e5f6-7890-abcd-ef1234567890/rerun",
            json={"question": "New?"},
        )

    assert secret_msg in caplog.text


# ── POST /sessions/{id}/wtp — error sanitization ────────────────────────────

def test_wtp_error_hides_exception_details(mock_deps):
    """500 from WTP must NOT contain the raw exception message."""
    session_id = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    mock_deps["get_session"].return_value = {
        "id": session_id,
        "question": "Product: TestApp\n\nA cool product.",
        "sector": "tech",
        "num_personas": 2,
        "demographic_filter": {},
        "status": "completed",
        "responses": [
            {"post_id": 1, "persona_summary": "25-34 male", "response_text": "Good"},
        ],
    }

    secret_msg = "internal_model_config_leak"

    with (
        patch("focus_groups.api.get_posts_by_ids", return_value=[
            {"post_id": 1, "text": "Test", "sector": "tech", "demographic_tags": {"age_group": "25-34"}},
        ]),
        patch("focus_groups.api.collect_psm_responses", side_effect=Exception(secret_msg)),
    ):
        resp = mock_deps["client"].post(
            f"/api/sessions/{session_id}/wtp",
            json={"price_points": [49, 99], "segment_by": "age_group"},
        )

    assert resp.status_code == 500
    detail = resp.json()["detail"]
    assert secret_msg not in detail
    assert "WTP analysis failed" in detail


def test_wtp_error_logs_exception(mock_deps, caplog):
    """The actual exception must be logged server-side."""
    session_id = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    mock_deps["get_session"].return_value = {
        "id": session_id,
        "question": "Product: TestApp\n\nA cool product.",
        "sector": "tech",
        "num_personas": 2,
        "demographic_filter": {},
        "status": "completed",
        "responses": [
            {"post_id": 1, "persona_summary": "25-34 male", "response_text": "Good"},
        ],
    }

    secret_msg = "internal_model_config_leak"

    with (
        patch("focus_groups.api.get_posts_by_ids", return_value=[
            {"post_id": 1, "text": "Test", "sector": "tech", "demographic_tags": {"age_group": "25-34"}},
        ]),
        patch("focus_groups.api.collect_psm_responses", side_effect=Exception(secret_msg)),
        caplog.at_level(logging.ERROR, logger="focus_groups.api"),
    ):
        mock_deps["client"].post(
            f"/api/sessions/{session_id}/wtp",
            json={"price_points": [49, 99], "segment_by": "age_group"},
        )

    assert secret_msg in caplog.text


# ── Global exception handler ────────────────────────────────────────────────

def test_unhandled_exception_returns_generic_500(mock_deps):
    """An unhandled exception in any endpoint should return a generic 500."""
    secret_msg = "unexpected_crash_details_xyz"
    mock_deps["get_session"].side_effect = RuntimeError(secret_msg)

    resp = mock_deps["client"].get("/api/sessions/some-id")

    assert resp.status_code == 500
    body = resp.json()
    assert secret_msg not in body.get("detail", "")
    assert "Internal server error" in body.get("detail", "")
