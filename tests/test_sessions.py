"""
Tests for src.sessions — session CRUD against a mock psycopg2 connection.

Uses a mock cursor that tracks SQL calls and returns canned data.
"""

from unittest.mock import MagicMock, patch, call
from datetime import datetime, timezone

import pytest

from focus_groups.sessions import (
    create_session,
    save_responses,
    complete_session,
    fail_session,
    get_session,
    list_sessions,
    count_sessions,
    update_session_question,
    delete_responses,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

_SENTINEL = object()


def _make_conn(fetchone=_SENTINEL, fetchall=_SENTINEL):
    """Build a mock connection + cursor with configurable returns."""
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    if fetchone is not _SENTINEL:
        cursor.fetchone.return_value = fetchone
    if fetchall is not _SENTINEL:
        cursor.fetchall.return_value = fetchall
    return conn, cursor


# ── create_session ────────────────────────────────────────────────────────────

def test_create_session_returns_id():
    fake_uuid = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    conn, cursor = _make_conn(fetchone=(fake_uuid,))

    session_id = create_session(
        conn,
        sector="tech",
        demographic_filter={"age_group": "25-34"},
        num_personas=5,
        question="What do you think about AI?",
    )

    assert session_id == fake_uuid
    cursor.execute.assert_called_once()
    sql = cursor.execute.call_args[0][0]
    assert "INSERT INTO focus_group_sessions" in sql
    assert "RETURNING id" in sql
    conn.commit.assert_called_once()


def test_create_session_passes_params():
    conn, cursor = _make_conn(fetchone=("b2c3d4e5-f6a7-8901-bcde-f12345678901",))

    create_session(conn, "financial", {"gender": "female"}, 3, "Test?")

    params = cursor.execute.call_args[0][1]
    assert params[0] == "financial"
    assert params[2] == "Test?"
    assert params[3] == 3


def test_create_session_none_sector():
    conn, cursor = _make_conn(fetchone=("c3d4e5f6-a7b8-9012-cdef-123456789012",))

    create_session(conn, None, {}, 5, "Q?")

    params = cursor.execute.call_args[0][1]
    assert params[0] is None


# ── save_responses ────────────────────────────────────────────────────────────

def test_save_responses_inserts_rows():
    conn, cursor = _make_conn()
    cursor.rowcount = 2

    responses = [
        {
            "post_id": 10,
            "persona_summary": "25-34 year old male",
            "system_prompt": "You are simulating...",
            "response_text": "I think AI is great.",
            "model": "claude-sonnet-4-20250514",
        },
        {
            "post_id": 20,
            "persona_summary": "35-44 year old female",
            "system_prompt": "You are simulating...",
            "response_text": "I'm worried about bias.",
            "model": "claude-sonnet-4-20250514",
        },
    ]

    count = save_responses(conn, session_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890", responses=responses)

    assert count == 2
    conn.commit.assert_called_once()


def test_save_responses_empty_list():
    conn, cursor = _make_conn()

    count = save_responses(conn, session_id="b2c3d4e5-f6a7-8901-bcde-f12345678901", responses=[])

    assert count == 0
    conn.commit.assert_not_called()


# ── complete_session / fail_session ───────────────────────────────────────────

def test_complete_session_sets_status():
    conn, cursor = _make_conn()

    complete_session(conn, session_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890")

    sql = cursor.execute.call_args[0][0]
    assert "status = 'completed'" in sql
    assert "completed_at" in sql
    conn.commit.assert_called_once()


def test_fail_session_sets_status():
    conn, cursor = _make_conn()

    fail_session(conn, session_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890")

    sql = cursor.execute.call_args[0][0]
    assert "status = 'failed'" in sql
    conn.commit.assert_called_once()


# ── get_session ───────────────────────────────────────────────────────────────

def test_get_session_returns_dict():
    now = datetime.now(timezone.utc)
    session_row = ("a1b2c3d4-e5f6-7890-abcd-ef1234567890", "tech", {"age_group": "25-34"}, "Test?", 5, "completed", now, now)
    response_rows = [
        (10, 42, "25-34 male", "prompt...", "Response 1", "claude-sonnet-4-20250514", now),
    ]

    conn, cursor = _make_conn()
    cursor.fetchone.return_value = session_row
    cursor.fetchall.return_value = response_rows

    result = get_session(conn, session_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890")

    assert result is not None
    assert result["id"] == "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    assert result["sector"] == "tech"
    assert result["question"] == "Test?"
    assert result["status"] == "completed"
    assert len(result["responses"]) == 1
    assert result["responses"][0]["post_id"] == 42


def test_get_session_not_found():
    conn, cursor = _make_conn(fetchone=None)

    result = get_session(conn, session_id="00000000-0000-0000-0000-000000000000")

    assert result is None


# ── list_sessions ─────────────────────────────────────────────────────────────

def test_list_sessions_returns_list():
    now = datetime.now(timezone.utc)
    rows = [
        ("a1b2c3d4-e5f6-7890-abcd-ef1234567890", "tech", "Test?", 5, "completed", now),
        ("b2c3d4e5-f6a7-8901-bcde-f12345678901", "financial", "Another?", 3, "running", now),
    ]
    conn, cursor = _make_conn(fetchall=rows)

    result = list_sessions(conn, limit=10)

    assert len(result) == 2
    assert result[0]["id"] == "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    assert result[1]["sector"] == "financial"


def test_list_sessions_empty():
    conn, cursor = _make_conn(fetchall=[])

    result = list_sessions(conn, limit=10)

    assert result == []


# ── list_sessions pagination ─────────────────────────────────────────────────

def test_list_sessions_with_offset():
    now = datetime.now(timezone.utc)
    rows = [
        ("c3d4e5f6-a7b8-9012-cdef-123456789012", "political", "Third?", 2, "pending", now),
    ]
    conn, cursor = _make_conn(fetchall=rows)

    result = list_sessions(conn, limit=10, offset=2)

    assert len(result) == 1
    sql = cursor.execute.call_args[0][0]
    assert "OFFSET" in sql
    params = cursor.execute.call_args[0][1]
    assert params == (10, 2)


def test_list_sessions_orders_by_created_at():
    conn, cursor = _make_conn(fetchall=[])

    list_sessions(conn, limit=10)

    sql = cursor.execute.call_args[0][0]
    assert "ORDER BY created_at DESC" in sql
    assert "ORDER BY id" not in sql


def test_list_sessions_default_offset_zero():
    conn, cursor = _make_conn(fetchall=[])

    list_sessions(conn, limit=5)

    params = cursor.execute.call_args[0][1]
    assert params == (5, 0)


def test_list_sessions_count():
    conn, cursor = _make_conn(fetchall=[])
    cursor.fetchone.return_value = (42,)

    total = count_sessions(conn)

    assert total == 42
    sql = cursor.execute.call_args[0][0]
    assert "COUNT" in sql


# ── update_session_question ──────────────────────────────────────────────────

def test_update_session_question():
    conn, cursor = _make_conn()
    sid = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"

    update_session_question(conn, sid, "New question?")

    sql = cursor.execute.call_args[0][0]
    assert "UPDATE focus_group_sessions" in sql
    assert "question" in sql
    params = cursor.execute.call_args[0][1]
    assert params == ("New question?", sid)
    conn.commit.assert_called_once()


def test_update_session_question_updates_fields():
    conn, cursor = _make_conn()
    sid = "b2c3d4e5-f6a7-8901-bcde-f12345678901"

    update_session_question(conn, sid, "Product: NewApp\n\nA cool app")

    params = cursor.execute.call_args[0][1]
    assert params[0] == "Product: NewApp\n\nA cool app"
    assert params[1] == sid


# ── delete_responses ─────────────────────────────────────────────────────────

def test_delete_responses():
    conn, cursor = _make_conn()
    sid = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"

    delete_responses(conn, sid)

    sql = cursor.execute.call_args[0][0]
    assert "DELETE FROM focus_group_responses" in sql
    assert "session_id" in sql
    params = cursor.execute.call_args[0][1]
    assert params == (sid,)
    conn.commit.assert_called_once()
