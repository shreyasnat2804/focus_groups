"""
Tests for src.sessions — session CRUD against a mock psycopg2 connection.

Uses a mock cursor that tracks SQL calls and returns canned data.
"""

from unittest.mock import MagicMock, patch, call
from datetime import datetime, timezone

import pytest

from src.sessions import (
    create_session,
    save_responses,
    complete_session,
    fail_session,
    get_session,
    list_sessions,
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
    conn, cursor = _make_conn(fetchone=(7,))

    session_id = create_session(
        conn,
        sector="tech",
        demographic_filter={"age_group": "25-34"},
        num_personas=5,
        question="What do you think about AI?",
    )

    assert session_id == 7
    cursor.execute.assert_called_once()
    sql = cursor.execute.call_args[0][0]
    assert "INSERT INTO focus_group_sessions" in sql
    assert "RETURNING id" in sql
    conn.commit.assert_called_once()


def test_create_session_passes_params():
    conn, cursor = _make_conn(fetchone=(1,))

    create_session(conn, "financial", {"gender": "female"}, 3, "Test?")

    params = cursor.execute.call_args[0][1]
    assert params[0] == "financial"
    assert params[2] == 3
    assert params[3] == "Test?"


def test_create_session_none_sector():
    conn, cursor = _make_conn(fetchone=(1,))

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

    count = save_responses(conn, session_id=7, responses=responses)

    assert count == 2
    conn.commit.assert_called_once()


def test_save_responses_empty_list():
    conn, cursor = _make_conn()

    count = save_responses(conn, session_id=1, responses=[])

    assert count == 0
    conn.commit.assert_not_called()


# ── complete_session / fail_session ───────────────────────────────────────────

def test_complete_session_sets_status():
    conn, cursor = _make_conn()

    complete_session(conn, session_id=7)

    sql = cursor.execute.call_args[0][0]
    assert "status = 'completed'" in sql
    assert "completed_at" in sql
    conn.commit.assert_called_once()


def test_fail_session_sets_status():
    conn, cursor = _make_conn()

    fail_session(conn, session_id=7)

    sql = cursor.execute.call_args[0][0]
    assert "status = 'failed'" in sql
    conn.commit.assert_called_once()


# ── get_session ───────────────────────────────────────────────────────────────

def test_get_session_returns_dict():
    now = datetime.now(timezone.utc)
    session_row = (1, "tech", {"age_group": "25-34"}, "Test?", 5, "completed", now, now)
    response_rows = [
        (10, 42, "25-34 male", "prompt...", "Response 1", "claude-sonnet-4-20250514", now),
    ]

    conn, cursor = _make_conn()
    cursor.fetchone.return_value = session_row
    cursor.fetchall.return_value = response_rows

    result = get_session(conn, session_id=1)

    assert result is not None
    assert result["id"] == 1
    assert result["sector"] == "tech"
    assert result["question"] == "Test?"
    assert result["status"] == "completed"
    assert len(result["responses"]) == 1
    assert result["responses"][0]["post_id"] == 42


def test_get_session_not_found():
    conn, cursor = _make_conn(fetchone=None)

    result = get_session(conn, session_id=999)

    assert result is None


# ── list_sessions ─────────────────────────────────────────────────────────────

def test_list_sessions_returns_list():
    now = datetime.now(timezone.utc)
    rows = [
        (1, "tech", "Test?", 5, "completed", now),
        (2, "financial", "Another?", 3, "running", now),
    ]
    conn, cursor = _make_conn(fetchall=rows)

    result = list_sessions(conn, limit=10)

    assert len(result) == 2
    assert result[0]["id"] == 1
    assert result[1]["sector"] == "financial"


def test_list_sessions_empty():
    conn, cursor = _make_conn(fetchall=[])

    result = list_sessions(conn, limit=10)

    assert result == []
