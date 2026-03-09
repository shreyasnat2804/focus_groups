"""Tests for Makefile and .env.example completeness."""

import os
import re
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAKEFILE_PATH = os.path.join(ROOT, "Makefile")
ENV_EXAMPLE_PATH = os.path.join(ROOT, ".env.example")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read(path: str) -> str:
    with open(path) as f:
        return f.read()


def _makefile_targets(content: str) -> list[str]:
    """Extract target names from a Makefile (lines like 'target:')."""
    return re.findall(r"^([a-zA-Z_][a-zA-Z0-9_-]*)\s*:", content, re.MULTILINE)


# ---------------------------------------------------------------------------
# Makefile existence and parseability
# ---------------------------------------------------------------------------

class TestMakefileExists:
    def test_makefile_exists(self):
        assert os.path.isfile(MAKEFILE_PATH), "Makefile not found at project root"

    def test_makefile_not_empty(self):
        content = _read(MAKEFILE_PATH)
        assert len(content.strip()) > 0, "Makefile is empty"

    def test_makefile_parseable_by_make(self):
        """make --dry-run --print-data-base should succeed (parse check)."""
        result = subprocess.run(
            ["make", "-n", "-p", "-f", MAKEFILE_PATH],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"make failed to parse Makefile: {result.stderr}"
        )


# ---------------------------------------------------------------------------
# Expected targets
# ---------------------------------------------------------------------------

EXPECTED_TARGETS = [
    "build-api",
    "build-web",
    "push-api",
    "push-web",
    "deploy-api",
    "deploy-web",
    "setup-secrets",
    "setup-gcp",
    "deploy-all",
    "local",
    "test",
]


class TestMakefileTargets:
    def test_all_expected_targets_present(self):
        content = _read(MAKEFILE_PATH)
        targets = _makefile_targets(content)
        for expected in EXPECTED_TARGETS:
            assert expected in targets, f"Missing Makefile target: {expected}"


# ---------------------------------------------------------------------------
# Variables
# ---------------------------------------------------------------------------

class TestMakefileVariables:
    def test_project_id_defined(self):
        content = _read(MAKEFILE_PATH)
        assert re.search(r"^PROJECT_ID\s*\??\s*[:?]?=", content, re.MULTILINE), (
            "PROJECT_ID variable not defined in Makefile"
        )

    def test_region_defined(self):
        content = _read(MAKEFILE_PATH)
        assert re.search(r"^REGION\s*\??\s*[:?]?=", content, re.MULTILINE), (
            "REGION variable not defined in Makefile"
        )


# ---------------------------------------------------------------------------
# .env.example
# ---------------------------------------------------------------------------

REQUIRED_ENV_VARS = [
    "PG_HOST",
    "PG_PORT",
    "PG_DB",
    "PG_USER",
    "PG_PASSWORD",
    "ANTHROPIC_API_KEY",
    "FG_API_KEY",
    "CORS_ORIGINS",
    "LOG_FORMAT",
    "LOG_LEVEL",
]


class TestEnvExample:
    def test_env_example_exists(self):
        assert os.path.isfile(ENV_EXAMPLE_PATH), ".env.example not found"

    def test_all_required_vars_present(self):
        content = _read(ENV_EXAMPLE_PATH)
        for var in REQUIRED_ENV_VARS:
            assert re.search(rf"^#?\s*{var}\s*=", content, re.MULTILINE), (
                f"Missing variable in .env.example: {var}"
            )
