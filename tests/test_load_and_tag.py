"""
Tests for load_and_tag.py — batch JSONL loading + demographic tagging pipeline.
"""

import json
import textwrap
from unittest.mock import MagicMock, mock_open, patch, call

import pytest

MODULE = "focus_groups.load_and_tag"


def _make_post(source_id: str, title: str = "title", selftext: str = "body", subreddit: str = "test"):
    return {"id": source_id, "title": title, "selftext": selftext, "subreddit": subreddit}


def _posts_to_jsonl(posts: list[dict]) -> str:
    return "\n".join(json.dumps(p) for p in posts)


# ── Happy path ───────────────────────────────────────────────────────────────

@patch(f"{MODULE}.insert_tags")
@patch(f"{MODULE}.tag_post")
@patch(f"{MODULE}.get_post_ids_by_source_ids")
@patch(f"{MODULE}.insert_posts")
@patch(f"{MODULE}.load_demographic_value_ids")
@patch(f"{MODULE}.get_conn")
def test_happy_path_three_posts(
    mock_conn, mock_load_vals, mock_insert, mock_id_map, mock_tag, mock_insert_tags,
):
    posts = [_make_post(f"p{i}") for i in range(3)]
    jsonl = _posts_to_jsonl(posts)

    mock_conn.return_value = MagicMock()
    mock_load_vals.return_value = {"age_group": {}}
    mock_insert.return_value = 3
    mock_id_map.return_value = {"p0": 100, "p1": 101, "p2": 102}
    mock_tag.return_value = [{"dimension": "age_group", "value": "25-34", "confidence": 0.9, "method": "regex"}]
    mock_insert_tags.return_value = 3

    with patch("builtins.open", mock_open(read_data=jsonl)):
        from focus_groups.load_and_tag import main
        main()

    mock_insert.assert_called_once()
    assert len(mock_insert.call_args[0][1]) == 3
    mock_tag.assert_called()
    assert mock_tag.call_count == 3
    mock_insert_tags.assert_called_once()
    assert len(mock_insert_tags.call_args[0][1]) == 3  # one tag per post


# ── Empty JSONL ──────────────────────────────────────────────────────────────

@patch(f"{MODULE}.insert_tags")
@patch(f"{MODULE}.tag_post")
@patch(f"{MODULE}.get_post_ids_by_source_ids")
@patch(f"{MODULE}.insert_posts")
@patch(f"{MODULE}.load_demographic_value_ids")
@patch(f"{MODULE}.get_conn")
def test_empty_jsonl_no_db_calls(
    mock_conn, mock_load_vals, mock_insert, mock_id_map, mock_tag, mock_insert_tags,
):
    mock_conn.return_value = MagicMock()
    mock_load_vals.return_value = {}

    with patch("builtins.open", mock_open(read_data="")):
        from focus_groups.load_and_tag import main
        main()

    mock_insert.assert_not_called()
    mock_tag.assert_not_called()
    mock_insert_tags.assert_not_called()


# ── Duplicate handling (insert returns 0) ────────────────────────────────────

@patch(f"{MODULE}.insert_tags")
@patch(f"{MODULE}.tag_post")
@patch(f"{MODULE}.get_post_ids_by_source_ids")
@patch(f"{MODULE}.insert_posts")
@patch(f"{MODULE}.load_demographic_value_ids")
@patch(f"{MODULE}.get_conn")
def test_duplicates_still_tags(
    mock_conn, mock_load_vals, mock_insert, mock_id_map, mock_tag, mock_insert_tags,
):
    """Even when insert_posts returns 0 (all dupes), tagging still runs for existing posts."""
    posts = [_make_post("dup1")]
    jsonl = _posts_to_jsonl(posts)

    mock_conn.return_value = MagicMock()
    mock_load_vals.return_value = {}
    mock_insert.return_value = 0  # all duplicates
    mock_id_map.return_value = {"dup1": 200}  # post already in DB
    mock_tag.return_value = [{"dimension": "gender", "value": "male", "confidence": 0.8, "method": "regex"}]
    mock_insert_tags.return_value = 1

    with patch("builtins.open", mock_open(read_data=jsonl)):
        from focus_groups.load_and_tag import main
        main()

    mock_insert.assert_called_once()
    mock_tag.assert_called_once()
    mock_insert_tags.assert_called_once()


# ── Tagger failure — posts still inserted, tag rows skipped for that post ────

@patch(f"{MODULE}.insert_tags")
@patch(f"{MODULE}.tag_post")
@patch(f"{MODULE}.get_post_ids_by_source_ids")
@patch(f"{MODULE}.insert_posts")
@patch(f"{MODULE}.load_demographic_value_ids")
@patch(f"{MODULE}.get_conn")
def test_tagger_failure_posts_still_inserted(
    mock_conn, mock_load_vals, mock_insert, mock_id_map, mock_tag, mock_insert_tags,
):
    posts = [_make_post("ok1"), _make_post("fail1"), _make_post("ok2")]
    jsonl = _posts_to_jsonl(posts)

    mock_conn.return_value = MagicMock()
    mock_load_vals.return_value = {}
    mock_insert.return_value = 3
    mock_id_map.return_value = {"ok1": 1, "fail1": 2, "ok2": 3}

    tag_ok = [{"dimension": "age_group", "value": "25-34", "confidence": 0.9, "method": "regex"}]
    mock_tag.side_effect = [tag_ok, Exception("tagger broke"), tag_ok]
    mock_insert_tags.return_value = 2

    with patch("builtins.open", mock_open(read_data=jsonl)):
        from focus_groups.load_and_tag import main
        # The current implementation does NOT catch tagger errors — it will raise.
        # This test documents that behavior.
        with pytest.raises(Exception, match="tagger broke"):
            main()

    # Posts were inserted before tagging failed
    mock_insert.assert_called_once()


# ── Batch sizing: 501 posts → two batches (500 + 1) ─────────────────────────

@patch(f"{MODULE}.insert_tags")
@patch(f"{MODULE}.tag_post")
@patch(f"{MODULE}.get_post_ids_by_source_ids")
@patch(f"{MODULE}.insert_posts")
@patch(f"{MODULE}.load_demographic_value_ids")
@patch(f"{MODULE}.get_conn")
def test_batch_sizing_501_posts(
    mock_conn, mock_load_vals, mock_insert, mock_id_map, mock_tag, mock_insert_tags,
):
    posts = [_make_post(f"p{i}") for i in range(501)]
    jsonl = _posts_to_jsonl(posts)

    mock_conn.return_value = MagicMock()
    mock_load_vals.return_value = {}
    mock_insert.return_value = 500  # first batch
    mock_id_map.return_value = {f"p{i}": i for i in range(501)}
    mock_tag.return_value = []  # no tags (simplify)
    mock_insert_tags.return_value = 0

    with patch("builtins.open", mock_open(read_data=jsonl)):
        from focus_groups.load_and_tag import main
        main()

    # insert_posts called twice: batch of 500, then batch of 1
    assert mock_insert.call_count == 2
    assert len(mock_insert.call_args_list[0][0][1]) == 500
    assert len(mock_insert.call_args_list[1][0][1]) == 1
