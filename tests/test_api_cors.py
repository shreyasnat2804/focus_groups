"""
Tests for CORS middleware configuration.

Verifies that:
- Allowed origins get proper CORS headers
- Non-allowed origins are rejected (no CORS headers)
- Credentials, methods, and headers are explicitly scoped
"""

import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def cors_client():
    """Create a test client with mocked DB and default CORS origins."""
    mock_conn = MagicMock()

    with patch.dict(os.environ, {}, clear=False):
        # Remove CORS_ORIGINS if set so defaults apply
        os.environ.pop("CORS_ORIGINS", None)

        # Re-import to pick up env changes
        import importlib
        import focus_groups.api as api_mod
        importlib.reload(api_mod)

        api_mod.app.dependency_overrides[api_mod.get_db] = lambda: mock_conn
        api_mod.app.state.limiter.reset()
        client = TestClient(api_mod.app)

        yield client

        api_mod.app.dependency_overrides.clear()


@pytest.fixture
def custom_cors_client():
    """Create a test client with a custom CORS_ORIGINS env var."""
    mock_conn = MagicMock()

    with patch.dict(os.environ, {"CORS_ORIGINS": "https://app.example.com,https://staging.example.com"}):
        import importlib
        import focus_groups.api as api_mod
        importlib.reload(api_mod)

        api_mod.app.dependency_overrides[api_mod.get_db] = lambda: mock_conn
        api_mod.app.state.limiter.reset()
        client = TestClient(api_mod.app)

        yield client

        api_mod.app.dependency_overrides.clear()


def test_allowed_origin_gets_cors_headers(cors_client):
    """Request from an allowed origin should get Access-Control-Allow-Origin."""
    resp = cors_client.options(
        "/api/sessions",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert resp.headers.get("access-control-allow-credentials") == "true"


def test_second_allowed_origin(cors_client):
    """localhost:3000 is also in the default allow list."""
    resp = cors_client.options(
        "/api/sessions",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:3000"


def test_disallowed_origin_no_cors_headers(cors_client):
    """Request from a non-allowed origin should not get CORS headers."""
    resp = cors_client.options(
        "/api/sessions",
        headers={
            "Origin": "https://evil.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert resp.headers.get("access-control-allow-origin") is None


def test_wildcard_origin_not_allowed(cors_client):
    """Ensure we're not using wildcard origins."""
    resp = cors_client.options(
        "/api/sessions",
        headers={
            "Origin": "https://anything.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    # If wildcard were set, this would return '*' or the origin
    assert resp.headers.get("access-control-allow-origin") is None


def test_allowed_methods_are_explicit(cors_client):
    """Only explicitly listed HTTP methods should be allowed."""
    resp = cors_client.options(
        "/api/sessions",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
        },
    )
    allowed = resp.headers.get("access-control-allow-methods", "")
    for method in ["GET", "POST", "PUT", "PATCH", "DELETE"]:
        assert method in allowed


def test_allowed_headers_include_api_key(cors_client):
    """X-API-Key should be in the allowed headers."""
    resp = cors_client.options(
        "/api/sessions",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "X-API-Key",
        },
    )
    allowed_headers = resp.headers.get("access-control-allow-headers", "")
    assert "x-api-key" in allowed_headers.lower()


def test_custom_cors_origins_from_env(custom_cors_client):
    """CORS_ORIGINS env var should control allowed origins."""
    resp = custom_cors_client.options(
        "/api/sessions",
        headers={
            "Origin": "https://app.example.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert resp.headers.get("access-control-allow-origin") == "https://app.example.com"


def test_custom_cors_rejects_unlisted_origin(custom_cors_client):
    """Origins not in CORS_ORIGINS env var should be rejected."""
    resp = custom_cors_client.options(
        "/api/sessions",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert resp.headers.get("access-control-allow-origin") is None
