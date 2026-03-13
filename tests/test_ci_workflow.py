"""Tests to validate the GitHub Actions CI workflow YAML structure."""

import pathlib

import yaml
import pytest


WORKFLOW_PATH = pathlib.Path(__file__).resolve().parents[1] / ".github" / "workflows" / "ci.yml"


@pytest.fixture
def workflow():
    """Load and parse the CI workflow YAML."""
    assert WORKFLOW_PATH.exists(), f"Workflow file not found at {WORKFLOW_PATH}"
    return yaml.safe_load(WORKFLOW_PATH.read_text())


class TestCIWorkflowStructure:
    """Validate the CI workflow YAML has the expected structure."""

    def test_has_test_job(self, workflow):
        """Workflow must define a 'test' job."""
        assert "jobs" in workflow
        assert "test" in workflow["jobs"], "Missing 'test' job in workflow"

    def test_python_version(self, workflow):
        """Test job must use Python 3.11."""
        steps = workflow["jobs"]["test"]["steps"]
        setup_python_steps = [
            s for s in steps
            if isinstance(s.get("uses", ""), str) and s.get("uses", "").startswith("actions/setup-python")
        ]
        assert len(setup_python_steps) == 1, "Expected exactly one setup-python step"
        python_version = setup_python_steps[0]["with"]["python-version"]
        assert str(python_version) == "3.11", f"Expected Python 3.11, got {python_version}"

    def test_postgres_service_uses_pgvector(self, workflow):
        """Test job must have a postgres service using the pgvector image."""
        services = workflow["jobs"]["test"].get("services", {})
        assert "postgres" in services, "Missing 'postgres' service"
        image = services["postgres"]["image"]
        assert "pgvector/pgvector" in image, f"Expected pgvector image, got {image}"
        assert "pg16" in image, f"Expected pg16 tag in image, got {image}"

    def test_triggers_on_correct_branches(self, workflow):
        """Workflow must trigger on push to main/poc and PRs to main."""
        on = workflow[True]  # YAML parses 'on' as True
        # Push triggers
        push_branches = on["push"]["branches"]
        assert "main" in push_branches, "Push trigger missing 'main' branch"
        assert "poc" in push_branches, "Push trigger missing 'poc' branch"
        # PR triggers
        pr_branches = on["pull_request"]["branches"]
        assert "main" in pr_branches, "PR trigger missing 'main' branch"

    def test_runs_on_ubuntu_latest(self, workflow):
        """Test job must run on ubuntu-latest."""
        runs_on = workflow["jobs"]["test"]["runs-on"]
        assert runs_on == "ubuntu-latest"

    def test_has_checkout_step(self, workflow):
        """Test job must checkout the repo."""
        steps = workflow["jobs"]["test"]["steps"]
        checkout_steps = [
            s for s in steps
            if isinstance(s.get("uses", ""), str) and "actions/checkout" in s.get("uses", "")
        ]
        assert len(checkout_steps) >= 1, "Missing actions/checkout step"

    def test_has_install_dependencies_step(self, workflow):
        """Test job must install dependencies from requirements.txt."""
        steps = workflow["jobs"]["test"]["steps"]
        install_steps = [
            s for s in steps
            if "Install dependencies" in s.get("name", "")
        ]
        assert len(install_steps) == 1, "Missing install dependencies step"
        run_cmd = install_steps[0]["run"]
        assert "requirements.txt" in run_cmd
        assert "pip install -e ." in run_cmd
        assert "pytest" in run_cmd

    def test_has_init_db_step(self, workflow):
        """Test job must init the DB schema with db/init.sql."""
        steps = workflow["jobs"]["test"]["steps"]
        db_steps = [
            s for s in steps
            if "Init DB" in s.get("name", "")
        ]
        assert len(db_steps) == 1, "Missing Init DB step"
        assert "db/init.sql" in db_steps[0]["run"]

    def test_has_run_tests_step(self, workflow):
        """Test job must run pytest."""
        steps = workflow["jobs"]["test"]["steps"]
        test_steps = [
            s for s in steps
            if "Run tests" in s.get("name", "")
        ]
        assert len(test_steps) == 1, "Missing Run tests step"
        assert "pytest" in test_steps[0]["run"]

    def test_deploy_jobs_gated_on_main(self, workflow):
        """Deploy jobs should only run on pushes to main."""
        jobs = workflow["jobs"]
        for name in ("deploy-api", "deploy-web"):
            assert name in jobs, f"{name} job missing"
            assert "main" in jobs[name].get("if", ""), f"{name} should be gated to main"
