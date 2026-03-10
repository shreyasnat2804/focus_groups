"""Shared test fixtures."""

import pytest


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """Reset the slowapi rate limiter before each test to avoid cross-test pollution."""
    from focus_groups.api import app
    app.state.limiter.reset()
