"""
Integration tests for export against real DB data.

Creates sessions + responses in DB, then verifies CSV/PDF export output.
"""

import uuid
from datetime import datetime, timezone

import pytest

from focus_groups.db import get_conn, insert_posts, get_post_ids_by_source_ids
from focus_groups.export import export_csv, export_pdf
from focus_groups.sessions import create_session, save_responses, complete_session, get_session


@pytest.fixture(scope="module")
def conn():
    """Single DB connection for the entire module. Skip if DB unreachable or tables missing."""
    try:
        c = get_conn()
    except Exception as exc:
        pytest.skip(f"Postgres not available: {exc}")

    try:
        with c.cursor() as cur:
            cur.execute("SELECT 1 FROM focus_group_sessions LIMIT 0")
    except Exception as exc:
        c.rollback()
        c.close()
        pytest.skip(f"focus_group_sessions table not available: {exc}")

    yield c
    c.close()


def _insert_test_post(conn) -> int:
    source_id = f"exp_{uuid.uuid4().hex[:10]}"
    post = {
        "id": source_id,
        "sector": "tech",
        "subreddit": "testsubreddit",
        "title": f"Export test {source_id}",
        "selftext": "Export integration test content.",
        "author": "testuser",
        "score": 1,
        "num_comments": 0,
        "created_utc": datetime.now(timezone.utc).timestamp(),
        "permalink": f"/r/test/{source_id}",
        "scraped_at": datetime.now(timezone.utc).isoformat(),
    }
    insert_posts(conn, [post])
    id_map = get_post_ids_by_source_ids(conn, [source_id])
    return id_map[source_id]


@pytest.fixture(scope="module")
def session_with_responses(conn):
    """Create a session with responses in the real DB and return the session dict."""
    post_id = _insert_test_post(conn)
    sid = create_session(conn, "tech", {}, 1, "Export integration test?")
    save_responses(conn, sid, [
        {
            "post_id": post_id,
            "persona_summary": "25-34 year old male",
            "system_prompt": "You are simulating...",
            "response_text": "This is an export integration test response.",
            "model": "test-model",
        },
    ])
    complete_session(conn, sid)
    return get_session(conn, sid)


def test_export_csv_from_db(session_with_responses):
    result = export_csv(session_with_responses)
    assert isinstance(result, str)
    assert "response_id" in result
    assert "25-34 year old male" in result
    assert "export integration test response" in result.lower()
    assert "# question: Export integration test?" in result


def test_export_pdf_from_db(session_with_responses):
    result = export_pdf(session_with_responses)
    assert isinstance(result, bytes)
    assert result[:5] == b"%PDF-"
    assert len(result) > 500  # non-trivial PDF with content
