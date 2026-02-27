"""
Tests for remove_megathreads.py — megathread detection and removal from DB + JSONL.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

MODULE = "focus_groups.remove_megathreads"


def _make_jsonl_file(posts: list[dict], tmp_path: Path) -> Path:
    """Write posts to a temp JSONL file and return its path."""
    fpath = tmp_path / "posts.jsonl"
    with open(fpath, "w") as f:
        for p in posts:
            f.write(json.dumps(p) + "\n")
    return fpath


# ── Detection: recurring megathreads found ───────────────────────────────────

@patch(f"{MODULE}.get_conn")
def test_detects_and_deletes_megathreads(mock_get_conn, tmp_path):
    """Posts with duplicate (subreddit, title) are identified and deleted."""
    mock_conn = MagicMock()
    mock_get_conn.return_value = mock_conn
    mock_cur = MagicMock()
    mock_conn.cursor.return_value = mock_cur

    # DB returns 3 posts belonging to 1 recurring megathread title
    mock_cur.fetchall.return_value = [
        ("src_1", "news", "Weekly Discussion", 3),
        ("src_2", "news", "Weekly Discussion", 3),
        ("src_3", "news", "Weekly Discussion", 3),
    ]
    mock_cur.rowcount = 3

    # Create JSONL with 5 posts: 3 megathreads + 2 normal
    posts = [
        {"id": "src_1", "title": "Weekly Discussion", "subreddit": "news"},
        {"id": "src_2", "title": "Weekly Discussion", "subreddit": "news"},
        {"id": "src_3", "title": "Weekly Discussion", "subreddit": "news"},
        {"id": "src_4", "title": "Unique Post", "subreddit": "tech"},
        {"id": "src_5", "title": "Another Unique", "subreddit": "tech"},
    ]
    data_file = _make_jsonl_file(posts, tmp_path)

    with patch(f"{MODULE}.DATA_FILE", data_file):
        from focus_groups.remove_megathreads import main
        main()

    # Verify DELETE query was run with the 3 source IDs
    delete_call = mock_cur.execute.call_args_list[1]
    assert "DELETE FROM posts" in delete_call[0][0]
    assert set(delete_call[0][1][0]) == {"src_1", "src_2", "src_3"}
    mock_conn.commit.assert_called_once()

    # Verify JSONL was rewritten with only the 2 non-megathread posts
    with open(data_file) as f:
        remaining = [json.loads(line) for line in f]
    assert len(remaining) == 2
    remaining_ids = {p["id"] for p in remaining}
    assert remaining_ids == {"src_4", "src_5"}


# ── No megathreads found ────────────────────────────────────────────────────

@patch(f"{MODULE}.get_conn")
def test_no_megathreads_no_delete(mock_get_conn, tmp_path):
    """When no recurring titles exist, nothing is deleted."""
    mock_conn = MagicMock()
    mock_get_conn.return_value = mock_conn
    mock_cur = MagicMock()
    mock_conn.cursor.return_value = mock_cur
    mock_cur.fetchall.return_value = []

    posts = [
        {"id": "a", "title": "Unique 1", "subreddit": "sub1"},
        {"id": "b", "title": "Unique 2", "subreddit": "sub2"},
    ]
    data_file = _make_jsonl_file(posts, tmp_path)

    with patch(f"{MODULE}.DATA_FILE", data_file):
        from focus_groups.remove_megathreads import main
        main()

    # Only the SELECT query should have run, no DELETE
    assert mock_cur.execute.call_count == 1
    mock_conn.commit.assert_not_called()

    # JSONL unchanged
    with open(data_file) as f:
        remaining = [json.loads(line) for line in f]
    assert len(remaining) == 2


# ── JSONL rewrite preserves non-deleted posts exactly ────────────────────────

@patch(f"{MODULE}.get_conn")
def test_jsonl_rewrite_preserves_content(mock_get_conn, tmp_path):
    """Rewritten JSONL preserves the exact content of kept posts."""
    mock_conn = MagicMock()
    mock_get_conn.return_value = mock_conn
    mock_cur = MagicMock()
    mock_conn.cursor.return_value = mock_cur

    mock_cur.fetchall.return_value = [
        ("del_1", "sub", "Mega Thread", 2),
        ("del_2", "sub", "Mega Thread", 2),
    ]
    mock_cur.rowcount = 2

    kept_post = {"id": "keep_1", "title": "Important Post", "subreddit": "tech", "extra_field": 42}
    posts = [
        {"id": "del_1", "title": "Mega Thread", "subreddit": "sub"},
        kept_post,
        {"id": "del_2", "title": "Mega Thread", "subreddit": "sub"},
    ]
    data_file = _make_jsonl_file(posts, tmp_path)

    with patch(f"{MODULE}.DATA_FILE", data_file):
        from focus_groups.remove_megathreads import main
        main()

    with open(data_file) as f:
        remaining = [json.loads(line) for line in f]
    assert len(remaining) == 1
    assert remaining[0] == kept_post


# ── Postgres DELETE with correct source IDs ──────────────────────────────────

@patch(f"{MODULE}.get_conn")
def test_postgres_delete_uses_any_array(mock_get_conn, tmp_path):
    """DELETE query should use ANY(%s) with the source_ids list."""
    mock_conn = MagicMock()
    mock_get_conn.return_value = mock_conn
    mock_cur = MagicMock()
    mock_conn.cursor.return_value = mock_cur

    mock_cur.fetchall.return_value = [
        ("x1", "s", "T", 2),
        ("x2", "s", "T", 2),
    ]
    mock_cur.rowcount = 2

    data_file = _make_jsonl_file(
        [{"id": "x1", "title": "T"}, {"id": "x2", "title": "T"}],
        tmp_path,
    )

    with patch(f"{MODULE}.DATA_FILE", data_file):
        from focus_groups.remove_megathreads import main
        main()

    # Second execute call is the DELETE
    delete_call = mock_cur.execute.call_args_list[1]
    query = delete_call[0][0]
    params = delete_call[0][1]
    assert "DELETE FROM posts WHERE source_id = ANY" in query
    assert set(params[0]) == {"x1", "x2"}
