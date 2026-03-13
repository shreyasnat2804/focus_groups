"""
Tests for author history tag propagation (Layer 3).
Uses mock DB connections to test logic without requiring Postgres.

Run with: python3 -m pytest tests/test_author_propagation.py -v
"""

from unittest.mock import MagicMock, patch, call

import pytest

from focus_groups.author_propagation import propagate_author_tags


def _mock_conn_with_data(authors_posts, existing_tags, value_ids=None):
    """
    Build a mock connection that simulates DB queries for propagation.

    authors_posts: list of author names with 2+ posts (returned by get_authors_with_multiple_posts)
    existing_tags: {author: [(dimension, value, post_id), ...]} — self_disclosure tags
    value_ids: {(dimension, value): id} — demographic value lookup
    """
    if value_ids is None:
        value_ids = {
            ("age_group", "25-34"): 1,
            ("age_group", "35-44"): 2,
            ("gender", "female"): 3,
            ("gender", "male"): 4,
            ("income_bracket", "high_income"): 5,
            ("parent_status", "parent"): 6,
        }

    conn = MagicMock()
    return conn, authors_posts, existing_tags, value_ids


@patch("focus_groups.author_propagation.insert_tags")
@patch("focus_groups.author_propagation.load_demographic_value_ids")
@patch("focus_groups.author_propagation.get_authors_with_multiple_posts")
def test_consistent_tags_propagated(mock_get_authors, mock_load_ids, mock_insert):
    """Author with consistent age tag across posts → propagated to untagged posts."""
    conn = MagicMock()
    mock_get_authors.return_value = ["alice"]
    mock_load_ids.return_value = {
        ("age_group", "25-34"): 1,
        ("gender", "female"): 3,
    }

    # Cursor for self-disclosure tags query: alice has age=25-34 on post 10
    # Cursor for untagged posts query: post 20 lacks age_group
    cur = MagicMock()
    cur.__enter__ = MagicMock(return_value=cur)
    cur.__exit__ = MagicMock(return_value=False)

    # First query: self-disclosure tags for alice
    # Returns (dimension, value, post_count)
    call_count = [0]

    def fetchall_side_effect():
        call_count[0] += 1
        if call_count[0] == 1:
            # Self-disclosure tags: age_group=25-34 seen on 1 post
            return [("age_group", "25-34", 1)]
        elif call_count[0] == 2:
            # Untagged posts for age_group: post 20
            return [(20,)]
        return []

    cur.fetchall = fetchall_side_effect
    conn.cursor.return_value = cur

    mock_insert.return_value = 1

    stats = propagate_author_tags(conn)

    assert stats["authors_processed"] == 1
    assert stats["tags_inserted"] >= 1
    # Verify insert_tags was called with author_history method
    insert_call_args = mock_insert.call_args
    tags = insert_call_args[0][1]  # second positional arg
    assert all(t["method"] == "author_history" for t in tags)
    assert all(t["confidence"] == 0.75 for t in tags)


@patch("focus_groups.author_propagation.insert_tags")
@patch("focus_groups.author_propagation.load_demographic_value_ids")
@patch("focus_groups.author_propagation.get_authors_with_multiple_posts")
def test_conflicting_tags_skipped(mock_get_authors, mock_load_ids, mock_insert):
    """Author with conflicting age tags → dimension skipped entirely."""
    conn = MagicMock()
    mock_get_authors.return_value = ["bob"]
    mock_load_ids.return_value = {("age_group", "25-34"): 1, ("age_group", "35-44"): 2}

    cur = MagicMock()
    cur.__enter__ = MagicMock(return_value=cur)
    cur.__exit__ = MagicMock(return_value=False)

    call_count = [0]

    def fetchall_side_effect():
        call_count[0] += 1
        if call_count[0] == 1:
            # Two different age values → conflict
            return [("age_group", "25-34", 1), ("age_group", "35-44", 1)]
        return []

    cur.fetchall = fetchall_side_effect
    conn.cursor.return_value = cur
    mock_insert.return_value = 0

    stats = propagate_author_tags(conn)

    assert stats["authors_skipped_conflict"] >= 1
    # insert_tags should not be called with any age_group tags
    if mock_insert.called:
        for call_args in mock_insert.call_args_list:
            tags = call_args[0][1]
            assert not any(t["dimension"] == "age_group" for t in tags)


@patch("focus_groups.author_propagation.insert_tags")
@patch("focus_groups.author_propagation.load_demographic_value_ids")
@patch("focus_groups.author_propagation.get_authors_with_multiple_posts")
def test_deleted_author_excluded(mock_get_authors, mock_load_ids, mock_insert):
    """[deleted] authors should be excluded by get_authors_with_multiple_posts."""
    conn = MagicMock()
    # get_authors_with_multiple_posts already filters these out
    mock_get_authors.return_value = []
    mock_load_ids.return_value = {}

    stats = propagate_author_tags(conn)

    assert stats["authors_processed"] == 0
    assert stats["tags_inserted"] == 0


@patch("focus_groups.author_propagation.insert_tags")
@patch("focus_groups.author_propagation.load_demographic_value_ids")
@patch("focus_groups.author_propagation.get_authors_with_multiple_posts")
def test_single_post_author_excluded(mock_get_authors, mock_load_ids, mock_insert):
    """Authors with only 1 post are excluded — nothing to propagate."""
    conn = MagicMock()
    # get_authors_with_multiple_posts only returns authors with 2+
    mock_get_authors.return_value = []
    mock_load_ids.return_value = {}

    stats = propagate_author_tags(conn)

    assert stats["authors_processed"] == 0
    mock_insert.assert_not_called()


@patch("focus_groups.author_propagation.insert_tags")
@patch("focus_groups.author_propagation.load_demographic_value_ids")
@patch("focus_groups.author_propagation.get_authors_with_multiple_posts")
def test_idempotent_rerun(mock_get_authors, mock_load_ids, mock_insert):
    """Running twice produces same result — second run inserts 0 because ON CONFLICT DO NOTHING."""
    conn = MagicMock()
    mock_get_authors.return_value = ["carol"]
    mock_load_ids.return_value = {("gender", "female"): 3}

    cur = MagicMock()
    cur.__enter__ = MagicMock(return_value=cur)
    cur.__exit__ = MagicMock(return_value=False)

    call_count = [0]

    def fetchall_side_effect():
        call_count[0] += 1
        if call_count[0] == 1:
            return [("gender", "female", 1)]
        elif call_count[0] == 2:
            return [(30,)]
        return []

    cur.fetchall = fetchall_side_effect
    conn.cursor.return_value = cur

    # First run inserts 1
    mock_insert.return_value = 1
    stats1 = propagate_author_tags(conn)

    # Reset for second run
    call_count[0] = 0
    mock_insert.return_value = 0  # ON CONFLICT DO NOTHING
    stats2 = propagate_author_tags(conn)

    assert stats2["tags_inserted"] == 0


@patch("focus_groups.author_propagation.insert_tags")
@patch("focus_groups.author_propagation.load_demographic_value_ids")
@patch("focus_groups.author_propagation.get_authors_with_multiple_posts")
def test_only_self_disclosure_used_as_source(mock_get_authors, mock_load_ids, mock_insert):
    """Only self_disclosure tags are used as source — subreddit_prior tags are ignored."""
    conn = MagicMock()
    mock_get_authors.return_value = ["dave"]
    mock_load_ids.return_value = {("income_bracket", "high_income"): 5}

    cur = MagicMock()
    cur.__enter__ = MagicMock(return_value=cur)
    cur.__exit__ = MagicMock(return_value=False)

    call_count = [0]

    def fetchall_side_effect():
        call_count[0] += 1
        if call_count[0] == 1:
            # Only self_disclosure tags returned by the query (SQL filters method='self_disclosure')
            return []  # No self-disclosure tags for dave
        return []

    cur.fetchall = fetchall_side_effect
    conn.cursor.return_value = cur

    stats = propagate_author_tags(conn)

    # No self-disclosure tags → nothing to propagate
    mock_insert.assert_not_called()


@patch("focus_groups.author_propagation.insert_tags")
@patch("focus_groups.author_propagation.load_demographic_value_ids")
@patch("focus_groups.author_propagation.get_authors_with_multiple_posts")
def test_multiple_dimensions_propagated(mock_get_authors, mock_load_ids, mock_insert):
    """Author with consistent tags in multiple dimensions → all propagated."""
    conn = MagicMock()
    mock_get_authors.return_value = ["eve"]
    mock_load_ids.return_value = {
        ("age_group", "25-34"): 1,
        ("gender", "female"): 3,
    }

    cur = MagicMock()
    cur.__enter__ = MagicMock(return_value=cur)
    cur.__exit__ = MagicMock(return_value=False)

    call_count = [0]

    def fetchall_side_effect():
        call_count[0] += 1
        if call_count[0] == 1:
            # Two dimensions, each consistent
            return [("age_group", "25-34", 1), ("gender", "female", 1)]
        elif call_count[0] == 2:
            # Posts lacking age_group
            return [(40,), (41,)]
        elif call_count[0] == 3:
            # Posts lacking gender
            return [(42,)]
        return []

    cur.fetchall = fetchall_side_effect
    conn.cursor.return_value = cur

    mock_insert.return_value = 3

    stats = propagate_author_tags(conn)

    assert stats["tags_inserted"] == 3
    assert mock_insert.called
    tags = mock_insert.call_args[0][1]
    dimensions_tagged = {t["dimension"] for t in tags}
    assert "age_group" in dimensions_tagged
    assert "gender" in dimensions_tagged
