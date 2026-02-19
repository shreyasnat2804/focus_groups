"""
Integration tests for new db.py helpers — requires Docker Postgres running.
Run with: python3 -m pytest tests/test_db.py -v

Set env vars to override defaults:
    PG_HOST, PG_PORT, PG_DB, PG_USER, PG_PASSWORD
"""

import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db import get_conn, insert_posts, get_post_ids_by_source_ids, insert_tags, _sanitize_text


@pytest.fixture(scope="module")
def conn():
    """Single DB connection for the entire module. Skip if DB unreachable."""
    try:
        c = get_conn()
        yield c
        c.close()
    except Exception as exc:
        pytest.skip(f"Postgres not available: {exc}")


def _make_post(suffix: str = "") -> dict:
    """Return a minimal valid post dict with a unique source_id."""
    unique_id = uuid.uuid4().hex[:10] + suffix
    return {
        "id": unique_id,
        "sector": "test",
        "subreddit": "testsubreddit",
        "title": f"Test post {unique_id}",
        "selftext": "This is test content with enough characters to pass validation.",
        "author": "testuser",
        "score": 42,
        "num_comments": 5,
        "created_utc": datetime.now(timezone.utc).timestamp(),
        "permalink": f"/r/test/{unique_id}",
        "scraped_at": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# get_post_ids_by_source_ids
# ---------------------------------------------------------------------------

def test_get_post_ids_by_source_ids_basic(conn):
    """Insert a post then look up its DB id by source_id."""
    post = _make_post("_lookup")
    insert_posts(conn, [post])

    id_map = get_post_ids_by_source_ids(conn, [post["id"]])
    assert post["id"] in id_map
    assert isinstance(id_map[post["id"]], int)


def test_get_post_ids_by_source_ids_multiple(conn):
    """Insert multiple posts and look them all up at once."""
    posts = [_make_post(f"_multi{i}") for i in range(3)]
    insert_posts(conn, posts)

    source_ids = [p["id"] for p in posts]
    id_map = get_post_ids_by_source_ids(conn, source_ids)
    for sid in source_ids:
        assert sid in id_map


def test_get_post_ids_missing(conn):
    """A source_id not in DB must be absent from the returned dict."""
    fake_id = "nonexistent_" + uuid.uuid4().hex[:8]
    id_map = get_post_ids_by_source_ids(conn, [fake_id])
    assert fake_id not in id_map


def test_get_post_ids_empty_input(conn):
    """Empty list input returns empty dict."""
    result = get_post_ids_by_source_ids(conn, [])
    assert result == {}


# ---------------------------------------------------------------------------
# insert_tags
# ---------------------------------------------------------------------------

def test_insert_tags_basic(conn):
    """Insert a post and attach tags, verify count returned."""
    post = _make_post("_tag1")
    insert_posts(conn, [post])
    id_map = get_post_ids_by_source_ids(conn, [post["id"]])
    db_id = id_map[post["id"]]

    tags = [
        {"post_id": db_id, "dimension": "age_group", "value": "25-34",
         "confidence": 0.90, "method": "self_disclosure"},
        {"post_id": db_id, "dimension": "gender", "value": "female",
         "confidence": 0.85, "method": "self_disclosure"},
    ]
    n = insert_tags(conn, tags)
    assert n == 2


def test_insert_tags_idempotent(conn):
    """Inserting the same tags twice leaves count unchanged (ON CONFLICT DO NOTHING)."""
    post = _make_post("_idem")
    insert_posts(conn, [post])
    id_map = get_post_ids_by_source_ids(conn, [post["id"]])
    db_id = id_map[post["id"]]

    tags = [
        {"post_id": db_id, "dimension": "income_bracket", "value": "middle_income",
         "confidence": 0.50, "method": "subreddit_prior"},
    ]
    n1 = insert_tags(conn, tags)
    n2 = insert_tags(conn, tags)

    assert n1 == 1
    assert n2 == 0  # conflict, nothing inserted


def test_insert_tags_empty_list(conn):
    """Empty tag list returns 0 without error."""
    n = insert_tags(conn, [])
    assert n == 0


# ---------------------------------------------------------------------------
# UTF-8 sanitization
# ---------------------------------------------------------------------------

def test_sanitize_text_valid_unicode():
    """Normal strings pass through unchanged."""
    s = "I'm 28 years old — making $80k/year with 'smart quotes'"
    assert _sanitize_text(s) == s


def test_sanitize_text_lone_surrogate():
    """Lone surrogate (U+D800) is replaced with U+FFFD, not stored as invalid UTF-8."""
    bad = "hello \ud800 world"        # lone surrogate — invalid UTF-8
    result = _sanitize_text(bad)
    assert "\ud800" not in result      # surrogate gone
    assert "\ufffd" in result          # replaced with U+FFFD
    result.encode("utf-8")            # must be encodable without error


def test_sanitize_text_none_and_empty():
    assert _sanitize_text(None) == ""
    assert _sanitize_text("") == ""


def test_insert_posts_with_unicode_text(conn):
    """Posts with curly quotes, em-dashes, emoji insert and query without error."""
    post = _make_post("_utf8")
    post["selftext"] = "Smart quotes \u2018like this\u2019 and em\u2014dashes are fine."
    n = insert_posts(conn, [post])
    assert n == 1
    id_map = get_post_ids_by_source_ids(conn, [post["id"]])
    assert post["id"] in id_map


def test_insert_posts_sanitizes_surrogate(conn):
    """Posts whose text contains a lone surrogate are sanitized and inserted cleanly."""
    post = _make_post("_surr")
    post["selftext"] = "Bad char: \ud800 end"   # lone surrogate
    # Should not raise — _sanitize_text replaces the surrogate
    n = insert_posts(conn, [post])
    assert n == 1
    # Verify the stored text is queryable (no CharacterNotInRepertoire on read)
    id_map = get_post_ids_by_source_ids(conn, [post["id"]])
    db_id = id_map[post["id"]]
    with conn.cursor() as cur:
        cur.execute("SELECT text FROM posts WHERE id = %s", (db_id,))
        text = cur.fetchone()[0]
    assert "\ud800" not in text        # surrogate was replaced
    assert text                        # non-empty


def test_insert_tags_multiple_methods_same_dimension(conn):
    """Same dimension + different method → both allowed (not a conflict)."""
    post = _make_post("_methods")
    insert_posts(conn, [post])
    id_map = get_post_ids_by_source_ids(conn, [post["id"]])
    db_id = id_map[post["id"]]

    tags = [
        {"post_id": db_id, "dimension": "income_bracket", "value": "lower_income",
         "confidence": 0.6, "method": "subreddit_prior"},
        {"post_id": db_id, "dimension": "income_bracket", "value": "high_income",
         "confidence": 0.9, "method": "self_disclosure"},
    ]
    n = insert_tags(conn, tags)
    assert n == 2  # different methods → no conflict
