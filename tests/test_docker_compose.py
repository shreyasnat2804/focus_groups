"""Tests for docker-compose.yml full 3-service local dev stack."""

import pathlib

import yaml
import pytest

COMPOSE_PATH = pathlib.Path(__file__).resolve().parent.parent / "docker-compose.yml"


@pytest.fixture
def compose():
    """Load and parse docker-compose.yml."""
    with open(COMPOSE_PATH) as f:
        return yaml.safe_load(f)


class TestServiceDefinitions:
    """Verify the compose file defines exactly the expected services."""

    def test_defines_three_services(self, compose):
        services = set(compose["services"].keys())
        assert services == {"db", "api", "web"}

    def test_no_version_key(self, compose):
        assert "version" not in compose, (
            "The deprecated 'version' key should not be present"
        )


class TestDbService:
    """Verify db service configuration."""

    def test_image_is_pgvector_pg16(self, compose):
        assert compose["services"]["db"]["image"] == "pgvector/pgvector:pg16"

    def test_has_healthcheck(self, compose):
        db = compose["services"]["db"]
        assert "healthcheck" in db
        assert "test" in db["healthcheck"]

    def test_port_mapping(self, compose):
        ports = compose["services"]["db"]["ports"]
        assert "5432:5432" in ports


class TestApiService:
    """Verify api service configuration."""

    def test_depends_on_db_healthy(self, compose):
        api = compose["services"]["api"]
        assert "depends_on" in api
        assert "db" in api["depends_on"]
        assert api["depends_on"]["db"]["condition"] == "service_healthy"

    def test_pg_host_is_db(self, compose):
        env = compose["services"]["api"]["environment"]
        assert env["PG_HOST"] == "db"

    def test_port_mapping(self, compose):
        ports = compose["services"]["api"]["ports"]
        assert "8000:8080" in ports

    def test_has_healthcheck(self, compose):
        api = compose["services"]["api"]
        assert "healthcheck" in api


class TestWebService:
    """Verify web service configuration."""

    def test_depends_on_api_healthy(self, compose):
        web = compose["services"]["web"]
        assert "depends_on" in web
        assert "api" in web["depends_on"]
        assert web["depends_on"]["api"]["condition"] == "service_healthy"

    def test_port_mapping(self, compose):
        ports = compose["services"]["web"]["ports"]
        assert "3000:8080" in ports
