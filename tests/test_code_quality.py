"""
Tests for code quality fixes:
- insert_tags gracefully handles unknown dimension/value pairs
- purge_expired_sessions is throttled to run at most once per hour
- Claude model/token config reads from environment variables
"""

import os
import time
from unittest.mock import MagicMock, patch

import pytest


# ── insert_tags: unknown dimension/value ─────────────────────────────────────

class TestInsertTagsUnknownKeys:
    """insert_tags should skip unknown dimension/value pairs instead of raising KeyError."""

    @patch("focus_groups.db.execute_values")
    def test_unknown_dimension_value_skipped(self, mock_exec):
        """Tags with dimension/value not in the lookup table are skipped, not crashed."""
        from focus_groups.db import insert_tags

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_cursor.rowcount = 1

        # Known lookup table has only age_group/25-34
        value_ids = {("age_group", "25-34"): 1}

        tags = [
            {"post_id": 100, "dimension": "age_group", "value": "25-34",
             "confidence": 0.9, "method": "self_disclosure"},
            {"post_id": 100, "dimension": "nonexistent_dim", "value": "unknown_val",
             "confidence": 0.5, "method": "subreddit_prior"},
        ]

        # Should NOT raise KeyError
        result = insert_tags(mock_conn, tags, value_ids=value_ids)
        # Only the known tag should be passed to execute_values
        args_list = mock_exec.call_args[0][2]
        assert len(args_list) == 1
        assert args_list[0][1] == 1  # value_id for age_group/25-34

    def test_all_unknown_tags_skipped_returns_zero(self):
        """When all tags have unknown keys, no DB insert happens, returns 0."""
        from focus_groups.db import insert_tags

        mock_conn = MagicMock()
        value_ids = {("age_group", "25-34"): 1}

        tags = [
            {"post_id": 100, "dimension": "fake_dim", "value": "fake_val",
             "confidence": 0.5, "method": "test"},
        ]

        result = insert_tags(mock_conn, tags, value_ids=value_ids)
        assert result == 0

    @patch("focus_groups.db.execute_values")
    def test_known_tags_still_inserted(self, mock_exec):
        """Known tags are still inserted even when some are skipped."""
        from focus_groups.db import insert_tags

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_cursor.rowcount = 2

        value_ids = {("age_group", "25-34"): 1, ("gender", "male"): 2}

        tags = [
            {"post_id": 100, "dimension": "age_group", "value": "25-34",
             "confidence": 0.9, "method": "self_disclosure"},
            {"post_id": 100, "dimension": "bogus", "value": "nope",
             "confidence": 0.5, "method": "test"},
            {"post_id": 100, "dimension": "gender", "value": "male",
             "confidence": 0.8, "method": "self_disclosure"},
        ]

        result = insert_tags(mock_conn, tags, value_ids=value_ids)
        # execute_values should have been called with 2 rows (the 2 known tags)
        args_list = mock_exec.call_args[0][2]
        assert len(args_list) == 2
        assert result == 2  # rowcount from mock


# ── purge_expired_sessions throttling ────────────────────────────────────────

class TestPurgeThrottling:
    """purge_expired_sessions should only run once per PURGE_INTERVAL on GET /sessions."""

    def test_purge_called_on_first_request(self):
        """First GET /api/sessions should trigger purge."""
        with (
            patch("focus_groups.api.purge_expired_sessions") as mock_purge,
            patch("focus_groups.api.count_sessions", return_value=0),
            patch("focus_groups.api.list_sessions", return_value=[]),
        ):
            import focus_groups.api as api_mod
            api_mod._last_purge = 0  # reset

            from focus_groups.api import app, get_db
            from fastapi.testclient import TestClient
            app.dependency_overrides[get_db] = lambda: MagicMock()
            client = TestClient(app)

            resp = client.get("/api/sessions")
            app.dependency_overrides.clear()
            assert resp.status_code == 200
            mock_purge.assert_called_once()

    def test_purge_not_called_within_interval(self):
        """Second GET /api/sessions within the interval should NOT trigger purge."""
        with (
            patch("focus_groups.api.purge_expired_sessions") as mock_purge,
            patch("focus_groups.api.count_sessions", return_value=0),
            patch("focus_groups.api.list_sessions", return_value=[]),
        ):
            import focus_groups.api as api_mod
            api_mod._last_purge = time.time()  # just ran

            from focus_groups.api import app, get_db
            from fastapi.testclient import TestClient
            app.dependency_overrides[get_db] = lambda: MagicMock()
            client = TestClient(app)

            resp = client.get("/api/sessions")
            app.dependency_overrides.clear()
            assert resp.status_code == 200
            mock_purge.assert_not_called()

    def test_purge_called_after_interval_expires(self):
        """GET /api/sessions after PURGE_INTERVAL has elapsed should trigger purge."""
        with (
            patch("focus_groups.api.purge_expired_sessions") as mock_purge,
            patch("focus_groups.api.count_sessions", return_value=0),
            patch("focus_groups.api.list_sessions", return_value=[]),
        ):
            import focus_groups.api as api_mod
            api_mod._last_purge = time.time() - 3601  # expired

            from focus_groups.api import app, get_db
            from fastapi.testclient import TestClient
            app.dependency_overrides[get_db] = lambda: MagicMock()
            client = TestClient(app)

            resp = client.get("/api/sessions")
            app.dependency_overrides.clear()
            assert resp.status_code == 200
            mock_purge.assert_called_once()


# ── Claude model config from env vars ────────────────────────────────────────

class TestClaudeModelConfig:
    """MODEL and MAX_TOKENS should be configurable via environment variables."""

    def test_default_model(self):
        """Without env var, MODEL defaults to claude-sonnet-4-20250514."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CLAUDE_MODEL", None)
            # Re-import to pick up defaults
            import importlib
            import focus_groups.claude as claude_mod
            importlib.reload(claude_mod)
            assert claude_mod.MODEL == "claude-sonnet-4-20250514"

    def test_custom_model_from_env(self):
        """CLAUDE_MODEL env var overrides the default model."""
        with patch.dict(os.environ, {"CLAUDE_MODEL": "claude-haiku-4-5-20251001"}):
            import importlib
            import focus_groups.claude as claude_mod
            importlib.reload(claude_mod)
            assert claude_mod.MODEL == "claude-haiku-4-5-20251001"

    def test_default_max_tokens(self):
        """Without env var, MAX_TOKENS defaults to 1024."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CLAUDE_MAX_TOKENS", None)
            import importlib
            import focus_groups.claude as claude_mod
            importlib.reload(claude_mod)
            assert claude_mod.MAX_TOKENS == 1024

    def test_custom_max_tokens_from_env(self):
        """CLAUDE_MAX_TOKENS env var overrides the default."""
        with patch.dict(os.environ, {"CLAUDE_MAX_TOKENS": "2048"}):
            import importlib
            import focus_groups.claude as claude_mod
            importlib.reload(claude_mod)
            assert claude_mod.MAX_TOKENS == 2048

    def test_generate_uses_configured_model(self):
        """generate_persona_response should use the configured MODEL and MAX_TOKENS."""
        with patch.dict(os.environ, {"CLAUDE_MODEL": "test-model", "CLAUDE_MAX_TOKENS": "512"}):
            import importlib
            import focus_groups.claude as claude_mod
            importlib.reload(claude_mod)

            mock_client = MagicMock()
            message = MagicMock()
            message.content = [MagicMock(text="test response")]
            mock_client.messages.create.return_value = message

            from focus_groups.personas.cards import PersonaCard
            card = PersonaCard(
                post_id=1,
                demographic_tags={"age_group": "25-34"},
                text_excerpt="test",
                sector="tech",
            )

            claude_mod.generate_persona_response(mock_client, card, "test?")
            call_kwargs = mock_client.messages.create.call_args[1]
            assert call_kwargs["model"] == "test-model"
            assert call_kwargs["max_tokens"] == 512
