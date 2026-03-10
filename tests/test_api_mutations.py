"""
Tests for API mutation endpoints: soft delete, restore, permanent delete, rename.

Uses the same mock_deps pattern as test_api.py.
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from focus_groups.personas.cards import PersonaCard


SESSION_ID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
MISSING_ID = "00000000-0000-0000-0000-000000000000"


@pytest.fixture
def mock_deps():
    """Patch external dependencies and return the FastAPI test client."""
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
        patch("focus_groups.api.soft_delete_session") as mock_soft_delete,
        patch("focus_groups.api.restore_session") as mock_restore,
        patch("focus_groups.api.permanently_delete_session") as mock_perm_delete,
    ):
        mock_get_client.return_value = MagicMock()
        mock_count.return_value = 0

        from focus_groups.api import app, get_db
        app.dependency_overrides[get_db] = lambda: mock_conn
        app.state.limiter.reset()
        client = TestClient(app)

        yield {
            "client": client,
            "conn": mock_conn,
            "get_session": mock_get_session,
            "soft_delete_session": mock_soft_delete,
            "restore_session": mock_restore,
            "permanently_delete_session": mock_perm_delete,
            "update_session_name": mock_update_name,
        }

        app.dependency_overrides.clear()


def _session_dict(**overrides):
    """Return a minimal session dict."""
    now = datetime.now(timezone.utc).isoformat()
    base = {
        "id": SESSION_ID,
        "sector": "tech",
        "demographic_filter": {},
        "question": "Test?",
        "num_personas": 2,
        "status": "completed",
        "created_at": now,
        "completed_at": now,
        "name": None,
        "responses": [],
    }
    base.update(overrides)
    return base


# ── DELETE /api/sessions/{id} (soft delete) ──────────────────────────────────

def test_soft_delete_success(mock_deps):
    mock_deps["get_session"].return_value = _session_dict()

    resp = mock_deps["client"].delete(f"/api/sessions/{SESSION_ID}")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "deleted"
    assert data["session_id"] == SESSION_ID
    mock_deps["soft_delete_session"].assert_called_once_with(mock_deps["conn"], SESSION_ID)


def test_soft_delete_not_found(mock_deps):
    mock_deps["get_session"].return_value = None

    resp = mock_deps["client"].delete(f"/api/sessions/{MISSING_ID}")

    assert resp.status_code == 404
    mock_deps["soft_delete_session"].assert_not_called()


# ── POST /api/sessions/{id}/restore ──────────────────────────────────────────

def test_restore_success(mock_deps):
    mock_deps["get_session"].return_value = _session_dict()

    resp = mock_deps["client"].post(f"/api/sessions/{SESSION_ID}/restore")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "restored"
    assert data["session_id"] == SESSION_ID
    mock_deps["restore_session"].assert_called_once_with(mock_deps["conn"], SESSION_ID)


def test_restore_not_found(mock_deps):
    mock_deps["get_session"].return_value = None

    resp = mock_deps["client"].post(f"/api/sessions/{MISSING_ID}/restore")

    assert resp.status_code == 404
    mock_deps["restore_session"].assert_not_called()


# ── DELETE /api/sessions/{id}/permanent ──────────────────────────────────────

def test_permanent_delete_success(mock_deps):
    mock_deps["get_session"].return_value = _session_dict()

    resp = mock_deps["client"].delete(f"/api/sessions/{SESSION_ID}/permanent")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "permanently_deleted"
    assert data["session_id"] == SESSION_ID
    mock_deps["permanently_delete_session"].assert_called_once_with(mock_deps["conn"], SESSION_ID)


def test_permanent_delete_not_found(mock_deps):
    mock_deps["get_session"].return_value = None

    resp = mock_deps["client"].delete(f"/api/sessions/{MISSING_ID}/permanent")

    assert resp.status_code == 404
    mock_deps["permanently_delete_session"].assert_not_called()


# ── PATCH /api/sessions/{id}/name ────────────────────────────────────────────

def test_rename_session_success(mock_deps):
    mock_deps["get_session"].return_value = _session_dict()

    resp = mock_deps["client"].patch(
        f"/api/sessions/{SESSION_ID}/name",
        json={"name": "My Focus Group"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] == SESSION_ID
    assert data["name"] == "My Focus Group"
    mock_deps["update_session_name"].assert_called_once_with(
        mock_deps["conn"], SESSION_ID, "My Focus Group",
    )


def test_rename_session_clear_name(mock_deps):
    mock_deps["get_session"].return_value = _session_dict(name="Old Name")

    resp = mock_deps["client"].patch(
        f"/api/sessions/{SESSION_ID}/name",
        json={"name": None},
    )

    assert resp.status_code == 200
    assert resp.json()["name"] is None
    mock_deps["update_session_name"].assert_called_once()


def test_rename_session_not_found(mock_deps):
    mock_deps["get_session"].return_value = None

    resp = mock_deps["client"].patch(
        f"/api/sessions/{MISSING_ID}/name",
        json={"name": "Whatever"},
    )

    assert resp.status_code == 404
    mock_deps["update_session_name"].assert_not_called()
