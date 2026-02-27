"""Tests for health check endpoints.

Verifies:
- GET /health returns 200 (liveness probe)
- GET /ready returns 200 when DB is healthy (readiness probe)
- GET /ready returns 503 when DB is unreachable
- Both endpoints work without authentication
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Test client with mocked DB pool."""
    with patch("focus_groups.api.init_pool"), \
         patch("focus_groups.api.close_pool"):
        from focus_groups.api import app
        yield TestClient(app)


class TestLiveness:
    """Tests for GET /health."""

    def test_returns_200(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    def test_no_auth_required(self, client):
        """Health endpoint must work without X-API-Key header."""
        # Ensure FG_API_KEY is set so auth would reject if applied
        with patch.dict("os.environ", {"FG_API_KEY": "secret"}, clear=False):
            resp = client.get("/health")
        assert resp.status_code == 200


class TestReadiness:
    """Tests for GET /ready."""

    def test_returns_200_when_db_healthy(self, client):
        mock_conn = MagicMock()
        with patch("focus_groups.api.get_pool_conn", return_value=mock_conn), \
             patch("focus_groups.api.return_pool_conn"):
            resp = client.get("/ready")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ready"}

    def test_returns_503_when_db_unavailable(self, client):
        with patch("focus_groups.api.get_pool_conn", side_effect=Exception("pool exhausted")):
            resp = client.get("/ready")
        assert resp.status_code == 503
        assert resp.json()["status"] == "unavailable"

    def test_returns_503_when_query_fails(self, client):
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value.execute.side_effect = Exception("db down")
        with patch("focus_groups.api.get_pool_conn", return_value=mock_conn), \
             patch("focus_groups.api.return_pool_conn"):
            resp = client.get("/ready")
        assert resp.status_code == 503

    def test_no_auth_required(self, client):
        """Ready endpoint must work without X-API-Key header."""
        mock_conn = MagicMock()
        with patch.dict("os.environ", {"FG_API_KEY": "secret"}, clear=False), \
             patch("focus_groups.api.get_pool_conn", return_value=mock_conn), \
             patch("focus_groups.api.return_pool_conn"):
            resp = client.get("/ready")
        assert resp.status_code == 200

    def test_connection_returned_on_success(self, client):
        """Pool connection must be returned even on success."""
        mock_conn = MagicMock()
        with patch("focus_groups.api.get_pool_conn", return_value=mock_conn) as mock_get, \
             patch("focus_groups.api.return_pool_conn") as mock_return:
            client.get("/ready")
        mock_return.assert_called_once_with(mock_conn)

    def test_connection_returned_on_query_failure(self, client):
        """Pool connection must be returned even when query fails."""
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value.execute.side_effect = Exception("fail")
        with patch("focus_groups.api.get_pool_conn", return_value=mock_conn), \
             patch("focus_groups.api.return_pool_conn") as mock_return:
            client.get("/ready")
        mock_return.assert_called_once_with(mock_conn)
