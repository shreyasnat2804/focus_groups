"""Tests for Render deployment configuration."""

import pathlib

import yaml
import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
RENDER_YAML = ROOT / "render.yaml"
NGINX_CONF = ROOT / "frontend" / "nginx.conf"
FRONTEND_DOCKERFILE = ROOT / "frontend" / "Dockerfile"


# ── render.yaml existence & validity ────────────────────────────────────────


def test_render_yaml_exists():
    assert RENDER_YAML.exists(), "render.yaml must exist at repo root"


def test_render_yaml_is_valid():
    data = yaml.safe_load(RENDER_YAML.read_text())
    assert isinstance(data, dict)


# ── databases section ───────────────────────────────────────────────────────


@pytest.fixture
def render_data():
    return yaml.safe_load(RENDER_YAML.read_text())


def test_databases_section_exists(render_data):
    assert "databases" in render_data


def test_fg_db_database(render_data):
    dbs = render_data["databases"]
    names = [db["name"] for db in dbs]
    assert "fg-db" in names


# ── services section ────────────────────────────────────────────────────────


def test_services_section_exists(render_data):
    assert "services" in render_data


def _find_service(render_data, name):
    for svc in render_data["services"]:
        if svc["name"] == name:
            return svc
    pytest.fail(f"Service '{name}' not found in render.yaml")


def test_fg_api_service(render_data):
    svc = _find_service(render_data, "fg-api")
    assert svc["dockerfilePath"] == "./Dockerfile"
    assert svc["healthCheckPath"] == "/health"


def test_fg_web_service(render_data):
    svc = _find_service(render_data, "fg-web")
    assert svc["dockerfilePath"] == "./frontend/Dockerfile"
    assert svc["healthCheckPath"] == "/health"


def test_fg_api_has_database_url(render_data):
    svc = _find_service(render_data, "fg-api")
    env_vars = {e["key"]: e for e in svc["envVars"]}
    assert "DATABASE_URL" in env_vars
    assert "fromDatabase" in env_vars["DATABASE_URL"]


def test_fg_api_has_anthropic_key(render_data):
    svc = _find_service(render_data, "fg-api")
    env_vars = {e["key"]: e for e in svc["envVars"]}
    assert "ANTHROPIC_API_KEY" in env_vars


def test_both_services_have_port(render_data):
    for name in ("fg-api", "fg-web"):
        svc = _find_service(render_data, name)
        env_keys = [e["key"] for e in svc["envVars"]]
        assert "PORT" in env_keys, f"{name} must have PORT env var"


# ── frontend nginx.conf uses PORT variable substitution ─────────────────────


def test_nginx_conf_uses_port_variable():
    content = NGINX_CONF.read_text()
    assert "${PORT}" in content, "nginx.conf must use ${PORT} variable substitution"
    assert "listen 8080" not in content, "nginx.conf must not hardcode port 8080"


# ── frontend Dockerfile uses envsubst ────────────────────────────────────────


def test_frontend_dockerfile_uses_envsubst():
    content = FRONTEND_DOCKERFILE.read_text()
    assert "envsubst" in content, "Dockerfile must use envsubst for PORT substitution"


def test_frontend_dockerfile_copies_template():
    content = FRONTEND_DOCKERFILE.read_text()
    assert "default.conf.template" in content, (
        "Dockerfile must copy nginx.conf as a .template file"
    )


def test_frontend_dockerfile_sets_port_env():
    content = FRONTEND_DOCKERFILE.read_text()
    assert "ENV PORT=8080" in content or "ENV PORT 8080" in content, (
        "Dockerfile must set default PORT=8080"
    )
