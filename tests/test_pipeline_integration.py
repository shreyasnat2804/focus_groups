"""
Integration test for the full pipeline — real DB, mocked Claude.

Patches select_personas and run_focus_group to avoid API calls,
but uses real Postgres for session creation + response storage.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

import pytest

from focus_groups.db import get_conn, insert_posts, get_post_ids_by_source_ids
from focus_groups.personas.cards import PersonaCard
from focus_groups.sessions import get_session


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
    source_id = f"pipe_{uuid.uuid4().hex[:10]}"
    post = {
        "id": source_id,
        "sector": "tech",
        "subreddit": "testsubreddit",
        "title": f"Pipeline test {source_id}",
        "selftext": "Pipeline integration test content.",
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


def test_pipeline_with_mocked_claude(conn):
    """Full pipeline: real DB, mocked Claude → session exists with correct responses."""
    post_id = _insert_test_post(conn)

    cards = [
        PersonaCard(
            post_id=post_id,
            demographic_tags={"age_group": "25-34", "gender": "male"},
            text_excerpt="Test excerpt.",
            sector="tech",
        ),
    ]

    canned_responses = [
        {
            "post_id": post_id,
            "persona_summary": "25-34 year old male",
            "system_prompt": "You are simulating...",
            "response_text": "Pipeline test response.",
            "model": "test-model",
        },
    ]

    # Wrap conn so run_pipeline's conn.close() doesn't close our shared fixture
    wrapper = MagicMock(wraps=conn)
    wrapper.close = MagicMock()  # no-op close

    with (
        patch("focus_groups.cli_runner.get_conn", return_value=wrapper),
        patch("focus_groups.cli_runner.get_client", return_value=MagicMock()),
        patch("focus_groups.cli_runner.select_personas", return_value=cards),
        patch("focus_groups.cli_runner.run_focus_group", return_value=canned_responses),
    ):
        from focus_groups.cli_runner import run_pipeline
        from io import StringIO

        output = StringIO()
        run_pipeline(
            question="Pipeline integration test?",
            sector="tech",
            num_personas=1,
            save=True,
            output=output,
        )

        text = output.getvalue()
        assert "Pipeline test response" in text
        assert "Session saved: id=" in text

    # Verify session exists in DB
    # Extract session_id from output
    for line in text.split("\n"):
        if "Session saved: id=" in line:
            session_id = line.split("id=")[1].strip()
            break

    session = get_session(conn, session_id)
    assert session is not None
    assert session["status"] == "completed"
    assert len(session["responses"]) == 1
    assert session["responses"][0]["response_text"] == "Pipeline test response."
