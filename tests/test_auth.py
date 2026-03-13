"""
Tests for API key authentication.

Verifies:
- 401 returned when key required but missing
- 401 returned when key is wrong
- 200 returned when key matches
- Auth disabled when FG_API_KEY env var is not set
"""

from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def _mock_externals():
    """Override get_db dependency and patch session helpers so endpoints don't hit real services."""
    from focus_groups.api import app, get_db
    app.dependency_overrides[get_db] = lambda: MagicMock()
    with (
        patch("focus_groups.api.count_sessions", return_value=0),
        patch("focus_groups.api.list_sessions", return_value=[]),
        patch("focus_groups.api.purge_expired_sessions"),
    ):
        yield
    app.dependency_overrides.clear()


@pytest.fixture
def client_auth_enabled(_mock_externals):
    """TestClient with FG_API_KEY set."""
    with patch.dict("os.environ", {"FG_API_KEY": "test-secret-key"}, clear=False):
        # Re-import to pick up env change in the dependency
        from focus_groups.api import app
        app.state.limiter.reset()
        yield TestClient(app)


@pytest.fixture
def client_auth_disabled(_mock_externals):
    """TestClient with FG_API_KEY unset."""
    with patch.dict("os.environ", {}, clear=False):
        import os
        os.environ.pop("FG_API_KEY", None)
        from focus_groups.api import app
        app.state.limiter.reset()
        yield TestClient(app)


# ── Auth enabled ─────────────────────────────────────────────────────────────

def test_missing_key_returns_401(client_auth_enabled):
    resp = client_auth_enabled.get("/api/sessions")
    assert resp.status_code == 401
    assert "Invalid or missing API key" in resp.json()["detail"]


def test_wrong_key_returns_401(client_auth_enabled):
    resp = client_auth_enabled.get(
        "/api/sessions",
        headers={"X-API-Key": "wrong-key"},
    )
    assert resp.status_code == 401


def test_valid_key_returns_200(client_auth_enabled):
    resp = client_auth_enabled.get(
        "/api/sessions",
        headers={"X-API-Key": "test-secret-key"},
    )
    assert resp.status_code == 200


def test_valid_key_on_post_endpoint(client_auth_enabled):
    """Auth works on mutation endpoints too (global dependency)."""
    with (
        patch("focus_groups.api.select_personas", return_value=[]),
    ):
        resp = client_auth_enabled.post(
            "/api/sessions",
            json={"question": "Test?", "num_personas": 2},
            headers={"X-API-Key": "test-secret-key"},
        )
    # 404 because no personas, but NOT 401
    assert resp.status_code == 404


# ── Auth disabled (no FG_API_KEY env var) ────────────────────────────────────

def test_no_key_needed_when_auth_disabled(client_auth_disabled):
    resp = client_auth_disabled.get("/api/sessions")
    assert resp.status_code == 200


def test_random_key_ignored_when_auth_disabled(client_auth_disabled):
    resp = client_auth_disabled.get(
        "/api/sessions",
        headers={"X-API-Key": "anything"},
    )
    assert resp.status_code == 200
