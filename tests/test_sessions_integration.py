"""
Integration tests for session CRUD — requires Docker Postgres running.
Run with: python3 -m pytest tests/test_sessions_integration.py -v

Follows test_db.py pattern: module-scoped conn, pytest.skip if unreachable,
unique data via uuid.
"""

import uuid
from datetime import datetime, timezone

import pytest

from focus_groups.db import get_conn, insert_posts, get_post_ids_by_source_ids
from focus_groups.sessions import (
    create_session,
    complete_session,
    fail_session,
    get_session,
    list_sessions,
    save_responses,
)


@pytest.fixture(scope="module")
def conn():
    """Single DB connection for the entire module. Skip if DB unreachable or tables missing."""
    try:
        c = get_conn()
    except Exception as exc:
        pytest.skip(f"Postgres not available: {exc}")

    # Verify the sessions table exists
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
    """Insert a minimal post and return its DB id (needed for response FK)."""
    source_id = f"test_{uuid.uuid4().hex[:10]}"
    post = {
        "id": source_id,
        "sector": "test",
        "subreddit": "testsubreddit",
        "title": f"Test post {source_id}",
        "selftext": "Integration test content.",
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


# ── Session CRUD ─────────────────────────────────────────────────────────────

def test_create_session_roundtrip(conn):
    """create → get, verify dict shape."""
    sid = create_session(conn, "tech", {"age_group": "25-34"}, 3, "Test question?")
    conn.commit()
    session = get_session(conn, sid)

    assert session is not None
    assert str(session["id"]) == sid
    assert session["sector"] == "tech"
    assert session["question"] == "Test question?"
    assert session["num_personas"] == 3
    assert session["status"] == "pending"
    assert session["demographic_filter"] == {"age_group": "25-34"}
    assert isinstance(session["responses"], list)


def test_complete_session_updates_status(conn):
    sid = create_session(conn, None, {}, 5, "Complete test?")
    conn.commit()
    complete_session(conn, sid)
    conn.commit()

    session = get_session(conn, sid)
    assert session["status"] == "completed"
    assert session["completed_at"] is not None


def test_fail_session_updates_status(conn):
    sid = create_session(conn, None, {}, 5, "Fail test?")
    conn.commit()
    fail_session(conn, sid)

    session = get_session(conn, sid)
    assert session["status"] == "failed"
    assert session["completed_at"] is not None


def test_save_and_retrieve_responses(conn):
    """Insert a test post (FK), create session, save responses, verify."""
    post_id = _insert_test_post(conn)
    sid = create_session(conn, "tech", {}, 1, "Response test?")
    conn.commit()

    responses = [
        {
            "post_id": post_id,
            "persona_summary": "25-34 year old male",
            "system_prompt": "You are simulating...",
            "response_text": "Integration test response.",
            "model": "test-model",
        },
    ]
    n = save_responses(conn, sid, responses)
    conn.commit()
    assert n == 1

    session = get_session(conn, sid)
    assert len(session["responses"]) == 1
    assert session["responses"][0]["persona_summary"] == "25-34 year old male"
    assert session["responses"][0]["response_text"] == "Integration test response."


def test_list_sessions_includes_new(conn):
    sid = create_session(conn, "tech", {}, 2, f"List test {uuid.uuid4().hex[:6]}?")
    conn.commit()
    sessions = list_sessions(conn, limit=100)

    session_ids = [str(s["id"]) for s in sessions]
    assert sid in session_ids


def test_list_sessions_respects_limit(conn):
    # Create a few sessions to ensure there's data
    for i in range(3):
        create_session(conn, None, {}, 1, f"Limit test {uuid.uuid4().hex[:6]}?")
    conn.commit()

    sessions = list_sessions(conn, limit=2)
    assert len(sessions) <= 2
