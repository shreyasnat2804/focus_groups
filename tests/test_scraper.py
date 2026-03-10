"""Tests for focus_groups.scraper module."""

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import pytest
import requests

from focus_groups.scraper import (
    fetch_json,
    iter_subreddit,
    run,
    SUBREDDIT_REGIONS,
    SUBREDDITS,
    MIN_SCORE,
    MIN_BODY_CHARS,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SENTINEL = object()


def _mock_response(status_code=200, json_data=None, headers=None, bad_json=False):
    """Create a mock requests.Response."""
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    resp.headers = headers or {}
    if bad_json:
        resp.json.side_effect = json.JSONDecodeError("bad", "", 0)
    else:
        resp.json.return_value = json_data
    return resp


def _reddit_page(posts, after=None):
    """Build a Reddit-style listing JSON with children and optional after cursor."""
    return {
        "data": {
            "children": [{"data": p} for p in posts],
            "after": after,
        }
    }


def _valid_post(id="abc123", score=100, body=_SENTINEL, author="someuser", created_utc=None):
    """Return a post dict that passes all filters."""
    return {
        "id": id,
        "score": score,
        "selftext": ("x" * (MIN_BODY_CHARS + 10)) if body is _SENTINEL else body,
        "author": author,
        "title": "Test title",
        "created_utc": created_utc or datetime(2023, 6, 1, tzinfo=timezone.utc).timestamp(),
        "num_comments": 5,
        "permalink": f"/r/test/comments/{id}/",
    }


# ===========================================================================
# fetch_json() tests
# ===========================================================================


class TestFetchJson:
    """Tests for fetch_json()."""

    @patch("focus_groups.scraper.time.sleep")
    def test_network_error_retry_then_succeed(self, mock_sleep):
        session = MagicMock()
        good_resp = _mock_response(200, json_data={"ok": True})
        session.get.side_effect = [
            requests.RequestException("timeout"),
            requests.RequestException("reset"),
            good_resp,
        ]

        result = fetch_json("http://example.com", session, attempt=0)

        assert result == {"ok": True}
        assert session.get.call_count == 3
        assert mock_sleep.call_args_list[0][0] == (1,)   # 2**0
        assert mock_sleep.call_args_list[1][0] == (2,)   # 2**1

    @patch("focus_groups.scraper.time.sleep")
    def test_429_rate_limit_retries_with_increment(self, mock_sleep):
        session = MagicMock()
        rate_resp = _mock_response(429, headers={"Retry-After": "5"})
        good_resp = _mock_response(200, json_data={"ok": True})
        session.get.side_effect = [rate_resp, good_resp]

        result = fetch_json("http://example.com", session, attempt=0)

        assert result == {"ok": True}
        mock_sleep.assert_called_once_with(5)

    @patch("focus_groups.scraper.time.sleep")
    def test_429_max_retries_exceeded(self, mock_sleep):
        session = MagicMock()
        rate_resp = _mock_response(429, headers={"Retry-After": "1"})
        session.get.return_value = rate_resp

        result = fetch_json("http://example.com", session, attempt=0)

        assert result is None
        # Should have tried 6 times (attempts 0-5), sleeping on first 5
        assert session.get.call_count == 6
        assert mock_sleep.call_count == 5

    def test_403_skip_no_retry(self):
        session = MagicMock()
        session.get.return_value = _mock_response(403)

        result = fetch_json("http://example.com", session)

        assert result is None
        assert session.get.call_count == 1

    def test_404_skip_no_retry(self):
        session = MagicMock()
        session.get.return_value = _mock_response(404)

        result = fetch_json("http://example.com", session)

        assert result is None
        assert session.get.call_count == 1

    @patch("focus_groups.scraper.time.sleep")
    def test_500_server_error_retry(self, mock_sleep):
        session = MagicMock()
        err = _mock_response(500)
        good = _mock_response(200, json_data={"ok": True})
        session.get.side_effect = [err, err, good]

        result = fetch_json("http://example.com", session, attempt=0)

        assert result == {"ok": True}
        assert session.get.call_count == 3

    @patch("focus_groups.scraper.time.sleep")
    def test_max_retries_exhausted_on_network_error(self, mock_sleep):
        session = MagicMock()
        session.get.side_effect = requests.RequestException("fail")

        result = fetch_json("http://example.com", session, attempt=0)

        assert result is None
        assert session.get.call_count == 4  # attempts 0,1,2,3 — fails at attempt 3

    def test_bad_json_returns_none(self):
        session = MagicMock()
        session.get.return_value = _mock_response(200, bad_json=True)

        result = fetch_json("http://example.com", session)

        assert result is None


# ===========================================================================
# iter_subreddit() tests
# ===========================================================================


class TestIterSubreddit:
    """Tests for iter_subreddit()."""

    @patch("focus_groups.scraper.time.sleep")
    @patch("focus_groups.scraper.fetch_json")
    def test_basic_pagination_two_pages(self, mock_fetch, mock_sleep):
        page1 = _reddit_page([_valid_post(id="p1"), _valid_post(id="p2")], after="cursor1")
        page2 = _reddit_page([_valid_post(id="p3")], after=None)
        mock_fetch.side_effect = [page1, page2]

        posts = list(iter_subreddit("test_sub", "tech", MagicMock()))

        assert [p["id"] for p in posts] == ["p1", "p2", "p3"]
        assert all(p["sector"] == "tech" for p in posts)

    @patch("focus_groups.scraper.time.sleep")
    @patch("focus_groups.scraper.fetch_json")
    def test_post_filtering_low_score(self, mock_fetch, mock_sleep):
        page = _reddit_page([_valid_post(id="low", score=1)], after=None)
        mock_fetch.return_value = page

        posts = list(iter_subreddit("test_sub", "tech", MagicMock()))

        assert posts == []

    @patch("focus_groups.scraper.time.sleep")
    @patch("focus_groups.scraper.fetch_json")
    def test_post_filtering_short_body(self, mock_fetch, mock_sleep):
        page = _reddit_page([_valid_post(id="short", body="hi")], after=None)
        mock_fetch.return_value = page

        posts = list(iter_subreddit("test_sub", "tech", MagicMock()))

        assert posts == []

    @patch("focus_groups.scraper.time.sleep")
    @patch("focus_groups.scraper.fetch_json")
    def test_post_filtering_deleted_author(self, mock_fetch, mock_sleep):
        page = _reddit_page([_valid_post(id="del", author="[deleted]")], after=None)
        mock_fetch.return_value = page

        posts = list(iter_subreddit("test_sub", "tech", MagicMock()))

        assert posts == []

    @patch("focus_groups.scraper.time.sleep")
    @patch("focus_groups.scraper.fetch_json")
    def test_post_filtering_automoderator(self, mock_fetch, mock_sleep):
        page = _reddit_page([_valid_post(id="auto", author="AutoModerator")], after=None)
        mock_fetch.return_value = page

        posts = list(iter_subreddit("test_sub", "tech", MagicMock()))

        assert posts == []

    @patch("focus_groups.scraper.time.sleep")
    @patch("focus_groups.scraper.fetch_json")
    def test_post_filtering_empty_body(self, mock_fetch, mock_sleep):
        page = _reddit_page([_valid_post(id="empty", body="")], after=None)
        mock_fetch.return_value = page

        posts = list(iter_subreddit("test_sub", "tech", MagicMock()))

        assert posts == []

    @patch("focus_groups.scraper.time.sleep")
    @patch("focus_groups.scraper.fetch_json")
    def test_post_filtering_deleted_body(self, mock_fetch, mock_sleep):
        page = _reddit_page([_valid_post(id="rem", body="[removed]")], after=None)
        mock_fetch.return_value = page

        posts = list(iter_subreddit("test_sub", "tech", MagicMock()))

        assert posts == []

    @patch("focus_groups.scraper.time.sleep")
    @patch("focus_groups.scraper.fetch_json")
    def test_date_cutoff_skips_old_posts_and_stops(self, mock_fetch, mock_sleep):
        cutoff = datetime(2023, 1, 1, tzinfo=timezone.utc)
        old_ts = datetime(2022, 6, 1, tzinfo=timezone.utc).timestamp()
        new_ts = datetime(2023, 6, 1, tzinfo=timezone.utc).timestamp()

        page = _reddit_page(
            [_valid_post(id="new1", created_utc=new_ts), _valid_post(id="old1", created_utc=old_ts)],
            after="cursor",
        )
        mock_fetch.return_value = page

        posts = list(iter_subreddit("test_sub", "tech", MagicMock(), min_date=cutoff))

        assert [p["id"] for p in posts] == ["new1"]
        # Should not fetch page 2 because hit_cutoff is True
        assert mock_fetch.call_count == 1

    @patch("focus_groups.scraper.time.sleep")
    @patch("focus_groups.scraper.fetch_json")
    def test_empty_page_stops_pagination(self, mock_fetch, mock_sleep):
        mock_fetch.return_value = _reddit_page([], after=None)

        posts = list(iter_subreddit("test_sub", "tech", MagicMock()))

        assert posts == []
        assert mock_fetch.call_count == 1

    @patch("focus_groups.scraper.time.sleep")
    @patch("focus_groups.scraper.fetch_json")
    def test_no_after_cursor_stops(self, mock_fetch, mock_sleep):
        page = _reddit_page([_valid_post(id="p1")], after=None)
        mock_fetch.return_value = page

        posts = list(iter_subreddit("test_sub", "tech", MagicMock()))

        assert len(posts) == 1
        assert mock_fetch.call_count == 1

    @patch("focus_groups.scraper.time.sleep")
    @patch("focus_groups.scraper.fetch_json")
    def test_fetch_json_returns_none_stops(self, mock_fetch, mock_sleep):
        mock_fetch.return_value = None

        posts = list(iter_subreddit("test_sub", "tech", MagicMock()))

        assert posts == []

    @patch("focus_groups.scraper.time.sleep")
    @patch("focus_groups.scraper.fetch_json")
    def test_region_mapping_applied(self, mock_fetch, mock_sleep):
        page = _reddit_page([_valid_post(id="uk1")], after=None)
        mock_fetch.return_value = page

        posts = list(iter_subreddit("UKPersonalFinance", "financial", MagicMock()))

        assert posts[0]["region"] == "UK"

    @patch("focus_groups.scraper.time.sleep")
    @patch("focus_groups.scraper.fetch_json")
    def test_no_region_mapping_returns_none(self, mock_fetch, mock_sleep):
        page = _reddit_page([_valid_post(id="us1")], after=None)
        mock_fetch.return_value = page

        posts = list(iter_subreddit("personalfinance", "financial", MagicMock()))

        assert posts[0]["region"] is None


# ===========================================================================
# SUBREDDIT_REGIONS tests
# ===========================================================================


class TestSubredditRegions:

    def test_regional_subs_in_subreddits_have_mapping(self):
        """Every subreddit in SUBREDDITS that has a region mapping should be correctly represented."""
        all_subs = {s for subs in SUBREDDITS.values() for s in subs}
        for sub in all_subs:
            if sub in SUBREDDIT_REGIONS:
                assert isinstance(SUBREDDIT_REGIONS[sub], str)
                assert len(SUBREDDIT_REGIONS[sub]) == 2  # 2-letter region code

    def test_unmapped_subs_return_none(self):
        """Subreddits not in SUBREDDIT_REGIONS should return None region."""
        unmapped = ["cscareerquestions", "personalfinance", "NeutralPolitics"]
        for sub in unmapped:
            assert SUBREDDIT_REGIONS.get(sub) is None


# ===========================================================================
# run() tests
# ===========================================================================


class TestRun:

    @patch("focus_groups.scraper.time.sleep")
    @patch("focus_groups.scraper._try_get_db_conn", return_value=None)
    @patch("focus_groups.scraper.iter_subreddit")
    def test_jsonl_dedup(self, mock_iter, mock_db, mock_sleep, tmp_path):
        """Posts already in the JSONL file should be skipped."""
        jsonl = tmp_path / "posts.jsonl"
        jsonl.write_text(json.dumps({"id": "existing1"}) + "\n")

        mock_iter.return_value = iter([
            {"id": "existing1", "sector": "tech", "subreddit": "test"},
            {"id": "new1", "sector": "tech", "subreddit": "test"},
        ])

        with patch("focus_groups.scraper.OUTPUT_FILE", jsonl), \
             patch("focus_groups.scraper.DATA_DIR", tmp_path):
            total = run(sectors=["tech"], max_pages_per_sub=1, min_date=None)

        assert total == 1
        lines = jsonl.read_text().strip().split("\n")
        ids = [json.loads(l)["id"] for l in lines]
        assert "existing1" in ids
        assert "new1" in ids

    @patch("focus_groups.scraper.time.sleep")
    @patch("focus_groups.scraper.iter_subreddit")
    def test_db_insert_path(self, mock_iter, mock_sleep, tmp_path):
        """When DB is available, posts should be inserted."""
        jsonl = tmp_path / "posts.jsonl"
        mock_conn = MagicMock()
        mock_insert = MagicMock(return_value=2)

        mock_iter.return_value = iter([
            {"id": "p1", "sector": "tech", "subreddit": "test", "title": "t", "selftext": "b"},
            {"id": "p2", "sector": "tech", "subreddit": "test", "title": "t", "selftext": "b"},
        ])

        with patch("focus_groups.scraper.OUTPUT_FILE", jsonl), \
             patch("focus_groups.scraper.DATA_DIR", tmp_path), \
             patch("focus_groups.scraper._try_get_db_conn", return_value=mock_conn), \
             patch("focus_groups.scraper.insert_posts", mock_insert, create=True), \
             patch.dict("sys.modules", {"focus_groups.db": MagicMock(
                 insert_posts=mock_insert,
                 get_post_ids_by_source_ids=MagicMock(return_value={}),
                 insert_tags=MagicMock(return_value=0),
             )}), \
             patch.dict("sys.modules", {"focus_groups.tagger": MagicMock(
                 tag_post=MagicMock(return_value=[]),
             )}):
            total = run(sectors=["tech"], max_pages_per_sub=1, min_date=None)

        assert total == 2
        mock_insert.assert_called_once()
        batch = mock_insert.call_args[0][1]
        assert len(batch) == 2

    @patch("focus_groups.scraper.time.sleep")
    @patch("focus_groups.scraper._try_get_db_conn", return_value=None)
    @patch("focus_groups.scraper.iter_subreddit")
    def test_db_unavailable_jsonl_only(self, mock_iter, mock_db, mock_sleep, tmp_path):
        """When DB is unavailable, should still write to JSONL."""
        jsonl = tmp_path / "posts.jsonl"

        mock_iter.return_value = iter([
            {"id": "p1", "sector": "tech", "subreddit": "test"},
        ])

        with patch("focus_groups.scraper.OUTPUT_FILE", jsonl), \
             patch("focus_groups.scraper.DATA_DIR", tmp_path):
            total = run(sectors=["tech"], max_pages_per_sub=1, min_date=None)

        assert total == 1
        assert json.loads(jsonl.read_text().strip())["id"] == "p1"

    @patch("focus_groups.scraper.time.sleep")
    @patch("focus_groups.scraper._try_get_db_conn", return_value=None)
    @patch("focus_groups.scraper.iter_subreddit")
    def test_probe_mode(self, mock_iter, mock_db, mock_sleep, tmp_path):
        """Probe mode should only scrape first subreddit per sector."""
        jsonl = tmp_path / "posts.jsonl"
        mock_iter.return_value = iter([])

        with patch("focus_groups.scraper.OUTPUT_FILE", jsonl), \
             patch("focus_groups.scraper.DATA_DIR", tmp_path):
            run(sectors=["tech", "financial"], max_pages_per_sub=1, probe=True, min_date=None)

        # iter_subreddit should be called once per sector (first sub only)
        called_subs = [call[0][0] for call in mock_iter.call_args_list]
        assert called_subs == ["cscareerquestions", "personalfinance"]
