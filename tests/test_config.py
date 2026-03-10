"""
Tests for configuration and environment variable setup.

Validates that:
- .env.example exists and documents all required env vars
- .env.example does not contain real secrets
- .gitignore excludes .env
"""

import pathlib

# Project root is one level up from tests/
ROOT = pathlib.Path(__file__).resolve().parent.parent

REQUIRED_KEYS = [
    "PG_HOST",
    "PG_PORT",
    "PG_DB",
    "PG_USER",
    "PG_PASSWORD",
    "ANTHROPIC_API_KEY",
]


def _read_env_example() -> str:
    path = ROOT / ".env.example"
    assert path.exists(), ".env.example must exist at the project root"
    return path.read_text()


def test_env_example_exists():
    assert (ROOT / ".env.example").exists(), ".env.example is missing"


def test_env_example_contains_required_keys():
    content = _read_env_example()
    for key in REQUIRED_KEYS:
        assert key in content, f".env.example is missing required key: {key}"


def test_env_example_has_no_real_secrets():
    """Ensure .env.example doesn't contain actual API keys or passwords."""
    content = _read_env_example()
    # Anthropic API key prefix
    assert "sk-ant-" not in content, ".env.example contains a real Anthropic API key"
    # Generic secret patterns
    assert "sk-proj-" not in content, ".env.example contains a real OpenAI key"
    # Check that PG_PASSWORD isn't set to something that looks like a real password
    # (the placeholder 'localdev' is fine since it's the local dev default)
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if "PASSWORD" in stripped and "=" in stripped:
            _, _, value = stripped.partition("=")
            value = value.strip()
            assert len(value) < 40, (
                f"PG_PASSWORD value looks like a real secret (too long): {value[:10]}..."
            )


def test_gitignore_contains_env():
    gitignore = ROOT / ".gitignore"
    assert gitignore.exists(), ".gitignore is missing"
    content = gitignore.read_text()
    lines = [line.strip() for line in content.splitlines()]
    assert ".env" in lines, ".gitignore must contain '.env' on its own line"
