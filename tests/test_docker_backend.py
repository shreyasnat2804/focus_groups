"""Tests for backend Docker configuration files."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_dockerfile_exists():
    assert (ROOT / "Dockerfile").is_file(), "Dockerfile must exist at project root"


def test_dockerfile_has_builder_stage():
    text = (ROOT / "Dockerfile").read_text()
    assert "AS builder" in text, "Dockerfile must have a builder stage"


def test_dockerfile_has_runtime_stage():
    text = (ROOT / "Dockerfile").read_text()
    lines = text.splitlines()
    from_lines = [l for l in lines if l.strip().startswith("FROM")]
    assert len(from_lines) >= 2, "Dockerfile must have at least two FROM stages (multi-stage)"


def test_dockerfile_uses_gunicorn():
    text = (ROOT / "Dockerfile").read_text()
    assert "gunicorn" in text, "Dockerfile CMD must use gunicorn"


def test_dockerfile_exposes_8080():
    text = (ROOT / "Dockerfile").read_text()
    assert "EXPOSE 8080" in text, "Dockerfile must expose port 8080"


def test_dockerfile_non_root_user():
    text = (ROOT / "Dockerfile").read_text()
    assert "USER" in text, "Dockerfile must switch to a non-root user"


def test_dockerignore_exists():
    assert (ROOT / ".dockerignore").is_file(), ".dockerignore must exist at project root"


def test_dockerignore_excludes_env():
    text = (ROOT / ".dockerignore").read_text()
    assert ".env" in text, ".dockerignore must exclude .env"


def test_dockerignore_excludes_git():
    text = (ROOT / ".dockerignore").read_text()
    assert ".git/" in text, ".dockerignore must exclude .git/"


def test_dockerignore_excludes_tests():
    text = (ROOT / ".dockerignore").read_text()
    assert "tests/" in text, ".dockerignore must exclude tests/"


def test_requirements_no_sentence_transformers():
    text = (ROOT / "requirements.txt").read_text()
    assert "sentence-transformers" not in text, (
        "requirements.txt must not contain sentence-transformers (moved to requirements-ml.txt)"
    )


def test_requirements_no_torch():
    text = (ROOT / "requirements.txt").read_text()
    assert "torch" not in text, (
        "requirements.txt must not contain torch (moved to requirements-ml.txt)"
    )


def test_requirements_has_gunicorn():
    text = (ROOT / "requirements.txt").read_text()
    assert "gunicorn" in text, "requirements.txt must include gunicorn"


def test_requirements_has_fastapi():
    text = (ROOT / "requirements.txt").read_text()
    assert "fastapi" in text, "requirements.txt must include fastapi"


def test_requirements_ml_exists():
    assert (ROOT / "requirements-ml.txt").is_file(), "requirements-ml.txt must exist"


def test_requirements_ml_references_base():
    text = (ROOT / "requirements-ml.txt").read_text()
    assert "-r requirements.txt" in text, (
        "requirements-ml.txt must reference requirements.txt via -r"
    )


def test_requirements_ml_has_sentence_transformers():
    text = (ROOT / "requirements-ml.txt").read_text()
    assert "sentence-transformers" in text, (
        "requirements-ml.txt must include sentence-transformers"
    )
