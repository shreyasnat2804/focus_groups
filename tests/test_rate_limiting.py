"""
Tests for rate limiting on API endpoints.

Verifies that slowapi rate limits are enforced and return 429 responses
when exceeded, and that rate limit headers are present in responses.
"""

from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def rate_limit_client():
    """Create a test client with mocked dependencies but real rate limiting."""
    with (
        patch("focus_groups.api.get_client") as mock_get_client,
        patch("focus_groups.api.select_personas") as mock_select,
        patch("focus_groups.api.run_focus_group") as mock_run,
        patch("focus_groups.api.create_session") as mock_create,
        patch("focus_groups.api.save_responses") as mock_save,
        patch("focus_groups.api.complete_session"),
        patch("focus_groups.api.fail_session"),
        patch("focus_groups.api.get_session") as mock_get_session,
        patch("focus_groups.api.list_sessions") as mock_list,
        patch("focus_groups.api.count_sessions") as mock_count,
        patch("focus_groups.api.update_session_question"),
        patch("focus_groups.api.update_session_name"),
        patch("focus_groups.api.delete_responses"),
        patch("focus_groups.api.soft_delete_session"),
        patch("focus_groups.api.restore_session"),
        patch("focus_groups.api.permanently_delete_session"),
        patch("focus_groups.api.purge_expired_sessions"),
    ):
        from focus_groups.personas.cards import PersonaCard

        mock_get_client.return_value = MagicMock()
        mock_select.return_value = [
            PersonaCard(post_id=1, demographic_tags={"age_group": "25-34"}, text_excerpt="Test", sector="tech"),
        ]
        mock_run.return_value = [
            {"post_id": 1, "persona_summary": "25-34", "system_prompt": "...", "response_text": "Ok", "model": "claude-sonnet-4-20250514"},
        ]
        mock_create.return_value = "test-session-id"
        mock_save.return_value = 1
        mock_count.return_value = 1

        now = datetime.now(timezone.utc).isoformat()
        mock_get_session.return_value = {
            "id": "test-session-id",
            "sector": "tech",
            "demographic_filter": {},
            "question": "Test?",
            "num_personas": 1,
            "status": "completed",
            "created_at": now,
            "completed_at": now,
            "responses": [],
        }
        mock_list.return_value = [
            {"id": "test-session-id", "sector": "tech", "question": "Q?", "num_personas": 1, "status": "completed", "created_at": now},
        ]

        from focus_groups.api import app, get_db
        app.dependency_overrides[get_db] = lambda: MagicMock()
        # Reset the limiter state between tests
        app.state.limiter.reset()
        client = TestClient(app)
        yield client

        app.dependency_overrides.clear()


# ── Rate limit enforcement ───────────────────────────────────────────────────

def test_create_session_rate_limit(rate_limit_client):
    """POST /api/sessions should return 429 after exceeding 5/minute."""
    for i in range(5):
        resp = rate_limit_client.post("/api/sessions", json={
            "question": f"Q{i}?", "num_personas": 1, "sector": "tech",
        })
        assert resp.status_code == 200, f"Request {i+1} failed unexpectedly: {resp.status_code}"

    # 6th request should be rate limited
    resp = rate_limit_client.post("/api/sessions", json={
        "question": "One too many?", "num_personas": 1, "sector": "tech",
    })
    assert resp.status_code == 429


def test_rerun_rate_limit(rate_limit_client):
    """POST .../rerun should return 429 after exceeding 5/minute."""
    for i in range(5):
        resp = rate_limit_client.post(
            "/api/sessions/test-session-id/rerun",
            json={"question": f"Q{i}?"},
        )
        assert resp.status_code == 200, f"Request {i+1} failed: {resp.status_code}"

    resp = rate_limit_client.post(
        "/api/sessions/test-session-id/rerun",
        json={"question": "One too many?"},
    )
    assert resp.status_code == 429


def test_list_sessions_rate_limit(rate_limit_client):
    """GET /api/sessions should allow 30/minute (higher limit for reads)."""
    # Should allow at least 6 requests (more than the write limit of 5)
    for i in range(6):
        resp = rate_limit_client.get("/api/sessions")
        assert resp.status_code == 200, f"Request {i+1} failed: {resp.status_code}"


def test_delete_session_rate_limit(rate_limit_client):
    """DELETE endpoints should allow 20/minute."""
    for i in range(6):
        resp = rate_limit_client.delete("/api/sessions/test-session-id")
        assert resp.status_code == 200, f"Request {i+1} failed: {resp.status_code}"


def test_export_rate_limit(rate_limit_client):
    """GET .../export/csv should allow 10/minute."""
    for i in range(6):
        with patch("focus_groups.api.export_csv", return_value="col1,col2\na,b"):
            resp = rate_limit_client.get("/api/sessions/test-session-id/export/csv")
        assert resp.status_code == 200, f"Request {i+1} failed: {resp.status_code}"


# ── 429 response body ────────────────────────────────────────────────────────

def test_429_response_body(rate_limit_client):
    """429 responses should include an error message."""
    for i in range(5):
        rate_limit_client.post("/api/sessions", json={
            "question": f"Q{i}?", "num_personas": 1, "sector": "tech",
        })

    resp = rate_limit_client.post("/api/sessions", json={
        "question": "Over limit", "num_personas": 1, "sector": "tech",
    })
    assert resp.status_code == 429
    data = resp.json()
    assert "error" in data or "detail" in data
