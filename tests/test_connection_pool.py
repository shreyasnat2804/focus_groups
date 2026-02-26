"""
Tests for connection pooling (db.py pool functions) and the get_db FastAPI dependency.

Verifies:
- Pool initialization and shutdown
- get_pool_conn raises if pool not initialized
- Connections are returned to pool even when endpoints raise
- get_db dependency yields and returns connections properly
"""

from unittest.mock import MagicMock, patch

import pytest


# ── Pool functions ────────────────────────────────────────────────────────────

class TestPoolLifecycle:
    """Tests for init_pool, get_pool_conn, return_pool_conn, close_pool."""

    @patch("focus_groups.db.ThreadedConnectionPool")
    @patch("focus_groups.db.register_vector")
    def test_init_pool_creates_pool(self, mock_reg, mock_pool_cls):
        from focus_groups.db import init_pool, close_pool, _pool
        import focus_groups.db as db_mod

        init_pool(minconn=1, maxconn=5)
        mock_pool_cls.assert_called_once()
        assert db_mod._pool is not None

        # Cleanup
        db_mod._pool = None

    def test_get_pool_conn_raises_without_init(self):
        import focus_groups.db as db_mod
        old_pool = db_mod._pool
        db_mod._pool = None
        try:
            from focus_groups.db import get_pool_conn
            with pytest.raises(RuntimeError, match="not initialised"):
                get_pool_conn()
        finally:
            db_mod._pool = old_pool

    @patch("focus_groups.db.register_vector")
    def test_get_pool_conn_returns_connection(self, mock_reg):
        import focus_groups.db as db_mod
        mock_pool = MagicMock()
        mock_conn = MagicMock()
        mock_pool.getconn.return_value = mock_conn
        old_pool = db_mod._pool
        db_mod._pool = mock_pool

        try:
            from focus_groups.db import get_pool_conn
            conn = get_pool_conn()
            assert conn is mock_conn
            mock_pool.getconn.assert_called_once()
            mock_reg.assert_called_once_with(mock_conn)
        finally:
            db_mod._pool = old_pool

    def test_return_pool_conn_puts_back(self):
        import focus_groups.db as db_mod
        mock_pool = MagicMock()
        mock_conn = MagicMock()
        old_pool = db_mod._pool
        db_mod._pool = mock_pool

        try:
            from focus_groups.db import return_pool_conn
            return_pool_conn(mock_conn)
            mock_pool.putconn.assert_called_once_with(mock_conn)
        finally:
            db_mod._pool = old_pool

    def test_close_pool_closes_all(self):
        import focus_groups.db as db_mod
        mock_pool = MagicMock()
        old_pool = db_mod._pool
        db_mod._pool = mock_pool

        try:
            from focus_groups.db import close_pool
            close_pool()
            mock_pool.closeall.assert_called_once()
            assert db_mod._pool is None
        finally:
            db_mod._pool = old_pool


# ── get_db dependency ─────────────────────────────────────────────────────────

class TestGetDbDependency:
    """Test that the get_db FastAPI dependency returns connections to the pool."""

    @patch("focus_groups.api.return_pool_conn")
    @patch("focus_groups.api.get_pool_conn")
    def test_get_db_yields_and_returns(self, mock_get, mock_return):
        mock_conn = MagicMock()
        mock_get.return_value = mock_conn

        from focus_groups.api import get_db
        gen = get_db()
        conn = next(gen)
        assert conn is mock_conn

        # Simulate finally block
        try:
            gen.send(None)
        except StopIteration:
            pass

        mock_return.assert_called_once_with(mock_conn)

    @patch("focus_groups.api.return_pool_conn")
    @patch("focus_groups.api.get_pool_conn")
    def test_get_db_returns_conn_on_error(self, mock_get, mock_return):
        """Connection must be returned even if the endpoint raises."""
        mock_conn = MagicMock()
        mock_get.return_value = mock_conn

        from focus_groups.api import get_db
        gen = get_db()
        next(gen)

        # Simulate an exception thrown into the generator
        with pytest.raises(ValueError):
            gen.throw(ValueError, ValueError("boom"), None)

        mock_return.assert_called_once_with(mock_conn)
