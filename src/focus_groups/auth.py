"""API key authentication via X-API-Key header."""

import os

from fastapi import Security, HTTPException
from fastapi.security import APIKeyHeader

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


def get_api_key() -> str | None:
    """Read API key from environment. Returns None if auth is disabled."""
    return os.getenv("FG_API_KEY")


async def require_api_key(api_key: str = Security(API_KEY_HEADER)):
    """FastAPI dependency that validates the API key.

    If FG_API_KEY is not set, authentication is disabled (local dev convenience).
    """
    expected = get_api_key()
    if expected is None:
        return  # Auth disabled
    if not api_key or api_key != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
