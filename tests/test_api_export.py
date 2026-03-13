"""
Tests for export API endpoints — GET /sessions/{id}/export/csv and /export/pdf.

All external dependencies are mocked (same pattern as test_api.py).
"""

from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def sample_session():
    now = datetime.now(timezone.utc).isoformat()
    return {
        "id": 1,
        "sector": "tech",
        "demographic_filter": {},
        "question": "What do you think about AI?",
        "num_personas": 2,
        "status": "completed",
        "created_at": now,
        "completed_at": now,
        "responses": [
            {
                "id": 1,
                "post_id": 42,
                "persona_summary": "25-34 year old male",
                "system_prompt": "You are simulating...",
                "response_text": "I think AI is great.",
                "model": "claude-sonnet-4-20250514",
                "created_at": now,
            },
        ],
    }


@pytest.fixture
def mock_deps(sample_session):
    """Override get_db dependency and patch get_session, return the FastAPI test client."""
    mock_conn = MagicMock()

    with (
        patch("focus_groups.api.get_session") as mock_get_session,
    ):
        mock_get_session.return_value = sample_session

        from focus_groups.api import app, get_db
        app.dependency_overrides[get_db] = lambda: mock_conn
        app.state.limiter.reset()
        client = TestClient(app)

        yield {
            "client": client,
            "conn": mock_conn,
            "get_session": mock_get_session,
        }

        app.dependency_overrides.clear()


# ── CSV endpoint ─────────────────────────────────────────────────────────────

def test_export_csv_returns_200(mock_deps):
    resp = mock_deps["client"].get("/api/sessions/1/export/csv")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert "attachment" in resp.headers.get("content-disposition", "")


def test_export_csv_content(mock_deps):
    resp = mock_deps["client"].get("/api/sessions/1/export/csv")
    text = resp.text
    assert "response_id" in text
    assert "25-34 year old male" in text


def test_export_csv_session_not_found(mock_deps):
    mock_deps["get_session"].return_value = None
    resp = mock_deps["client"].get("/api/sessions/999/export/csv")
    assert resp.status_code == 404


# ── PDF endpoint ─────────────────────────────────────────────────────────────

def test_export_pdf_returns_200(mock_deps):
    resp = mock_deps["client"].get("/api/sessions/1/export/pdf")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert "attachment" in resp.headers.get("content-disposition", "")


def test_export_pdf_content(mock_deps):
    resp = mock_deps["client"].get("/api/sessions/1/export/pdf")
    assert resp.content[:5] == b"%PDF-"


def test_export_pdf_session_not_found(mock_deps):
    mock_deps["get_session"].return_value = None
    resp = mock_deps["client"].get("/api/sessions/999/export/pdf")
    assert resp.status_code == 404
