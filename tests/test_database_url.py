"""Tests for DATABASE_URL support in db.py."""

import os
from unittest.mock import patch, MagicMock

import pytest


class TestPgKwargs:
    """Test _pg_kwargs() with DATABASE_URL vs PG_* env vars."""

    def test_database_url_returns_dsn(self):
        """When DATABASE_URL is set, _pg_kwargs() returns {"dsn": DATABASE_URL}."""
        url = "postgresql://user:pass@host:5432/mydb"
        with patch.dict(os.environ, {"DATABASE_URL": url}, clear=False):
            from focus_groups.db import _pg_kwargs
            result = _pg_kwargs()
        assert result == {"dsn": url}

    def test_no_database_url_returns_individual_vars(self):
        """When DATABASE_URL is NOT set, _pg_kwargs() returns the individual PG_* dict."""
        env = {
            "PG_HOST": "myhost",
            "PG_PORT": "5433",
            "PG_DB": "testdb",
            "PG_USER": "testuser",
            "PG_PASSWORD": "testpass",
        }
        with patch.dict(os.environ, env, clear=False):
            # Make sure DATABASE_URL is not set
            os.environ.pop("DATABASE_URL", None)
            from focus_groups.db import _pg_kwargs
            result = _pg_kwargs()
        assert result == {
            "host": "myhost",
            "port": "5433",
            "dbname": "testdb",
            "user": "testuser",
            "password": "testpass",
        }

    def test_fallback_defaults_when_no_env(self):
        """When no env vars are set, _pg_kwargs() uses sensible defaults."""
        remove_keys = ["DATABASE_URL", "PG_HOST", "PG_PORT", "PG_DB", "PG_USER", "PG_PASSWORD"]
        env_backup = {k: os.environ.pop(k) for k in remove_keys if k in os.environ}
        try:
            from focus_groups.db import _pg_kwargs
            result = _pg_kwargs()
            assert result == {
                "host": "localhost",
                "port": "5432",
                "dbname": "focusgroups",
                "user": "fg_user",
                "password": "localdev",
            }
        finally:
            os.environ.update(env_backup)

    def test_database_url_takes_priority(self):
        """DATABASE_URL takes priority over individual PG_* vars when both are set."""
        url = "postgresql://render:secret@render-host:5432/renderdb"
        env = {
            "DATABASE_URL": url,
            "PG_HOST": "localhost",
            "PG_PORT": "5432",
            "PG_DB": "focusgroups",
            "PG_USER": "fg_user",
            "PG_PASSWORD": "localdev",
        }
        with patch.dict(os.environ, env, clear=False):
            from focus_groups.db import _pg_kwargs
            result = _pg_kwargs()
        assert result == {"dsn": url}


class TestGetConnWithDsn:
    """Test that get_conn() works when _pg_kwargs returns dsn format."""

    @patch("focus_groups.db.register_vector")
    @patch("focus_groups.db.psycopg2.connect")
    def test_get_conn_with_database_url(self, mock_connect, mock_register):
        """get_conn() passes dsn to psycopg2.connect when DATABASE_URL is set."""
        url = "postgresql://user:pass@host:5432/mydb"
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn

        with patch.dict(os.environ, {"DATABASE_URL": url}, clear=False):
            from focus_groups.db import get_conn
            conn = get_conn()

        mock_connect.assert_called_once_with(dsn=url)
        mock_register.assert_called_once_with(mock_conn)
        assert conn is mock_conn

    @patch("focus_groups.db.register_vector")
    @patch("focus_groups.db.psycopg2.connect")
    def test_get_conn_with_pg_vars(self, mock_connect, mock_register):
        """get_conn() passes individual kwargs to psycopg2.connect when no DATABASE_URL."""
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn

        env_remove = {"DATABASE_URL"}
        env_backup = {k: os.environ.pop(k) for k in env_remove if k in os.environ}
        try:
            from focus_groups.db import get_conn
            conn = get_conn()
            call_kwargs = mock_connect.call_args[1]
            assert "host" in call_kwargs
            assert "dsn" not in call_kwargs
        finally:
            os.environ.update(env_backup)


class TestInitPoolWithDsn:
    """Test that init_pool() works when _pg_kwargs returns dsn format."""

    @patch("focus_groups.db.ThreadedConnectionPool")
    def test_init_pool_with_database_url(self, mock_pool_cls):
        """init_pool() passes dsn to ThreadedConnectionPool when DATABASE_URL is set."""
        url = "postgresql://user:pass@host:5432/mydb"

        with patch.dict(os.environ, {"DATABASE_URL": url}, clear=False):
            import focus_groups.db as db_mod
            db_mod._pool = None  # reset
            db_mod.init_pool(minconn=1, maxconn=5)

        mock_pool_cls.assert_called_once_with(1, 5, dsn=url)

    @patch("focus_groups.db.ThreadedConnectionPool")
    def test_init_pool_with_pg_vars(self, mock_pool_cls):
        """init_pool() passes individual kwargs when no DATABASE_URL."""
        env_backup = {}
        if "DATABASE_URL" in os.environ:
            env_backup["DATABASE_URL"] = os.environ.pop("DATABASE_URL")
        try:
            import focus_groups.db as db_mod
            db_mod._pool = None  # reset
            db_mod.init_pool(minconn=1, maxconn=5)
            call_kwargs = mock_pool_cls.call_args[1]
            assert "host" in call_kwargs
            assert "dsn" not in call_kwargs
        finally:
            os.environ.update(env_backup)
