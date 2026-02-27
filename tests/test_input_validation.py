"""
Tests for input validation: Pydantic model constraints on SessionRequest,
RerunRequest, WtpRequest, and ILIKE wildcard escaping in sessions.py.
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def client():
    """Return a TestClient with all external deps mocked."""
    mock_conn = MagicMock()

    with (
        patch("focus_groups.api.get_client") as mock_get_client,
        patch("focus_groups.api.select_personas") as mock_select,
        patch("focus_groups.api.run_focus_group") as mock_run,
        patch("focus_groups.api.create_session") as mock_create,
        patch("focus_groups.api.save_responses"),
        patch("focus_groups.api.complete_session"),
        patch("focus_groups.api.fail_session"),
        patch("focus_groups.api.get_session") as mock_get_session,
        patch("focus_groups.api.list_sessions") as mock_list,
        patch("focus_groups.api.count_sessions") as mock_count,
        patch("focus_groups.api.update_session_question"),
        patch("focus_groups.api.update_session_name"),
        patch("focus_groups.api.delete_responses"),
    ):
        mock_get_client.return_value = MagicMock()
        mock_select.return_value = [MagicMock()]
        mock_run.return_value = [
            {
                "post_id": 1,
                "persona_summary": "test",
                "system_prompt": "test",
                "response_text": "test",
                "model": "test",
            }
        ]
        mock_create.return_value = "test-session-id"
        mock_count.return_value = 5
        mock_list.return_value = []
        mock_get_session.return_value = {
            "id": "test-session-id",
            "sector": "tech",
            "demographic_filter": {},
            "question": "old question",
            "num_personas": 5,
            "status": "completed",
            "created_at": "2026-01-01",
            "completed_at": "2026-01-01",
            "name": None,
            "responses": [{"post_id": 1}],
        }

        from focus_groups.api import app, get_db

        app.dependency_overrides[get_db] = lambda: mock_conn
        app.state.limiter.reset()
        yield TestClient(app)
        app.dependency_overrides.clear()


HEADERS = {"X-API-Key": "test-key"}


# ── SessionRequest validation ─────────────────────────────────────────────────

class TestSessionRequestValidation:
    """Validate SessionRequest constraints on num_personas, question, and sector."""

    def test_num_personas_zero_rejected(self, client):
        resp = client.post(
            "/api/sessions",
            json={"question": "What do you think?", "num_personas": 0},
            headers=HEADERS,
        )
        assert resp.status_code == 422

    def test_num_personas_negative_rejected(self, client):
        resp = client.post(
            "/api/sessions",
            json={"question": "What do you think?", "num_personas": -1},
            headers=HEADERS,
        )
        assert resp.status_code == 422

    def test_num_personas_above_max_rejected(self, client):
        resp = client.post(
            "/api/sessions",
            json={"question": "What do you think?", "num_personas": 51},
            headers=HEADERS,
        )
        assert resp.status_code == 422

    def test_empty_question_rejected(self, client):
        resp = client.post(
            "/api/sessions",
            json={"question": "", "num_personas": 5},
            headers=HEADERS,
        )
        assert resp.status_code == 422

    def test_question_too_long_rejected(self, client):
        resp = client.post(
            "/api/sessions",
            json={"question": "x" * 2001, "num_personas": 5},
            headers=HEADERS,
        )
        assert resp.status_code == 422

    def test_invalid_sector_rejected(self, client):
        resp = client.post(
            "/api/sessions",
            json={"question": "What do you think?", "num_personas": 5, "sector": "invalid"},
            headers=HEADERS,
        )
        assert resp.status_code == 422

    def test_valid_request_accepted(self, client):
        resp = client.post(
            "/api/sessions",
            json={"question": "What do you think?", "num_personas": 5, "sector": "tech"},
            headers=HEADERS,
        )
        assert resp.status_code == 200

    def test_valid_request_no_sector_accepted(self, client):
        resp = client.post(
            "/api/sessions",
            json={"question": "What do you think?", "num_personas": 5},
            headers=HEADERS,
        )
        assert resp.status_code == 200

    def test_num_personas_at_max_accepted(self, client):
        resp = client.post(
            "/api/sessions",
            json={"question": "What do you think?", "num_personas": 50},
            headers=HEADERS,
        )
        assert resp.status_code == 200

    def test_question_at_max_length_accepted(self, client):
        resp = client.post(
            "/api/sessions",
            json={"question": "x" * 2000, "num_personas": 5},
            headers=HEADERS,
        )
        assert resp.status_code == 200


# ── RerunRequest validation ───────────────────────────────────────────────────

class TestRerunRequestValidation:
    """Validate RerunRequest constraints."""

    def test_rerun_num_personas_zero_rejected(self, client):
        resp = client.post(
            "/api/sessions/test-session-id/rerun",
            json={"question": "New question?", "num_personas": 0},
            headers=HEADERS,
        )
        assert resp.status_code == 422

    def test_rerun_num_personas_above_max_rejected(self, client):
        resp = client.post(
            "/api/sessions/test-session-id/rerun",
            json={"question": "New question?", "num_personas": 51},
            headers=HEADERS,
        )
        assert resp.status_code == 422

    def test_rerun_empty_question_rejected(self, client):
        resp = client.post(
            "/api/sessions/test-session-id/rerun",
            json={"question": ""},
            headers=HEADERS,
        )
        assert resp.status_code == 422

    def test_rerun_question_too_long_rejected(self, client):
        resp = client.post(
            "/api/sessions/test-session-id/rerun",
            json={"question": "x" * 2001},
            headers=HEADERS,
        )
        assert resp.status_code == 422

    def test_rerun_invalid_sector_rejected(self, client):
        resp = client.post(
            "/api/sessions/test-session-id/rerun",
            json={"question": "New question?", "sector": "invalid"},
            headers=HEADERS,
        )
        assert resp.status_code == 422

    def test_rerun_valid_request_accepted(self, client):
        resp = client.post(
            "/api/sessions/test-session-id/rerun",
            json={"question": "New question?", "sector": "financial", "num_personas": 10},
            headers=HEADERS,
        )
        assert resp.status_code == 200


# ── WtpRequest validation ────────────────────────────────────────────────────

class TestWtpRequestValidation:
    """Validate WtpRequest.segment_by is restricted to known demographic dimensions."""

    def test_invalid_segment_by_rejected(self, client):
        resp = client.post(
            "/api/sessions/test-session-id/wtp",
            json={"segment_by": "ssn"},
            headers=HEADERS,
        )
        assert resp.status_code == 422

    def test_valid_segment_by_values(self, client):
        for val in ["age_group", "gender", "income_bracket", "education_level", "region"]:
            from focus_groups.api import WtpRequest
            model = WtpRequest(segment_by=val)
            assert model.segment_by == val


# ── ILIKE wildcard escaping ───────────────────────────────────────────────────

class TestIlikeEscaping:
    """Ensure ILIKE wildcards in search are escaped to prevent wildcard injection."""

    def test_percent_escaped_in_search(self):
        from focus_groups.sessions import _build_filter_clause

        where, params = _build_filter_clause(search="100%off")
        assert r"\%" in params[0]
        assert "ESCAPE" in where

    def test_underscore_escaped_in_search(self):
        from focus_groups.sessions import _build_filter_clause

        where, params = _build_filter_clause(search="my_search")
        assert r"\_" in params[0]
        assert "ESCAPE" in where

    def test_normal_search_unaffected(self):
        from focus_groups.sessions import _build_filter_clause

        where, params = _build_filter_clause(search="normal search")
        assert params[0] == "%normal search%"

    def test_both_wildcards_escaped(self):
        from focus_groups.sessions import _build_filter_clause

        where, params = _build_filter_clause(search="50%_off")
        assert r"\%" in params[0]
        assert r"\_" in params[0]
